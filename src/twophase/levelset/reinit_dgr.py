"""
Direct Geometric Reinitialization (DGR, WIKI-T-030) and Hybrid strategies.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .interfaces import IReinitializer
from .heaviside import heaviside, invert_heaviside
from ..core.boundary import boundary_axes, sync_periodic_image_nodes

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class DGRReinitializer(IReinitializer):
    """Direct Geometric Reinitialization (DGR).

    Restores interface thickness to ε in one step via logit inversion.
    See WIKI-T-030 for proofs.

    Design note: DGR corrects interface THICKNESS only (assumes |∇φ_true|≈1).
    For simulations with σ>0 and capillary dynamics, the interface can develop
    folds (|∇ψ|→0 in band) that DGR cannot correct (global median scale≈1
    is insensitive to local outliers). Chapter 5 therefore forbids appending
    DGR after split reinitialization for such oscillatory capillary cases.
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, phi_smooth_C: float = 0.0):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.phi_smooth_C = float(phi_smooth_C)
        self._bc_axes = boundary_axes(getattr(ccd, "bc_type", "wall"), grid.ndim)

    def reinitialize(self, psi):
        xp = self.xp
        psi = xp.asarray(psi)  # Ensure device-native (no-op on CPU).
        sync_periodic_image_nodes(psi, self._bc_axes)
        dV = self.grid.cell_volumes()
        M_old = xp.sum(psi * dV)

        # Compute |∇ψ| via CCD
        grad_sq = xp.zeros_like(psi)
        for ax in range(self.grid.ndim):
            g1, _ = self.ccd.differentiate(psi, ax)
            grad_sq = grad_sq + g1 * g1
        grad_psi = xp.sqrt(xp.maximum(grad_sq, 1e-28))

        # Estimate ε_eff from interface band (0.05 < ψ < 0.95)
        band = (psi > 0.05) & (psi < 0.95)
        psi_1mpsi = psi * (1.0 - psi)
        if xp.any(band):
            eps_local = psi_1mpsi[band] / xp.maximum(grad_psi[band], 1e-14)
            # GPU sync point: scalar extraction forces device→host transfer.
            # Acceptable — DGR runs every reinit_every steps, not every step.
            eps_eff = float(xp.median(eps_local))
        else:
            eps_eff = self.eps

        phi_raw = invert_heaviside(xp, psi, self.eps)
        sync_periodic_image_nodes(phi_raw, self._bc_axes)
        scale = eps_eff / self.eps if eps_eff > 1e-14 else 1.0
        phi_sdf = phi_raw * scale

        # Optional non-paper compatibility smoothing on φ_sdf.
        # Default is 0.0 so the Chapter 5 DGR map remains exactly:
        # logit inversion → ε_eff/ε rescale → H_ε reconstruction → φ-shift.
        #
        # CCD Laplacian smoothing on φ_sdf (WIKI-T-030 addendum).
        # ∇²φ ≈ κ = O(1) → C·h²·∇²φ = O(h²) → convergence-preserving.
        # Damps O(h^5) wall-boundary asymmetry accumulated over ~10^4 steps.
        if self.phi_smooth_C > 0.0:
            from .curvature_filter import _ccd_laplacian
            h_min = min(float(xp.min(xp.asarray(self.grid.h[ax])))
                        for ax in range(self.grid.ndim))
            phi_sdf = phi_sdf + self.phi_smooth_C * h_min**2 * _ccd_laplacian(xp, self.ccd, phi_sdf)
            sync_periodic_image_nodes(phi_sdf, self._bc_axes)

        psi_new = heaviside(xp, phi_sdf, self.eps)
        sync_periodic_image_nodes(psi_new, self._bc_axes)
        # φ-space mass correction: uniform interface shift, no shape distortion.
        # ψ-space correction (λ·4q(1-q)) shifts interface by δx ∝ 1/|∇ψ| which is
        # curvature-dependent → systematic mode elongation on oscillating droplets.
        # φ-space: δφ = ΔM / ∫H'_ε dV; interface shifts uniformly δx = δφ/|∇φ|≈δφ
        # (since DGR produces |∇φ_sdf|≈1 post-scale). No shape change for curved interfaces.
        w_phi = psi_new * (1.0 - psi_new) / self.eps  # H'_eps(phi_sdf) = dψ/dφ
        W = xp.sum(w_phi * dV)
        M_new = xp.sum(psi_new * dV)
        active = W > 1e-14
        W_safe = xp.where(active, W, 1.0)
        delta_phi = xp.where(active, (M_old - M_new) / W_safe, 0.0)
        phi_sdf = phi_sdf + delta_phi
        sync_periodic_image_nodes(phi_sdf, self._bc_axes)
        psi_new = heaviside(xp, phi_sdf, self.eps)
        sync_periodic_image_nodes(psi_new, self._bc_axes)
        return psi_new


class HybridReinitializer(IReinitializer):
    """Hybrid: shape restoration (split) + thickness correction (DGR).

    Composes SplitReinitializer and DGRReinitializer sequentially.  This path
    is retained for explicit comparison/legacy studies only.  Chapter 5 states
    that σ>0 oscillatory capillary cases must not append DGR after split
    reinitialization because fold cells can make the median-width DGR correction
    generate nonphysical curvature spikes.
    """

    def __init__(self, split: IReinitializer, dgr: IReinitializer):
        self._split = split
        self._dgr = dgr

    def reinitialize(self, psi):
        q = self._split.reinitialize(psi)
        q = self._dgr.reinitialize(q)
        return q
