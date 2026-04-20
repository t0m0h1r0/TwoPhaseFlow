"""
Conservative Level Set reinitialization — facade + legacy.

Reinitializer is a facade (C2 preserved) that delegates to strategy classes:
  - SplitReinitializer     (reinit_split.py)    — operator-split comp+diff
  - UnifiedDCCDReinitializer (reinit_unified.py) — combined RHS (WIKI-T-028)
  - DGRReinitializer       (reinit_dgr.py)      — direct geometric (WIKI-T-030)
  - HybridReinitializer    (reinit_dgr.py)      — split + DGR composition
  - EikonalReinitializer   (reinit_eikonal.py)  — unified Eikonal + local-ε (WIKI-T-031)

ReinitializerWENO5 is legacy (C2 — DO NOT DELETE).
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

from .interfaces import IReinitializer
from .advection import _weno5_pos, _weno5_neg, _pad_bc
from .heaviside import apply_mass_correction
from .reinit_ops import volume_monitor as _volume_monitor

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


_EPS_D_COMP = 0.05  # Dissipative CCD filter strength ε_d (§5 eq:eps_adv)


class Reinitializer(IReinitializer):
    """Reinitialize ψ — facade delegating to strategy classes.

    Parameters
    ----------
    backend, grid, ccd, eps, n_steps, bc, unified_dccd, mass_correction,
    eps_d_comp, method
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero',
                 unified_dccd: bool = False,
                 mass_correction: bool = True,
                 eps_d_comp: float = _EPS_D_COMP,
                 method: str = 'split',
                 phi_smooth_C: float = 1e-4,
                 eps_scale: float = 1.0,
                 sigma_0: float = 3.0):
        self.xp = backend.xp
        self.grid = grid
        self.eps = eps

        # Canonical method dispatch: unified_dccd=True → method='unified'
        if unified_dccd and method == 'split':
            method = 'unified'
        self._method = method

        # Build the appropriate strategy
        common = dict(
            backend=backend, grid=grid, ccd=ccd, eps=eps,
            n_steps=n_steps, bc=bc, eps_d_comp=eps_d_comp,
            mass_correction=mass_correction,
        )

        if method == 'split':
            from .reinit_split import SplitReinitializer
            self._strategy = SplitReinitializer(**common)
        elif method == 'unified':
            from .reinit_unified import UnifiedDCCDReinitializer
            self._strategy = UnifiedDCCDReinitializer(**common)
        elif method == 'dgr':
            from .reinit_dgr import DGRReinitializer
            self._strategy = DGRReinitializer(
                backend=backend, grid=grid, ccd=ccd, eps=eps,
                phi_smooth_C=phi_smooth_C,
            )
        elif method == 'hybrid':
            from .reinit_split import SplitReinitializer
            from .reinit_dgr import DGRReinitializer, HybridReinitializer
            split = SplitReinitializer(**common)
            dgr = DGRReinitializer(
                backend=backend, grid=grid, ccd=ccd, eps=eps,
                phi_smooth_C=phi_smooth_C,
            )
            self._strategy = HybridReinitializer(split, dgr)
        elif method == 'eikonal':
            from .reinit_eikonal import EikonalReinitializer
            self._strategy = EikonalReinitializer(
                backend=backend, grid=grid, ccd=ccd, eps=eps,
                n_iter=n_steps, mass_correction=mass_correction, zsp=True,
                eps_scale=eps_scale,
            )
        elif method == 'eikonal_xi':
            from .reinit_eikonal import EikonalReinitializer
            self._strategy = EikonalReinitializer(
                backend=backend, grid=grid, ccd=ccd, eps=eps,
                n_iter=n_steps, mass_correction=mass_correction,
                zsp=False, xi_sdf=True, eps_scale=eps_scale,
            )
        elif method == 'eikonal_fmm':
            from .reinit_eikonal import EikonalReinitializer
            self._strategy = EikonalReinitializer(
                backend=backend, grid=grid, ccd=ccd, eps=eps,
                n_iter=n_steps, mass_correction=mass_correction,
                zsp=False, xi_sdf=False, fmm=True, eps_scale=eps_scale,
            )
        elif method == 'ridge_eikonal':
            # CHK-159 SP-E: Ridge-Eikonal hybrid on non-uniform grids.
            from .ridge_eikonal import RidgeEikonalReinitializer
            self._strategy = RidgeEikonalReinitializer(
                backend=backend, grid=grid, ccd=ccd, eps=eps,
                sigma_0=sigma_0,
                eps_scale=max(eps_scale, 1.4),
                mass_correction=mass_correction,
            )
        else:
            raise ValueError(f"Unknown reinit method: {method!r}")

    def reinitialize(self, psi):
        """Delegate to the selected strategy."""
        return self._strategy.reinitialize(psi)

    def volume_monitor(self, psi) -> float:
        """M(τ) = ∫ ψ(1−ψ) dV — decreases during reinitialization."""
        return _volume_monitor(self.xp, psi, self.grid)


# ── Legacy WENO5 implementation (retained for comparison / validation) ────────
#
# Prior implementation used WENO5 flux splitting + TVD-RK3 for BOTH compression
# and diffusion terms (combined RHS).  Replaced by operator-split Dissipative CCD
# + CN scheme (Reinitializer above) to match the paper (§5c).
# DO NOT DELETE — preserved for cross-validation benchmarks.


