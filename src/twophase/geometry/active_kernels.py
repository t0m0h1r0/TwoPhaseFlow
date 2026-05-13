"""Active-row P1 geometry kernels for AO-Fast.

A3 chain:
  Equation: SP-AO defines active hard-volume rows
  ``Q_h(phi)_C=q_target_C`` on compact support ``A_q``.
  Discretization: each active row evaluates the same P1 marching-squares
  cut-cell volume, interface length, and local derivatives as the dense oracle,
  but only for explicitly supplied cell ids.
  Code: this module is backend-native active-row geometry.  It does not discover
  support from a full-grid mask and it is not a dense runtime fallback.

Symbol mapping
--------------
``A_q`` -> ``cell_ids_A``
``Q_h(phi)_A`` -> ``q_A``
``S_h(phi)_A`` -> ``s_A``
``J_q`` -> ``jq_local_A``
``dS_h`` -> ``ds_local_A``
"""

from __future__ import annotations

from dataclasses import dataclass


_EDGE_CORNERS = ((0, 1), (1, 2), (2, 3), (3, 0))


@dataclass(frozen=True)
class P1ActiveGeometry:
    """Backend-native P1 geometry evaluated only on compact active rows."""

    q_A: object
    s_A: object
    case_code_A: object
    edge_mask_A: object
    lambda_edge_A: object
    cell_measure_A: object
    jq_local_A: object
    ds_local_A: object
    row_norm_A: object
    sign_margin_A: object
    finite_mask_A: object
    regular_mask_A: object


@dataclass(frozen=True)
class P1ActiveVolumeGeometry:
    """Backend-native P1 cell volumes without surface/Jacobian work."""

    q_A: object
    case_code_A: object
    cell_measure_A: object


def active_cell_node_ids_2d(grid, cell_ids):
    """Return flattened Q1/P1 corner node ids for compact 2D cell ids."""
    xp = grid.xp
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if tuple(ids.shape[-1:]) != (2,):
        raise ValueError("cell_ids must have shape (n_active, 2)")
    i = ids[:, 0]
    j = ids[:, 1]
    n_y_nodes = int(grid.N[1]) + 1
    return xp.stack(
        (
            i * n_y_nodes + j,
            (i + 1) * n_y_nodes + j,
            (i + 1) * n_y_nodes + (j + 1),
            i * n_y_nodes + (j + 1),
        ),
        axis=-1,
    )


def refresh_active_geometry_2d(grid, phi, cell_ids, *, level: float = 0.0):
    """Evaluate active ``Q_h/S_h/J_q/dS_h`` rows for supplied cell ids.

    The caller owns support construction.  This function never calls
    ``where``/``nonzero`` over the full grid to discover active cells.
    """
    if grid.ndim != 2:
        raise ValueError("refresh_active_geometry_2d currently supports 2D grids")
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("cell_ids must have shape (n_active, 2)")

    values, points = _active_cell_corner_fields(xp, grid, phi_dev - float(level), ids)
    cell_measure_A = _active_cell_measures_from_points(points)
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_code = _case_field(xp, values)
    q_A = _local_cut_areas(xp, values, points, crossings, case_code)
    s_A = _local_surface_lengths(xp, crossings, case_code)
    jq_local_A = _local_area_derivatives(xp, values, points, crossings, case_code)
    ds_local_A = _local_length_derivatives(xp, crossings, case_code)
    edge_mask_A = _edge_mask(xp, crossings)
    lambda_edge_A = xp.stack(tuple(crossing["theta"] for crossing in crossings), axis=-1)
    row_norm_A = xp.sum(jq_local_A * jq_local_A, axis=-1)
    abs_values = xp.stack(tuple(xp.abs(value) for value in values), axis=-1)
    finite_values = xp.stack(tuple(xp.isfinite(value) for value in values), axis=-1)
    finite_mask_A = xp.all(finite_values, axis=-1)
    sign_margin_A = xp.min(abs_values, axis=-1)
    regular_mask_A = finite_mask_A & (sign_margin_A > 0.0)
    return P1ActiveGeometry(
        q_A=q_A,
        s_A=s_A,
        case_code_A=case_code,
        edge_mask_A=edge_mask_A,
        lambda_edge_A=lambda_edge_A,
        cell_measure_A=cell_measure_A,
        jq_local_A=jq_local_A,
        ds_local_A=ds_local_A,
        row_norm_A=row_norm_A,
        sign_margin_A=sign_margin_A,
        finite_mask_A=finite_mask_A,
        regular_mask_A=regular_mask_A,
    )


