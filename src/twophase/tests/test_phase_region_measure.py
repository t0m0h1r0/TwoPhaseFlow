"""Tests for PhaseRegion component-measure reductions."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.geometry import (
    AtlasValidationError,
    BoundaryAttachment,
    ChartType,
    ConstraintPolicy,
    InterfaceAtlas,
    PhaseRegionBatch,
    PhaseRole,
    TopologyType,
    assemble_phase_region_measurement,
    component_offsets_from_batch_ids,
    enum_values,
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

    with pytest.raises(AtlasValidationError, match="q_target shape"):
        assemble_phase_region_measurement(
            region,
            component_q,
            np.ones(3),
            q_target=np.ones((3, 3)),
        )

