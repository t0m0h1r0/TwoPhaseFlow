"""Factorized low-order FD correction solver for defect correction.

Paper mapping
-------------
In Eq. ``eq:dc_three_step``, this class supplies the low-order correction
operator ``L_L``.  It solves the same second-order conservative FD flux form as
the legacy sparse low-order PPE path, but factors the pinned matrix once per
outer defect-correction solve and reuses that factor for all correction RHSs.

Symbol mapping
--------------
``rhs`` → defect ``d^{(k)}``; ``rho`` → low-order density coefficient field;
``prepare_operator`` → factorize ``L_L``; ``solve`` → apply ``L_L^{-1}``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .interfaces import IPPESolver
from .ppe_builder import PPEBuilder

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.boundary import BoundarySpec
    from ..core.grid import Grid
    from ..simulation.scheme_build_ctx import PPEBuildCtx


class PPESolverFDDirect(IPPESolver):
    """Pinned low-order FD direct solve with per-DC factor reuse."""

    scheme_names = ("fd_direct",)
    _scheme_aliases = {"fd_spsolve": "fd_direct"}

    @classmethod
    def _build(cls, name: str, ctx: "PPEBuildCtx") -> "PPESolverFDDirect":
        return cls(ctx.backend, ctx.grid, bc_type=ctx.bc_type, bc_spec=ctx.bc_spec)

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        bc_type: str = "wall",
        bc_spec: "BoundarySpec | None" = None,
    ):
        self.backend = backend
        self.xp = backend.xp
        self.bc_type = bc_type
        self.bc_spec = bc_spec
        self.ppb = PPEBuilder(backend, grid, bc_type, bc_spec)
        self._refresh_structure(grid)
        self._factor = None

    def _refresh_structure(self, grid: "Grid") -> None:
        dummy_rho = np.ones(grid.shape, dtype=np.float64)
        triplet, shape = self.ppb.build(dummy_rho)
        self._rows = triplet[1]
        self._cols = triplet[2]
        self._shape = shape

    def update_grid(self, grid: "Grid") -> None:
        self.ppb = PPEBuilder(self.backend, grid, self.bc_type, self.bc_spec)
        self._refresh_structure(grid)
        self._factor = None

    def invalidate_cache(self) -> None:
        self.ppb.invalidate_gpu_cache()
        self._factor = None

    def prepare_operator(self, rho) -> None:
        data = self.ppb.build_values(rho)
        if self.backend.is_gpu():
            matrix = self.backend.sparse.csc_matrix(
                (data, (self._rows, self._cols)),
                shape=self._shape,
            )
        else:
            import scipy.sparse as sp

            matrix = sp.csc_matrix(
                (data, (self._rows, self._cols)),
                shape=self._shape,
            )
        self._factor = self.backend.sparse_linalg.splu(matrix)

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        if self._factor is None:
            self.prepare_operator(rho)
        rhs_vec = self.xp.asarray(rhs).ravel().copy()
        rhs_vec[self.ppb._pin_dof] = 0.0
        pressure_vec = self._factor.solve(rhs_vec)
        self.last_diagnostics = {"ppe_fd_direct_factor_reuse": 1.0}
        return self.xp.asarray(pressure_vec).reshape(self.ppb.shape_field)
