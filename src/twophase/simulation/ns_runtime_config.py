"""Runtime option normalization helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from .ns_option_canonicalizer import (
    canonicalize_convection_time_scheme,
    canonicalize_momentum_gradient_scheme,
    canonicalize_ppe_solver_name,
    canonicalize_surface_tension_gradient_scheme,
    canonicalize_viscous_time_scheme,
    pressure_scheme_for_ppe_solver,
    validate_pressure_jump_ppe_compatibility,
)


@dataclass(frozen=True)
class NSInterfaceRuntimeState:
    rebuild_freq: int
    reinit_every: int
    reinit_method: str
    reinit_trigger_mode: str
    reinit_threshold: float
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
    ppe_dc_base_solver_name: str | None
    ppe_iteration_method: str
    ppe_coefficient_scheme: str
    ppe_interface_coupling_scheme: str
    capillary_range_projection: str
    capillary_reaction_projection: str
    pressure_force_contract: str
    scalar_operator_pairing: str
    pressure_history_mode: str
    pressure_history_extrapolation: str
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
    ppe_dc_fail_close: bool
    pressure_scheme: str


@dataclass(frozen=True)
class NSSchemeRuntimeState:
    momentum_form: str
    convection_time_scheme: str
    viscous_time_scheme: str
    viscous_solver: str
    viscous_solver_tolerance: float
    viscous_solver_max_iterations: int
    viscous_solver_restart: int
    viscous_dc_max_iterations: int
    viscous_dc_relaxation: float
    viscous_dc_low_operator: str
    momentum_gradient_scheme: str
    pressure_gradient_scheme: str
    surface_tension_gradient_scheme: str
    capillary_force_source: str
    curvature_method: str
    gravity_formulation: str
    gravity_transport_adjoint: str
    gravity_metric: str
    gravity_hodge_gate: str
    gravity_work_gate: str
    advection_scheme: str
    convection_scheme: str


def normalise_ns_interface_runtime(options) -> NSInterfaceRuntimeState:
    rebuild_freq = max(0, int(options.grid_rebuild_freq))
    reinit_every = int(options.reinit_every)
    reinit_method = str(getattr(options, "reinit_method", "ridge_eikonal")).strip().lower()
    reinit_trigger_mode = str(getattr(options, "reinit_trigger_mode", "adaptive")).strip().lower()
    if reinit_trigger_mode not in {"adaptive", "fixed"}:
        raise ValueError(
            "Unsupported reinit_trigger_mode="
            f"'{getattr(options, 'reinit_trigger_mode', None)}'. Use adaptive|fixed."
        )
    reinit_threshold = float(getattr(options, "reinit_threshold", 1.10))
    if reinit_threshold <= 1.0:
        raise ValueError("reinit_threshold must be > 1.0")
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
    if interface_tracking_method not in {
        "phi_primary",
        "psi_direct",
        "q_cell_fraction",
        "none",
    }:
        raise ValueError(
            "Unsupported interface_tracking_method="
            f"'{tracking_method}'. Use phi_primary|psi_direct|q_cell_fraction|none."
        )

    phi_primary_transport = (
        bool(options.phi_primary_transport)
        if interface_tracking_method not in {
            "phi_primary",
            "psi_direct",
            "q_cell_fraction",
        }
        else interface_tracking_method == "phi_primary"
    )
    phi_primary_redist_every = max(1, int(options.phi_primary_redist_every))
    phi_primary_clip_factor = max(2.0, float(options.phi_primary_clip_factor))
    phi_primary_heaviside_eps_scale = max(
        1.0, float(options.phi_primary_heaviside_eps_scale)
    )

    reproject_mode = str(options.reproject_mode).strip().lower()
    if reproject_mode not in {
        "legacy", "variable_density_only", "face_hodge", "gfm", "consistent_gfm",
    }:
        raise ValueError(
            f"Unsupported reproject_mode='{options.reproject_mode}'. "
            "Use legacy|variable_density_only|face_hodge|gfm|consistent_gfm."
        )
    if reproject_variable_density and reproject_mode == "legacy":
        reproject_mode = "variable_density_only"

    return NSInterfaceRuntimeState(
        rebuild_freq=rebuild_freq,
        reinit_every=reinit_every,
        reinit_method=reinit_method,
        reinit_trigger_mode=reinit_trigger_mode,
        reinit_threshold=reinit_threshold,
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
    )
    ppe_solver_name = canonicalize_ppe_solver_name(
        raw_ppe,
        ppe_aliases=ppe_aliases,
        ppe_registry=ppe_registry,
    )
    ppe_defect_correction = bool(options.ppe_defect_correction)
    raw_base_solver = getattr(options, "ppe_dc_base_solver", None)
    if ppe_defect_correction:
        if raw_base_solver is None:
            raw_base_solver = (
                "fd_direct"
                if ppe_solver_name in {"fccd_iterative", "fvm_iterative"}
                else ppe_solver_name
            )
        ppe_dc_base_solver_name = canonicalize_ppe_solver_name(
            raw_base_solver,
            ppe_aliases=ppe_aliases,
            ppe_registry=ppe_registry,
        )
    else:
        ppe_dc_base_solver_name = None

    ppe_iteration_method = str(options.ppe_iteration_method).strip().lower()
    ppe_coefficient_scheme = str(options.ppe_coefficient_scheme).strip().lower()
    ppe_interface_coupling_scheme = str(
        options.ppe_interface_coupling_scheme
    ).strip().lower()
    capillary_range_projection = str(
        getattr(options, "capillary_range_projection", "auto")
    ).strip().lower()
    capillary_reaction_projection = str(
        getattr(options, "capillary_reaction_projection", "none")
    ).strip().lower()
    pressure_force_contract = str(
        getattr(options, "pressure_force_contract", "raw_compact_gradient")
    ).strip().lower()
    scalar_operator_pairing = str(
        getattr(options, "scalar_operator_pairing", "legacy")
    ).strip().lower()
    pressure_history_mode = str(
        getattr(options, "pressure_history_mode", "face_acceleration")
    ).strip().lower()
    pressure_history_extrapolation = str(
        getattr(options, "pressure_history_extrapolation", "constant")
    ).strip().lower()
    if capillary_range_projection not in {
        "auto",
        "none",
        "range_projected",
        "component_hodge_augmented",
    }:
        raise ValueError(
            "Unsupported capillary_range_projection="
            f"'{getattr(options, 'capillary_range_projection', None)}'. "
            "Use auto|none|range_projected|component_hodge_augmented."
        )
    if capillary_range_projection == "auto":
        capillary_range_projection = (
            "component_hodge_augmented"
            if (
                surface_tension_scheme == "pressure_jump"
                and ppe_interface_coupling_scheme == "affine_jump"
            )
            else "none"
        )
    elif surface_tension_scheme != "pressure_jump":
        capillary_range_projection = "none"
    if (
        capillary_range_projection != "none"
        and ppe_interface_coupling_scheme != "affine_jump"
    ):
        raise ValueError(
            "capillary_range_projection requires "
            "ppe_interface_coupling_scheme='affine_jump'."
        )
    if capillary_reaction_projection not in {"none", "pressure_component_hodge"}:
        raise ValueError(
            "Unsupported capillary_reaction_projection="
            f"'{getattr(options, 'capillary_reaction_projection', None)}'. "
            "Use none|pressure_component_hodge."
        )
    if (
        capillary_reaction_projection != "none"
        and ppe_interface_coupling_scheme != "affine_jump"
    ):
        raise ValueError(
            "capillary_reaction_projection requires "
            "ppe_interface_coupling_scheme='affine_jump'."
        )
    if pressure_force_contract not in {
        "raw_compact_gradient",
        "variational_adjoint",
    }:
        raise ValueError(
            "Unsupported pressure_force_contract="
            f"'{getattr(options, 'pressure_force_contract', None)}'. "
            "Use raw_compact_gradient|variational_adjoint."
        )
    if scalar_operator_pairing not in {
        "legacy",
        "require_certified",
        "variational_operator",
    }:
        raise ValueError(
            "Unsupported scalar_operator_pairing="
            f"'{getattr(options, 'scalar_operator_pairing', None)}'. "
            "Use legacy|require_certified|variational_operator."
        )
    if (
        pressure_force_contract == "raw_compact_gradient"
        and scalar_operator_pairing != "legacy"
    ):
        raise ValueError(
            "scalar_operator_pairing requires "
            "pressure_force_contract='variational_adjoint' unless using legacy."
        )
    if pressure_history_mode not in {
        "face_acceleration",
        "pressure_coordinate",
    }:
        raise ValueError(
            "Unsupported pressure_history_mode="
            f"'{getattr(options, 'pressure_history_mode', None)}'. "
            "Use face_acceleration|pressure_coordinate."
        )
    if pressure_history_extrapolation not in {"constant", "bdf2"}:
        raise ValueError(
            "Unsupported pressure_history_extrapolation="
            f"'{getattr(options, 'pressure_history_extrapolation', None)}'. "
            "Use constant|bdf2."
        )
    if (
        pressure_history_mode == "pressure_coordinate"
        and pressure_force_contract != "variational_adjoint"
    ):
        raise ValueError(
            "pressure_history_mode='pressure_coordinate' requires "
            "pressure_force_contract='variational_adjoint'."
        )
    validate_pressure_jump_ppe_compatibility(
        surface_tension_scheme=surface_tension_scheme,
        ppe_coefficient_scheme=ppe_coefficient_scheme,
        ppe_interface_coupling_scheme=ppe_interface_coupling_scheme,
        coefficient_error=(
            "surface_tension_scheme='pressure_jump' requires "
            "ppe_coefficient_scheme='phase_separated'"
        ),
        interface_error=(
            "surface_tension_scheme='pressure_jump' requires "
            "ppe_interface_coupling_scheme='affine_jump' "
            "(or explicit legacy 'jump_decomposition')"
        ),
    )

    return NSPPERuntimeState(
        ppe_solver_name=ppe_solver_name,
        ppe_dc_base_solver_name=ppe_dc_base_solver_name,
        ppe_iteration_method=ppe_iteration_method,
        ppe_coefficient_scheme=ppe_coefficient_scheme,
        ppe_interface_coupling_scheme=ppe_interface_coupling_scheme,
        capillary_range_projection=capillary_range_projection,
        capillary_reaction_projection=capillary_reaction_projection,
        pressure_force_contract=pressure_force_contract,
        scalar_operator_pairing=scalar_operator_pairing,
        pressure_history_mode=pressure_history_mode,
        pressure_history_extrapolation=pressure_history_extrapolation,
        ppe_tolerance=float(options.ppe_tolerance),
        ppe_max_iterations=int(options.ppe_max_iterations),
        ppe_restart=options.ppe_restart,
        ppe_preconditioner=str(options.ppe_preconditioner).strip().lower(),
        ppe_pcr_stages=options.ppe_pcr_stages,
        ppe_c_tau=float(options.ppe_c_tau),
        ppe_defect_correction=ppe_defect_correction,
        ppe_dc_max_iterations=int(options.ppe_dc_max_iterations),
        ppe_dc_tolerance=float(options.ppe_dc_tolerance),
        ppe_dc_relaxation=float(options.ppe_dc_relaxation),
        ppe_dc_fail_close=bool(getattr(options, "ppe_dc_fail_close", False)),
        pressure_scheme=pressure_scheme_for_ppe_solver(ppe_solver_name),
    )


def normalise_ns_scheme_runtime(options) -> NSSchemeRuntimeState:
    momentum_form = str(
        getattr(options, "momentum_form", "primitive_velocity")
    ).strip().lower()
    if momentum_form not in {"primitive_velocity", "conservative_common_flux"}:
        raise ValueError(
            "Unsupported momentum_form="
            f"'{getattr(options, 'momentum_form', None)}'. "
            "Use primitive_velocity|conservative_common_flux."
        )
    convection_time_scheme = canonicalize_convection_time_scheme(
        options.convection_time_scheme
    )
    raw_viscous_time_scheme = getattr(
        options,
        "viscous_time_scheme",
        "crank_nicolson" if getattr(options, "cn_viscous", False) else "implicit_bdf2",
    )
    viscous_time_scheme = canonicalize_viscous_time_scheme(raw_viscous_time_scheme)
    if convection_time_scheme == "imex_bdf2" and viscous_time_scheme != "implicit_bdf2":
        raise ValueError(
            "convection_time_scheme='imex_bdf2' requires "
            "viscosity.time_integrator='implicit_bdf2'."
        )
    if viscous_time_scheme == "implicit_bdf2" and convection_time_scheme != "imex_bdf2":
        raise ValueError(
            "viscosity.time_integrator='implicit_bdf2' requires "
            "convection.time_integrator='imex_bdf2'."
        )
    momentum_gradient_scheme = canonicalize_momentum_gradient_scheme(
        options.momentum_gradient_scheme
    )
    pressure_gradient_scheme = canonicalize_momentum_gradient_scheme(
        options.pressure_gradient_scheme or momentum_gradient_scheme
    )
    surface_tension_gradient_scheme = canonicalize_surface_tension_gradient_scheme(
        surface_tension_scheme=options.surface_tension_scheme,
        surface_tension_gradient_scheme=options.surface_tension_gradient_scheme,
        momentum_gradient_scheme=momentum_gradient_scheme,
    )
    capillary_force_source = str(
        getattr(options, "capillary_force_source", "curvature_jump")
    ).strip().lower()
    if capillary_force_source not in {
        "curvature_jump",
        "closed_interface_riesz",
        "bundle_virtual_work",
    }:
        raise ValueError(
            "Unsupported capillary_force_source="
            f"'{getattr(options, 'capillary_force_source', None)}'. "
            "Use curvature_jump|closed_interface_riesz|bundle_virtual_work."
        )
    if (
        capillary_force_source in {"closed_interface_riesz", "bundle_virtual_work"}
        and str(options.surface_tension_scheme).strip().lower() != "pressure_jump"
    ):
        raise ValueError(
            f"capillary_force_source='{capillary_force_source}' requires "
            "surface_tension_scheme='pressure_jump'."
        )
    gravity_formulation = str(
        getattr(options, "gravity_formulation", "body_acceleration")
    ).strip().lower()
    if gravity_formulation not in {
        "none",
        "body_acceleration",
        "variational_potential",
    }:
        raise ValueError(
            "Unsupported gravity_formulation="
            f"'{getattr(options, 'gravity_formulation', None)}'. "
            "Use none|body_acceleration|variational_potential."
        )
    gravity_transport_adjoint = str(
        getattr(options, "gravity_transport_adjoint", "legacy")
    ).strip().lower()
    gravity_metric = str(getattr(options, "gravity_metric", "legacy")).strip().lower()
    gravity_hodge_gate = str(
        getattr(options, "gravity_hodge_gate", "off")
    ).strip().lower()
    gravity_work_gate = str(getattr(options, "gravity_work_gate", "off")).strip().lower()
    if gravity_transport_adjoint not in {"legacy", "common_flux"}:
        raise ValueError("gravity_transport_adjoint must be legacy|common_flux.")
    if gravity_metric not in {"legacy", "transported_face_mass"}:
        raise ValueError("gravity_metric must be legacy|transported_face_mass.")
    if gravity_hodge_gate not in {"off", "diagnostic", "fail_close"}:
        raise ValueError("gravity_hodge_gate must be off|diagnostic|fail_close.")
    if gravity_work_gate not in {"off", "diagnostic", "fail_close"}:
        raise ValueError("gravity_work_gate must be off|diagnostic|fail_close.")
    if gravity_formulation == "variational_potential":
        if momentum_form != "conservative_common_flux":
            raise ValueError(
                "gravity_formulation='variational_potential' requires "
                "momentum_form='conservative_common_flux'."
            )
        if gravity_transport_adjoint != "common_flux":
            raise ValueError(
                "gravity_formulation='variational_potential' requires "
                "gravity_transport_adjoint='common_flux'."
            )
        if gravity_metric != "transported_face_mass":
            raise ValueError(
                "gravity_formulation='variational_potential' requires "
                "gravity_metric='transported_face_mass'."
            )

    return NSSchemeRuntimeState(
        momentum_form=momentum_form,
        convection_time_scheme=convection_time_scheme,
        viscous_time_scheme=viscous_time_scheme,
        viscous_solver=str(getattr(options, "viscous_solver", "defect_correction")),
        viscous_solver_tolerance=float(getattr(options, "viscous_solver_tolerance", 1.0e-8)),
        viscous_solver_max_iterations=int(getattr(options, "viscous_solver_max_iterations", 80)),
        viscous_solver_restart=int(getattr(options, "viscous_solver_restart", 40)),
        viscous_dc_max_iterations=int(getattr(options, "viscous_dc_max_iterations", 3)),
        viscous_dc_relaxation=float(getattr(options, "viscous_dc_relaxation", 0.8)),
        viscous_dc_low_operator=str(getattr(options, "viscous_dc_low_operator", "component")),
        momentum_gradient_scheme=momentum_gradient_scheme,
        pressure_gradient_scheme=pressure_gradient_scheme,
        surface_tension_gradient_scheme=surface_tension_gradient_scheme,
        capillary_force_source=capillary_force_source,
        curvature_method=str(
            getattr(options, "curvature_method", "psi_direct_filtered")
        ).strip().lower(),
        gravity_formulation=gravity_formulation,
        gravity_transport_adjoint=gravity_transport_adjoint,
        gravity_metric=gravity_metric,
        gravity_hodge_gate=gravity_hodge_gate,
        gravity_work_gate=gravity_work_gate,
        advection_scheme=str(options.advection_scheme),
        convection_scheme=str(options.convection_scheme),
    )
