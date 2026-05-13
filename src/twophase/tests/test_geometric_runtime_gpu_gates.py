"""GPU fail-close gates for dense exact AO runtime pieces."""

from __future__ import annotations

import pytest
import numpy as np

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.geometry.p1_cut_geometry import cut_geometry_2d
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
