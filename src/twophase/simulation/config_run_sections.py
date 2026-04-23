"""Run-section parsing helpers for experiment configs."""

from __future__ import annotations

from typing import Any

from .config_sections import opt_float, validate_choice
from .config_models import RunCfg

_ADVECTION_SCHEMES = ("dissipative_ccd", "weno5", "fccd_nodal", "fccd_flux")
_ADVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_CONVECTION_SCHEMES = ("ccd", "fccd_nodal", "fccd_flux", "uccd6")
_CONVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_REINIT_METHODS = (
    "split", "unified", "dgr", "hybrid",
    "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
)
_PROJECTION_MODES = (
    "legacy", "variable_density", "iim", "gfm", "consistent_iim", "consistent_gfm",
)
_PROJECTION_MODE_ALIASES = {
    "standard": "legacy",
    "variable_density_only": "variable_density",
    "pressure_jump": "consistent_gfm",
}
_PROJECTION_TO_REPROJECT_MODE = {
    "legacy": "legacy",
    "variable_density": "variable_density_only",
    "iim": "iim",
    "gfm": "gfm",
    "consistent_iim": "consistent_iim",
    "consistent_gfm": "consistent_gfm",
}
_PPE_DISCRETIZATION_SOLVERS = {
    ("fvm", "iterative"): "fvm_iterative",
    ("fvm", "direct"): "fvm_direct",
    ("fccd", "iterative"): "fccd_iterative",
}
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
_MOMENTUM_PREDICTORS = ("projection_predictor_corrector",)
_CONVECTION_TIME_SCHEMES = ("ab2", "forward_euler")
_MOMENTUM_FORMS = ("primitive_velocity",)
_VISCOUS_SPATIAL_SCHEMES = ("conservative_stress", "ccd_bulk", "ccd_stress_legacy")
_VISCOUS_SPATIAL_ALIASES = {
    "ccd": "ccd_bulk",
    "conservative": "conservative_stress",
}
_CURVATURE_SCHEMES = ("psi_direct_hfe",)
_MOMENTUM_PREDICTOR_ALIASES = {
    "predictor_corrector": "projection_predictor_corrector",
    "fractional_step": "projection_predictor_corrector",
}
_MOMENTUM_GRADIENT_SCHEMES = ("ccd", "fccd_flux", "fccd_nodal")
_MOMENTUM_GRADIENT_ALIASES = {
    "projection_consistent": "ccd",
    "fccd": "fccd_flux",
}
_PPE_SOLVER_KINDS = ("iterative", "direct", "defect_correction")
_PPE_ITERATION_METHODS = ("gmres",)
_PPE_PRECONDITIONERS = ("jacobi", "line_pcr", "none")


