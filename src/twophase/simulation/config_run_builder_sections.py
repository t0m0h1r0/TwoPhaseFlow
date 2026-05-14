"""Run-section config assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config_models import RunCfg
from .config_sections import opt_float, validate_choice
from .config_run_tracking_sections import (
    parse_tracking_enabled,
    parse_tracking_gauge_reconstruction,
    parse_tracking_method,
    parse_tracking_primary,
    parse_tracking_redistance_every,
    tracking_redistance,
)

DEFAULT_CFL_MULTIPLIER = 1.0
LEGACY_THEORY_CFL_ALIASES = {"auto", "theory", "theoretical"}
THEORY_CFL_ADVECTIVE = 0.10
THEORY_CFL_CAPILLARY = 0.05
THEORY_CFL_VISCOUS = 1.0
_BOUNDARY_HODGE_MODES = ("off", "wall_trace_projection")
_BOUNDARY_HODGE_STATE_SPACES = ("full_face", "constrained_face")
_BOUNDARY_HODGE_WALL_TRACES = ("reconstruct_nodes",)
_BOUNDARY_HODGE_WALL_RETRACTIONS = ("metric_projection",)
_BOUNDARY_HODGE_METRICS = ("transported_face_mass",)
_BOUNDARY_HODGE_PRESSURE_PAIRINGS = (
    "active_variational_adjoint",
    "restricted_variational_adjoint",
)
_BOUNDARY_HODGE_SOLVERS = ("matrix_free_cg",)
_BOUNDARY_HODGE_GATES = ("off", "diagnostic", "fail_close")


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


def resolve_cfl_policy(raw: Any) -> tuple[float, str, float, float, float]:
    """Resolve ``run.time.cfl`` as a multiplier on theory CFL constants."""
    if raw is None:
        multiplier = DEFAULT_CFL_MULTIPLIER
    elif isinstance(raw, str):
        value = raw.strip().lower()
        multiplier = (
            DEFAULT_CFL_MULTIPLIER
            if value in LEGACY_THEORY_CFL_ALIASES
            else float(value)
        )
    elif isinstance(raw, dict):
        multiplier = float(raw.get("multiplier", raw.get("value", DEFAULT_CFL_MULTIPLIER)))
        adv_factor = float(raw.get("advective", multiplier))
        cap_factor = float(raw.get("capillary", multiplier))
        visc_factor = float(raw.get("viscous", multiplier))
        return (
            multiplier,
            "theory_multiplier",
            THEORY_CFL_ADVECTIVE * adv_factor,
            THEORY_CFL_CAPILLARY * cap_factor,
            THEORY_CFL_VISCOUS * visc_factor,
        )
    else:
        multiplier = float(raw)
    if multiplier <= 0.0:
        raise ValueError("run.time.cfl must be a positive multiplier.")
    return (
        multiplier,
        "theory_multiplier",
        THEORY_CFL_ADVECTIVE * multiplier,
        THEORY_CFL_CAPILLARY * multiplier,
        THEORY_CFL_VISCOUS * multiplier,
    )


def _parse_boundary_hodge(projection: dict[str, Any]) -> dict[str, Any]:
    raw = projection.get("boundary_hodge", {}) or {}
    if isinstance(raw, str):
        raw = {"mode": raw}
    if not isinstance(raw, dict):
        raise ValueError("numerics.projection.boundary_hodge must be a mapping or mode string.")
    mode_raw = raw.get("mode", "off")
    if mode_raw is True:
        mode_value = "wall_trace_projection"
    elif mode_raw is False:
        mode_value = "off"
    else:
        mode_value = mode_raw
    mode = validate_choice(
        str(mode_value).strip().lower(),
        _BOUNDARY_HODGE_MODES,
        "numerics.projection.boundary_hodge.mode",
    )
    state_space = validate_choice(
        str(raw.get("state_space", "full_face")).strip().lower(),
        _BOUNDARY_HODGE_STATE_SPACES,
        "numerics.projection.boundary_hodge.state_space",
    )
    wall_trace = validate_choice(
        str(raw.get("wall_trace", "reconstruct_nodes")).strip().lower(),
        _BOUNDARY_HODGE_WALL_TRACES,
        "numerics.projection.boundary_hodge.wall_trace",
    )
    wall_retraction = validate_choice(
        str(raw.get("wall_retraction", "metric_projection")).strip().lower(),
        _BOUNDARY_HODGE_WALL_RETRACTIONS,
        "numerics.projection.boundary_hodge.wall_retraction",
    )
    metric = validate_choice(
        str(raw.get("metric", "transported_face_mass")).strip().lower(),
        _BOUNDARY_HODGE_METRICS,
        "numerics.projection.boundary_hodge.metric",
    )
    pressure_default = (
        "restricted_variational_adjoint"
        if state_space == "constrained_face"
        else "active_variational_adjoint"
    )
    pressure_pairing = validate_choice(
        str(raw.get("pressure_pairing", pressure_default)).strip().lower(),
        _BOUNDARY_HODGE_PRESSURE_PAIRINGS,
        "numerics.projection.boundary_hodge.pressure_pairing",
    )
    if state_space == "constrained_face" and pressure_pairing != "restricted_variational_adjoint":
        raise ValueError(
            "numerics.projection.boundary_hodge.state_space='constrained_face' "
            "requires pressure_pairing='restricted_variational_adjoint'."
        )
    if mode == "wall_trace_projection" and state_space == "constrained_face":
        raise ValueError(
            "boundary_hodge.mode='wall_trace_projection' is a post-pressure "
            "diagnostic and must not be combined with state_space='constrained_face'."
        )
    solver = validate_choice(
        str(raw.get("solver", "matrix_free_cg")).strip().lower(),
        _BOUNDARY_HODGE_SOLVERS,
        "numerics.projection.boundary_hodge.solver",
    )
    if mode == "wall_trace_projection" and solver != "matrix_free_cg":
        raise ValueError(
            "numerics.projection.boundary_hodge.solver must be "
            "'matrix_free_cg' for mode='wall_trace_projection'."
        )
    gate = validate_choice(
        str(raw.get("gate", "diagnostic")).strip().lower(),
        _BOUNDARY_HODGE_GATES,
        "numerics.projection.boundary_hodge.gate",
    )
    tolerance = float(raw.get("tolerance", 1.0e-10))
    if tolerance <= 0.0:
        raise ValueError("numerics.projection.boundary_hodge.tolerance must be > 0.")
    max_iterations = int(raw.get("max_iterations", 80))
    if max_iterations <= 0:
        raise ValueError(
            "numerics.projection.boundary_hodge.max_iterations must be positive."
        )
    return {
        "mode": mode,
        "state_space": state_space,
        "wall_trace": wall_trace,
        "wall_retraction": wall_retraction,
        "metric": metric,
        "pressure_pairing": pressure_pairing,
        "solver": solver,
        "tolerance": tolerance,
        "max_iterations": max_iterations,
        "gate": gate,
    }


def build_run_cfg(options: RunCfgBuilderOptions) -> RunCfg:
    """Build `RunCfg` from normalized run-section fragments."""
    snap_raw = options.snapshots.get("times", [])
    if snap_raw is None:
        snap_raw = []

    cfl_raw = options.time_cfg.get("cfl")
    dt_fixed_raw = options.time_cfg.get("dt")
    if cfl_raw is not None and dt_fixed_raw is not None:
        raise ValueError("run.time: 'cfl' and 'dt' are mutually exclusive.")
    cfl_number, cfl_policy, cfl_adv, cfl_cap, cfl_visc = resolve_cfl_policy(cfl_raw)
    boundary_hodge = _parse_boundary_hodge(options.projection)
    face_no_slip_raw = options.projection.get("face_no_slip_boundary_state")
    face_no_slip_boundary_state = (
        boundary_hodge["state_space"] == "constrained_face"
        if face_no_slip_raw is None
        else bool(face_no_slip_raw)
    )
    if boundary_hodge["state_space"] == "constrained_face" and not face_no_slip_boundary_state:
        raise ValueError(
            "numerics.projection.boundary_hodge.state_space='constrained_face' "
            "requires numerics.projection.face_no_slip_boundary_state=true so "
            "the stored face cochain and the nodal no-slip state live in the same "
            "boundary space."
        )

    tracking_redist = tracking_redistance(options.tracking)
    reinit_schedule = options.reinit_schedule
    reinit_trigger_mode = str(
        reinit_schedule.get(
            "mode",
            "fixed" if "every_steps" in reinit_schedule else "adaptive",
        )
    ).strip().lower()
    if reinit_trigger_mode not in {"adaptive", "fixed"}:
        raise ValueError(
            "interface.reinitialization.schedule.mode must be 'adaptive' or 'fixed', "
            f"got {reinit_trigger_mode!r}"
        )
    reinit_threshold = float(
        reinit_schedule.get("threshold", reinit_schedule.get("monitor_threshold", 1.10))
    )
    if reinit_threshold <= 1.0:
        raise ValueError("interface.reinitialization.schedule.threshold must be > 1.0")
    reinit_every = int(reinit_schedule.get("every_steps", 0))
    if options.reinit_method is None and reinit_every != 0:
        raise ValueError(
            "interface.reinitialization.algorithm='none' requires "
            "interface.reinitialization.schedule.every_steps=0"
        )
    reinit_volume_constraint = str(
        options.reinit_profile.get("volume_constraint", "diffuse_mass")
    ).strip().lower().replace("-", "_")
    if reinit_volume_constraint not in {
        "diffuse_mass",
        "psi_mass",
        "sharp_phase_volume",
        "sharp_volume",
        "sharp_area",
    }:
        raise ValueError(
            "interface.reinitialization.profile.volume_constraint must be "
            "'diffuse_mass' or 'sharp_phase_volume', "
            f"got {reinit_volume_constraint!r}"
        )
    cfg = RunCfg(
        T_final=opt_float(options.time_cfg["final"]),
        max_steps=int(options.time_cfg["max_steps"]) if "max_steps" in options.time_cfg else None,
        cfl=cfl_number,
        cfl_policy=cfl_policy,
        cfl_advective=cfl_adv,
        cfl_capillary=cfl_cap,
        cfl_viscous=cfl_visc,
        snap_times=[float(x) for x in snap_raw],
        snap_interval=opt_float(options.snapshots.get("interval")),
        reinit_eps_scale=float(options.reinit_profile.get("eps_scale", 1.0)),
        print_every=int(options.time_cfg.get("print_every", 100)),
        dt_fixed=opt_float(dt_fixed_raw),
        cn_viscous=(
            options.operator_settings["viscous_time_scheme"]
            in {"crank_nicolson", "implicit_bdf2"}
        ),
        reinit_every=reinit_every,
        reinit_trigger_mode=reinit_trigger_mode,
        reinit_threshold=reinit_threshold,
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
        interface_gauge_reconstruction=parse_tracking_gauge_reconstruction(
            options.tracking,
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
        dgr_phi_smooth_C=float(options.reinit_profile.get("dgr_phi_smooth_C", 0.0)),
        ridge_sigma_0=options.ridge_sigma_0,
        reinit_volume_constraint=reinit_volume_constraint,
        advection_scheme=options.operator_settings["advection_scheme"],
        momentum_form=options.operator_settings["momentum_form"],
        convection_scheme=options.operator_settings["convection_scheme"],
        ppe_solver=options.operator_settings["ppe_solver"],
        ppe_dc_base_solver=options.operator_settings["ppe_dc_base_solver"],
        pressure_scheme=options.operator_settings["pressure_scheme"],
        ppe_coefficient_scheme=options.operator_settings["poisson_coefficient"],
        ppe_interface_coupling_scheme=options.operator_settings["poisson_interface_coupling"],
        capillary_range_projection=options.operator_settings["capillary_range_projection"],
        capillary_reaction_projection=options.operator_settings["capillary_reaction_projection"],
        pressure_force_contract=options.operator_settings["pressure_force_contract"],
        scalar_operator_pairing=options.operator_settings["scalar_operator_pairing"],
        pressure_history_mode=options.operator_settings["pressure_history_mode"],
        pressure_history_extrapolation=options.operator_settings[
            "pressure_history_extrapolation"
        ],
        capillary_closed_interface_endpoint=options.operator_settings[
            "capillary_closed_interface_endpoint"
        ],
        capillary_closed_interface_metric=options.operator_settings[
            "capillary_closed_interface_metric"
        ],
        capillary_closed_interface_constraints=options.operator_settings[
            "capillary_closed_interface_constraints"
        ],
        capillary_closed_interface_fail_close=options.operator_settings[
            "capillary_closed_interface_fail_close"
        ],
        surface_tension_scheme=options.operator_settings["surface_tension_scheme"],
        capillary_force_source=options.operator_settings["capillary_force_source"],
        curvature_method=options.operator_settings["curvature_method"],
        convection_time_scheme=options.operator_settings["convection_time_scheme"],
        viscous_spatial_scheme=options.operator_settings["viscous_spatial_scheme"],
        viscous_time_scheme=options.operator_settings["viscous_time_scheme"],
        viscous_solver=options.operator_settings["viscous_solver"],
        viscous_solver_tolerance=options.operator_settings["viscous_solver_tolerance"],
        viscous_solver_max_iterations=options.operator_settings[
            "viscous_solver_max_iterations"
        ],
        viscous_solver_restart=options.operator_settings["viscous_solver_restart"],
        viscous_dc_max_iterations=options.operator_settings["viscous_dc_max_iterations"],
        viscous_dc_relaxation=options.operator_settings["viscous_dc_relaxation"],
        viscous_dc_low_operator=options.operator_settings["viscous_dc_low_operator"],
        cn_mode=options.operator_settings["cn_mode"],
        cn_buoyancy_predictor_assembly_mode=options.operator_settings[
            "cn_buoyancy_predictor_assembly_mode"
        ],
        gravity_formulation=options.operator_settings["gravity_formulation"],
        gravity_transport_adjoint=options.operator_settings[
            "gravity_transport_adjoint"
        ],
        gravity_metric=options.operator_settings["gravity_metric"],
        gravity_hodge_gate=options.operator_settings["gravity_hodge_gate"],
        gravity_work_gate=options.operator_settings["gravity_work_gate"],
        pressure_gradient_scheme=options.operator_settings["pressure_gradient_scheme"],
        surface_tension_gradient_scheme=options.operator_settings["surface_tension_gradient_scheme"],
        momentum_gradient_scheme=options.operator_settings["momentum_gradient_scheme"],
        uccd6_sigma=options.operator_settings["uccd6_sigma"],
        face_flux_projection=bool(options.projection.get("face_flux_projection", False)),
        canonical_face_state=bool(options.projection.get("canonical_face_state", False)),
        face_native_predictor_state=bool(
            options.projection.get("face_native_predictor_state", False)
        ),
        face_no_slip_boundary_state=face_no_slip_boundary_state,
        preserve_projected_faces=bool(
            options.projection.get("preserve_projected_faces", False)
        ),
        boundary_hodge_mode=boundary_hodge["mode"],
        boundary_hodge_state_space=boundary_hodge["state_space"],
        boundary_hodge_wall_trace=boundary_hodge["wall_trace"],
        boundary_hodge_wall_retraction=boundary_hodge["wall_retraction"],
        boundary_hodge_metric=boundary_hodge["metric"],
        boundary_hodge_pressure_pairing=boundary_hodge["pressure_pairing"],
        boundary_hodge_solver=boundary_hodge["solver"],
        boundary_hodge_tolerance=boundary_hodge["tolerance"],
        boundary_hodge_max_iterations=boundary_hodge["max_iterations"],
        boundary_hodge_gate=boundary_hodge["gate"],
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
        ppe_dc_fail_close=options.operator_settings["ppe_dc_fail_close"],
        debug_diagnostics=bool(options.debug.get("step_diagnostics", False)),
    )
    if cfg.gravity_formulation == "variational_potential":
        required_projection_flags = {
            "face_flux_projection": cfg.face_flux_projection,
            "canonical_face_state": cfg.canonical_face_state,
            "face_native_predictor_state": cfg.face_native_predictor_state,
            "preserve_projected_faces": cfg.preserve_projected_faces,
        }
        missing = [name for name, enabled in required_projection_flags.items() if not enabled]
        if missing:
            raise ValueError(
                "numerics.momentum.terms.gravity.formulation='variational_potential' "
                "requires projection flags "
                f"{', '.join(missing)} to be true."
            )
        if cfg.projection_consistent_buoyancy:
            raise ValueError(
                "variational_potential gravity must not be combined with "
                "projection_consistent_buoyancy; both represent buoyancy in "
                "the pressure Hodge space."
            )
    if cfg.boundary_hodge_mode != "off":
        required_projection_flags = {
            "face_flux_projection": cfg.face_flux_projection,
            "canonical_face_state": cfg.canonical_face_state,
            "face_native_predictor_state": cfg.face_native_predictor_state,
            "preserve_projected_faces": cfg.preserve_projected_faces,
        }
        missing = [name for name, enabled in required_projection_flags.items() if not enabled]
        if missing:
            raise ValueError(
                "numerics.projection.boundary_hodge requires projection flags "
                f"{', '.join(missing)} to be true."
            )
    return cfg
