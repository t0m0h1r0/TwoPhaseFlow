"""Step-stage helper services for `TwoPhaseNSSolver`."""

from __future__ import annotations

import numpy as np

from ..core.array_checks import all_arrays_exact_zero
from ..core.boundary import boundary_axes, is_all_periodic
from ..ns_terms.context import NSComputeContext
from .ns_predictor_assembly import (
    select_buoyancy_predictor_state_assembly,
    select_gravity_aligned_axis,
    select_transverse_axis,
)
from ..coupling.interface_stress_closure import build_young_laplace_interface_stress_context
from ..coupling.capillary_geometry import apply_wall_compatible_curvature
from .ns_step_state import NSStepState

IMEX_BDF2_PROJECTION_FACTOR = 2.0 / 3.0


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


def _previous_pressure_acceleration_nodes(
    state: NSStepState,
    *,
    xp,
    div_op,
    pressure_grad_op,
    ppe_solver_name: str | None,
    ppe_coefficient_scheme: str,
    ppe_interface_coupling_scheme: str,
):
    """Return ``rho^{-1} G(p^n)`` using the PPE pressure-jump contract."""
    if (
        str(ppe_interface_coupling_scheme).strip().lower() == "affine_jump"
        and str(ppe_coefficient_scheme).strip().lower() == "phase_separated"
        and div_op is not None
        and hasattr(div_op, "pressure_fluxes")
        and hasattr(div_op, "reconstruct_nodes")
        and state.psi is not None
        and state.kappa is not None
        and float(state.sigma) != 0.0
    ):
        pressure_gradient = (
            "fccd" if str(ppe_solver_name).strip().lower() == "fccd_iterative" else "fvm"
        )
        context = build_young_laplace_interface_stress_context(
            xp=xp,
            psi=state.psi,
            kappa_lg=state.kappa,
            sigma=state.sigma,
        )
        pressure_faces = div_op.pressure_fluxes(
            state.previous_pressure,
            state.rho,
            pressure_gradient=pressure_gradient,
            coefficient_scheme="phase_separated",
            interface_coupling_scheme="affine_jump",
            interface_stress_context=context,
        )
        return div_op.reconstruct_nodes(pressure_faces)

    if pressure_grad_op is None:
        raise RuntimeError("IPC predictor requires pressure_grad_op for ∇p^n")
    return [
        pressure_grad_op.gradient(state.previous_pressure, 0) / state.rho,
        pressure_grad_op.gradient(state.previous_pressure, 1) / state.rho,
    ]


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


def _zero_wall_normal_face_components(face_components: list, *, xp, bc_type: str = "wall") -> list:
    """Zero wall-normal face fluxes at domain boundaries."""
    bounded = []
    ndim = face_components[0].ndim
    axes = boundary_axes(bc_type, ndim)
    for axis, face in enumerate(face_components):
        bounded_face = xp.array(face, copy=True)
        if axes[axis] != "wall":
            bounded.append(bounded_face)
            continue
        lower = [slice(None)] * ndim
        upper = [slice(None)] * ndim
        lower[axis] = 0
        upper[axis] = -1
        bounded_face[tuple(lower)] = 0.0
        bounded_face[tuple(upper)] = 0.0
        bounded.append(bounded_face)
    return bounded


def _zero_wall_velocity_face_components(face_components: list, *, xp, bc_type: str = "wall") -> list:
    """Apply no-slip wall boundaries to carried face-velocity state."""
    bounded = []
    axes = boundary_axes(bc_type, face_components[0].ndim)
    for face in face_components:
        bounded_face = xp.array(face, copy=True)
        for axis in range(bounded_face.ndim):
            if axes[axis] != "wall":
                continue
            lower = [slice(None)] * bounded_face.ndim
            upper = [slice(None)] * bounded_face.ndim
            lower[axis] = 0
            upper[axis] = -1
            bounded_face[tuple(lower)] = 0.0
            bounded_face[tuple(upper)] = 0.0
        bounded.append(bounded_face)
    return bounded


