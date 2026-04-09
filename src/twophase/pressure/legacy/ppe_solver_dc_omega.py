"""
DC-Omega sweep PPE solver: Thomas ADI with under-relaxation.

# DO NOT DELETE — passed tests 2026-04-05
# Superseded by: PPESolverCCDLU (Kronecker LU direct solve)
# Retained for: cross-validation and regression baseline
# Registered: docs/01_PROJECT_MAP.md §8
"""

from __future__ import annotations

import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...backend import Backend
    from ...config import SimulationConfig
    from ...core.grid import Grid
    from ...ccd.ccd_solver import CCDSolver
    from ...core.boundary import BoundarySpec

from ...interfaces.ppe_solver import IPPESolver


class PPESolverDCOmega(IPPESolver):
    """Thomas ADI DC sweep with under-relaxation omega in (0, 1]."""

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        omega: float = 0.5,
        ccd: "CCDSolver | None" = None,
        bc_spec: "BoundarySpec | None" = None,
    ) -> None:
        if not (0.0 < omega <= 1.0):
            raise ValueError(f"omega must be in (0, 1], got {omega}")

        self.xp = backend.xp
        self.backend = backend
        self.grid = grid
        self.omega = omega
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter
        self.c_tau = config.solver.pseudo_c_tau

        if ccd is not None:
            self.ccd = ccd
        else:
            from ...ccd.ccd_solver import CCDSolver as _CCD
            self.ccd = _CCD(grid, backend)

        if bc_spec is not None:
            self._bc_spec = bc_spec
        else:
            from ...core.boundary import BoundarySpec as _BS
            self._bc_spec = _BS(
                bc_type=config.numerics.bc_type,
                shape=grid.shape,
                N=grid.N,
            )

        self._h_min = min(
            grid.L[ax] / grid.N[ax] for ax in range(grid.ndim)
        )

    def solve(self, rhs, rho, dt: float, p_init=None):
        shape = self.grid.shape

        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float)

        from ..ccd_ppe_utils import (
            precompute_density_gradients, compute_ccd_laplacian,
            compute_lts_dtau, check_convergence,
        )
        from ..thomas_sweep import thomas_sweep_1d

        dtau = compute_lts_dtau(rho_np, self.c_tau, self._h_min)

        p = (
            np.zeros(shape, dtype=float)
            if p_init is None
            else np.asarray(self.backend.to_host(p_init), dtype=float)
        )

        drho = precompute_density_gradients(rho_np, self.ccd, self.backend)
        pin_dof = self._bc_spec.pin_dof

        converged = False
        residual = float("nan")
        for _ in range(self.maxiter):
            Lp = compute_ccd_laplacian(p, rho_np, drho, self.ccd, self.backend)
            R = rhs_np - Lp

            residual, converged = check_convergence(R, pin_dof, self.tol)
            if converged:
                break

            q  = thomas_sweep_1d(R, rho_np, drho[0], dtau, axis=0, grid=self.grid)
            q.ravel()[pin_dof] = 0.0
            dp = thomas_sweep_1d(q, rho_np, drho[1], dtau, axis=1, grid=self.grid)
            dp.ravel()[pin_dof] = 0.0

            p = p - self.omega * dp
            p.ravel()[pin_dof] = 0.0

        if not converged:
            warnings.warn(
                f"PPESolverDCOmega(omega={self.omega}): did not converge in "
                f"{self.maxiter} iterations (final residual {residual:.3e}, "
                f"tol={self.tol:.3e}).",
                RuntimeWarning,
                stacklevel=2,
            )

        if not np.isfinite(p).all():
            warnings.warn(
                "PPESolverDCOmega: non-finite values detected.",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.xp.asarray(p)
