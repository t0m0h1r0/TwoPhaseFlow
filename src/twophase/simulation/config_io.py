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

from .config_models import ExperimentConfig, GridCfg, OutputCfg, PhysicsCfg, RunCfg
from .config_compat import (
    _coefficient_to_projection_mode,
    _normalize_interface_fitting_method,
    _normalize_momentum_predictor,
    _opt_float,
    _parse_enabled,
    _parse_grid,
    _parse_grid_rebuild,
    _parse_interface_width_mode,
    _parse_numerics_layout,
    _parse_output,
    _parse_physics,
    _parse_ppe_solver_config,
    _parse_ppe_solver_options,
    _parse_projection_mode,
    _parse_raw,
    _parse_run,
    _parse_time_integrator,
    _parse_tracking_enabled,
    _parse_tracking_method,
    _parse_tracking_primary,
    _parse_tracking_redistance_every,
    _require_pyyaml,
    _resolve_surface_tension,
    _resolve_viscosity,
    _tracking_redistance,
    _validate_choice,
    load_experiment_config,
)
from .config_constants import (
    _ADVECTION_SCHEME_ALIASES,
    _ADVECTION_SCHEMES,
    _CONVECTION_SCHEME_ALIASES,
    _CONVECTION_SCHEMES,
    _CONVECTION_TIME_SCHEMES,
    _CURVATURE_SCHEMES,
    _INTERFACE_TIME_SCHEMES,
    _MOMENTUM_FORMS,
    _MOMENTUM_GRADIENT_ALIASES,
    _MOMENTUM_GRADIENT_SCHEMES,
    _MOMENTUM_PREDICTOR_ALIASES,
    _MOMENTUM_PREDICTORS,
    _PPE_DISCRETIZATIONS,
    _PPE_DISCRETIZATION_SOLVERS,
    _PPE_ITERATION_METHODS,
    _PPE_PRECONDITIONERS,
    _PPE_SCHEMES,
    _PPE_SOLVER_KINDS,
    _PPE_TO_PRESSURE_SCHEME,
    _POISSON_COEFFICIENT_ALIASES,
    _POISSON_COEFFICIENTS,
    _POISSON_INTERFACE_COUPLING_ALIASES,
    _POISSON_INTERFACE_COUPLINGS,
    _PROJECTION_MODE_ALIASES,
    _PROJECTION_MODES,
    _PROJECTION_TO_REPROJECT_MODE,
    _REINIT_METHODS,
    _SURFACE_TENSION_ALIASES,
    _SURFACE_TENSION_SCHEMES,
    _VISCOUS_SPATIAL_ALIASES,
    _VISCOUS_SPATIAL_SCHEMES,
    _VISCOUS_TIME_SCHEMES,
)
