"""Experiment configuration I/O for §13 benchmarks.

``ExperimentConfig`` is the single source of truth for a config-driven
simulation run.  It is loaded from YAML via :func:`load_experiment_config`.

YAML top-level sections
-----------------------
grid            GridCfg      — grid geometry and resolution
physics         PhysicsCfg   — fluid properties (direct or derived)
run             RunCfg       — time integration parameters
output          OutputCfg    — save paths and figure specs
diagnostics     list[str]    — metrics to collect (see DiagnosticCollector)
initial_condition  dict      — forwarded to InitialConditionBuilder
initial_velocity   dict|null — forwarded to velocity_field_from_dict
boundary_condition dict|null — BC type and parameters

Derived physics
---------------
If the physics section includes non-dimensional parameters, they are
resolved before constructing PhysicsCfg:

    Re         → mu    = rho_l * sqrt(g_acc * d_ref) * d_ref / Re
    Eo         → sigma = g_acc * (rho_l - rho_g) * d_ref**2 / Eo
    Ca         → sigma = mu_g * gamma_dot * R_ref / Ca
    lambda_mu  → mu_l  = lambda_mu * mu_g
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any


# ── sub-config classes ───────────────────────────────────────────────────────

@dataclass
class GridCfg:
    NX: int = 64
    NY: int = 64
    LX: float = 1.0
    LY: float = 1.0
    bc_type: str = "wall"   # "wall" or "periodic"
    alpha_grid: float = 1.0       # interface-fitted concentration (1.0 = uniform)
    eps_factor: float = 1.5       # interface thickness ε = eps_factor × h
    eps_g_factor: float = 2.0     # grid density Gaussian width factor
    eps_g_cells: float | None = None  # ξ-space grid density width (cells); overrides eps_g_factor
    dx_min_floor: float = 1e-6    # minimum cell width floor
    use_local_eps: bool = False   # ε(x) = C_ε · h_local(x) for curvature/reconstruction
    eps_xi_cells: float | None = None  # ξ-space Heaviside eps width (cells); implies use_local_eps
    grid_rebuild_freq: int = 1    # 0 = IC-fitted static, K > 0 = rebuild every K steps
    interface_fitting_enabled: bool = True
    interface_fitting_method: str = "gaussian_levelset"


@dataclass
class PhysicsCfg:
    rho_l: float = 1.0
    rho_g: float = 1.0
    sigma: float = 0.0
    mu: float = 0.01            # uniform viscosity (fallback)
    mu_l: float | None = None   # liquid viscosity for variable-μ
    mu_g: float | None = None   # gas   viscosity for variable-μ
    g_acc: float = 0.0
    rho_ref: float | None = None
    # Derived-parameter cache (for override + re-resolution)
    _lambda_mu: float | None = None  # mu_l / mu_g  (stored for override)

    def with_lambda_mu(self, lambda_mu: float) -> "PhysicsCfg":
        """Return a copy with mu_l = lambda_mu * mu_g applied."""
        import copy
        obj = copy.copy(self)
        if obj.mu_g is not None:
            object.__setattr__(obj, "mu_l", lambda_mu * obj.mu_g)
        object.__setattr__(obj, "_lambda_mu", lambda_mu)
        return obj


@dataclass
class RunCfg:
    T_final: float | None = None
    max_steps: int | None = None        # None = no step cap; set explicitly as safety brake only
    cfl: float = 0.15
    snap_times: list = field(default_factory=list)
    snap_interval: float | None = None  # auto-generate output snapshots every N time units
    reinit_eps_scale: float = 1.0
    print_every: int = 100
    dt_fixed: float | None = None
    cn_viscous: bool = False
    reinit_every: int = 2
    reproject_mode: str = "legacy"
    phi_primary_transport: bool = False
    interface_tracking_enabled: bool = True
    interface_tracking_method: str = "psi_direct"
    phi_primary_redist_every: int = 4
    phi_primary_clip_factor: float = 12.0
    phi_primary_heaviside_eps_scale: float = 1.0
    kappa_max: float | None = None  # curvature cap (None = unlimited)
    reinit_method: str | None = None  # None → auto (DGR); 'split'/'dgr'/'hybrid'/'ridge_eikonal'
    dgr_phi_smooth_C: float = 1e-4   # CCD Laplacian smoothing on φ_sdf in DGR reinit
    ridge_sigma_0: float = 3.0       # Gaussian-ξ ridge bandwidth (CHK-159, SP-E D1)
    # Stage-wise numerical schemes — bridged from SimulationBuilder (CHK-158)
    # and WIKI-X-023 per-term NS decomposition.
    # advection_scheme : ψ advection — 'dissipative_ccd' | 'weno5' | 'fccd'
    # convection_scheme: momentum    — 'ccd' | 'fccd' | 'uccd6'
    # ppe_solver       : pressure    — 'fvm_iterative' | 'fvm_direct' | 'fccd_iterative'
    # surface_tension_scheme: σκ∇ψ or [p]=σκ — 'csf' | 'pressure_jump' | 'none'
    # viscous_spatial_scheme: viscous — 'ccd' | 'conservative_stress' | 'ccd_stress_legacy'
    # viscous_time_scheme: viscous predictor — 'explicit' | 'crank_nicolson'
    advection_scheme: str = "dissipative_ccd"
    convection_scheme: str = "ccd"
    ppe_solver: str = "fvm_iterative"
    pressure_scheme: str = "fvm_matrixfree"  # internal backend key derived from ppe_solver
    ppe_coefficient_scheme: str = "phase_density"
    surface_tension_scheme: str = "csf"
    convection_time_scheme: str = "ab2"
    viscous_spatial_scheme: str = "ccd_bulk"
    viscous_time_scheme: str = "explicit"
    pressure_gradient_scheme: str = "ccd"
    surface_tension_gradient_scheme: str = "ccd"
    momentum_gradient_scheme: str = "ccd"
    uccd6_sigma: float = 1.0e-3   # hyperviscosity coefficient for convection_scheme='uccd6'
    face_flux_projection: bool = False  # experimental CHK-172 PoC; default off
    ppe_iteration_method: str = "gmres"
    ppe_tolerance: float = 1.0e-8
    ppe_max_iterations: int = 500
    ppe_restart: int | None = 80
    ppe_preconditioner: str = "line_pcr"
    ppe_pcr_stages: int | None = 4
    ppe_c_tau: float = 2.0
    ppe_defect_correction: bool = False
    ppe_dc_max_iterations: int = 0
    ppe_dc_tolerance: float = 0.0
    ppe_dc_relaxation: float = 1.0
    debug_diagnostics: bool = False  # record bf_residual_max/div_u_max/kappa_max/ppe_rhs_max per step


@dataclass
class OutputCfg:
    dir: str = "results"
    save_npz: bool = True
    figures: list = field(default_factory=list)


# ── master config ────────────────────────────────────────────────────────────

@dataclass
class ExperimentConfig:
    """Complete experiment configuration.

    Parameters
    ----------
    grid : GridCfg
    physics : PhysicsCfg
    run : RunCfg
    output : OutputCfg
    diagnostics : list of str
    initial_condition : dict   forwarded to InitialConditionBuilder
    initial_velocity : dict or None
    boundary_condition : dict or None
    """

    grid: GridCfg = field(default_factory=GridCfg)
    physics: PhysicsCfg = field(default_factory=PhysicsCfg)
    run: RunCfg = field(default_factory=RunCfg)
    output: OutputCfg = field(default_factory=OutputCfg)
    diagnostics: list = field(default_factory=list)
    initial_condition: dict = field(default_factory=dict)
    initial_velocity: dict | None = None
    boundary_condition: dict | None = None
    sweep: list | None = None  # list of {label, overrides} dicts

    # ── override support ─────────────────────────────────────────────────

    def override(self, **kwargs) -> "ExperimentConfig":
        """Return a shallow copy with top-level or nested fields replaced.

        Supports dot-notation for one level of nesting::

            cfg2 = cfg.override(**{"physics.rho_l": 500.0, "run.T_final": 5.0})

        Special case: ``physics.lambda_mu`` triggers mu_l = lambda_mu × mu_g.
        """
        obj = copy.copy(self)
        for key, val in kwargs.items():
            if key == "physics.lambda_mu":
                new_ph = obj.physics.with_lambda_mu(float(val))
                object.__setattr__(obj, "physics", new_ph)
            elif "." in key:
                section, attr = key.split(".", 1)
                sub = copy.copy(getattr(obj, section))
                object.__setattr__(sub, attr, val)
                object.__setattr__(obj, section, sub)
            else:
                object.__setattr__(obj, key, val)
        return obj

    # ── class-method loader ──────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ExperimentConfig":
        """Load from a YAML file."""
        yaml = _require_pyyaml()
        with open(path) as fh:
            raw = yaml.safe_load(fh) or {}
        return _parse_raw(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "ExperimentConfig":
        """Construct from a plain dict (already loaded from YAML)."""
        return _parse_raw(raw)


# ── convenience loader ───────────────────────────────────────────────────────

def load_experiment_config(path: str | Path) -> ExperimentConfig:
    """Load :class:`ExperimentConfig` from a YAML file."""
    return ExperimentConfig.from_yaml(path)


def _require_pyyaml() -> Any:
    """Import PyYAML only when YAML loading is requested."""
    try:
        import yaml
        return yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required to load experiment YAML files. "
            "Install it with `pip install pyyaml` or `pip install twophase[io]`."
        )


# ── parsing helpers ──────────────────────────────────────────────────────────

def _parse_raw(raw: dict) -> ExperimentConfig:
    interface = raw["interface"]
    numerics = raw["numerics"]
    grid = _parse_grid(raw["grid"], interface)
    physics = _parse_physics(raw["physics"])
    output = _parse_output(raw.get("output", {}))
    run = _parse_run(raw["run"], interface, numerics, raw.get("output", {}))
    return ExperimentConfig(
        grid=grid,
        physics=physics,
        run=run,
        output=output,
        diagnostics=list(raw.get("diagnostics", [])),
        initial_condition=dict(raw.get("initial_condition", {})),
        initial_velocity=raw.get("initial_velocity") or None,
        boundary_condition=raw.get("boundary_condition") or None,
        sweep=raw.get("sweep") or None,
    )


def _parse_grid(d: dict, interface: dict) -> GridCfg:
    cells = d["cells"]
    NX, NY = int(cells[0]), int(cells[1])
    domain = d["domain"]
    size = domain["size"]
    LX, LY = float(size[0]), float(size[1])
    distribution = d["distribution"]
    width = interface["thickness"]
    distribution_type = _validate_choice(
        distribution["type"], ("uniform", "interface_fitted"),
        "grid.distribution.type",
    )
    fitting_enabled = distribution_type == "interface_fitted"
    fitting_method = _normalize_interface_fitting_method(
        distribution.get("method", "gaussian_levelset" if fitting_enabled else "none")
    )
    if fitting_method == "none":
        fitting_enabled = False
    alpha_grid = float(distribution.get("alpha", 1.0))
    if not fitting_enabled:
        alpha_grid = 1.0
    eps_factor = float(width.get("base_factor", 1.5))
    eps_g_factor = float(distribution.get("eps_g_factor", 2.0))
    eps_g_cells = _opt_float(distribution.get("eps_g_cells"))
    eps_xi_cells = _opt_float(width.get("xi_cells"))
    use_local_eps = _parse_interface_width_mode(width, eps_xi_cells)
    return GridCfg(
        NX=NX,
        NY=NY,
        LX=LX,
        LY=LY,
        bc_type=str(domain["boundary"]),
        alpha_grid=alpha_grid,
        eps_factor=eps_factor,
        eps_g_factor=eps_g_factor,
        eps_g_cells=eps_g_cells,
        dx_min_floor=float(d.get("dx_min_floor", 1e-6)),
        use_local_eps=use_local_eps,
        eps_xi_cells=eps_xi_cells,
        grid_rebuild_freq=_parse_grid_rebuild(distribution.get("schedule", "static")),
        interface_fitting_enabled=fitting_enabled,
        interface_fitting_method=("none" if not fitting_enabled else fitting_method),
    )


def _parse_physics(d: dict) -> PhysicsCfg:
    """Parse physics section, resolving derived parameters."""
    phases = d["phases"]
    liquid = phases["liquid"]
    gas = phases["gas"]
    rho_l = float(liquid["rho"])
    rho_g = float(gas["rho"])
    g_acc = float(d.get("gravity", 0.0))
    rho_ref = _opt_float(d.get("rho_ref"))
    d_ref = _opt_float(d.get("d_ref"))

    mu_raw, mu_l_raw, mu_g_raw = _resolve_viscosity(d, rho_l, g_acc, d_ref)
    sigma_raw = _resolve_surface_tension(d, rho_l, rho_g, g_acc, d_ref, mu_g_raw)

    return PhysicsCfg(
        rho_l=rho_l,
        rho_g=rho_g,
        sigma=sigma_raw,
        mu=mu_raw,
        mu_l=mu_l_raw,
        mu_g=mu_g_raw,
        g_acc=g_acc,
        rho_ref=rho_ref,
    )


def _resolve_viscosity(
    d: dict,
    rho_l: float,
    g_acc: float,
    d_ref: float | None,
) -> tuple[float, float | None, float | None]:
    """Resolve uniform and phase viscosities from direct or derived inputs."""
    phases = d["phases"]
    liquid = phases["liquid"]
    gas = phases["gas"]
    mu_g = _opt_float(gas["mu"])
    mu_l = _opt_float(liquid["mu"])
    mu = _opt_float(d.get("mu"))

    lambda_mu = _opt_float(d.get("lambda_mu"))
    if lambda_mu is not None and mu_g is not None:
        mu_l = lambda_mu * mu_g

    re_num = _opt_float(d.get("Re"))
    if re_num is not None and d_ref is not None and g_acc > 0.0:
        mu_derived = rho_l * math.sqrt(g_acc * d_ref) * d_ref / re_num
        if mu is None:
            mu = mu_derived
        if mu_g is None:
            mu_g = mu_derived
        if mu_l is None:
            mu_l = mu_derived

    if mu is None:
        if mu_g is not None:
            mu = mu_g
        elif mu_l is not None:
            mu = mu_l
        else:
            mu = 0.01

    if mu_g is None and mu_l is None:
        return mu, mu, mu
    if mu_g is None:
        mu_g = mu
    if mu_l is None:
        mu_l = mu
    return mu, mu_l, mu_g


def _resolve_surface_tension(
    d: dict,
    rho_l: float,
    rho_g: float,
    g_acc: float,
    d_ref: float | None,
    mu_g: float | None,
) -> float:
    """Resolve surface tension from direct sigma, Eotvos number, or Ca."""
    sigma = _opt_float(d.get("surface_tension"))

    eo_num = _opt_float(d.get("Eo"))
    if eo_num is not None and d_ref is not None and g_acc > 0.0:
        sigma = g_acc * (rho_l - rho_g) * d_ref ** 2 / eo_num

    ca_num = _opt_float(d.get("Ca"))
    r_ref = _opt_float(d.get("R_ref")) or (d_ref / 2.0 if d_ref else None)
    gamma_dot = _opt_float(d.get("gamma_dot"))
    if (
        ca_num is not None
        and mu_g is not None
        and gamma_dot is not None
        and r_ref is not None
    ):
        sigma = mu_g * gamma_dot * r_ref / ca_num

    return 0.0 if sigma is None else sigma


_ADVECTION_SCHEMES = ("dissipative_ccd", "weno5", "fccd_nodal", "fccd_flux")
_ADVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_CONVECTION_SCHEMES = ("ccd", "fccd_nodal", "fccd_flux", "uccd6")
_CONVECTION_SCHEME_ALIASES = {"fccd": "fccd_flux"}
_REINIT_METHODS = (
    "split", "unified", "dgr", "hybrid",
    "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
)
_PROJECTION_MODES = (
    "standard", "variable_density", "iim", "gfm",
)
_PROJECTION_MODE_ALIASES = {
    "consistent_iim": "iim",
    "consistent_gfm": "gfm",
}
_PROJECTION_TO_REPROJECT_MODE = {
    "standard": "legacy",
    "variable_density": "variable_density_only",
    "iim": "iim",
    "gfm": "gfm",
}
_PPE_SCHEMES = ("fvm_iterative", "fvm_direct", "fccd_iterative")
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
    "variable_density": "phase_density",
    "phase_separated_density": "phase_separated",
    "split_phase": "phase_separated",
}
_SURFACE_TENSION_SCHEMES = ("csf", "pressure_jump", "none")
_SURFACE_TENSION_ALIASES = {
    "gfm_jump": "pressure_jump",
    "ppe_jump": "pressure_jump",
}
_VISCOUS_TIME_SCHEMES = ("forward_euler", "crank_nicolson")
_INTERFACE_TIME_SCHEMES = ("tvd_rk3",)
_MOMENTUM_PREDICTORS = ("projection_predictor_corrector",)
_CONVECTION_TIME_SCHEMES = ("ab2", "forward_euler")
_MOMENTUM_FORMS = ("primitive_velocity",)
_VISCOUS_SPATIAL_SCHEMES = ("conservative_stress", "ccd_bulk", "ccd_stress_legacy")
_VISCOUS_SPATIAL_ALIASES = {
    "stress_divergence": "conservative_stress",
    "low_order_conservative": "conservative_stress",
    "ccd": "ccd_bulk",
    "ccd_legacy": "ccd_stress_legacy",
}
_CURVATURE_SCHEMES = ("psi_direct_hfe",)
_MOMENTUM_PREDICTOR_ALIASES = {
    "fractional_step": "projection_predictor_corrector",
    "pressure_correction": "projection_predictor_corrector",
}
_MOMENTUM_GRADIENT_SCHEMES = ("ccd", "fccd_flux", "fccd_nodal")
_MOMENTUM_GRADIENT_ALIASES = {
    "projection_consistent": "ccd",
    "fccd": "fccd_flux",
}
_PPE_SOLVER_KINDS = ("iterative", "direct", "defect_correction")
_PPE_ITERATION_METHODS = ("gmres",)
_PPE_PRECONDITIONERS = ("jacobi", "line_pcr", "none")


def _parse_run(
    d: dict,
    interface: dict,
    numerics: dict,
    output: dict | None = None,
) -> RunCfg:
    output = output or {}
    time_cfg = d["time"]
    snapshots = output.get("snapshots", {}) or {}
    reinit = interface["reinitialization"]
    interface_geometry = interface.get("geometry", {}) or {}
    interface_curvature = interface_geometry.get("curvature", {}) or {}
    reinit_profile = reinit.get("profile", {}) or {}
    reinit_schedule = reinit["schedule"]
    layout = _parse_numerics_layout(numerics)
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
    if not poisson_operator and (
        "discretization" in poisson or "coefficient" in poisson
    ):
        poisson_operator = {
            key: poisson[key]
            for key in ("discretization", "coefficient")
            if key in poisson
        }
    poisson_discretization = _validate_choice(
        poisson_operator.get("discretization", "fvm"),
        _PPE_DISCRETIZATIONS,
        layout["paths"]["poisson_discretization"],
    )
    if "coefficient" not in poisson_operator:
        raise ValueError(
            f"{layout['paths']['poisson_coefficient']} is required; "
            "use 'phase_separated' for SP-M or 'phase_density' for mixture-density PPE."
        )
    poisson_coefficient = _validate_choice(
        _POISSON_COEFFICIENT_ALIASES.get(
            str(poisson_operator["coefficient"]).strip().lower(),
            poisson_operator["coefficient"],
        ),
        _POISSON_COEFFICIENTS,
        layout["paths"]["poisson_coefficient"],
    )
    ppe_solver_cfg = poisson["solver"]
    debug = d.get("debug", {}) or {}

    snap_raw = snapshots.get("times", [])
    if snap_raw is None:
        snap_raw = []
    cfl_raw = time_cfg.get("cfl")
    dt_fixed_raw = time_cfg.get("dt")
    if cfl_raw is not None and dt_fixed_raw is not None:
        raise ValueError(
            "run.time: 'cfl' and 'dt' are mutually exclusive."
        )
    advection_scheme = _validate_choice(
        _ADVECTION_SCHEME_ALIASES.get(
            str(interface_transport["spatial"]).strip().lower(),
            interface_transport["spatial"],
        ),
        _ADVECTION_SCHEMES,
        layout["paths"]["interface_spatial"],
    )
    _parse_time_integrator(
        interface_transport, _INTERFACE_TIME_SCHEMES,
        layout["paths"]["interface_time"],
        default="tvd_rk3",
        aliases={"explicit": "tvd_rk3", "rk3": "tvd_rk3"},
    )
    _validate_choice(
        momentum.get("form", "primitive_velocity"), _MOMENTUM_FORMS,
        layout["paths"]["momentum_form"],
    )
    convection_scheme = _validate_choice(
        _CONVECTION_SCHEME_ALIASES.get(
            str(convection["spatial"]).strip().lower(),
            convection["spatial"],
        ),
        _CONVECTION_SCHEMES,
        layout["paths"]["convection_spatial"],
    )
    convection_time_scheme = _parse_time_integrator(
        convection, _CONVECTION_TIME_SCHEMES,
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
    ) = _parse_ppe_solver_config(
        ppe_solver_cfg,
        layout["paths"]["poisson_solver"],
        poisson_discretization,
        layout["paths"]["poisson_discretization"],
    )
    pressure_scheme = _PPE_TO_PRESSURE_SCHEME[ppe_solver]
    _raw_p_grad = pressure_term.get("gradient", pressure_term.get("spatial", "ccd"))
    pressure_gradient_scheme = _validate_choice(
        _MOMENTUM_GRADIENT_ALIASES.get(
            str(_raw_p_grad).strip().lower(),
            _raw_p_grad,
        ),
        _MOMENTUM_GRADIENT_SCHEMES,
        layout["paths"]["pressure_spatial"],
    )
    _raw_st_grad = surface_tension.get(
        "gradient",
        surface_tension.get("spatial", surface_tension.get("force_gradient", "ccd")),
    )
    surface_tension_gradient_scheme = _validate_choice(
        _MOMENTUM_GRADIENT_ALIASES.get(
            str(_raw_st_grad).strip().lower(),
            _raw_st_grad,
        ),
        _MOMENTUM_GRADIENT_SCHEMES,
        layout["paths"]["surface_tension_spatial"],
    )
    momentum_gradient_scheme = pressure_gradient_scheme
    surface_tension_scheme = _validate_choice(
        _SURFACE_TENSION_ALIASES.get(
            str(surface_tension.get("formulation", surface_tension.get("model", "csf"))).strip().lower(),
            surface_tension.get("formulation", surface_tension.get("model", "csf")),
        ),
        _SURFACE_TENSION_SCHEMES,
        layout["paths"]["surface_tension_model"],
    )
    _validate_choice(
        interface_curvature.get("method", surface_tension.get("curvature", "psi_direct_hfe")),
        _CURVATURE_SCHEMES,
        layout["paths"]["surface_tension_curvature"],
    )
    uccd6_sigma = float(convection.get("uccd6_sigma", 1.0e-3))
    if uccd6_sigma <= 0.0:
        raise ValueError(
            f"{layout['paths']['convection_uccd6_sigma']} must be > 0, "
            f"got {uccd6_sigma}"
        )
    viscous_spatial_scheme = _validate_choice(
        _VISCOUS_SPATIAL_ALIASES.get(
            str(viscosity["spatial"]).strip().lower(),
            viscosity["spatial"],
        ),
        _VISCOUS_SPATIAL_SCHEMES,
        layout["paths"]["viscosity_spatial"],
    )
    viscous_time_scheme = _parse_time_integrator(
        viscosity, _VISCOUS_TIME_SCHEMES,
        layout["paths"]["viscosity_time"],
    )
    reproject_mode = _parse_projection_mode(
        projection.get("mode", _coefficient_to_projection_mode(poisson_coefficient)),
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
            f"interface.reinitialization.profile.ridge_sigma_0 must be > 0, got {ridge_sigma_0}"
        )
    return RunCfg(
        T_final=_opt_float(time_cfg["final"]),
        max_steps=int(time_cfg["max_steps"]) if "max_steps" in time_cfg else None,
        cfl=float(cfl_raw if cfl_raw is not None else 0.15),
        snap_times=[float(x) for x in snap_raw],
        snap_interval=_opt_float(snapshots.get("interval")),
        reinit_eps_scale=float(reinit_profile.get("eps_scale", 1.0)),
        print_every=int(time_cfg.get("print_every", 100)),
        dt_fixed=_opt_float(dt_fixed_raw),
        cn_viscous=(viscous_time_scheme == "crank_nicolson"),
        reinit_every=int(reinit_schedule["every_steps"]),
        reproject_mode=reproject_mode,
        phi_primary_transport=_parse_tracking_primary(
            tracking, layout["paths"]["tracking_primary"]
        ),
        interface_tracking_enabled=_parse_tracking_enabled(tracking),
        interface_tracking_method=_parse_tracking_method(
            tracking, layout["paths"]["tracking_primary"]
        ),
        phi_primary_redist_every=_parse_tracking_redistance_every(
            tracking, layout["paths"]["tracking_redistance"]
        ),
        phi_primary_clip_factor=float(_tracking_redistance(tracking).get("clip_factor", 12.0)),
        phi_primary_heaviside_eps_scale=float(
            _tracking_redistance(tracking).get("heaviside_eps_scale", 1.0)
        ),
        kappa_max=_opt_float(
            interface_curvature.get("cap", surface_tension.get("curvature_cap"))
        ),
        reinit_method=reinit_method,
        dgr_phi_smooth_C=float(
            reinit_profile.get("dgr_phi_smooth_C", 1e-4)
        ),
        ridge_sigma_0=ridge_sigma_0,
        advection_scheme=advection_scheme,
        convection_scheme=convection_scheme,
        ppe_solver=ppe_solver,
        pressure_scheme=pressure_scheme,
        ppe_coefficient_scheme=poisson_coefficient,
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


def _parse_output(d: dict) -> OutputCfg:
    return OutputCfg(
        dir=str(d.get("dir", "results")),
        save_npz=bool(d.get("save_npz", True)),
        figures=list(d.get("figures", [])),
    )


def _opt_float(val: Any) -> float | None:
    if val is None:
        return None
    return float(val)


def _validate_choice(raw: Any, choices: tuple[str, ...], path: str) -> str:
    value = str(raw).strip().lower()
    if value not in choices:
        raise ValueError(f"{path} must be one of {choices}, got {value!r}")
    return value


def _parse_numerics_layout(numerics: dict) -> dict:
    """Return canonical numeric sub-sections from the ch13 YAML schema.

    The canonical schema is term-based:
    ``numerics.interface``, ``numerics.momentum``, and ``numerics.projection``.
    A legacy adapter is kept here so older checked-in YAML can fail with useful
    validation messages while the new configs remain the documented shape.
    """
    if "interface" in numerics and "momentum" in numerics and "projection" in numerics:
        interface_num = numerics["interface"]
        time_num = numerics.get("time", {}) or {}
        interface_transport = dict(interface_num["transport"])
        _validate_choice(
            _normalize_momentum_predictor(
                time_num.get("algorithm",
                time_num.get("momentum_predictor", "projection_predictor_corrector"))
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
                "spatial", "projection_consistent"
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
            "poisson_solver": "numerics.elliptic.pressure_projection.poisson.solver",
        },
    }


def _parse_time_integrator(
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
    return _validate_choice(alias_map.get(value, value), choices, path)


def _parse_ppe_solver_config(
    solver_cfg: dict,
    path: str,
    discretization: str = "fvm",
    discretization_path: str = "projection.poisson.operator.discretization",
) -> tuple[
    str, str, float, int, int | None, str, int | None, float, bool, int, float, float
]:
    kind = _validate_choice(solver_cfg["kind"], _PPE_SOLVER_KINDS, f"{path}.kind")
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
            raise ValueError(
                f"{path}.kind='defect_correction' requires {path}.base_solver"
            )
        effective_solver_cfg = solver_cfg["base_solver"]
        effective_kind = _validate_choice(
            effective_solver_cfg["kind"], ("iterative", "direct"),
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
    ) = _parse_ppe_solver_options(effective_kind, effective_solver_cfg, effective_path)
    if discretization == "fccd" and ppe_preconditioner not in {"jacobi", "none"}:
        raise ValueError(
            f"{effective_path}.preconditioner for FCCD PPE must be 'jacobi' or 'none', "
            f"got {ppe_preconditioner!r}"
        )
    return (
        ppe_solver, ppe_iteration_method, ppe_tolerance, ppe_max_iterations,
        ppe_restart, ppe_preconditioner, ppe_pcr_stages, ppe_c_tau,
        dc_enabled, dc_max_iterations, dc_tolerance, dc_relaxation,
    )


def _parse_ppe_solver_options(kind: str, solver_cfg: dict, path: str) -> tuple[
    str, float, int, int | None, str, int | None, float
]:
    """Parse direct-vs-iterative PPE solver options without mixing semantics."""
    iterative_keys = {
        "method", "tolerance", "max_iterations", "restart",
        "preconditioner", "pcr_stages", "c_tau",
    }
    if kind == "direct":
        present = sorted(iterative_keys.intersection(solver_cfg))
        if present:
            raise ValueError(
                f"{path}.kind='direct' "
                f"does not accept iterative options: {present}"
            )
        return "none", 0.0, 0, None, "none", None, 0.0

    ppe_iteration_method = _validate_choice(
        solver_cfg.get("method", "gmres"), _PPE_ITERATION_METHODS,
        f"{path}.method",
    )
    ppe_preconditioner = _validate_choice(
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
        for _k in ("pcr_stages", "c_tau"):
            if _k in solver_cfg:
                raise ValueError(
                    f"{path}.{_k} is only valid when preconditioner='line_pcr', "
                    f"got preconditioner={ppe_preconditioner!r}"
                )
    ppe_pcr_stages = (
        int(solver_cfg["pcr_stages"]) if "pcr_stages" in solver_cfg else None
    )
    if ppe_pcr_stages is not None and ppe_pcr_stages <= 0:
        raise ValueError(f"{path}.pcr_stages must be > 0")
    ppe_c_tau = float(solver_cfg.get("c_tau", 2.0))
    if ppe_c_tau <= 0.0:
        raise ValueError(f"{path}.c_tau must be > 0")
    return (
        ppe_iteration_method, ppe_tolerance, ppe_max_iterations, ppe_restart,
        ppe_preconditioner, ppe_pcr_stages, ppe_c_tau,
    )


def _parse_interface_width_mode(
    width: dict,
    eps_xi_cells: float | None,
) -> bool:
    """Resolve canonical interface-width mode to the internal local-eps boolean."""
    mode = width["mode"]
    mode = str(mode).strip().lower()
    if mode == "nominal":
        return False
    if mode == "local":
        return True
    if mode == "xi_cells":
        if eps_xi_cells is None:
            raise ValueError(
                "interface.thickness.mode='xi_cells' requires xi_cells"
            )
        return True
    raise ValueError(
        "interface.thickness.mode must be nominal|local|xi_cells, "
        f"got {mode!r}"
    )


def _parse_grid_rebuild(raw: Any) -> int:
    """Resolve interface-fitting rebuild schedule to the internal frequency."""
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"static", "initial", "initial_only", "never", "off"}:
            return 0
        if value in {"every_step", "dynamic", "each_step"}:
            return 1
        if value.startswith("every_"):
            return int(value.removeprefix("every_"))
    freq = int(raw)
    if freq < 0:
        raise ValueError(
            f"grid.distribution.schedule must be >= 0, got {freq}"
        )
    return freq


def _parse_enabled(raw: Any) -> bool:
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"true", "yes", "on", "1", "enabled"}:
            return True
        if value in {"false", "no", "off", "0", "disabled"}:
            return False
    return bool(raw)


def _normalize_interface_fitting_method(raw: Any) -> str:
    method = str(raw).strip().lower()
    if method not in {"gaussian_levelset", "none"}:
        raise ValueError(
            "grid.distribution.method must be gaussian_levelset|none, "
            f"got {method!r}"
        )
    return method


def _parse_tracking_method(
    tracking: dict,
    path: str = "numerics.interface.tracking.primary",
) -> str:
    """Resolve interface tracking primary field to internal transport mode."""
    if not _parse_tracking_enabled(tracking):
        return "none"
    primary = str(tracking["primary"]).strip().lower()
    if primary == "phi":
        return "phi_primary"
    if primary == "psi":
        return "psi_direct"
    if primary == "none":
        return "none"
    raise ValueError(
        f"{path} must be phi|psi|none, got {primary!r}"
    )


def _parse_tracking_enabled(tracking: dict) -> bool:
    if "enabled" in tracking:
        return _parse_enabled(tracking.get("enabled"))
    return str(tracking["primary"]).strip().lower() != "none"


def _parse_tracking_primary(
    tracking: dict,
    path: str = "numerics.interface.tracking.primary",
) -> bool:
    return _parse_tracking_method(tracking, path) == "phi_primary"


def _tracking_redistance(tracking: dict) -> dict:
    return tracking.get("redistance", {}) or {}


def _parse_tracking_redistance_every(
    tracking: dict,
    path: str = "numerics.interface.tracking.redistance.schedule.every_steps",
) -> int:
    schedule = (_tracking_redistance(tracking).get("schedule", {}) or {})
    every = int(schedule.get("every_steps", 4))
    if every <= 0:
        raise ValueError(
            f"{path} must be > 0"
        )
    return every


def _normalize_momentum_predictor(raw: str) -> str:
    """Resolve paper-term aliases for momentum_predictor to the internal key."""
    return _MOMENTUM_PREDICTOR_ALIASES.get(str(raw).strip().lower(), str(raw).strip().lower())


def _parse_projection_mode(raw: Any, path: str = "numerics.projection.mode") -> str:
    """Parse canonical YAML projection mode to the internal solver key."""
    mode = str(raw).strip().lower()
    mode = _PROJECTION_MODE_ALIASES.get(mode, mode)
    if mode not in _PROJECTION_MODES:
        raise ValueError(
            f"{path} must be one of {_PROJECTION_MODES}, got {raw!r}"
        )
    return _PROJECTION_TO_REPROJECT_MODE[mode]


def _coefficient_to_projection_mode(coefficient: str) -> str:
    """Derive the standard projection mode from the PPE coefficient model."""
    if coefficient == "phase_density":
        return "variable_density"
    if coefficient == "phase_separated":
        return "consistent_gfm"
    raise ValueError(f"Unsupported PPE coefficient model: {coefficient!r}")
