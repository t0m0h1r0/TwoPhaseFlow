"""Operator and solver parsing helpers for run-section config handling."""

from __future__ import annotations

from .config_constants import (
    _ADVECTION_SCHEME_ALIASES,
    _ADVECTION_SCHEMES,
    _CONVECTION_SCHEME_ALIASES,
    _CONVECTION_SCHEMES,
    _CONVECTION_TIME_SCHEMES,
    _CURVATURE_SCHEME_ALIASES,
    _CURVATURE_SCHEMES,
    _INTERFACE_TIME_SCHEMES,
    _MOMENTUM_FORMS,
    _SURFACE_TENSION_ALIASES as _SURFACE_TENSION_ALIASES_BASE,
    _SURFACE_TENSION_SCHEMES,
    _VISCOUS_DC_LOW_OPERATOR_ALIASES,
    _VISCOUS_DC_LOW_OPERATORS,
    _VISCOUS_SPATIAL_ALIASES as _VISCOUS_SPATIAL_ALIASES_BASE,
    _VISCOUS_SPATIAL_SCHEMES,
    _VISCOUS_SOLVER_ALIASES,
    _VISCOUS_SOLVERS,
    _VISCOUS_TIME_SCHEMES,
)
from .config_run_poisson_sections import parse_run_poisson_settings
from .ns_option_canonicalizer import (
    CONVECTION_TIME_SCHEME_ALIASES,
    VISCOUS_TIME_SCHEME_ALIASES,
    canonicalize_momentum_gradient_scheme,
    canonicalize_surface_tension_gradient_scheme,
    validate_pressure_jump_ppe_compatibility,
)
from .config_sections import validate_choice
from .config_run_layout_sections import parse_time_integrator

_SURFACE_TENSION_ALIASES = {
    **_SURFACE_TENSION_ALIASES_BASE,
    "balanced_force": "csf",
}
_VISCOUS_SPATIAL_ALIASES = {
    **_VISCOUS_SPATIAL_ALIASES_BASE,
    "conservative": "conservative_stress",
}
_CN_MODES = ("picard", "richardson_picard")
_CN_MODE_ALIASES = {
    "richardson": "richardson_picard",
    "cn_richardson": "richardson_picard",
    "richardson_cn": "richardson_picard",
}
_PREDICTOR_ASSEMBLY_MODES = (
    "none",
    "balanced_buoyancy",
)
_PREDICTOR_ASSEMBLY_ALIASES = {
    "balanced": "balanced_buoyancy",
    "well_balanced": "balanced_buoyancy",
    "well_balanced_buoyancy": "balanced_buoyancy",
    "buoyancy_split": "balanced_buoyancy",
    "buoyancy_faceresidual_stagesplit_transversefullband": "balanced_buoyancy",
}


