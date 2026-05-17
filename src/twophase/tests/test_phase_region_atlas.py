"""Tests for PhaseRegion InterfaceAtlas schema validation."""

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
    component_offsets_from_batch_ids,
    enum_values,
)


def _atlas() -> InterfaceAtlas:
    component_to_batch = np.array((0, 0), dtype=np.int64)
    return InterfaceAtlas(
        batch_size=1,
        component_offsets=component_offsets_from_batch_ids(1, component_to_batch),
        component_to_batch=component_to_batch,
        chart_type=enum_values((ChartType.CLOSED_RADIAL, ChartType.GRAPH)),
        topology=enum_values((TopologyType.CLOSED, TopologyType.GRAPH_PERIODIC)),
        attachment=enum_values((BoundaryAttachment.NONE, BoundaryAttachment.TOP)),
        orientation=np.array((1.0, -1.0)),
        phase_role=enum_values((PhaseRole.GAS_INSIDE, PhaseRole.GAS_ABOVE)),
        constraint_policy=enum_values(
            (ConstraintPolicy.COMPONENT_VOLUME, ConstraintPolicy.TOTAL_VOLUME)
        ),
        dof_offsets=np.array((0, 3, 7), dtype=np.int64),
        vertex_offsets=np.array((0, 4, 9), dtype=np.int64),
        active_cell_offsets=np.array((0, 5, 11), dtype=np.int64),
    )


def test_phase_region_batch_accepts_closed_bubble_plus_top_layer_schema():
    atlas = _atlas()
    region = PhaseRegionBatch(
        atlas=atlas,
        dofs=np.linspace(0.1, 0.7, 7),
        vertices=np.arange(18, dtype=float).reshape(9, 2) * 1.0e-2,
        active_cell_ids=np.arange(11, dtype=np.int64),
        active_weights=np.linspace(1.0, 2.0, 11),
        metric_epoch=3,
    )

    assert atlas.n_components == 2
    assert region.batch_size == 1
    assert region.n_components == 2
    np.testing.assert_array_equal(atlas.component_counts_by_batch(), np.array((2,)))
    np.testing.assert_array_equal(atlas.component_indices_for_chart(ChartType.GRAPH), np.array((1,)))
    np.testing.assert_allclose(region.dofs_for_component(0), np.linspace(0.1, 0.7, 7)[:3])
    np.testing.assert_allclose(
        region.vertices_for_component(1),
        np.arange(18, dtype=float).reshape(9, 2)[4:] * 1.0e-2,
    )
    ids, weights = region.active_cells_for_component(1)
    np.testing.assert_array_equal(ids, np.arange(5, 11, dtype=np.int64))
    np.testing.assert_allclose(weights, np.linspace(1.0, 2.0, 11)[5:])


def test_component_offsets_require_batch_sorted_components():
    component_to_batch = np.array((0, 1, 0), dtype=np.int64)

    with pytest.raises(AtlasValidationError, match="sorted by batch"):
        component_offsets_from_batch_ids(2, component_to_batch)

    with pytest.raises(AtlasValidationError, match="integer-valued"):
        component_offsets_from_batch_ids(2, np.array((0.0, 0.5)))


def test_atlas_rejects_closed_component_with_boundary_attachment():
    atlas = _atlas()

    with pytest.raises(AtlasValidationError, match="closed components"):
        InterfaceAtlas(
            batch_size=atlas.batch_size,
            component_offsets=atlas.component_offsets,
            component_to_batch=atlas.component_to_batch,
            chart_type=atlas.chart_type,
            topology=atlas.topology,
            attachment=enum_values((BoundaryAttachment.TOP, BoundaryAttachment.TOP)),
            orientation=atlas.orientation,
            phase_role=atlas.phase_role,
            constraint_policy=atlas.constraint_policy,
            dof_offsets=atlas.dof_offsets,
            vertex_offsets=atlas.vertex_offsets,
            active_cell_offsets=atlas.active_cell_offsets,
        )


def test_atlas_rejects_offsets_that_do_not_match_packed_arrays():
    atlas = _atlas()

    with pytest.raises(AtlasValidationError, match="dof_offsets end"):
        PhaseRegionBatch(
            atlas=atlas,
            dofs=np.linspace(0.1, 0.6, 6),
            vertices=np.arange(18, dtype=float).reshape(9, 2),
            active_cell_ids=np.arange(11, dtype=np.int64),
            active_weights=np.ones(11),
        )


def test_atlas_rejects_non_unit_orientation_and_bad_vertex_shape():
    atlas = _atlas()

    with pytest.raises(AtlasValidationError, match="orientation"):
        InterfaceAtlas(
            batch_size=atlas.batch_size,
            component_offsets=atlas.component_offsets,
            component_to_batch=atlas.component_to_batch,
            chart_type=atlas.chart_type,
            topology=atlas.topology,
            attachment=atlas.attachment,
            orientation=np.array((1.0, 0.0)),
            phase_role=atlas.phase_role,
            constraint_policy=atlas.constraint_policy,
            dof_offsets=atlas.dof_offsets,
            vertex_offsets=atlas.vertex_offsets,
            active_cell_offsets=atlas.active_cell_offsets,
        )

    with pytest.raises(AtlasValidationError, match="vertices"):
        PhaseRegionBatch(
            atlas=atlas,
            dofs=np.linspace(0.1, 0.7, 7),
            vertices=np.arange(9, dtype=float),
            active_cell_ids=np.arange(11, dtype=np.int64),
            active_weights=np.ones(11),
        )
