"""Tests for PhaseRegion component-measure reductions."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.geometry import (
    AtlasValidationError,
    BoundaryAttachment,
    CellMeasurePhase,
    ChartType,
    ConstraintPolicy,
    InterfaceAtlas,
    PhaseRegionBatch,
    PhaseRole,
    TopologyType,
    assemble_phase_region_measurement,
    component_offsets_from_batch_ids,
    enum_values,
    graph_q_from_eta,
    graph_segment_energy_gradient,
    map_cell_measure_to_phase_owner,
)


def _region_for_three_components() -> PhaseRegionBatch:
    component_to_batch = np.array((0, 0, 1), dtype=np.int64)
    atlas = InterfaceAtlas(
        batch_size=2,
        component_offsets=component_offsets_from_batch_ids(2, component_to_batch),
        component_to_batch=component_to_batch,
        chart_type=enum_values((ChartType.CLOSED_RADIAL, ChartType.GRAPH, ChartType.GRAPH)),
        topology=enum_values(
            (TopologyType.CLOSED, TopologyType.GRAPH_PERIODIC, TopologyType.GRAPH_PERIODIC)
        ),
        attachment=enum_values(
            (BoundaryAttachment.NONE, BoundaryAttachment.TOP, BoundaryAttachment.TOP)
        ),
        orientation=np.array((1.0, -1.0, -1.0)),
        phase_role=enum_values(
            (PhaseRole.GAS_INSIDE, PhaseRole.GAS_ABOVE, PhaseRole.GAS_ABOVE)
        ),
        constraint_policy=enum_values(
            (
                ConstraintPolicy.COMPONENT_VOLUME,
                ConstraintPolicy.TOTAL_VOLUME,
                ConstraintPolicy.TOTAL_VOLUME,
            )
        ),
        dof_offsets=np.array((0, 2, 5, 8), dtype=np.int64),
        vertex_offsets=np.array((0, 3, 5, 7), dtype=np.int64),
        active_cell_offsets=np.array((0, 2, 5, 8), dtype=np.int64),
    )
    return PhaseRegionBatch(
        atlas=atlas,
        dofs=np.linspace(0.0, 0.7, 8),
        vertices=np.arange(14, dtype=float).reshape(7, 2),
        active_cell_ids=np.arange(8, dtype=np.int64),
        active_weights=np.ones(8),
    )


def test_assemble_phase_region_measurement_reduces_components_by_batch():
    region = _region_for_three_components()
    component_q = np.array(
        (
            [[0.10, 0.00], [0.00, 0.05]],
            [[0.00, 0.20], [0.10, 0.00]],
            [[0.30, 0.00], [0.00, 0.10]],
        ),
        dtype=float,
    )
    perimeters = np.array((1.0, 2.0, 4.0))
    target = np.stack(
        (
            component_q[0] + component_q[1] + 0.01,
            component_q[2],
        ),
        axis=0,
    )

    measurement = assemble_phase_region_measurement(
        region,
        component_q,
        perimeters,
        q_target=target,
        cell_area=np.ones((2, 2)),
    )

    np.testing.assert_allclose(measurement.q_phys[0], component_q[0] + component_q[1])
    np.testing.assert_allclose(measurement.q_phys[1], component_q[2])
    np.testing.assert_allclose(measurement.component_volumes, np.array((0.15, 0.30, 0.40)))
    np.testing.assert_allclose(measurement.batch_volumes, np.array((0.45, 0.40)))
    np.testing.assert_allclose(measurement.batch_perimeters, np.array((3.0, 4.0)))
    np.testing.assert_allclose(measurement.residual_volume, np.array((0.04, 0.0)))
    assert measurement.residual_l2 > 0.0
    assert measurement.residual_linf == pytest.approx(0.01)
    assert measurement.force_admissible is False


def test_assemble_phase_region_measurement_accepts_device_component_arrays_when_available():
    cp = pytest.importorskip("cupy")
    try:
        if cp.cuda.runtime.getDeviceCount() < 1:
            pytest.skip("CUDA device is unavailable")
    except cp.cuda.runtime.CUDARuntimeError as exc:
        pytest.skip(f"CUDA device is unavailable: {exc}")
    region = _region_for_three_components()
    component_q_cpu = np.array(
        (
            [[0.10, 0.00], [0.00, 0.05]],
            [[0.00, 0.20], [0.10, 0.00]],
            [[0.30, 0.00], [0.00, 0.10]],
        ),
        dtype=float,
    )
    perimeters_cpu = np.array((1.0, 2.0, 4.0))
    target_cpu = np.stack(
        (
            component_q_cpu[0] + component_q_cpu[1],
            component_q_cpu[2],
        ),
        axis=0,
    )

    measurement = assemble_phase_region_measurement(
        region,
        cp.asarray(component_q_cpu),
        cp.asarray(perimeters_cpu),
        q_target=cp.asarray(target_cpu),
        cell_area=cp.ones((2, 2)),
    )

    assert hasattr(measurement.q_phys, "__cuda_array_interface__")
    np.testing.assert_allclose(
        cp.asnumpy(measurement.q_phys[0]),
        component_q_cpu[0] + component_q_cpu[1],
    )
    np.testing.assert_allclose(cp.asnumpy(measurement.batch_perimeters), np.array((3.0, 4.0)))
    assert measurement.residual_l2 == pytest.approx(0.0)
    assert measurement.force_admissible is False


def test_single_batch_target_may_omit_batch_axis():
    component_to_batch = np.array((0,), dtype=np.int64)
    atlas = InterfaceAtlas(
        batch_size=1,
        component_offsets=component_offsets_from_batch_ids(1, component_to_batch),
        component_to_batch=component_to_batch,
        chart_type=enum_values((ChartType.CLOSED_RADIAL,)),
        topology=enum_values((TopologyType.CLOSED,)),
        attachment=enum_values((BoundaryAttachment.NONE,)),
        orientation=np.array((1.0,)),
        phase_role=enum_values((PhaseRole.GAS_INSIDE,)),
        constraint_policy=enum_values((ConstraintPolicy.TOTAL_VOLUME,)),
        dof_offsets=np.array((0, 1), dtype=np.int64),
        vertex_offsets=np.array((0, 3), dtype=np.int64),
        active_cell_offsets=np.array((0, 1), dtype=np.int64),
    )
    region = PhaseRegionBatch(
        atlas=atlas,
        dofs=np.array((0.2,)),
        vertices=np.zeros((3, 2)),
        active_cell_ids=np.array((0,), dtype=np.int64),
        active_weights=np.array((0.2,)),
    )
    component_q = np.array(([[0.2, 0.0], [0.0, 0.1]],))

    measurement = assemble_phase_region_measurement(
        region,
        component_q,
        np.array((1.5,)),
        q_target=component_q[0],
        cell_area=np.ones((2, 2)),
    )

    assert measurement.residual_l2 == pytest.approx(0.0)
    np.testing.assert_allclose(measurement.q_phys[0], component_q[0])


def test_gas_owner_measurement_matches_exact_liquid_complement():
    component_to_batch = np.array((0,), dtype=np.int64)
    atlas = InterfaceAtlas(
        batch_size=1,
        component_offsets=component_offsets_from_batch_ids(1, component_to_batch),
        component_to_batch=component_to_batch,
        chart_type=enum_values((ChartType.CLOSED_RADIAL,)),
        topology=enum_values((TopologyType.CLOSED,)),
        attachment=enum_values((BoundaryAttachment.NONE,)),
        orientation=np.array((-1.0,)),
        phase_role=enum_values((PhaseRole.GAS_OUTSIDE,)),
        constraint_policy=enum_values((ConstraintPolicy.TOTAL_VOLUME,)),
        dof_offsets=np.array((0, 1), dtype=np.int64),
        vertex_offsets=np.array((0, 4), dtype=np.int64),
        active_cell_offsets=np.array((0, 4), dtype=np.int64),
    )
    region = PhaseRegionBatch(
        atlas=atlas,
        dofs=np.array((0.2,)),
        vertices=np.zeros((4, 2)),
        active_cell_ids=np.arange(4, dtype=np.int64),
        active_weights=np.ones(4),
    )
    cell_area = np.array(((0.10, 0.20), (0.15, 0.25)), dtype=float)
    liquid_q = np.array(((0.03, 0.14), (0.05, 0.10)), dtype=float)
    owner_map = map_cell_measure_to_phase_owner(
        liquid_q,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
    )

    measurement = assemble_phase_region_measurement(
        region,
        owner_map.q_owner[None, ...],
        np.array((1.25,)),
        q_target=owner_map.q_owner,
        cell_area=cell_area,
    )

    np.testing.assert_allclose(measurement.q_phys[0], cell_area - liquid_q)
    assert measurement.batch_volumes[0] == pytest.approx(float(np.sum(cell_area - liquid_q)))
    assert owner_map.complement_used is True
    assert measurement.residual_l2 == pytest.approx(0.0)
    assert measurement.capacity_excess_linf <= 0.0
    assert measurement.force_admissible is False


def test_graph_gas_above_phase_region_matches_exact_capillary_complement_on_nonuniform_grid():
    grid = Grid(
        GridConfig(ndim=2, N=(8, 7), L=(0.02, 0.02), alpha_grid=1.0),
        Backend(use_gpu=False),
    )
    grid.coords[0] = 0.02 * np.array((0.0, 0.04, 0.13, 0.25, 0.43, 0.58, 0.73, 0.89, 1.0))
    grid.coords[1] = 0.02 * np.array((0.0, 0.08, 0.19, 0.37, 0.56, 0.72, 0.90, 1.0))
    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    mean = 0.0103
    amplitude = 1.7e-4
    mode = 2
    length = 0.02
    eta = mean + amplitude * np.cos(2.0 * np.pi * mode * x_edges / length)
    eta[-1] = eta[0]
    q_liquid = np.asarray(graph_q_from_eta(grid, eta).q, dtype=float)
    dx = np.diff(x_edges)
    dy = np.diff(y_edges)
    cell_area = dx[:, None] * dy[None, :]
    q_gas = cell_area - q_liquid
    owner = map_cell_measure_to_phase_owner(
        q_liquid,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
    )
    active_ids = np.flatnonzero(q_gas.ravel() != 0.0).astype(np.int64)
    active_weights = q_gas.ravel()[active_ids]
    component_to_batch = np.array((0,), dtype=np.int64)
    vertices = np.stack((x_edges, eta), axis=-1)
    region = PhaseRegionBatch(
        atlas=InterfaceAtlas(
            batch_size=1,
            component_offsets=component_offsets_from_batch_ids(1, component_to_batch),
            component_to_batch=component_to_batch,
            chart_type=enum_values((ChartType.GRAPH,)),
            topology=enum_values((TopologyType.GRAPH_PERIODIC,)),
            attachment=enum_values((BoundaryAttachment.TOP,)),
            orientation=np.array((-1.0,)),
            phase_role=enum_values((PhaseRole.GAS_ABOVE,)),
            constraint_policy=enum_values((ConstraintPolicy.TOTAL_VOLUME,)),
            dof_offsets=np.array((0, eta.size), dtype=np.int64),
            vertex_offsets=np.array((0, vertices.shape[0]), dtype=np.int64),
            active_cell_offsets=np.array((0, active_ids.size), dtype=np.int64),
        ),
        dofs=eta,
        vertices=vertices,
        active_cell_ids=active_ids,
        active_weights=active_weights,
    )
    energy = graph_segment_energy_gradient(x_edges, eta, sigma=0.0728)
    measurement = assemble_phase_region_measurement(
        region,
        q_gas[None, ...],
        np.array((float(energy.energy) / 0.0728,)),
        q_target=owner.q_owner,
        cell_area=cell_area,
    )
    eta_center = 0.5 * (eta[:-1] + eta[1:])
    column_height = np.sum(q_liquid, axis=1) / dx
    mode_unique = np.cos(2.0 * np.pi * mode * x_edges[:-1] / length)
    mode_nodes = np.r_[mode_unique, mode_unique[0]]
    eps = 1.0e-8
    fd_rate = (
        float(graph_segment_energy_gradient(x_edges, eta + eps * mode_nodes, sigma=0.0728).energy)
        - float(graph_segment_energy_gradient(x_edges, eta - eps * mode_nodes, sigma=0.0728).energy)
    ) / (2.0 * eps)
    exact_rate = float(np.sum(np.asarray(energy.nodal_gradient) * mode_unique))
    weights = np.asarray(energy.weights, dtype=float)
    force_density = -np.asarray(energy.nodal_gradient, dtype=float) / weights
    force_mode = float(np.sum(weights * force_density * mode_unique) / np.sum(weights * mode_unique * mode_unique))
    eta_mode = float(np.sum(weights * (eta[:-1] - mean) * mode_unique) / np.sum(weights * mode_unique * mode_unique))

    np.testing.assert_allclose(measurement.q_phys[0], q_gas, atol=1.0e-18)
    assert measurement.residual_l2 == pytest.approx(0.0, abs=1.0e-18)
    assert measurement.batch_volumes[0] == pytest.approx(float(np.sum(cell_area) - np.sum(q_liquid)), abs=1.0e-18)
    assert float(np.sum(active_weights)) == pytest.approx(float(measurement.component_volumes[0]), abs=1.0e-18)
    np.testing.assert_allclose(column_height, eta_center, atol=5.0e-17)
    assert abs(fd_rate - exact_rate) < 1.0e-10
    assert eta_mode * force_mode < 0.0
    assert measurement.force_admissible is False


def test_assemble_phase_region_measurement_fails_closed_on_bad_shapes_and_capacity():
    region = _region_for_three_components()
    component_q = np.ones((3, 2, 2))

    with pytest.raises(AtlasValidationError, match="component_perimeters"):
        assemble_phase_region_measurement(region, component_q, np.ones(2))

    with pytest.raises(AtlasValidationError, match="cell capacity"):
        assemble_phase_region_measurement(
            region,
            component_q,
            np.ones(3),
            cell_area=np.ones((2, 2)),
        )

    bad_negative = component_q.copy()
    bad_negative[0, 0, 0] = -1.0e-2
    with pytest.raises(AtlasValidationError, match="component_q is below zero"):
        assemble_phase_region_measurement(region, bad_negative, np.ones(3))

    bad_component_capacity = np.zeros_like(component_q)
    bad_component_capacity[0, 0, 0] = 2.0
    with pytest.raises(AtlasValidationError, match="component_q exceeds cell capacity"):
        assemble_phase_region_measurement(
            region,
            bad_component_capacity,
            np.ones(3),
            cell_area=np.ones((2, 2)),
        )

    with pytest.raises(AtlasValidationError, match="q_target shape"):
        assemble_phase_region_measurement(
            region,
            component_q,
            np.ones(3),
            q_target=np.ones((3, 3)),
        )
