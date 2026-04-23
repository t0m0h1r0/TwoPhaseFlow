"""Run-section parsing helpers for experiment configs."""

from __future__ import annotations

from .config_models import RunCfg
from .config_run_builder_sections import RunCfgBuilderOptions, build_run_cfg
from .config_run_context_sections import build_run_parse_context
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
from .config_run_reinit_sections import parse_run_reinit_projection
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


def parse_run(
    d: dict,
    interface: dict,
    numerics: dict,
    output: dict | None = None,
) -> RunCfg:
    """Parse the run section from experiment YAML."""
    context = build_run_parse_context(
        run_section=d,
        interface=interface,
        numerics=numerics,
        output=output,
    )

    operator_settings = parse_run_operator_settings(
        layout=context.layout,
        interface_transport=context.layout["interface_transport"],
        momentum=context.layout["momentum"],
        convection=context.layout["convection"],
        viscosity=context.layout["viscosity"],
        pressure_term=context.layout["pressure_term"],
        surface_tension=context.layout["surface_tension"],
        interface_curvature=context.interface_curvature,
        projection=context.projection,
    )

    reinit_projection = parse_run_reinit_projection(
        reinit=context.reinit,
        reinit_profile=context.reinit_profile,
        projection=context.projection,
        poisson_coefficient=operator_settings["poisson_coefficient"],
        projection_mode_path=context.layout["paths"]["projection_mode"],
    )

    return build_run_cfg(
        RunCfgBuilderOptions(
            time_cfg=context.time_cfg,
            snapshots=context.snapshots,
            tracking=context.tracking,
            projection=context.projection,
            interface_curvature=context.interface_curvature,
            surface_tension=context.layout["surface_tension"],
            reinit_profile=context.reinit_profile,
            reinit_schedule=context.reinit_schedule,
            layout_paths=context.layout["paths"],
            operator_settings=operator_settings,
            reproject_mode=reinit_projection.reproject_mode,
            reinit_method=reinit_projection.reinit_method,
            ridge_sigma_0=reinit_projection.ridge_sigma_0,
            debug=context.debug,
        )
    )
