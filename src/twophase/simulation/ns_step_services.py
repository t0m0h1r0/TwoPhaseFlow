"""Step-stage helper services for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.array_checks import all_arrays_exact_zero
from ..core.boundary import is_all_periodic
from ..ns_terms.context import NSComputeContext
from .ns_predictor_assembly import (
    select_buoyancy_predictor_state_assembly,
    select_gravity_aligned_axis,
    select_transverse_axis,
)
from ..coupling.interface_stress_closure import build_young_laplace_interface_stress_context
from ..coupling.capillary_geometry import apply_wall_compatible_curvature
from ..coupling.closed_interface_riesz import closed_interface_riesz_cochain
from ..coupling.transport_variational_capillary import (
    p2_trace_surface_energy_ale_discrete_gradient_2d,
    p2_trace_surface_energy_discrete_gradient_2d,
    p2_trace_surface_energy_gradient_2d,
)
from .interface_projection_diagnostics import (
    capillary_component_hodge_augmented_projection,
    capillary_external_component_saddle_projection,
    capillary_jump_range_projection,
    capillary_face_cochain_diagnostics,
    capillary_pressure_adjoint_face_weights,
    zero_capillary_face_diagnostics,
)
from .geometric_capillary_reaction_split import (
    build_geometric_capillary_reaction_split,
)
from .geometric_phase_runtime import (
    GeometricRuntimeCapillaryApplicationState,
    validate_geometric_runtime_capillary_application_admitted,
)
from .gravity_covector import build_variational_gravity_faces
from .face_boundary import (
    zero_wall_normal_face_components,
    zero_wall_velocity_face_components,
)
from .boundary_hodge import project_wall_trace, wall_trace_from_faces
from .ns_predictor_face_state import FaceNativePredictorAssembly
from .ns_step_state import NSStepState

IMEX_BDF2_PROJECTION_FACTOR = 2.0 / 3.0
_JUMP_CURVATURE_METHODS = {
    "face_implicit",
    "transport_variational",
    "transport_variational_p2",
    "transport_variational_p2_midpoint",
    "transport_variational_p2_discrete_gradient",
    "transport_variational_p2_ale_discrete_gradient",
}


@dataclass
class PressureJumpStageContext:
    """Operation-local pressure-jump artifacts shared inside one PPE stage."""

    transport_temporaries: dict
    trace_projection_diagnostics: dict | None = None
    corrected_capillary_components: list | None = None


def _backend_is_gpu(backend) -> bool:
    return bool(getattr(backend, "is_gpu", lambda: False)())


def _apply_solver_interface_jump(ppe_solver, base_pressure):
    """Map a base pressure to the solver's physical pressure representation."""
    applier = getattr(ppe_solver, "apply_interface_jump", None)
    if callable(applier):
        return applier(base_pressure)
    operator = getattr(ppe_solver, "operator", None)
    applier = getattr(operator, "apply_interface_jump", None)
    if callable(applier):
        return applier(base_pressure)
    return base_pressure


def _scalar_from_backend(backend, xp, value) -> float:
    return float(np.asarray(backend.to_host(xp.asarray(value))))


def _face_linf(backend, xp, components: list) -> float:
    if not components:
        return 0.0
    return max(
        _scalar_from_backend(backend, xp, xp.max(xp.abs(component)))
        for component in components
    )


def _face_pair_shapes_match(left: list, right: list) -> bool:
    return len(left) == len(right) and all(
        tuple(left_component.shape) == tuple(right_component.shape)
        for left_component, right_component in zip(left, right, strict=True)
    )


def _projection_base_face_components(*, xp, state: NSStepState, div_op) -> tuple[list, bool]:
    """Return a projection-native face base and whether carried faces were used."""
    base_faces = [
        xp.asarray(component) for component in div_op.face_fluxes([state.u, state.v])
    ]
    carried_source = state.projected_face_components
    if carried_source is None:
        carried_source = state.face_velocity_components
    if carried_source is None:
        return base_faces, False
    carried_faces = [xp.asarray(component) for component in carried_source]
    if _face_pair_shapes_match(carried_faces, base_faces):
        return carried_faces, True
    return base_faces, False


def _geometric_to_projection_face_pair_2d(
    *,
    xp,
    grid,
    face_pair: list,
    boundary: tuple[str, str] = ("wall", "wall"),
) -> list:
    """Map AO cell-face increments to the NS projection face lattice.

    A3 mapping:
      Equation: ``u_f^* += Pi_CF(dt M_C^{-1} r_sigma)``.
      Discretization: AO capillary increments live on cell faces
      ``((Nx+1,Ny),(Nx,Ny+1))`` as integrated face-volume cochains, while the
      nodal-control-volume projection uses point velocities on the dual face
      lattice ``((Nx,Ny+1),(Nx+1,Ny))``.  ``Pi_CF`` first divides by the
      physical face measure and then applies tensor P1 interpolation between
      the two face lattices, using physical nonuniform distances at nodes.
      Code: this backend-native slice kernel performs the cochain-to-velocity
      conversion and interpolation before wall-face projection and PPE use.
    """
    if grid is None or getattr(grid, "ndim", None) != 2:
        raise ValueError("AO capillary face bridge requires a 2D grid")
    nx, ny = int(grid.N[0]), int(grid.N[1])
    x_face = xp.asarray(face_pair[0])
    y_face = xp.asarray(face_pair[1])
    if tuple(x_face.shape) != (nx + 1, ny) or tuple(y_face.shape) != (nx, ny + 1):
        raise ValueError(
            "AO capillary face increment must use geometric cell-face "
            f"shapes {((nx + 1, ny), (nx, ny + 1))}; got "
            f"{(tuple(x_face.shape), tuple(y_face.shape))}"
        )

    dx = xp.asarray(grid.coords[0][1:] - grid.coords[0][:-1], dtype=x_face.dtype)
    dy = xp.asarray(grid.coords[1][1:] - grid.coords[1][:-1], dtype=x_face.dtype)
    x_velocity = x_face / dy.reshape((1, ny))
    y_velocity = y_face / dx.reshape((nx, 1))

    x_mid = 0.5 * (x_velocity[:-1, :] + x_velocity[1:, :])
    projected_x = xp.empty((nx, ny + 1), dtype=x_face.dtype)
    _cell_center_to_nodes_axis1(
        xp=xp,
        values=x_mid,
        widths=dy,
        out=projected_x,
        periodic=boundary[1] == "periodic",
    )

    y_mid = 0.5 * (y_velocity[:, :-1] + y_velocity[:, 1:])
    projected_y = xp.empty((nx + 1, ny), dtype=y_face.dtype)
    _cell_center_to_nodes_axis0(
        xp=xp,
        values=y_mid,
        widths=dx,
        out=projected_y,
        periodic=boundary[0] == "periodic",
    )
    return [projected_x, projected_y]


def _cell_center_to_nodes_axis0(*, xp, values, widths, out, periodic: bool) -> None:
    n = int(values.shape[0])
    if periodic:
        seam = (
            widths[0] * values[-1, :] + widths[-1] * values[0, :]
        ) / (widths[-1] + widths[0])
        out[0, :] = seam
        out[n, :] = seam
    else:
        out[0, :] = values[0, :]
        out[n, :] = values[-1, :]
    if n > 1:
        denom = (widths[:-1] + widths[1:]).reshape((-1, 1))
        left_weight = widths[1:].reshape((-1, 1)) / denom
        right_weight = widths[:-1].reshape((-1, 1)) / denom
        out[1:n, :] = left_weight * values[:-1, :] + right_weight * values[1:, :]


def _cell_center_to_nodes_axis1(*, xp, values, widths, out, periodic: bool) -> None:
    n = int(values.shape[1])
    if periodic:
        seam = (
            widths[0] * values[:, -1] + widths[-1] * values[:, 0]
        ) / (widths[-1] + widths[0])
        out[:, 0] = seam
        out[:, n] = seam
    else:
        out[:, 0] = values[:, 0]
        out[:, n] = values[:, -1]
    if n > 1:
        denom = (widths[:-1] + widths[1:]).reshape((1, -1))
        lower_weight = widths[1:].reshape((1, -1)) / denom
        upper_weight = widths[:-1].reshape((1, -1)) / denom
        out[:, 1:n] = lower_weight * values[:, :-1] + upper_weight * values[:, 1:]


def _ao_application_boundary(application) -> tuple[str, str]:
    capillary = getattr(application, "capillary", None)
    material = getattr(capillary, "material", None)
    face_hodge = getattr(material, "face_hodge", None)
    return tuple(getattr(face_hodge, "boundary", ("wall", "wall")))


def _ao_predictor_increment_for_projection_faces(
    *,
    xp,
    grid,
    application,
    reference_faces: list,
) -> tuple[list, str]:
    return _ao_face_pair_for_projection_faces(
        xp=xp,
        grid=grid,
        face_pair=application.predictor_face_increment,
        reference_faces=reference_faces,
        boundary=_ao_application_boundary(application),
        label="predictor",
    )


def _ao_pressure_reaction_increment_for_projection_faces(
    *,
    xp,
    grid,
    application,
    reference_faces: list,
) -> tuple[list, str]:
    return _ao_face_pair_for_projection_faces(
        xp=xp,
        grid=grid,
        face_pair=application.pressure_reaction_face_increment,
        reference_faces=reference_faces,
        boundary=_ao_application_boundary(application),
        label="pressure reaction",
    )


def _ao_capillary_acceleration_for_projection_faces(
    *,
    xp,
    grid,
    face_pair,
    reference_faces: list,
    boundary: tuple[str, str],
    label: str,
) -> tuple[list, str]:
    return _ao_face_pair_for_projection_faces(
        xp=xp,
        grid=grid,
        face_pair=face_pair,
        reference_faces=reference_faces,
        boundary=boundary,
        label=label,
    )


def _needs_geometric_pressure_reaction_split(application) -> bool:
    capillary = getattr(application, "capillary", None)
    return (
        str(
            getattr(
                application,
                "pressure_reaction_projection_status",
                getattr(capillary, "pressure_reaction_projection_status", ""),
            )
        ).strip().lower()
        == "pressure_reaction_projection_pending"
    )


def _split_pending_geometric_capillary_application(
    state: NSStepState,
    *,
    backend,
    xp,
    div_op,
    ppe_solver,
    ppe_runtime,
    grid,
    reference_faces: list,
    curvature_method: str,
) -> tuple[GeometricRuntimeCapillaryApplicationState, str]:
    """Build the pressure-adjoint split before AO predictor application."""
    application = state.geometric_runtime_capillary_application
    if application is None:
        raise ValueError("AO capillary split requires an application packet")
    if not _needs_geometric_pressure_reaction_split(application):
        return application, "already_split"
    if ppe_solver is None:
        raise RuntimeError("AO pressure-reaction split requires the active PPE solver")
    raw_acceleration, raw_face_space = _ao_capillary_acceleration_for_projection_faces(
        xp=xp,
        grid=grid,
        face_pair=application.predictor_face_acceleration,
        reference_faces=reference_faces,
        boundary=_ao_application_boundary(application),
        label="raw source acceleration",
    )
    component_accelerations = tuple(
        getattr(application.capillary, "component_reaction_accelerations", ())
    )
    if not component_accelerations:
        raise ValueError(
            "AO pressure_component_hodge split requires at least one "
            "cell-volume reaction direction"
        )
    component_faces = []
    for index, component in enumerate(component_accelerations):
        faces, _ = _ao_capillary_acceleration_for_projection_faces(
            xp=xp,
            grid=grid,
            face_pair=component,
            reference_faces=reference_faces,
            boundary=_ao_application_boundary(application),
            label=f"component-{index} reaction acceleration",
        )
        component_faces.append(faces)
    pressure_flux_kwargs = _pressure_face_flux_kwargs(
        xp=xp,
        state=state,
        ppe_runtime=ppe_runtime,
        interface_sigma=0.0,
        curvature_method=curvature_method,
    )
    face_weights = capillary_pressure_adjoint_face_weights(
        xp=xp,
        div_op=div_op,
        rho=state.rho,
        pressure_flux_kwargs=pressure_flux_kwargs,
    )
    if face_weights is None:
        raise RuntimeError(
            "AO pressure-reaction split requires pressure-adjoint face weights"
        )
    split = build_geometric_capillary_reaction_split(
        xp=xp,
        div_op=div_op,
        ppe_solver=ppe_solver,
        rho=state.rho,
        pressure_flux_kwargs=pressure_flux_kwargs,
        raw_source_face_acceleration=raw_acceleration,
        component_reaction_face_accelerations=tuple(component_faces),
        face_weight_components=face_weights,
    )
    split_application = _application_from_geometric_capillary_split(
        application,
        split,
        backend=backend,
        xp=xp,
    )
    validate_geometric_runtime_capillary_application_admitted(split_application)
    state.geometric_runtime_capillary_application = split_application
    certificate = dict(state.conservative_transport_certificate or {})
    certificate.update(
        {
            "ao_pressure_reaction_projection_status": split.status,
            "ao_pressure_reaction_projection_face_space": raw_face_space,
            "ao_pressure_reaction_projection_raw_l2": _scalar_from_backend(
                backend,
                xp,
                split.raw_source_weighted_l2,
            ),
            "ao_pressure_reaction_projection_corrected_l2": _scalar_from_backend(
                backend,
                xp,
                split.corrected_source_weighted_l2,
            ),
            "ao_pressure_reaction_projection_range_l2": _scalar_from_backend(
                backend,
                xp,
                split.pressure_range_weighted_l2,
            ),
            "ao_pressure_reaction_projection_balanced_l2": _scalar_from_backend(
                backend,
                xp,
                split.balanced_weighted_l2,
            ),
            "ao_pressure_reaction_projection_pressure_adjoint_residual": (
                _scalar_from_backend(backend, xp, split.pressure_adjoint_residual)
            ),
            "ao_pressure_reaction_projection_saddle_constraint_linf": (
                _scalar_from_backend(backend, xp, split.saddle_constraint_linf)
            ),
        }
    )
    state.conservative_transport_certificate = certificate
    return split_application, raw_face_space