def parse_run(
    d: dict,
    interface: dict,
    numerics: dict,
    output: dict | None = None,
) -> RunCfg:
    """Parse the run section from experiment YAML."""
    output = output or {}
    time_cfg = d["time"]
    snapshots = output.get("snapshots", {}) or {}
    reinit = interface["reinitialization"]
    interface_geometry = interface.get("geometry", {}) or {}
    interface_curvature = interface_geometry.get("curvature", {}) or {}
    reinit_profile = reinit.get("profile", {}) or {}
    reinit_schedule = reinit["schedule"]
    layout = parse_numerics_layout(numerics)
    interface_transport = layout["interface_transport"]
    tracking = layout["tracking"]
    momentum = layout["momentum"]
    convection = layout["convection"]
    viscosity = layout["viscosity"]
    pressure_term = layout["pressure_term"]
    surface_tension = layout["surface_tension"]
    projection = layout["projection"]
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
    debug = d.get("debug", {}) or {}
    snap_raw = snapshots.get("times", [])
    if snap_raw is None:
        snap_raw = []
    cfl_raw = time_cfg.get("cfl")
    dt_fixed_raw = time_cfg.get("dt")
    if cfl_raw is not None and dt_fixed_raw is not None:
        raise ValueError("run.time: 'cfl' and 'dt' are mutually exclusive.")
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
    reproject_mode = parse_projection_mode(
        projection.get("mode", coefficient_to_projection_mode(poisson_coefficient)),
        layout["paths"]["projection_mode"],
    )
    reinit_method = reinit["algorithm"]
    if reinit_method is not None and reinit_method not in _REINIT_METHODS:
        raise ValueError(
            f"interface.reinitialization.algorithm must be one of {_REINIT_METHODS}, "
            f"got {reinit_method!r}"
        )
    ridge_sigma_0 = float(reinit_profile.get("ridge_sigma_0", 3.0))
    if ridge_sigma_0 <= 0.0:
        raise ValueError(
            "interface.reinitialization.profile.ridge_sigma_0 must be > 0, "
            f"got {ridge_sigma_0}"
        )
    return RunCfg(
        T_final=opt_float(time_cfg["final"]),
        max_steps=int(time_cfg["max_steps"]) if "max_steps" in time_cfg else None,
        cfl=float(cfl_raw if cfl_raw is not None else 0.15),
        snap_times=[float(x) for x in snap_raw],
        snap_interval=opt_float(snapshots.get("interval")),
        reinit_eps_scale=float(reinit_profile.get("eps_scale", 1.0)),
        print_every=int(time_cfg.get("print_every", 100)),
        dt_fixed=opt_float(dt_fixed_raw),
        cn_viscous=(viscous_time_scheme == "crank_nicolson"),
        reinit_every=int(reinit_schedule["every_steps"]),
        reproject_mode=reproject_mode,
        phi_primary_transport=parse_tracking_primary(
            tracking,
            layout["paths"]["tracking_primary"],
        ),
        interface_tracking_enabled=parse_tracking_enabled(tracking),
        interface_tracking_method=parse_tracking_method(
            tracking,
            layout["paths"]["tracking_primary"],
        ),
        phi_primary_redist_every=parse_tracking_redistance_every(
            tracking,
            layout["paths"]["tracking_redistance"],
        ),
        phi_primary_clip_factor=float(tracking_redistance(tracking).get("clip_factor", 12.0)),
        phi_primary_heaviside_eps_scale=float(
            tracking_redistance(tracking).get("heaviside_eps_scale", 1.0)
        ),
        kappa_max=opt_float(interface_curvature.get("cap", surface_tension.get("curvature_cap"))),
        reinit_method=reinit_method,
        dgr_phi_smooth_C=float(reinit_profile.get("dgr_phi_smooth_C", 1e-4)),
        ridge_sigma_0=ridge_sigma_0,
        advection_scheme=advection_scheme,
        convection_scheme=convection_scheme,
        ppe_solver=ppe_solver,
        pressure_scheme=pressure_scheme,
        ppe_coefficient_scheme=poisson_coefficient,
        ppe_interface_coupling_scheme=poisson_interface_coupling,
        surface_tension_scheme=surface_tension_scheme,
        convection_time_scheme=convection_time_scheme,
        viscous_spatial_scheme=viscous_spatial_scheme,
        viscous_time_scheme=viscous_time_scheme,
        pressure_gradient_scheme=pressure_gradient_scheme,
        surface_tension_gradient_scheme=surface_tension_gradient_scheme,
        momentum_gradient_scheme=momentum_gradient_scheme,
        uccd6_sigma=uccd6_sigma,
        face_flux_projection=bool(projection.get("face_flux_projection", False)),
        ppe_iteration_method=ppe_iteration_method,
        ppe_tolerance=ppe_tolerance,
        ppe_max_iterations=ppe_max_iterations,
        ppe_restart=ppe_restart,
        ppe_preconditioner=ppe_preconditioner,
        ppe_pcr_stages=ppe_pcr_stages,
        ppe_c_tau=ppe_c_tau,
        ppe_defect_correction=ppe_defect_correction,
        ppe_dc_max_iterations=ppe_dc_max_iterations,
        ppe_dc_tolerance=ppe_dc_tolerance,
        ppe_dc_relaxation=ppe_dc_relaxation,
        debug_diagnostics=bool(debug.get("step_diagnostics", False)),
    )


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
            surface_tension = {"model": "csf"}
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


