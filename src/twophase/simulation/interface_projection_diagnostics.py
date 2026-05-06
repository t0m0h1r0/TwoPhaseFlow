"""Diagnostics for interface projection and capillary face cochains.

Symbol mapping
--------------
``q^-``      -> ``psi_before`` before metric/reinitialization projection.
``q^+``      -> ``psi_after`` after projection and mass closure.
``S_h(q)``   -> ``p2_trace_surface_energy_2d``.
``D_f``      -> ``div_op.divergence_from_faces``.
``a_f``      -> capillary/pressure-jump face cochain.

These helpers are diagnostic only.  They do not alter the interface transport,
Ridge-Eikonal reconstruction, PPE solve, or velocity corrector.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

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


def _face_components_divergence_linf(xp, div_op, face_components, *, dtype) -> Any:
    if not hasattr(div_op, "divergence_from_faces"):
        return xp.asarray(0.0, dtype=dtype)
    div_field = div_op.divergence_from_faces(face_components)
    return xp.max(xp.abs(div_field))


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