def parse_run_operator_settings(
    *,
    layout: dict,
    interface_transport: dict,
    momentum: dict,
    convection: dict,
    viscosity: dict,
    pressure_term: dict,
    surface_tension: dict,
    interface_curvature: dict,
    projection: dict,
) -> dict:
    poisson_settings = parse_run_poisson_settings(
        layout=layout,
        projection=projection,
    )

    advection_scheme = validate_choice(
        _ADVECTION_SCHEME_ALIASES.get(
            str(interface_transport["spatial"]).strip().lower(),
            interface_transport["spatial"],
        ),
        _ADVECTION_SCHEMES,
        layout["paths"]["interface_spatial"],
    )
    parse_time_integrator(
        interface_transport,
        _INTERFACE_TIME_SCHEMES,
        layout["paths"]["interface_time"],
        default="tvd_rk3",
        aliases={"explicit": "tvd_rk3", "rk3": "tvd_rk3"},
    )
    validate_choice(
        momentum.get("form", "primitive_velocity"),
        _MOMENTUM_FORMS,
        layout["paths"]["momentum_form"],
    )
    convection_scheme = validate_choice(
        _CONVECTION_SCHEME_ALIASES.get(
            str(convection["spatial"]).strip().lower(),
            convection["spatial"],
        ),
        _CONVECTION_SCHEMES,
        layout["paths"]["convection_spatial"],
    )
    convection_time_scheme = parse_time_integrator(
        convection,
        _CONVECTION_TIME_SCHEMES,
        layout["paths"]["convection_time"],
        default="ab2",
        aliases=CONVECTION_TIME_SCHEME_ALIASES,
    )
    raw_p_grad = pressure_term.get("gradient", pressure_term.get("spatial", "ccd"))
    pressure_gradient_scheme = canonicalize_momentum_gradient_scheme(
        raw_p_grad,
        path=layout["paths"]["pressure_spatial"],
    )
    surface_tension_scheme = validate_choice(
        _SURFACE_TENSION_ALIASES.get(
            str(
                surface_tension.get("formulation", surface_tension.get("model", "csf"))
            ).strip().lower(),
            surface_tension.get("formulation", surface_tension.get("model", "csf")),
        ),
        _SURFACE_TENSION_SCHEMES,
        layout["paths"]["surface_tension_model"],
    )
    momentum_gradient_scheme = pressure_gradient_scheme
    if surface_tension_scheme == "pressure_jump":
        validate_pressure_jump_ppe_compatibility(
            surface_tension_scheme=surface_tension_scheme,
            ppe_coefficient_scheme=poisson_settings["poisson_coefficient"],
            ppe_interface_coupling_scheme=poisson_settings["poisson_interface_coupling"],
            coefficient_error=(
                f"{layout['paths']['surface_tension_model']}='pressure_jump' "
                "requires poisson.operator.coefficient='phase_separated'."
            ),
            interface_error=(
                f"{layout['paths']['surface_tension_model']}='pressure_jump' "
                "requires poisson.operator.interface_coupling="
                "'affine_jump' (or explicit legacy 'jump_decomposition')."
            ),
        )
        explicit_st_grad = any(
            key in surface_tension for key in ("gradient", "spatial", "force_gradient")
        )
        raw_st_grad = (
            surface_tension.get(
                "gradient",
                surface_tension.get(
                    "spatial",
                    surface_tension.get("force_gradient"),
                ),
            )
            if explicit_st_grad
            else None
        )
    else:
        raw_st_grad = surface_tension.get(
            "gradient",
            surface_tension.get("spatial", surface_tension.get("force_gradient", "ccd")),
        )
    surface_tension_gradient_scheme = canonicalize_surface_tension_gradient_scheme(
        surface_tension_scheme=surface_tension_scheme,
        surface_tension_gradient_scheme=raw_st_grad,
        momentum_gradient_scheme=momentum_gradient_scheme,
        path=layout["paths"]["surface_tension_spatial"],
    )
    raw_curvature_method = str(
        interface_curvature.get(
            "method",
            surface_tension.get("curvature", "psi_direct_filtered"),
        )
    ).strip().lower()
    validate_choice(
        _CURVATURE_SCHEME_ALIASES.get(raw_curvature_method, raw_curvature_method),
        _CURVATURE_SCHEMES,
        layout["paths"]["surface_tension_curvature"],
    )
    uccd6_sigma = float(convection.get("uccd6_sigma", 1.0e-3))
    if uccd6_sigma <= 0.0:
        raise ValueError(
            f"{layout['paths']['convection_uccd6_sigma']} must be > 0, got {uccd6_sigma}"
        )
    viscous_spatial_scheme = validate_choice(
        _VISCOUS_SPATIAL_ALIASES.get(
            str(viscosity["spatial"]).strip().lower(),
            viscosity["spatial"],
        ),
        _VISCOUS_SPATIAL_SCHEMES,
        layout["paths"]["viscosity_spatial"],
    )
    viscous_time_scheme = parse_time_integrator(
        viscosity,
        _VISCOUS_TIME_SCHEMES,
        layout["paths"]["viscosity_time"],
        aliases=VISCOUS_TIME_SCHEME_ALIASES,
    )
    cn_mode = validate_choice(
        _CN_MODE_ALIASES.get(
            str(viscosity.get("cn_mode", "picard")).strip().lower(),
            str(viscosity.get("cn_mode", "picard")).strip().lower(),
        ),
        _CN_MODES,
        f"{layout['paths']['viscosity_time']}.cn_mode",
    )
    raw_viscous_solver = viscosity.get("solver", {}) or {}
    if isinstance(raw_viscous_solver, str):
        viscous_solver_cfg = {"kind": raw_viscous_solver}
    else:
        viscous_solver_cfg = dict(raw_viscous_solver)
    viscous_solver = validate_choice(
        _VISCOUS_SOLVER_ALIASES.get(
            str(viscous_solver_cfg.get("kind", "defect_correction")).strip().lower(),
            str(viscous_solver_cfg.get("kind", "defect_correction")).strip().lower(),
        ),
        _VISCOUS_SOLVERS,
        f"{layout['paths']['viscosity_time']}.solver.kind",
    )
    viscous_dc_cfg = viscous_solver_cfg.get("corrections", {}) or {}
    viscous_solver_tolerance = float(
        viscous_solver_cfg.get("tolerance", viscous_dc_cfg.get("tolerance", 1.0e-8))
    )
    viscous_solver_max_iterations = int(viscous_solver_cfg.get("max_iterations", 80))
    viscous_solver_restart = int(viscous_solver_cfg.get("restart", 40))
    viscous_dc_max_iterations = int(viscous_dc_cfg.get("max_iterations", 3))
    viscous_dc_relaxation = float(viscous_dc_cfg.get("relaxation", 0.8))
    raw_viscous_dc_low_operator = str(
        viscous_dc_cfg.get(
            "low_operator",
            viscous_solver_cfg.get("low_operator", "component"),
        )
    ).strip().lower()
    viscous_dc_low_operator = validate_choice(
        _VISCOUS_DC_LOW_OPERATOR_ALIASES.get(
            raw_viscous_dc_low_operator,
            raw_viscous_dc_low_operator,
        ),
        _VISCOUS_DC_LOW_OPERATORS,
        f"{layout['paths']['viscosity_time']}.solver.corrections.low_operator",
    )
    if viscous_solver_tolerance <= 0.0:
        raise ValueError(
            f"{layout['paths']['viscosity_time']}.solver.tolerance must be > 0"
        )
    if viscous_solver_max_iterations <= 0:
        raise ValueError(
            f"{layout['paths']['viscosity_time']}.solver.max_iterations must be > 0"
        )
    if viscous_solver_restart <= 0:
        raise ValueError(
            f"{layout['paths']['viscosity_time']}.solver.restart must be > 0"
        )
    if viscous_dc_max_iterations <= 0:
        raise ValueError(
            f"{layout['paths']['viscosity_time']}.solver.corrections.max_iterations "
            "must be > 0"
        )
    if viscous_dc_relaxation <= 0.0:
        raise ValueError(
            f"{layout['paths']['viscosity_time']}.solver.corrections.relaxation "
            "must be > 0"
        )
    predictor_cfg = momentum.get("predictor", {}) or {}
    raw_predictor_assembly = predictor_cfg.get(
        "assembly",
        viscosity.get("predictor_assembly", "none"),
    )
    predictor_assembly = validate_choice(
        _PREDICTOR_ASSEMBLY_ALIASES.get(
            str(raw_predictor_assembly).strip().lower(),
            str(raw_predictor_assembly).strip().lower(),
        ),
        _PREDICTOR_ASSEMBLY_MODES,
        "numerics.momentum.predictor.assembly",
    )
    if convection_time_scheme == "imex_bdf2" and viscous_time_scheme != "implicit_bdf2":
        raise ValueError(
            f"{layout['paths']['convection_time']}='imex_bdf2' requires "
            f"{layout['paths']['viscosity_time']}='implicit_bdf2'"
        )
    if viscous_time_scheme == "implicit_bdf2" and convection_time_scheme != "imex_bdf2":
        raise ValueError(
            f"{layout['paths']['viscosity_time']}='implicit_bdf2' requires "
            f"{layout['paths']['convection_time']}='imex_bdf2'"
        )
    return {
        "poisson_coefficient": poisson_settings["poisson_coefficient"],
        "poisson_interface_coupling": poisson_settings["poisson_interface_coupling"],
        "advection_scheme": advection_scheme,
        "convection_scheme": convection_scheme,
        "convection_time_scheme": convection_time_scheme,
        "ppe_solver": poisson_settings["ppe_solver"],
        "ppe_dc_base_solver": poisson_settings["ppe_dc_base_solver"],
        "pressure_scheme": poisson_settings["pressure_scheme"],
        "ppe_iteration_method": poisson_settings["ppe_iteration_method"],
        "ppe_tolerance": poisson_settings["ppe_tolerance"],
        "ppe_max_iterations": poisson_settings["ppe_max_iterations"],
        "ppe_restart": poisson_settings["ppe_restart"],
        "ppe_preconditioner": poisson_settings["ppe_preconditioner"],
        "ppe_pcr_stages": poisson_settings["ppe_pcr_stages"],
        "ppe_c_tau": poisson_settings["ppe_c_tau"],
        "ppe_defect_correction": poisson_settings["ppe_defect_correction"],
        "ppe_dc_max_iterations": poisson_settings["ppe_dc_max_iterations"],
        "ppe_dc_tolerance": poisson_settings["ppe_dc_tolerance"],
        "ppe_dc_relaxation": poisson_settings["ppe_dc_relaxation"],
        "pressure_gradient_scheme": pressure_gradient_scheme,
        "surface_tension_scheme": surface_tension_scheme,
        "surface_tension_gradient_scheme": surface_tension_gradient_scheme,
        "momentum_gradient_scheme": momentum_gradient_scheme,
        "uccd6_sigma": uccd6_sigma,
        "viscous_spatial_scheme": viscous_spatial_scheme,
        "viscous_time_scheme": viscous_time_scheme,
        "viscous_solver": viscous_solver,
        "viscous_solver_tolerance": viscous_solver_tolerance,
        "viscous_solver_max_iterations": viscous_solver_max_iterations,
        "viscous_solver_restart": viscous_solver_restart,
        "viscous_dc_max_iterations": viscous_dc_max_iterations,
        "viscous_dc_relaxation": viscous_dc_relaxation,
        "viscous_dc_low_operator": viscous_dc_low_operator,
        "cn_mode": cn_mode,
        "cn_buoyancy_predictor_assembly_mode": predictor_assembly,
    }