def _application_from_geometric_capillary_split(
    application,
    split,
    *,
    backend,
    xp,
) -> GeometricRuntimeCapillaryApplicationState:
    dt = float(application.dt)
    predictor_acceleration = tuple(
        xp.asarray(component) for component in split.corrected_source_face_acceleration
    )
    pressure_acceleration = tuple(
        xp.asarray(component) for component in split.pressure_range_face_acceleration
    )
    balanced_acceleration = tuple(
        xp.asarray(component) for component in split.balanced_face_acceleration
    )
    predictor_increment = tuple(dt * component for component in predictor_acceleration)
    pressure_increment = tuple(dt * component for component in pressure_acceleration)
    balanced_increment = tuple(dt * component for component in balanced_acceleration)
    tolerance = float(application.capillary.pressure_range_tolerance)
    balanced_l2 = dt * _scalar_from_backend(backend, xp, split.balanced_weighted_l2)
    balanced_max = dt * _scalar_from_backend(
        backend,
        xp,
        split.max_abs_balanced_face_acceleration,
    )
    pressure_exact_static = balanced_l2 <= tolerance and balanced_max <= tolerance
    return GeometricRuntimeCapillaryApplicationState(
        capillary=application.capillary,
        dt=dt,
        predictor_face_acceleration=predictor_acceleration,
        pressure_reaction_face_acceleration=pressure_acceleration,
        predictor_face_increment=predictor_increment,
        pressure_reaction_face_increment=pressure_increment,
        pressure_balanced_face_increment=balanced_increment,
        predictor_increment_weighted_l2=(
            dt
            * _scalar_from_backend(backend, xp, split.corrected_source_weighted_l2)
        ),
        pressure_reaction_increment_weighted_l2=(
            dt * _scalar_from_backend(backend, xp, split.pressure_range_weighted_l2)
        ),
        pressure_balanced_increment_weighted_l2=balanced_l2,
        max_abs_pressure_balanced_face_increment=balanced_max,
        pressure_exact_static=pressure_exact_static,
        capillary_drive_present=not pressure_exact_static,
        pressure_reaction_coordinate=xp.asarray(split.pressure_range_coordinate),
        face_hodge_weights=split.face_weight_components,
        pressure_reaction_projection_status=split.status,
    )


def _ao_face_pair_for_projection_faces(
    *,
    xp,
    grid,
    face_pair,
    reference_faces: list,
    boundary: tuple[str, str],
    label: str,
) -> tuple[list, str]:
    increments = [xp.asarray(component) for component in face_pair]
    if _face_pair_shapes_match(increments, reference_faces):
        return increments, "projection_native"
    projected = _geometric_to_projection_face_pair_2d(
        xp=xp,
        grid=grid,
        face_pair=increments,
        boundary=boundary,
    )
    if not _face_pair_shapes_match(projected, reference_faces):
        reference_shapes = tuple(tuple(face.shape) for face in reference_faces)
        raise ValueError(
            f"AO capillary {label} bridge did not produce projection-native "
            f"face shapes {reference_shapes}"
        )
    return projected, "geometric_cell_face_p1_to_projection_face"


def _capillary_interface_psi(*, xp, state: NSStepState, curvature_method: str):
    """Return the interface geometry used by the capillary jump operator.

    A3 mapping:
      Equation: ``g_Γ^{n+1/2}=∂E_{Γ,h}(ψ^{n+1/2})`` with
      ``ψ^{n+1/2}=(ψ^n+ψ^{n+1})/2`` for the midpoint P2 route.
      Discretization: ``ψ^n`` is the operation-local previous step state,
      already remapped to the current grid when the fitted grid rebuilds.
      Code: pressure-jump and face-corrector contexts receive the same
      backend-native ``interface_psi`` temporary.
    """
    if (
        curvature_method == "transport_variational_p2_midpoint"
        and state.psi_previous is not None
    ):
        half = xp.asarray(0.5, dtype=xp.asarray(state.psi).dtype)
        return half * (xp.asarray(state.psi_previous) + xp.asarray(state.psi))
    return state.psi


def _capillary_interface_psi_previous(
    *, state: NSStepState, curvature_method: str
):
    """Return the previous interface state needed by discrete-gradient routes."""
    if curvature_method in {
        "transport_variational_p2_discrete_gradient",
        "transport_variational_p2_ale_discrete_gradient",
    }:
        return state.psi_previous
    return None


def _capillary_transport_variational_temporaries(
    *,
    xp,
    state: NSStepState,
    curvature_method: str,
    grid,
    sigma: float,
) -> dict:
    """Build operation-local P2 covectors once for GPU pressure-jump work.

    These arrays are step temporaries attached to the jump context; they are
    not reused after the pressure/corrector operation that requested them.
    """
    if grid is None or curvature_method not in {
        "transport_variational_p2",
        "transport_variational_p2_midpoint",
        "transport_variational_p2_discrete_gradient",
        "transport_variational_p2_ale_discrete_gradient",
    }:
        return {}
    interface_psi = _capillary_interface_psi(
        xp=xp,
        state=state,
        curvature_method=curvature_method,
    )
    if curvature_method in {
        "transport_variational_p2_discrete_gradient",
        "transport_variational_p2_ale_discrete_gradient",
    }:
        previous = _capillary_interface_psi_previous(
            state=state,
            curvature_method=curvature_method,
        )
        if previous is None:
            return {}
        current = xp.asarray(interface_psi)
        previous = xp.asarray(previous)
        transport_psi = xp.asarray(0.5, dtype=current.dtype) * (previous + current)
        if curvature_method == "transport_variational_p2_ale_discrete_gradient":
            covector = p2_trace_surface_energy_ale_discrete_gradient_2d(
                xp=xp,
                grid=grid,
                psi_previous=previous,
                psi=current,
                sigma=float(sigma),
                previous_surface_energy=(
                    state.transport_variational_previous_surface_energy
                ),
            )
        else:
            covector = p2_trace_surface_energy_discrete_gradient_2d(
                xp=xp,
                grid=grid,
                psi_previous=previous,
                psi=current,
                sigma=float(sigma),
            )
        return {
            "transport_variational_nodal_covector": covector,
            "transport_variational_psi": transport_psi,
            "transport_variational_previous_surface_energy": (
                state.transport_variational_previous_surface_energy
            ),
        }
    covector = p2_trace_surface_energy_gradient_2d(
        xp=xp,
        grid=grid,
        psi=interface_psi,
        sigma=float(sigma),
    )
    return {
        "transport_variational_nodal_covector": covector,
        "transport_variational_psi": interface_psi,
    }


def _pressure_face_flux_kwargs(
    *,
    xp,
    state: NSStepState,
    ppe_runtime,
    interface_sigma: float | None = None,
    curvature_method: str = "psi_direct_filtered",
    interface_psi=None,
    interface_psi_previous=None,
    transport_variational_temporaries=None,
) -> dict:
    """Return face-pressure kwargs for the projection-native pressure law.

    A3 mapping:
      Equation: ``G_Γ(p;j)=G_f(p)-B_Γ(j)``.
      Discretization: face-normal pressure acceleration uses the same
      coefficient, gradient, and affine jump context as PPE projection.
      Code: ``div_op.pressure_fluxes(p, rho, **kwargs)``.
    """
    if ppe_runtime is None:
        return {}
    kwargs = {
        "pressure_gradient": (
            "fccd"
            if getattr(ppe_runtime, "ppe_solver_name", None) == "fccd_iterative"
            else "fvm"
        ),
    }
    pressure_force_contract = getattr(
        ppe_runtime,
        "pressure_force_contract",
        "raw_compact_gradient",
    )
    if pressure_force_contract != "raw_compact_gradient":
        kwargs["pressure_force_contract"] = pressure_force_contract
    if getattr(ppe_runtime, "ppe_coefficient_scheme", None) == "phase_separated":
        kwargs["coefficient_scheme"] = "phase_separated"
    if getattr(ppe_runtime, "ppe_interface_coupling_scheme", "none") == "affine_jump":
        sigma = state.sigma if interface_sigma is None else float(interface_sigma)
        kwargs["interface_coupling_scheme"] = "affine_jump"
        kwargs["interface_stress_context"] = (
            build_young_laplace_interface_stress_context(
                xp=xp,
                psi=state.psi if interface_psi is None else interface_psi,
                kappa_lg=state.kappa,
                sigma=sigma,
                psi_previous=interface_psi_previous,
                **(transport_variational_temporaries or {}),
                face_curvature_method=(
                    curvature_method
                    if curvature_method in _JUMP_CURVATURE_METHODS
                    else "nodal_cut_face"
                ),
            )
        )
    return kwargs


def _pressure_history_mode(ppe_runtime) -> str:
    """Return the active pressure-history representation."""
    return str(
        getattr(ppe_runtime, "pressure_history_mode", "face_acceleration")
    ).strip().lower()


def _uses_static_geometric_capillary_application(state: NSStepState) -> bool:
    """Return whether AO static capillarity has already consumed the force slot."""
    application = state.geometric_runtime_capillary_application
    certificate = state.conservative_transport_certificate or {}
    return bool(
        application is not None
        and application.pressure_exact_static
        and certificate.get("ao_static_surface_tension_applied") is True
    )


def _uses_nonstatic_geometric_capillary_application(state: NSStepState) -> bool:
    """Return whether AO non-static capillarity owns the surface-force slot."""
    application = state.geometric_runtime_capillary_application
    certificate = state.conservative_transport_certificate or {}
    return bool(
        application is not None
        and not application.pressure_exact_static
        and application.capillary_drive_present
        and certificate.get("ao_nonstatic_surface_tension_slot_bypassed") is True
    )


def _uses_geometric_capillary_surface_slot(state: NSStepState) -> bool:
    return (
        _uses_static_geometric_capillary_application(state)
        or _uses_nonstatic_geometric_capillary_application(state)
    )


def _pressure_coordinate_history_base(*, xp, state: NSStepState, ppe_runtime):
    """Extrapolate scalar pressure coordinates for pressure-adjoint history."""
    previous = state.previous_base_pressure
    if previous is None:
        return None
    previous = xp.asarray(previous)
    extrapolation = str(
        getattr(ppe_runtime, "pressure_history_extrapolation", "constant")
    ).strip().lower()
    if (
        extrapolation == "bdf2"
        and state.previous_previous_base_pressure is not None
    ):
        return 2.0 * previous - xp.asarray(state.previous_previous_base_pressure)
    return previous


