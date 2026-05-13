"""GPU fail-close gates for dense exact AO runtime pieces."""

from __future__ import annotations

import pytest
import numpy as np

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.geometry.p1_cut_geometry import cut_geometry_2d
from twophase.geometry.swept_flux import (
    _axis_aligned_strip_area,
    _axis_aligned_strip_area_unfused,
)
from twophase.ppe.fd_direct import _PreparedCuPySuperLUSolve
from twophase.simulation import geometric_phase_runtime_gpu as gpu_runtime
from twophase.simulation.geometric_phase_runtime_gpu import (
    _host_scalar_packet_float,
    _solve_schur_dc_fixed_gpu,
    _solve_schur_for_active_policy_gpu,
    _solve_schur_pcg_fixed_gpu,
)


class _CountingBackend:
    xp = np

    def __init__(self):
        self.host_transfer_count = 0

    def to_host(self, value):
        self.host_transfer_count += 1
        return value


def test_gpu_scalar_packet_uses_one_host_transfer():
    backend = _CountingBackend()
    values = _host_scalar_packet_float(
        backend,
        [
            ("compatibility", np.asarray(1.0e-12)),
            ("normal", np.asarray(2.0e-12)),
            ("predictor", np.asarray(3.0e-12)),
        ],
    )

    assert values == {
        "compatibility": pytest.approx(1.0e-12),
        "normal": pytest.approx(2.0e-12),
        "predictor": pytest.approx(3.0e-12),
    }
    assert backend.host_transfer_count == 1


def test_gpu_single_scalar_transfer_helper_fails_closed():
    backend = _CountingBackend()
    with pytest.raises(RuntimeError, match="single-scalar GPU host transfer"):
        gpu_runtime._host_scalar_float(backend, np.asarray(1.0), "compatibility")
    assert backend.host_transfer_count == 0


def test_gpu_schur_pcg_respects_device_tolerance_mask():
    class GridStub:
        ndim = 2
        N = (1, 1)
        xp = np

    grid = GridStub()
    jq_local = np.ones((1, 1, 4), dtype=float)
    rhs = np.asarray([[8.0]])
    row_norm = np.asarray([[4.0]])
    active = np.asarray([[True]])

    converged_initially = _solve_schur_pcg_fixed_gpu(
        grid,
        np,
        jq_local,
        rhs,
        row_norm,
        active,
        max_iterations=4,
        tolerance=100.0,
        roundoff_floor=1.0e-14,
    )
    solved = _solve_schur_pcg_fixed_gpu(
        grid,
        np,
        jq_local,
        rhs,
        row_norm,
        active,
        max_iterations=4,
        tolerance=1.0e-12,
        roundoff_floor=1.0e-14,
    )

    np.testing.assert_allclose(converged_initially, 0.0)
    np.testing.assert_allclose(solved, 2.0)


def test_gpu_schur_pcg_uses_fixed_shape_masked_support(monkeypatch):
    class GridStub:
        ndim = 2
        N = (2, 2)
        xp = np

    grid = GridStub()
    jq_local = np.zeros((2, 2, 4), dtype=float)
    jq_local[0, 0, :] = 1.0
    rhs = np.zeros((2, 2), dtype=float)
    rhs[0, 0] = 8.0
    row_norm = np.sum(jq_local * jq_local, axis=-1)
    active = row_norm > 0.0

    def _dynamic_support_must_not_run(*_args, **_kwargs):
        raise AssertionError("dynamic active support discovery was called")

    monkeypatch.setattr(np, "argwhere", _dynamic_support_must_not_run)
    monkeypatch.setattr(np, "unique", _dynamic_support_must_not_run)

    solved = gpu_runtime._solve_schur_pcg_fixed_gpu(
        grid,
        np,
        jq_local,
        rhs,
        row_norm,
        active,
        max_iterations=4,
        tolerance=1.0e-12,
        roundoff_floor=1.0e-14,
    )

    expected = np.zeros((2, 2), dtype=float)
    expected[0, 0] = 2.0
    np.testing.assert_allclose(solved, expected)


