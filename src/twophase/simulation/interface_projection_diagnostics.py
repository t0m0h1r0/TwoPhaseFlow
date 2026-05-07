"""Diagnostics for interface projection and capillary face cochains.

Symbol mapping
--------------
``q^-``      -> ``psi_before`` before metric/reinitialization projection.
``q^+``      -> ``psi_after`` after projection and mass closure.
``S_h(q)``   -> ``p2_trace_surface_energy_2d``.
``D_f``      -> ``div_op.divergence_from_faces``.
``a_f``      -> capillary/pressure-jump face cochain.

The range projection helpers are diagnostic by default.  The
component-augmented helper also returns a corrected face cochain for the
velocity corrector when explicitly selected by the runtime configuration; it
does not alter interface transport or Ridge-Eikonal reconstruction.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..coupling.interface_stress_closure import affine_jump_face_inverse_density
from ..coupling.transport_variational_capillary import p2_trace_surface_energy_2d


_REINIT_ZERO_DIAGNOSTICS = {
    "reinit_triggered": 0.0,
    "reinit_volume_delta": 0.0,
    "reinit_surface_energy_delta": 0.0,
    "reinit_linf_delta": 0.0,
    "reinit_zero_level_displacement": 0.0,
    "reinit_zero_crossing_change_count": 0.0,
}

_FACE_ZERO_DIAGNOSTICS = {
    "capillary_face_linf": 0.0,
    "capillary_face_divergence_linf": 0.0,
    "capillary_jump_linf": 0.0,
    "capillary_range_projection_linf": 0.0,
    "capillary_hodge_residual": 0.0,
    "capillary_hodge_divergence_linf": 0.0,
    "capillary_range_projection_solved": 0.0,
    "capillary_face_weighted_l2": 0.0,
    "capillary_jump_weighted_l2": 0.0,
    "capillary_range_projection_weighted_l2": 0.0,
    "capillary_hodge_weighted_l2": 0.0,
    "capillary_corrected_jump_linf": 0.0,
    "capillary_corrected_jump_weighted_l2": 0.0,
    "capillary_component_hodge_linf": 0.0,
    "capillary_component_hodge_weighted_l2": 0.0,
    "capillary_component_hodge_coefficient_linf": 0.0,
    "capillary_component_hodge_denominator": 0.0,
    "capillary_static_critical_surface_l2": 0.0,
    "capillary_static_critical_residual_l2": 0.0,
    "capillary_static_critical_residual_ratio": 0.0,
    "capillary_static_critical_component_count": 0.0,
}


def zero_reinit_projection_diagnostics() -> dict[str, float]:
    """Return the default no-projection diagnostic row."""
    return dict(_REINIT_ZERO_DIAGNOSTICS)


def zero_capillary_face_diagnostics() -> dict[str, float]:
    """Return the default no-face-cochain diagnostic row."""
    return dict(_FACE_ZERO_DIAGNOSTICS)


def reinit_projection_diagnostics(
    *,
    xp,
    backend,
    grid,
    psi_before,
    psi_after,
    sigma: float,
    phase_threshold: float = 0.5,
) -> dict[str, float]:
    """Measure the metric projection ``q^- -> q^+`` without changing fields."""
    before = xp.asarray(psi_before)
    after = xp.asarray(psi_after)
    dV = xp.asarray(grid.cell_volumes())
    volume_delta = xp.sum((after - before) * dV)
    surface_before = p2_trace_surface_energy_2d(
        xp=xp,
        grid=grid,
        psi=before,
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
    )
    surface_after = p2_trace_surface_energy_2d(
        xp=xp,
        grid=grid,
        psi=after,
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
    )
    zero_disp, crossing_change_count = _zero_level_projection_metrics(
        xp=xp,
        grid=grid,
        psi_before=before,
        psi_after=after,
        phase_threshold=float(phase_threshold),
    )
    raw = xp.stack(
        [
            volume_delta,
            surface_after - surface_before,
            xp.max(xp.abs(after - before)),
            zero_disp,
            crossing_change_count,
        ]
    )
    values = [float(value) for value in backend.asnumpy(raw)]
    return {
        "reinit_triggered": 1.0,
        "reinit_volume_delta": values[0],
        "reinit_surface_energy_delta": values[1],
        "reinit_linf_delta": values[2],
        "reinit_zero_level_displacement": values[3],
        "reinit_zero_crossing_change_count": values[4],
    }


def capillary_face_cochain_diagnostics(
    *,
    xp,
    backend,
    div_op,
    face_components,
    capillary_jump_components=None,
    range_projection_components=None,
    hodge_residual_components=None,
    face_weight_components=None,
    corrected_jump_components=None,
    component_hodge_residual_components=None,
    component_hodge_coefficients=None,
    component_hodge_denominator=None,
    static_criticality=None,
) -> dict[str, float]:
    """Measure the post-PPE face cochain left in the projection face space.

    ``capillary_hodge_residual`` is the infinity norm of
    ``c_f - Π_{range(A_fG_f)}c_f`` when ``hodge_residual_components`` is
    supplied.  The fallback to ``face_components`` is retained only for direct
    low-level diagnostic callers that do not run the range projection.
    """
    if face_components is None:
        return zero_capillary_face_diagnostics()
    face_linf = _face_components_linf(xp, face_components)
    if hasattr(div_op, "divergence_from_faces"):
        div_field = div_op.divergence_from_faces(face_components)
        div_linf = xp.max(xp.abs(div_field))
    else:
        div_linf = xp.asarray(0.0, dtype=face_linf.dtype)
    hodge_components = (
        face_components
        if hodge_residual_components is None
        else hodge_residual_components
    )
    hodge_linf = _face_components_linf(xp, hodge_components)
    hodge_div_linf = _face_components_divergence_linf(
        xp,
        div_op,
        hodge_components,
        dtype=face_linf.dtype,
    )
    jump_linf = _optional_face_components_linf(
        xp,
        capillary_jump_components,
        dtype=face_linf.dtype,
    )
    projection_linf = _optional_face_components_linf(
        xp,
        range_projection_components,
        dtype=face_linf.dtype,
    )
    face_weighted_l2 = _optional_face_components_weighted_l2(
        xp,
        face_components,
        face_weight_components,
        dtype=face_linf.dtype,
    )
    jump_weighted_l2 = _optional_face_components_weighted_l2(
        xp,
        capillary_jump_components,
        face_weight_components,
        dtype=face_linf.dtype,
    )
    projection_weighted_l2 = _optional_face_components_weighted_l2(
        xp,
        range_projection_components,
        face_weight_components,
        dtype=face_linf.dtype,
    )
    hodge_weighted_l2 = _optional_face_components_weighted_l2(
        xp,
        hodge_components,
        face_weight_components,
        dtype=face_linf.dtype,
    )
    corrected_jump_linf = _optional_face_components_linf(
        xp,
        corrected_jump_components,
        dtype=face_linf.dtype,
    )
    corrected_jump_weighted_l2 = _optional_face_components_weighted_l2(
        xp,
        corrected_jump_components,
        face_weight_components,
        dtype=face_linf.dtype,
    )
    component_hodge_linf = _optional_face_components_linf(
        xp,
        component_hodge_residual_components,
        dtype=face_linf.dtype,
    )
    component_hodge_weighted_l2 = _optional_face_components_weighted_l2(
        xp,
        component_hodge_residual_components,
        face_weight_components,
        dtype=face_linf.dtype,
    )
    component_hodge_coefficient_linf = _optional_scalar_linf(
        xp,
        component_hodge_coefficients,
        dtype=face_linf.dtype,
    )
    component_hodge_denominator_value = _optional_scalar_value(
        xp,
        component_hodge_denominator,
        dtype=face_linf.dtype,
    )
    static_surface, static_residual, static_ratio, static_components = (
        _static_criticality_values(static_criticality)
    )
    solved = xp.asarray(
        1.0 if hodge_residual_components is not None else 0.0,
        dtype=face_linf.dtype,
    )
    values = [
        float(value)
        for value in backend.asnumpy(
            xp.stack(
                [
                    face_linf,
                    div_linf,
                    jump_linf,
                    projection_linf,
                    hodge_linf,
                    hodge_div_linf,
                    solved,
                    face_weighted_l2,
                    jump_weighted_l2,
                    projection_weighted_l2,
                    hodge_weighted_l2,
                    corrected_jump_linf,
                    corrected_jump_weighted_l2,
                    component_hodge_linf,
                    component_hodge_weighted_l2,
                    component_hodge_coefficient_linf,
                    component_hodge_denominator_value,
                    xp.asarray(static_surface, dtype=face_linf.dtype),
                    xp.asarray(static_residual, dtype=face_linf.dtype),
                    xp.asarray(static_ratio, dtype=face_linf.dtype),
                    xp.asarray(static_components, dtype=face_linf.dtype),
                ]
            )
        )
    ]
    return {
        "capillary_face_linf": values[0],
        "capillary_face_divergence_linf": values[1],
        "capillary_jump_linf": values[2],
        "capillary_range_projection_linf": values[3],
        "capillary_hodge_residual": values[4],
        "capillary_hodge_divergence_linf": values[5],
        "capillary_range_projection_solved": values[6],
        "capillary_face_weighted_l2": values[7],
        "capillary_jump_weighted_l2": values[8],
        "capillary_range_projection_weighted_l2": values[9],
        "capillary_hodge_weighted_l2": values[10],
        "capillary_corrected_jump_linf": values[11],
        "capillary_corrected_jump_weighted_l2": values[12],
        "capillary_component_hodge_linf": values[13],
        "capillary_component_hodge_weighted_l2": values[14],
        "capillary_component_hodge_coefficient_linf": values[15],
        "capillary_component_hodge_denominator": values[16],
        "capillary_static_critical_surface_l2": values[17],
        "capillary_static_critical_residual_l2": values[18],
        "capillary_static_critical_residual_ratio": values[19],
        "capillary_static_critical_component_count": values[20],
    }


def capillary_jump_range_projection(
    *,
    xp,
    div_op,
    ppe_solver,
    rho,
    pressure_flux_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Project the capillary jump cochain into ``range(A_f G_f)``.

    The projected potential ``q`` solves
    ``D_f A_f G_f q = D_f c_f`` with the same affine cut-face coefficient
    ``A_f`` but with the jump value set to zero in the operator.  The returned
    residual ``c_f - A_fG_fq`` is the discrete Hodge component that cannot be
    represented by the pressure range.
    """
    if not hasattr(div_op, "pressure_fluxes") or not hasattr(
        div_op,
        "divergence_from_faces",
    ):
        raise RuntimeError("capillary range projection requires face flux/divergence")
    if not hasattr(ppe_solver, "solve") or not hasattr(
        ppe_solver,
        "set_interface_jump_context",
    ):
        raise RuntimeError("capillary range projection requires jump-aware PPE solver")

    pressure_zero = xp.zeros_like(rho)
    capillary_flux_at_zero = div_op.pressure_fluxes(
        pressure_zero,
        rho,
        **pressure_flux_kwargs,
    )
    capillary_jump_faces = [
        -xp.asarray(component) for component in capillary_flux_at_zero
    ]
    face_weights = _capillary_face_hodge_weights(
        xp=xp,
        div_op=div_op,
        rho=rho,
        pressure_flux_kwargs=pressure_flux_kwargs,
    )
    source = div_op.divergence_from_faces(capillary_jump_faces)
    zero_jump_kwargs = _zero_jump_pressure_flux_kwargs(pressure_flux_kwargs)
    snapshots = _snapshot_solver_graph(ppe_solver)
    try:
        _invalidate_solver_graph_cache(ppe_solver)
        _set_zero_jump_solver_context(ppe_solver, zero_jump_kwargs)
        projected_pressure = xp.asarray(ppe_solver.solve(source, rho, dt=0.0, p_init=None))
        range_projection_faces = div_op.pressure_fluxes(
            projected_pressure,
            rho,
            **zero_jump_kwargs,
        )
    finally:
        _restore_solver_graph(snapshots)
    hodge_residual_faces = [
        jump_face - projected_face
        for jump_face, projected_face in zip(
            capillary_jump_faces,
            range_projection_faces,
        )
    ]
    return {
        "capillary_jump_components": capillary_jump_faces,
        "range_projection_components": range_projection_faces,
        "hodge_residual_components": hodge_residual_faces,
        "face_weight_components": face_weights,
    }