def _affine_pressure_history_jump_offset(xp, pressure_flux_kwargs: dict | None):
    """Return the nodal jump offset stripped from smooth pressure history.

    Affine-jump face laws consume the physical discontinuous pressure in
    ``G(p)-B(j)``.  Grid-rebuild history, however, must transport the smooth
    phase pressure representative.  The same reduced coordinate as the HFE
    split is ``p_reduced = p_physical - j_gl (1-psi)``.
    """
    if not pressure_flux_kwargs:
        return None
    if pressure_flux_kwargs.get("interface_coupling_scheme") != "affine_jump":
        return None
    context = pressure_flux_kwargs.get("interface_stress_context")
    if context is None:
        return None
    psi = getattr(context, "psi", None)
    if psi is None:
        return None
    pressure_jump = getattr(context, "pressure_jump_gas_minus_liquid", None)
    if pressure_jump is None:
        kappa = getattr(context, "kappa_lg", None)
        sigma = float(getattr(context, "sigma", 0.0))
        if kappa is None or sigma == 0.0:
            return None
        pressure_jump = -sigma * xp.asarray(kappa)
    return xp.asarray(pressure_jump) * (1.0 - xp.asarray(psi))


def _decode_affine_pressure_history_coordinate(
    xp,
    pressure_coordinate,
    pressure_flux_kwargs: dict | None,
):
    """Convert the smooth stored history coordinate to physical pressure."""
    offset = _affine_pressure_history_jump_offset(xp, pressure_flux_kwargs)
    if offset is None:
        return pressure_coordinate
    return xp.asarray(pressure_coordinate) + offset


def _encode_affine_pressure_history_coordinate(
    xp,
    physical_pressure,
    pressure_flux_kwargs: dict | None,
):
    """Convert physical affine-jump pressure to the smooth stored coordinate."""
    offset = _affine_pressure_history_jump_offset(xp, pressure_flux_kwargs)
    if offset is None:
        return physical_pressure
    return xp.asarray(physical_pressure) - offset


def _pressure_coordinate_history_faces(
    *,
    xp,
    state: NSStepState,
    div_op,
    ppe_runtime,
    curvature_method: str,
    capillary_force_source: str,
    grid,
) -> tuple[object | None, list | None]:
    """Build pressure-history faces by reapplying current-metric ``G_var``.

    A3 mapping:
      Equation: ``r_p^E=-D_f^T W_p lambda^E`` and
      ``a_p^E=M_f^{-1}r_p^E``.
      Discretization: the stored scalar coordinate ``lambda`` is extrapolated,
      then converted to face reaction by the active pressure-adjoint flux
      operator using the current density/interface metric.
      Code: no old face-acceleration array is reused.
    """
    base = _pressure_coordinate_history_base(
        xp=xp,
        state=state,
        ppe_runtime=ppe_runtime,
    )
    if base is None:
        return None, None
    closed_interface_source = (
        capillary_force_source == "closed_interface_riesz"
        and not _uses_geometric_capillary_surface_slot(state)
    )
    history_jump_sigma = (
        0.0
        if closed_interface_source or _uses_geometric_capillary_surface_slot(state)
        else state.sigma
    )
    interface_psi = _capillary_interface_psi(
        xp=xp,
        state=state,
        curvature_method=curvature_method,
    )
    interface_psi_previous = _capillary_interface_psi_previous(
        state=state,
        curvature_method=curvature_method,
    )
    transport_temporaries = _capillary_transport_variational_temporaries(
        xp=xp,
        state=state,
        curvature_method=curvature_method,
        grid=grid,
        sigma=history_jump_sigma,
    )
    kwargs = _pressure_face_flux_kwargs(
        xp=xp,
        state=state,
        ppe_runtime=ppe_runtime,
        interface_sigma=history_jump_sigma,
        curvature_method=curvature_method,
        interface_psi=interface_psi,
        interface_psi_previous=interface_psi_previous,
        transport_variational_temporaries=transport_temporaries,
    )
    physical_base = _decode_affine_pressure_history_coordinate(xp, base, kwargs)
    return physical_base, div_op.pressure_fluxes(physical_base, state.rho, **kwargs)


def _closed_interface_trace_projection_diagnostics(projection) -> dict:
    """Adapt trace-Riesz projection output to capillary diagnostic kwargs."""
    component_hodge_components = None
    if projection.component_hodge_residual_components:
        component_hodge_components = projection.component_hodge_residual_components[0]
    return {
        "capillary_jump_components": projection.capillary_jump_components,
        "range_projection_components": projection.range_projection_components,
        "hodge_residual_components": projection.hodge_residual_components,
        "face_weight_components": projection.face_weight_components,
        "corrected_jump_components": projection.corrected_capillary_components,
        "component_hodge_residual_components": component_hodge_components,
        "component_hodge_coefficients": projection.component_hodge_coefficients,
        "component_hodge_denominator": projection.component_hodge_denominator,
        "static_criticality": projection.static_criticality,
    }


def _closed_interface_trace_psi(*, state: NSStepState):
    """Use transported geometry before metric/reinit projection when available."""
    return (
        state.psi_transport_endpoint
        if state.psi_transport_endpoint is not None
        else state.psi
    )


def build_pressure_robust_buoyancy_residual_accel_faces(
    *,
    buoyancy_force_components: list,
    rho,
    rho_ref: float,
    g_acc: float,
    div_op,
    xp,
    coords=None,
    Y=None,
    pressure_gradient: str = "fccd",
    pressure_coefficient_scheme: str = "phase_separated",
) -> list | None:
    """Return buoyancy residual acceleration on projection-native faces.

    A3 mapping:
      Equation: ``rho' g = -grad(rho' Phi_g) + Phi_g grad(rho')``.
      Discretization: ``a_f^res = face(f_b/rho) + (1/rho)_f G_f(rho'Phi_g)``.
      Code: ``div_op.face_fluxes`` and ``div_op.pressure_fluxes`` reuse the
      same non-uniform-grid face operator as the PPE corrector.
    """
    if (
        len(buoyancy_force_components) < 2
        or g_acc == 0.0
        or div_op is None
        or not hasattr(div_op, "face_fluxes")
        or not hasattr(div_op, "pressure_fluxes")
    ):
        return None
    coordinate_fields = coords
    if coordinate_fields is None and Y is not None:
        coordinate_fields = [None] * len(buoyancy_force_components)
        coordinate_fields[-1] = Y
    if coordinate_fields is None:
        return None
    preferred_axis = None
    if Y is not None:
        preferred_axis = len(buoyancy_force_components) - 1
    elif coordinate_fields is not None:
        populated_axes = [
            axis
            for axis, coordinate_field in enumerate(coordinate_fields)
            if coordinate_field is not None
        ]
        if len(populated_axes) == 1:
            preferred_axis = populated_axes[0]
    gravity_axis = select_gravity_aligned_axis(
        buoyancy_force_components,
        xp,
        preferred_axis=preferred_axis,
    )
    if gravity_axis is None:
        gravity_axis = len(buoyancy_force_components) - 1
    if gravity_axis >= len(coordinate_fields):
        return None
    gravity_coordinate = coordinate_fields[gravity_axis]
    if gravity_coordinate is None:
        return None

    rho_excess = rho - rho_ref
    hydrostatic_scalar = rho_excess * float(g_acc) * xp.asarray(gravity_coordinate)
    buoyancy_accel_components = [
        xp.asarray(component) / rho for component in buoyancy_force_components
    ]
    buoyancy_accel_faces = div_op.face_fluxes(buoyancy_accel_components)
    try:
        hydrostatic_accel_faces = div_op.pressure_fluxes(
            hydrostatic_scalar,
            rho,
            pressure_gradient=pressure_gradient,
            coefficient_scheme=pressure_coefficient_scheme,
        )
    except TypeError:
        hydrostatic_accel_faces = div_op.pressure_fluxes(hydrostatic_scalar, rho)
    return [
        buoyancy_face + hydrostatic_face
        for buoyancy_face, hydrostatic_face in zip(
            buoyancy_accel_faces,
            hydrostatic_accel_faces,
        )
    ]


def materialise_ns_step_fields(state: NSStepState) -> NSStepState:
    """Build density and viscosity fields for the current step."""
    if state.conservative_density is not None:
        state.rho = state.conservative_density
    else:
        state.rho = state.rho_g + (state.rho_l - state.rho_g) * state.psi
    if state.mu_l is not None and state.mu_g is not None:
        state.mu_field = state.mu_g + (state.mu_l - state.mu_g) * state.psi
    else:
        state.mu_field = state.mu
    return state


def _interface_supported_curvature(kappa, psi, *, xp, psi_min: float | None):
    """Preserve the CLS curvature invariant ``kappa=0`` off the interface."""
    if psi_min is None or psi_min <= 0.0:
        return kappa
    band = (psi > psi_min) & (psi < 1.0 - psi_min)
    return xp.where(band, kappa, 0.0)


def compute_ns_surface_tension_stage(
    state: NSStepState,
    *,
    backend,
    curv,
    curvature_filter,
    interface_runtime,
    step_diag,
    st_force,
    ccd,
    grid,
    bc_type: str,
    surface_tension_grad_op,
    projection_consistent_buoyancy: bool,
) -> NSStepState:
    """Compute curvature and balanced-force surface tension terms."""
    xp = backend.xp
    kappa_raw = curv.compute(state.psi)
    state.kappa = curvature_filter.apply(xp.asarray(kappa_raw), xp.asarray(state.psi))
    state.kappa = _interface_supported_curvature(
        state.kappa,
        state.psi,
        xp=xp,
        psi_min=getattr(curv, "psi_min", 0.01),
    )
    state.kappa = apply_wall_compatible_curvature(
        xp=xp,
        grid=grid,
        psi=state.psi,
        kappa_lg=state.kappa,
        bc_type=bc_type,
        psi_min=getattr(curv, "psi_min", 0.01),
    )
    if interface_runtime.kappa_max is not None:
        state.kappa = xp.clip(
            state.kappa,
            -interface_runtime.kappa_max,
            interface_runtime.kappa_max,
        )
    state.debug_scalars = None
    if step_diag.enabled:
        state.debug_scalars = [xp.max(xp.abs(state.kappa))]

    state.f_x, state.f_y = st_force.compute(
        state.kappa,
        state.psi,
        state.sigma,
        ccd,
        grad_op=surface_tension_grad_op,
    )
    if projection_consistent_buoyancy and state.g_acc != 0.0:
        state.f_y = state.f_y - (state.rho - state.rho_ref) * state.g_acc
    return state


def compute_ns_geometric_static_surface_tension_stage(
    state: NSStepState,
    *,
    backend,
    step_diag,
    projection_consistent_buoyancy: bool,
    tolerance: float | None = None,
) -> NSStepState:
    """Consume a pressure-exact AO capillary application without legacy CSF.

    A3 mapping:
      Equation: static Young-Laplace balance gives
      ``dt a_sigma - dt a_pi = 0`` on faces under the runtime convention where
      ``a_pi`` is the pressure-reaction acceleration that cancels the capillary
      predictor drive.
      Discretization: AO capillary predictor and pressure-reaction increments
      are face-native cochains; exact static balance has zero residual
      pressure-balanced increment.
      Code: the nodal surface-tension force supplied to legacy predictor/PPE
      slots is the zero covector, with the AO face packet retained for the
      downstream pressure/momentum route.
    """
    application = state.geometric_runtime_capillary_application
    if application is None:
        raise ValueError(
            "geometric_cell_fraction surface tension requires an AO capillary "
            "application packet"
        )
    if not application.pressure_exact_static:
        raise ValueError(
            "geometric_cell_fraction non-static capillary application requires "
            "downstream AO momentum and PPE integration"
        )
    if tolerance is None:
        tolerance = application.capillary.pressure_range_tolerance
    tolerance = float(tolerance)
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be finite and non-negative")
    if (
        application.pressure_balanced_increment_weighted_l2 > tolerance
        or application.max_abs_pressure_balanced_face_increment > tolerance
    ):
        raise ValueError(
            "pressure-exact geometric capillary application has a non-zero "
            "pressure-balanced increment"
        )

    xp = backend.xp
    state.kappa = xp.zeros_like(state.psi)
    state.debug_scalars = None
    if step_diag.enabled:
        state.debug_scalars = [xp.asarray(0.0, dtype=xp.asarray(state.psi).dtype)]

    state.f_x = xp.zeros_like(state.u)
    state.f_y = xp.zeros_like(state.v)
    if projection_consistent_buoyancy and state.g_acc != 0.0:
        if state.rho is None:
            raise ValueError(
                "geometric static surface tension with buoyancy requires "
                "materialised density"
            )
        state.f_y = state.f_y - (state.rho - state.rho_ref) * state.g_acc

    certificate = dict(state.conservative_transport_certificate or {})
    certificate.update(
        {
            "ao_static_surface_tension_applied": True,
            "ao_static_surface_tension_l2_tolerance": tolerance,
            "ao_static_surface_tension_force_source": (
                "geometric_pressure_exact_static"
            ),
            "ao_static_surface_tension_balanced_increment_weighted_l2": (
                application.pressure_balanced_increment_weighted_l2
            ),
            "ao_static_surface_tension_balanced_max_abs_face_increment": (
                application.max_abs_pressure_balanced_face_increment
            ),
        }
    )
    state.conservative_transport_certificate = certificate
    return state


