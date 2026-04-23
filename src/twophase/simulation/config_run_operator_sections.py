"""Operator and solver parsing helpers for run-section config handling."""

from __future__ import annotations

from .config_sections import validate_choice
from .config_run_layout_sections import parse_time_integrator
from .config_run_ppe_sections import parse_ppe_solver_config

_ADVECTION_SCHEMES = ("dissipative_ccd", "weno5", "fccd_nodal", "fccd_flux")
_ADVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_CONVECTION_SCHEMES = ("ccd", "fccd_nodal", "fccd_flux", "uccd6")
_CONVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_PPE_TO_PRESSURE_SCHEME = {
    "fvm_iterative": "fvm_matrixfree",
    "fvm_direct": "fvm_spsolve",
    "fccd_iterative": "fccd_matrixfree",
}
_PPE_DISCRETIZATIONS = ("fvm", "fccd")
_POISSON_COEFFICIENTS = ("phase_density", "variable_density", "phase_separated")
_POISSON_COEFFICIENT_ALIASES = {
    "mixture_density": "phase_density",
    "phase": "phase_separated",
}
_POISSON_INTERFACE_COUPLINGS = ("none", "jump_decomposition")
_POISSON_INTERFACE_COUPLING_ALIASES = {"jump": "jump_decomposition"}
_SURFACE_TENSION_SCHEMES = ("csf", "pressure_jump", "none")
_SURFACE_TENSION_ALIASES = {"balanced_force": "csf"}
_VISCOUS_TIME_SCHEMES = ("forward_euler", "crank_nicolson")
_INTERFACE_TIME_SCHEMES = ("tvd_rk3",)
_CONVECTION_TIME_SCHEMES = ("ab2", "forward_euler")
_MOMENTUM_FORMS = ("primitive_velocity",)
_VISCOUS_SPATIAL_SCHEMES = ("conservative_stress", "ccd_bulk", "ccd_stress_legacy")
_VISCOUS_SPATIAL_ALIASES = {
    "ccd": "ccd_bulk",
    "conservative": "conservative_stress",
}
_CURVATURE_SCHEMES = ("psi_direct_hfe",)
_MOMENTUM_GRADIENT_SCHEMES = ("ccd", "fccd_flux", "fccd_nodal")
_MOMENTUM_GRADIENT_ALIASES = {
    "projection_consistent": "ccd",
    "fccd": "fccd_flux",
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
    poisson = projection["poisson"]
    poisson_operator = poisson.get("operator", {})
    if not poisson_operator and ("discretization" in poisson or "coefficient" in poisson):
        poisson_operator = {
            key: poisson[key]
            for key in ("discretization", "coefficient")
            if key in poisson
        }
    poisson_discretization = validate_choice(
        poisson_operator.get("discretization", "fvm"),
        _PPE_DISCRETIZATIONS,
        layout["paths"]["poisson_discretization"],
    )
    if "coefficient" not in poisson_operator:
        raise ValueError(
            f"{layout['paths']['poisson_coefficient']} is required; "
            "use 'phase_separated' for SP-M or 'phase_density' for mixture-density PPE."
        )
    poisson_coefficient = validate_choice(
        _POISSON_COEFFICIENT_ALIASES.get(
            str(poisson_operator["coefficient"]).strip().lower(),
            poisson_operator["coefficient"],
        ),
        _POISSON_COEFFICIENTS,
        layout["paths"]["poisson_coefficient"],
    )
    coupling_default = (
        "jump_decomposition" if poisson_coefficient == "phase_separated" else "none"
    )
    poisson_interface_coupling = validate_choice(
        _POISSON_INTERFACE_COUPLING_ALIASES.get(
            str(poisson_operator.get("interface_coupling", coupling_default)).strip().lower(),
            poisson_operator.get("interface_coupling", coupling_default),
        ),
        _POISSON_INTERFACE_COUPLINGS,
        layout["paths"]["poisson_interface_coupling"],
    )
    if poisson_coefficient == "phase_density" and poisson_interface_coupling != "none":
        raise ValueError(
            f"{layout['paths']['poisson_interface_coupling']} must be 'none' "
            "when poisson coefficient is 'phase_density'."
        )
    ppe_solver_cfg = poisson["solver"]

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
        aliases={"explicit": "ab2"},
    )
    (
        ppe_solver,
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
        ppe_defect_correction,
        ppe_dc_max_iterations,
        ppe_dc_tolerance,
        ppe_dc_relaxation,
    ) = parse_ppe_solver_config(
        ppe_solver_cfg,
        layout["paths"]["poisson_solver"],
        poisson_discretization,
        layout["paths"]["poisson_discretization"],
    )
    pressure_scheme = _PPE_TO_PRESSURE_SCHEME[ppe_solver]
    raw_p_grad = pressure_term.get("gradient", pressure_term.get("spatial", "ccd"))
    pressure_gradient_scheme = validate_choice(
        _MOMENTUM_GRADIENT_ALIASES.get(str(raw_p_grad).strip().lower(), raw_p_grad),
        _MOMENTUM_GRADIENT_SCHEMES,
        layout["paths"]["pressure_spatial"],
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
    if surface_tension_scheme == "pressure_jump":
        if poisson_coefficient != "phase_separated":
            raise ValueError(
                f"{layout['paths']['surface_tension_model']}='pressure_jump' "
                "requires poisson.operator.coefficient='phase_separated'."
            )
        if poisson_interface_coupling != "jump_decomposition":
            raise ValueError(
                f"{layout['paths']['surface_tension_model']}='pressure_jump' "
                "requires poisson.operator.interface_coupling='jump_decomposition'."
            )
        explicit_st_grad = any(
            key in surface_tension for key in ("gradient", "spatial", "force_gradient")
        )
        if explicit_st_grad:
            raise ValueError(
                f"{layout['paths']['surface_tension_spatial']} must be omitted "
                "when surface_tension.formulation='pressure_jump'; "
                "the jump is applied in the PPE, not as σκ∇ψ."
            )
        surface_tension_gradient_scheme = "none"
    else:
        raw_st_grad = surface_tension.get(
            "gradient",
            surface_tension.get("spatial", surface_tension.get("force_gradient", "ccd")),
        )
        surface_tension_gradient_scheme = validate_choice(
            _MOMENTUM_GRADIENT_ALIASES.get(str(raw_st_grad).strip().lower(), raw_st_grad),
            _MOMENTUM_GRADIENT_SCHEMES,
            layout["paths"]["surface_tension_spatial"],
        )
    momentum_gradient_scheme = pressure_gradient_scheme
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
        "poisson_coefficient": poisson_coefficient,
        "poisson_interface_coupling": poisson_interface_coupling,
        "advection_scheme": advection_scheme,
        "convection_scheme": convection_scheme,
        "convection_time_scheme": convection_time_scheme,
        "ppe_solver": ppe_solver,
        "pressure_scheme": pressure_scheme,
        "ppe_iteration_method": ppe_iteration_method,
        "ppe_tolerance": ppe_tolerance,
        "ppe_max_iterations": ppe_max_iterations,
        "ppe_restart": ppe_restart,
        "ppe_preconditioner": ppe_preconditioner,
        "ppe_pcr_stages": ppe_pcr_stages,
        "ppe_c_tau": ppe_c_tau,
        "ppe_defect_correction": ppe_defect_correction,
        "ppe_dc_max_iterations": ppe_dc_max_iterations,
        "ppe_dc_tolerance": ppe_dc_tolerance,
        "ppe_dc_relaxation": ppe_dc_relaxation,
        "pressure_gradient_scheme": pressure_gradient_scheme,
        "surface_tension_scheme": surface_tension_scheme,
        "surface_tension_gradient_scheme": surface_tension_gradient_scheme,
        "momentum_gradient_scheme": momentum_gradient_scheme,
        "uccd6_sigma": uccd6_sigma,
        "viscous_spatial_scheme": viscous_spatial_scheme,
        "viscous_time_scheme": viscous_time_scheme,
    }
