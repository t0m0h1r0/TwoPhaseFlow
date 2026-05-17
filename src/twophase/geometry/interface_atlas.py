"""Phase-region interface atlas schema.

Symbol mapping
--------------
``Omega_g`` -> gas phase region owned by ``PhaseRegionBatch``.
``Gamma`` -> boundary components stored by ``InterfaceAtlas``.
``R_h`` -> finite-dimensional phase-region state.
``q_phys`` -> future ``Q_h(R_h)`` cell measure; not stored here.
``r`` -> future off-manifold residual; not stored here.

This module is a schema and validation layer only.  It does not reconstruct a
level-set field, compute ``Q_h``, transport volume, build capillary forces, or
project pressure/velocity.  Components are packed by batch so later kernels can
use chart-grouped vector operations and segment reductions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable

import numpy as np


class AtlasValidationError(ValueError):
    """Raised when a phase-region atlas violates its declared stratum."""


class ChartType(IntEnum):
    """Interface chart kernel used by one atlas component."""

    GRAPH = 1
    CLOSED_RADIAL = 2
    OPEN_CURVE = 3
    LOCAL_PLIC = 4


class TopologyType(IntEnum):
    """Topological stratum of one atlas component."""

    CLOSED = 1
    OPEN = 2
    GRAPH_PERIODIC = 3
    LOCAL_FRAGMENT = 4


class BoundaryAttachment(IntEnum):
    """Boundary attachment declared by one atlas component."""

    NONE = 0
    TOP = 1
    BOTTOM = 2
    LEFT = 3
    RIGHT = 4
    PERIODIC_X = 5
    PERIODIC_Y = 6
    WALL = 7


class PhaseRole(IntEnum):
    """Which side of a chart belongs to the gas phase."""

    GAS_INSIDE = 1
    GAS_OUTSIDE = 2
    GAS_ABOVE = 3
    GAS_BELOW = 4


class ConstraintPolicy(IntEnum):
    """Volume constraint declared for one component."""

    NONE = 0
    TOTAL_VOLUME = 1
    COMPONENT_VOLUME = 2
    DIAGNOSTIC_ONLY = 3


@dataclass(frozen=True)
class InterfaceAtlas:
    """Packed component metadata for one batched phase-region atlas.

    Args:
        batch_size: Number of phase-region entries.
        component_offsets: Monotone offsets of components by batch, shape
            ``(batch_size + 1,)``.
        component_to_batch: Batch id for each component, shape
            ``(n_components,)``.  Components must be packed by batch.
        chart_type: ``ChartType`` label for each component.
        topology: ``TopologyType`` label for each component.
        attachment: ``BoundaryAttachment`` label for each component.
        orientation: Gas-side orientation sign for each component; must be
            exactly ``+1`` or ``-1``.
        phase_role: ``PhaseRole`` label for each component.
        constraint_policy: ``ConstraintPolicy`` label for each component.
        dof_offsets: Monotone offsets into the packed dof array.
        vertex_offsets: Monotone offsets into the packed vertex array.
        active_cell_offsets: Monotone offsets into packed active-cell arrays.
    """

    batch_size: int
    component_offsets: object
    component_to_batch: object
    chart_type: object
    topology: object
    attachment: object
    orientation: object
    phase_role: object
    constraint_policy: object
    dof_offsets: object
    vertex_offsets: object
    active_cell_offsets: object

    def __post_init__(self) -> None:
        batch_size = int(self.batch_size)
        if batch_size <= 0:
            raise AtlasValidationError("batch_size must be positive")
        object.__setattr__(self, "batch_size", batch_size)

        component_to_batch = _as_int_1d(self.component_to_batch, "component_to_batch")
        n_components = int(component_to_batch.size)
        if n_components == 0:
            raise AtlasValidationError("InterfaceAtlas requires at least one component")
        if np.any(component_to_batch < 0) or np.any(component_to_batch >= batch_size):
            raise AtlasValidationError("component_to_batch entries must be valid batch ids")

        component_offsets = _as_offset_array(
            self.component_offsets,
            "component_offsets",
            expected_size=batch_size + 1,
            expected_end=n_components,
        )
        expected_to_batch = np.empty(n_components, dtype=np.int64)
        for batch_index in range(batch_size):
            lo = int(component_offsets[batch_index])
            hi = int(component_offsets[batch_index + 1])
            expected_to_batch[lo:hi] = batch_index
        if not np.array_equal(component_to_batch, expected_to_batch):
            raise AtlasValidationError(
                "components must be packed by batch and match component_offsets"
            )

        chart_type = _as_enum_array(self.chart_type, ChartType, "chart_type", n_components)
        topology = _as_enum_array(self.topology, TopologyType, "topology", n_components)
        attachment = _as_enum_array(
            self.attachment,
            BoundaryAttachment,
            "attachment",
            n_components,
        )
        phase_role = _as_enum_array(self.phase_role, PhaseRole, "phase_role", n_components)
        constraint_policy = _as_enum_array(
            self.constraint_policy,
            ConstraintPolicy,
            "constraint_policy",
            n_components,
        )
        orientation = _as_float_1d(self.orientation, "orientation", n_components)
        if not np.all(np.isfinite(orientation)):
            raise AtlasValidationError("orientation entries must be finite")
        if not np.all(np.isin(orientation, (-1.0, 1.0))):
            raise AtlasValidationError("orientation entries must be +1 or -1")

        dof_offsets = _as_offset_array(
            self.dof_offsets,
            "dof_offsets",
            expected_size=n_components + 1,
        )
        vertex_offsets = _as_offset_array(
            self.vertex_offsets,
            "vertex_offsets",
            expected_size=n_components + 1,
        )
        active_cell_offsets = _as_offset_array(
            self.active_cell_offsets,
            "active_cell_offsets",
            expected_size=n_components + 1,
        )

        _validate_chart_topology(chart_type, topology, attachment, phase_role)

        object.__setattr__(self, "component_offsets", component_offsets)
        object.__setattr__(self, "component_to_batch", component_to_batch)
        object.__setattr__(self, "chart_type", chart_type)
        object.__setattr__(self, "topology", topology)
        object.__setattr__(self, "attachment", attachment)
        object.__setattr__(self, "orientation", orientation)
        object.__setattr__(self, "phase_role", phase_role)
        object.__setattr__(self, "constraint_policy", constraint_policy)
        object.__setattr__(self, "dof_offsets", dof_offsets)
        object.__setattr__(self, "vertex_offsets", vertex_offsets)
        object.__setattr__(self, "active_cell_offsets", active_cell_offsets)

    @property
    def n_components(self) -> int:
        """Number of atlas components."""
        return int(self.component_to_batch.size)

    def component_slice_for_batch(self, batch_index: int) -> slice:
        """Return the packed component slice owned by one batch entry."""
        batch = int(batch_index)
        if batch < 0 or batch >= self.batch_size:
            raise IndexError("batch_index out of range")
        return slice(int(self.component_offsets[batch]), int(self.component_offsets[batch + 1]))

    def dof_slice(self, component_index: int) -> slice:
        """Return the packed dof slice for one component."""
        return _component_offset_slice(self.dof_offsets, component_index, self.n_components)

    def vertex_slice(self, component_index: int) -> slice:
        """Return the packed vertex slice for one component."""
        return _component_offset_slice(self.vertex_offsets, component_index, self.n_components)

    def active_cell_slice(self, component_index: int) -> slice:
        """Return the packed active-cell slice for one component."""
        return _component_offset_slice(
            self.active_cell_offsets,
            component_index,
            self.n_components,
        )

    def component_indices_for_chart(self, chart: ChartType | int) -> object:
        """Return component indices that use one chart type."""
        return np.flatnonzero(self.chart_type == int(chart))

    def component_counts_by_batch(self) -> object:
        """Return a vectorized component count for each batch entry."""
        return np.diff(self.component_offsets)


@dataclass(frozen=True)
class PhaseRegionBatch:
    """Finite-dimensional phase-region state with packed chart data.

    ``PhaseRegionBatch`` owns the discrete region state ``R_h``.  The packed
    arrays are intentionally independent of any particular measurement or
    force implementation, so later modules can build ``Q_h(R_h)``, perimeter
    sums, and residual diagnostics without changing ownership.
    """

    atlas: InterfaceAtlas
    dofs: object
    vertices: object
    active_cell_ids: object
    active_weights: object
    metric_epoch: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.atlas, InterfaceAtlas):
            raise AtlasValidationError("atlas must be an InterfaceAtlas")
        dofs = np.asarray(self.dofs, dtype=float)
        if dofs.ndim != 1:
            raise AtlasValidationError("dofs must be a one-dimensional packed array")
        vertices = np.asarray(self.vertices, dtype=float)
        if vertices.ndim != 2 or vertices.shape[-1] != 2:
            raise AtlasValidationError("vertices must have shape (n_vertices, 2)")
        active_cell_ids = _as_int_1d(self.active_cell_ids, "active_cell_ids")
        active_weights = np.asarray(self.active_weights, dtype=float)
        if active_weights.ndim != 1:
            raise AtlasValidationError("active_weights must be one-dimensional")
        if active_cell_ids.size != active_weights.size:
            raise AtlasValidationError("active_cell_ids and active_weights must have same size")
        if not np.all(np.isfinite(dofs)):
            raise AtlasValidationError("dofs must be finite")
        if not np.all(np.isfinite(vertices)):
            raise AtlasValidationError("vertices must be finite")
        if not np.all(np.isfinite(active_weights)):
            raise AtlasValidationError("active_weights must be finite")
        if int(self.atlas.dof_offsets[-1]) != dofs.size:
            raise AtlasValidationError("dof_offsets end must equal len(dofs)")
        if int(self.atlas.vertex_offsets[-1]) != vertices.shape[0]:
            raise AtlasValidationError("vertex_offsets end must equal number of vertices")
        if int(self.atlas.active_cell_offsets[-1]) != active_cell_ids.size:
            raise AtlasValidationError(
                "active_cell_offsets end must equal len(active_cell_ids)"
            )
        if int(self.metric_epoch) < 0:
            raise AtlasValidationError("metric_epoch must be nonnegative")

        object.__setattr__(self, "dofs", dofs)
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "active_cell_ids", active_cell_ids)
        object.__setattr__(self, "active_weights", active_weights)
        object.__setattr__(self, "metric_epoch", int(self.metric_epoch))

    @property
    def batch_size(self) -> int:
        """Number of phase-region entries."""
        return self.atlas.batch_size

    @property
    def n_components(self) -> int:
        """Number of atlas components."""
        return self.atlas.n_components

    def dofs_for_component(self, component_index: int) -> object:
        """Return the packed dofs for one component."""
        return self.dofs[self.atlas.dof_slice(component_index)]

    def vertices_for_component(self, component_index: int) -> object:
        """Return the packed vertices for one component."""
        return self.vertices[self.atlas.vertex_slice(component_index)]

    def active_cells_for_component(self, component_index: int) -> tuple[object, object]:
        """Return active cell ids and weights for one component."""
        slc = self.atlas.active_cell_slice(component_index)
        return self.active_cell_ids[slc], self.active_weights[slc]


def component_offsets_from_batch_ids(batch_size: int, component_to_batch: object) -> object:
    """Build packed component offsets from already-sorted batch ids."""
    batch = int(batch_size)
    ids = _as_int_1d(component_to_batch, "component_to_batch")
    if batch <= 0:
        raise AtlasValidationError("batch_size must be positive")
    if ids.size == 0:
        raise AtlasValidationError("component_to_batch cannot be empty")
    if np.any(ids < 0) or np.any(ids >= batch):
        raise AtlasValidationError("component_to_batch entries must be valid batch ids")
    if np.any(np.diff(ids) < 0):
        raise AtlasValidationError("component_to_batch must be sorted by batch")
    counts = np.bincount(ids, minlength=batch)
    return np.concatenate(([0], np.cumsum(counts))).astype(np.int64)


def _as_int_1d(values: object, name: str) -> object:
    raw = np.asarray(values)
    if raw.ndim != 1:
        raise AtlasValidationError(f"{name} must be one-dimensional")
    numeric = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(numeric)):
        raise AtlasValidationError(f"{name} entries must be finite")
    if not np.allclose(numeric, np.rint(numeric), rtol=0.0, atol=0.0):
        raise AtlasValidationError(f"{name} entries must be integer-valued")
    return numeric.astype(np.int64)


def _as_float_1d(values: object, name: str, expected_size: int) -> object:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or arr.size != int(expected_size):
        raise AtlasValidationError(f"{name} must have shape ({int(expected_size)},)")
    return arr


def _as_enum_array(
    values: object,
    enum_type: type[IntEnum],
    name: str,
    expected_size: int,
) -> object:
    arr = _as_int_1d(values, name)
    if arr.size != int(expected_size):
        raise AtlasValidationError(f"{name} must have shape ({int(expected_size)},)")
    allowed = np.asarray([int(entry) for entry in enum_type], dtype=np.int64)
    if not np.all(np.isin(arr, allowed)):
        raise AtlasValidationError(f"{name} contains unknown labels")
    return arr


def _as_offset_array(
    values: object,
    name: str,
    *,
    expected_size: int,
    expected_end: int | None = None,
) -> object:
    arr = _as_int_1d(values, name)
    if arr.size != int(expected_size):
        raise AtlasValidationError(f"{name} must have shape ({int(expected_size)},)")
    if int(arr[0]) != 0:
        raise AtlasValidationError(f"{name} must start at zero")
    if np.any(np.diff(arr) < 0):
        raise AtlasValidationError(f"{name} must be monotone")
    if expected_end is not None and int(arr[-1]) != int(expected_end):
        raise AtlasValidationError(f"{name} must end at {int(expected_end)}")
    return arr


def _component_offset_slice(offsets: object, component_index: int, n_components: int) -> slice:
    component = int(component_index)
    if component < 0 or component >= int(n_components):
        raise IndexError("component_index out of range")
    return slice(int(offsets[component]), int(offsets[component + 1]))


def _validate_chart_topology(
    chart_type: object,
    topology: object,
    attachment: object,
    phase_role: object,
) -> None:
    closed = topology == int(TopologyType.CLOSED)
    if np.any(closed & (attachment != int(BoundaryAttachment.NONE))):
        raise AtlasValidationError("closed components must not declare boundary attachment")
    if np.any((chart_type == int(ChartType.CLOSED_RADIAL)) & ~closed):
        raise AtlasValidationError("closed radial charts require CLOSED topology")
    if np.any((chart_type == int(ChartType.GRAPH)) & closed):
        raise AtlasValidationError("graph charts must not declare CLOSED topology")
    graph_or_open = (chart_type == int(ChartType.GRAPH)) | (chart_type == int(ChartType.OPEN_CURVE))
    if np.any(graph_or_open & (attachment == int(BoundaryAttachment.NONE))):
        raise AtlasValidationError("graph/open components must declare boundary attachment")
    allowed_open_roles = np.isin(
        phase_role,
        (int(PhaseRole.GAS_ABOVE), int(PhaseRole.GAS_BELOW)),
    )
    if np.any(graph_or_open & ~allowed_open_roles):
        raise AtlasValidationError("graph/open components require GAS_ABOVE or GAS_BELOW")
    if np.any((chart_type == int(ChartType.LOCAL_PLIC)) & (topology != int(TopologyType.LOCAL_FRAGMENT))):
        raise AtlasValidationError("local PLIC charts require LOCAL_FRAGMENT topology")


def enum_values(entries: Iterable[IntEnum]) -> object:
    """Return enum values as an integer array for vectorized fixtures."""
    return np.asarray([int(entry) for entry in entries], dtype=np.int64)