def compute_ns_geometric_surface_tension_stage(
    state: NSStepState,
    *,
    backend,
    step_diag,
    projection_consistent_buoyancy: bool,
) -> NSStepState:
    """Consume AO capillarity without returning to legacy curvature/CSF."""
    application = state.geometric_runtime_capillary_application
    if application is None:
        raise ValueError(
            "geometric_cell_fraction surface tension requires an AO capillary "
            "application packet"
        )
    if application.pressure_exact_static:
        return compute_ns_geometric_static_surface_tension_stage(
            state,
            backend=backend,
            step_diag=step_diag,
            projection_consistent_buoyancy=projection_consistent_buoyancy,
        )
    if not application.capillary_drive_present:
        raise ValueError(
            "non-static geometric capillary application must carry a capillary "
            "predictor drive"
        )

    xp = backend.xp
    state.kappa = xp.zeros_like(state.psi)
    state.debug_scalars = None
    if step_diag.enabled:
        state.debug_scalars = [xp.asarray(0.0, dtype=xp.asarray(state.psi).dtype)]
    state.f_x = xp.zeros_like(state.u)
    state.f_y = xp.zeros_like(state.v)
    if projection_consistent_buoyancy and state.g_acc != 0.0:
        if state.rho is None:
            raise ValueError(
                "geometric non-static surface tension with buoyancy requires "
                "materialised density"
            )
        state.f_y = state.f_y - (state.rho - state.rho_ref) * state.g_acc

    certificate = dict(state.conservative_transport_certificate or {})
    certificate.update(
        {
            "ao_nonstatic_surface_tension_slot_bypassed": True,
            "ao_nonstatic_capillary_predictor_pending": True,
            "ao_nonstatic_capillary_predictor_increment_weighted_l2": (
                application.predictor_increment_weighted_l2
            ),
            "ao_nonstatic_pressure_reaction_increment_weighted_l2": (
                application.pressure_reaction_increment_weighted_l2
            ),
        }
    )
    state.conservative_transport_certificate = certificate
    return state


def compute_ns_predictor_stage(
    state: NSStepState,
    *,
    backend,
    ccd,
    conv_term,
    viscous_predictor,
    scheme_runtime,
    conv_ab2_ready: bool,
    conv_prev,
    velocity_bdf2_ready: bool = False,
    velocity_prev=None,
    projection_consistent_buoyancy: bool,
    face_native_predictor_state: bool = False,
    face_no_slip_boundary_state: bool = False,
    div_op=None,
    bc_type: str = "wall",
    cn_buoyancy_predictor_assembly_mode: str = "none",
    pressure_grad_op=None,
    Y=None,
    coords=None,
    ppe_coefficient_scheme: str = "phase_separated",
    conservative_momentum_transport: bool = False,
    ppe_runtime=None,
    ppe_solver=None,
    curvature_method: str = "psi_direct_filtered",
    capillary_force_source: str = "curvature_jump",
    grid=None,
) -> tuple[NSStepState, bool, tuple | None, bool, tuple | None]:
    """Advance the momentum predictor stage."""
    xp = backend.xp
    if conservative_momentum_transport:
        conv_u = xp.zeros_like(state.u)
        conv_v = xp.zeros_like(state.v)
    else:
        conv_ctx = NSComputeContext(
            velocity=[state.u, state.v],
            ccd=ccd,
            rho=state.rho,
            mu=state.mu_field,
        )
        conv_u, conv_v = conv_term.compute(conv_ctx)

    gravity_formulation = str(
        getattr(scheme_runtime, "gravity_formulation", "body_acceleration")
    ).strip().lower()
    variational_gravity = (
        gravity_formulation == "variational_potential" and state.g_acc != 0.0
    )
    if gravity_formulation == "none":
        buoy_v = xp.zeros_like(state.v)
    elif variational_gravity:
        if projection_consistent_buoyancy:
            raise RuntimeError(
                "variational_potential gravity is mutually exclusive with "
                "projection_consistent_buoyancy."
            )
        if cn_buoyancy_predictor_assembly_mode != "none":
            raise RuntimeError(
                "variational_potential gravity requires predictor assembly 'none'; "
                "legacy balanced buoyancy would double-count the same potential."
            )
        if div_op is None or not hasattr(div_op, "_fccd") or Y is None:
            raise RuntimeError(
                "variational_potential gravity requires FCCD face transport and "
                "the vertical coordinate field."
            )
        gravity_faces = build_variational_gravity_faces(
            xp=xp,
            fccd=div_op._fccd,
            rho=state.rho,
            vertical_coordinate=Y,
            g_acc=state.g_acc,
            gravity_axis=1,
        )
        gravity_accel_faces = gravity_faces.acceleration_components
        if not is_all_periodic(bc_type, 2) and state.bc_hook is None:
            if face_no_slip_boundary_state:
                gravity_accel_faces = zero_wall_velocity_face_components(
                    gravity_accel_faces,
                    xp=xp,
                    bc_type=bc_type,
                )
            else:
                gravity_accel_faces = zero_wall_normal_face_components(
                    gravity_accel_faces,
                    xp=xp,
                    bc_type=bc_type,
                )
        state.gravity_covector_face_components = gravity_faces.covector_components
        state.gravity_accel_face_components = gravity_accel_faces
        state.gravity_face_density_components = gravity_faces.face_density_components
        state.gravity_force_diagnostics = {
            "formulation": "variational_potential",
            "transport_adjoint": getattr(
                scheme_runtime,
                "gravity_transport_adjoint",
                "common_flux",
            ),
            "metric": getattr(
                scheme_runtime,
                "gravity_metric",
                "transported_face_mass",
            ),
        }
        buoy_v = xp.zeros_like(state.v)
    else:
        buoy_v = xp.zeros_like(state.v)
    if (
        gravity_formulation == "body_acceleration"
        and state.g_acc != 0.0
        and not projection_consistent_buoyancy
    ):
        buoy_v = -(state.rho - state.rho_ref) / state.rho * state.g_acc
    buoyancy_components = [xp.zeros_like(state.u), state.rho * buoy_v]

    next_conv_prev = conv_prev
    next_conv_ab2_ready = conv_ab2_ready
    next_velocity_prev = velocity_prev
    next_velocity_bdf2_ready = velocity_bdf2_ready
    convection_history_ready = conv_ab2_ready and conv_prev is not None
    if conservative_momentum_transport:
        convection_history_ready = True
    bdf2_history_ready = (
        convection_history_ready and velocity_bdf2_ready and velocity_prev is not None
    )
    if conservative_momentum_transport:
        conv_step_u = conv_u
        conv_step_v = conv_v
        next_conv_prev = None
        next_conv_ab2_ready = False
    elif scheme_runtime.convection_time_scheme == "ab2":
        if conv_ab2_ready and conv_prev is not None:
            conv_step_u = 1.5 * conv_u - 0.5 * conv_prev[0]
            conv_step_v = 1.5 * conv_v - 0.5 * conv_prev[1]
        else:
            conv_step_u = conv_u
            conv_step_v = conv_v
        next_conv_prev = (xp.copy(conv_u), xp.copy(conv_v))
        next_conv_ab2_ready = True
    elif scheme_runtime.convection_time_scheme == "imex_bdf2":
        if bdf2_history_ready:
            conv_step_u = 2.0 * conv_u - conv_prev[0]
            conv_step_v = 2.0 * conv_v - conv_prev[1]
        else:
            conv_step_u = conv_u
            conv_step_v = conv_v
        next_conv_prev = (xp.copy(conv_u), xp.copy(conv_v))
        next_conv_ab2_ready = True
    else:
        conv_step_u = conv_u
        conv_step_v = conv_v

    previous_pressure_accel_faces = None
    previous_pressure_accel_nodes = None
    can_use_pressure_history_faces = (
        face_native_predictor_state
        and div_op is not None
        and hasattr(div_op, "face_fluxes")
        and hasattr(div_op, "reconstruct_nodes")
    )
    if (
        can_use_pressure_history_faces
        and hasattr(div_op, "pressure_fluxes")
        and _pressure_history_mode(ppe_runtime) == "pressure_coordinate"
    ):
        (
            state.pressure_extrapolated_base,
            previous_pressure_accel_faces,
        ) = _pressure_coordinate_history_faces(
            xp=xp,
            state=state,
            div_op=div_op,
            ppe_runtime=ppe_runtime,
            curvature_method=curvature_method,
            capillary_force_source=capillary_force_source,
            grid=grid,
        )
        if previous_pressure_accel_faces is not None:
            state.pressure_history_face_components = [
                xp.asarray(component) for component in previous_pressure_accel_faces
            ]
            previous_pressure_accel_nodes = div_op.reconstruct_nodes(
                previous_pressure_accel_faces
            )
            conv_step_u = conv_step_u - previous_pressure_accel_nodes[0]
            conv_step_v = conv_step_v - previous_pressure_accel_nodes[1]
    elif (
        can_use_pressure_history_faces
        and state.previous_pressure_accel_face_components is not None
    ):
        previous_pressure_accel_faces = [
            xp.asarray(component)
            for component in state.previous_pressure_accel_face_components
        ]
        previous_pressure_accel_nodes = div_op.reconstruct_nodes(
            previous_pressure_accel_faces
        )
        conv_step_u = conv_step_u - previous_pressure_accel_nodes[0]
        conv_step_v = conv_step_v - previous_pressure_accel_nodes[1]
    elif state.previous_pressure is not None:
        if pressure_grad_op is None:
            raise RuntimeError("IPC predictor requires pressure_grad_op for ∇p^n")
        dpn_dx = pressure_grad_op.gradient(state.previous_pressure, 0)
        dpn_dy = pressure_grad_op.gradient(state.previous_pressure, 1)
        conv_step_u = conv_step_u - dpn_dx / state.rho
        conv_step_v = conv_step_v - dpn_dy / state.rho

    predictor_kwargs = {}
    face_state_assembly = None
    projection_base_faces = None
    carried_projection_face_state = False
    if (
        face_native_predictor_state
        and div_op is not None
        and hasattr(div_op, "face_fluxes")
    ):
        projection_base_faces, carried_projection_face_state = (
            _projection_base_face_components(xp=xp, state=state, div_op=div_op)
        )
    can_use_face_state = (
        face_native_predictor_state
        and carried_projection_face_state
        and div_op is not None
        and hasattr(div_op, "face_fluxes")
        and hasattr(div_op, "reconstruct_nodes")
    )
    if can_use_face_state and cn_buoyancy_predictor_assembly_mode != "none":
        face_state_assembly = FaceNativePredictorAssembly(
            xp=xp,
            state=state,
            div_op=div_op,
            bc_type=bc_type,
            face_no_slip_boundary_state=face_no_slip_boundary_state,
            residual_accel_builder=(
                build_pressure_robust_buoyancy_residual_accel_faces
            ),
            coords=coords,
            Y=Y,
            ppe_coefficient_scheme=ppe_coefficient_scheme,
        )
        selection = select_buoyancy_predictor_state_assembly(
            mode=cn_buoyancy_predictor_assembly_mode,
            fullband_state_transform=face_state_assembly.fullband_state_transform,
            residual_buoyancy_force_builder=(
                face_state_assembly.residual_face_buoyancy_force_builder
            ),
        )
        if selection.predictor_state_assembly is not None:
            predictor_kwargs["predictor_state_assembly"] = selection.predictor_state_assembly
        repair_mode = selection.cn_intermediate_state_repair_mode
        if repair_mode == "transverse_fullband_local":
            preferred_axis = len(buoyancy_components) - 1 if Y is not None else None
            transverse_axis = select_transverse_axis(
                buoyancy_components,
                xp,
                preferred_axis=preferred_axis,
            )
            if transverse_axis is not None:
                predictor_kwargs["intermediate_velocity_operator_transform"] = (
                    face_state_assembly.fullband_component_transform(transverse_axis)
                )

    if scheme_runtime.convection_time_scheme == "imex_bdf2" and bdf2_history_ready:
        state.projection_dt = IMEX_BDF2_PROJECTION_FACTOR * state.dt
        if not hasattr(viscous_predictor, "predict_bdf2"):
            raise TypeError(
                "IMEX-BDF2 momentum requires a viscous predictor with predict_bdf2()."
            )
        state.u_star, state.v_star = viscous_predictor.predict_bdf2(
            state.u,
            state.v,
            velocity_prev[0],
            velocity_prev[1],
            conv_step_u,
            conv_step_v,
            state.mu_field,
            state.rho,
            state.dt,
            ccd,
            buoy_v=buoy_v,
            psi=state.psi,
        )
    else:
        state.projection_dt = state.dt
        state.u_star, state.v_star = viscous_predictor.predict(
            state.u,
            state.v,
            conv_step_u,
            conv_step_v,
            state.mu_field,
            state.rho,
            state.dt,
            ccd,
            buoy_v=buoy_v,
            psi=state.psi,
            **predictor_kwargs,
        )
    if face_native_predictor_state and div_op is not None and hasattr(div_op, "face_fluxes"):
        state.predictor_face_components = None
        if projection_base_faces is None:
            projection_base_faces, _ = _projection_base_face_components(
                xp=xp,
                state=state,
                div_op=div_op,
            )
        predictor_delta_faces = div_op.face_fluxes(
            [state.u_star - state.u, state.v_star - state.v]
        )
        if (
            face_state_assembly is not None
            and face_state_assembly.face_residual_buoyancy_state is not None
        ):
            residual_faces, residual_nodes = (
                face_state_assembly.face_residual_buoyancy_state
            )
            residual_node_faces = div_op.face_fluxes(residual_nodes)
            predictor_delta_faces = [
                delta_face + state.dt * (residual_face - residual_node_face)
                for delta_face, residual_face, residual_node_face in zip(
                    predictor_delta_faces,
                    residual_faces,
                    residual_node_faces,
                )
            ]
        if (
            previous_pressure_accel_faces is not None
            and previous_pressure_accel_nodes is not None
        ):
            pressure_node_faces = div_op.face_fluxes(previous_pressure_accel_nodes)
            pressure_history_dt = (
                state.projection_dt
                if state.projection_dt is not None
                else state.dt
            )
            predictor_delta_faces = [
                delta_face
                - pressure_history_dt * (pressure_face - node_face)
                for delta_face, pressure_face, node_face in zip(
                    predictor_delta_faces,
                    previous_pressure_accel_faces,
                    pressure_node_faces,
                )
            ]
        if state.gravity_accel_face_components is not None:
            gravity_dt = (
                state.projection_dt
                if state.projection_dt is not None
                else state.dt
            )
            predictor_delta_faces = [
                delta_face + gravity_dt * gravity_face
                for delta_face, gravity_face in zip(
                    predictor_delta_faces,
                    state.gravity_accel_face_components,
                )
            ]
        state.predictor_face_components = [
            base_face + delta_face
            for base_face, delta_face in zip(
                projection_base_faces,
                predictor_delta_faces,
            )
        ]
        ao_capillary_predictor_applied = False
        if _uses_nonstatic_geometric_capillary_application(state):
            application = state.geometric_runtime_capillary_application
            if state.predictor_face_components is None:
                raise ValueError(
                    "non-static AO capillary predictor requires face-native "
                    "predictor components"
                )
            if _needs_geometric_pressure_reaction_split(application):
                application, _ = _split_pending_geometric_capillary_application(
                    state,
                    backend=backend,
                    xp=xp,
                    div_op=div_op,
                    ppe_solver=ppe_solver,
                    ppe_runtime=ppe_runtime,
                    grid=grid,
                    reference_faces=state.predictor_face_components,
                    curvature_method=curvature_method,
                )
            if application.pressure_exact_static:
                certificate = dict(state.conservative_transport_certificate or {})
                certificate.update(
                    {
                        "ao_static_surface_tension_applied": True,
                        "ao_static_surface_tension_force_source": (
                            "geometric_pressure_reaction_split"
                        ),
                        "ao_static_split_downstream_unblocked": True,
                        "ao_static_surface_tension_balanced_increment_weighted_l2": (
                            application.pressure_balanced_increment_weighted_l2
                        ),
                        "ao_static_surface_tension_balanced_max_abs_face_increment": (
                            application.max_abs_pressure_balanced_face_increment
                        ),
                    }
                )
                state.conservative_transport_certificate = certificate
            else:
                increments, increment_face_space = (
                    _ao_predictor_increment_for_projection_faces(
                        xp=xp,
                        grid=grid,
                        application=application,
                        reference_faces=state.predictor_face_components,
                    )
                )
                state.predictor_face_components = [
                    predictor_face + increment
                    for predictor_face, increment in zip(
                        state.predictor_face_components,
                        increments,
                    )
                ]
                state.geometric_capillary_predictor_applied = True
                ao_capillary_predictor_applied = True
                certificate = dict(state.conservative_transport_certificate or {})
                certificate.update(
                    {
                        "ao_capillary_predictor_face_increment_applied": True,
                        "ao_capillary_predictor_increment_weighted_l2": (
                            application.predictor_increment_weighted_l2
                        ),
                        "ao_capillary_predictor_face_space": increment_face_space,
                        "ao_pressure_reaction_increment_pending": True,
                    }
                )
                state.conservative_transport_certificate = certificate
        if not is_all_periodic(bc_type, 2) and state.bc_hook is None:
            if face_no_slip_boundary_state:
                state.predictor_face_components = zero_wall_velocity_face_components(
                    state.predictor_face_components,
                    xp=xp,
                    bc_type=bc_type,
                )
            else:
                state.predictor_face_components = zero_wall_normal_face_components(
                    state.predictor_face_components,
                    xp=xp,
                    bc_type=bc_type,
                )
        if ao_capillary_predictor_applied and hasattr(div_op, "reconstruct_nodes"):
            state.u_star, state.v_star = div_op.reconstruct_nodes(
                state.predictor_face_components
            )
    if scheme_runtime.convection_time_scheme == "imex_bdf2":
        next_velocity_prev = (xp.copy(state.u), xp.copy(state.v))
        next_velocity_bdf2_ready = True
    return (
        state,
        next_conv_ab2_ready,
        next_conv_prev,
        next_velocity_bdf2_ready,
        next_velocity_prev,
    )