def test_gpu_masked_schur_direct_formula_matches_j_jt_composition():
    class GridStub:
        ndim = 2
        N = (3, 2)
        xp = np

    rng = np.random.default_rng(314)
    grid = GridStub()
    jq_local = rng.normal(size=(3, 2, 4))
    active = np.asarray(
        [[True, False], [True, True], [False, True]],
        dtype=bool,
    )
    jq_local = np.where(active[..., None], jq_local, 0.0)
    row_norm = np.sum(jq_local * jq_local, axis=-1)
    cell = rng.normal(size=(3, 2))
    support = gpu_runtime._masked_schur_support_from_active(
        grid,
        np,
        jq_local,
        row_norm,
        active,
    )

    direct = support.apply_schur(cell)
    composed = support.apply_j(support.apply_j_transpose(cell))

    np.testing.assert_allclose(direct, composed, rtol=1.0e-14, atol=1.0e-14)


def test_gpu_masked_schur_raw_kernel_matches_vector_formula():
    cp = pytest.importorskip("cupy")
    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip("CUDA device unavailable")
    except cp.cuda.runtime.CUDARuntimeError as exc:
        pytest.skip(str(exc))

    class GridStub:
        ndim = 2
        N = (3, 2)
        xp = cp

    rng = np.random.default_rng(2718)
    grid = GridStub()
    active_np = np.asarray(
        [[True, False], [True, True], [False, True]],
        dtype=bool,
    )
    jq_np = rng.normal(size=(3, 2, 4))
    jq_np = np.where(active_np[..., None], jq_np, 0.0)
    cell_np = rng.normal(size=(3, 2))
    jq_local = cp.asarray(jq_np)
    active = cp.asarray(active_np)
    cell = cp.asarray(cell_np)
    row_norm = cp.sum(jq_local * jq_local, axis=-1)
    support = gpu_runtime._masked_schur_support_from_active(
        grid,
        cp,
        jq_local,
        row_norm,
        active,
    )

    raw = support.apply_schur(cell)
    vector = gpu_runtime._apply_schur_masked_2d_vector(
        cp,
        jq_local,
        active,
        cell,
        grid.N,
        (grid.N[0] + 1, grid.N[1] + 1),
    )

    cp.testing.assert_allclose(raw, vector, rtol=1.0e-12, atol=1.0e-12)


def test_gpu_pcg_block_kernel_matches_vector_pcg():
    cp = pytest.importorskip("cupy")
    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip("CUDA device unavailable")
    except cp.cuda.runtime.CUDARuntimeError as exc:
        pytest.skip(str(exc))

    class GridStub:
        ndim = 2
        N = (4, 4)
        xp = cp

    rng = np.random.default_rng(1618)
    grid = GridStub()
    active_np = np.ones(grid.N, dtype=bool)
    jq_np = rng.normal(size=grid.N + (4,))
    rhs_np = rng.normal(size=grid.N)
    jq_local = cp.asarray(jq_np)
    rhs = cp.asarray(rhs_np)
    active = cp.asarray(active_np)
    row_norm = cp.sum(jq_local * jq_local, axis=-1)
    support = gpu_runtime._masked_schur_support_from_active(
        grid,
        cp,
        jq_local,
        row_norm,
        active,
    )

    raw = gpu_runtime._solve_schur_pcg_block_raw_if_available(
        cp,
        jq_local,
        rhs,
        row_norm,
        active,
        None,
        grid.N,
        iterations=12,
        tolerance=1.0e-12,
        roundoff_floor=1.0e-14,
    )
    vector = gpu_runtime._solve_schur_pcg_fixed_gpu_vector(
        cp,
        rhs,
        None,
        support,
        iterations=12,
        tolerance=1.0e-12,
        roundoff_floor=1.0e-14,
    )

    assert raw is not None
    cp.testing.assert_allclose(raw, vector, rtol=1.0e-10, atol=1.0e-10)


