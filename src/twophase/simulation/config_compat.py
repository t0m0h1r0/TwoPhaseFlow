"""Compatibility helpers re-exported by ``config_io``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_loader import load_experiment_config, parse_raw, require_pyyaml
from .config_output_sections import parse_output as _parse_output
from .config_run_sections import (
    coefficient_to_projection_mode as _coefficient_to_projection_mode,
    normalize_momentum_predictor as _normalize_momentum_predictor,
    parse_enabled as _parse_enabled,
    parse_numerics_layout as _parse_numerics_layout,
    parse_ppe_solver_config as _parse_ppe_solver_config,
    parse_ppe_solver_options as _parse_ppe_solver_options,
    parse_projection_mode as _parse_projection_mode,
    parse_run as _parse_run,
    parse_time_integrator as _parse_time_integrator,
    parse_tracking_enabled as _parse_tracking_enabled,
    parse_tracking_method as _parse_tracking_method,
    parse_tracking_primary as _parse_tracking_primary,
    parse_tracking_redistance_every as _parse_tracking_redistance_every,
    tracking_redistance as _tracking_redistance,
)
from .config_sections import (
    normalize_interface_fitting_method as _normalize_interface_fitting_method,
    opt_float as _opt_float,
    parse_grid as _parse_grid,
    parse_grid_rebuild as _parse_grid_rebuild,
    parse_interface_width_mode as _parse_interface_width_mode,
    parse_physics as _parse_physics,
    resolve_surface_tension as _resolve_surface_tension,
    resolve_viscosity as _resolve_viscosity,
    validate_choice as _validate_choice,
)


def _require_pyyaml() -> Any:
    return require_pyyaml()


def _parse_raw(raw: dict):
    return parse_raw(raw)


__all__ = [
    "load_experiment_config",
    "_require_pyyaml",
    "_parse_raw",
    "_parse_grid",
    "_parse_physics",
    "_resolve_viscosity",
    "_resolve_surface_tension",
    "_parse_run",
    "_parse_output",
    "_opt_float",
    "_validate_choice",
    "_parse_numerics_layout",
    "_parse_time_integrator",
    "_parse_ppe_solver_config",
    "_parse_ppe_solver_options",
    "_parse_interface_width_mode",
    "_parse_grid_rebuild",
    "_parse_enabled",
    "_normalize_interface_fitting_method",
    "_parse_tracking_method",
    "_parse_tracking_enabled",
    "_parse_tracking_primary",
    "_tracking_redistance",
    "_parse_tracking_redistance_every",
    "_normalize_momentum_predictor",
    "_parse_projection_mode",
    "_coefficient_to_projection_mode",
    "Path",
]
