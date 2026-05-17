"""Tests for graph q-manifold projection helpers."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.geometry.interface_charts import (
    eta_from_cosine_modes,
    graph_segment_energy_gradient,
    project_column_height_to_graph,
)
from twophase.geometry.q_manifold_projection import (
    graph_force_projection,
    graph_q_from_eta,
    project_graph_q_f0,
)


def _grid(nx: int = 64, ny: int = 64) -> Grid:
    backend = Backend(use_gpu=False)
    return Grid(GridConfig(ndim=2, N=(nx, ny), L=(1.0, 1.0), alpha_grid=1.0), backend)


def _zero_column_cell_residual(grid: Grid, q: object, *, fraction: float) -> object:
    q_target = np.asarray(q, dtype=float).copy()
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    cell_area = dx[:, None] * dy[None, :]
    theta = np.divide(q_target, cell_area, out=np.zeros_like(q_target), where=cell_area > 0.0)
    for i in range(q_target.shape[0]):
        cut_candidates = np.flatnonzero((theta[i] > 1.0e-12) & (theta[i] < 1.0 - 1.0e-12))
        if cut_candidates.size == 0:
            continue
        j = int(cut_candidates[0])
        below = max(j - 1, 0)
        above = min(j + 1, q_target.shape[1] - 1)
        amount = min(
            float(fraction) * float(cell_area[i, j]),
            float(q_target[i, below]),
            float(cell_area[i, above] - q_target[i, above]),
        )
        if amount <= 0.0:
            continue
        q_target[i, below] -= amount
        q_target[i, above] += amount
    return q_target


def test_graph_f0_recovers_clean_and_low_mode_chart():
    grid = _grid()
    x_edges = np.asarray(grid.coords[0], dtype=float)
    eta_clean = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2),),
    )
    eta_low = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2), (4, 1.2e-2)),
    )

    clean_q = graph_q_from_eta(grid, eta_clean).q
    low_q = graph_q_from_eta(grid, eta_low).q

    clean = project_graph_q_f0(grid, clean_q, max_mode=4, sigma=1.0)
    low = project_graph_q_f0(grid, low_q, max_mode=4, sigma=1.0)

    np.testing.assert_allclose(clean.gamma_state.eta, eta_clean, atol=1.0e-12)
    np.testing.assert_allclose(low.gamma_state.eta, eta_low, atol=1.0e-12)
    assert clean.residual_report.l2 < 1.0e-13
    assert low.residual_report.l2 < 1.0e-13
    assert abs(low.gamma_state.coefficient_map()["cos_4"] - 1.2e-2) < 1.0e-12
    assert clean.stage == "F0"
    assert clean.chart_kind == "graph"


def test_graph_column_projection_has_batched_scalar_parity():
    grid = _grid()
    x_edges = np.asarray(grid.coords[0], dtype=float)
    eta_clean = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2),),
    )
    eta_low = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2), (4, 1.2e-2)),
    )
    height_batch = np.stack((eta_clean[:-1], eta_low[:-1]), axis=0)

    scalar = [
        project_column_height_to_graph(x_edges, height, max_mode=4)
        for height in height_batch
    ]
    batched = project_column_height_to_graph(x_edges, height_batch, max_mode=4)

    np.testing.assert_allclose(
        np.asarray(batched.eta),
        np.stack([np.asarray(state.eta) for state in scalar], axis=0),
        atol=1.0e-14,
    )
    np.testing.assert_allclose(
        np.asarray(batched.coefficient_map()["cos_4"]),
        np.asarray([state.coefficient_map()["cos_4"] for state in scalar]),
        atol=1.0e-14,
    )


def test_graph_f0_keeps_zero_column_cell_residual_out_of_geometry():
    grid = _grid()
    x_edges = np.asarray(grid.coords[0], dtype=float)
    eta_clean = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2),),
    )
    clean_q = graph_q_from_eta(grid, eta_clean).q
    high_q = _zero_column_cell_residual(grid, clean_q, fraction=5.0e-2)

    result = project_graph_q_f0(grid, high_q, max_mode=4, sigma=1.0)

    np.testing.assert_allclose(result.gamma_state.eta, eta_clean, atol=1.0e-12)
    assert result.residual_report.l2 > 1.0e-5
    assert result.residual_report.column_linf < 1.0e-13
    assert result.residual_report.total_volume_abs < 1.0e-13
    assert result.constraint_report["column_residual_linf"] < 1.0e-13
    np.testing.assert_allclose(result.residual, high_q - result.q_phys)


def test_graph_surface_force_opposes_base_mode_after_projection():
    grid = _grid()
    x_edges = np.asarray(grid.coords[0], dtype=float)
    eta = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2),),
    )
    q = graph_q_from_eta(grid, eta).q
    result = project_graph_q_f0(grid, q, max_mode=4, sigma=1.0)
    energy = graph_segment_energy_gradient(x_edges, result.gamma_state.eta, sigma=1.0)

    force_mode = graph_force_projection(energy, x_edges, mode=2)
    assert result.gamma_state.coefficient_map()["cos_2"] * force_mode < 0.0


def test_graph_projection_fails_closed_for_device_inputs():
    grid = _grid()

    class DeviceLike:
        __cuda_array_interface__ = {
            "shape": (1,),
            "typestr": "<f8",
            "data": (0, False),
            "version": 3,
        }

    with pytest.raises(ValueError, match="GPU execution requires"):
        project_graph_q_f0(grid, DeviceLike(), max_mode=4)