def test_gpu_swept_strip_raw_kernel_matches_unfused_nonuniform_geometry():
    cp = pytest.importorskip("cupy")
    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip("CUDA device unavailable")
    except cp.cuda.runtime.CUDARuntimeError as exc:
        pytest.skip(str(exc))

    rng = np.random.default_rng(811)
    x_edges_np = np.cumsum(np.r_[0.0, rng.uniform(0.05, 0.17, size=5)])
    y_edges_np = np.cumsum(np.r_[0.0, rng.uniform(0.04, 0.19, size=4)])
    phi_lb_np = rng.normal(size=(5, 4))
    phi_rb_np = rng.normal(size=(5, 4))
    phi_lt_np = rng.normal(size=(5, 4))
    phi_rt_np = rng.normal(size=(5, 4))
    # Include the ambiguous P1 case-10 split and zero-adjacent cuts in the
    # oracle comparison; these are where fail-open fallbacks most easily hide.
    phi_lb_np[1, 1] = 1.0
    phi_rb_np[1, 1] = -1.0
    phi_rt_np[1, 1] = 1.0
    phi_lt_np[1, 1] = -1.0
    phi_lb_np[3, 2] = 0.0

    x_edges = cp.asarray(x_edges_np)
    y_edges = cp.asarray(y_edges_np)
    phi_lb = cp.asarray(phi_lb_np)
    phi_rb = cp.asarray(phi_rb_np)
    phi_lt = cp.asarray(phi_lt_np)
    phi_rt = cp.asarray(phi_rt_np)

    x0 = x_edges[:-1].reshape((-1, 1))
    x1 = x_edges[1:].reshape((-1, 1))
    y0 = y_edges[:-1].reshape((1, -1))
    y1 = y_edges[1:].reshape((1, -1))
    dx = (x_edges[1:] - x_edges[:-1]).reshape((-1, 1))
    dy = (y_edges[1:] - y_edges[:-1]).reshape((1, -1))

    x_lower = x1 - 0.37 * dx
    x_upper = x1
    y_lower = y0
    y_upper = y0 + 0.41 * dy

    raw_x = _axis_aligned_strip_area(
        cp, "x", x0, x1, y0, y1, x_lower, x_upper, phi_lb, phi_rb, phi_lt, phi_rt
    )
    oracle_x = _axis_aligned_strip_area_unfused(
        cp, "x", x0, x1, y0, y1, x_lower, x_upper, phi_lb, phi_rb, phi_lt, phi_rt
    )
    raw_y = _axis_aligned_strip_area(
        cp, "y", x0, x1, y0, y1, y_lower, y_upper, phi_lb, phi_rb, phi_lt, phi_rt
    )
    oracle_y = _axis_aligned_strip_area_unfused(
        cp, "y", x0, x1, y0, y1, y_lower, y_upper, phi_lb, phi_rb, phi_lt, phi_rt
    )

    cp.testing.assert_allclose(raw_x, oracle_x, rtol=1.0e-12, atol=1.0e-12)
    cp.testing.assert_allclose(raw_y, oracle_y, rtol=1.0e-12, atol=1.0e-12)

    cases = np.arange(16, dtype=np.uint8)
    case_values = np.ones((16, 1, 4), dtype=float)
    for corner in range(4):
        case_values[:, 0, corner] = np.where(cases & (1 << corner), -1.0, 1.0)
    case_x0 = cp.asarray(np.linspace(0.0, 1.5, 16)).reshape((-1, 1))
    case_dx = cp.asarray(np.linspace(0.05, 0.2, 16)).reshape((-1, 1))
    case_x1 = case_x0 + case_dx
    case_y0 = cp.asarray([[0.0]])
    case_y1 = cp.asarray([[0.7]])
    case_x_lower = case_x0 + 0.23 * case_dx
    case_x_upper = case_x0 + 0.81 * case_dx
    case_y_lower = cp.asarray([[0.11]])
    case_y_upper = cp.asarray([[0.53]])
    case_phi_lb = cp.asarray(case_values[:, :, 0])
    case_phi_rb = cp.asarray(case_values[:, :, 1])
    case_phi_rt = cp.asarray(case_values[:, :, 2])
    case_phi_lt = cp.asarray(case_values[:, :, 3])

    case_raw_x = _axis_aligned_strip_area(
        cp,
        "x",
        case_x0,
        case_x1,
        case_y0,
        case_y1,
        case_x_lower,
        case_x_upper,
        case_phi_lb,
        case_phi_rb,
        case_phi_lt,
        case_phi_rt,
    )
    case_oracle_x = _axis_aligned_strip_area_unfused(
        cp,
        "x",
        case_x0,
        case_x1,
        case_y0,
        case_y1,
        case_x_lower,
        case_x_upper,
        case_phi_lb,
        case_phi_rb,
        case_phi_lt,
        case_phi_rt,
    )
    case_raw_y = _axis_aligned_strip_area(
        cp,
        "y",
        case_x0,
        case_x1,
        case_y0,
        case_y1,
        case_y_lower,
        case_y_upper,
        case_phi_lb,
        case_phi_rb,
        case_phi_lt,
        case_phi_rt,
    )
    case_oracle_y = _axis_aligned_strip_area_unfused(
        cp,
        "y",
        case_x0,
        case_x1,
        case_y0,
        case_y1,
        case_y_lower,
        case_y_upper,
        case_phi_lb,
        case_phi_rb,
        case_phi_lt,
        case_phi_rt,
    )
    cp.testing.assert_allclose(case_raw_x, case_oracle_x, rtol=1.0e-12, atol=1.0e-12)
    cp.testing.assert_allclose(case_raw_y, case_oracle_y, rtol=1.0e-12, atol=1.0e-12)


