"""Trace velocity maps and VJPs for closed-interface capillarity.

Symbol mapping
--------------
``C_K`` -> :class:`ReconstructedNodalP1TraceVelocityMap`
``u_f`` -> face velocity components
``delta z`` -> trace vertex velocities
``C_K^T g_z`` -> face covector pullback
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..core.boundary import is_periodic_axis
from ..simulation.face_projection import reconstruct_nodes_from_faces
from .closed_interface_trace import TraceGraph2D


@dataclass(frozen=True)
class ReconstructedNodalP1TraceVelocityMap:
    """P1 trace velocity map through reconstructed nodal vector velocity."""

    grid: Any
    bc_type: str = "wall"

    def vertex_velocities(
        self,
        *,
        xp,
        graph: TraceGraph2D,
        face_components,
    ) -> dict[int, np.ndarray]:
        """Return ``C_K u_f`` as host vertex vectors."""
        nodal_components = reconstruct_nodes_from_faces(
            xp,
            self.grid,
            [xp.asarray(component) for component in face_components],
            self.bc_type,
        )
        nodal_host = [np.asarray(_to_host(xp, component)) for component in nodal_components]
        velocities: dict[int, np.ndarray] = {}
        for vertex in graph.vertices:
            lo, hi = vertex.node_indices
            alpha = float(vertex.alpha)
            velocities[vertex.index] = np.asarray(
                [
                    (1.0 - alpha) * nodal_host[0][lo] + alpha * nodal_host[0][hi],
                    (1.0 - alpha) * nodal_host[1][lo] + alpha * nodal_host[1][hi],
                ],
                dtype=float,
            )
        return velocities

    def pullback_vertex_covectors(
        self,
        *,
        xp,
        graph: TraceGraph2D,
        vertex_covectors: dict[int, np.ndarray],
        dtype=None,
    ) -> list[Any]:
        """Return ``C_K^T g_z`` on face components."""
        if dtype is None:
            dtype = float
        nodal_covectors = [
            np.zeros(tuple(self.grid.shape), dtype=float),
            np.zeros(tuple(self.grid.shape), dtype=float),
        ]
        for vertex in graph.vertices:
            covector = np.asarray(vertex_covectors[vertex.index], dtype=float)
            lo, hi = vertex.node_indices
            alpha = float(vertex.alpha)
            nodal_covectors[0][lo] += (1.0 - alpha) * covector[0]
            nodal_covectors[0][hi] += alpha * covector[0]
            nodal_covectors[1][lo] += (1.0 - alpha) * covector[1]
            nodal_covectors[1][hi] += alpha * covector[1]
        return [
            xp.asarray(
                _transpose_reconstruct_nodes_component(
                    self.grid,
                    nodal_covectors[axis],
                    axis,
                    self.bc_type,
                ),
                dtype=dtype,
            )
            for axis in range(2)
        ]


def face_vertex_vjp_residual(
    *,
    xp,
    graph: TraceGraph2D,
    trace_velocity_map: ReconstructedNodalP1TraceVelocityMap,
    face_components,
    vertex_covectors: dict[int, np.ndarray],
    face_covectors=None,
) -> float:
    """Return relative residual of ``<g,C_K u> = <C_K^T g,u>``."""
    velocities = trace_velocity_map.vertex_velocities(
        xp=xp,
        graph=graph,
        face_components=face_components,
    )
    left = 0.0
    for index, covector in vertex_covectors.items():
        left += float(np.dot(covector, velocities[index]))
    if face_covectors is None:
        face_covectors = trace_velocity_map.pullback_vertex_covectors(
            xp=xp,
            graph=graph,
            vertex_covectors=vertex_covectors,
            dtype=xp.asarray(face_components[0]).dtype,
        )
    right = 0.0
    for covector, velocity in zip(face_covectors, face_components, strict=True):
        right += float(
            np.sum(
                np.asarray(_to_host(xp, covector))
                * np.asarray(_to_host(xp, velocity))
            )
        )
    denominator = abs(left) + abs(right) + 1.0e-30
    return abs(left - right) / denominator


def _transpose_reconstruct_nodes_component(
    grid,
    nodal_covector: np.ndarray,
    axis: int,
    bc_type: str,
):
    shape = list(grid.shape)
    shape[axis] = grid.N[axis]
    face_covector = np.zeros(tuple(shape), dtype=float)
    n_cells = grid.N[axis]
    periodic = is_periodic_axis(bc_type, axis, grid.ndim)
    nodal = np.array(nodal_covector, copy=True, dtype=float)
    if periodic:
        nodal[_sl(axis, 0, 1, grid.ndim)] += nodal[
            _sl(axis, n_cells, n_cells + 1, grid.ndim)
        ]
        nodal[_sl(axis, n_cells, n_cells + 1, grid.ndim)] = 0.0
        for face_index in range(n_cells):
            current_node = face_index
            next_node = 0 if face_index + 1 == n_cells else face_index + 1
            face_covector[_sl(axis, face_index, face_index + 1, grid.ndim)] = 0.5 * (
                nodal[_sl(axis, current_node, current_node + 1, grid.ndim)]
                + nodal[_sl(axis, next_node, next_node + 1, grid.ndim)]
            )
        return face_covector
    for face_index in range(n_cells):
        value = np.zeros_like(face_covector[_sl(axis, face_index, face_index + 1, grid.ndim)])
        if face_index == 0:
            value += nodal[_sl(axis, 0, 1, grid.ndim)]
        else:
            value += 0.5 * nodal[_sl(axis, face_index, face_index + 1, grid.ndim)]
        if face_index == n_cells - 1:
            value += nodal[_sl(axis, n_cells, n_cells + 1, grid.ndim)]
        else:
            value += 0.5 * nodal[_sl(axis, face_index + 1, face_index + 2, grid.ndim)]
        face_covector[_sl(axis, face_index, face_index + 1, grid.ndim)] = value
    return face_covector


def _sl(axis: int, start: int, stop: int, ndim: int) -> tuple[slice, ...]:
    slices = [slice(None)] * ndim
    slices[axis] = slice(start, stop)
    return tuple(slices)


def _to_host(xp, array):
    if hasattr(xp, "asnumpy"):
        return xp.asnumpy(array)
    return array
