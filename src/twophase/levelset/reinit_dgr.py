"""
Direct Geometric Reinitialization (DGR, WIKI-T-030) and Hybrid strategies.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..interfaces.levelset import IReinitializer
from .heaviside import heaviside, invert_heaviside, apply_mass_correction

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class DGRReinitializer(IReinitializer):
    """Direct Geometric Reinitialization (DGR).

    Restores interface thickness to ε in one step via logit inversion.
    See WIKI-T-030 for proofs.
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps

    def reinitialize(self, psi):
        xp = self.xp
        psi = xp.asarray(psi)  # Ensure device-native (no-op on CPU).
        dV = xp.asarray(self.grid.cell_volumes())
        M_old = float(xp.sum(psi * dV))

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
            eps_eff = float(xp.median(eps_local))
        else:
            eps_eff = self.eps

        phi_raw = invert_heaviside(xp, psi, self.eps)
        scale = eps_eff / self.eps if eps_eff > 1e-14 else 1.0
        phi_sdf = phi_raw * scale

        psi_new = heaviside(xp, phi_sdf, self.eps)
        psi_new = apply_mass_correction(xp, psi_new, dV, M_old)
        return psi_new


class HybridReinitializer(IReinitializer):
    """Hybrid: shape restoration (split) + thickness correction (DGR).

    Composes SplitReinitializer and DGRReinitializer sequentially.
    """

    def __init__(self, split: IReinitializer, dgr: IReinitializer):
        self._split = split
        self._dgr = dgr

    def reinitialize(self, psi):
        q = self._split.reinitialize(psi)
        q = self._dgr.reinitialize(q)
        return q