class ReinitializerWENO5(IReinitializer):
    """Reinitialize ψ via WENO5 compression + CCD diffusion, TVD-RK3 time march.

    Legacy implementation — kept for comparison against the Dissipative CCD + CN
    scheme (``Reinitializer``).  API is identical.
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero'):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.n_steps = n_steps
        self._bc = bc
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]

        _TVD_RK3_SAFETY = 0.5
        ndim = grid.ndim
        dx_min = min(float(grid.L[ax] / grid.N[ax]) for ax in range(ndim))
        dtau_para = _TVD_RK3_SAFETY * dx_min**2 / (2.0 * ndim * eps)
        dtau_hyp  = 0.5 * dx_min
        self.dtau = min(dtau_para, dtau_hyp)

    def reinitialize(self, psi) -> "array":
        xp = self.xp
        q = xp.copy(psi)
        dtau = self.dtau
        ccd = self.ccd
        for _ in range(self.n_steps):
            r0 = self._rhs(q, ccd)
            q1 = xp.clip(q + dtau * r0, 0.0, 1.0)
            r1 = self._rhs(q1, ccd)
            q2 = xp.clip(0.75 * q + 0.25 * (q1 + dtau * r1), 0.0, 1.0)
            r2 = self._rhs(q2, ccd)
            q = xp.clip((1.0 / 3.0) * q + (2.0 / 3.0) * (q2 + dtau * r2), 0.0, 1.0)
        return q

    def _rhs(self, psi, ccd: "CCDSolver"):
        xp = self.xp
        ndim = self.grid.ndim
        eps = self.eps
        dpsi = []
        d2psi_sum = xp.zeros_like(psi)
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(psi, ax)
            dpsi.append(g1)
            d2psi_sum += g2
        grad_psi_sq = sum(g * g for g in dpsi)
        safe_grad   = xp.maximum(xp.sqrt(xp.maximum(grad_psi_sq, 1e-28)), 1e-14)
        n_hat = [g / safe_grad for g in dpsi]
        psi_1mpsi = psi * (1.0 - psi)
        alpha = float(xp.max(xp.abs(psi_1mpsi)))
        alpha = max(alpha, 1e-14)
        div_compression = xp.zeros_like(psi)
        for ax in range(ndim):
            F_ax = psi_1mpsi * n_hat[ax]
            div_ax = self._weno5_compression_div(psi, F_ax, alpha, ax)
            div_compression += div_ax
        return -div_compression + eps * d2psi_sum

    def _weno5_compression_div(self, psi, F, alpha: float, axis: int):
        xp = self.xp
        n = psi.shape[axis]
        psi_p = _pad_bc(xp, psi, axis, 3, self._bc)
        F_p   = _pad_bc(xp, F,   axis, 3, self._bc)

        def sl(start, stop):
            s = [slice(None)] * psi.ndim
            s[axis] = slice(start, stop if stop != 0 else None)
            return tuple(s)

        i_max = n - 1
        fp_m2 = F_p[sl(1, 1+i_max)]; fp_m1 = F_p[sl(2, 2+i_max)]
        fp_0  = F_p[sl(3, 3+i_max)]; fp_p1 = F_p[sl(4, 4+i_max)]; fp_p2 = F_p[sl(5, 5+i_max)]
        pp_m2 = psi_p[sl(1,1+i_max)]; pp_m1 = psi_p[sl(2,2+i_max)]
        pp_0  = psi_p[sl(3,3+i_max)]; pp_p1 = psi_p[sl(4,4+i_max)]; pp_p2 = psi_p[sl(5,5+i_max)]
        Fplus_m2 = 0.5*(fp_m2+alpha*pp_m2); Fplus_m1 = 0.5*(fp_m1+alpha*pp_m1)
        Fplus_0  = 0.5*(fp_0 +alpha*pp_0 ); Fplus_p1 = 0.5*(fp_p1+alpha*pp_p1)
        Fplus_p2 = 0.5*(fp_p2+alpha*pp_p2)
        Fp_face  = _weno5_pos(xp, Fplus_m2, Fplus_m1, Fplus_0, Fplus_p1, Fplus_p2)

        fm_m1 = F_p[sl(2,2+i_max)]; fm_0  = F_p[sl(3,3+i_max)]; fm_p1 = F_p[sl(4,4+i_max)]
        fm_p2 = F_p[sl(5,5+i_max)]; fm_p3 = F_p[sl(6,6+i_max)]
        pm_m1 = psi_p[sl(2,2+i_max)]; pm_0  = psi_p[sl(3,3+i_max)]; pm_p1 = psi_p[sl(4,4+i_max)]
        pm_p2 = psi_p[sl(5,5+i_max)]; pm_p3 = psi_p[sl(6,6+i_max)]
        Fminus_m1 = 0.5*(fm_m1-alpha*pm_m1); Fminus_0  = 0.5*(fm_0 -alpha*pm_0 )
        Fminus_p1 = 0.5*(fm_p1-alpha*pm_p1); Fminus_p2 = 0.5*(fm_p2-alpha*pm_p2)
        Fminus_p3 = 0.5*(fm_p3-alpha*pm_p3)
        Fm_face   = _weno5_neg(xp, Fminus_m1, Fminus_0, Fminus_p1, Fminus_p2, Fminus_p3)

        flux_face = Fp_face + Fm_face
        h = self._h[axis]
        sl_hi = [slice(None)] * psi.ndim; sl_hi[axis] = slice(1, None)
        sl_lo = [slice(None)] * psi.ndim; sl_lo[axis] = slice(0, -1)
        div_interior = (flux_face[tuple(sl_hi)] - flux_face[tuple(sl_lo)]) / h
        shape_pad = list(psi.shape); shape_pad[axis] = 1
        pad = xp.zeros(shape_pad)
        return xp.concatenate([pad, div_interior, pad], axis=axis)

    def volume_monitor(self, psi) -> float:
        dV = self.grid.cell_volumes()
        return float(self.xp.sum(psi * (1.0 - psi) * dV))
