"""Fixed-stratum trace graph for closed-interface capillary work.

Symbol mapping
--------------
``K`` -> :class:`~twophase.coupling.closed_interface_stratum.ClosedInterfaceStratum`
``z_e`` -> :class:`TraceVertex2D`
``Gamma_h`` -> :class:`TraceGraph2D`
``S_h`` -> :func:`trace_graph_surface_length`
``V_m`` -> :func:`trace_component_areas`

The graph is a geometry object only.  It contains no pressure, curvature, or
solver state, so the surface-energy covectors can later be pulled back through
an explicitly chosen trace velocity map.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .closed_interface_stratum import ClosedInterfaceStratum
from .closed_interface_stratum import array_to_numpy
from .closed_interface_stratum import build_closed_interface_stratum


_EDGE_CORNERS = ((0, 1), (1, 2), (2, 3), (3, 0))


@dataclass(frozen=True)
class TraceVertex2D:
    """One zero-crossing vertex on a global grid edge."""

    index: int
    edge_key: tuple[str, int, int]
    node_indices: tuple[tuple[int, int], tuple[int, int]]
    alpha: float
    point: np.ndarray


@dataclass(frozen=True)
class TraceSegment2D:
    """One fixed-stratum marching-squares segment."""

    left: int
    right: int
    cell_index: tuple[int, int]


@dataclass(frozen=True)
class TraceComponent2D:
    """One closed interface loop."""

    vertex_indices: tuple[int, ...]
    signed_area: float


@dataclass(frozen=True)
class TraceGraph2D:
    """Closed-interface trace graph on one regular stratum."""

    stratum: ClosedInterfaceStratum
    vertices: tuple[TraceVertex2D, ...]
    segments: tuple[TraceSegment2D, ...]
    components: tuple[TraceComponent2D, ...]
    phase_threshold: float


def build_trace_graph_2d(
    *,
    xp,
    grid,
    psi,
    phase_threshold: float = 0.5,
    threshold_tol: float = 0.0,
    fail_on_ambiguous: bool = True,
) -> TraceGraph2D:
    """Build a globally keyed closed trace graph for a 2-D nodal carrier."""
    if grid.ndim != 2:
        raise ValueError("build_trace_graph_2d currently supports 2D grids")
    stratum = build_closed_interface_stratum(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=float(phase_threshold),
        threshold_tol=float(threshold_tol),
    )
    if not stratum.regular:
        raise ValueError("trace graph requires a regular fixed stratum")
    psi_host = array_to_numpy(xp, xp.asarray(psi))
    vertices_by_key: dict[tuple[str, int, int], int] = {}
    vertices: list[TraceVertex2D] = []
    segments: list[TraceSegment2D] = []
    for i, j, values, points, nodes in _iter_cells(grid, psi_host):
        shifted = values - float(phase_threshold)
        inside = values >= float(phase_threshold)
        case = sum(int(flag) << bit for bit, flag in enumerate(inside))
        if case in {0, 15}:
            continue
        if fail_on_ambiguous and case in {5, 10}:
            raise ValueError("ambiguous marching-squares cell in closed trace graph")
        crossings = []
        for edge_index, (lo, hi) in enumerate(_EDGE_CORNERS):
            if shifted[lo] * shifted[hi] < 0.0:
                key = _edge_key(i, j, edge_index)
                vertex_index = vertices_by_key.get(key)
                if vertex_index is None:
                    vertex_index = len(vertices)
                    vertices_by_key[key] = vertex_index
                    vertices.append(
                        _crossing_vertex(
                            index=vertex_index,
                            edge_key=key,
                            values=values,
                            points=points,
                            nodes=nodes,
                            lo=lo,
                            hi=hi,
                            threshold=float(phase_threshold),
                        )
                    )
                crossings.append(vertex_index)
        if len(crossings) != 2:
            raise ValueError("closed trace graph requires non-ambiguous two-cut cells")
        segments.append(TraceSegment2D(crossings[0], crossings[1], (i, j)))
    components = _trace_components(vertices, segments)
    return TraceGraph2D(
        stratum=stratum,
        vertices=tuple(vertices),
        segments=tuple(segments),
        components=tuple(components),
        phase_threshold=float(phase_threshold),
    )


def trace_graph_surface_length(graph: TraceGraph2D, *, sigma: float = 1.0) -> float:
    """Return ``sigma*S_h`` from trace segments."""
    total = 0.0
    for segment in graph.segments:
        left = graph.vertices[segment.left].point
        right = graph.vertices[segment.right].point
        total += float(np.linalg.norm(right - left))
    return float(sigma) * total


def trace_component_areas(graph: TraceGraph2D) -> tuple[float, ...]:
    """Return positive oriented component areas."""
    return tuple(float(component.signed_area) for component in graph.components)


def trace_surface_vertex_covectors(
    graph: TraceGraph2D,
    *,
    sigma: float = 1.0,
) -> dict[int, np.ndarray]:
    """Return vertex covectors for ``sigma*S_h``."""
    covectors = _zero_vertex_covectors(graph)
    for segment in graph.segments:
        left = graph.vertices[segment.left].point
        right = graph.vertices[segment.right].point
        delta = right - left
        length = float(np.linalg.norm(delta))
        if length <= 0.0:
            raise ValueError("zero-length trace segment")
        tangent = delta / length
        covectors[segment.left] -= float(sigma) * tangent
        covectors[segment.right] += float(sigma) * tangent
    return covectors


def trace_component_area_vertex_covectors(
    graph: TraceGraph2D,
) -> list[dict[int, np.ndarray]]:
    """Return shoelace area vertex covectors for each component."""
    result = []
    for component in graph.components:
        covectors = _zero_vertex_covectors(graph)
        ids = component.vertex_indices
        n_vertices = len(ids)
        for local_index, vertex_index in enumerate(ids):
            previous_point = graph.vertices[ids[(local_index - 1) % n_vertices]].point
            next_point = graph.vertices[ids[(local_index + 1) % n_vertices]].point
            covectors[vertex_index] += 0.5 * np.asarray(
                [
                    next_point[1] - previous_point[1],
                    previous_point[0] - next_point[0],
                ],
                dtype=float,
            )
        result.append(covectors)
    return result


def trace_vertex_covector_action(
    covectors: dict[int, np.ndarray],
    vertex_vectors: dict[int, np.ndarray],
) -> float:
    """Return ``sum_z g_z . v_z`` for trace vertex fields."""
    total = 0.0
    for index, covector in covectors.items():
        total += float(np.dot(covector, vertex_vectors[index]))
    return total


def _iter_cells(grid, psi_host: np.ndarray):
    coords_x = np.asarray(grid.coords[0], dtype=float)
    coords_y = np.asarray(grid.coords[1], dtype=float)
    for i in range(grid.N[0]):
        for j in range(grid.N[1]):
            values = np.asarray(
                [
                    psi_host[i, j],
                    psi_host[i + 1, j],
                    psi_host[i + 1, j + 1],
                    psi_host[i, j + 1],
                ],
                dtype=float,
            )
            points = (
                np.asarray([coords_x[i], coords_y[j]], dtype=float),
                np.asarray([coords_x[i + 1], coords_y[j]], dtype=float),
                np.asarray([coords_x[i + 1], coords_y[j + 1]], dtype=float),
                np.asarray([coords_x[i], coords_y[j + 1]], dtype=float),
            )
            nodes = (
                (i, j),
                (i + 1, j),
                (i + 1, j + 1),
                (i, j + 1),
            )
            yield i, j, values, points, nodes


def _edge_key(i: int, j: int, edge_index: int) -> tuple[str, int, int]:
    if edge_index == 0:
        return ("h", i, j)
    if edge_index == 1:
        return ("v", i + 1, j)
    if edge_index == 2:
        return ("h", i, j + 1)
    return ("v", i, j)


def _crossing_vertex(
    *,
    index: int,
    edge_key: tuple[str, int, int],
    values: np.ndarray,
    points: tuple[np.ndarray, ...],
    nodes: tuple[tuple[int, int], ...],
    lo: int,
    hi: int,
    threshold: float,
) -> TraceVertex2D:
    denominator = values[hi] - values[lo]
    alpha = (threshold - values[lo]) / denominator
    point = np.asarray(points[lo], dtype=float) + alpha * (
        np.asarray(points[hi], dtype=float) - np.asarray(points[lo], dtype=float)
    )
    return TraceVertex2D(
        index=index,
        edge_key=edge_key,
        node_indices=(nodes[lo], nodes[hi]),
        alpha=float(alpha),
        point=point,
    )


def _trace_components(
    vertices: list[TraceVertex2D],
    segments: list[TraceSegment2D],
) -> list[TraceComponent2D]:
    adjacency: dict[int, list[int]] = {vertex.index: [] for vertex in vertices}
    for segment in segments:
        adjacency[segment.left].append(segment.right)
        adjacency[segment.right].append(segment.left)
    if any(len(neighbours) != 2 for neighbours in adjacency.values()):
        raise ValueError("closed trace graph requires every vertex to have degree two")
    visited_edges: set[tuple[int, int]] = set()
    components = []
    for segment in segments:
        edge = _canonical_edge(segment.left, segment.right)
        if edge in visited_edges:
            continue
        loop = _walk_loop(segment.left, segment.right, adjacency, visited_edges, len(segments))
        area = _polygon_area([vertices[index].point for index in loop])
        if area < 0.0:
            loop = tuple(reversed(loop))
            area = -area
        components.append(TraceComponent2D(tuple(loop), float(area)))
    return components


def _walk_loop(
    start: int,
    second: int,
    adjacency: dict[int, list[int]],
    visited_edges: set[tuple[int, int]],
    max_steps: int,
) -> tuple[int, ...]:
    loop = [start, second]
    previous = start
    current = second
    visited_edges.add(_canonical_edge(previous, current))
    for _ in range(max_steps + 1):
        if current == start:
            return tuple(loop[:-1])
        candidates = [value for value in adjacency[current] if value != previous]
        if not candidates:
            raise ValueError("open trace component")
        following = candidates[0]
        visited_edges.add(_canonical_edge(current, following))
        previous, current = current, following
        loop.append(current)
    raise ValueError("trace component walk did not close")


def _canonical_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left <= right else (right, left)


def _polygon_area(points: list[np.ndarray]) -> float:
    area = 0.0
    for point, next_point in zip(points, points[1:] + points[:1], strict=True):
        area += point[0] * next_point[1] - point[1] * next_point[0]
    return 0.5 * area


def _zero_vertex_covectors(graph: TraceGraph2D) -> dict[int, np.ndarray]:
    return {vertex.index: np.zeros(2, dtype=float) for vertex in graph.vertices}
