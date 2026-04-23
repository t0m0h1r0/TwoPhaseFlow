"""Runtime option normalization helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NSInterfaceRuntimeState:
    rebuild_freq: int
    reinit_every: int
    reproject_variable_density: bool
    face_flux_projection: bool
    reinit_eps_scale: float
    kappa_max: float | None
    interface_tracking_enabled: bool
    interface_tracking_method: str
    phi_primary_transport: bool
    phi_primary_redist_every: int
    phi_primary_clip_factor: float
    phi_primary_heaviside_eps_scale: float
    reproject_mode: str


@dataclass(frozen=True)
class NSPPERuntimeState:
    ppe_solver_name: str
    ppe_iteration_method: str
    ppe_coefficient_scheme: str
    ppe_interface_coupling_scheme: str
    ppe_tolerance: float
    ppe_max_iterations: int
    ppe_restart: int | None
    ppe_preconditioner: str
    ppe_pcr_stages: int | None
    ppe_c_tau: float
    ppe_defect_correction: bool
    ppe_dc_max_iterations: int
    ppe_dc_tolerance: float
    ppe_dc_relaxation: float
    pressure_scheme: str


@dataclass(frozen=True)
class NSSchemeRuntimeState:
    convection_time_scheme: str
    momentum_gradient_scheme: str
    pressure_gradient_scheme: str
    surface_tension_gradient_scheme: str
    advection_scheme: str
    convection_scheme: str


def normalise_ns_interface_runtime(options) -> NSInterfaceRuntimeState:
    rebuild_freq = max(0, int(options.grid_rebuild_freq))
    reinit_every = int(options.reinit_every)
    reproject_variable_density = bool(options.reproject_variable_density)
    face_flux_projection = False
    reinit_eps_scale = float(options.reinit_eps_scale)
    kappa_max = float(options.kappa_max) if options.kappa_max is not None else None

    interface_tracking_enabled = bool(options.interface_tracking_enabled)
    tracking_method = options.interface_tracking_method
    if not interface_tracking_enabled:
        interface_tracking_method = "none"
    else:
        if tracking_method is None:
            tracking_method = (
                "phi_primary" if bool(options.phi_primary_transport) else "psi_direct"
            )
        interface_tracking_method = str(tracking_method).strip().lower()
        if interface_tracking_method == "phi":
            interface_tracking_method = "phi_primary"
        elif interface_tracking_method == "psi":
            interface_tracking_method = "psi_direct"
        elif interface_tracking_method == "none":
            interface_tracking_enabled = False
    if interface_tracking_method not in {"phi_primary", "psi_direct", "none"}:
        raise ValueError(
            "Unsupported interface_tracking_method="
            f"'{tracking_method}'. Use phi_primary|psi_direct|none."
        )

    phi_primary_transport = (
        bool(options.phi_primary_transport)
        if interface_tracking_method not in {"phi_primary", "psi_direct"}
        else interface_tracking_method == "phi_primary"
    )
    phi_primary_redist_every = max(1, int(options.phi_primary_redist_every))
    phi_primary_clip_factor = max(2.0, float(options.phi_primary_clip_factor))
    phi_primary_heaviside_eps_scale = max(
        1.0, float(options.phi_primary_heaviside_eps_scale)
    )

    reproject_mode = str(options.reproject_mode).strip().lower()
    if reproject_mode not in {
        "legacy", "variable_density_only", "iim", "gfm",
        "consistent_iim", "consistent_gfm",
    }:
        raise ValueError(
            f"Unsupported reproject_mode='{options.reproject_mode}'. "
            "Use legacy|variable_density_only|gfm|iim."
        )
    if reproject_variable_density and reproject_mode == "legacy":
        reproject_mode = "variable_density_only"

    return NSInterfaceRuntimeState(
        rebuild_freq=rebuild_freq,
        reinit_every=reinit_every,
        reproject_variable_density=reproject_variable_density,
        face_flux_projection=face_flux_projection,
        reinit_eps_scale=reinit_eps_scale,
        kappa_max=kappa_max,
        interface_tracking_enabled=interface_tracking_enabled,
        interface_tracking_method=interface_tracking_method,
        phi_primary_transport=phi_primary_transport,
        phi_primary_redist_every=phi_primary_redist_every,
        phi_primary_clip_factor=phi_primary_clip_factor,
        phi_primary_heaviside_eps_scale=phi_primary_heaviside_eps_scale,
        reproject_mode=reproject_mode,
    )


def normalise_ns_ppe_runtime(
    options,
    *,
    surface_tension_scheme: str,
    ppe_aliases: dict,
    ppe_registry: dict,
) -> NSPPERuntimeState:
    raw_ppe = str(
        options.pressure_scheme if options.pressure_scheme is not None else options.ppe_solver
    ).strip().lower()
    ppe_solver_name = ppe_aliases.get(raw_ppe, raw_ppe)
    if ppe_solver_name not in ppe_registry:
        raise ValueError(
            f"Unsupported ppe_solver={raw_ppe!r}. "
            "Use fvm_iterative|fvm_direct|fccd_iterative."
        )

    ppe_iteration_method = str(options.ppe_iteration_method).strip().lower()
    ppe_coefficient_scheme = str(options.ppe_coefficient_scheme).strip().lower()
    ppe_interface_coupling_scheme = str(
        options.ppe_interface_coupling_scheme
    ).strip().lower()
    if str(surface_tension_scheme).strip().lower() == "pressure_jump":
        if ppe_coefficient_scheme != "phase_separated":
            raise ValueError(
                "surface_tension_scheme='pressure_jump' requires "
                "ppe_coefficient_scheme='phase_separated'"
            )
        if ppe_interface_coupling_scheme != "jump_decomposition":
            raise ValueError(
                "surface_tension_scheme='pressure_jump' requires "
                "ppe_interface_coupling_scheme='jump_decomposition'"
            )

    return NSPPERuntimeState(
        ppe_solver_name=ppe_solver_name,
        ppe_iteration_method=ppe_iteration_method,
        ppe_coefficient_scheme=ppe_coefficient_scheme,
        ppe_interface_coupling_scheme=ppe_interface_coupling_scheme,
        ppe_tolerance=float(options.ppe_tolerance),
        ppe_max_iterations=int(options.ppe_max_iterations),
        ppe_restart=options.ppe_restart,
        ppe_preconditioner=str(options.ppe_preconditioner).strip().lower(),
        ppe_pcr_stages=options.ppe_pcr_stages,
        ppe_c_tau=float(options.ppe_c_tau),
        ppe_defect_correction=bool(options.ppe_defect_correction),
        ppe_dc_max_iterations=int(options.ppe_dc_max_iterations),
        ppe_dc_tolerance=float(options.ppe_dc_tolerance),
        ppe_dc_relaxation=float(options.ppe_dc_relaxation),
        pressure_scheme=(
            "fvm_matrixfree" if ppe_solver_name == "fvm_iterative"
            else "fvm_spsolve" if ppe_solver_name == "fvm_direct"
            else "fccd_matrixfree"
        ),
    )


def normalise_ns_scheme_runtime(options) -> NSSchemeRuntimeState:
    conv_time_aliases = {
        "adams_bashforth_2": "ab2",
        "adams_bashforth": "ab2",
        "ab_2": "ab2",
        "explicit": "ab2",
        "forward_euler": "forward_euler",
        "euler": "forward_euler",
    }
    raw_time_scheme = str(options.convection_time_scheme).strip().lower()
    convection_time_scheme = conv_time_aliases.get(raw_time_scheme, raw_time_scheme)
    if convection_time_scheme not in {"ab2", "forward_euler"}:
        raise ValueError(
            "Unsupported convection_time_scheme="
            f"{convection_time_scheme!r}; use ab2|forward_euler."
        )

    momentum_gradient_scheme = str(options.momentum_gradient_scheme).strip().lower()
    pressure_gradient_scheme = str(
        options.pressure_gradient_scheme or momentum_gradient_scheme
    ).strip().lower()
    raw_st_scheme = str(options.surface_tension_scheme).strip().lower()
    if raw_st_scheme == "pressure_jump":
        if options.surface_tension_gradient_scheme not in {None, "none"}:
            raise ValueError(
                "surface_tension_gradient_scheme must be omitted or 'none' "
                "when surface_tension_scheme='pressure_jump'"
            )
        surface_tension_gradient_scheme = "none"
    else:
        surface_tension_gradient_scheme = str(
            options.surface_tension_gradient_scheme or momentum_gradient_scheme
        ).strip().lower()

    return NSSchemeRuntimeState(
        convection_time_scheme=convection_time_scheme,
        momentum_gradient_scheme=momentum_gradient_scheme,
        pressure_gradient_scheme=pressure_gradient_scheme,
        surface_tension_gradient_scheme=surface_tension_gradient_scheme,
        advection_scheme=str(options.advection_scheme),
        convection_scheme=str(options.convection_scheme),
    )