def _pressure_stage_predictor_rhs(
    state: NSStepState,
    *,
    xp,
    div_op,
    projection_dt: float,
    face_native_predictor_state: bool,
    bc_type: str,
    face_no_slip_boundary_state: bool,
):
    """Return the PPE RHS contribution from the predictor velocity."""
    predictor_faces = None
    if face_native_predictor_state and state.predictor_face_components is not None:
        predictor_faces = state.predictor_face_components
    if predictor_faces is None or not hasattr(div_op, "divergence_from_faces"):
        return div_op.divergence([state.u_star, state.v_star]) / projection_dt
    if not is_all_periodic(bc_type, 2) and state.bc_hook is None:
        if face_no_slip_boundary_state:
            predictor_faces = zero_wall_velocity_face_components(
                predictor_faces,
                xp=xp,
                bc_type=bc_type,
            )
        else:
            predictor_faces = zero_wall_normal_face_components(
                predictor_faces,
                xp=xp,
                bc_type=bc_type,
            )
    return div_op.divergence_from_faces(predictor_faces) / projection_dt


def _prepare_nonstatic_geometric_pressure_reaction(
    state: NSStepState,
    *,
    backend,
    xp,
    div_op,
    grid,
    projection_dt: float,
    bc_type: str,
    face_no_slip_boundary_state: bool,
) -> None:
    """Prepare the AO pressure-reaction cochain for the face-native PPE.

    A3 mapping:
      Equation: the AO split provides the pressure-range increment ``dt a_pi``
      paired with the predictor increment ``dt a_sigma``.
      Discretization: the increment is converted to the projection face lattice,
      constrained by the active predictor-face boundary convention, divided by
      ``dt`` to form ``a_pi``, and converted to the source cochain
      ``D_f a_pi`` without leaving the active array backend.
      Code: store the face increment and its divergence source on the step state
      so the scalar PPE/corrector integration can consume the exact same arrays.
    """
    if state.predictor_face_components is None:
        raise ValueError(
            "non-static AO pressure reaction requires face-native predictor "
            "components"
        )
    if not hasattr(div_op, "divergence_from_faces"):
        raise RuntimeError("non-static AO pressure reaction requires face divergence")
    application = state.geometric_runtime_capillary_application
    increments, increment_face_space = (
        _ao_pressure_reaction_increment_for_projection_faces(
            xp=xp,
            grid=grid,
            application=application,
            reference_faces=state.predictor_face_components,
        )
    )
    if not is_all_periodic(bc_type, 2) and state.bc_hook is None:
        if face_no_slip_boundary_state:
            increments = zero_wall_velocity_face_components(
                increments,
                xp=xp,
                bc_type=bc_type,
            )
        else:
            increments = zero_wall_normal_face_components(
                increments,
                xp=xp,
                bc_type=bc_type,
            )
    acceleration = [increment / projection_dt for increment in increments]
    rhs = div_op.divergence_from_faces(acceleration)
    reaction_coordinate = getattr(
        application,
        "pressure_reaction_coordinate",
        None,
    )
    state.geometric_capillary_pressure_reaction_face_increment = increments
    state.geometric_capillary_pressure_reaction_face_acceleration = acceleration
    state.geometric_capillary_pressure_reaction_coordinate = (
        None if reaction_coordinate is None else xp.asarray(reaction_coordinate)
    )
    state.geometric_capillary_pressure_reaction_rhs = rhs
    state.geometric_capillary_pressure_reaction_prepared = True
    certificate = dict(state.conservative_transport_certificate or {})
    certificate.update(
        {
            "ao_pressure_reaction_increment_pending": False,
            "ao_pressure_reaction_increment_prepared": True,
            "ao_pressure_reaction_face_space": increment_face_space,
            "ao_pressure_reaction_increment_weighted_l2": (
                application.pressure_reaction_increment_weighted_l2
            ),
            "ao_pressure_reaction_increment_linf": _face_linf(
                backend,
                xp,
                increments,
            ),
            "ao_pressure_reaction_acceleration_linf": _face_linf(
                backend,
                xp,
                acceleration,
            ),
            "ao_pressure_reaction_rhs_linf": _scalar_from_backend(
                backend,
                xp,
                xp.max(xp.abs(rhs)),
            ),
            "ao_pressure_reaction_coordinate_available": (
                reaction_coordinate is not None
            ),
        }
    )
    state.conservative_transport_certificate = certificate


def _pressure_jump_grid(ppe_solver, div_op):
    """Return the grid used by the active pressure-jump operator."""
    jump_grid = getattr(ppe_solver, "grid", None)
    if jump_grid is None:
        jump_grid = getattr(getattr(ppe_solver, "operator", None), "grid", None)
    if jump_grid is None:
        jump_grid = getattr(getattr(div_op, "_fccd", None), "grid", None)
    return jump_grid


def _suppress_geometric_surface_jump_sigma(
    state: NSStepState,
    *,
    surface_tension_scheme: str,
) -> float:
    """Return the legacy pressure-jump sigma after AO surface-slot ownership."""
    if _uses_geometric_capillary_surface_slot(state):
        return 0.0
    return state.sigma if surface_tension_scheme == "pressure_jump" else 0.0


def _pressure_fluxes_for_active_operator(div_op, pressure, rho, kwargs: dict):
    """Evaluate pressure faces with only kwargs supported by the active operator."""
    if type(div_op).__name__ == "FVMDivergenceOperator":
        return div_op.pressure_fluxes(pressure, rho)
    return div_op.pressure_fluxes(pressure, rho, **kwargs)


