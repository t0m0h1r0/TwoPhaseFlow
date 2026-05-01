"""Structured option groups for ``TwoPhaseNSSolver`` construction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolverGridOptions:
    """Geometry and backend settings for the NS pipeline."""

    NX: int
    NY: int
    LX: float
    LY: float
    bc_type: str = "wall"
    use_gpu: bool | None = None
    alpha_grid: float = 1.0
    fitting_axes: tuple[bool, bool] = (True, True)
    fitting_alpha_grid: tuple[float, float] = (1.0, 1.0)
    eps_factor: float = 1.5
    eps_g_factor: float = 2.0
    fitting_eps_g_factor: tuple[float, float] = (2.0, 2.0)
    eps_g_cells: float | None = None
    fitting_eps_g_cells: tuple[float | None, float | None] = (None, None)
    wall_refinement_axes: tuple[bool, bool] = (False, False)
    wall_alpha_grid: tuple[float, float] = (1.0, 1.0)
    wall_eps_g_factor: float = 2.0
    wall_eps_g_factor_axes: tuple[float, float] = (2.0, 2.0)
    wall_eps_g_cells: tuple[float | None, float | None] = (None, None)
    wall_sides: tuple[tuple[str, ...], tuple[str, ...]] = (
        ("lower", "upper"),
        ("lower", "upper"),
    )
    dx_min_floor: float = 1e-6
    fitting_dx_min_floor: tuple[float, float] = (1e-6, 1e-6)
    use_local_eps: bool = False
    eps_xi_cells: float | None = None


@dataclass(frozen=True)
class SolverInterfaceOptions:
    """Interface-transport and remap settings."""

    grid_rebuild_freq: int = 1
    reinit_every: int = 2
    reinit_method: str = "eikonal_xi"
    reproject_variable_density: bool = False
    reproject_mode: str = "legacy"
    phi_primary_transport: bool = True
    interface_tracking_enabled: bool = True
    interface_tracking_method: str | None = None
    phi_primary_redist_every: int = 4
    phi_primary_clip_factor: float = 12.0
    phi_primary_heaviside_eps_scale: float = 1.0
    kappa_max: float | None = None
    dgr_phi_smooth_C: float = 1e-4
    reinit_eps_scale: float = 1.0
    ridge_sigma_0: float = 3.0


@dataclass(frozen=True)
class SolverPPEOptions:
    """Pressure-solver settings."""

    ppe_solver: str = "fvm_iterative"
    ppe_dc_base_solver: str | None = None
    pressure_scheme: str | None = None
    ppe_coefficient_scheme: str = "phase_density"
    ppe_interface_coupling_scheme: str = "none"
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


@dataclass(frozen=True)
class SolverSchemeOptions:
    """Scheme selection and runtime toggles."""

    hfe_C: float = 0.05
    reinit_steps: int = 4
    cn_viscous: bool = False
    Re: float = 1.0
    surface_tension_scheme: str = "csf"
    convection_time_scheme: str = "ab2"
    advection_scheme: str = "dissipative_ccd"
    convection_scheme: str = "ccd"
    pressure_gradient_scheme: str | None = None
    surface_tension_gradient_scheme: str | None = None
    momentum_gradient_scheme: str = "projection_consistent"
    viscous_spatial_scheme: str = "ccd_bulk"
    viscous_time_scheme: str = "forward_euler"
    cn_mode: str = "picard"
    cn_buoyancy_predictor_assembly_mode: str = "none"
    uccd6_sigma: float = 1.0e-3
    face_flux_projection: bool = False
    canonical_face_state: bool = False
    face_native_predictor_state: bool = False
    face_no_slip_boundary_state: bool = False
    preserve_projected_faces: bool = False
    projection_consistent_buoyancy: bool = False
    debug_diagnostics: bool = False


@dataclass(frozen=True)
class NSSolverInitOptions:
    """Top-level grouped options for ``TwoPhaseNSSolver``."""

    grid: SolverGridOptions
    interface: SolverInterfaceOptions
    ppe: SolverPPEOptions
    schemes: SolverSchemeOptions
