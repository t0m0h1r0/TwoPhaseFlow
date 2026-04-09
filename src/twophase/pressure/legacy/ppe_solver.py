"""
PPE linear solver (BiCGSTAB, FVM).

# DO NOT DELETE — passed tests 2026-03-20
# Superseded by: PPESolverCCDLU in ppe_solver_ccd_lu.py
# Retained for: reference FVM implementation
# Violation: PR-1 (FVM O(h^2), FD forbidden in solver core)
# Registered: docs/01_PROJECT_MAP.md §8
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...backend import Backend
    from ...config import SimulationConfig
    from ...core.grid import Grid

from ...interfaces.ppe_solver import IPPESolver
from ..ppe_builder import PPEBuilder

_FILL_PERIODIC = 10
_FILL_WALL     = 1


class PPESolver(IPPESolver):
    """FVM sparse PPE solver (BiCGSTAB). Legacy — use PPESolverCCDLU."""

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
    ):
        self.backend = backend
        self.xp = backend.xp
        self.tol = config.solver.bicgstab_tol
        self.maxiter = config.solver.bicgstab_maxiter
        bc_type = config.numerics.bc_type
        self._builder = PPEBuilder(backend, grid, bc_type=bc_type)

    def solve(self, rhs, rho, dt: float, p_init=None):
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla
        import numpy as np_host

        triplet, A_shape = self._builder.build(rho)
        n_dof = self._builder.n_dof
        field_shape = self._builder.shape_field

        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        rhs_host = self.backend.to_host(rhs).ravel().astype(float)
        rhs_host[self._builder._pin_dof] = 0.0
        if self._builder._periodic_image_dofs is not None:
            rhs_host[self._builder._periodic_image_dofs] = 0.0

        x0 = None
        if p_init is not None:
            x0 = self.backend.to_host(p_init).ravel().astype(float)

        fill = _FILL_PERIODIC if self._builder.bc_type == 'periodic' else _FILL_WALL
        try:
            ilu = spla.spilu(A.tocsc(), fill_factor=fill)
            M = spla.LinearOperator(A_shape, ilu.solve)
        except Exception:
            M = None

        p_flat, info = spla.bicgstab(
            A, rhs_host,
            x0=x0,
            M=M,
            rtol=self.tol,
            maxiter=self.maxiter,
        )

        if info != 0:
            import warnings
            warnings.warn(
                f"PPE BiCGSTAB did not converge (info={info}).",
                RuntimeWarning,
                stacklevel=2,
            )

        p_arr = np_host.reshape(p_flat, field_shape)
        return self.backend.to_device(p_arr)