def capillary_component_hodge_augmented_projection(
    *,
    xp,
    div_op,
    ppe_solver,
    rho,
    pressure_flux_kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Return the one-component augmented Hodge capillary cochain.

    Let ``c`` be the capillary jump cochain and ``b`` the unit component
    pressure-jump cochain on the same cut-face complex.  Adding the component
    volume reaction to the pressure range is equivalent to removing the
    ``M_f``-orthogonal component of the pressure-range Hodge residual along
    ``h_b = b - Π_R b``.  The corrected cochain
    ``c - beta h_b`` has the same divergence as ``c`` up to the projection
    solve residual, so the PPE source remains the same while the corrector no
    longer treats the static component reaction as physical acceleration.
    """
    raw_projection = capillary_jump_range_projection(
        xp=xp,
        div_op=div_op,
        ppe_solver=ppe_solver,
        rho=rho,
        pressure_flux_kwargs=pressure_flux_kwargs,
    )
    component_projection = capillary_jump_range_projection(
        xp=xp,
        div_op=div_op,
        ppe_solver=ppe_solver,
        rho=rho,
        pressure_flux_kwargs=_unit_component_jump_pressure_flux_kwargs(
            xp,
            pressure_flux_kwargs,
        ),
    )
    face_weights = raw_projection["face_weight_components"]
    component_hodge_faces = component_projection["hodge_residual_components"]
    raw_hodge_faces = raw_projection["hodge_residual_components"]
    denominator = _face_components_weighted_dot(
        xp,
        component_hodge_faces,
        component_hodge_faces,
        face_weights,
    )
    numerator = _face_components_weighted_dot(
        xp,
        raw_hodge_faces,
        component_hodge_faces,
        face_weights,
    )
    safe_denominator = xp.where(
        denominator > 0.0,
        denominator,
        xp.ones_like(denominator),
    )
    beta = xp.where(denominator > 0.0, numerator / safe_denominator, 0.0)
    corrected_jump_faces = [
        jump_face - beta * component_hodge_face
        for jump_face, component_hodge_face in zip(
            raw_projection["capillary_jump_components"],
            component_hodge_faces,
            strict=True,
        )
    ]
    augmented_hodge_faces = [
        raw_hodge_face - beta * component_hodge_face
        for raw_hodge_face, component_hodge_face in zip(
            raw_hodge_faces,
            component_hodge_faces,
            strict=True,
        )
    ]
    return {
        **raw_projection,
        "hodge_residual_components": augmented_hodge_faces,
        "corrected_jump_components": corrected_jump_faces,
        "component_hodge_residual_components": component_hodge_faces,
        "component_hodge_coefficients": beta,
        "component_hodge_denominator": denominator,
    }


def _face_components_linf(xp, face_components) -> Any:
    maxima = [xp.max(xp.abs(xp.asarray(component))) for component in face_components]
    if not maxima:
        return xp.asarray(0.0)
    return xp.max(xp.stack(maxima))


def _optional_face_components_linf(xp, face_components, *, dtype) -> Any:
    if face_components is None:
        return xp.asarray(0.0, dtype=dtype)
    return _face_components_linf(xp, face_components)


def _optional_face_components_weighted_l2(
    xp,
    face_components,
    face_weight_components,
    *,
    dtype,
) -> Any:
    if face_components is None or face_weight_components is None:
        return xp.asarray(0.0, dtype=dtype)
    terms = [
        xp.sum(xp.asarray(component) * xp.asarray(component) * xp.asarray(weight))
        for component, weight in zip(
            face_components,
            face_weight_components,
            strict=True,
        )
    ]
    if not terms:
        return xp.asarray(0.0, dtype=dtype)
    return xp.sqrt(xp.sum(xp.stack(terms)))


def _face_components_weighted_dot(
    xp,
    left_components,
    right_components,
    face_weight_components,
) -> Any:
    terms = []
    for axis, (left, right) in enumerate(
        zip(left_components, right_components, strict=True)
    ):
        left_arr = xp.asarray(left)
        right_arr = xp.asarray(right)
        if face_weight_components is None:
            terms.append(xp.sum(left_arr * right_arr))
        else:
            terms.append(
                xp.sum(left_arr * right_arr * xp.asarray(face_weight_components[axis]))
            )
    if not terms:
        return xp.asarray(0.0)
    return xp.sum(xp.stack(terms))


def _optional_scalar_linf(xp, scalar, *, dtype) -> Any:
    if scalar is None:
        return xp.asarray(0.0, dtype=dtype)
    return xp.max(xp.abs(xp.asarray(scalar)))


def _optional_scalar_value(xp, scalar, *, dtype) -> Any:
    if scalar is None:
        return xp.asarray(0.0, dtype=dtype)
    return xp.asarray(scalar, dtype=dtype)


def _static_criticality_values(static_criticality) -> tuple[float, float, float, float]:
    if static_criticality is None:
        return 0.0, 0.0, 0.0, 0.0
    return (
        float(static_criticality.surface_vertex_l2),
        float(static_criticality.residual_l2),
        float(static_criticality.residual_ratio),
        float(static_criticality.component_count),
    )


def _face_components_divergence_linf(xp, div_op, face_components, *, dtype) -> Any:
    if not hasattr(div_op, "divergence_from_faces"):
        return xp.asarray(0.0, dtype=dtype)
    div_field = div_op.divergence_from_faces(face_components)
    return xp.max(xp.abs(div_field))


def _capillary_face_hodge_weights(
    *,
    xp,
    div_op,
    rho,
    pressure_flux_kwargs: dict[str, Any],
) -> list[Any] | None:
    """Return face weights for the ``A_f^{-1}`` Hodge diagnostic norm."""
    fccd = getattr(div_op, "_fccd", None)
    grid = getattr(fccd, "grid", None)
    if grid is None:
        return None
    rho_arr = xp.asarray(rho)
    coefficient_scheme = str(
        pressure_flux_kwargs.get("coefficient_scheme", "phase_density")
    ).strip().lower()
    interface_coupling_scheme = str(
        pressure_flux_kwargs.get("interface_coupling_scheme", "none")
    ).strip().lower()
    context = pressure_flux_kwargs.get("interface_stress_context")
    weights = []
    for axis in range(grid.ndim):
        n_cells = grid.N[axis]

        def sl(start, stop, ax=axis):
            slices = [slice(None)] * grid.ndim
            slices[ax] = slice(start, stop)
            return tuple(slices)

        rho_lo = rho_arr[sl(0, n_cells)]
        rho_hi = rho_arr[sl(1, n_cells + 1)]
        coeff = 2.0 / (rho_lo + rho_hi)
        if (
            coefficient_scheme == "phase_separated"
            and interface_coupling_scheme == "affine_jump"
        ):
            coeff = affine_jump_face_inverse_density(
                xp=xp,
                grid=grid,
                rho=rho_arr,
                axis=axis,
                context=context,
            )
        elif (
            coefficient_scheme == "phase_separated"
            and interface_coupling_scheme != "affine_jump"
        ):
            threshold = pressure_flux_kwargs.get("phase_threshold")
            if threshold is None:
                threshold = 0.5 * (xp.min(rho_arr) + xp.max(rho_arr))
            same_phase = (rho_lo >= threshold) == (rho_hi >= threshold)
            coeff = xp.where(same_phase, coeff, 0.0)

        d_face = xp.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        transverse_axis = 1 - axis
        face_area = xp.asarray(grid.h[transverse_axis])
        area_shape = [1] * grid.ndim
        area_shape[transverse_axis] = -1
        measure = d_face.reshape(d_shape) * face_area.reshape(area_shape)
        weights.append(xp.where(coeff > 0.0, measure / coeff, 0.0))
    return weights


def _zero_jump_pressure_flux_kwargs(pressure_flux_kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs = dict(pressure_flux_kwargs)
    context = kwargs.get("interface_stress_context")
    if context is not None:
        kwargs["interface_stress_context"] = replace(
            context,
            pressure_jump_gas_minus_liquid=None,
            sigma=0.0,
        )
    return kwargs


def _unit_component_jump_pressure_flux_kwargs(
    xp,
    pressure_flux_kwargs: dict[str, Any],
) -> dict[str, Any]:
    kwargs = dict(pressure_flux_kwargs)
    context = kwargs.get("interface_stress_context")
    if context is not None:
        kwargs["interface_stress_context"] = replace(
            context,
            pressure_jump_gas_minus_liquid=xp.ones_like(context.psi),
            kappa_lg=None,
            sigma=0.0,
            cut_face_quadrature=False,
        )
    return kwargs


def _set_zero_jump_solver_context(ppe_solver, pressure_flux_kwargs: dict[str, Any]) -> None:
    context = pressure_flux_kwargs.get("interface_stress_context")
    if context is None:
        return
    kappa = context.kappa_lg
    if kappa is None:
        kappa = context.psi * 0.0
    ppe_solver.set_interface_jump_context(
        psi=context.psi,
        kappa=kappa,
        sigma=0.0,
        psi_previous=context.psi_previous,
        face_curvature_method=context.face_curvature_method,
        transport_variational_nodal_covector=(
            context.transport_variational_nodal_covector
        ),
        transport_variational_psi=context.transport_variational_psi,
        transport_variational_previous_surface_energy=(
            context.transport_variational_previous_surface_energy
        ),
    )


def _snapshot_solver_graph(root) -> list[tuple[Any, dict[str, Any]]]:
    snapshots: list[tuple[Any, dict[str, Any]]] = []
    seen: set[int] = set()
    stack = [root]
    while stack:
        obj = stack.pop()
        obj_id = id(obj)
        if obj_id in seen:
            continue
        seen.add(obj_id)
        snapshots.append(
            (
                obj,
                {
                    key: _snapshot_value(value)
                    for key, value in getattr(obj, "__dict__", {}).items()
                },
            )
        )
        for child_name in ("base_solver", "operator"):
            child = getattr(obj, child_name, None)
            if child is not None:
                stack.append(child)
    return snapshots


def _snapshot_value(value):
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value


def _restore_solver_graph(snapshots: list[tuple[Any, dict[str, Any]]]) -> None:
    for obj, state in snapshots:
        obj.__dict__.clear()
        obj.__dict__.update(state)


def _invalidate_solver_graph_cache(root) -> None:
    seen: set[int] = set()
    stack = [root]
    while stack:
        obj = stack.pop()
        obj_id = id(obj)
        if obj_id in seen:
            continue
        seen.add(obj_id)
        invalidator = getattr(obj, "invalidate_cache", None)
        if callable(invalidator):
            invalidator()
        for child_name in ("base_solver", "operator"):
            child = getattr(obj, child_name, None)
            if child is not None:
                stack.append(child)


def _zero_level_projection_metrics(
    *,
    xp,
    grid,
    psi_before,
    psi_after,
    phase_threshold: float,
):
    displacement_maxima = []
    crossing_changes = []
    threshold = xp.asarray(phase_threshold, dtype=psi_before.dtype)
    for axis in range(grid.ndim):
        n_cells = grid.N[axis]

        def sl(start, stop, ax=axis):
            slices = [slice(None)] * grid.ndim
            slices[ax] = slice(start, stop)
            return tuple(slices)

        before_lo = psi_before[sl(0, n_cells)]
        before_hi = psi_before[sl(1, n_cells + 1)]
        after_lo = psi_after[sl(0, n_cells)]
        after_hi = psi_after[sl(1, n_cells + 1)]
        before_cross = (before_lo < threshold) != (before_hi < threshold)
        after_cross = (after_lo < threshold) != (after_hi < threshold)
        common = before_cross & after_cross
        before_theta = _crossing_fraction(xp, before_lo, before_hi, threshold)
        after_theta = _crossing_fraction(xp, after_lo, after_hi, threshold)
        d_face = xp.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        displacement = xp.abs(after_theta - before_theta) * d_face.reshape(d_shape)
        displacement_maxima.append(
            xp.max(xp.where(common, displacement, xp.zeros_like(displacement)))
        )
        crossing_changes.append(xp.sum((before_cross != after_cross).astype(psi_before.dtype)))
    return xp.max(xp.stack(displacement_maxima)), xp.sum(xp.stack(crossing_changes))


def _crossing_fraction(xp, lo, hi, threshold):
    denom = hi - lo
    safe = xp.where(xp.abs(denom) > 1.0e-30, denom, xp.ones_like(denom))
    return (threshold - lo) / safe
