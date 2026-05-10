import numpy as np
import pytest

from twophase.ppe.defect_correction import PPESolverDefectCorrection
from twophase.ppe.interfaces import IPPESolver


class _BackendStub:
    xp = np

    def is_gpu(self):
        return False

    def asnumpy(self, value):
        return np.asarray(value)


class _TrackingGpuBackendStub(_BackendStub):
    def __init__(self):
        self.transfer_shapes = []

    def is_gpu(self):
        return True

    def asnumpy(self, value):
        array = np.asarray(value)
        self.transfer_shapes.append(array.shape)
        return array


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
        self.static_cache_flags = []
        self.last_diagnostics = {"ppe_interface_coupling_affine_jump": 1.0}

    def prepare_operator(self, rho):
        self.rho = np.asarray(rho)

    def set_static_operator_cache(self, enabled):
        self.static_cache_flags.append(bool(enabled))

    def apply(self, pressure):
        self.apply_calls += 1
        return np.asarray(pressure)

    def solve(self, rhs, rho, dt, p_init=None):
        self.solve_calls += 1
        self.seen_tolerances.append(self.tol)
        return np.asarray(rhs, dtype=float)


class _DifferentOperatorStub(_SameOperatorStub):
    pass


class _OverScaledBaseStub(_SameOperatorStub):
    def solve(self, rhs, rho, dt, p_init=None):
        self.solve_calls += 1
        self.seen_tolerances.append(self.tol)
        return 10.0 * np.asarray(rhs, dtype=float)


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


def test_same_operator_defect_correction_is_rejected_without_affine_jump():
    grid = object()
    base = _SameOperatorStub(grid, coefficient_scheme="phase_density")
    operator = _SameOperatorStub(grid, coefficient_scheme="phase_density")
    base.interface_coupling_scheme = "none"
    operator.interface_coupling_scheme = "none"

    with pytest.raises(ValueError, match="distinct low-order base solver"):
        PPESolverDefectCorrection(
            _BackendStub(),
            grid,
            base,
            operator,
            max_corrections=3,
            tolerance=1.0e-8,
        )


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
    assert solver.last_diagnostics["ppe_dc_converged"] == 1.0
    assert solver.last_diagnostics["ppe_dc_final_residual_l2"] == 0.0
    assert solver.last_diagnostics["ppe_dc_iterations"] == 0.0


def test_defect_correction_uses_residual_minimising_step_length():
    grid = object()
    base = _OverScaledBaseStub(grid)
    operator = _DifferentOperatorStub(grid)
    solver = PPESolverDefectCorrection(
        _BackendStub(),
        grid,
        base,
        operator,
        max_corrections=1,
        tolerance=1.0e-12,
        relaxation=1.0,
    )

    pressure = solver.solve(np.ones((2, 2)), np.ones((2, 2)), dt=1.0)

    expected = np.ones((2, 2))
    expected[0, 0] = 0.0
    np.testing.assert_allclose(pressure, expected)
    assert operator.apply_calls == 3
    assert solver.last_diagnostics["ppe_dc_converged"] == 1.0
    assert solver.last_diagnostics["ppe_dc_final_residual_l2"] == pytest.approx(0.0)


def test_defect_correction_line_search_keeps_gpu_transfers_scalar_sized():
    grid = object()
    backend = _TrackingGpuBackendStub()
    solver = PPESolverDefectCorrection(
        backend,
        grid,
        _OverScaledBaseStub(grid),
        _DifferentOperatorStub(grid),
        max_corrections=1,
        tolerance=1.0e-12,
        relaxation=1.0,
    )

    solver.solve(np.ones((4, 4)), np.ones((4, 4)), dt=1.0)

    assert backend.transfer_shapes
    assert max(int(np.prod(shape or (1,))) for shape in backend.transfer_shapes) <= 2


def test_defect_correction_collapse_branch_fails_closed():
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
    solver._collapse_same_operator = True

    with pytest.raises(RuntimeError, match="same-operator defect-correction collapse"):
        solver.solve(np.ones((2, 2)), np.ones((2, 2)), dt=1.0)


def test_defect_correction_forwards_static_operator_cache():
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

    solver.set_static_operator_cache(True)

    assert base.static_cache_flags == [True]
    assert operator.static_cache_flags == [True]