def refresh_active_volume_geometry_2d(grid, phi, cell_ids, *, level: float = 0.0):
    """Evaluate only the active P1 cut-cell volumes ``Q_h(phi)_A``.

    This is the exact same marching-squares volume formula used by
    ``refresh_active_geometry_2d``.  It deliberately skips interface length and
    derivative tables for line-search stages where the discrete equation only
    asks whether the hard volume residual decreased.
    """
    if grid.ndim != 2:
        raise ValueError(
            "refresh_active_volume_geometry_2d currently supports 2D grids"
        )
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("cell_ids must have shape (n_active, 2)")

    values, points = _active_cell_corner_fields(xp, grid, phi_dev - float(level), ids)
    cell_measure_A = _active_cell_measures_from_points(points)
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_code = _case_field(xp, values)
    return P1ActiveVolumeGeometry(
        q_A=_local_cut_areas(xp, values, points, crossings, case_code),
        case_code_A=case_code,
        cell_measure_A=cell_measure_A,
    )


def refresh_active_volume_geometry_candidates_2d(
    grid,
    phi_candidates,
    cell_ids,
    *,
    level: float = 0.0,
):
    """Evaluate exact ``Q_h`` for a fixed batch of candidate P1 gauges."""
    if grid.ndim != 2:
        raise ValueError(
            "refresh_active_volume_geometry_candidates_2d currently supports 2D grids"
        )
    xp = grid.xp
    phi_dev = xp.asarray(phi_candidates)
    expected_tail = (grid.N[0] + 1, grid.N[1] + 1)
    if phi_dev.ndim != 3 or tuple(phi_dev.shape[-2:]) != expected_tail:
        raise ValueError(
            "phi_candidates must have shape (n_candidates, "
            f"{expected_tail[0]}, {expected_tail[1]})"
        )
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("cell_ids must have shape (n_active, 2)")

    values, points = _active_cell_corner_fields_batched(
        xp,
        grid,
        phi_dev - float(level),
        ids,
    )
    cell_measure_A = _active_cell_measures_from_points(points)
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_code = _case_field(xp, values)
    return P1ActiveVolumeGeometry(
        q_A=_local_cut_areas(xp, values, points, crossings, case_code),
        case_code_A=case_code,
        cell_measure_A=cell_measure_A,
    )


def _active_cell_corner_fields(xp, grid, phi, cell_ids):
    i = cell_ids[:, 0]
    j = cell_ids[:, 1]
    x = _device_coord_1d(xp, grid, 0, phi.dtype)
    y = _device_coord_1d(xp, grid, 1, phi.dtype)
    values = (
        phi[i, j],
        phi[i + 1, j],
        phi[i + 1, j + 1],
        phi[i, j + 1],
    )
    points = (
        (x[i], y[j]),
        (x[i + 1], y[j]),
        (x[i + 1], y[j + 1]),
        (x[i], y[j + 1]),
    )
    return values, points


def _active_cell_corner_fields_batched(xp, grid, phi, cell_ids):
    i = cell_ids[:, 0]
    j = cell_ids[:, 1]
    x = _device_coord_1d(xp, grid, 0, phi.dtype)
    y = _device_coord_1d(xp, grid, 1, phi.dtype)
    values = (
        phi[:, i, j],
        phi[:, i + 1, j],
        phi[:, i + 1, j + 1],
        phi[:, i, j + 1],
    )
    points = (
        (x[i], y[j]),
        (x[i + 1], y[j]),
        (x[i + 1], y[j + 1]),
        (x[i], y[j + 1]),
    )
    return values, points


def _device_coord_1d(xp, grid, axis: int, dtype):
    getter = getattr(grid, "device_coords", None)
    if callable(getter):
        return getter(axis, dtype=dtype)
    return xp.asarray(grid.coords[axis], dtype=dtype)


def _active_cell_measures_from_points(points):
    dx = points[1][0] - points[0][0]
    dy = points[2][1] - points[1][1]
    return dx * dy


