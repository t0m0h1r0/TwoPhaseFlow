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
    lambda_mu  → mu_l  = lambda_mu * mu_g  (legacy mu is mu_g fallback)
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
    phi_primary_redist_every: int = 4
    phi_primary_clip_factor: float = 12.0
    phi_primary_heaviside_eps_scale: float = 1.0
    kappa_max: float | None = None  # curvature cap (None = unlimited)
    reinit_method: str | None = None  # None → auto (DGR); 'split'/'dgr'/'hybrid'/'ridge_eikonal'
    dgr_phi_smooth_C: float = 1e-4   # CCD Laplacian smoothing on φ_sdf in DGR reinit
    ridge_sigma_0: float = 3.0       # Gaussian-ξ ridge bandwidth (CHK-159, SP-E D1)
    # Stage-wise numerical schemes — bridged from SimulationBuilder (CHK-158)
    # and ch12/ch13 PPE policy.
    # advection_scheme : ψ advection — 'dissipative_ccd' | 'weno5' | 'fccd_nodal' | 'fccd_flux'
    # convection_scheme: momentum    — 'ccd'             | 'fccd_nodal' | 'fccd_flux'
    # ppe_solver       : pressure    — 'fvm_iterative'   | 'fvm_direct'
    # viscous_time_scheme: viscous predictor — 'explicit' | 'crank_nicolson'
    advection_scheme: str = "dissipative_ccd"
    convection_scheme: str = "ccd"
    ppe_solver: str = "fvm_iterative"
    viscous_time_scheme: str = "explicit"
    face_flux_projection: bool = False  # experimental CHK-172 PoC; default off
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
    grid = _parse_grid(raw.get("grid", {}))
    physics = _parse_physics(raw.get("physics", {}))
    output = _parse_output(raw.get("output", {}))
    run = _parse_run(raw.get("run", {}), raw.get("output", {}))
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


def _parse_grid(d: dict) -> GridCfg:
    adaptation = d.get("adaptation", {}) or {}
    width = d.get("interface_width", {}) or {}
    alpha_grid = float(adaptation.get("alpha", d.get("alpha_grid", 1.0)))
    eps_factor = float(width.get("base_factor", d.get("eps_factor", 1.5)))
    eps_g_factor = float(adaptation.get("eps_g_factor", d.get("eps_g_factor", 2.0)))
    eps_g_cells = _opt_float(adaptation.get("eps_g_cells", d.get("eps_g_cells")))
    eps_xi_cells = _opt_float(width.get("xi_cells", d.get("eps_xi_cells")))
    use_local_eps = _parse_interface_width_mode(width, d, eps_xi_cells)
    return GridCfg(
        NX=int(d.get("NX", 64)),
        NY=int(d.get("NY", 64)),
        LX=float(d.get("LX", 1.0)),
        LY=float(d.get("LY", 1.0)),
        bc_type=str(d.get("bc_type", "wall")),
        alpha_grid=alpha_grid,
        eps_factor=eps_factor,
        eps_g_factor=eps_g_factor,
        eps_g_cells=eps_g_cells,
        dx_min_floor=float(d.get("dx_min_floor", 1e-6)),
        use_local_eps=use_local_eps,
        eps_xi_cells=eps_xi_cells,
        grid_rebuild_freq=_parse_grid_rebuild(
            adaptation.get("rebuild", d.get("grid_rebuild_freq", 1))
        ),
    )


def _parse_physics(d: dict) -> PhysicsCfg:
    """Parse physics section, resolving derived parameters."""
    rho_l = float(d.get("rho_l", 1.0))
    rho_g = float(d.get("rho_g", 1.0))
    g_acc = float(d.get("g_acc", 0.0))
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
    mu_g = _opt_float(d.get("mu_g"))
    mu_l = _opt_float(d.get("mu_l"))
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
    sigma = _opt_float(d.get("sigma"))

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
_CONVECTION_SCHEMES = ("ccd", "fccd_nodal", "fccd_flux")
_REINIT_METHODS = (
    "split", "unified", "dgr", "hybrid",
    "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
)
_REPROJECT_MODES = (
    "legacy", "variable_density_only", "consistent_iim", "consistent_gfm",
)
_PPE_SCHEMES = ("fvm_iterative", "fvm_direct")
_PPE_SCHEME_ALIASES = {
    "fvm_matrixfree": "fvm_iterative",
    "matrixfree": "fvm_iterative",
    "fvm_spsolve": "fvm_direct",
    "spsolve": "fvm_direct",
}
_VISCOUS_TIME_SCHEMES = ("explicit", "crank_nicolson")


