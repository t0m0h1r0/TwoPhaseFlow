"""Experiment config compatibility facade for §13 benchmarks.

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

from pathlib import Path
from typing import Any

from .config_models import ExperimentConfig, GridCfg, OutputCfg, PhysicsCfg, RunCfg

# ── convenience loader ───────────────────────────────────────────────────────

def load_experiment_config(path: str | Path) -> ExperimentConfig:
    """Load :class:`ExperimentConfig` from a YAML file."""
    from .config_loader import load_experiment_config as _load_experiment_config

    return _load_experiment_config(path)


def _require_pyyaml() -> Any:
    from .config_loader import require_pyyaml

    return require_pyyaml()


# ── parsing helpers ──────────────────────────────────────────────────────────

def _parse_raw(raw: dict) -> ExperimentConfig:
    from .config_loader import parse_raw

    return parse_raw(raw)


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
    from .config_output_sections import parse_output

    return parse_output(d)


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