def _edge_crossing(xp, values, points, edge: int):
    lo, hi = _EDGE_CORNERS[edge]
    value_lo = values[lo]
    value_hi = values[hi]
    mask = value_lo * value_hi < 0.0
    denominator = value_hi - value_lo
    safe_denominator = xp.where(mask, denominator, xp.ones_like(denominator))
    theta = xp.where(mask, -value_lo / safe_denominator, 0.0)
    x = points[lo][0] + theta * (points[hi][0] - points[lo][0])
    y = points[lo][1] + theta * (points[hi][1] - points[lo][1])
    return {
        "mask": mask,
        "theta": theta,
        "x": x,
        "y": y,
        "lo": lo,
        "hi": hi,
        "values": values,
        "points": points,
    }


def _case_field(xp, values):
    inside = tuple(value < 0.0 for value in values)
    case_field = xp.zeros_like(values[0], dtype=xp.uint8)
    for corner, mask in enumerate(inside):
        case_field = case_field + mask.astype(xp.uint8) * (1 << corner)
    return case_field


def _edge_mask(xp, crossings):
    mask = xp.zeros_like(crossings[0]["theta"], dtype=xp.uint8)
    for edge, crossing in enumerate(crossings):
        mask = mask + crossing["mask"].astype(xp.uint8) * (1 << edge)
    return mask


def _local_cut_areas(xp, values, points, crossings, case_field):
    local_area = xp.zeros_like(values[0])
    for case_id in range(16):
        for tokens in _liquid_polygon_rings(case_id):
            if len(tokens) < 3:
                continue
            active = case_field == case_id
            for kind, index in tokens:
                if kind == "edge":
                    active = active & crossings[index]["mask"]
            shoelace = xp.zeros_like(values[0])
            for token, next_token in zip(tokens, tokens[1:] + tokens[:1], strict=True):
                x, y = _token_point(token, points=points, crossings=crossings)
                next_x, next_y = _token_point(
                    next_token, points=points, crossings=crossings
                )
                shoelace = shoelace + x * next_y - y * next_x
            local_area = local_area + xp.where(
                active,
                0.5 * shoelace,
                xp.zeros_like(shoelace),
            )
    return local_area


def _local_surface_lengths(xp, crossings, case_field):
    local_length = xp.zeros_like(crossings[0]["theta"])
    for case_id in range(16):
        edges = _crossing_edges(case_id)
        if len(edges) not in {2, 4}:
            continue
        active = case_field == case_id
        for edge in edges:
            active = active & crossings[edge]["mask"]
        length = _segment_length(xp, crossings[edges[0]], crossings[edges[1]])
        if len(edges) == 4:
            length = length + _segment_length(xp, crossings[edges[2]], crossings[edges[3]])
        local_length = local_length + xp.where(active, length, xp.zeros_like(length))
    return local_length


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


def _local_length_derivatives(xp, crossings, case_field):
    local = _local_zeros(xp, tuple(crossing["theta"] for crossing in crossings))
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


def _liquid_polygon_rings(case_id: int):
    if case_id == 10:
        return (
            (("corner", 1), ("edge", 1), ("edge", 0)),
            (("corner", 3), ("edge", 3), ("edge", 2)),
        )
    tokens = _liquid_polygon_tokens(case_id)
    if not tokens:
        return ()
    return (tokens,)


def _liquid_polygon_tokens(case_id: int):
    inside = tuple(bool(case_id & (1 << corner)) for corner in range(4))
    tokens = []
    for edge, (lo, hi) in enumerate(_EDGE_CORNERS):
        if inside[lo]:
            tokens.append(("corner", lo))
        if inside[lo] != inside[hi]:
            tokens.append(("edge", edge))
    return tuple(tokens)


def _crossing_edges(case_id: int) -> tuple[int, ...]:
    inside = tuple(bool(case_id & (1 << corner)) for corner in range(4))
    return tuple(
        edge
        for edge, (lo, hi) in enumerate(_EDGE_CORNERS)
        if inside[lo] != inside[hi]
    )


def _token_point(token, *, points, crossings):
    kind, index = token
    if kind == "corner":
        return points[index][0], points[index][1]
    crossing = crossings[index]
    return crossing["x"], crossing["y"]


def _segment_length(xp, left, right):
    return xp.sqrt((right["x"] - left["x"]) ** 2 + (right["y"] - left["y"]) ** 2)


def _local_zeros(xp, values):
    return [xp.zeros_like(values[0]) for _corner in range(4)]


def _stack_local(xp, local):
    return xp.stack(local, axis=-1)
