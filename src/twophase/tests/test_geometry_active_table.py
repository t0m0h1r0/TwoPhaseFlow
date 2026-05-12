"""AO-Fast active geometry table and operator gates."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend, is_device_array
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.geometry import active_projection as active_projection_module
from twophase.geometry.active_kernels import refresh_active_geometry_2d
from twophase.geometry.active_projection import (
    ActiveSchurOperator,
    project_active_cell_volume_compatibility_2d,
    solve_active_pcg,
)
from twophase.geometry.active_table import (
    ORIGIN_FLUX,
    ORIGIN_HALO,
    ORIGIN_TARGET,
    ActiveSupportBudget,
    TargetStateCode,
    build_active_table_for_cell_ids,
    build_debug_active_table_from_dense,
    compact_active_cell_ids_from_streams,
)
from twophase.geometry.dense_reference import MetricCellComplex, cut_geometry_2d


def _grid(nx: int = 8, ny: int | None = None):
    ny = nx if ny is None else ny
    backend = Backend(use_gpu=False)
    return Grid(GridConfig(ndim=2, N=(nx, ny), L=(1.0, 1.0)), backend), backend


def _mesh(grid):
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    return np.meshgrid(x, y, indexing="ij")


def _gather(field, cell_ids):
    ids = np.asarray(cell_ids, dtype=np.int64)
    return np.asarray(field)[ids[:, 0], ids[:, 1]]


def _local_corner_field(field):
    return np.stack(
        (
            field[:-1, :-1],
            field[1:, :-1],
            field[1:, 1:],
            field[:-1, 1:],
        ),
        axis=-1,
    )


def test_debug_active_table_matches_dense_oracle_rows():
    grid, _backend = _grid(12)
    x, y = _mesh(grid)
    phi = x + 0.2 * y - 0.53
    dense = cut_geometry_2d(grid, phi)

    table = build_debug_active_table_from_dense(
        grid,
        phi,
        support_budget=ActiveSupportBudget(
            max_active_ratio=0.6,
            max_support_stream_ratio=0.6,
            max_epoch_growth_ratio=2.0,
        ),
        allowed_context="oracle_test",
    )

    assert table.ledger.dense_scan_used is True
    assert table.n_active < grid.N[0] * grid.N[1]
    assert table.metric_key_A is table.cell_measure_A
    np.testing.assert_allclose(
        table.cell_measure_A,
        _gather(MetricCellComplex.from_grid(grid).cell_measures, table.cell_ids_A),
    )
    np.testing.assert_allclose(table.q_A, _gather(dense.q, table.cell_ids_A))
    np.testing.assert_allclose(
        table.s_A,
        _gather(dense.cell_surface_lengths, table.cell_ids_A),
    )
    assert np.all(np.asarray(table.cell_measure_A) > 0.0)
    assert np.all(np.asarray(table.target_theta_A) >= -1.0e-14)
    assert np.all(np.asarray(table.target_theta_A) <= 1.0 + 1.0e-14)


def test_compact_stream_support_tracks_target_flux_and_halo_metadata():
    grid, _backend = _grid(6)
    x, y = _mesh(grid)
    phi = x + y - 1.05
    current = np.asarray([[2, 2], [2, 3]], dtype=np.int64)
    target = np.asarray([[0, 0]], dtype=np.int64)
    flux = np.asarray([[4, 4]], dtype=np.int64)
    ids, origin = compact_active_cell_ids_from_streams(
        grid_shape=grid.N,
        current_cell_ids=current,
        target_cell_ids=target,
        flux_touched_cell_ids=flux,
        include_halo=True,
        boundary=("wall", "wall"),
    )
    target_index = np.where((ids == np.asarray([0, 0])).all(axis=1))[0][0]
    flux_index = np.where((ids == np.asarray([4, 4])).all(axis=1))[0][0]
    assert origin[target_index] & ORIGIN_TARGET
    assert origin[flux_index] & ORIGIN_FLUX
    assert np.any(origin & ORIGIN_HALO)

    complex_h = MetricCellComplex.from_grid(grid)
    q_target = np.zeros(grid.N, dtype=float)
    q_target[0, 0] = 0.25 * np.asarray(complex_h.cell_measures)[0, 0]
    table = build_active_table_for_cell_ids(
        grid,
        phi,
        ids,
        q_target=q_target,
        origin_mask=origin,
        flux_touched_mask=(origin & ORIGIN_FLUX) != 0,
        halo_mask=(origin & ORIGIN_HALO) != 0,
        support_budget=ActiveSupportBudget(
            max_active_ratio=0.8,
            max_support_stream_ratio=0.8,
            max_epoch_growth_ratio=2.0,
        ),
    )

    assert table.ledger.dense_scan_used is False
    assert table.ledger.n_flux_touched >= 1
    assert table.target_state_code_A[target_index] == TargetStateCode.MIXED
    assert table.target_state_code_A[flux_index] == TargetStateCode.EMPTY


def test_active_table_capacity_overrun_fails_closed():
    grid, _backend = _grid(4)
    x, _ = _mesh(grid)
    phi = x - 0.45
    too_many = np.argwhere(np.ones(grid.N, dtype=bool))

    with pytest.raises(ValueError, match="capacity exceeded"):
        build_active_table_for_cell_ids(
            grid,
            phi,
            too_many,
            support_budget=ActiveSupportBudget(
                max_active_ratio=0.25,
                max_support_stream_ratio=0.25,
                max_epoch_growth_ratio=2.0,
            ),
        )


def test_compact_support_stream_budget_overrun_fails_closed():
    grid, _backend = _grid(4)
    too_many_stream_cells = np.asarray(
        [[0, 0], [0, 1], [1, 0], [1, 1], [2, 2]],
        dtype=np.int64,
    )

    with pytest.raises(ValueError, match="compact support stream capacity exceeded"):
        compact_active_cell_ids_from_streams(
            grid_shape=grid.N,
            current_cell_ids=too_many_stream_cells,
            support_budget=ActiveSupportBudget(
                max_active_ratio=1.0,
                max_support_stream_ratio=0.25,
                max_epoch_growth_ratio=2.0,
            ),
            include_halo=False,
        )


def test_compact_support_stream_rejects_device_arrays_before_host_conversion():
    class _DeviceStream:
        __cuda_array_interface__ = {"shape": (1, 2), "typestr": "<i8", "data": (0, False)}

    with pytest.raises(ValueError, match="fused GPU compaction"):
        compact_active_cell_ids_from_streams(
            grid_shape=(4, 4),
            current_cell_ids=_DeviceStream(),
        )


def test_compact_table_construction_does_not_call_dense_oracle(monkeypatch):
    grid, _backend = _grid(6)
    x, _ = _mesh(grid)
    phi = x - 0.43
    ids = np.asarray([[2, 0], [2, 1], [2, 2]], dtype=np.int64)

    def _blocked_dense_call(*_args, **_kwargs):
        raise AssertionError("compact active table must not call dense oracle")

    monkeypatch.setattr(
        "twophase.geometry.active_table.cut_geometry_2d",
        _blocked_dense_call,
    )
    monkeypatch.setattr(
        "twophase.geometry.active_table.MetricCellComplex.from_grid",
        _blocked_dense_call,
    )

    table = build_active_table_for_cell_ids(grid, phi, ids)
    assert table.n_active == 3
    assert table.ledger.dense_scan_used is False


def test_gpu_active_table_stays_device_and_pcg_host_control_fails_closed():
    cp = pytest.importorskip("cupy")
    try:
        grid = Grid(GridConfig(ndim=2, N=(6, 6), L=(1.0, 1.0)), Backend(use_gpu=True))
    except RuntimeError as exc:
        pytest.skip(str(exc))
    x = cp.asarray(grid.coords[0], dtype=cp.float32)
    y = cp.asarray(grid.coords[1], dtype=cp.float32)
    X, _ = cp.meshgrid(x, y, indexing="ij")
    phi = X - 0.43
    ids = cp.asarray([[2, 0], [2, 1], [2, 2]], dtype=cp.int64)

    table = build_active_table_for_cell_ids(grid, phi, ids)
    assert is_device_array(table.q_A)
    assert is_device_array(table.jq_local_A)
    assert table.ledger.dense_scan_used is False
    assert table.ledger.device_resident is True
    assert table.ledger.host_transfer_count == 0
    assert table.ledger.n_halo == 0
    assert table.ledger.n_flux_touched == 0
    assert table.ledger.n_target_mixed == -1
    assert table.ledger.deferred_device_count_fields == ("n_target_mixed",)
    assert table.metric_key_A is table.cell_measure_A

    operator = ActiveSchurOperator(table)
    assert operator.n_active_nodes < (grid.N[0] + 1) * (grid.N[1] + 1)
    compact_jt = operator.apply_j_transpose_compact(cp.ones((table.n_active,), dtype=float))
    assert is_device_array(compact_jt)
    assert compact_jt.shape == (operator.n_active_nodes,)
    assert compact_jt.dtype == table.jq_local_A.dtype
    rhs = operator.apply_schur(cp.ones((table.n_active,), dtype=float))
    assert is_device_array(rhs)
    with pytest.raises(ValueError, match="host synchronization"):
        active_projection_module._norm_linf(cp, rhs)
    with pytest.raises(ValueError, match="fused device reductions"):
        operator.diagnostics()
    with pytest.raises(ValueError, match="fused device solver"):
        solve_active_pcg(operator, rhs, tolerance=1.0e-10, max_iterations=8)
    with pytest.raises(ValueError, match="fused device reductions"):
        project_active_cell_volume_compatibility_2d(
            grid,
            phi,
            table,
            tolerance=1.0e-10,
            max_newton_iterations=1,
        )


def test_active_jq_and_ds_match_finite_difference_on_active_rows():
    grid, _backend = _grid(10)
    x, y = _mesh(grid)
    phi = x + 0.15 * y - 0.48
    direction = 0.02 * np.sin(2.0 * np.pi * x) + 0.01 * np.cos(2.0 * np.pi * y)
    eps = 1.0e-7
    table = build_debug_active_table_from_dense(
        grid,
        phi,
        support_budget=ActiveSupportBudget(
            max_active_ratio=0.6,
            max_support_stream_ratio=0.6,
            max_epoch_growth_ratio=2.0,
        ),
        allowed_context="oracle_test",
    )
    active = np.asarray(table.row_norm_A) > 0.0

    geom_plus = refresh_active_geometry_2d(grid, phi + eps * direction, table.cell_ids_A)
    geom_minus = refresh_active_geometry_2d(grid, phi - eps * direction, table.cell_ids_A)
    local_direction = _gather(_local_corner_field(direction), table.cell_ids_A)

    predicted_q = np.sum(np.asarray(table.jq_local_A) * local_direction, axis=-1)
    predicted_s = np.sum(np.asarray(table.ds_local_A) * local_direction, axis=-1)
    fd_q = (np.asarray(geom_plus.q_A) - np.asarray(geom_minus.q_A)) / (2.0 * eps)
    fd_s = (np.asarray(geom_plus.s_A) - np.asarray(geom_minus.s_A)) / (2.0 * eps)

    np.testing.assert_allclose(predicted_q[active], fd_q[active], rtol=1.0e-6, atol=1.0e-9)
    np.testing.assert_allclose(predicted_s[active], fd_s[active], rtol=1.0e-6, atol=1.0e-9)


def test_active_schur_adjointness_and_pcg_floor_policy():
    grid, _backend = _grid(8)
    x, y = _mesh(grid)
    phi = x + 0.25 * y - 0.52
    table = build_debug_active_table_from_dense(
        grid,
        phi,
        support_budget=ActiveSupportBudget(
            max_active_ratio=0.7,
            max_support_stream_ratio=0.7,
            max_epoch_growth_ratio=2.0,
        ),
        allowed_context="oracle_test",
    )
    operator = ActiveSchurOperator(table)
    rng = np.random.default_rng(1234)
    nodal = rng.normal(size=table.node_shape)
    cell = rng.normal(size=table.n_active)

    left = float(np.dot(np.asarray(operator.apply_j(nodal)), cell))
    right = float(np.sum(nodal * np.asarray(operator.apply_j_transpose(cell))))
    np.testing.assert_allclose(left, right, rtol=1.0e-12, atol=1.0e-12)

    diagnostics = operator.diagnostics()
    assert diagnostics.active_row_count > 0
    assert diagnostics.cheap_condition_estimate >= 1.0

    compact_jt = operator.apply_j_transpose_compact(cell)
    assert compact_jt.shape == (operator.n_active_nodes,)
    np.testing.assert_allclose(
        operator.apply_j_compact(compact_jt),
        operator.apply_j(operator.apply_j_transpose(cell)),
        rtol=1.0e-12,
        atol=1.0e-12,
    )

    rhs = operator.apply_schur(cell)
    result = solve_active_pcg(
        operator,
        rhs,
        tolerance=1.0e-10,
        max_iterations=4 * table.n_active,
    )
    assert result.stop_reason == "algebraic_tolerance"
    assert result.residual_linf <= 1.0e-10

    with pytest.raises(ValueError, match="roundoff floor"):
        solve_active_pcg(
            operator,
            rhs,
            tolerance=1.0e-12,
            tau_cg_floor=1.0e-10,
            max_iterations=4,
        )


def test_active_projection_accepts_exact_active_residual_without_dense_fallback():
    grid, _backend = _grid(12)
    x, y = _mesh(grid)
    phi = x + 0.2 * y - 0.53
    direction = 0.001 * np.sin(2.0 * np.pi * x) + 0.0005 * np.cos(2.0 * np.pi * y)
    support = build_debug_active_table_from_dense(
        grid,
        phi,
        support_budget=ActiveSupportBudget(
            max_active_ratio=0.7,
            max_support_stream_ratio=0.7,
            max_epoch_growth_ratio=2.0,
        ),
        allowed_context="oracle_test",
    )
    target_geometry = refresh_active_geometry_2d(
        grid,
        phi + direction,
        support.cell_ids_A,
    )
    table = build_active_table_for_cell_ids(
        grid,
        phi,
        support.cell_ids_A,
        q_target=target_geometry.q_A,
        origin_mask=support.origin_mask_A,
        halo_mask=support.halo_mask_A,
        support_budget=ActiveSupportBudget(
            max_active_ratio=0.7,
            max_support_stream_ratio=0.7,
            max_epoch_growth_ratio=2.0,
        ),
    )

    result = project_active_cell_volume_compatibility_2d(
        grid,
        phi,
        table,
        tolerance=1.0e-11,
        max_newton_iterations=6,
        max_pcg_iterations=4 * table.n_active,
    )

    assert result.ledger.stop_reason == "exact_active_residual"
    assert result.ledger.final_residual_linf <= 1.0e-11
    assert result.table.ledger.dense_scan_used is False


def test_active_projection_empty_support_returns_noop_ledger():
    grid, _backend = _grid(6)
    x, _ = _mesh(grid)
    phi = x - 2.0
    empty_ids = np.zeros((0, 2), dtype=np.int64)
    table = build_active_table_for_cell_ids(grid, phi, empty_ids)

    result = project_active_cell_volume_compatibility_2d(
        grid,
        phi,
        table,
        tolerance=1.0e-11,
        max_pcg_iterations=0,
    )

    assert result.ledger.stop_reason == "empty_active_support"
    assert result.ledger.final_residual_linf == 0.0
    np.testing.assert_allclose(result.phi, phi)
