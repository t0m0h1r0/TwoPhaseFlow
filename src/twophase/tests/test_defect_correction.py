import numpy as np

from twophase.ppe.defect_correction import PPESolverDefectCorrection
from twophase.ppe.interfaces import IPPESolver


class _BackendStub:
    xp = np

    def is_gpu(self):
        return False

    def asnumpy(self, value):
        return np.asarray(value)


class _SameOperatorStub(IPPESolver):
    def __init__(self, grid, *, coefficient_scheme="phase_separated"):
        self.grid = grid
        self.coefficient_scheme = coefficient_scheme
        self.interface_coupling_scheme = "affine_jump"
        self.bc_type = "wall"
        self._pin_dof = 0
        self._pin_dofs = (0,)
        self.tol = 1.0e-6
        self.solve_calls = 0
        self.apply_calls = 0
        self.seen_tolerances = []
        self.last_diagnostics = {"ppe_interface_coupling_affine_jump": 1.0}

    def prepare_operator(self, rho):
        self.rho = np.asarray(rho)

    def apply(self, pressure):
        self.apply_calls += 1
        return np.asarray(pressure)

    def solve(self, rhs, rho, dt, p_init=None):
        self.solve_calls += 1
        self.seen_tolerances.append(self.tol)
        return np.asarray(rhs, dtype=float)


class _DifferentOperatorStub(_SameOperatorStub):
    pass


def test_same_operator_defect_correction_is_rejected():
    grid = object()
    base = _SameOperatorStub(grid)
    operator = _SameOperatorStub(grid)
    try:
        PPESolverDefectCorrection(
            _BackendStub(),
            grid,
            base,
            operator,
            max_corrections=3,
            tolerance=1.0e-8,
        )
    except ValueError as exc:
        assert "distinct low-order base solver" in str(exc)
    else:
        raise AssertionError("same-operator defect correction must be rejected")


def test_different_operator_defect_correction_keeps_residual_loop():
    grid = object()
    base = _SameOperatorStub(grid)
    operator = _DifferentOperatorStub(grid)
    solver = PPESolverDefectCorrection(
        _BackendStub(),
        grid,
        base,
        operator,
        max_corrections=2,
        tolerance=1.0e-8,
    )

    solver.solve(np.ones((2, 2)), np.ones((2, 2)), dt=1.0)

    assert base.solve_calls >= 1
    assert base.seen_tolerances[0] == 1.0e-6
    assert operator.apply_calls >= 1
    assert solver.last_residual_history