def test_gpu_fd_direct_uses_explicit_spsm_solve_plan_for_same_factor():
    cp = pytest.importorskip("cupy")
    cpsp = pytest.importorskip("cupyx.scipy.sparse")
    cpspla = pytest.importorskip("cupyx.scipy.sparse.linalg")
    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip("CUDA device unavailable")
    except cp.cuda.runtime.CUDARuntimeError as exc:
        pytest.skip(str(exc))

    matrix = cpsp.csc_matrix(
        cp.asarray(
            [
                [4.0, 1.0, 0.0, 0.0],
                [1.0, 3.0, 1.0, 0.0],
                [0.0, 1.0, 2.5, 0.5],
                [0.0, 0.0, 0.5, 2.0],
            ]
        )
    )
    raw_factor = cpspla.splu(matrix)
    plan = _PreparedCuPySuperLUSolve(raw_factor, rhs_shape=(matrix.shape[0], 1))

    rhs_a = cp.asarray([1.0, -2.0, 3.0, 0.5])
    rhs_b = cp.asarray([-0.25, 0.75, 1.25, -1.5])
    cp.testing.assert_allclose(plan.solve(rhs_a), raw_factor.solve(rhs_a))
    prepared_analyses = plan.analysis_count
    assert prepared_analyses == 2

    cp.testing.assert_allclose(plan.solve(rhs_b), raw_factor.solve(rhs_b))
    assert plan.analysis_count == prepared_analyses

    with pytest.raises(RuntimeError, match="vector RHS"):
        plan.solve(cp.eye(matrix.shape[0]))


def test_gpu_schur_dc_and_dc_then_pcg_follow_yaml_scheme():
    class GridStub:
        ndim = 2
        N = (1, 1)
        xp = np

    grid = GridStub()
    jq_local = np.ones((1, 1, 4), dtype=float)
    rhs = np.asarray([[8.0]])
    row_norm = np.asarray([[4.0]])
    active = np.asarray([[True]])

    dc_only = _solve_schur_dc_fixed_gpu(
        grid,
        np,
        jq_local,
        rhs,
        row_norm,
        active,
        max_iterations=1,
        tolerance=1.0e-12,
        relaxation=1.0,
    )
    chained = _solve_schur_for_active_policy_gpu(
        grid,
        np,
        jq_local,
        rhs,
        row_norm,
        active,
        solver_scheme="dc_then_pcg",
        pcg_tolerance=1.0e-12,
        pcg_max_iterations=4,
        pcg_roundoff_floor=1.0e-14,
        dc_tolerance=1.0e-12,
        dc_max_iterations=1,
        dc_relaxation=1.0,
    )

    np.testing.assert_allclose(dc_only, 2.0)
    np.testing.assert_allclose(chained, 2.0)


def test_direct_dense_geometry_rejects_gpu_backend():
    try:
        import cupy  # noqa: F401
    except Exception:
        pytest.skip("CuPy is not importable")
    try:
        backend = Backend(use_gpu=True)
    except RuntimeError as exc:
        pytest.skip(f"GPU backend unavailable: {exc}")

    grid = Grid(GridConfig(ndim=2, N=(8, 8), L=(1.0, 1.0)), backend)
    xp = backend.xp
    x = xp.asarray(grid.coords[0]).reshape((-1, 1))
    phi = x - xp.asarray(0.5)

    with pytest.raises(ValueError, match="active fused AO-Fast kernels"):
        cut_geometry_2d(grid, phi)
