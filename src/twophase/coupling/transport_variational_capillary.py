"""Transport-adjoint variational capillarity for CLS/FCCD interfaces.

A3 chain:
  Equation: ``d(σ|Γ|)/dt + P_Γ = 0``.
  Discretization: define ``E_Γ(ψ)=σ|Γ_h(ψ)|`` by cell-local line segments,
  differentiate it with respect to nodal ``ψ``, and map the covector through
  the adjoint of the actual face transport ``ψ_t=-D_f(ψ_f u_f)``.
  Code: return the face pressure-gradient jump whose face work equals that
  transport-adjoint capillary power.
"""

from __future__ import annotations


def _cell_corner_fields(xp, grid, psi):
    x = xp.asarray(grid.coords[0], dtype=psi.dtype)
    y = xp.asarray(grid.coords[1], dtype=psi.dtype)
    x0 = x[:-1].reshape((-1, 1))
    x1 = x[1:].reshape((-1, 1))
    y0 = y[:-1].reshape((1, -1))
    y1 = y[1:].reshape((1, -1))
    values = (
        psi[:-1, :-1],
        psi[1:, :-1],
        psi[1:, 1:],
        psi[:-1, 1:],
    )
    points = (
        (x0, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
    )
    return values, points


def _cell_geometry_fields(xp, grid, dtype):
    x = xp.asarray(grid.coords[0], dtype=dtype)
    y = xp.asarray(grid.coords[1], dtype=dtype)
    x0 = x[:-1].reshape((-1, 1))
    x1 = x[1:].reshape((-1, 1))
    y0 = y[:-1].reshape((1, -1))
    y1 = y[1:].reshape((1, -1))
    centre_x = 0.5 * (x0 + x1)
    centre_y = 0.5 * (y0 + y1)
    return x0, x1, y0, y1, centre_x, centre_y


def _edge_crossing(xp, values, points, edge, threshold):
    edge_corners = ((0, 1), (1, 2), (2, 3), (3, 0))
    lo, hi = edge_corners[edge]
    value_lo = values[lo]
    value_hi = values[hi]
    shifted_lo = value_lo - threshold
    shifted_hi = value_hi - threshold
    mask = shifted_lo * shifted_hi < 0.0
    denominator = value_hi - value_lo
    safe_denominator = xp.where(mask, denominator, xp.ones_like(denominator))
    theta = xp.where(mask, (threshold - value_lo) / safe_denominator, 0.0)
    tangent_x = points[hi][0] - points[lo][0]
    tangent_y = points[hi][1] - points[lo][1]
    point_x = points[lo][0] + theta * tangent_x
    point_y = points[lo][1] + theta * tangent_y
    denominator_sq = safe_denominator * safe_denominator
    dtheta_lo = xp.where(mask, (threshold - value_hi) / denominator_sq, 0.0)
    dtheta_hi = xp.where(mask, -(threshold - value_lo) / denominator_sq, 0.0)
    derivatives = (
        (lo, tangent_x * dtheta_lo, tangent_y * dtheta_lo),
        (hi, tangent_x * dtheta_hi, tangent_y * dtheta_hi),
    )
    return {
        "mask": mask,
        "x": point_x,
        "y": point_y,
        "derivatives": derivatives,
    }


def _bilinear_basis_at_point(point_x, point_y, geometry):
    x0, x1, y0, y1, _, _ = geometry
    local_x = (point_x - x0) / (x1 - x0)
    local_y = (point_y - y0) / (y1 - y0)
    return (
        (1.0 - local_x) * (1.0 - local_y),
        local_x * (1.0 - local_y),
        local_x * local_y,
        (1.0 - local_x) * local_y,
    )


def _bilinear_value_and_line_derivative(
    values,
    point_x,
    point_y,
    direction_x,
    direction_y,
    geometry,
):
    x0, x1, y0, y1, _, _ = geometry
    basis = _bilinear_basis_at_point(point_x, point_y, geometry)
    local_x = (point_x - x0) / (x1 - x0)
    local_y = (point_y - y0) / (y1 - y0)
    value = sum(component * basis_component for component, basis_component in zip(values, basis, strict=True))
    dvalue_dlocal_x = (
        -(1.0 - local_y) * values[0]
        + (1.0 - local_y) * values[1]
        + local_y * values[2]
        - local_y * values[3]
    )
    dvalue_dlocal_y = (
        -(1.0 - local_x) * values[0]
        - local_x * values[1]
        + local_x * values[2]
        + (1.0 - local_x) * values[3]
    )
    derivative = (
        dvalue_dlocal_x * direction_x / (x1 - x0)
        + dvalue_dlocal_y * direction_y / (y1 - y0)
    )
    return value, derivative, basis


def _fixed_midline_for_edge_pair(xp, edge_a: int, edge_b: int, geometry):
    x0, x1, y0, y1, centre_x, centre_y = geometry
    pair = tuple(sorted((edge_a, edge_b)))
    if pair == (0, 1):
        start_x, start_y = x1, y0
        end_x, end_y = centre_x, centre_y
    elif pair == (1, 2):
        start_x, start_y = x1, y1
        end_x, end_y = centre_x, centre_y
    elif pair == (2, 3):
        start_x, start_y = x0, y1
        end_x, end_y = centre_x, centre_y
    elif pair == (0, 3):
        start_x, start_y = x0, y0
        end_x, end_y = centre_x, centre_y
    elif pair == (0, 2):
        start_x, start_y = x0, centre_y
        end_x, end_y = x1, centre_y
    elif pair == (1, 3):
        start_x, start_y = centre_x, y0
        end_x, end_y = centre_x, y1
    else:
        start_x = xp.zeros_like(centre_x)
        start_y = xp.zeros_like(centre_y)
        end_x = xp.zeros_like(centre_x)
        end_y = xp.zeros_like(centre_y)
    return start_x, start_y, end_x - start_x, end_y - start_y


def _midline_crossing(
    xp,
    values,
    edge_a: int,
    edge_b: int,
    threshold,
    geometry,
    active,
):
    start_x, start_y, direction_x, direction_y = _fixed_midline_for_edge_pair(
        xp,
        edge_a,
        edge_b,
        geometry,
    )
    lam = xp.full_like(values[0], 0.5)
    for _ in range(4):
        point_x = start_x + lam * direction_x
        point_y = start_y + lam * direction_y
        value, derivative, _ = _bilinear_value_and_line_derivative(
            values,
            point_x,
            point_y,
            direction_x,
            direction_y,
            geometry,
        )
        valid = active & (derivative != 0.0)
        safe_derivative = xp.where(valid, derivative, xp.ones_like(derivative))
        lam = xp.where(valid, lam - (value - threshold) / safe_derivative, lam)

    point_x = start_x + lam * direction_x
    point_y = start_y + lam * direction_y
    _, derivative, basis = _bilinear_value_and_line_derivative(
        values,
        point_x,
        point_y,
        direction_x,
        direction_y,
        geometry,
    )
    valid = active & (derivative != 0.0) & (lam >= 0.0) & (lam <= 1.0)
    safe_derivative = xp.where(valid, derivative, xp.ones_like(derivative))
    derivatives = tuple(
        (
            corner,
            -direction_x * basis_component / safe_derivative,
            -direction_y * basis_component / safe_derivative,
        )
        for corner, basis_component in enumerate(basis)
    )
    return {
        "mask": valid,
        "x": point_x,
        "y": point_y,
        "derivatives": derivatives,
    }


def _add_local_contribution(
    xp,
    local,
    crossing_a,
    crossing_b,
    mask,
    *,
    sigma,
):
    segment_x = crossing_b["x"] - crossing_a["x"]
    segment_y = crossing_b["y"] - crossing_a["y"]
    length = xp.sqrt(segment_x * segment_x + segment_y * segment_y)
    active = mask & (length > xp.asarray(0.0, dtype=length.dtype))
    safe_length = xp.where(active, length, xp.ones_like(length))
    direction_x = segment_x / safe_length
    direction_y = segment_y / safe_length

    def add_derivatives(crossing, sign):
        for corner, derivative_x, derivative_y in crossing["derivatives"]:
            contribution = float(sign) * float(sigma) * (
                direction_x * derivative_x + direction_y * derivative_y
            )
            local[corner] = local[corner] + xp.where(
                active,
                contribution,
                xp.zeros_like(contribution),
            )

    add_derivatives(crossing_a, -1.0)
    add_derivatives(crossing_b, 1.0)


def _add_p2_local_contribution(
    xp,
    local,
    crossing_a,
    crossing_mid,
    crossing_b,
    mask,
    *,
    sigma,
):
    dtype = crossing_a["x"].dtype
    quadrature_points = (
        -xp.sqrt(xp.asarray(3.0 / 5.0, dtype=dtype)),
        xp.asarray(0.0, dtype=dtype),
        xp.sqrt(xp.asarray(3.0 / 5.0, dtype=dtype)),
    )
    quadrature_weights = (
        xp.asarray(5.0 / 9.0, dtype=dtype),
        xp.asarray(8.0 / 9.0, dtype=dtype),
        xp.asarray(5.0 / 9.0, dtype=dtype),
    )
    node_x = (crossing_a["x"], crossing_mid["x"], crossing_b["x"])
    node_y = (crossing_a["y"], crossing_mid["y"], crossing_b["y"])
    force_x = [xp.zeros_like(crossing_a["x"]) for _ in range(3)]
    force_y = [xp.zeros_like(crossing_a["y"]) for _ in range(3)]

    for point, weight in zip(quadrature_points, quadrature_weights, strict=True):
        shape_derivatives = (
            point - 0.5,
            -2.0 * point,
            point + 0.5,
        )
        tangent_x = sum(
            derivative * coordinate
            for derivative, coordinate in zip(shape_derivatives, node_x, strict=True)
        )
        tangent_y = sum(
            derivative * coordinate
            for derivative, coordinate in zip(shape_derivatives, node_y, strict=True)
        )
        length = xp.sqrt(tangent_x * tangent_x + tangent_y * tangent_y)
        active = mask & (length > xp.asarray(0.0, dtype=dtype))
        safe_length = xp.where(active, length, xp.ones_like(length))
        unit_x = tangent_x / safe_length
        unit_y = tangent_y / safe_length
        for node_index, derivative in enumerate(shape_derivatives):
            weighted_derivative = float(sigma) * weight * derivative
            force_x[node_index] = force_x[node_index] + xp.where(
                active,
                weighted_derivative * unit_x,
                xp.zeros_like(unit_x),
            )
            force_y[node_index] = force_y[node_index] + xp.where(
                active,
                weighted_derivative * unit_y,
                xp.zeros_like(unit_y),
            )

    for node_index, crossing in enumerate(
        (crossing_a, crossing_mid, crossing_b)
    ):
        for corner, derivative_x, derivative_y in crossing["derivatives"]:
            local[corner] = local[corner] + xp.where(
                mask,
                force_x[node_index] * derivative_x
                + force_y[node_index] * derivative_y,
                xp.zeros_like(local[corner]),
            )


def _p1_local_energy(xp, crossing_a, crossing_b, mask, *, sigma):
    segment_x = crossing_b["x"] - crossing_a["x"]
    segment_y = crossing_b["y"] - crossing_a["y"]
    length = xp.sqrt(segment_x * segment_x + segment_y * segment_y)
    active = mask & (length > xp.asarray(0.0, dtype=length.dtype))
    return xp.where(active, float(sigma) * length, xp.zeros_like(length))


def _p2_local_energy(xp, crossing_a, crossing_mid, crossing_b, mask, *, sigma):
    dtype = crossing_a["x"].dtype
    quadrature_points = (
        -xp.sqrt(xp.asarray(3.0 / 5.0, dtype=dtype)),
        xp.asarray(0.0, dtype=dtype),
        xp.sqrt(xp.asarray(3.0 / 5.0, dtype=dtype)),
    )
    quadrature_weights = (
        xp.asarray(5.0 / 9.0, dtype=dtype),
        xp.asarray(8.0 / 9.0, dtype=dtype),
        xp.asarray(5.0 / 9.0, dtype=dtype),
    )
    node_x = (crossing_a["x"], crossing_mid["x"], crossing_b["x"])
    node_y = (crossing_a["y"], crossing_mid["y"], crossing_b["y"])
    energy = xp.zeros_like(crossing_a["x"])
    for point, weight in zip(quadrature_points, quadrature_weights, strict=True):
        shape_derivatives = (
            point - 0.5,
            -2.0 * point,
            point + 0.5,
        )
        tangent_x = sum(
            derivative * coordinate
            for derivative, coordinate in zip(shape_derivatives, node_x, strict=True)
        )
        tangent_y = sum(
            derivative * coordinate
            for derivative, coordinate in zip(shape_derivatives, node_y, strict=True)
        )
        length = xp.sqrt(tangent_x * tangent_x + tangent_y * tangent_y)
        active = mask & (length > xp.asarray(0.0, dtype=dtype))
        energy = energy + xp.where(
            active,
            float(sigma) * weight * length,
            xp.zeros_like(length),
        )
    return energy


def marching_squares_surface_energy_gradient_2d(
    *,
    xp,
    grid,
    psi,
    sigma: float,
    phase_threshold: float = 0.5,
):
    """Return the derivative of ``σ|Γ_h(ψ)|`` with respect to nodal ``ψ``."""
    if grid.ndim != 2:
        raise ValueError("transport_variational capillarity currently supports 2D")
    psi = xp.asarray(psi)
    values, points = _cell_corner_fields(xp, grid, psi)
    threshold = xp.asarray(phase_threshold, dtype=psi.dtype)
    crossings = [
        _edge_crossing(xp, values, points, edge, threshold)
        for edge in range(4)
    ]
    crossing_count = sum(
        crossing["mask"].astype(psi.dtype) for crossing in crossings
    )
    local = [xp.zeros_like(values[0]) for _ in range(4)]

    for edge_a in range(4):
        for edge_b in range(edge_a + 1, 4):
            mask = (
                (crossing_count == 2.0)
                & crossings[edge_a]["mask"]
                & crossings[edge_b]["mask"]
            )
            _add_local_contribution(
                xp,
                local,
                crossings[edge_a],
                crossings[edge_b],
                mask,
                sigma=sigma,
            )

    ambiguous = crossing_count == 4.0
    _add_local_contribution(
        xp,
        local,
        crossings[0],
        crossings[1],
        ambiguous,
        sigma=sigma,
    )
    _add_local_contribution(
        xp,
        local,
        crossings[2],
        crossings[3],
        ambiguous,
        sigma=sigma,
    )

    gradient = xp.zeros_like(psi)
    gradient[:-1, :-1] = gradient[:-1, :-1] + local[0]
    gradient[1:, :-1] = gradient[1:, :-1] + local[1]
    gradient[1:, 1:] = gradient[1:, 1:] + local[2]
    gradient[:-1, 1:] = gradient[:-1, 1:] + local[3]
    return gradient


def p2_trace_surface_energy_2d(
    *,
    xp,
    grid,
    psi,
    sigma: float,
    phase_threshold: float = 0.5,
):
    """Return the P2 isoparametric discrete surface energy ``σ|Γ_h|``."""
    if grid.ndim != 2:
        raise ValueError("transport_variational_p2 supports 2D")
    psi = xp.asarray(psi)
    values, points = _cell_corner_fields(xp, grid, psi)
    geometry = _cell_geometry_fields(xp, grid, psi.dtype)
    threshold = xp.asarray(phase_threshold, dtype=psi.dtype)
    crossings = [
        _edge_crossing(xp, values, points, edge, threshold)
        for edge in range(4)
    ]
    crossing_count = sum(
        crossing["mask"].astype(psi.dtype) for crossing in crossings
    )
    local_energy = xp.zeros_like(values[0])

    for edge_a in range(4):
        for edge_b in range(edge_a + 1, 4):
            mask = (
                (crossing_count == 2.0)
                & crossings[edge_a]["mask"]
                & crossings[edge_b]["mask"]
            )
            crossing_mid = _midline_crossing(
                xp,
                values,
                edge_a,
                edge_b,
                threshold,
                geometry,
                mask,
            )
            p2_mask = mask & crossing_mid["mask"]
            local_energy = local_energy + _p2_local_energy(
                xp,
                crossings[edge_a],
                crossing_mid,
                crossings[edge_b],
                p2_mask,
                sigma=sigma,
            )
            p1_mask = mask & ~crossing_mid["mask"]
            local_energy = local_energy + _p1_local_energy(
                xp,
                crossings[edge_a],
                crossings[edge_b],
                p1_mask,
                sigma=sigma,
            )

    ambiguous = crossing_count == 4.0
    for edge_a, edge_b in ((0, 1), (2, 3)):
        crossing_mid = _midline_crossing(
            xp,
            values,
            edge_a,
            edge_b,
            threshold,
            geometry,
            ambiguous,
        )
        p2_mask = ambiguous & crossing_mid["mask"]
        local_energy = local_energy + _p2_local_energy(
            xp,
            crossings[edge_a],
            crossing_mid,
            crossings[edge_b],
            p2_mask,
            sigma=sigma,
        )
        p1_mask = ambiguous & ~crossing_mid["mask"]
        local_energy = local_energy + _p1_local_energy(
            xp,
            crossings[edge_a],
            crossings[edge_b],
            p1_mask,
            sigma=sigma,
        )

    return xp.sum(local_energy)


def p2_trace_surface_energy_gradient_2d(
    *,
    xp,
    grid,
    psi,
    sigma: float,
    phase_threshold: float = 0.5,
):
    """Return P2 isoparametric trace ``∂E_Γ,h/∂ψ`` on the active backend."""
    if grid.ndim != 2:
        raise ValueError("transport_variational_p2 supports 2D")
    psi = xp.asarray(psi)
    values, points = _cell_corner_fields(xp, grid, psi)
    geometry = _cell_geometry_fields(xp, grid, psi.dtype)
    threshold = xp.asarray(phase_threshold, dtype=psi.dtype)
    crossings = [
        _edge_crossing(xp, values, points, edge, threshold)
        for edge in range(4)
    ]
    crossing_count = sum(
        crossing["mask"].astype(psi.dtype) for crossing in crossings
    )
    local = [xp.zeros_like(values[0]) for _ in range(4)]

    for edge_a in range(4):
        for edge_b in range(edge_a + 1, 4):
            mask = (
                (crossing_count == 2.0)
                & crossings[edge_a]["mask"]
                & crossings[edge_b]["mask"]
            )
            crossing_mid = _midline_crossing(
                xp,
                values,
                edge_a,
                edge_b,
                threshold,
                geometry,
                mask,
            )
            p2_mask = mask & crossing_mid["mask"]
            _add_p2_local_contribution(
                xp,
                local,
                crossings[edge_a],
                crossing_mid,
                crossings[edge_b],
                p2_mask,
                sigma=sigma,
            )
            p1_mask = mask & ~crossing_mid["mask"]
            _add_local_contribution(
                xp,
                local,
                crossings[edge_a],
                crossings[edge_b],
                p1_mask,
                sigma=sigma,
            )

    ambiguous = crossing_count == 4.0
    for edge_a, edge_b in ((0, 1), (2, 3)):
        crossing_mid = _midline_crossing(
            xp,
            values,
            edge_a,
            edge_b,
            threshold,
            geometry,
            ambiguous,
        )
        p2_mask = ambiguous & crossing_mid["mask"]
        _add_p2_local_contribution(
            xp,
            local,
            crossings[edge_a],
            crossing_mid,
            crossings[edge_b],
            p2_mask,
            sigma=sigma,
        )
        p1_mask = ambiguous & ~crossing_mid["mask"]
        _add_local_contribution(
            xp,
            local,
            crossings[edge_a],
            crossings[edge_b],
            p1_mask,
            sigma=sigma,
        )

    gradient = xp.zeros_like(psi)
    gradient[:-1, :-1] = gradient[:-1, :-1] + local[0]
    gradient[1:, :-1] = gradient[1:, :-1] + local[1]
    gradient[1:, 1:] = gradient[1:, 1:] + local[2]
    gradient[:-1, 1:] = gradient[:-1, 1:] + local[3]
    return gradient


def _central_difference_step(xp, base, direction):
    dtype = xp.asarray(base).dtype
    dtype_eps = xp.asarray(xp.finfo(dtype).eps, dtype=dtype)
    base_norm = xp.sqrt(xp.sum(xp.asarray(base) * xp.asarray(base)))
    direction_norm = xp.sqrt(
        xp.sum(xp.asarray(direction) * xp.asarray(direction))
    )
    safe_direction_norm = xp.where(
        direction_norm > xp.asarray(0.0, dtype=dtype),
        direction_norm,
        xp.ones_like(direction_norm),
    )
    return xp.sqrt(dtype_eps) * (
        xp.asarray(1.0, dtype=dtype) + base_norm
    ) / safe_direction_norm


def p2_trace_surface_energy_hessian_product_2d(
    *,
    xp,
    grid,
    psi,
    direction,
    sigma: float,
    phase_threshold: float = 0.5,
):
    """Return matrix-free ``∂²E_Γ,h/∂ψ²`` applied to ``direction``.

    This is the Newton-Krylov operator for the P2 variational capillary
    residual.  The finite-difference length is derived from backend dtype and
    vector scale, never from a fixed tolerance constant.
    """
    base = xp.asarray(psi)
    vector = xp.asarray(direction)
    step = _central_difference_step(xp, base, vector)
    grad_plus = p2_trace_surface_energy_gradient_2d(
        xp=xp,
        grid=grid,
        psi=base + step * vector,
        sigma=sigma,
        phase_threshold=phase_threshold,
    )
    grad_minus = p2_trace_surface_energy_gradient_2d(
        xp=xp,
        grid=grid,
        psi=base - step * vector,
        sigma=sigma,
        phase_threshold=phase_threshold,
    )
    return (grad_plus - grad_minus) / (2.0 * step)


def _negative_face_divergence_adjoint(*, xp, fccd, nodal_covector, axis: int):
    """Return ``(-D_f)^T`` for ``FCCDSolver.face_divergence``."""
    covector = xp.moveaxis(xp.asarray(nodal_covector), axis, 0)
    n_faces = fccd.grid.N[axis]
    weights = fccd._weights[axis]
    if fccd._axis_periodic(axis):
        unique = xp.array(covector[:n_faces], copy=True)
        unique[0] = unique[0] + covector[n_faces]
        if weights["uniform"]:
            weighted = unique * weights["inv_H"]
        else:
            inv_width = fccd._broadcast_axis0(
                weights["inv_H_periodic_node"],
                unique.ndim,
            )
            weighted = unique * inv_width
        adjoint = xp.roll(weighted, -1, axis=0) - weighted
        return xp.moveaxis(adjoint, 0, axis)

    if weights["uniform"]:
        weighted = covector * weights["inv_H"]
    else:
        inv_width = fccd._broadcast_axis0(weights["inv_H_node"], covector.ndim)
        weighted = covector * inv_width
    adjoint = weighted[:-1] - weighted[1:]
    return xp.moveaxis(adjoint, 0, axis)


def transport_variational_pressure_jump_gradient(
    *,
    xp,
    grid,
    psi,
    fccd,
    sigma: float,
    axis: int,
    phase_threshold: float = 0.5,
    trace_space: str = "p1",
):
    """Return a face-gradient jump whose work is transport-adjoint capillarity."""
    if fccd is None:
        raise ValueError("transport_variational capillarity requires FCCD")
    psi = xp.asarray(psi)
    if trace_space == "p2":
        energy_gradient = p2_trace_surface_energy_gradient_2d(
            xp=xp,
            grid=grid,
            psi=psi,
            sigma=float(sigma),
            phase_threshold=float(phase_threshold),
        )
    else:
        energy_gradient = marching_squares_surface_energy_gradient_2d(
            xp=xp,
            grid=grid,
            psi=psi,
            sigma=float(sigma),
            phase_threshold=float(phase_threshold),
        )
    adjoint = _negative_face_divergence_adjoint(
        xp=xp,
        fccd=fccd,
        nodal_covector=energy_gradient,
        axis=axis,
    )
    power_covector = -fccd.face_value(psi, axis) * adjoint

    d_face = xp.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
    d_shape = [1] * grid.ndim
    d_shape[axis] = -1
    transverse_axis = 1 - axis
    face_area = xp.asarray(grid.h[transverse_axis])
    area_shape = [1] * grid.ndim
    area_shape[transverse_axis] = -1
    face_measure = d_face.reshape(d_shape) * face_area.reshape(area_shape)
    return power_covector / face_measure