def _embed_nonstatic_geometric_pressure_reaction_corrector(
    state: NSStepState,
    *,
    xp,
    div_op,
    ppe_runtime,
    curvature_method: str,
    pressure_flux_kwargs: dict | None,
) -> None:
    """Add the prepared AO pressure reaction to face pressure corrections.

    A3 mapping:
      Equation: ``u^{n+1}=u^* - dt(a_p + a_pi)`` with
      ``D a_p = D(u^*)/dt - D a_pi``.
      Discretization: scalar PPE pressure faces provide ``a_p`` on the same
      projection face lattice, while the AO packet supplies ``a_pi`` directly.
      Code: store ``a_p+a_pi`` in the existing face-native corrector fields so
      the standard corrector subtraction cannot double-count ``dt a_pi``.
    """
    reaction_faces = state.geometric_capillary_pressure_reaction_face_acceleration
    if reaction_faces is None:
        raise ValueError(
            "non-static AO pressure reaction corrector requires prepared "
            "face acceleration"
        )
    if not hasattr(div_op, "pressure_fluxes"):
        raise RuntimeError(
            "non-static AO pressure reaction corrector requires pressure faces"
        )
    if state.pressure_correction_face_components is None:
        kwargs = (
            dict(pressure_flux_kwargs)
            if pressure_flux_kwargs is not None
            else _pressure_face_flux_kwargs(
                xp=xp,
                state=state,
                ppe_runtime=ppe_runtime,
                interface_sigma=0.0,
                curvature_method=curvature_method,
            )
        )
        scalar_faces = _pressure_fluxes_for_active_operator(
            div_op,
            state.pressure_increment,
            state.rho,
            kwargs,
        )
        state.pressure_correction_face_components = [
            xp.asarray(component) for component in scalar_faces
        ]
    scalar_correction_faces = [
        xp.asarray(component) for component in state.pressure_correction_face_components
    ]
    scalar_full_faces = (
        [xp.asarray(component) for component in state.pressure_accel_face_components]
        if state.pressure_accel_face_components is not None
        else scalar_correction_faces
    )
    state.geometric_capillary_scalar_pressure_face_components = scalar_full_faces
    state.pressure_correction_face_components = [
        xp.asarray(correction_face) + xp.asarray(reaction_face)
        for correction_face, reaction_face in zip(
            scalar_correction_faces,
            reaction_faces,
            strict=True,
        )
    ]
    if state.pressure_accel_face_components is None:
        state.pressure_accel_face_components = [
            xp.asarray(pressure_face) + xp.asarray(reaction_face)
            for pressure_face, reaction_face in zip(
                scalar_full_faces,
                reaction_faces,
                strict=True,
            )
        ]
    else:
        state.pressure_accel_face_components = [
            xp.asarray(pressure_face) + xp.asarray(reaction_face)
            for pressure_face, reaction_face in zip(
                scalar_full_faces,
                reaction_faces,
                strict=True,
            )
        ]
    certificate = dict(state.conservative_transport_certificate or {})
    certificate.update(
        {
            "ao_scalar_ppe_solve_completed": True,
            "ao_pressure_reaction_rhs_subtracted": True,
            "ao_pressure_reaction_corrector_embedded": True,
        }
    )
    state.conservative_transport_certificate = certificate


def _install_nonstatic_geometric_pressure_coordinate(
    state: NSStepState,
    *,
    xp,
    ppe_solver,
) -> None:
    """Store the scalar AO pressure coordinate after face embedding.

    The face corrector has already consumed ``a_pi`` directly.  The scalar
    coordinate is retained in ``pressure_base`` only as the current-step full
    pressure representation.  It must not become pressure history: AO geometric
    pressure reaction is a constraint response recomputed from the current
    active geometry, not a smooth hydrodynamic phase pressure to extrapolate
    through HFE/affine history.
    """
    coordinate = state.geometric_capillary_pressure_reaction_coordinate
    if coordinate is None:
        raise ValueError(
            "non-static AO pressure reaction requires the scalar coordinate "
            "from the pressure-adjoint split"
        )
    state.pressure_base = xp.asarray(state.pressure_base) + xp.asarray(coordinate)
    state.pressure = _apply_solver_interface_jump(ppe_solver, state.pressure_base)
    certificate = dict(state.conservative_transport_certificate or {})
    certificate.update(
        {
            "ao_pressure_reaction_coordinate_embedded": True,
        }
    )
    state.conservative_transport_certificate = certificate


def _smooth_pressure_history_base_without_ao_reaction(
    xp,
    state: NSStepState,
):
    """Return the smooth pressure coordinate admissible for history storage."""
    base = xp.asarray(state.pressure_base)
    coordinate = state.geometric_capillary_pressure_reaction_coordinate
    if _uses_nonstatic_geometric_capillary_application(state):
        if coordinate is None:
            raise ValueError(
                "non-static AO pressure-coordinate history requires the "
                "geometric pressure reaction coordinate to separate the "
                "smooth HFE history variable"
            )
        return base - xp.asarray(coordinate)
    return base


def _install_pressure_jump_context(
    state: NSStepState,
    *,
    xp,
    div_op,
    ppe_solver,
    ppe_runtime,
    curvature_method: str,
    closed_interface_source: bool,
    physical_jump_sigma: float,
    rhs,
) -> tuple[object, PressureJumpStageContext]:
    """Install the PPE jump context and add closed-interface RHS if needed."""
    if closed_interface_source and not hasattr(ppe_solver, "set_interface_jump_context"):
        raise RuntimeError("closed_interface_riesz requires a jump-aware PPE solver")
    if not hasattr(ppe_solver, "set_interface_jump_context"):
        return rhs, PressureJumpStageContext(transport_temporaries={})

    jump_sigma = 0.0 if closed_interface_source else physical_jump_sigma
    interface_psi = _capillary_interface_psi(
        xp=xp,
        state=state,
        curvature_method=curvature_method,
    )
    interface_psi_previous = _capillary_interface_psi_previous(
        state=state,
        curvature_method=curvature_method,
    )
    jump_grid = _pressure_jump_grid(ppe_solver, div_op)
    transport_temporaries = _capillary_transport_variational_temporaries(
        xp=xp,
        state=state,
        curvature_method=curvature_method,
        grid=jump_grid,
        sigma=physical_jump_sigma,
    )

    trace_projection_diagnostics = None
    corrected_capillary_components = None
    if closed_interface_source:
        if not hasattr(div_op, "divergence_from_faces"):
            raise RuntimeError("closed_interface_riesz requires face divergence")
        fccd = getattr(div_op, "_fccd", None)
        if fccd is None:
            raise RuntimeError("closed_interface_riesz requires the active FCCD operator")
        if jump_grid is None:
            raise RuntimeError("closed_interface_riesz requires a pressure-jump grid")
        pressure_flux_kwargs_for_projection = _pressure_face_flux_kwargs(
            xp=xp,
            state=state,
            ppe_runtime=ppe_runtime,
            interface_sigma=jump_sigma,
            curvature_method=curvature_method,
            interface_psi=interface_psi,
            interface_psi_previous=interface_psi_previous,
            transport_variational_temporaries=transport_temporaries,
        )
        capillary_face_weights = capillary_pressure_adjoint_face_weights(
            xp=xp,
            div_op=div_op,
            rho=state.rho,
            pressure_flux_kwargs=pressure_flux_kwargs_for_projection,
        )
        cochain = closed_interface_riesz_cochain(
            xp=xp,
            grid=jump_grid,
            psi=_closed_interface_trace_psi(state=state),
            fccd=fccd,
            sigma=physical_jump_sigma,
            rho=state.rho,
            face_weight_components=capillary_face_weights,
        )
        trace_projection_diagnostics = capillary_external_component_saddle_projection(
            xp=xp,
            div_op=div_op,
            ppe_solver=ppe_solver,
            rho=state.rho,
            pressure_flux_kwargs=pressure_flux_kwargs_for_projection,
            raw_components=cochain.surface_acceleration,
            component_reaction_components=[cochain.volume_reaction_acceleration],
            face_weight_components=capillary_face_weights,
        )
        corrected_capillary_components = (
            trace_projection_diagnostics["corrected_jump_components"]
        )
        rhs = rhs + div_op.divergence_from_faces(corrected_capillary_components)

    state.transport_variational_nodal_covector = transport_temporaries.get(
        "transport_variational_nodal_covector"
    )
    state.transport_variational_psi = transport_temporaries.get(
        "transport_variational_psi"
    )
    ppe_solver.set_interface_jump_context(
        psi=interface_psi,
        kappa=state.kappa,
        sigma=jump_sigma,
        psi_previous=interface_psi_previous,
        **transport_temporaries,
        face_curvature_method=(
            curvature_method
            if curvature_method in _JUMP_CURVATURE_METHODS
            else "nodal_cut_face"
        ),
    )
    return rhs, PressureJumpStageContext(
        transport_temporaries=transport_temporaries,
        trace_projection_diagnostics=trace_projection_diagnostics,
        corrected_capillary_components=corrected_capillary_components,
    )


def _capillary_pressure_flux_evaluation_kwargs(
    *,
    xp,
    div_op,
    ppe_solver,
    ppe_runtime,
    rho,
    pressure_flux_kwargs: dict,
    closed_interface_source: bool,
    jump_context: PressureJumpStageContext,
) -> tuple[dict | None, dict]:
    """Select capillary face cochain used when evaluating pressure faces."""
    if closed_interface_source:
        if jump_context.corrected_capillary_components is None:
            raise RuntimeError("closed_interface_riesz did not produce a face cochain")
        range_projection = jump_context.trace_projection_diagnostics
        pressure_flux_eval_kwargs = dict(pressure_flux_kwargs)
        pressure_flux_eval_kwargs["capillary_jump_components"] = (
            jump_context.corrected_capillary_components
        )
        return range_projection, pressure_flux_eval_kwargs

    capillary_projection_mode = getattr(
        ppe_runtime,
        "capillary_range_projection",
        "none",
    )
    if capillary_projection_mode == "range_projected":
        range_projection = capillary_jump_range_projection(
            xp=xp,
            div_op=div_op,
            ppe_solver=ppe_solver,
            rho=rho,
            pressure_flux_kwargs=pressure_flux_kwargs,
        )
        pressure_flux_eval_kwargs = dict(pressure_flux_kwargs)
        pressure_flux_eval_kwargs["capillary_jump_components"] = (
            range_projection["range_projection_components"]
        )
        return range_projection, pressure_flux_eval_kwargs
    if capillary_projection_mode == "component_hodge_augmented":
        range_projection = capillary_component_hodge_augmented_projection(
            xp=xp,
            div_op=div_op,
            ppe_solver=ppe_solver,
            rho=rho,
            pressure_flux_kwargs=pressure_flux_kwargs,
        )
        pressure_flux_eval_kwargs = dict(pressure_flux_kwargs)
        pressure_flux_eval_kwargs["capillary_jump_components"] = (
            range_projection["corrected_jump_components"]
        )
        return range_projection, pressure_flux_eval_kwargs
    return None, pressure_flux_kwargs


