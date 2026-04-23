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
from dataclasses import dataclass, field
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
    ppe_interface_coupling_scheme: str = "none"
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
    from .config_sections import parse_grid

    return parse_grid(d, interface)


def _parse_physics(d: dict) -> PhysicsCfg:
    """Parse physics section, resolving derived parameters."""
    from .config_sections import parse_physics

    return parse_physics(d)


def _resolve_viscosity(
    d: dict,
    rho_l: float,
    g_acc: float,
    d_ref: float | None,
) -> tuple[float, float | None, float | None]:
    """Resolve uniform and phase viscosities from direct or derived inputs."""
    from .config_sections import resolve_viscosity

    return resolve_viscosity(d, rho_l, g_acc, d_ref)


def _resolve_surface_tension(
    d: dict,
    rho_l: float,
    rho_g: float,
    g_acc: float,
    d_ref: float | None,
    mu_g: float | None,
) -> float:
    """Resolve surface tension from direct sigma, Eotvos number, or Ca."""
    from .config_sections import resolve_surface_tension

    return resolve_surface_tension(d, rho_l, rho_g, g_acc, d_ref, mu_g)


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
_POISSON_INTERFACE_COUPLINGS = ("none", "jump_decomposition")
_POISSON_INTERFACE_COUPLING_ALIASES = {
    "pressure_jump": "jump_decomposition",
    "jump": "jump_decomposition",
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
    from .config_run_sections import parse_run

    return parse_run(d, interface, numerics, output)


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
    from .config_run_sections import parse_numerics_layout

    return parse_numerics_layout(numerics)


def _parse_time_integrator(
    cfg: dict,
    choices: tuple[str, ...],
    path: str,
    *,
    default: str = "forward_euler",
    aliases: dict[str, str] | None = None,
) -> str:
    from .config_run_sections import parse_time_integrator

    return parse_time_integrator(cfg, choices, path, default=default, aliases=aliases)


def _parse_ppe_solver_config(
    solver_cfg: dict,
    path: str,
    discretization: str = "fvm",
    discretization_path: str = "projection.poisson.operator.discretization",
) -> tuple[
    str, str, float, int, int | None, str, int | None, float, bool, int, float, float
]:
    from .config_run_sections import parse_ppe_solver_config

    return parse_ppe_solver_config(solver_cfg, path, discretization, discretization_path)


def _parse_ppe_solver_options(kind: str, solver_cfg: dict, path: str) -> tuple[
    str, float, int, int | None, str, int | None, float
]:
    from .config_run_sections import parse_ppe_solver_options

    return parse_ppe_solver_options(kind, solver_cfg, path)


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
    from .config_run_sections import parse_enabled

    return parse_enabled(raw)


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
    from .config_run_sections import parse_tracking_method

    return parse_tracking_method(tracking, path)


def _parse_tracking_enabled(tracking: dict) -> bool:
    from .config_run_sections import parse_tracking_enabled

    return parse_tracking_enabled(tracking)


def _parse_tracking_primary(
    tracking: dict,
    path: str = "numerics.interface.tracking.primary",
) -> bool:
    from .config_run_sections import parse_tracking_primary

    return parse_tracking_primary(tracking, path)


def _tracking_redistance(tracking: dict) -> dict:
    from .config_run_sections import tracking_redistance

    return tracking_redistance(tracking)


def _parse_tracking_redistance_every(
    tracking: dict,
    path: str = "numerics.interface.tracking.redistance.schedule.every_steps",
) -> int:
    from .config_run_sections import parse_tracking_redistance_every

    return parse_tracking_redistance_every(tracking, path)


def _normalize_momentum_predictor(raw: str) -> str:
    from .config_run_sections import normalize_momentum_predictor

    return normalize_momentum_predictor(raw)


def _parse_projection_mode(raw: Any, path: str = "numerics.projection.mode") -> str:
    from .config_run_sections import parse_projection_mode

    return parse_projection_mode(raw, path)


def _coefficient_to_projection_mode(coefficient: str) -> str:
    from .config_run_sections import coefficient_to_projection_mode

    return coefficient_to_projection_mode(coefficient)
