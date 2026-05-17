"""Tests for q-manifold projection helpers."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.geometry.interface_charts import (
    closed_polygon_geometry,
    closed_radial_chart_from_modes,
    eta_from_cosine_modes,
    graph_segment_energy_gradient,
    project_column_height_to_graph,
)
from twophase.geometry.q_manifold_projection import (
    closed_mode_restoring_action,
    closed_radial_q_from_chart,
    graph_force_projection,
    graph_q_from_eta,
    project_closed_radial_mode_f0,
    project_graph_q_f0,
    project_graph_q_f1_low_mode,
)


def _grid(nx: int = 64, ny: int = 64, *, alpha_grid: float = 1.0) -> Grid:
    backend = Backend(use_gpu=False)
    return Grid(
        GridConfig(ndim=2, N=(nx, ny), L=(1.0, 1.0), alpha_grid=float(alpha_grid)),
        backend,
    )


def _fit_x_nonuniform_grid(grid: Grid) -> None:
    x_nodes = np.asarray(grid.coords[0], dtype=float)
    y_nodes = np.asarray(grid.coords[1], dtype=float)
    x, _y = np.meshgrid(x_nodes, y_nodes, indexing="ij")
    eps = 1.5 * (float(grid.L[0]) / int(grid.N[0]))
    phi = x - 0.5 * float(grid.L[0])
    psi = 1.0 / (1.0 + np.exp(-phi / eps))
    grid.update_from_levelset(psi, eps=eps, ccd=CCDSolver(grid, grid.backend, bc_type="wall"))


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


def _closed_high_residual(grid: Grid, q: object, *, mode: int, fraction: float) -> object:
    q_arr = np.asarray(q, dtype=float)
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    cell_area = dx[:, None] * dy[None, :]
    theta = np.divide(q_arr, cell_area, out=np.zeros_like(q_arr), where=cell_area > 0.0)
    mask = (theta > 1.0e-3) & (theta < 1.0 - 1.0e-3)
    x_center = 0.5 * (np.asarray(grid.coords[0])[:-1] + np.asarray(grid.coords[0])[1:])
    y_center = 0.5 * (np.asarray(grid.coords[1])[:-1] + np.asarray(grid.coords[1])[1:])
    x, y = np.meshgrid(x_center, y_center, indexing="ij")
    angle = np.mod(np.arctan2(y - 0.5, x - 0.5), 2.0 * np.pi)
    pattern = mask * np.sin(7.0 * angle + 0.3 * np.cos(5.0 * angle))
    basis = np.stack((mask.astype(float), mask * np.cos(int(mode) * angle)), axis=-1)
    gram = np.einsum("ija,ijb->ab", basis, basis)
    rhs = np.einsum("ija,ij->a", basis, pattern)
    coeff = np.linalg.solve(gram, rhs)
    residual = pattern - np.einsum("ija,a->ij", basis, coeff)
    if not np.any(residual):
        raise AssertionError("closed residual pattern vanished")
    positive = residual > 0.0
    negative = residual < 0.0
    limits = []
    if np.any(positive):
        limits.append(np.min((cell_area - q_arr)[positive] / residual[positive]))
    if np.any(negative):
        limits.append(np.min(q_arr[negative] / (-residual[negative])))
    scale = float(fraction) * max(min(limits), 0.0)
    return q_arr + scale * residual


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


def test_graph_f0_recovers_clean_chart_on_nonuniform_grid():
    grid = _grid(alpha_grid=2.0)
    _fit_x_nonuniform_grid(grid)
    x_edges = np.asarray(grid.coords[0], dtype=float)
    dx = np.diff(x_edges)
    assert float(np.max(dx) - np.min(dx)) > 1.0e-4
    eta_clean = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2), (4, 1.2e-2)),
    )
    clean_q = graph_q_from_eta(grid, eta_clean).q

    clean = project_graph_q_f0(grid, clean_q, max_mode=4, sigma=1.0)

    np.testing.assert_allclose(clean.gamma_state.eta, eta_clean, atol=1.0e-11)
    assert clean.residual_report.l2 < 1.0e-12
    assert clean.residual_report.total_volume_abs < 1.0e-14
    assert clean.constraint_report["column_residual_linf"] < 1.0e-13
    assert clean.validity_report["stage"] == "F0"


def test_graph_f1_recovers_truncated_low_mode_on_nonuniform_grid():
    grid = _grid(alpha_grid=2.0)
    _fit_x_nonuniform_grid(grid)
    x_edges = np.asarray(grid.coords[0], dtype=float)
    eta_low = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2), (4, 2.0e-4)),
    )
    q_low = graph_q_from_eta(grid, eta_low).q

    f0 = project_graph_q_f0(grid, q_low, max_mode=2, sigma=1.0)
    f1 = project_graph_q_f1_low_mode(
        grid,
        q_low,
        f0_max_mode=2,
        correction_max_mode=4,
        sigma=1.0,
    )

    assert f0.residual_report.l2 > 1.0e-5
    assert f1.stage == "F1"
    assert f1.validity_report["force_admissible"] is False
    assert f1.residual_report.l2 < 1.0e-2 * f0.residual_report.l2
    np.testing.assert_allclose(f1.gamma_state.eta, eta_low, atol=5.0e-7)
    assert abs(f1.gamma_state.coefficient_map()["cos_4"] - 2.0e-4) < 5.0e-7


def test_graph_f1_does_not_turn_zero_column_residual_into_shape_modes():
    grid = _grid(alpha_grid=2.0)
    _fit_x_nonuniform_grid(grid)
    x_edges = np.asarray(grid.coords[0], dtype=float)
    eta_clean = eta_from_cosine_modes(
        x_edges,
        base_height=0.455,
        modes=((2, 4.0e-2),),
    )
    clean_q = graph_q_from_eta(grid, eta_clean).q
    high_q = _zero_column_cell_residual(grid, clean_q, fraction=5.0e-2)

    f0 = project_graph_q_f0(grid, high_q, max_mode=4, sigma=1.0)
    f1 = project_graph_q_f1_low_mode(
        grid,
        high_q,
        f0_max_mode=4,
        correction_max_mode=4,
        sigma=1.0,
    )

    assert f1.residual_report.l2 >= 0.99 * f0.residual_report.l2
    f0_coeffs = f0.gamma_state.coefficient_map()
    f1_coeffs = f1.gamma_state.coefficient_map()
    for key, value in f0_coeffs.items():
        if key == "mean":
            continue
        assert abs(float(f1_coeffs[key]) - float(value)) < 1.0e-10


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


def test_closed_polygon_area_length_and_gradients_match_finite_difference():
    theta = np.linspace(0.0, 2.0 * np.pi, 96, endpoint=False)
    state = closed_radial_chart_from_modes(
        theta,
        center=(0.5, 0.5),
        base_radius=0.22,
        modes=((2, 2.0e-2),),
    )
    geometry = closed_polygon_geometry(state.vertices, sigma=1.0)
    direction = np.stack(
        (np.cos(3.0 * theta), np.sin(5.0 * theta)),
        axis=-1,
    )
    eps = 1.0e-7
    plus = np.asarray(state.vertices) + eps * direction
    minus = np.asarray(state.vertices) - eps * direction
    geo_plus = closed_polygon_geometry(plus, sigma=1.0)
    geo_minus = closed_polygon_geometry(minus, sigma=1.0)

    fd_length = (float(geo_plus.length) - float(geo_minus.length)) / (2.0 * eps)
    fd_area = (float(geo_plus.area) - float(geo_minus.area)) / (2.0 * eps)
    grad_length = float(np.sum(np.asarray(geometry.surface_gradient) * direction))
    grad_area = float(np.sum(np.asarray(geometry.area_gradient) * direction))

    assert abs(fd_length - grad_length) < 1.0e-7
    assert abs(fd_area - grad_area) < 1.0e-9


def test_closed_radial_chart_and_polygon_geometry_have_batched_scalar_parity():
    theta = np.linspace(0.0, 2.0 * np.pi, 96, endpoint=False)
    centers = np.array(((0.5, 0.5), (0.48, 0.52)))
    base_radii = np.array((0.22, 0.19))
    modes = ((2, 1.5e-2),)

    batched_state = closed_radial_chart_from_modes(
        theta,
        center=centers,
        base_radius=base_radii,
        modes=modes,
    )
    batched_geometry = closed_polygon_geometry(batched_state.vertices, sigma=1.0)

    for batch_index, (center, base_radius) in enumerate(zip(centers, base_radii)):
        scalar_state = closed_radial_chart_from_modes(
            theta,
            center=center,
            base_radius=float(base_radius),
            modes=modes,
        )
        scalar_geometry = closed_polygon_geometry(scalar_state.vertices, sigma=1.0)

        np.testing.assert_allclose(batched_state.vertices[batch_index], scalar_state.vertices)
        np.testing.assert_allclose(batched_state.radius[batch_index], scalar_state.radius)
        np.testing.assert_allclose(batched_geometry.area[batch_index], scalar_geometry.area)
        np.testing.assert_allclose(batched_geometry.length[batch_index], scalar_geometry.length)
        np.testing.assert_allclose(
            batched_geometry.surface_gradient[batch_index],
            scalar_geometry.surface_gradient,
        )
        np.testing.assert_allclose(
            batched_geometry.area_gradient[batch_index],
            scalar_geometry.area_gradient,
        )


def test_closed_radial_q_area_and_mode2_restoring_action():
    grid = _grid(96, 96)
    theta = np.linspace(0.0, 2.0 * np.pi, 192, endpoint=False)
    circle = closed_radial_chart_from_modes(
        theta,
        center=(0.5, 0.5),
        base_radius=0.22,
        modes=(),
    )
    state = closed_radial_chart_from_modes(
        theta,
        center=(0.5, 0.5),
        base_radius=0.22,
        modes=((2, 2.0e-2),),
    )
    q_measure = closed_radial_q_from_chart(grid, state)
    geometry = closed_polygon_geometry(state.vertices, sigma=1.0)
    circle_geometry = closed_polygon_geometry(circle.vertices, sigma=1.0)

    assert abs(float(np.sum(q_measure.q)) - float(geometry.area)) < 8.0e-4
    assert float(geometry.length) > float(circle_geometry.length)
    assert closed_mode_restoring_action(geometry, state.vertices, state.theta, mode=2) < 0.0


def test_closed_radial_mode_projection_splits_high_residual():
    grid = _grid(96, 96)
    theta = np.linspace(0.0, 2.0 * np.pi, 192, endpoint=False)
    state = closed_radial_chart_from_modes(
        theta,
        center=(0.5, 0.5),
        base_radius=0.22,
        modes=((2, 1.6e-2),),
    )
    q_base = closed_radial_q_from_chart(grid, state).q
    q_high = _closed_high_residual(grid, q_base, mode=2, fraction=5.0e-2)

    clean = project_closed_radial_mode_f0(
        grid,
        q_base,
        center=(0.5, 0.5),
        mode=2,
        theta_count=192,
    )
    high = project_closed_radial_mode_f0(
        grid,
        q_high,
        center=(0.5, 0.5),
        mode=2,
        theta_count=192,
    )

    assert clean.chart_kind == "closed_radial"
    assert clean.residual_report.total_volume_abs < 1.0e-3
    assert high.residual_report.l2 > clean.residual_report.l2
    assert high.residual_report.total_volume_abs < 1.0e-3
    assert abs(
        high.gamma_state.coefficient_map()["cos_2"]
        - clean.gamma_state.coefficient_map()["cos_2"]
    ) < 3.0e-4