def materialise_ns_step_fields(state: NSStepState) -> NSStepState:
    """Build density and viscosity fields for the current step."""
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
    ppe_interface_coupling_scheme: str = "none",
    ppe_solver_name: str | None = None,
) -> tuple[NSStepState, bool, tuple | None, bool, tuple | None]:
    """Advance the momentum predictor stage."""
    xp = backend.xp
    conv_ctx = NSComputeContext(
        velocity=[state.u, state.v],
        ccd=ccd,
        rho=state.rho,
        mu=state.mu_field,
    )
    conv_u, conv_v = conv_term.compute(conv_ctx)

    buoy_v = xp.zeros_like(state.v)
    if state.g_acc != 0.0 and not projection_consistent_buoyancy:
        buoy_v = -(state.rho - state.rho_ref) / state.rho * state.g_acc
    buoyancy_components = [xp.zeros_like(state.u), state.rho * buoy_v]

    next_conv_prev = conv_prev
    next_conv_ab2_ready = conv_ab2_ready
    next_velocity_prev = velocity_prev
    next_velocity_bdf2_ready = velocity_bdf2_ready
    bdf2_history_ready = (
        conv_ab2_ready
        and conv_prev is not None
        and velocity_bdf2_ready
        and velocity_prev is not None
    )
    if scheme_runtime.convection_time_scheme == "ab2":
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

    if state.previous_pressure is not None:
        previous_pressure_accel = _previous_pressure_acceleration_nodes(
            state,
            xp=xp,
            div_op=div_op,
            pressure_grad_op=pressure_grad_op,
            ppe_solver_name=ppe_solver_name,
            ppe_coefficient_scheme=ppe_coefficient_scheme,
            ppe_interface_coupling_scheme=ppe_interface_coupling_scheme,
        )
        conv_step_u = conv_step_u - previous_pressure_accel[0]
        conv_step_v = conv_step_v - previous_pressure_accel[1]

    predictor_kwargs = {}
    face_residual_buoyancy_state = None
    can_use_face_state = (
        face_native_predictor_state
        and state.face_velocity_components is not None
        and div_op is not None
        and hasattr(div_op, "face_fluxes")
        and hasattr(div_op, "reconstruct_nodes")
    )
    if can_use_face_state and cn_buoyancy_predictor_assembly_mode != "none":

        def face_consistent_velocity_transform(velocity_components: list) -> None:
            if len(velocity_components) < 2:
                return
            delta_faces = div_op.face_fluxes(
                [
                    velocity_components[0] - state.u,
                    velocity_components[1] - state.v,
                ]
            )
            predictor_faces = [
                xp.asarray(face_velocity) + delta_face
                for face_velocity, delta_face in zip(
                    state.face_velocity_components,
                    delta_faces,
                )
            ]
            if not is_all_periodic(bc_type, 2) and state.bc_hook is None:
                if face_no_slip_boundary_state:
                    predictor_faces = _zero_wall_velocity_face_components(
                        predictor_faces,
                        xp=xp,
                        bc_type=bc_type,
                    )
                else:
                    predictor_faces = _zero_wall_normal_face_components(
                        predictor_faces,
                        xp=xp,
                        bc_type=bc_type,
                    )
            mapped_components = div_op.reconstruct_nodes(predictor_faces)
            velocity_components[0][...] = mapped_components[0]
            velocity_components[1][...] = mapped_components[1]

        def fullband_interface_mask():
            if state.psi is None:
                return None
            psi_arr = xp.asarray(state.psi)
            band = (psi_arr > 1.0e-6) & (psi_arr < 1.0 - 1.0e-6)
            for dilation_axis in range(psi_arr.ndim):
                base_band = xp.copy(band)
                lower = [slice(None)] * psi_arr.ndim
                upper = [slice(None)] * psi_arr.ndim
                lower[dilation_axis] = slice(1, None)
                upper[dilation_axis] = slice(None, -1)
                band[tuple(lower)] = band[tuple(lower)] | base_band[tuple(upper)]
                band[tuple(upper)] = band[tuple(upper)] | base_band[tuple(lower)]
            return band

        def fullband_state_transform(velocity_components: list) -> None:
            if len(velocity_components) < 2:
                return
            raw_components = [
                xp.array(velocity_components[0], copy=True),
                xp.array(velocity_components[1], copy=True),
            ]
            face_consistent_velocity_transform(velocity_components)
            band = fullband_interface_mask()
            if band is None:
                return
            velocity_components[0][...] = xp.where(
                band,
                velocity_components[0],
                raw_components[0],
            )
            velocity_components[1][...] = xp.where(
                band,
                velocity_components[1],
                raw_components[1],
            )

        def fullband_component_transform(axis: int):
            def _transform(velocity_components: list) -> None:
                if len(velocity_components) < 2:
                    return
                raw_components = [
                    xp.array(velocity_components[0], copy=True),
                    xp.array(velocity_components[1], copy=True),
                ]
                face_consistent_velocity_transform(velocity_components)
                band = fullband_interface_mask()
                if band is None:
                    mapped_axis = xp.array(velocity_components[axis], copy=True)
                else:
                    mapped_axis = xp.where(
                        band,
                        velocity_components[axis],
                        raw_components[axis],
                    )
                velocity_components[0][...] = raw_components[0]
                velocity_components[1][...] = raw_components[1]
                velocity_components[axis][...] = mapped_axis

            return _transform

        def residual_face_buoyancy_force_builder(
            buoyancy_force_components: list,
            rho_field,
            xp_mod,
        ) -> list:
            nonlocal face_residual_buoyancy_state
            residual_accel_faces = build_pressure_robust_buoyancy_residual_accel_faces(
                buoyancy_force_components=buoyancy_force_components,
                rho=rho_field,
                rho_ref=state.rho_ref,
                g_acc=state.g_acc,
                div_op=div_op,
                xp=xp_mod,
                coords=coords,
                Y=Y,
                pressure_coefficient_scheme=ppe_coefficient_scheme,
            )
            if residual_accel_faces is None:
                face_residual_buoyancy_state = None
                return buoyancy_force_components
            residual_accel_nodes = div_op.reconstruct_nodes(residual_accel_faces)
            face_residual_buoyancy_state = (
                residual_accel_faces,
                residual_accel_nodes,
            )
            return [
                rho_field * residual_node
                for residual_node in residual_accel_nodes
            ]

        selection = select_buoyancy_predictor_state_assembly(
            mode=cn_buoyancy_predictor_assembly_mode,
            fullband_state_transform=fullband_state_transform,
            residual_buoyancy_force_builder=residual_face_buoyancy_force_builder,
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
                    fullband_component_transform(transverse_axis)
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
        if state.face_velocity_components is not None:
            predictor_delta_faces = div_op.face_fluxes(
                [state.u_star - state.u, state.v_star - state.v]
            )
            if face_residual_buoyancy_state is not None:
                residual_faces, residual_nodes = face_residual_buoyancy_state
                residual_node_faces = div_op.face_fluxes(residual_nodes)
                predictor_delta_faces = [
                    delta_face + state.dt * (residual_face - residual_node_face)
                    for delta_face, residual_face, residual_node_face in zip(
                        predictor_delta_faces,
                        residual_faces,
                        residual_node_faces,
                    )
                ]
            state.predictor_face_components = [
                xp.asarray(face_velocity) + delta_face
                for face_velocity, delta_face in zip(
                    state.face_velocity_components,
                    predictor_delta_faces,
                )
            ]
        else:
            state.predictor_face_components = div_op.face_fluxes(
                [state.u_star, state.v_star]
            )
        if not is_all_periodic(bc_type, 2) and state.bc_hook is None:
            if face_no_slip_boundary_state:
                state.predictor_face_components = _zero_wall_velocity_face_components(
                    state.predictor_face_components,
                    xp=xp,
                    bc_type=bc_type,
                )
            else:
                state.predictor_face_components = _zero_wall_normal_face_components(
                    state.predictor_face_components,
                    xp=xp,
                    bc_type=bc_type,
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
) -> tuple[NSStepState, object, np.ndarray]:
    """Solve IPC PPE for δp and accumulate pⁿ⁺¹ = pⁿ + δp."""
    xp = backend.xp
    projection_dt = state.projection_dt if state.projection_dt is not None else state.dt
    predictor_faces = None
    if face_native_predictor_state and state.predictor_face_components is not None:
        predictor_faces = state.predictor_face_components
    if predictor_faces is not None and hasattr(div_op, "divergence_from_faces"):
        if not is_all_periodic(bc_type, 2) and state.bc_hook is None:
            if face_no_slip_boundary_state:
                predictor_faces = _zero_wall_velocity_face_components(
                    predictor_faces,
                    xp=xp,
                    bc_type=bc_type,
                )
            else:
                predictor_faces = _zero_wall_normal_face_components(
                    predictor_faces,
                    xp=xp,
                    bc_type=bc_type,
                )
        predictor_rhs = div_op.divergence_from_faces(predictor_faces) / projection_dt
    else:
        predictor_rhs = div_op.divergence([state.u_star, state.v_star]) / projection_dt
    rhs = predictor_rhs + div_op.divergence([state.f_x / state.rho, state.f_y / state.rho])
    if state.debug_scalars is not None:
        state.debug_scalars.append(xp.max(xp.abs(rhs)))
    if hasattr(ppe_solver, "set_interface_jump_context"):
        jump_sigma = state.sigma if surface_tension_scheme == "pressure_jump" else 0.0
        ppe_solver.set_interface_jump_context(
            psi=state.psi,
            kappa=state.kappa,
            sigma=jump_sigma,
        )

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
    state.pressure_base = xp.asarray(previous_base) + xp.asarray(base_increment)
    state.pressure = _apply_solver_interface_jump(ppe_solver, state.pressure_base)
    next_p_prev_dev = xp.copy(state.pressure)
    next_p_prev = (
        None
        if _backend_is_gpu(backend)
        else np.asarray(backend.to_host(next_p_prev_dev))
    )
    state.p_corrector = state.pressure_increment
    return state, next_p_prev_dev, next_p_prev

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
    if face_flux_projection:
        proj_op = fccd_div_op if fccd_div_op is not None else div_op
        if proj_op is fccd_div_op:
            project_kwargs["pressure_gradient"] = (
                "fccd" if ppe_runtime.ppe_solver_name == "fccd_iterative" else "fvm"
            )
            if ppe_runtime.ppe_coefficient_scheme == "phase_separated":
                project_kwargs["coefficient_scheme"] = "phase_separated"
            if (
                getattr(ppe_runtime, "ppe_interface_coupling_scheme", "none")
                == "affine_jump"
            ):
                project_kwargs["interface_coupling_scheme"] = "affine_jump"
                project_kwargs["interface_stress_context"] = (
                    build_young_laplace_interface_stress_context(
                        xp=xp,
                        psi=state.psi,
                        kappa_lg=state.kappa,
                        sigma=state.sigma,
                    )
                )
    if correction_is_zero and (
        not face_flux_projection
        or getattr(proj_op, "supports_zero_projection_shortcut", False)
    ):
        state.projected_face_components = None
        state.u = xp.zeros_like(state.u_star)
        state.v = xp.zeros_like(state.v_star)
        if state.debug_scalars is not None:
            state.debug_scalars.append(xp.asarray(0.0))
        apply_velocity_bc(state.u, state.v, state.bc_hook, bc_type)
        return state

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
                state.projected_face_components = _zero_wall_velocity_face_components(
                    state.projected_face_components,
                    xp=xp,
                    bc_type=bc_type,
                )
            state.u, state.v = proj_op.reconstruct_nodes(state.projected_face_components)
        elif keep_face_state and hasattr(proj_op, "project_faces"):
            state.projected_face_components = proj_op.project_faces(
                [state.u_star, state.v_star],
                state.p_corrector,
                state.rho,
                projection_dt,
                [state.f_x / state.rho, state.f_y / state.rho],
                **project_kwargs,
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
    preserve_face_state = (
        keep_face_state
        and state.projected_face_components is not None
        and not is_all_periodic(bc_type, 2)
        and state.bc_hook is None
    )
    if not preserve_face_state:
        apply_velocity_bc(state.u, state.v, state.bc_hook, bc_type)
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