def parse_ppe_solver_config(
    solver_cfg: dict,
    path: str,
    discretization: str = "fvm",
    discretization_path: str = "projection.poisson.operator.discretization",
) -> tuple[str, str, float, int, int | None, str, int | None, float, bool, int, float, float]:
    kind = validate_choice(solver_cfg["kind"], _PPE_SOLVER_KINDS, f"{path}.kind")
    if kind != "defect_correction" and "base_solver" in solver_cfg:
        raise ValueError(
            f"{path}.base_solver is only valid when {path}.kind='defect_correction'"
        )
    dc_enabled = kind == "defect_correction"
    dc_max_iterations = 0
    dc_tolerance = 0.0
    dc_relaxation = 1.0
    effective_solver_cfg = solver_cfg
    effective_kind = kind
    effective_path = path
    if dc_enabled:
        allowed_dc_keys = {"kind", "corrections", "base_solver"}
        extra_keys = sorted(set(solver_cfg) - allowed_dc_keys)
        if extra_keys:
            raise ValueError(
                f"{path}.kind='defect_correction' does not accept base-solver "
                f"options at the DC level: {extra_keys}"
            )
        if "base_solver" not in solver_cfg:
            raise ValueError(f"{path}.kind='defect_correction' requires {path}.base_solver")
        effective_solver_cfg = solver_cfg["base_solver"]
        effective_kind = validate_choice(
            effective_solver_cfg["kind"],
            ("iterative", "direct"),
            f"{path}.base_solver.kind",
        )
        if "base_solver" in effective_solver_cfg:
            raise ValueError(f"{path}.base_solver.base_solver is not allowed")
        effective_path = f"{path}.base_solver"
        corrections = solver_cfg.get("corrections", {}) or {}
        dc_max_iterations = int(corrections.get("max_iterations", 3))
        dc_tolerance = float(corrections.get("tolerance", 1.0e-8))
        dc_relaxation = float(corrections.get("relaxation", 1.0))
        if dc_max_iterations <= 0:
            raise ValueError(f"{path}.corrections.max_iterations must be > 0")
        if dc_tolerance <= 0.0:
            raise ValueError(f"{path}.corrections.tolerance must be > 0")
        if dc_relaxation <= 0.0:
            raise ValueError(f"{path}.corrections.relaxation must be > 0")
    solver_key = (discretization, effective_kind)
    if solver_key not in _PPE_DISCRETIZATION_SOLVERS:
        raise ValueError(
            f"{discretization_path}={discretization!r} does not support "
            f"{effective_path}.kind={effective_kind!r}"
        )
    ppe_solver = _PPE_DISCRETIZATION_SOLVERS[solver_key]
    if discretization == "fccd" and effective_kind == "iterative":
        effective_solver_cfg = dict(effective_solver_cfg)
        effective_solver_cfg.setdefault("preconditioner", "none")
    (
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
    ) = parse_ppe_solver_options(effective_kind, effective_solver_cfg, effective_path)
    if discretization == "fccd" and ppe_preconditioner not in {"jacobi", "none"}:
        raise ValueError(
            f"{effective_path}.preconditioner for FCCD PPE must be 'jacobi' or 'none', "
            f"got {ppe_preconditioner!r}"
        )
    return (
        ppe_solver,
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
        dc_enabled,
        dc_max_iterations,
        dc_tolerance,
        dc_relaxation,
    )


