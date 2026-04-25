"""Lifecycle helpers for `TwoPhaseNSSolver` runtime assembly."""

from __future__ import annotations

from .ns_runtime_bootstrap import bind_ns_runtime_bootstrap, build_ns_runtime_bootstrap


def reset_ns_runtime_contexts(solver) -> None:
    """Drop cached setup/timestep contexts after geometry changes."""
    solver._runtime_setup_ctx = None
    solver._runtime_timestep_ctx = None


def initialise_ns_solver_from_options(solver, options) -> None:
    """Run the ordered runtime assembly sequence for `TwoPhaseNSSolver`."""
    solver._canonical_face_state = bool(
        getattr(options.schemes, "canonical_face_state", False)
    )
    solver._face_native_predictor_state = bool(
        getattr(options.schemes, "face_native_predictor_state", False)
    )
    solver._face_no_slip_boundary_state = bool(
        getattr(options.schemes, "face_no_slip_boundary_state", False)
    )
    solver._cn_buoyancy_predictor_assembly_mode = str(
        getattr(options.schemes, "cn_buoyancy_predictor_assembly_mode", "none")
    )
    solver._preserve_projected_faces = bool(
        getattr(options.schemes, "preserve_projected_faces", False)
    )
    solver._projection_consistent_buoyancy = bool(
        getattr(options.schemes, "projection_consistent_buoyancy", False)
    )
    solver._projected_face_components = None
    solver._initialise_geometry(options.grid)
    solver._initialise_interface_runtime(options.interface)
    solver._initialise_ppe_runtime(
        options.ppe,
        surface_tension_scheme=options.schemes.surface_tension_scheme,
    )
    solver._initialise_scheme_runtime(options.schemes)
    solver._initialise_operator_stack(options.grid, options.schemes)
    bootstrap = build_ns_runtime_bootstrap(
        backend=solver._backend,
        grid=solver._grid,
        adv=solver._adv,
        eps=solver._eps,
        interface_runtime=solver._interface_runtime,
        scheme_options=options.schemes,
        build_reinitializer=lambda: solver._build_reinitializer(
            options.interface,
            options.schemes,
        ),
    )
    bind_ns_runtime_bootstrap(solver, bootstrap)
