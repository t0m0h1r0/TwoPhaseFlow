"""Dissipative-CCD CLS advection strategy."""

from __future__ import annotations

from typing import List, TYPE_CHECKING

from .interfaces import ILevelSetAdvection
from ..core.boundary import boundary_axes
from ..time_integration.tvd_rk3 import tvd_rk3
from .heaviside import apply_mass_correction
from .advection_kernels import _EPS_D_ADV, _dccd_filter_stencil, _pad_bc

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver
    from ..simulation.scheme_build_ctx import AdvectionBuildCtx


class DissipativeCCDAdvection(ILevelSetAdvection):
    """Advects ψ using Dissipative CCD + TVD-RK3.

    Scope: this class implements DCCD strictly for level-set / volume-fraction
    advection (transport of an advected scalar). The DCCD 3-point filter must
    NOT be applied to the pressure field (∇p): see Chapter 12 U9 negation test
    (`paper/sections/12u9_dccd_pressure_prohibition.tex`). PPE / momentum
    corrector paths use plain CCD; this is enforced by call-site separation
    (only this class invokes ``_dccd_filter_stencil`` in the production
    pipeline).
    """

    scheme_names = ("dissipative_ccd",)
    _scheme_aliases = {"dccd": "dissipative_ccd"}

    @classmethod
    def _build(cls, name: str, ctx: "AdvectionBuildCtx") -> "DissipativeCCDAdvection":
        ls_bc = tuple(
            "periodic" if axis == "periodic" else "neumann"
            for axis in boundary_axes(ctx.ccd.bc_type, ctx.grid.ndim)
        )
        return cls(ctx.backend, ctx.grid, ctx.ccd, bc=ls_bc)

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        ccd: "CCDSolver",
        bc: str | tuple[str, ...] = 'periodic',
        eps_d: float = _EPS_D_ADV,
        mass_correction: bool = False,
    ):
        xp = backend.xp
        self.xp = xp
        self._grid = grid
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]
        self._ccd = ccd
        self._bc = (
            tuple(str(value).strip().lower() for value in bc)
            if isinstance(bc, (tuple, list))
            else str(bc).strip().lower()
        )
        self._eps_d = float(eps_d)
        self._mass_correction = mass_correction

        self._dV = grid.cell_volumes() if mass_correction else None
        if not grid.uniform:
            self._J_reshaped = []
            for ax in range(grid.ndim):
                shape = [1] * grid.ndim
                shape[ax] = -1
                self._J_reshaped.append(xp.asarray(grid.J[ax]).reshape(shape))
        else:
            self._J_reshaped = None

    def _axis_bc(self, axis: int) -> str:
        return self._bc[axis] if isinstance(self._bc, tuple) else self._bc

    def advance(self, psi, velocity_components: List, dt: float, clip_bounds=(0.0, 1.0)):
        xp = self.xp
        psi = xp.asarray(psi)
        velocity_components = [xp.asarray(vc) for vc in velocity_components]

        if self._mass_correction:
            M_old = xp.sum(psi * self._dV)

        if clip_bounds is None:
            post_stage = None
        else:
            lo, hi = clip_bounds
            post_stage = lambda q: xp.clip(q, lo, hi)
        q_new = tvd_rk3(
            xp, psi, dt,
            lambda q: self._rhs(q, velocity_components),
            post_stage=post_stage,
        )

        if self._mass_correction:
            q_new = apply_mass_correction(xp, q_new, self._dV, M_old)

        return q_new

    def _rhs(self, psi, vel):
        xp = self.xp
        ndim = len(vel)
        result = xp.zeros_like(psi)

        for ax in range(ndim):
            f = psi * vel[ax]
            n = f.shape[ax]

            def _sl(start, stop, _ax=ax):
                s = [slice(None)] * f.ndim
                s[_ax] = slice(start, stop)
                return tuple(s)

            if self._grid.uniform:
                fp, _ = self._ccd.differentiate(f, axis=ax)
                fp_pad = _pad_bc(xp, fp, ax, 1, self._axis_bc(ax))
                fp_p1 = fp_pad[_sl(2, n + 2)]
                fp_m1 = fp_pad[_sl(0, n)]
                F_tilde = _dccd_filter_stencil(fp, fp_p1, fp_m1, self._eps_d)
            else:
                fp_xi, _ = self._ccd.differentiate(f, axis=ax, apply_metric=False)
                fp_x = self._J_reshaped[ax] * fp_xi
                fp_x_pad = _pad_bc(xp, fp_x, ax, 1, self._axis_bc(ax))
                fp_x_p1 = fp_x_pad[_sl(2, n + 2)]
                fp_x_m1 = fp_x_pad[_sl(0, n)]
                F_tilde = _dccd_filter_stencil(fp_x, fp_x_p1, fp_x_m1, self._eps_d)

            result -= F_tilde

        return result
