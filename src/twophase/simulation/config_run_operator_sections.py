"""Operator and solver parsing helpers for run-section config handling."""

from __future__ import annotations

from .config_constants import (
    _ADVECTION_SCHEME_ALIASES,
    _ADVECTION_SCHEMES,
    _CAPILLARY_FORCE_SOURCE_ALIASES,
    _CAPILLARY_FORCE_SOURCES,
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
_CLOSED_INTERFACE_ENDPOINTS = ("conservative_psi",)
_CLOSED_INTERFACE_METRICS = ("pressure_adjoint",)
_CLOSED_INTERFACE_CONSTRAINTS = ("component_volume",)


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
        default="imex_bdf2",
        aliases=CONVECTION_TIME_SCHEME_ALIASES,
    )
    raw_p_grad = pressure_term.get("gradient", pressure_term.get("spatial", "fccd_flux"))
    pressure_gradient_scheme = canonicalize_momentum_gradient_scheme(
        raw_p_grad,
        path=layout["paths"]["pressure_spatial"],
    )
    surface_tension_scheme = validate_choice(
        _SURFACE_TENSION_ALIASES.get(
            str(
                surface_tension.get(
                    "formulation",
                    surface_tension.get("model", "pressure_jump"),
                )
            ).strip().lower(),
            surface_tension.get(
                "formulation",
                surface_tension.get("model", "pressure_jump"),
            ),
        ),
        _SURFACE_TENSION_SCHEMES,
        layout["paths"]["surface_tension_model"],
    )
    capillary_force_source = validate_choice(
        _CAPILLARY_FORCE_SOURCE_ALIASES.get(
            str(surface_tension.get("source", "curvature_jump")).strip().lower(),
            surface_tension.get("source", "curvature_jump"),
        ),
        _CAPILLARY_FORCE_SOURCES,
        layout["paths"]["surface_tension_source"],
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
    curvature_method = validate_choice(
        _CURVATURE_SCHEME_ALIASES.get(raw_curvature_method, raw_curvature_method),
        _CURVATURE_SCHEMES,
        layout["paths"]["surface_tension_curvature"],
    )
    if (
        surface_tension_scheme == "pressure_jump"
        and curvature_method == "transport_variational_p2_ale_discrete_gradient"
    ):
        raise ValueError(
            f"{layout['paths']['surface_tension_curvature']}="
            "'transport_variational_p2_ale_discrete_gradient' is not a "
            "validated pressure_jump production route: it leaves a nonzero "
            "divergence-free capillary face cochain on static Young-Laplace "
            "droplets. Use a scalar Young-Laplace jump geometry such as "
            "'face_implicit' until the P2 ALE pressure-jump range projection "
            "is implemented and verified."
        )
    if capillary_force_source == "closed_interface_riesz":
        closed_interface_contract = _parse_closed_interface_contract(
            surface_tension=surface_tension,
            path=(
                f"{layout['paths']['surface_tension_source'].rsplit('.', 1)[0]}"
                ".closed_interface"
            ),
        )
        if surface_tension_scheme != "pressure_jump":
            raise ValueError(
                f"{layout['paths']['surface_tension_source']}='closed_interface_riesz' "
                "requires capillary_force.formulation='pressure_jump'."
            )
        if "curvature" in surface_tension:
            raise ValueError(
                f"{layout['paths']['surface_tension_source']}='closed_interface_riesz' "
                "must not be combined with capillary_force.curvature."
            )
        if "capillary_range_projection" in projection["poisson"].get("operator", {}):
            raise ValueError(
                f"{layout['paths']['surface_tension_source']}='closed_interface_riesz' "
                "uses poisson.operator.capillary_reaction_projection, not "
                "capillary_range_projection."
            )
        if poisson_settings["capillary_reaction_projection"] != "pressure_component_hodge":
            raise ValueError(
                f"{layout['paths']['surface_tension_source']}='closed_interface_riesz' "
                "requires poisson.operator.capillary_reaction_projection="
                "'pressure_component_hodge'."
            )
        poisson_settings["capillary_range_projection"] = "none"
    else:
        closed_interface_contract = _default_closed_interface_contract()
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
        default="implicit_bdf2",
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
        viscosity.get("predictor_assembly", "balanced_buoyancy"),
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
        "capillary_range_projection": poisson_settings["capillary_range_projection"],
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
        "capillary_force_source": capillary_force_source,
        "curvature_method": curvature_method,
        "capillary_reaction_projection": poisson_settings["capillary_reaction_projection"],
        "pressure_force_contract": poisson_settings["pressure_force_contract"],
        "scalar_operator_pairing": poisson_settings["scalar_operator_pairing"],
        **closed_interface_contract,
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


def _default_closed_interface_contract() -> dict:
    return {
        "capillary_closed_interface_endpoint": "conservative_psi",
        "capillary_closed_interface_metric": "pressure_adjoint",
        "capillary_closed_interface_constraints": ("component_volume",),
        "capillary_closed_interface_fail_close": True,
    }


def _parse_closed_interface_contract(*, surface_tension: dict, path: str) -> dict:
    raw_contract = surface_tension.get("closed_interface", {})
    if raw_contract is None:
        raw_contract = {}
    if not isinstance(raw_contract, dict):
        raise ValueError(f"{path} must be a mapping when provided.")
    endpoint = validate_choice(
        str(raw_contract.get("endpoint", "conservative_psi")).strip().lower(),
        _CLOSED_INTERFACE_ENDPOINTS,
        f"{path}.endpoint",
    )
    residual_contract = raw_contract.get("residual_contract", {})
    if residual_contract is None:
        residual_contract = {}
    if not isinstance(residual_contract, dict):
        raise ValueError(f"{path}.residual_contract must be a mapping when provided.")
    metric = validate_choice(
        str(residual_contract.get("metric", "pressure_adjoint")).strip().lower(),
        _CLOSED_INTERFACE_METRICS,
        f"{path}.residual_contract.metric",
    )
    constraints = residual_contract.get("constraints", ("component_volume",))
    if isinstance(constraints, str):
        constraints = (constraints,)
    try:
        constraint_tuple = tuple(
            validate_choice(
                str(constraint).strip().lower(),
                _CLOSED_INTERFACE_CONSTRAINTS,
                f"{path}.residual_contract.constraints",
            )
            for constraint in constraints
        )
    except TypeError as exc:
        raise ValueError(
            f"{path}.residual_contract.constraints must be a sequence."
        ) from exc
    if constraint_tuple != ("component_volume",):
        raise ValueError(
            f"{path}.residual_contract.constraints must be ['component_volume']."
        )
    fail_close = residual_contract.get("fail_close", True)
    if fail_close is not True:
        raise ValueError(f"{path}.residual_contract.fail_close must be true.")
    return {
        "capillary_closed_interface_endpoint": endpoint,
        "capillary_closed_interface_metric": metric,
        "capillary_closed_interface_constraints": constraint_tuple,
        "capillary_closed_interface_fail_close": True,
    }