def parse_ppe_solver_options(
    kind: str,
    solver_cfg: dict,
    path: str,
) -> tuple[str, float, int, int | None, str, int | None, float]:
    iterative_keys = {
        "method", "tolerance", "max_iterations", "restart",
        "preconditioner", "pcr_stages", "c_tau",
    }
    if kind == "direct":
        present = sorted(iterative_keys.intersection(solver_cfg))
        if present:
            raise ValueError(
                f"{path}.kind='direct' does not accept iterative options: {present}"
            )
        return "none", 0.0, 0, None, "none", None, 0.0
    ppe_iteration_method = validate_choice(
        solver_cfg.get("method", "gmres"),
        _PPE_ITERATION_METHODS,
        f"{path}.method",
    )
    ppe_preconditioner = validate_choice(
        solver_cfg.get("preconditioner", "line_pcr"),
        _PPE_PRECONDITIONERS,
        f"{path}.preconditioner",
    )
    ppe_tolerance = float(solver_cfg.get("tolerance", 1.0e-8))
    if ppe_tolerance <= 0.0:
        raise ValueError(f"{path}.tolerance must be > 0")
    ppe_max_iterations = int(solver_cfg.get("max_iterations", 500))
    if ppe_max_iterations <= 0:
        raise ValueError(f"{path}.max_iterations must be > 0")
    ppe_restart = int(solver_cfg["restart"]) if "restart" in solver_cfg else None
    if ppe_restart is not None and ppe_restart <= 0:
        raise ValueError(f"{path}.restart must be > 0")
    if ppe_preconditioner != "line_pcr":
        for key in ("pcr_stages", "c_tau"):
            if key in solver_cfg:
                raise ValueError(
                    f"{path}.{key} is only valid when preconditioner='line_pcr', "
                    f"got preconditioner={ppe_preconditioner!r}"
                )
    ppe_pcr_stages = int(solver_cfg["pcr_stages"]) if "pcr_stages" in solver_cfg else None
    if ppe_pcr_stages is not None and ppe_pcr_stages <= 0:
        raise ValueError(f"{path}.pcr_stages must be > 0")
    ppe_c_tau = float(solver_cfg.get("c_tau", 2.0))
    if ppe_c_tau <= 0.0:
        raise ValueError(f"{path}.c_tau must be > 0")
    return (
        ppe_iteration_method,
        ppe_tolerance,
        ppe_max_iterations,
        ppe_restart,
        ppe_preconditioner,
        ppe_pcr_stages,
        ppe_c_tau,
    )


def parse_enabled(raw: Any) -> bool:
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"true", "yes", "on", "1", "enabled"}:
            return True
        if value in {"false", "no", "off", "0", "disabled"}:
            return False
    return bool(raw)


def parse_tracking_method(
    tracking: dict,
    path: str = "numerics.interface.tracking.primary",
) -> str:
    if not parse_tracking_enabled(tracking):
        return "none"
    primary = str(tracking["primary"]).strip().lower()
    if primary == "phi":
        return "phi_primary"
    if primary == "psi":
        return "psi_direct"
    if primary == "none":
        return "none"
    raise ValueError(f"{path} must be phi|psi|none, got {primary!r}")


def parse_tracking_enabled(tracking: dict) -> bool:
    if "enabled" in tracking:
        return parse_enabled(tracking.get("enabled"))
    return str(tracking["primary"]).strip().lower() != "none"


def parse_tracking_primary(
    tracking: dict,
    path: str = "numerics.interface.tracking.primary",
) -> bool:
    return parse_tracking_method(tracking, path) == "phi_primary"


def tracking_redistance(tracking: dict) -> dict:
    return tracking.get("redistance", {}) or {}


def parse_tracking_redistance_every(
    tracking: dict,
    path: str = "numerics.interface.tracking.redistance.schedule.every_steps",
) -> int:
    schedule = (tracking_redistance(tracking).get("schedule", {}) or {})
    every = int(schedule.get("every_steps", 4))
    if every <= 0:
        raise ValueError(f"{path} must be > 0")
    return every


def normalize_momentum_predictor(raw: str) -> str:
    key = str(raw).strip().lower()
    return _MOMENTUM_PREDICTOR_ALIASES.get(key, key)


def parse_projection_mode(raw: Any, path: str = "numerics.projection.mode") -> str:
    mode = str(raw).strip().lower()
    mode = _PROJECTION_MODE_ALIASES.get(mode, mode)
    if mode not in _PROJECTION_MODES:
        raise ValueError(f"{path} must be one of {_PROJECTION_MODES}, got {raw!r}")
    return _PROJECTION_TO_REPROJECT_MODE[mode]


def coefficient_to_projection_mode(coefficient: str) -> str:
    if coefficient == "phase_density":
        return "variable_density"
    if coefficient == "phase_separated":
        return "gfm"
    raise ValueError(f"Unsupported PPE coefficient model: {coefficient!r}")