def solve_ns_pressure_stage(
    state: NSStepState,
    *,
    backend,
    div_op,
    ppe_solver,
    p_prev_dev,
    surface_tension_scheme: str,
    p_base_prev_dev=None,
    face_native_predictor_state: bool = False,
    bc_type: str = "wall",
    face_no_slip_boundary_state: bool = False,
    ppe_runtime=None,
    curvature_method: str = "psi_direct_filtered",
    capillary_force_source: str = "curvature_jump",
) -> tuple[NSStepState, object, np.ndarray]:
    """Solve IPC PPE and prepare scalar/face pressure history.

    A3 mapping: for affine pressure jumps, the face-native path treats the
    full face pressure cochain as the pressure-history state.  Because the
    predictor already subtracts ``a_p^n=A_f(G_f p^n-B_f(j^n))``, the PPE
    solves the next full cochain by adding ``D_f a_p^n`` to its source, while
    the corrector applies only the cochain increment
    ``a_p^{n+1}-a_p^n``.  This is the face-space form of the IPC jump
    contract and avoids solving a pressure increment with a full jump.
    """
    xp = backend.xp
    projection_dt = state.projection_dt if state.projection_dt is not None else state.dt
    predictor_rhs = _pressure_stage_predictor_rhs(
        state,
        xp=xp,
        div_op=div_op,
        projection_dt=projection_dt,
        face_native_predictor_state=face_native_predictor_state,
        bc_type=bc_type,
        face_no_slip_boundary_state=face_no_slip_boundary_state,
    )
    nonstatic_geometric_capillary = _uses_nonstatic_geometric_capillary_application(
        state
    )
    if nonstatic_geometric_capillary:
        if not state.geometric_capillary_predictor_applied:
            raise ValueError(
                "non-static AO capillary predictor requires face-native "
                "predictor application before PPE"
            )
        _prepare_nonstatic_geometric_pressure_reaction(
            state,
            backend=backend,
            xp=xp,
            div_op=div_op,
            grid=_pressure_jump_grid(ppe_solver, div_op),
            projection_dt=projection_dt,
            bc_type=bc_type,
            face_no_slip_boundary_state=face_no_slip_boundary_state,
        )
    rhs = predictor_rhs
    if nonstatic_geometric_capillary:
        rhs = rhs - state.geometric_capillary_pressure_reaction_rhs
    rhs = rhs + div_op.divergence([state.f_x / state.rho, state.f_y / state.rho])
    closed_interface_source = (
        capillary_force_source == "closed_interface_riesz"
        and not _uses_geometric_capillary_surface_slot(state)
    )
    physical_jump_sigma = _suppress_geometric_surface_jump_sigma(
        state,
        surface_tension_scheme=surface_tension_scheme,
    )
    rhs, jump_context = _install_pressure_jump_context(
        state,
        xp=xp,
        div_op=div_op,
        ppe_solver=ppe_solver,
        ppe_runtime=ppe_runtime,
        curvature_method=curvature_method,
        closed_interface_source=closed_interface_source,
        physical_jump_sigma=physical_jump_sigma,
        rhs=rhs,
    )

    uses_affine_face_history = (
        face_native_predictor_state
        and getattr(ppe_runtime, "ppe_interface_coupling_scheme", "none")
        == "affine_jump"
        and hasattr(div_op, "pressure_fluxes")
        and hasattr(div_op, "reconstruct_nodes")
    )
    pressure_coordinate_history = (
        uses_affine_face_history
        and _pressure_history_mode(ppe_runtime) == "pressure_coordinate"
    )
    previous_pressure_accel_faces = None
    previous_pressure_history_rhs = None
    if (
        uses_affine_face_history
        and not pressure_coordinate_history
        and state.previous_pressure_accel_face_components is not None
    ):
        if not hasattr(div_op, "divergence_from_faces"):
            raise RuntimeError(
                "affine_jump IPC pressure history requires face divergence"
            )
        previous_pressure_accel_faces = [
            xp.asarray(component)
            for component in state.previous_pressure_accel_face_components
        ]
        previous_pressure_history_rhs = div_op.divergence_from_faces(
            previous_pressure_accel_faces
        )
        rhs = rhs + previous_pressure_history_rhs

    if nonstatic_geometric_capillary:
        state.geometric_capillary_pressure_residual_rhs = rhs
        certificate = dict(state.conservative_transport_certificate or {})
        certificate.update(
            {
                "ao_pressure_reaction_rhs_subtracted": True,
                "ao_scalar_ppe_rhs_linf": _scalar_from_backend(
                    backend,
                    xp,
                    xp.max(xp.abs(rhs)),
                ),
                "ao_pressure_history_face_acceleration_applied": (
                    previous_pressure_accel_faces is not None
                ),
            }
        )
        if previous_pressure_accel_faces is not None:
            certificate.update(
                {
                    "ao_pressure_history_rhs_added": True,
                    "ao_pressure_history_face_acceleration_linf": _face_linf(
                        backend,
                        xp,
                        previous_pressure_accel_faces,
                    ),
                    "ao_pressure_history_rhs_linf": _scalar_from_backend(
                        backend,
                        xp,
                        xp.max(xp.abs(previous_pressure_history_rhs)),
                    ),
                }
            )
        state.conservative_transport_certificate = certificate

    if state.debug_scalars is not None:
        state.debug_scalars.append(xp.max(xp.abs(rhs)))

    state.pressure_increment = ppe_solver.solve(
        rhs,
        state.rho,
        dt=projection_dt,
        p_init=None,
    )
    base_increment = getattr(ppe_solver, "last_base_pressure", state.pressure_increment)
    previous_base = (
        state.previous_base_pressure
        if state.previous_base_pressure is not None
        else p_base_prev_dev
    )
    if previous_base is None:
        previous_base = p_prev_dev
    if previous_base is None:
        previous_base = xp.zeros_like(base_increment)
    if pressure_coordinate_history:
        history_base = state.pressure_extrapolated_base
        if history_base is None:
            history_base = xp.zeros_like(base_increment)
        state.pressure_base = xp.asarray(history_base) + xp.asarray(base_increment)
    elif uses_affine_face_history:
        state.pressure_base = xp.asarray(base_increment)
    else:
        state.pressure_base = xp.asarray(previous_base) + xp.asarray(base_increment)
    state.pressure = _apply_solver_interface_jump(ppe_solver, state.pressure_base)
    state.pressure_accel_face_components = None
    state.pressure_correction_face_components = None
    state.capillary_face_diagnostics = zero_capillary_face_diagnostics()
    pressure_flux_eval_kwargs = None
    if uses_affine_face_history:
        jump_sigma = 0.0 if closed_interface_source else physical_jump_sigma
        interface_psi = _capillary_interface_psi(
            xp=xp,
            state=state,
            curvature_method=curvature_method,
        )
        interface_psi_previous = _capillary_interface_psi_previous(
            state=state,
            curvature_method=curvature_method,
        )
        pressure_flux_kwargs = _pressure_face_flux_kwargs(
            xp=xp,
            state=state,
            ppe_runtime=ppe_runtime,
            interface_sigma=jump_sigma,
            curvature_method=curvature_method,
            interface_psi=interface_psi,
            interface_psi_previous=interface_psi_previous,
            transport_variational_temporaries=jump_context.transport_temporaries,
        )
        range_projection, pressure_flux_eval_kwargs = (
            _capillary_pressure_flux_evaluation_kwargs(
                xp=xp,
                div_op=div_op,
                ppe_solver=ppe_solver,
                ppe_runtime=ppe_runtime,
                rho=state.rho,
                pressure_flux_kwargs=pressure_flux_kwargs,
                closed_interface_source=closed_interface_source,
                jump_context=jump_context,
            )
        )
        correction_pressure = (
            xp.asarray(base_increment)
            if pressure_coordinate_history
            else xp.asarray(state.pressure_increment)
        )
        correction_pressure_faces = _pressure_fluxes_for_active_operator(
            div_op,
            correction_pressure,
            state.rho,
            pressure_flux_eval_kwargs,
        )
        if pressure_coordinate_history:
            state.pressure_correction_face_components = [
                xp.asarray(component) for component in correction_pressure_faces
            ]
            state.pressure_accel_face_components = [
                xp.asarray(component)
                for component in _pressure_fluxes_for_active_operator(
                    div_op,
                    state.pressure_base,
                    state.rho,
                    pressure_flux_eval_kwargs,
                )
            ]
        elif previous_pressure_accel_faces is None:
            state.pressure_correction_face_components = [
                xp.asarray(component) for component in correction_pressure_faces
            ]
        else:
            state.pressure_correction_face_components = [
                xp.asarray(full_face) - previous_face
                for full_face, previous_face in zip(
                    correction_pressure_faces, previous_pressure_accel_faces
                )
            ]
        if not pressure_coordinate_history:
            state.pressure_accel_face_components = [
                xp.asarray(component) for component in correction_pressure_faces
            ]
        if state.debug_scalars is not None:
            if range_projection is None:
                range_projection = capillary_jump_range_projection(
                    xp=xp,
                    div_op=div_op,
                    ppe_solver=ppe_solver,
                    rho=state.rho,
                    pressure_flux_kwargs=pressure_flux_kwargs,
                )
            state.capillary_face_diagnostics = capillary_face_cochain_diagnostics(
                xp=xp,
                backend=backend,
                div_op=div_op,
                face_components=state.pressure_accel_face_components,
                **range_projection,
            )
    if nonstatic_geometric_capillary:
        _embed_nonstatic_geometric_pressure_reaction_corrector(
            state,
            xp=xp,
            div_op=div_op,
            ppe_runtime=ppe_runtime,
            curvature_method=curvature_method,
            pressure_flux_kwargs=pressure_flux_eval_kwargs,
        )
        _install_nonstatic_geometric_pressure_coordinate(
            state,
            xp=xp,
            ppe_solver=ppe_solver,
        )
    if pressure_coordinate_history and uses_affine_face_history:
        smooth_history_base = _smooth_pressure_history_base_without_ao_reaction(
            xp,
            state,
        )
        state.pressure_history_storage_base = (
            _encode_affine_pressure_history_coordinate(
                xp,
                smooth_history_base,
                pressure_flux_eval_kwargs,
            )
        )
    next_p_prev_dev = xp.copy(state.pressure)
    next_p_prev = (
        None
        if _backend_is_gpu(backend)
        else np.asarray(backend.to_host(next_p_prev_dev))
    )
    state.p_corrector = state.pressure_increment
    return state, next_p_prev_dev, next_p_prev


def _apply_boundary_hodge_projection(
    state: NSStepState,
    *,
    xp,
    proj_op,
    bc_type: str,
    boundary_hodge_mode: str,
    boundary_hodge_wall_trace: str,
    boundary_hodge_metric: str,
    boundary_hodge_solver: str,
    boundary_hodge_tolerance: float,
    boundary_hodge_max_iterations: int,
) -> None:
    """Apply the configured boundary Hodge projection in-place."""
    mode = str(boundary_hodge_mode).strip().lower()
    if mode == "off" or state.projected_face_components is None:
        return
    if mode != "wall_trace_projection":
        raise ValueError(f"unsupported boundary_hodge mode {boundary_hodge_mode!r}")
    if str(boundary_hodge_wall_trace).strip().lower() != "reconstruct_nodes":
        raise ValueError("boundary_hodge.wall_trace must be 'reconstruct_nodes'")
    if str(boundary_hodge_metric).strip().lower() != "transported_face_mass":
        raise ValueError("boundary_hodge.metric must be 'transported_face_mass'")
    fccd = getattr(proj_op, "_fccd", None)
    grid = getattr(fccd, "grid", None)
    if grid is None:
        grid = getattr(proj_op, "_grid", None)
    if grid is None:
        raise RuntimeError("boundary_hodge requires a face operator with grid metadata.")
    if str(boundary_hodge_solver).strip().lower() != "matrix_free_cg":
        raise ValueError("boundary_hodge.solver must be 'matrix_free_cg'")
    projection = project_wall_trace(
        xp=xp,
        grid=grid,
        fccd=fccd,
        face_components=state.projected_face_components,
        rho=state.rho,
        bc_type=bc_type,
        tolerance=boundary_hodge_tolerance,
        max_iterations=boundary_hodge_max_iterations,
    )
    state.projected_face_components = projection.face_components
    state.boundary_hodge_diagnostics = dict(projection.diagnostics)


