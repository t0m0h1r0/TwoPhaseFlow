"""Local derivatives of SP-AO P1 cut geometry.

Symbol mapping
--------------
``J_q`` -> cell-local derivative of ``Q_h(phi)_C`` with respect to nodal
           gauge values.
``dS_h`` -> cell-local derivative of P1 interface length.

The returned local arrays have shape ``(NX, NY, 4)`` with corner order
``(i,j), (i+1,j), (i+1,j+1), (i,j+1)``.  They stay in the active backend
namespace so the later Schur/projection stages can assemble GPU-native row
tables without revisiting the geometry formulas.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cell_complex import MetricCellComplex
from .p1_cut_geometry import (
    _cell_corner_fields,
    _case_field,
    _crossing_edges,
    _edge_crossing,
    _liquid_polygon_rings,
    _segment_length,
    _token_point,
    _validate_regular_values,
)


@dataclass(frozen=True)
class P1CutDerivatives:
    """Cell-local ``J_q`` and ``dS_h`` tables for one regular stratum."""

    jq_local: object
    ds_local: object


def cut_geometry_derivatives_2d(grid, phi, *, level: float = 0.0) -> P1CutDerivatives:
    """Return backend-native local derivatives of ``Q_h`` and ``S_h``."""
    if grid.ndim != 2:
        raise ValueError("cut_geometry_derivatives_2d currently supports 2D grids")
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    phi_rel = phi_dev - float(level)
    _validate_regular_values(xp, phi_rel)
    complex_h = MetricCellComplex.from_grid(grid)
    values, points = _cell_corner_fields(xp, grid, phi_rel, complex_h=complex_h)
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_field = _case_field(xp, values)
    return P1CutDerivatives(
        jq_local=_local_area_derivatives(xp, values, points, crossings, case_field),
        ds_local=_local_length_derivatives(xp, values, crossings, case_field),
    )


def scatter_local_to_nodes(grid, local):
    """Scatter local corner derivatives to a nodal covector field."""
    if grid.ndim != 2:
        raise ValueError("scatter_local_to_nodes currently supports 2D grids")
    xp = grid.xp
    local = xp.asarray(local)
    expected_shape = (grid.N[0], grid.N[1], 4)
    if tuple(local.shape) != expected_shape:
        raise ValueError(
            "local derivative shape must be "
            f"{expected_shape}, got {tuple(local.shape)}"
        )
    gradient = xp.zeros((grid.N[0] + 1, grid.N[1] + 1), dtype=local.dtype)
    gradient[:-1, :-1] = gradient[:-1, :-1] + local[..., 0]
    gradient[1:, :-1] = gradient[1:, :-1] + local[..., 1]
    gradient[1:, 1:] = gradient[1:, 1:] + local[..., 2]
    gradient[:-1, 1:] = gradient[:-1, 1:] + local[..., 3]
    return gradient


def _local_area_derivatives(xp, values, points, crossings, case_field):
    local = _local_zeros(xp, values)
    for case_id in range(16):
        for tokens in _liquid_polygon_rings(case_id):
            if len(tokens) < 3:
                continue
            active = case_field == case_id
            for kind, index in tokens:
                if kind == "edge":
                    active = active & crossings[index]["mask"]
            for index, token in enumerate(tokens):
                previous_token = tokens[(index - 1) % len(tokens)]
                next_token = tokens[(index + 1) % len(tokens)]
                _add_area_vertex_contribution(
                    xp,
                    local,
                    token,
                    previous_token,
                    next_token,
                    active,
                    points=points,
                    crossings=crossings,
                )
    return _stack_local(xp, local)


def _local_length_derivatives(xp, values, crossings, case_field):
    del values
    local = _local_zeros(xp, tuple(crossing["x"] for crossing in crossings))
    for case_id in range(16):
        edges = _crossing_edges(case_id)
        if len(edges) not in {2, 4}:
            continue
        active = case_field == case_id
        for edge in edges:
            active = active & crossings[edge]["mask"]
        _add_segment_length_contribution(
            xp,
            local,
            crossings[edges[0]],
            crossings[edges[1]],
            active,
        )
        if len(edges) == 4:
            _add_segment_length_contribution(
                xp,
                local,
                crossings[edges[2]],
                crossings[edges[3]],
                active,
            )
    return _stack_local(xp, local)


def _add_area_vertex_contribution(
    xp,
    local,
    token,
    previous_token,
    next_token,
    active,
    *,
    points,
    crossings,
):
    if token[0] != "edge":
        return
    point_prev = _token_point(previous_token, points=points, crossings=crossings)
    point_next = _token_point(next_token, points=points, crossings=crossings)
    covector_x = 0.5 * (point_next[1] - point_prev[1])
    covector_y = 0.5 * (point_prev[0] - point_next[0])
    for corner, dx_dphi, dy_dphi in _crossing_derivatives(xp, crossings[token[1]]):
        contribution = covector_x * dx_dphi + covector_y * dy_dphi
        local[corner] = local[corner] + xp.where(
            active,
            contribution,
            xp.zeros_like(contribution),
        )


def _add_segment_length_contribution(xp, local, left, right, active):
    length = _segment_length(xp, left, right)
    safe_length = xp.where(length > 0.0, length, xp.ones_like(length))
    tangent_x = (right["x"] - left["x"]) / safe_length
    tangent_y = (right["y"] - left["y"]) / safe_length
    for corner, dx_dphi, dy_dphi in _crossing_derivatives(xp, left):
        contribution = -(tangent_x * dx_dphi + tangent_y * dy_dphi)
        local[corner] = local[corner] + xp.where(
            active,
            contribution,
            xp.zeros_like(contribution),
        )
    for corner, dx_dphi, dy_dphi in _crossing_derivatives(xp, right):
        contribution = tangent_x * dx_dphi + tangent_y * dy_dphi
        local[corner] = local[corner] + xp.where(
            active,
            contribution,
            xp.zeros_like(contribution),
        )


def _crossing_derivatives(xp, crossing):
    values = crossing["values"]
    points = crossing["points"]
    lo = crossing["lo"]
    hi = crossing["hi"]
    value_lo = values[lo]
    value_hi = values[hi]
    denominator = value_hi - value_lo
    safe_denominator = xp.where(
        crossing["mask"],
        denominator,
        xp.ones_like(denominator),
    )
    denominator_sq = safe_denominator * safe_denominator
    tangent_x = points[hi][0] - points[lo][0]
    tangent_y = points[hi][1] - points[lo][1]
    dtheta_lo = -value_hi / denominator_sq
    dtheta_hi = value_lo / denominator_sq
    return (
        (lo, tangent_x * dtheta_lo, tangent_y * dtheta_lo),
        (hi, tangent_x * dtheta_hi, tangent_y * dtheta_hi),
    )


def _local_zeros(xp, values):
    return [xp.zeros_like(values[0]) for _corner in range(4)]


def _stack_local(xp, local):
    return xp.stack(local, axis=-1)
