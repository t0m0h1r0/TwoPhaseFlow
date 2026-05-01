"""WENO5-based CLS advection strategy."""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from .interfaces import ILevelSetAdvection
from ..core.boundary import boundary_axes
from ..time_integration.tvd_rk3 import tvd_rk3
from .advection_kernels import _pad_bc, _weno5_neg, _weno5_pos

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..simulation.scheme_build_ctx import AdvectionBuildCtx


class LevelSetAdvection(ILevelSetAdvection):
    """Advects ψ using WENO5 + TVD-RK3."""

    scheme_names = ("weno5",)
    _scheme_aliases = {"weno": "weno5"}

    @classmethod
    def _build(cls, name: str, ctx: "AdvectionBuildCtx") -> "LevelSetAdvection":
        ls_bc = tuple(
            "periodic" if axis == "periodic" else "neumann"
            for axis in boundary_axes(ctx.bc_type, ctx.grid.ndim)
        )
        return cls(ctx.backend, ctx.grid, bc=ls_bc)

    def __init__(self, backend: "Backend", grid: "Grid", bc: str | tuple[str, ...] = 'zero'):
        self.xp = backend.xp
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]
        self._bc = (
            tuple(str(value).strip().lower() for value in bc)
            if isinstance(bc, (tuple, list))
            else str(bc).strip().lower()
        )

    def _axis_bc(self, axis: int) -> str:
        return self._bc[axis] if isinstance(self._bc, tuple) else self._bc

    def advance(self, psi, velocity_components: List, dt: float, clip_bounds=(0.0, 1.0)):
        xp = self.xp
        q_new = tvd_rk3(xp, psi, dt, lambda q: self._rhs(q, velocity_components))
        if clip_bounds is None:
            return q_new
        lo, hi = clip_bounds
        return xp.clip(q_new, lo, hi)

    def _rhs(self, psi, vel):
        xp = self.xp
        ndim = len(vel)
        result = xp.zeros_like(psi)

        alpha_global = float(max(
            xp.max(xp.abs(vel[ax])) for ax in range(ndim)
        ))
        alpha_global = max(alpha_global, 1e-14)

        for ax in range(ndim):
            h = self._h[ax]
            div_f = self._weno5_divergence(psi, vel[ax], ax, alpha_global, h)
            result -= div_f

        return result

    def _weno5_divergence(self, psi, u, axis: int, alpha: float, h: float):
        xp = self.xp
        n = psi.shape[axis]
        F = u * psi
        axis_bc = self._axis_bc(axis)
        psi_p = _pad_bc(xp, psi, axis, 3, axis_bc)
        F_p = _pad_bc(xp, F, axis, 3, axis_bc)

        def sl_ax(start, stop):
            s = [slice(None)] * psi.ndim
            s[axis] = slice(start, stop if stop != 0 else None)
            return tuple(s)

        i_max = n - 1
        fp_m2 = F_p[sl_ax(1, 1 + i_max)]
        fp_m1 = F_p[sl_ax(2, 2 + i_max)]
        fp_0 = F_p[sl_ax(3, 3 + i_max)]
        fp_p1 = F_p[sl_ax(4, 4 + i_max)]
        fp_p2 = F_p[sl_ax(5, 5 + i_max)]

        pp_m2 = psi_p[sl_ax(1, 1 + i_max)]
        pp_m1 = psi_p[sl_ax(2, 2 + i_max)]
        pp_0 = psi_p[sl_ax(3, 3 + i_max)]
        pp_p1 = psi_p[sl_ax(4, 4 + i_max)]
        pp_p2 = psi_p[sl_ax(5, 5 + i_max)]

        Fplus_m2 = 0.5 * (fp_m2 + alpha * pp_m2)
        Fplus_m1 = 0.5 * (fp_m1 + alpha * pp_m1)
        Fplus_0 = 0.5 * (fp_0 + alpha * pp_0)
        Fplus_p1 = 0.5 * (fp_p1 + alpha * pp_p1)
        Fplus_p2 = 0.5 * (fp_p2 + alpha * pp_p2)
        Fp_face = _weno5_pos(Fplus_m2, Fplus_m1, Fplus_0, Fplus_p1, Fplus_p2)

        fm_m1 = F_p[sl_ax(2, 2 + i_max)]
        fm_0 = F_p[sl_ax(3, 3 + i_max)]
        fm_p1 = F_p[sl_ax(4, 4 + i_max)]
        fm_p2 = F_p[sl_ax(5, 5 + i_max)]
        fm_p3 = F_p[sl_ax(6, 6 + i_max)]

        pm_m1 = psi_p[sl_ax(2, 2 + i_max)]
        pm_0 = psi_p[sl_ax(3, 3 + i_max)]
        pm_p1 = psi_p[sl_ax(4, 4 + i_max)]
        pm_p2 = psi_p[sl_ax(5, 5 + i_max)]
        pm_p3 = psi_p[sl_ax(6, 6 + i_max)]

        Fminus_m1 = 0.5 * (fm_m1 - alpha * pm_m1)
        Fminus_0 = 0.5 * (fm_0 - alpha * pm_0)
        Fminus_p1 = 0.5 * (fm_p1 - alpha * pm_p1)
        Fminus_p2 = 0.5 * (fm_p2 - alpha * pm_p2)
        Fminus_p3 = 0.5 * (fm_p3 - alpha * pm_p3)
        Fm_face = _weno5_neg(Fminus_m1, Fminus_0, Fminus_p1, Fminus_p2, Fminus_p3)

        flux_face = Fp_face + Fm_face

        sl_hi = [slice(None)] * psi.ndim
        sl_lo = [slice(None)] * psi.ndim
        sl_hi[axis] = slice(1, None)
        sl_lo[axis] = slice(0, -1)
        div_interior = (flux_face[tuple(sl_hi)] - flux_face[tuple(sl_lo)]) / h

        if axis_bc == 'periodic':
            sl_f0 = [slice(None)] * psi.ndim
            sl_fN = [slice(None)] * psi.ndim
            sl_f0[axis] = slice(0, 1)
            sl_fN[axis] = slice(-1, None)
            div_wrap = (flux_face[tuple(sl_f0)] - flux_face[tuple(sl_fN)]) / h
            return xp.concatenate([div_wrap, div_interior, div_wrap], axis=axis)

        shape_pad = list(psi.shape)
        shape_pad[axis] = 1
        pad = xp.zeros(shape_pad)
        return xp.concatenate([pad, div_interior, pad], axis=axis)