def _record_boundary_hodge_post_diagnostics(
    state: NSStepState,
    *,
    backend,
    xp,
    proj_op,
    div_op,
    bc_type: str,
    boundary_hodge_mode: str,
    boundary_hodge_tolerance: float,
    boundary_hodge_gate: str,
) -> None:
    """Record post-BC consistency diagnostics and optionally fail close."""
    if (
        str(boundary_hodge_mode).strip().lower() == "off"
        or state.projected_face_components is None
    ):
        return
    diagnostics = dict(state.boundary_hodge_diagnostics or {})
    grid = getattr(getattr(proj_op, "_fccd", None), "grid", None)
    if grid is None:
        grid = getattr(proj_op, "_grid", None)
    if grid is not None:
        wall_trace = wall_trace_from_faces(
            xp,
            grid,
            state.projected_face_components,
            bc_type,
        )
        diagnostics["boundary_hodge_wall_post_linf"] = _scalar_from_backend(
            backend,
            xp,
            xp.max(xp.abs(wall_trace)) if getattr(wall_trace, "size", 0) else xp.asarray(0.0),
        )
    if hasattr(div_op, "divergence_from_faces"):
        div_field = div_op.divergence_from_faces(state.projected_face_components)
        diagnostics["boundary_hodge_div_linf"] = _scalar_from_backend(
            backend,
            xp,
            xp.max(xp.abs(div_field)),
        )
    if hasattr(proj_op, "reconstruct_nodes"):
        reconstructed = proj_op.reconstruct_nodes(state.projected_face_components)
        diagnostics["boundary_hodge_reconstruct_delta_linf"] = _face_linf(
            backend,
            xp,
            [reconstructed[0] - state.u, reconstructed[1] - state.v],
        )
    state.boundary_hodge_diagnostics = diagnostics
    gate = str(boundary_hodge_gate).strip().lower()
    if gate != "fail_close":
        return
    wall_linf = diagnostics.get(
        "boundary_hodge_wall_post_linf",
        diagnostics.get("boundary_hodge_wall_linf", 0.0),
    )
    residual = diagnostics.get("boundary_hodge_cg_residual", 0.0)
    converged = diagnostics.get("boundary_hodge_cg_converged", 1.0)
    reconstruction_delta = diagnostics.get("boundary_hodge_reconstruct_delta_linf", 0.0)
    tolerance = max(float(boundary_hodge_tolerance), 1.0e-14)
    div_linf = diagnostics.get("boundary_hodge_div_linf", 0.0)
    div_tolerance = max(1.0e-6, 1000.0 * tolerance)
    if converged < 0.5 or wall_linf > 10.0 * tolerance or residual > 10.0 * tolerance:
        raise RuntimeError(
            "boundary_hodge fail-close: wall trace projection did not converge "
            f"(wall_linf={wall_linf:.6e}, residual={residual:.6e})."
        )
    if div_linf > div_tolerance:
        raise RuntimeError(
            "boundary_hodge fail-close: constrained face state is not divergence-free "
            f"(div_linf={div_linf:.6e}, tolerance={div_tolerance:.6e})."
        )
    if reconstruction_delta > 10.0 * tolerance:
        raise RuntimeError(
            "boundary_hodge fail-close: reconstructed face state differs from "
            f"post-BC nodal state by {reconstruction_delta:.6e}."
        )

def correct_ns_velocity_stage(
    state: NSStepState,
    *,
    backend,
    pressure_grad_op,
    face_flux_projection: bool,
    canonical_face_state: bool = False,
    face_native_predictor_state: bool = False,
    face_no_slip_boundary_state: bool = False,
    preserve_projected_faces: bool,
    fccd_div_op,
    div_op,
    ppe_runtime,
    bc_type: str,
    apply_velocity_bc,
    curvature_method: str = "psi_direct_filtered",
    capillary_force_source: str = "curvature_jump",
    boundary_hodge_mode: str = "off",
    boundary_hodge_wall_trace: str = "reconstruct_nodes",
    boundary_hodge_metric: str = "transported_face_mass",
    boundary_hodge_solver: str = "matrix_free_cg",
    boundary_hodge_tolerance: float = 1.0e-10,
    boundary_hodge_max_iterations: int = 80,
    boundary_hodge_gate: str = "diagnostic",
) -> NSStepState:
    """Apply pressure correction and optional face-flux projection."""
    xp = backend.xp
    projection_dt = state.projection_dt if state.projection_dt is not None else state.dt
    correction_is_zero = (
        not _backend_is_gpu(backend)
        and all_arrays_exact_zero(xp, (
            state.u_star,
            state.v_star,
            state.p_corrector,
            state.f_x,
            state.f_y,
        ))
    )
    proj_op = None
    project_kwargs = {}
    keep_face_state = canonical_face_state or preserve_projected_faces
    closed_interface_source = (
        capillary_force_source == "closed_interface_riesz"
        and not _uses_geometric_capillary_surface_slot(state)
    )
    if face_flux_projection:
        proj_op = fccd_div_op if fccd_div_op is not None else div_op
    nonstatic_geometric_capillary = _uses_nonstatic_geometric_capillary_application(
        state
    )
    if nonstatic_geometric_capillary and not (
        face_flux_projection
        and keep_face_state
        and face_native_predictor_state
        and state.predictor_face_components is not None
        and state.pressure_correction_face_components is not None
        and proj_op is not None
        and hasattr(proj_op, "pressure_fluxes")
        and hasattr(proj_op, "face_fluxes")
        and hasattr(proj_op, "reconstruct_nodes")
    ):
        raise ValueError(
            "non-static AO velocity corrector requires face-native projection "
            "state and prepared pressure correction faces"
        )
    static_geometric_capillary = _uses_static_geometric_capillary_application(state)
    if correction_is_zero and (
        not face_flux_projection
        or getattr(proj_op, "supports_zero_projection_shortcut", False)
        or static_geometric_capillary
    ):
        state.projected_face_components = None
        state.u = xp.zeros_like(state.u_star)
        state.v = xp.zeros_like(state.v_star)
        if state.debug_scalars is not None:
            state.debug_scalars.append(xp.asarray(0.0))
        apply_velocity_bc(state.u, state.v, state.bc_hook, bc_type)
        return state
    if face_flux_projection:
        if proj_op is fccd_div_op:
            interface_psi = _capillary_interface_psi(
                xp=xp,
                state=state,
                curvature_method=curvature_method,
            )
            interface_psi_previous = _capillary_interface_psi_previous(
                state=state,
                curvature_method=curvature_method,
            )
            transport_variational_temporaries = (
                {
                    "transport_variational_nodal_covector": (
                        state.transport_variational_nodal_covector
                    ),
                    "transport_variational_psi": state.transport_variational_psi,
                    "transport_variational_previous_surface_energy": (
                        state.transport_variational_previous_surface_energy
                    ),
                }
                if state.transport_variational_nodal_covector is not None
                else _capillary_transport_variational_temporaries(
                    xp=xp,
                    state=state,
                    curvature_method=curvature_method,
                    grid=getattr(getattr(proj_op, "_fccd", None), "grid", None),
                    sigma=state.sigma,
                )
            )
            project_kwargs = _pressure_face_flux_kwargs(
                xp=xp,
                state=state,
                ppe_runtime=ppe_runtime,
                interface_sigma=(
                    0.0
                    if closed_interface_source
                    else state.sigma
                ),
                curvature_method=curvature_method,
                interface_psi=interface_psi,
                interface_psi_previous=interface_psi_previous,
                transport_variational_temporaries=(
                    transport_variational_temporaries
                ),
            )

    dp_dx = pressure_grad_op.gradient(state.p_corrector, 0)
    dp_dy = pressure_grad_op.gradient(state.p_corrector, 1)
    if state.debug_scalars is not None:
        state.debug_scalars.append(
            xp.maximum(
                xp.max(xp.abs(dp_dx - state.f_x / state.rho)),
                xp.max(xp.abs(dp_dy - state.f_y / state.rho)),
            )
        )
    if face_flux_projection:
        if (
            keep_face_state
            and face_native_predictor_state
            and state.predictor_face_components is not None
            and hasattr(proj_op, "pressure_fluxes")
            and hasattr(proj_op, "face_fluxes")
            and hasattr(proj_op, "reconstruct_nodes")
        ):
            if state.pressure_correction_face_components is not None:
                pressure_faces = [
                    xp.asarray(component)
                    for component in state.pressure_correction_face_components
                ]
            else:
                pressure_faces = None
            if pressure_faces is None:
                if closed_interface_source:
                    raise RuntimeError(
                        "closed_interface_riesz corrector requires stored "
                        "component-saddle pressure faces"
                    )
                pressure_faces = proj_op.pressure_fluxes(
                    state.p_corrector,
                    state.rho,
                    **project_kwargs,
                )
            force_faces = proj_op.face_fluxes([state.f_x / state.rho, state.f_y / state.rho])
            state.projected_face_components = [
                predictor_face - projection_dt * pressure_face + projection_dt * force_face
                for predictor_face, pressure_face, force_face in zip(
                    state.predictor_face_components,
                    pressure_faces,
                    force_faces,
                )
            ]
            if (
                not is_all_periodic(bc_type, 2)
                and state.bc_hook is None
                and face_no_slip_boundary_state
            ):
                state.projected_face_components = zero_wall_velocity_face_components(
                    state.projected_face_components,
                    xp=xp,
                    bc_type=bc_type,
                )
            _apply_boundary_hodge_projection(
                state,
                xp=xp,
                proj_op=proj_op,
                bc_type=bc_type,
                boundary_hodge_mode=boundary_hodge_mode,
                boundary_hodge_wall_trace=boundary_hodge_wall_trace,
                boundary_hodge_metric=boundary_hodge_metric,
                boundary_hodge_solver=boundary_hodge_solver,
                boundary_hodge_tolerance=boundary_hodge_tolerance,
                boundary_hodge_max_iterations=boundary_hodge_max_iterations,
            )
            state.u, state.v = proj_op.reconstruct_nodes(state.projected_face_components)
            if nonstatic_geometric_capillary:
                certificate = dict(state.conservative_transport_certificate or {})
                if hasattr(div_op, "divergence_from_faces"):
                    div_field = div_op.divergence_from_faces(
                        state.projected_face_components
                    )
                    certificate["ao_projected_face_div_linf"] = (
                        _scalar_from_backend(
                            backend,
                            xp,
                            xp.max(xp.abs(div_field)),
                        )
                    )
                certificate["ao_nonstatic_velocity_corrector_applied"] = True
                state.conservative_transport_certificate = certificate
        elif keep_face_state and hasattr(proj_op, "project_faces"):
            state.projected_face_components = proj_op.project_faces(
                [state.u_star, state.v_star],
                state.p_corrector,
                state.rho,
                projection_dt,
                [state.f_x / state.rho, state.f_y / state.rho],
                **project_kwargs,
            )
            _apply_boundary_hodge_projection(
                state,
                xp=xp,
                proj_op=proj_op,
                bc_type=bc_type,
                boundary_hodge_mode=boundary_hodge_mode,
                boundary_hodge_wall_trace=boundary_hodge_wall_trace,
                boundary_hodge_metric=boundary_hodge_metric,
                boundary_hodge_solver=boundary_hodge_solver,
                boundary_hodge_tolerance=boundary_hodge_tolerance,
                boundary_hodge_max_iterations=boundary_hodge_max_iterations,
            )
            state.u, state.v = proj_op.reconstruct_nodes(state.projected_face_components)
        else:
            state.projected_face_components = None
            state.u, state.v = proj_op.project(
                [state.u_star, state.v_star],
                state.p_corrector,
                state.rho,
                projection_dt,
                [state.f_x / state.rho, state.f_y / state.rho],
                **project_kwargs,
            )
    else:
        state.projected_face_components = None
        state.u = state.u_star - projection_dt / state.rho * dp_dx + projection_dt * state.f_x / state.rho
        state.v = state.v_star - projection_dt / state.rho * dp_dy + projection_dt * state.f_y / state.rho
    apply_velocity_bc(state.u, state.v, state.bc_hook, bc_type)
    if face_flux_projection and state.projected_face_components is not None:
        _record_boundary_hodge_post_diagnostics(
            state,
            backend=backend,
            xp=xp,
            proj_op=proj_op,
            div_op=div_op,
            bc_type=bc_type,
            boundary_hodge_mode=boundary_hodge_mode,
            boundary_hodge_tolerance=boundary_hodge_tolerance,
            boundary_hodge_gate=boundary_hodge_gate,
        )
    return state

def record_ns_step_diagnostics(
    state: NSStepState,
    *,
    backend,
    div_op,
    step_diag,
    ppe_solver,
) -> None:
    """Flush step diagnostics to the active recorder."""
    if state.debug_scalars is None:
        return
    xp = backend.xp
    if (
        state.projected_face_components is not None
        and hasattr(div_op, "divergence_from_faces")
    ):
        div_field = div_op.divergence_from_faces(state.projected_face_components)
    else:
        div_field = div_op.divergence([state.u, state.v])
    state.debug_scalars.append(xp.max(xp.abs(div_field)))
    dbg = np.asarray(backend.to_host(xp.stack(state.debug_scalars)))
    step_diag.record_kappa(float(dbg[0]))
    step_diag.record_ppe_rhs(float(dbg[1]))
    step_diag.record_bf_residual(float(dbg[2]))
    step_diag.record_div_u(float(dbg[3]))
    step_diag.record_ppe_stats(
        getattr(ppe_solver, "last_diagnostics", {})
    )
    step_diag.record_ppe_stats(state.interface_projection_diagnostics or {})
    step_diag.record_ppe_stats(state.capillary_face_diagnostics or {})
    step_diag.record_ppe_stats(state.boundary_hodge_diagnostics or {})
