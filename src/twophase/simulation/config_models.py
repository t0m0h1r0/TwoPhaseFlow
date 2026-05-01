"""Schema models for experiment configuration."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GridCfg:
    NX: int = 64
    NY: int = 64
    LX: float = 1.0
    LY: float = 1.0
    bc_type: str = "wall"
    alpha_grid: float = 1.0
    fitting_axes: tuple[bool, bool] = (True, True)
    fitting_alpha_grid: tuple[float, float] = (1.0, 1.0)
    eps_factor: float = 1.5
    eps_g_factor: float = 2.0
    fitting_eps_g_factor: tuple[float, float] = (2.0, 2.0)
    eps_g_cells: float | None = None
    fitting_eps_g_cells: tuple[float | None, float | None] = (None, None)
    dx_min_floor: float = 1e-6
    fitting_dx_min_floor: tuple[float, float] = (1e-6, 1e-6)
    use_local_eps: bool = False
    eps_xi_cells: float | None = None
    grid_rebuild_freq: int = 1
    interface_fitting_enabled: bool = True
    interface_fitting_method: str = "gaussian_levelset"


@dataclass
class PhysicsCfg:
    rho_l: float = 1.0
    rho_g: float = 1.0
    sigma: float = 0.0
    mu: float = 0.01
    mu_l: float | None = None
    mu_g: float | None = None
    g_acc: float = 0.0
    rho_ref: float | None = None
    _lambda_mu: float | None = None

    def with_lambda_mu(self, lambda_mu: float) -> "PhysicsCfg":
        """Return a copy with mu_l = lambda_mu * mu_g applied."""
        obj = copy.copy(self)
        if obj.mu_g is not None:
            object.__setattr__(obj, "mu_l", lambda_mu * obj.mu_g)
        object.__setattr__(obj, "_lambda_mu", lambda_mu)
        return obj


@dataclass
class RunCfg:
    T_final: float | None = None
    max_steps: int | None = None
    cfl: float = 1.0
    cfl_policy: str = "theory_multiplier"
    cfl_advective: float = 0.10
    cfl_capillary: float = 0.05
    cfl_viscous: float = 1.0
    snap_times: list = field(default_factory=list)
    snap_interval: float | None = None
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
    kappa_max: float | None = None
    reinit_method: str | None = None
    dgr_phi_smooth_C: float = 1e-4
    ridge_sigma_0: float = 3.0
    advection_scheme: str = "dissipative_ccd"
    convection_scheme: str = "ccd"
    ppe_solver: str = "fvm_iterative"
    ppe_dc_base_solver: str | None = None
    pressure_scheme: str = "fvm_matrixfree"
    ppe_coefficient_scheme: str = "phase_density"
    ppe_interface_coupling_scheme: str = "none"
    surface_tension_scheme: str = "csf"
    convection_time_scheme: str = "ab2"
    viscous_spatial_scheme: str = "ccd_bulk"
    viscous_time_scheme: str = "explicit"
    cn_mode: str = "picard"
    cn_buoyancy_predictor_assembly_mode: str = "none"
    pressure_gradient_scheme: str = "ccd"
    surface_tension_gradient_scheme: str = "ccd"
    momentum_gradient_scheme: str = "ccd"
    uccd6_sigma: float = 1.0e-3
    face_flux_projection: bool = False
    canonical_face_state: bool = False
    face_native_predictor_state: bool = False
    face_no_slip_boundary_state: bool = False
    preserve_projected_faces: bool = False
    projection_consistent_buoyancy: bool = False
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
    debug_diagnostics: bool = False


@dataclass
class OutputCfg:
    dir: str = "results"
    save_npz: bool = True
    figures: list = field(default_factory=list)


@dataclass
class ExperimentConfig:
    """Complete experiment configuration."""

    grid: GridCfg = field(default_factory=GridCfg)
    physics: PhysicsCfg = field(default_factory=PhysicsCfg)
    run: RunCfg = field(default_factory=RunCfg)
    output: OutputCfg = field(default_factory=OutputCfg)
    diagnostics: list = field(default_factory=list)
    initial_condition: dict = field(default_factory=dict)
    initial_velocity: dict | None = None
    boundary_condition: dict | None = None
    sweep: list | None = None

    def override(self, **kwargs) -> "ExperimentConfig":
        """Return a shallow copy with top-level or nested fields replaced."""
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

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ExperimentConfig":
        """Load from a YAML file."""
        from .config_loader import parse_raw, require_pyyaml

        yaml = require_pyyaml()
        with open(path) as fh:
            raw = yaml.safe_load(fh) or {}
        return parse_raw(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "ExperimentConfig":
        """Construct from a plain dict."""
        from .config_loader import parse_raw

        return parse_raw(raw)