def _parse_run(d: dict, output: dict | None = None) -> RunCfg:
    output = output or {}
    snapshots = output.get("snapshots", d.get("snapshots", {})) or {}
    reinit = d.get("reinitialization", {}) or {}
    transport = d.get("transport", {}) or {}
    projection = d.get("projection", {}) or {}
    schemes = d.get("schemes", {}) or {}
    debug = d.get("debug", {}) or {}

    snap_raw = snapshots.get("times", d.get("snap_times", []))
    if snap_raw is None:
        snap_raw = []
    if d.get("cfl") is not None and d.get("dt_fixed") is not None:
        raise ValueError(
            "run: 'cfl' と 'dt_fixed' は排他です。どちらか一方のみ設定してください。"
        )
    advection_scheme = str(
        schemes.get("levelset_advection", schemes.get(
            "advection", d.get("advection_scheme", "dissipative_ccd")
        ))
    )
    if advection_scheme not in _ADVECTION_SCHEMES:
        raise ValueError(
            f"run.advection_scheme must be one of {_ADVECTION_SCHEMES}, "
            f"got {advection_scheme!r}"
        )
    convection_scheme = str(
        schemes.get("momentum_convection", schemes.get(
            "convection", d.get("convection_scheme", "ccd")
        ))
    )
    if convection_scheme not in _CONVECTION_SCHEMES:
        raise ValueError(
            f"run.convection_scheme must be one of {_CONVECTION_SCHEMES}, "
            f"got {convection_scheme!r}"
        )
    ppe_solver_raw = str(
        schemes.get("ppe", schemes.get(
            "pressure_poisson", d.get("ppe_solver", "fvm_iterative")
        ))
    )
    ppe_solver = _PPE_SCHEME_ALIASES.get(ppe_solver_raw, ppe_solver_raw)
    if ppe_solver not in _PPE_SCHEMES:
        raise ValueError(
            f"run.schemes.ppe must be one of {_PPE_SCHEMES}, got {ppe_solver!r}"
        )
    if "viscous_time" in schemes or "viscous" in schemes:
        viscous_time_scheme = str(schemes.get("viscous_time", schemes.get("viscous")))
    else:
        viscous_time_scheme = (
            "crank_nicolson" if bool(d.get("cn_viscous", False)) else "explicit"
        )
    if viscous_time_scheme not in _VISCOUS_TIME_SCHEMES:
        raise ValueError(
            "run.schemes.viscous_time must be one of "
            f"{_VISCOUS_TIME_SCHEMES}, got {viscous_time_scheme!r}"
        )
    reproject_mode = _normalize_reproject_mode(
        projection.get("mode", d.get("reproject_mode", "legacy"))
    )
    reinit_method = reinit.get("method", d.get("reinit_method")) or None
    if reinit_method is not None and reinit_method not in _REINIT_METHODS:
        raise ValueError(
            f"run.reinitialization.method must be one of {_REINIT_METHODS}, "
            f"got {reinit_method!r}"
        )
    ridge_sigma_0 = float(reinit.get("ridge_sigma_0", d.get("ridge_sigma_0", 3.0)))
    if ridge_sigma_0 <= 0.0:
        raise ValueError(f"run.ridge_sigma_0 must be > 0, got {ridge_sigma_0}")
    return RunCfg(
        T_final=_opt_float(d.get("T_final")),
        max_steps=int(d["max_steps"]) if "max_steps" in d else None,
        cfl=float(d.get("cfl", 0.15)),
        snap_times=[float(x) for x in snap_raw],
        snap_interval=_opt_float(snapshots.get("interval", d.get("snap_interval"))),
        reinit_eps_scale=float(reinit.get("eps_scale", d.get("reinit_eps_scale", 1.0))),
        print_every=int(d.get("print_every", 100)),
        dt_fixed=_opt_float(d.get("dt_fixed")),
        cn_viscous=(viscous_time_scheme == "crank_nicolson"),
        reinit_every=int(reinit.get("every", d.get("reinit_every", 2))),
        reproject_mode=reproject_mode,
        phi_primary_transport=_parse_transport_primary(transport, d),
        phi_primary_redist_every=int(
            transport.get("phi_redist_every", d.get("phi_primary_redist_every", 4))
        ),
        phi_primary_clip_factor=float(
            transport.get("phi_clip_factor", d.get("phi_primary_clip_factor", 12.0))
        ),
        phi_primary_heaviside_eps_scale=float(
            transport.get(
                "phi_heaviside_eps_scale",
                d.get("phi_primary_heaviside_eps_scale", 1.0),
            )
        ),
        kappa_max=_opt_float(d.get("kappa_max")),
        reinit_method=reinit_method,
        dgr_phi_smooth_C=float(
            reinit.get("dgr_phi_smooth_C", d.get("dgr_phi_smooth_C", 1e-4))
        ),
        ridge_sigma_0=ridge_sigma_0,
        advection_scheme=advection_scheme,
        convection_scheme=convection_scheme,
        ppe_solver=ppe_solver,
        viscous_time_scheme=viscous_time_scheme,
        face_flux_projection=bool(
            projection.get("face_flux_projection", d.get("face_flux_projection", False))
        ),
        debug_diagnostics=bool(
            debug.get("step_diagnostics", d.get("debug_diagnostics", False))
        ),
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


def _parse_interface_width_mode(
    width: dict,
    legacy_grid: dict,
    eps_xi_cells: float | None,
) -> bool:
    """Resolve interface-width mode to the legacy local-eps boolean."""
    mode = width.get("mode")
    if mode is None:
        return bool(legacy_grid.get("use_local_eps", False)) or eps_xi_cells is not None
    mode = str(mode).strip().lower()
    if mode in {"nominal", "global", "uniform"}:
        return False
    if mode in {"local", "local_cell"}:
        return True
    if mode in {"xi_cells", "xi"}:
        if eps_xi_cells is None:
            raise ValueError("grid.interface_width.mode='xi_cells' requires xi_cells")
        return True
    raise ValueError(
        "grid.interface_width.mode must be nominal|local|xi_cells, "
        f"got {mode!r}"
    )


def _parse_grid_rebuild(raw: Any) -> int:
    """Resolve grid adaptation rebuild policy to the legacy frequency integer."""
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
        raise ValueError(f"grid.adaptation.rebuild must be >= 0, got {freq}")
    return freq


def _parse_transport_primary(transport: dict, legacy_run: dict) -> bool:
    """Resolve transport.primary to the legacy phi_primary_transport boolean."""
    primary = transport.get("primary")
    if primary is None:
        return bool(legacy_run.get("phi_primary_transport", False))
    primary = str(primary).strip().lower()
    if primary == "phi":
        return True
    if primary == "psi":
        return False
    raise ValueError(f"run.transport.primary must be 'phi' or 'psi', got {primary!r}")


def _normalize_reproject_mode(raw: Any) -> str:
    """Normalize projection mode aliases used in experiment YAML."""
    mode = str(raw).strip().lower()
    aliases = {
        "none": "legacy",
        "variable_density": "variable_density_only",
        "iim": "consistent_iim",
        "gfm": "consistent_gfm",
    }
    mode = aliases.get(mode, mode)
    if mode not in _REPROJECT_MODES:
        raise ValueError(
            f"run.projection.mode must be one of {_REPROJECT_MODES} "
            "or aliases none|variable_density|iim|gfm, "
            f"got {raw!r}"
        )
    return mode
