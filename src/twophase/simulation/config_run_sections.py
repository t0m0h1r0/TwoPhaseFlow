"""Run-section parsing helpers for experiment configs."""

from __future__ import annotations

from typing import Any

from .config_sections import opt_float, validate_choice
from .config_models import RunCfg
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
    time_cfg = d["time"]
    snapshots = output.get("snapshots", {}) or {}
    reinit = interface["reinitialization"]
    interface_geometry = interface.get("geometry", {}) or {}
    interface_curvature = interface_geometry.get("curvature", {}) or {}
    reinit_profile = reinit.get("profile", {}) or {}
    reinit_schedule = reinit["schedule"]
    layout = parse_numerics_layout(numerics)
    tracking = layout["tracking"]
    projection = layout["projection"]
    debug = d.get("debug", {}) or {}
    snap_raw = snapshots.get("times", [])
    if snap_raw is None:
        snap_raw = []
    cfl_raw = time_cfg.get("cfl")
    dt_fixed_raw = time_cfg.get("dt")
    if cfl_raw is not None and dt_fixed_raw is not None:
        raise ValueError("run.time: 'cfl' and 'dt' are mutually exclusive.")

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

    return RunCfg(
        T_final=opt_float(time_cfg["final"]),
        max_steps=int(time_cfg["max_steps"]) if "max_steps" in time_cfg else None,
        cfl=float(cfl_raw if cfl_raw is not None else 0.15),
        snap_times=[float(x) for x in snap_raw],
        snap_interval=opt_float(snapshots.get("interval")),
        reinit_eps_scale=float(reinit_profile.get("eps_scale", 1.0)),
        print_every=int(time_cfg.get("print_every", 100)),
        dt_fixed=opt_float(dt_fixed_raw),
        cn_viscous=(operator_settings["viscous_time_scheme"] == "crank_nicolson"),
        reinit_every=int(reinit_schedule["every_steps"]),
        reproject_mode=reproject_mode,
        phi_primary_transport=parse_tracking_primary(
            tracking,
            layout["paths"]["tracking_primary"],
        ),
        interface_tracking_enabled=parse_tracking_enabled(tracking),
        interface_tracking_method=parse_tracking_method(
            tracking,
            layout["paths"]["tracking_primary"],
        ),
        phi_primary_redist_every=parse_tracking_redistance_every(
            tracking,
            layout["paths"]["tracking_redistance"],
        ),
        phi_primary_clip_factor=float(tracking_redistance(tracking).get("clip_factor", 12.0)),
        phi_primary_heaviside_eps_scale=float(
            tracking_redistance(tracking).get("heaviside_eps_scale", 1.0)
        ),
        kappa_max=opt_float(
            interface_curvature.get("cap", layout["surface_tension"].get("curvature_cap"))
        ),
        reinit_method=reinit_method,
        dgr_phi_smooth_C=float(reinit_profile.get("dgr_phi_smooth_C", 1e-4)),
        ridge_sigma_0=ridge_sigma_0,
        advection_scheme=operator_settings["advection_scheme"],
        convection_scheme=operator_settings["convection_scheme"],
        ppe_solver=operator_settings["ppe_solver"],
        pressure_scheme=operator_settings["pressure_scheme"],
        ppe_coefficient_scheme=operator_settings["poisson_coefficient"],
        ppe_interface_coupling_scheme=operator_settings["poisson_interface_coupling"],
        surface_tension_scheme=operator_settings["surface_tension_scheme"],
        convection_time_scheme=operator_settings["convection_time_scheme"],
        viscous_spatial_scheme=operator_settings["viscous_spatial_scheme"],
        viscous_time_scheme=operator_settings["viscous_time_scheme"],
        pressure_gradient_scheme=operator_settings["pressure_gradient_scheme"],
        surface_tension_gradient_scheme=operator_settings["surface_tension_gradient_scheme"],
        momentum_gradient_scheme=operator_settings["momentum_gradient_scheme"],
        uccd6_sigma=operator_settings["uccd6_sigma"],
        face_flux_projection=bool(projection.get("face_flux_projection", False)),
        ppe_iteration_method=operator_settings["ppe_iteration_method"],
        ppe_tolerance=operator_settings["ppe_tolerance"],
        ppe_max_iterations=operator_settings["ppe_max_iterations"],
        ppe_restart=operator_settings["ppe_restart"],
        ppe_preconditioner=operator_settings["ppe_preconditioner"],
        ppe_pcr_stages=operator_settings["ppe_pcr_stages"],
        ppe_c_tau=operator_settings["ppe_c_tau"],
        ppe_defect_correction=operator_settings["ppe_defect_correction"],
        ppe_dc_max_iterations=operator_settings["ppe_dc_max_iterations"],
        ppe_dc_tolerance=operator_settings["ppe_dc_tolerance"],
        ppe_dc_relaxation=operator_settings["ppe_dc_relaxation"],
        debug_diagnostics=bool(debug.get("step_diagnostics", False)),
    )
