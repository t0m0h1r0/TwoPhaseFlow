"""Sharp fixed-stratum geometry for closed-interface capillarity.

Symbol mapping
--------------
``K`` -> :class:`~twophase.coupling.closed_interface_stratum.ClosedInterfaceStratum`
``S_h`` -> :func:`trace_surface_length_2d`
``V_h`` -> :func:`liquid_area_2d`
``dS_h`` -> :func:`trace_surface_length_gradient_2d`
``dV_h`` -> :func:`liquid_area_gradient_2d`

These routines implement the first diagnostic slice of the closed-interface
Riesz capillary path.  They differentiate geometric functionals on an
unchanged marching-squares stratum and fail closed when the stratum changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from .closed_interface_stratum import build_closed_interface_stratum
from .closed_interface_stratum import array_to_numpy
from .transport_variational_capillary import (
    marching_squares_liquid_area_2d,
    marching_squares_liquid_area_gradient_2d,
    marching_squares_surface_energy_gradient_2d,
)


_CORNERS = ((0, 0), (1, 0), (1, 1), (0, 1))
_EDGE_CORNERS = ((0, 1), (1, 2), (2, 3), (3, 0))


@dataclass(frozen=True)
class DirectionalDerivativeCheck:
    """Directional finite-difference check on one fixed stratum."""

    valid: bool
    residual: float
    finite_difference: float
    gradient_action: float
    reason: str


def trace_surface_length_2d(
    *,
    xp,
    grid,
    psi,
    sigma: float = 1.0,
    phase_threshold: float = 0.5,
):
    """Return the P1 marching-squares surface energy ``sigma*S_h``."""
    if grid.ndim != 2:
        raise ValueError("trace_surface_length_2d currently supports 2D grids")
    psi_host = array_to_numpy(xp, xp.asarray(psi))
    total = 0.0
    for i, j, values, points in _iter_cells(grid, psi_host):
        del i, j
        crossings = _edge_crossings(values, points, float(phase_threshold))
        if len(crossings) == 2:
            total += _segment_length(crossings[0], crossings[1])
        elif len(crossings) == 4:
            total += _segment_length(crossings[0], crossings[1])
            total += _segment_length(crossings[2], crossings[3])
    return xp.asarray(float(sigma) * total, dtype=xp.asarray(psi).dtype)


def trace_surface_length_gradient_2d(
    *,
    xp,
    grid,
    psi,
    sigma: float = 1.0,
    phase_threshold: float = 0.5,
):
    """Return the nodal derivative of ``sigma*S_h`` on the active stratum."""
    return marching_squares_surface_energy_gradient_2d(
        xp=xp,
        grid=grid,
        psi=psi,
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
    )


def liquid_area_2d(
    *,
    xp,
    grid,
    psi,
    phase_threshold: float = 0.5,
):
    """Return the sharp P1 area of the phase with ``psi >= threshold``."""
    if grid.ndim != 2:
        raise ValueError("liquid_area_2d currently supports 2D grids")
    if hasattr(xp, "asnumpy"):
        return marching_squares_liquid_area_2d(
            xp=xp,
            grid=grid,
            psi=psi,
            phase_threshold=float(phase_threshold),
        )
    psi_host = array_to_numpy(xp, xp.asarray(psi))
    total = 0.0
    for i, j, values, points in _iter_cells(grid, psi_host):
        del i, j
        polygon = _liquid_polygon(values, points, float(phase_threshold))
        if len(polygon) >= 3:
            total += _polygon_area([vertex.point for vertex in polygon])
    return xp.asarray(total, dtype=xp.asarray(psi).dtype)


def liquid_area_gradient_2d(
    *,
    xp,
    grid,
    psi,
    phase_threshold: float = 0.5,
):
    """Return the nodal derivative of sharp P1 liquid area."""
    return marching_squares_liquid_area_gradient_2d(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=float(phase_threshold),
    )


def fixed_stratum_directional_derivative_check(
    *,
    xp,
    grid,
    psi,
    direction,
    value_fn: Callable,
    gradient_fn: Callable,
    epsilon: float = 1.0e-6,
    phase_threshold: float = 0.5,
    threshold_tol: float = 0.0,
) -> DirectionalDerivativeCheck:
    """Check ``dF[direction]`` by centered differences on one stratum."""
    base = build_closed_interface_stratum(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=float(phase_threshold),
        threshold_tol=float(threshold_tol),
    )
    if not base.regular:
        return DirectionalDerivativeCheck(False, np.inf, 0.0, 0.0, "irregular_base_stratum")
    psi_arr = xp.asarray(psi)
    direction_arr = xp.asarray(direction)
    plus = psi_arr + float(epsilon) * direction_arr
    minus = psi_arr - float(epsilon) * direction_arr
    if not base.matches(
        xp=xp,
        grid=grid,
        psi=plus,
        threshold_tol=float(threshold_tol),
    ):
        return DirectionalDerivativeCheck(False, np.inf, 0.0, 0.0, "plus_stratum_changed")
    if not base.matches(
        xp=xp,
        grid=grid,
        psi=minus,
        threshold_tol=float(threshold_tol),
    ):
        return DirectionalDerivativeCheck(False, np.inf, 0.0, 0.0, "minus_stratum_changed")

    value_plus = _scalar_float(
        xp,
        value_fn(xp=xp, grid=grid, psi=plus, phase_threshold=phase_threshold),
    )
    value_minus = _scalar_float(
        xp,
        value_fn(xp=xp, grid=grid, psi=minus, phase_threshold=phase_threshold),
    )
    finite_difference = (value_plus - value_minus) / (2.0 * float(epsilon))
    gradient = gradient_fn(xp=xp, grid=grid, psi=psi_arr, phase_threshold=phase_threshold)
    gradient_action = _scalar_float(xp, xp.sum(xp.asarray(gradient) * direction_arr))
    denominator = abs(finite_difference) + abs(gradient_action) + 1.0e-30
    residual = abs(finite_difference - gradient_action) / denominator
    return DirectionalDerivativeCheck(
        True,
        float(residual),
        float(finite_difference),
        float(gradient_action),
        "ok",
    )


@dataclass(frozen=True)
class _Vertex:
    point: np.ndarray
    derivatives: dict[int, np.ndarray]


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
            yield i, j, values, points


def _edge_crossings(values, points, threshold: float) -> list[np.ndarray]:
    crossings = []
    for lo, hi in _EDGE_CORNERS:
        shifted_lo = values[lo] - threshold
        shifted_hi = values[hi] - threshold
        if shifted_lo * shifted_hi < 0.0:
            crossings.append(_crossing_vertex(values, points, lo, hi, threshold).point)
    return crossings


def _liquid_polygon(values, points, threshold: float) -> list[_Vertex]:
    vertices = []
    inside = values >= threshold
    for lo, hi in _EDGE_CORNERS:
        if inside[lo]:
            vertices.append(_Vertex(np.asarray(points[lo], dtype=float), {}))
        if bool(inside[lo]) != bool(inside[hi]):
            vertices.append(_crossing_vertex(values, points, lo, hi, threshold))
    return vertices


def _crossing_vertex(values, points, lo: int, hi: int, threshold: float) -> _Vertex:
    denominator = values[hi] - values[lo]
    theta = (threshold - values[lo]) / denominator
    tangent = np.asarray(points[hi], dtype=float) - np.asarray(points[lo], dtype=float)
    point = np.asarray(points[lo], dtype=float) + theta * tangent
    denominator_sq = denominator * denominator
    dtheta_lo = (threshold - values[hi]) / denominator_sq
    dtheta_hi = -(threshold - values[lo]) / denominator_sq
    return _Vertex(
        point,
        {
            lo: tangent * dtheta_lo,
            hi: tangent * dtheta_hi,
        },
    )


def _segment_length(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(right - left))


def _polygon_area(points: list[np.ndarray]) -> float:
    area = 0.0
    for point, next_point in zip(points, points[1:] + points[:1], strict=True):
        area += point[0] * next_point[1] - point[1] * next_point[0]
    return 0.5 * area


def _polygon_value_gradient(vertices: list[_Vertex]) -> np.ndarray:
    local = np.zeros(4, dtype=float)
    n_vertices = len(vertices)
    for index, vertex in enumerate(vertices):
        previous_point = vertices[(index - 1) % n_vertices].point
        next_point = vertices[(index + 1) % n_vertices].point
        point_gradient = 0.5 * np.asarray(
            [
                next_point[1] - previous_point[1],
                previous_point[0] - next_point[0],
            ],
            dtype=float,
        )
        for corner, derivative in vertex.derivatives.items():
            local[corner] += float(np.dot(point_gradient, derivative))
    return local


def _scalar_float(xp, value) -> float:
    return float(np.asarray(array_to_numpy(xp, value)))
