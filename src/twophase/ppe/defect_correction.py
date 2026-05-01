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

from ..core.array_checks import all_arrays_exact_zero
from .interfaces import IPPESolver
from .fccd_matrixfree_helpers import fccd_interface_jump_is_active

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
        self._pin_dofs = getattr(operator, "_pin_dofs", (self._pin_dof,))
        if hasattr(self.base_solver, "_defer_interface_jump"):
            self.base_solver._defer_interface_jump = True
        if hasattr(self.operator, "_defer_interface_jump"):
            self.operator._defer_interface_jump = True
        if _can_collapse_same_operator(base_solver, operator):
            raise ValueError(
                "PPESolverDefectCorrection requires a distinct low-order base "
                "solver L_L; wrapping the same high-order operator would bypass "
                "the paper's defect-correction contract."
            )
        self._collapse_same_operator = False
        self.last_base_pressure = None
        self.last_diagnostics = {}
        self.last_residual_history: list[float] = []
        self.last_stalled: bool = False

    def update_grid(self, grid: "Grid | None" = None) -> None:
        """Refresh both the target operator and the configured base solver."""
        if grid is not None:
            self.grid = grid
        self.base_solver.update_grid(self.grid)
        self.operator.update_grid(self.grid)
        self._pin_dof = self.operator._pin_dof
        self._pin_dofs = getattr(self.operator, "_pin_dofs", (self._pin_dof,))
        self._collapse_same_operator = False

    def invalidate_cache(self) -> None:
        """Invalidate backend caches owned by the inner solver/operator."""
        self.base_solver.invalidate_cache()
        self.operator.invalidate_cache()

    def set_interface_jump_context(self, *, psi, kappa, sigma: float) -> None:
        """Forward SP-M pressure-jump context to wrapped PPE components."""
        for solver in (self.base_solver, self.operator):
            if hasattr(solver, "set_interface_jump_context"):
                solver.set_interface_jump_context(psi=psi, kappa=kappa, sigma=sigma)

    def clear_interface_jump_context(self) -> None:
        """Forward neutral-solve context clearing to wrapped PPE components."""
        for solver in (self.base_solver, self.operator):
            clearer = getattr(solver, "clear_interface_jump_context", None)
            if callable(clearer):
                clearer()

    def _subtract_interface_jump_operator(self, rhs_dev):
        """Apply jump decomposition for the wrapped operator residual solve."""
        operator = self.operator
        if not hasattr(operator, "apply_interface_jump") or not fccd_interface_jump_is_active(
            coefficient_scheme=getattr(operator, "coefficient_scheme", "none"),
            interface_coupling_scheme=getattr(operator, "interface_coupling_scheme", "none"),
            interface_jump_context=getattr(operator, "_interface_jump_context", None),
        ):
            return rhs_dev
        jump_pressure = operator.apply_interface_jump(self.xp.zeros_like(rhs_dev))
        return rhs_dev - self._apply_physical_operator(jump_pressure)

    def _add_affine_interface_jump_rhs(self, rhs_dev):
        """Apply affine jump contribution once for the wrapped operator solve."""
        operator = self.operator
        affine_rhs = getattr(operator, "_add_affine_interface_jump_rhs", None)
        if not callable(affine_rhs):
            return rhs_dev
        return affine_rhs(rhs_dev, force=True)

    def _apply_physical_operator(self, pressure):
        """Apply the physical PPE operator without gauge augmentation when exposed."""
        if hasattr(self.operator, "_apply_operator_core"):
            return self.operator._apply_operator_core(pressure)
        return self.operator.apply(pressure)

    def _uses_phase_mean_gauge(self) -> bool:
        checker = getattr(self.operator, "_uses_phase_mean_gauge", None)
        return bool(checker()) if callable(checker) else False

    def _enforce_pressure_gauge(self, pressure):
        """Apply the configured pressure nullspace gauge."""
        if self._uses_phase_mean_gauge() and hasattr(self.operator, "_project_phase_means"):
            return self.operator._project_phase_means(pressure)
        self._pin_flat(pressure.ravel(), 0.0)
        return pressure

    def _enforce_rhs_compatibility(self, rhs, *, record_stats: bool = True):
        """Apply the matching Neumann compatibility constraint to a RHS."""
        if self._uses_phase_mean_gauge() and hasattr(
            self.operator,
            "_project_rhs_compatibility",
        ):
            return self.operator._project_rhs_compatibility(
                rhs,
                record_stats=record_stats,
            )
        rhs_projected = rhs.copy()
        self._pin_flat(rhs_projected.ravel(), 0.0)
        return rhs_projected

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        """Solve by base solve plus residual defect corrections."""
        xp = self.xp
        rhs_dev = xp.asarray(rhs)
        self.operator.prepare_operator(rho)
        if hasattr(self.base_solver, "prepare_operator"):
            self.base_solver.prepare_operator(rho)
        rhs_dev = self._subtract_interface_jump_operator(rhs_dev)
        rhs_dev = self._add_affine_interface_jump_rhs(rhs_dev)
        rhs_dev = self._enforce_rhs_compatibility(rhs_dev)
        if self._collapse_same_operator:
            return self._solve_same_operator(rhs_dev, rho, dt=dt, p_init=p_init)
        pressure = xp.asarray(
            self.base_solver.solve(rhs_dev, rho, dt=dt, p_init=p_init)
        )
        pressure = self._enforce_pressure_gauge(pressure)
        initial_diagnostics = dict(getattr(self.operator, "last_diagnostics", {}))
        if not initial_diagnostics:
            initial_diagnostics = dict(
                getattr(self.base_solver, "last_diagnostics", {})
            )
        if (
            not self.backend.is_gpu()
            and all_arrays_exact_zero(xp, (rhs_dev, pressure))
        ):
            self.last_base_pressure = xp.copy(pressure)
            self.last_diagnostics = initial_diagnostics
            if hasattr(self.operator, "apply_interface_jump"):
                pressure = self.operator.apply_interface_jump(pressure)
            return pressure

        self._pin_dofs = getattr(self.operator, "_pin_dofs", (self._pin_dof,))
        rhs_flat = rhs_dev.ravel()
        rhs_norm = float(self.backend.asnumpy(xp.linalg.norm(rhs_flat)))
        scale = max(rhs_norm, 1.0)
        history: list[float] = []
        broke = False
        for _ in range(self.max_corrections):
            residual = rhs_dev - self.operator.apply(pressure)
            residual = self._enforce_rhs_compatibility(residual, record_stats=False)
            residual_norm = float(self.backend.asnumpy(xp.linalg.norm(residual.ravel())))
            history.append(residual_norm)
            if residual_norm <= self.tolerance * scale:
                broke = True
                break
            correction = xp.asarray(
                self.base_solver.solve(residual, rho, dt=dt, p_init=None)
            )
            correction = self._enforce_pressure_gauge(correction)
            pressure = pressure + self.relaxation * correction
            pressure = self._enforce_pressure_gauge(pressure)
        self.last_residual_history = history
        self.last_stalled = not broke
        self.last_base_pressure = xp.copy(pressure)
        self.last_diagnostics = initial_diagnostics
        if hasattr(self.operator, "apply_interface_jump"):
            pressure = self.operator.apply_interface_jump(pressure)
        return pressure

    def _solve_same_operator(self, rhs_dev, rho, *, dt: float, p_init=None):
        """Collapse redundant DC when base and target are the same operator."""
        original_tol = getattr(self.base_solver, "tol", None)
        if original_tol is not None:
            self.base_solver.tol = min(float(original_tol), self.tolerance)
        try:
            pressure = self.xp.asarray(
                self.base_solver.solve(rhs_dev, rho, dt=dt, p_init=p_init)
            )
        finally:
            if original_tol is not None:
                self.base_solver.tol = original_tol
        pressure = self._enforce_pressure_gauge(pressure)
        self.last_residual_history = []
        self.last_stalled = False
        self.last_base_pressure = self.xp.copy(pressure)
        self.last_diagnostics = dict(getattr(self.base_solver, "last_diagnostics", {}))
        if hasattr(self.operator, "apply_interface_jump"):
            pressure = self.operator.apply_interface_jump(pressure)
        return pressure

    def _pin_flat(self, flat, value) -> None:
        for dof in self._pin_dofs:
            flat[dof] = value


def _can_collapse_same_operator(base_solver: IPPESolver, operator: IPPESolver) -> bool:
    """Return whether DC wraps the same linear operator as its base solve."""
    if getattr(operator, "interface_coupling_scheme", "none") != "affine_jump":
        return False
    if type(base_solver) is not type(operator):
        return False
    for name in ("grid", "coefficient_scheme", "interface_coupling_scheme", "bc_type"):
        if getattr(base_solver, name, None) is not getattr(operator, name, None):
            if getattr(base_solver, name, None) != getattr(operator, name, None):
                return False
    return hasattr(base_solver, "solve") and hasattr(operator, "apply")
