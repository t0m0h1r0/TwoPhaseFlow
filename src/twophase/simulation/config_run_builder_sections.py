"""Run-section config assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config_models import RunCfg
from .config_sections import opt_float
from .config_run_tracking_sections import (
    parse_tracking_enabled,
    parse_tracking_method,
    parse_tracking_primary,
    parse_tracking_redistance_every,
    tracking_redistance,
)


@dataclass(frozen=True)
class RunCfgBuilderOptions:
    time_cfg: dict[str, Any]
    snapshots: dict[str, Any]
    tracking: dict[str, Any]
    projection: dict[str, Any]
    interface_curvature: dict[str, Any]
    surface_tension: dict[str, Any]
    reinit_profile: dict[str, Any]
    reinit_schedule: dict[str, Any]
    layout_paths: dict[str, str]
    operator_settings: dict[str, Any]
    reproject_mode: str
    reinit_method: str | None
    ridge_sigma_0: float
    debug: dict[str, Any]


def build_run_cfg(options: RunCfgBuilderOptions) -> RunCfg:
    """Build `RunCfg` from normalized run-section fragments."""
    snap_raw = options.snapshots.get("times", [])
    if snap_raw is None:
        snap_raw = []

    cfl_raw = options.time_cfg.get("cfl")
    dt_fixed_raw = options.time_cfg.get("dt")
    if cfl_raw is not None and dt_fixed_raw is not None:
        raise ValueError("run.time: 'cfl' and 'dt' are mutually exclusive.")

    tracking_redist = tracking_redistance(options.tracking)
    return RunCfg(
        T_final=opt_float(options.time_cfg["final"]),
        max_steps=int(options.time_cfg["max_steps"]) if "max_steps" in options.time_cfg else None,
        cfl=float(cfl_raw if cfl_raw is not None else 0.15),
        snap_times=[float(x) for x in snap_raw],
        snap_interval=opt_float(options.snapshots.get("interval")),
        reinit_eps_scale=float(options.reinit_profile.get("eps_scale", 1.0)),
        print_every=int(options.time_cfg.get("print_every", 100)),
        dt_fixed=opt_float(dt_fixed_raw),
        cn_viscous=(
            options.operator_settings["viscous_time_scheme"]
            in {"crank_nicolson", "implicit_bdf2"}
        ),
        reinit_every=int(options.reinit_schedule["every_steps"]),
        reproject_mode=options.reproject_mode,
        phi_primary_transport=parse_tracking_primary(
            options.tracking,
            options.layout_paths["tracking_primary"],
        ),
        interface_tracking_enabled=parse_tracking_enabled(options.tracking),
        interface_tracking_method=parse_tracking_method(
            options.tracking,
            options.layout_paths["tracking_primary"],
        ),
        phi_primary_redist_every=parse_tracking_redistance_every(
            options.tracking,
            options.layout_paths["tracking_redistance"],
        ),
        phi_primary_clip_factor=float(tracking_redist.get("clip_factor", 12.0)),
        phi_primary_heaviside_eps_scale=float(
            tracking_redist.get("heaviside_eps_scale", 1.0)
        ),
        kappa_max=opt_float(
            options.interface_curvature.get("cap", options.surface_tension.get("curvature_cap"))
        ),
        reinit_method=options.reinit_method,
        dgr_phi_smooth_C=float(options.reinit_profile.get("dgr_phi_smooth_C", 1e-4)),
        ridge_sigma_0=options.ridge_sigma_0,
        advection_scheme=options.operator_settings["advection_scheme"],
        convection_scheme=options.operator_settings["convection_scheme"],
        ppe_solver=options.operator_settings["ppe_solver"],
        pressure_scheme=options.operator_settings["pressure_scheme"],
        ppe_coefficient_scheme=options.operator_settings["poisson_coefficient"],
        ppe_interface_coupling_scheme=options.operator_settings["poisson_interface_coupling"],
        surface_tension_scheme=options.operator_settings["surface_tension_scheme"],
        convection_time_scheme=options.operator_settings["convection_time_scheme"],
        viscous_spatial_scheme=options.operator_settings["viscous_spatial_scheme"],
        viscous_time_scheme=options.operator_settings["viscous_time_scheme"],
        cn_mode=options.operator_settings["cn_mode"],
        cn_buoyancy_predictor_assembly_mode=options.operator_settings[
            "cn_buoyancy_predictor_assembly_mode"
        ],
        pressure_gradient_scheme=options.operator_settings["pressure_gradient_scheme"],
        surface_tension_gradient_scheme=options.operator_settings["surface_tension_gradient_scheme"],
        momentum_gradient_scheme=options.operator_settings["momentum_gradient_scheme"],
        uccd6_sigma=options.operator_settings["uccd6_sigma"],
        face_flux_projection=bool(options.projection.get("face_flux_projection", False)),
        canonical_face_state=bool(options.projection.get("canonical_face_state", False)),
        face_native_predictor_state=bool(
            options.projection.get("face_native_predictor_state", False)
        ),
        face_no_slip_boundary_state=bool(
            options.projection.get("face_no_slip_boundary_state", False)
        ),
        preserve_projected_faces=bool(
            options.projection.get("preserve_projected_faces", False)
        ),
        projection_consistent_buoyancy=bool(
            options.projection.get("projection_consistent_buoyancy", False)
        ),
        ppe_iteration_method=options.operator_settings["ppe_iteration_method"],
        ppe_tolerance=options.operator_settings["ppe_tolerance"],
        ppe_max_iterations=options.operator_settings["ppe_max_iterations"],
        ppe_restart=options.operator_settings["ppe_restart"],
        ppe_preconditioner=options.operator_settings["ppe_preconditioner"],
        ppe_pcr_stages=options.operator_settings["ppe_pcr_stages"],
        ppe_c_tau=options.operator_settings["ppe_c_tau"],
        ppe_defect_correction=options.operator_settings["ppe_defect_correction"],
        ppe_dc_max_iterations=options.operator_settings["ppe_dc_max_iterations"],
        ppe_dc_tolerance=options.operator_settings["ppe_dc_tolerance"],
        ppe_dc_relaxation=options.operator_settings["ppe_dc_relaxation"],
        debug_diagnostics=bool(options.debug.get("step_diagnostics", False)),
    )
