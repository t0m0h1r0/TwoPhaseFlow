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
    solver._boundary_hodge_mode = str(
        getattr(options.schemes, "boundary_hodge_mode", "off")
    )
    solver._boundary_hodge_state_space = str(
        getattr(options.schemes, "boundary_hodge_state_space", "full_face")
    )
    solver._boundary_hodge_wall_trace = str(
        getattr(options.schemes, "boundary_hodge_wall_trace", "reconstruct_nodes")
    )
    solver._boundary_hodge_wall_retraction = str(
        getattr(options.schemes, "boundary_hodge_wall_retraction", "metric_projection")
    )
    solver._boundary_hodge_metric = str(
        getattr(options.schemes, "boundary_hodge_metric", "transported_face_mass")
    )
    solver._boundary_hodge_pressure_pairing = str(
        getattr(
            options.schemes,
            "boundary_hodge_pressure_pairing",
            "active_variational_adjoint",
        )
    )
    solver._boundary_hodge_solver = str(
        getattr(options.schemes, "boundary_hodge_solver", "matrix_free_cg")
    )
    solver._boundary_hodge_tolerance = float(
        getattr(options.schemes, "boundary_hodge_tolerance", 1.0e-10)
    )
    solver._boundary_hodge_max_iterations = int(
        getattr(options.schemes, "boundary_hodge_max_iterations", 80)
    )
    solver._boundary_hodge_gate = str(
        getattr(options.schemes, "boundary_hodge_gate", "diagnostic")
    )
    solver._projection_consistent_buoyancy = bool(
        getattr(options.schemes, "projection_consistent_buoyancy", False)
    )
    solver._projected_face_components = None
    solver._conservative_density = None
    solver._conservative_momentum_components = None
    solver._p_prev_accel_face_components = None
    solver._p_base_prev2_dev = None
    solver._prepared_geometric_grid_rebuild_step = None
    solver._active_projection_solver_scheme = str(
        getattr(options.interface, "active_projection_solver_scheme", "pcg")
    ).strip().lower()
    solver._active_projection_absolute_tolerance = float(
        getattr(options.interface, "active_projection_absolute_tolerance", 1.0e-11)
    )
    solver._active_projection_relative_tolerance = float(
        getattr(options.interface, "active_projection_relative_tolerance", 0.0)
    )
    solver._active_projection_max_iterations = int(
        getattr(options.interface, "active_projection_max_iterations", 8)
    )
    solver._active_projection_pcg_tolerance = float(
        getattr(options.interface, "active_projection_pcg_tolerance", 1.0e-12)
    )
    solver._active_projection_pcg_max_iterations = int(
        getattr(options.interface, "active_projection_pcg_max_iterations", 256)
    )
    solver._active_projection_pcg_roundoff_floor = getattr(
        options.interface,
        "active_projection_pcg_roundoff_floor",
        1.0e-14,
    )
    solver._active_projection_dc_tolerance = float(
        getattr(options.interface, "active_projection_dc_tolerance", 1.0e-11)
    )
    solver._active_projection_dc_max_iterations = int(
        getattr(options.interface, "active_projection_dc_max_iterations", 8)
    )
    solver._active_projection_dc_relaxation = float(
        getattr(options.interface, "active_projection_dc_relaxation", 1.0)
    )
    solver._interface_gauge_reconstruction = str(
        getattr(options.interface, "interface_gauge_reconstruction", "fixed_stratum")
    ).strip().lower()
    solver._record_interface_projection_fields = False
    solver._last_interface_projection_fields = None
    solver._initialise_geometry(options.grid)
    _validate_geometric_backend(solver, options)
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


def _validate_geometric_backend(solver, options) -> None:
    """Reject active-geometry execution on the dense CPU runtime."""
    if (
        getattr(options.schemes, "advection_scheme", "") == "geometric_swept_volume"
        and not solver._backend.is_gpu()
    ):
        raise RuntimeError(
            "active_geometry_capillary requires a GPU backend; CPU dense "
            "runtime fallback is not permitted for AO-Fast"
        )
