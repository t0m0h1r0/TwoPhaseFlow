"""Concrete pressure-gradient operators.

Symbol mapping
--------------
∇p -> ``gradient(p, axis)``
∂p/∂x_i -> ``dp_daxis``
Δx_face -> ``_d_face_grad``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.boundary import is_wall_axis
from .gradient_operator import IGradientOperator

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ccd.fccd import FCCDSolver
    from ..core.grid import Grid
    from .scheme_build_ctx import GradientBuildCtx


class CCDGradientOperator(IGradientOperator):
    """6th-order CCD gradient: ∂p/∂x via compact differentiation.

    Applies Neumann boundary conditions on walls.
    Used on uniform or locally-refined grids when CCD accuracy is prioritized.
    """

    scheme_names = ("ccd", "projection_consistent")

    @classmethod
    def _build(cls, name: str, ctx: "GradientBuildCtx") -> "CCDGradientOperator":
        return ctx.ccd_op  # type: ignore[return-value]

    def __init__(self, backend: "Backend", ccd: "CCDSolver", bc_type: str = "wall") -> None:
        self.xp = backend.xp
        self._ccd = ccd
        self.bc_type = bc_type

    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute ∂p/∂x_axis via CCD with wall Neumann BC if needed."""
        dp_daxis = self._ccd.first_derivative(p, axis)
        if is_wall_axis(self.bc_type, axis, self._ccd.ndim):
            self._ccd.enforce_wall_neumann(dp_daxis, axis)
        return dp_daxis


class FCCDGradientOperator(IGradientOperator):
    """FCCD gradient shared by pressure correction and surface tension force."""

    scheme_names = ("fccd_flux", "fccd_nodal")
    _scheme_aliases = {"fccd": "fccd_flux"}

    @classmethod
    def _build(cls, name: str, ctx: "GradientBuildCtx") -> "FCCDGradientOperator":
        return cls(ctx.fccd)

    def __init__(self, fccd: "FCCDSolver") -> None:
        self._fccd = fccd

    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute nodal gradient via FCCD face gradient + R4 reconstruction."""
        return self._fccd.node_gradient(p, axis)


class FVMGradientOperator(IGradientOperator):
    """Face-average FVM gradient for non-uniform grids."""

    def __init__(self, backend: "Backend", grid: "Grid") -> None:
        self.xp = backend.xp
        self._grid = grid
        self._d_face_grad = None

    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute ∂p/∂x_axis via FVM face-averaging."""
        if self._d_face_grad is None:
            self._init_face_spacing()

        d = self._d_face_grad[axis]
        n_cells = self._grid.N[axis]
        ndim = self._grid.ndim

        def sl(start, stop):
            s = [slice(None)] * ndim
            s[axis] = slice(start, stop)
            return tuple(s)

        p_shifted_right = p[sl(1, n_cells + 1)]
        p_shifted_left = p[sl(0, n_cells)]
        g_face = (p_shifted_right - p_shifted_left) / d

        g = self.xp.zeros_like(p)
        g[sl(1, n_cells)] = 0.5 * (g_face[sl(0, n_cells - 1)] + g_face[sl(1, n_cells)])
        return g

    def _init_face_spacing(self) -> None:
        """Compute and cache face spacing Δx_face for all axes."""
        import numpy as _np

        self._d_face_grad = []
        for axis in range(self._grid.ndim):
            d = _np.diff(_np.asarray(self._grid.coords[axis]))
            shape = [1] * self._grid.ndim
            shape[axis] = -1
            self._d_face_grad.append(self.xp.asarray(d.reshape(shape)))
