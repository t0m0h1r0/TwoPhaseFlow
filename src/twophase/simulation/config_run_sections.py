"""Run-section parsing helpers for experiment configs."""

from __future__ import annotations

from .config_models import RunCfg
from .config_run_builder_sections import RunCfgBuilderOptions, build_run_cfg
from .config_sections import validate_choice
from .config_run_layout_sections import (
    normalize_momentum_predictor,
    parse_numerics_layout,
    parse_time_integrator,
)
from .config_run_operator_sections import parse_run_operator_settings
from .config_run_ppe_sections import (
    parse_ppe_solver_config,
    parse_ppe_solver_options,
)
from .config_run_tracking_sections import (
    coefficient_to_projection_mode,
    parse_enabled,
    parse_projection_mode,
    parse_tracking_enabled,
    parse_tracking_method,
    parse_tracking_primary,
    parse_tracking_redistance_every,
    tracking_redistance,
)

_REINIT_METHODS = (
    "split", "unified", "dgr", "hybrid",
    "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
)


def parse_run(
    d: dict,
    interface: dict,
    numerics: dict,
    output: dict | None = None,
) -> RunCfg:
    """Parse the run section from experiment YAML."""
    output = output or {}
    reinit = interface["reinitialization"]
    interface_geometry = interface.get("geometry", {}) or {}
    interface_curvature = interface_geometry.get("curvature", {}) or {}
    reinit_profile = reinit.get("profile", {}) or {}
    reinit_schedule = reinit["schedule"]
    layout = parse_numerics_layout(numerics)
    tracking = layout["tracking"]
    projection = layout["projection"]
    debug = d.get("debug", {}) or {}

    operator_settings = parse_run_operator_settings(
        layout=layout,
        interface_transport=layout["interface_transport"],
        momentum=layout["momentum"],
        convection=layout["convection"],
        viscosity=layout["viscosity"],
        pressure_term=layout["pressure_term"],
        surface_tension=layout["surface_tension"],
        interface_curvature=interface_curvature,
        projection=projection,
    )

    reproject_mode = parse_projection_mode(
        projection.get(
            "mode",
            coefficient_to_projection_mode(operator_settings["poisson_coefficient"]),
        ),
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

    return build_run_cfg(
        RunCfgBuilderOptions(
            time_cfg=d["time"],
            snapshots=output.get("snapshots", {}) or {},
            tracking=tracking,
            projection=projection,
            interface_curvature=interface_curvature,
            surface_tension=layout["surface_tension"],
            reinit_profile=reinit_profile,
            reinit_schedule=reinit_schedule,
            layout_paths=layout["paths"],
            operator_settings=operator_settings,
            reproject_mode=reproject_mode,
            reinit_method=reinit_method,
            ridge_sigma_0=ridge_sigma_0,
            debug=debug,
        )
    )
