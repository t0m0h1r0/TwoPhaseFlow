"""Layout and time-integrator parsing helpers for run-section config handling."""

from __future__ import annotations

from .config_sections import validate_choice

_MOMENTUM_PREDICTORS = ("projection_predictor_corrector",)
_MOMENTUM_PREDICTOR_ALIASES = {
    "predictor_corrector": "projection_predictor_corrector",
    "fractional_step": "projection_predictor_corrector",
}


def normalize_momentum_predictor(raw: str) -> str:
    key = str(raw).strip().lower()
    return _MOMENTUM_PREDICTOR_ALIASES.get(key, key)


def parse_numerics_layout(numerics: dict) -> dict:
    """Return canonical numeric sub-sections from the ch13 YAML schema."""
    if "interface" in numerics and "momentum" in numerics and "projection" in numerics:
        interface_num = numerics["interface"]
        time_num = numerics.get("time", {}) or {}
        interface_transport = dict(interface_num["transport"])
        validate_choice(
            normalize_momentum_predictor(
                time_num.get(
                    "algorithm",
                    time_num.get("momentum_predictor", "projection_predictor_corrector"),
                )
            ),
            _MOMENTUM_PREDICTORS,
            "numerics.time.algorithm",
        )
        tracking = dict(interface_num.get("tracking", {}) or {})
        if "primary" not in tracking:
            tracking["primary"] = interface_transport.get("variable", "psi")
        if "enabled" not in tracking:
            tracking["enabled"] = tracking["primary"] != "none"
        momentum = numerics["momentum"]
        terms = momentum.get("terms", {}) or {}
        operators = momentum.get("operators", {}) or {}
        convection = terms.get("convection", operators.get("convection"))
        viscosity = terms.get("viscosity", operators.get("viscosity"))
        surface_tension = terms.get("surface_tension", operators.get("surface_tension"))
        if surface_tension is None:
            surface_tension = {"model": "pressure_jump"}
        pressure_term = terms.get("pressure", {})
        if not pressure_term and "gradient" in operators:
            pressure_term = {
                "spatial": operators["gradient"].get("spatial", "projection_consistent")
            }
        if "spatial" not in surface_tension and "gradient" in operators:
            surface_tension = dict(surface_tension)
            surface_tension["spatial"] = operators["gradient"].get(
                "spatial",
                "projection_consistent",
            )
        projection = numerics["projection"]
        return {
            "interface_transport": interface_transport,
            "tracking": tracking,
            "momentum": momentum,
            "convection": convection,
            "viscosity": viscosity,
            "pressure_term": pressure_term,
            "surface_tension": surface_tension,
            "gravity": terms.get("gravity", {"enabled": False}),
            "projection": projection,
            "paths": {
                "interface_spatial": "numerics.interface.transport.spatial",
                "interface_time": "numerics.interface.transport.time_integrator",
                "tracking_primary": "numerics.interface.tracking.primary",
                "tracking_redistance": "numerics.interface.tracking.redistance.schedule.every_steps",
                "momentum_form": "numerics.momentum.form",
                "convection_spatial": "numerics.momentum.terms.convection.spatial",
                "convection_time": "numerics.momentum.terms.convection.time_integrator",
                "convection_uccd6_sigma": "numerics.momentum.terms.convection.uccd6_sigma",
                "viscosity_spatial": "numerics.momentum.terms.viscosity.spatial",
                "viscosity_time": "numerics.momentum.terms.viscosity.time_integrator",
                "pressure_spatial": "numerics.momentum.terms.pressure.gradient",
                "surface_tension_model": "numerics.momentum.terms.surface_tension.formulation",
                "surface_tension_curvature": "interface.geometry.curvature.method",
                "surface_tension_spatial": "numerics.momentum.terms.surface_tension.gradient",
                "projection_mode": "numerics.projection.mode",
                "poisson_discretization": "numerics.projection.poisson.operator.discretization",
                "poisson_coefficient": "numerics.projection.poisson.operator.coefficient",
                "poisson_interface_coupling": "numerics.projection.poisson.operator.interface_coupling",
                "poisson_solver": "numerics.projection.poisson.solver",
            },
        }
    physical_time = numerics["physical_time"]
    elliptic = numerics["elliptic"]
    interface_transport = physical_time["interface_advection"]
    momentum = physical_time["momentum"]
    projection = elliptic["pressure_projection"]
    return {
        "interface_transport": interface_transport,
        "tracking": interface_transport["tracking"],
        "momentum": momentum,
        "convection": momentum["convection"],
        "viscosity": momentum["viscosity"],
        "pressure_term": {},
        "surface_tension": momentum["capillary_force"],
        "gravity": {"enabled": False},
        "projection": projection,
        "paths": {
            "interface_spatial": "numerics.physical_time.interface_advection.spatial",
            "interface_time": "numerics.physical_time.interface_advection.time",
            "tracking_primary": "numerics.physical_time.interface_advection.tracking.primary",
            "tracking_redistance": (
                "numerics.physical_time.interface_advection.tracking."
                "redistance.schedule.every_steps"
            ),
            "momentum_form": "numerics.physical_time.momentum.form",
            "convection_spatial": "numerics.physical_time.momentum.convection.spatial",
            "convection_time": "numerics.physical_time.momentum.convection.time",
            "convection_uccd6_sigma": "numerics.physical_time.momentum.convection.uccd6_sigma",
            "viscosity_spatial": "numerics.physical_time.momentum.viscosity.spatial",
            "viscosity_time": "numerics.physical_time.momentum.viscosity.time",
            "pressure_spatial": "numerics.elliptic.pressure_projection.pressure.gradient",
            "surface_tension_model": "numerics.physical_time.momentum.capillary_force.formulation",
            "surface_tension_curvature": "numerics.physical_time.momentum.capillary_force.curvature",
            "surface_tension_spatial": "numerics.physical_time.momentum.capillary_force.force_gradient",
            "projection_mode": "numerics.elliptic.pressure_projection.mode",
            "poisson_discretization": "numerics.elliptic.pressure_projection.poisson.discretization",
            "poisson_coefficient": "numerics.elliptic.pressure_projection.poisson.coefficient",
            "poisson_interface_coupling": "numerics.elliptic.pressure_projection.poisson.interface_coupling",
            "poisson_solver": "numerics.elliptic.pressure_projection.poisson.solver",
        },
    }


def parse_time_integrator(
    cfg: dict,
    choices: tuple[str, ...],
    path: str,
    *,
    default: str = "forward_euler",
    aliases: dict[str, str] | None = None,
) -> str:
    raw = cfg.get("time_integrator", cfg.get("time", default))
    value = str(raw).strip().lower()
    alias_map = {
        "explicit": "forward_euler",
        "euler": "forward_euler",
        "euler_forward": "forward_euler",
        "forward-euler": "forward_euler",
        "cn": "crank_nicolson",
        "crank-nicolson": "crank_nicolson",
        "adams_bashforth_2": "ab2",
        "adams_bashforth": "ab2",
        "ab_2": "ab2",
        "runge_kutta_3": "tvd_rk3",
        "ssp_rk3": "tvd_rk3",
        "tvd_runge_kutta_3": "tvd_rk3",
        "rk3": "tvd_rk3",
    }
    if aliases:
        alias_map.update(aliases)
    return validate_choice(alias_map.get(value, value), choices, path)
