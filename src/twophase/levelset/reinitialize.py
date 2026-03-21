"""
Conservative Level Set reinitialization.

Implements §3.4 (Eq. 34) and §8.2–§8.3 of the paper.

The reinitialization PDE (in pseudo-time τ):

    ∂ψ/∂τ + ∇·[ψ(1−ψ) n̂] = ε ∇²ψ              (§3.4 Eq.34)

where n̂ = ∇ψ / |∇ψ| is the interface normal.

Left term: compression towards a step profile.
Right term: diffusion that controls interface thickness.
Equilibrium solution: ψ = H_ε(s/ε) where s is the signed distance.

Time integration (pseudo-time τ):
    TVD-RK3 (Shu–Osher scheme, §8.2 Eq. 79–81) — same as CLS advection.

Spatial discretization of compression term ∇·[ψ(1−ψ) n̂] (§8.3):
    WENO5 flux splitting with global Lax-Friedrichs dissipation.
    Flux F_ax = ψ(1−ψ) n̂_ax;  wave-speed bound α = max|ψ(1−ψ)| ≤ 1/4.
    LF split: F^± = (F ± α ψ) / 2 → WENO5 reconstruction → divergence.

Diffusion term ε ∇²ψ: evaluated with CCD 6th-order Laplacian.

The pseudo-time step is chosen as:
    Δτ = min(0.5 · min(Δx), min(Δx)² / (2·ndim·ε))   (§3.4 stability)

satisfying both the hyperbolic CFL and the parabolic stability condition.

Volume-conservation monitor M(τ) = ∫ ψ(1−ψ) dV should decrease
monotonically during reinitialization.
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

from ..interfaces.levelset import IReinitializer
from .advection import _weno5_pos, _weno5_neg, _pad_bc

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class Reinitializer(IReinitializer):
    """Reinitialize ψ by integrating the reinitialization PDE.

    Parameters
    ----------
    backend       : Backend
    grid          : Grid (for spacing h and domain size)
    ccd           : CCDSolver — コンストラクタ注入（毎呼び出しでの引き渡し不要）
    eps           : interface thickness ε
    n_steps       : number of pseudo-time steps per call (each is a full TVD-RK3 step)
    bc            : Ghost-cell BC for WENO5 compression stencils (§4 sec:weno5_boundary).
                    'periodic' | 'neumann' | 'outflow' | 'zero' (default, backward-compat)
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero'):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.n_steps = n_steps
        self._bc = bc  # WENO5 圧縮項のゴーストセルBCタイプ
        # Cell spacing per axis (for WENO5 divergence)
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]

        # Pseudo-time step satisfying both CFL conditions (§3.4):
        #   Hyperbolic: Δτ ≤ h / α  where α = max|ψ(1-ψ)| ≤ 1/4  ⟹  Δτ ≤ 4h
        #   Parabolic:  Δτ ≤ h² / (2·ndim·ε)   (explicit diffusion stability)
        # With ε = C·h the parabolic bound dominates for refined grids.
        #
        # TVD-RK3 safety factor (0.5):
        # The classical parabolic bound h²/(2·ndim·ε) is derived for the 2nd-order
        # finite-difference Laplacian.  CCD's 6th-order Laplacian has larger effective
        # eigenvalues for high-frequency (oscillatory) modes that arise near ψ=0 or
        # ψ=1 in the gas/liquid phase.  A safety factor of 0.5 prevents these modes
        # from being amplified within the TVD-RK3 sub-stages, which each take a full
        # forward-Euler step before the weighted combination is applied.
        _TVD_RK3_SAFETY = 0.5
        ndim = grid.ndim
        dx_min = min(float(grid.L[ax] / grid.N[ax]) for ax in range(ndim))
        dtau_para = _TVD_RK3_SAFETY * dx_min**2 / (2.0 * ndim * eps)
        dtau_hyp  = 0.5 * dx_min   # conservative (hyperbolic bound is 4·Δx)
        self.dtau = min(dtau_para, dtau_hyp)

    # ── Public API (IReinitializer 実装) ─────────────────────────────────

    def reinitialize(self, psi) -> "array":
        """Reinitialize ψ using TVD-RK3 pseudo-time integration (§8.2).

        Parameters
        ----------
        psi : array, shape ``grid.shape``

        Returns
        -------
        psi_new : reinitialized ψ array
        """
        xp = self.xp
        q = xp.copy(psi)
        dtau = self.dtau
        ccd = self.ccd

        for _ in range(self.n_steps):
            # TVD-RK3 (Shu-Osher scheme, §8 Eq. 79–81)
            # ψ ∈ [0,1] is enforced at each sub-stage to prevent negative ψ
            # from destabilising the nonlinear WENO5 compression flux.
            r0 = self._rhs(q, ccd)
            q1 = xp.clip(q + dtau * r0, 0.0, 1.0)
            r1 = self._rhs(q1, ccd)
            q2 = xp.clip(0.75 * q + 0.25 * (q1 + dtau * r1), 0.0, 1.0)
            r2 = self._rhs(q2, ccd)
            q = xp.clip((1.0 / 3.0) * q + (2.0 / 3.0) * (q2 + dtau * r2), 0.0, 1.0)

        return q

    # ── RHS of reinit PDE ─────────────────────────────────────────────────

    def _rhs(self, psi, ccd: "CCDSolver"):
        """Compute RHS = −∇·[ψ(1−ψ)n̂] + ε Δψ.

        Compression term ∇·[ψ(1−ψ)n̂] is discretised via WENO5 flux splitting
        (§8.3): flux F_ax = ψ(1−ψ)·n̂_ax, global LF with α = max|ψ(1−ψ)| ≤ 1/4.

        ε Δψ uses the CCD Laplacian (§8.3, "拡散項は CCD 法で評価").
        """
        xp = self.xp
        ndim = self.grid.ndim
        eps = self.eps

        # ── CCD gradient of ψ (for n̂ and Laplacian) ─────────────────────
        dpsi = []
        d2psi_sum = xp.zeros_like(psi)
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(psi, ax)
            dpsi.append(g1)
            d2psi_sum += g2   # Laplacian accumulates

        # n̂ = ∇ψ / |∇ψ|
        grad_psi_sq = sum(g * g for g in dpsi)
        safe_grad   = xp.maximum(xp.sqrt(xp.maximum(grad_psi_sq, 1e-28)), 1e-14)
        n_hat = [g / safe_grad for g in dpsi]

        # ── Compression term ∇·[ψ(1−ψ)n̂] via WENO5 (§8.3) ──────────────
        psi_1mpsi = psi * (1.0 - psi)

        # ── Compression term −∇·[ψ(1−ψ)n̂] via WENO5 (§8.3) ──────────────
        # Flux F_ax = ψ(1-ψ)·n̂_ax.
        # Global LF splitting: F^± = (F ± α·ψ)/2
        # α bounds max|dF/dψ| = max|(1-2ψ)·n̂_ax|.
        # At equilibrium ψ=H_ε(φ), the compression and diffusion terms must
        # balance.  The LF artificial viscosity is proportional to α, so we
        # use α = max|ψ(1-ψ)| (the paper's recommendation, §8.3) which is
        # small near equilibrium and reduces artificial diffusion.
        alpha = float(xp.max(xp.abs(psi_1mpsi)))
        alpha = max(alpha, 1e-14)

        div_compression = xp.zeros_like(psi)
        for ax in range(ndim):
            F_ax = psi_1mpsi * n_hat[ax]   # flux in direction ax
            div_ax = self._weno5_compression_div(psi, F_ax, alpha, ax)
            div_compression += div_ax

        # ── Diffusion term ε Δψ (CCD Laplacian) ──────────────────────────
        return -div_compression + eps * d2psi_sum

    # ── WENO5 flux divergence for compression term ────────────────────────

    def _weno5_compression_div(self, psi, F, alpha: float, axis: int):
        """WENO5 divergence of flux F = ψ(1−ψ)·n̂_ax along ``axis``.

        Uses global Lax-Friedrichs splitting:
            F^± = (F ± α·ψ) / 2   with α = max|ψ(1−ψ)| ≤ 1/4

        Identical stencil structure to LevelSetAdvection._weno5_divergence.
        """
        xp = self.xp
        n = psi.shape[axis]

        # §4 sec:weno5_boundary に従ったゴーストセル補充
        psi_p = _pad_bc(xp, psi, axis, 3, self._bc)
        F_p   = _pad_bc(xp, F,   axis, 3, self._bc)

        def sl(start, stop):
            s = [slice(None)] * psi.ndim
            s[axis] = slice(start, stop if stop != 0 else None)
            return tuple(s)

        i_max = n - 1   # number of internal faces

        # ── Positive-flux stencil (left-biased, nodes i-2..i+2) ──────────
        fp_m2 = F_p[sl(1, 1 + i_max)]
        fp_m1 = F_p[sl(2, 2 + i_max)]
        fp_0  = F_p[sl(3, 3 + i_max)]
        fp_p1 = F_p[sl(4, 4 + i_max)]
        fp_p2 = F_p[sl(5, 5 + i_max)]

        pp_m2 = psi_p[sl(1, 1 + i_max)]
        pp_m1 = psi_p[sl(2, 2 + i_max)]
        pp_0  = psi_p[sl(3, 3 + i_max)]
        pp_p1 = psi_p[sl(4, 4 + i_max)]
        pp_p2 = psi_p[sl(5, 5 + i_max)]

        Fplus_m2 = 0.5 * (fp_m2 + alpha * pp_m2)
        Fplus_m1 = 0.5 * (fp_m1 + alpha * pp_m1)
        Fplus_0  = 0.5 * (fp_0  + alpha * pp_0 )
        Fplus_p1 = 0.5 * (fp_p1 + alpha * pp_p1)
        Fplus_p2 = 0.5 * (fp_p2 + alpha * pp_p2)

        Fp_face = _weno5_pos(xp, Fplus_m2, Fplus_m1, Fplus_0, Fplus_p1, Fplus_p2)

        # ── Negative-flux stencil (right-biased, nodes i+1..i+3) ─────────
        fm_m1 = F_p[sl(2, 2 + i_max)]
        fm_0  = F_p[sl(3, 3 + i_max)]
        fm_p1 = F_p[sl(4, 4 + i_max)]
        fm_p2 = F_p[sl(5, 5 + i_max)]
        fm_p3 = F_p[sl(6, 6 + i_max)]

        pm_m1 = psi_p[sl(2, 2 + i_max)]
        pm_0  = psi_p[sl(3, 3 + i_max)]
        pm_p1 = psi_p[sl(4, 4 + i_max)]
        pm_p2 = psi_p[sl(5, 5 + i_max)]
        pm_p3 = psi_p[sl(6, 6 + i_max)]

        Fminus_m1 = 0.5 * (fm_m1 - alpha * pm_m1)
        Fminus_0  = 0.5 * (fm_0  - alpha * pm_0 )
        Fminus_p1 = 0.5 * (fm_p1 - alpha * pm_p1)
        Fminus_p2 = 0.5 * (fm_p2 - alpha * pm_p2)
        Fminus_p3 = 0.5 * (fm_p3 - alpha * pm_p3)

        Fm_face = _weno5_neg(xp, Fminus_m1, Fminus_0, Fminus_p1, Fminus_p2, Fminus_p3)

        flux_face = Fp_face + Fm_face   # shape: n-1 along axis

        # ── Divergence = (F_{i+1/2} − F_{i-1/2}) / h ─────────────────────
        h = self._h[axis]
        sl_hi = [slice(None)] * psi.ndim
        sl_lo = [slice(None)] * psi.ndim
        sl_hi[axis] = slice(1, None)
        sl_lo[axis] = slice(0, -1)
        div_interior = (flux_face[tuple(sl_hi)] - flux_face[tuple(sl_lo)]) / h

        # Pad boundary nodes to zero (wall BC)
        shape_pad = list(psi.shape)
        shape_pad[axis] = 1
        pad = xp.zeros(shape_pad)
        return xp.concatenate([pad, div_interior, pad], axis=axis)

    # ── Volume monitor ────────────────────────────────────────────────────

    def volume_monitor(self, psi) -> float:
        """M(τ) = ∫ ψ(1−ψ) dV — should decrease during reinitialization."""
        xp = self.xp
        dV = self.grid.cell_volume()
        return float(xp.sum(psi * (1.0 - psi))) * dV
