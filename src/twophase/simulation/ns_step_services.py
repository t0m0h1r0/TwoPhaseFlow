"""Step-stage helper services for `TwoPhaseNSSolver`."""

from __future__ import annotations

import numpy as np

from ..ns_terms.context import NSComputeContext
from .ns_step_state import NSStepState
from .step_diagnostics import ActiveStepDiagnostics


def materialise_ns_step_fields(state: NSStepState) -> NSStepState:
    """Build density and viscosity fields for the current step."""
    state.rho = state.rho_g + (state.rho_l - state.rho_g) * state.psi
    if state.mu_l is not None and state.mu_g is not None:
        state.mu_field = state.mu_g + (state.mu_l - state.mu_g) * state.psi
    else:
        state.mu_field = state.mu
    return state


def compute_ns_surface_tension_stage(
    state: NSStepState,
    *,
    backend,
    curv,
    hfe,
    interface_runtime,
    step_diag,
    st_force,
    ccd,
    surface_tension_grad_op,
    projection_consistent_buoyancy: bool,
) -> NSStepState:
    """Compute curvature and balanced-force surface tension terms."""
    xp = backend.xp
    kappa_raw = curv.compute(state.psi)
    state.kappa = hfe.apply(xp.asarray(kappa_raw), xp.asarray(state.psi))
    if interface_runtime.kappa_max is not None:
        state.kappa = xp.clip(
            state.kappa,
            -interface_runtime.kappa_max,
            interface_runtime.kappa_max,
        )
    state.debug_scalars = None
    if isinstance(step_diag, ActiveStepDiagnostics):
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
    projection_consistent_buoyancy: bool,
) -> tuple[NSStepState, bool, tuple | None]:
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

    next_conv_prev = conv_prev
    next_conv_ab2_ready = conv_ab2_ready
    if scheme_runtime.convection_time_scheme == "ab2":
        if conv_ab2_ready and conv_prev is not None:
            conv_step_u = 1.5 * conv_u - 0.5 * conv_prev[0]
            conv_step_v = 1.5 * conv_v - 0.5 * conv_prev[1]
        else:
            conv_step_u = conv_u
            conv_step_v = conv_v
        next_conv_prev = (xp.copy(conv_u), xp.copy(conv_v))
        next_conv_ab2_ready = True
    else:
        conv_step_u = conv_u
        conv_step_v = conv_v

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
    )
    return state, next_conv_ab2_ready, next_conv_prev


def solve_ns_pressure_stage(
    state: NSStepState,
    *,
    backend,
    div_op,
    ppe_solver,
    p_prev_dev,
    surface_tension_scheme: str,
) -> tuple[NSStepState, object, np.ndarray]:
    """Solve PPE and prepare the corrector pressure field."""
    xp = backend.xp
    rhs = div_op.divergence([state.u_star, state.v_star]) / state.dt
    rhs = rhs + div_op.divergence([state.f_x / state.rho, state.f_y / state.rho])
    if state.debug_scalars is not None:
        state.debug_scalars.append(xp.max(xp.abs(rhs)))
    if hasattr(ppe_solver, "set_interface_jump_context"):
        jump_sigma = state.sigma if surface_tension_scheme == "pressure_jump" else 0.0
        ppe_solver.set_interface_jump_context(
            psi=state.psi,
            kappa=state.kappa,
            sigma=jump_sigma,
        )

    state.pressure = ppe_solver.solve(
        rhs,
        state.rho,
        dt=state.dt,
        p_init=p_prev_dev,
    )
    next_p_prev_dev = getattr(ppe_solver, "last_base_pressure", state.pressure)
    next_p_prev = np.asarray(backend.to_host(next_p_prev_dev))
    state.p_corrector = (
        next_p_prev_dev
        if surface_tension_scheme == "pressure_jump"
        else state.pressure
    )
    return state, next_p_prev_dev, next_p_prev


def correct_ns_velocity_stage(
    state: NSStepState,
    *,
    backend,
    pressure_grad_op,
    face_flux_projection: bool,
    preserve_projected_faces: bool,
    fccd_div_op,
    div_op,
    ppe_runtime,
    bc_type: str,
    apply_velocity_bc,
) -> NSStepState:
    """Apply pressure correction and optional face-flux projection."""
    xp = backend.xp
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
        proj_op = fccd_div_op if fccd_div_op is not None else div_op
        project_kwargs = {}
        if proj_op is fccd_div_op:
            project_kwargs["pressure_gradient"] = (
                "fccd" if ppe_runtime.ppe_solver_name == "fccd_iterative" else "fvm"
            )
        if preserve_projected_faces and hasattr(proj_op, "project_faces"):
            state.projected_face_components = proj_op.project_faces(
                [state.u_star, state.v_star],
                state.p_corrector,
                state.rho,
                state.dt,
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
                state.dt,
                [state.f_x / state.rho, state.f_y / state.rho],
                **project_kwargs,
            )
    else:
        state.projected_face_components = None
        state.u = state.u_star - state.dt / state.rho * dp_dx + state.dt * state.f_x / state.rho
        state.v = state.v_star - state.dt / state.rho * dp_dy + state.dt * state.f_y / state.rho
    preserve_face_state = (
        preserve_projected_faces
        and state.projected_face_components is not None
        and bc_type == "wall"
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
