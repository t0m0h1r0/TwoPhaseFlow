"""Generic defect-correction wrapper for pressure Poisson solvers.

Symbol mapping:
    p        -> pressure correction field
    rhs      -> PPE right-hand side
    L(p)     -> discrete projection operator
    residual -> rhs - L(p)

A3 chain:
    §9 variable-density PPE
      -> defect correction on the selected discrete operator
      -> IPPESolver.prepare_operator/apply contract
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .interfaces import IPPESolver

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


class PPESolverDefectCorrection(IPPESolver):
    """Outer residual-correction loop for a matrix-free PPE operator."""

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        base_solver: IPPESolver,
        operator: IPPESolver,
        *,
        max_corrections: int = 3,
        tolerance: float = 1.0e-8,
        relaxation: float = 1.0,
    ) -> None:
        if max_corrections <= 0:
            raise ValueError("max_corrections must be > 0")
        if tolerance <= 0.0:
            raise ValueError("tolerance must be > 0")
        if relaxation <= 0.0:
            raise ValueError("relaxation must be > 0")
        if not hasattr(operator, "prepare_operator") or not hasattr(operator, "apply"):
            raise TypeError("operator must provide prepare_operator(rho) and apply(p)")
        self.backend = backend
        self.xp = backend.xp
        self.grid = grid
        self.base_solver = base_solver
        self.operator = operator
        self.max_corrections = int(max_corrections)
        self.tolerance = float(tolerance)
        self.relaxation = float(relaxation)
        self._pin_dof = operator._pin_dof

    def update_grid(self, grid: "Grid | None" = None) -> None:
        """Refresh both the target operator and the configured base solver."""
        if grid is not None:
            self.grid = grid
        self.base_solver.update_grid(self.grid)
        self.operator.update_grid(self.grid)
        self._pin_dof = self.operator._pin_dof

    def invalidate_cache(self) -> None:
        """Invalidate backend caches owned by the inner solver/operator."""
        self.base_solver.invalidate_cache()
        self.operator.invalidate_cache()

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        """Solve by base solve plus residual defect corrections."""
        xp = self.xp
        rhs_dev = xp.asarray(rhs)
        rhs_flat = rhs_dev.ravel().copy()
        rhs_flat[self._pin_dof] = 0.0
        pressure = xp.asarray(
            self.base_solver.solve(rhs_dev, rho, dt=dt, p_init=p_init)
        )
        pressure.ravel()[self._pin_dof] = 0.0

        self.operator.prepare_operator(rho)
        rhs_norm = float(self.backend.asnumpy(xp.linalg.norm(rhs_flat)))
        scale = max(rhs_norm, 1.0)
        for _ in range(self.max_corrections):
            residual = rhs_dev - self.operator.apply(pressure)
            residual.ravel()[self._pin_dof] = 0.0
            residual_norm = float(self.backend.asnumpy(xp.linalg.norm(residual.ravel())))
            if residual_norm <= self.tolerance * scale:
                break
            correction = xp.asarray(
                self.base_solver.solve(residual, rho, dt=dt, p_init=None)
            )
            correction.ravel()[self._pin_dof] = 0.0
            pressure = pressure + self.relaxation * correction
            pressure.ravel()[self._pin_dof] = 0.0
        return pressure
