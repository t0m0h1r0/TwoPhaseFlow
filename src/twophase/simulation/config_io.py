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
    lambda_mu  → mu_l  = lambda_mu * mu_g  (then mu = mu_g as fallback)
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
    use_local_eps: bool = False   # ε(x) = C_ε · h_local(x) for CSF
    eps_xi_cells: float | None = None  # ξ-space Heaviside eps width (cells); implies use_local_eps
    grid_rebuild_freq: int = 1    # rebuild grid every K steps (1 = every step)


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
    snap_interval: float | None = None  # auto-generate snap_times every N time units (None = disabled)
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
    reinit_method: str | None = None  # None → auto (DGR); 'split'/'dgr'/'hybrid' to override
    dgr_phi_smooth_C: float = 1e-4   # CCD Laplacian smoothing on φ_sdf in DGR reinit


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
    run = _parse_run(raw.get("run", {}))
    output = _parse_output(raw.get("output", {}))
    cfg = ExperimentConfig(
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
    if raw.get("physics", {}).get("dimensional", False):
        cfg = _to_nondim(cfg)
    return cfg


def _to_nondim(cfg: ExperimentConfig) -> ExperimentConfig:
    """Convert a dimensional (SI) ExperimentConfig to non-dimensional form.

    Reference scales (capillary, gas-based):
        L_ref = R_bubble           from initial_condition.radius
        rho_ref = rho_g            gas density as density scale
        U_ref = sqrt(sigma / (rho_ref * L_ref))   capillary velocity
        t_ref = L_ref / U_ref = sqrt(rho_ref * L_ref**3 / sigma)
        mu_ref = rho_ref * U_ref * L_ref = sqrt(rho_ref * sigma * L_ref)

    After conversion:
        rho_l* = rho_l / rho_ref,  rho_g* = 1,  sigma* = 1,  g* = g * rho_ref * L_ref**2 / sigma
    """
    ph = cfg.physics
    ic = cfg.initial_condition

    L_ref = float(ic.get("radius", 1.0)) if ic else 1.0
    rho_ref = ph.rho_g
    sigma_si = ph.sigma
    if sigma_si <= 0.0:
        raise ValueError("dimensional: sigma must be > 0 for non-dimensionalization")

    U_ref = math.sqrt(sigma_si / (rho_ref * L_ref))
    t_ref = L_ref / U_ref                             # = sqrt(rho_ref * L_ref**3 / sigma_si)
    mu_ref = rho_ref * U_ref * L_ref                  # = sqrt(rho_ref * sigma_si * L_ref)

    print(
        f"  [dimensional→nondim]  L_ref={L_ref:.3e} m  "
        f"U_ref={U_ref:.3e} m/s  t_ref={t_ref:.3e} s\n"
        f"                        Eo={ph.rho_l*ph.g_acc*(2*L_ref)**2/sigma_si:.3g}  "
        f"Oh={ph.mu_l/math.sqrt(ph.rho_l*sigma_si*L_ref):.3g}"
        if ph.mu_l is not None else
        f"  [dimensional→nondim]  L_ref={L_ref:.3e} m  "
        f"U_ref={U_ref:.3e} m/s  t_ref={t_ref:.3e} s"
    )

    # -- physics --
    mu_l_nd = (ph.mu_l / mu_ref) if ph.mu_l is not None else None
    mu_g_nd = (ph.mu_g / mu_ref) if ph.mu_g is not None else None
    mu_nd   = ph.mu / mu_ref
    ph_nd = PhysicsCfg(
        rho_l=ph.rho_l / rho_ref,
        rho_g=1.0,
        sigma=1.0,
        mu=mu_nd,
        mu_l=mu_l_nd,
        mu_g=mu_g_nd,
        g_acc=ph.g_acc * rho_ref * L_ref ** 2 / sigma_si,
        rho_ref=None,
    )

    # -- grid (LX, LY only; NX/NY/alpha etc. are already dimensionless) --
    gr = cfg.grid
    gr_nd = replace(gr, LX=gr.LX / L_ref, LY=gr.LY / L_ref)

    # -- initial condition (center, radius, epsilon) --
    ic_nd = dict(ic)
    if "center" in ic_nd:
        ic_nd["center"] = [float(c) / L_ref for c in ic_nd["center"]]
    if "radius" in ic_nd:
        ic_nd["radius"] = float(ic_nd["radius"]) / L_ref  # should be 1.0
    if "epsilon" in ic_nd:
        ic_nd["epsilon"] = float(ic_nd["epsilon"]) / L_ref

    # -- run (T_final, snap_interval, snap_times, dt_fixed) --
    run = cfg.run
    run_nd = replace(
        run,
        T_final=(run.T_final / t_ref) if run.T_final is not None else None,
        snap_interval=(run.snap_interval / t_ref) if run.snap_interval is not None else None,
        snap_times=[t / t_ref for t in run.snap_times],
        dt_fixed=(run.dt_fixed / t_ref) if run.dt_fixed is not None else None,
    )

    return replace(cfg, physics=ph_nd, grid=gr_nd, initial_condition=ic_nd, run=run_nd)


def _parse_grid(d: dict) -> GridCfg:
    return GridCfg(
        NX=int(d.get("NX", 64)),
        NY=int(d.get("NY", 64)),
        LX=float(d.get("LX", 1.0)),
        LY=float(d.get("LY", 1.0)),
        bc_type=str(d.get("bc_type", "wall")),
        alpha_grid=float(d.get("alpha_grid", 1.0)),
        eps_factor=float(d.get("eps_factor", 1.5)),
        eps_g_factor=float(d.get("eps_g_factor", 2.0)),
        eps_g_cells=_opt_float(d.get("eps_g_cells")),
        dx_min_floor=float(d.get("dx_min_floor", 1e-6)),
        use_local_eps=bool(d.get("use_local_eps", False)),
        eps_xi_cells=_opt_float(d.get("eps_xi_cells")),
        grid_rebuild_freq=int(d.get("grid_rebuild_freq", 1)),
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
        return mu, None, None
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


def _parse_run(d: dict) -> RunCfg:
    snap_raw = d.get("snap_times", [])
    if snap_raw is None:
        snap_raw = []
    if d.get("cfl") is not None and d.get("dt_fixed") is not None:
        raise ValueError(
            "run: 'cfl' と 'dt_fixed' は排他です。どちらか一方のみ設定してください。"
        )
    return RunCfg(
        T_final=_opt_float(d.get("T_final")),
        max_steps=int(d["max_steps"]) if "max_steps" in d else None,
        cfl=float(d.get("cfl", 0.15)),
        snap_times=[float(x) for x in snap_raw],
        snap_interval=_opt_float(d.get("snap_interval")),
        reinit_eps_scale=float(d.get("reinit_eps_scale", 1.0)),
        print_every=int(d.get("print_every", 100)),
        dt_fixed=_opt_float(d.get("dt_fixed")),
        cn_viscous=bool(d.get("cn_viscous", False)),
        reinit_every=int(d.get("reinit_every", 2)),
        reproject_mode=str(d.get("reproject_mode", "legacy")),
        phi_primary_transport=bool(d.get("phi_primary_transport", False)),
        phi_primary_redist_every=int(d.get("phi_primary_redist_every", 4)),
        phi_primary_clip_factor=float(d.get("phi_primary_clip_factor", 12.0)),
        phi_primary_heaviside_eps_scale=float(d.get("phi_primary_heaviside_eps_scale", 1.0)),
        kappa_max=_opt_float(d.get("kappa_max")),
        reinit_method=d.get("reinit_method") or None,
        dgr_phi_smooth_C=float(d.get("dgr_phi_smooth_C", 1e-4)),
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
