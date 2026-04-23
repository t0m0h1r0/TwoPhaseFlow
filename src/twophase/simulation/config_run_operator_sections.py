"""Operator and solver parsing helpers for run-section config handling."""

from __future__ import annotations

from .config_constants import (
    _ADVECTION_SCHEME_ALIASES,
    _ADVECTION_SCHEMES,
    _CONVECTION_SCHEME_ALIASES,
    _CONVECTION_SCHEMES,
    _CURVATURE_SCHEMES,
    _INTERFACE_TIME_SCHEMES,
    _MOMENTUM_FORMS,
    _SURFACE_TENSION_ALIASES as _SURFACE_TENSION_ALIASES_BASE,
    _SURFACE_TENSION_SCHEMES,
    _VISCOUS_SPATIAL_ALIASES as _VISCOUS_SPATIAL_ALIASES_BASE,
    _VISCOUS_SPATIAL_SCHEMES,
    _VISCOUS_TIME_SCHEMES,
)
from .config_run_poisson_sections import parse_run_poisson_settings
from .ns_option_canonicalizer import (
    CONVECTION_TIME_SCHEME_ALIASES,
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
        ("ab2", "forward_euler"),
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
                "requires poisson.operator.interface_coupling='jump_decomposition'."
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
    validate_choice(
        interface_curvature.get("method", surface_tension.get("curvature", "psi_direct_hfe")),
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
    )
    return {
        "poisson_coefficient": poisson_settings["poisson_coefficient"],
        "poisson_interface_coupling": poisson_settings["poisson_interface_coupling"],
        "advection_scheme": advection_scheme,
        "convection_scheme": convection_scheme,
        "convection_time_scheme": convection_time_scheme,
        "ppe_solver": poisson_settings["ppe_solver"],
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
    }
