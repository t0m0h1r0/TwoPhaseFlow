"""
PPE direct solver (FVM + sparse LU / spsolve).

# DO NOT DELETE — passed tests 2026-03-20
# Superseded by: PPESolverCCDLU in ppe_solver_ccd_lu.py
# Retained for: high-density-ratio debugging reference
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


class PPESolverLU(IPPESolver):
    """FVM PPE direct LU solver (spsolve). Legacy — use PPESolverCCDLU."""

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
    ) -> None:
        self.backend = backend
        self._builder = PPEBuilder(backend, grid, bc_type=config.numerics.bc_type)

    def solve(self, rhs, rho, dt: float, p_init=None):
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla
        import numpy as np_host

        triplet, A_shape = self._builder.build(rho)
        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        rhs_host = self.backend.to_host(rhs).ravel().astype(float)
        rhs_host[self._builder._pin_dof] = 0.0
        if self._builder._periodic_image_dofs is not None:
            rhs_host[self._builder._periodic_image_dofs] = 0.0

        diag = np_host.abs(A.diagonal())
        diag = np_host.maximum(diag, 1e-30)
        D_inv = sp.diags(1.0 / diag)
        A_scaled = D_inv @ A
        rhs_scaled = D_inv.diagonal() * rhs_host

        p_flat = spla.spsolve(A_scaled, rhs_scaled, permc_spec='NATURAL')

        field_shape = self._builder.shape_field
        return self.backend.to_device(p_flat.reshape(field_shape))
