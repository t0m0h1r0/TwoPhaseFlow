"""Contract helpers for PhaseRegion force admission candidates.

Symbol mapping
--------------
``psi`` -> runtime phase chart/gauge evaluated on grid nodes.
``rho`` -> nodal two-phase density ``rho_g + (rho_l-rho_g) psi``.
``M_f`` -> face mass metric built from nodal density.
``T`` -> fixed-stratum transport map ``-D_f(psi_f u_f)``.

This module is a contract helper only.  It does not connect capillary force to
pressure projection, advance velocity, solve nonlinear admission, micro-step,
or run a T/8 path.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from twophase.geometry import AtlasValidationError
from twophase.geometry import CellMeasurePhase
from twophase.geometry import map_cell_measure_to_phase_owner

from .closed_interface_riesz import closed_interface_riesz_cochain
from .closed_interface_riesz import component_reaction_hodge_gate
from .closed_interface_riesz import face_mass_components
from .closed_interface_riesz import fixed_stratum_virtual_work_check
from .closed_interface_riesz import transport_increment_from_face_velocity
from .closed_interface_riesz import weighted_hodge_decomposition
from .closed_interface_stratum import array_to_numpy


@dataclass(frozen=True)
class PhaseRegionFaceMassMetric:
    """Nodal density and face weights for a PhaseRegion force candidate."""

    rho_node: object
    face_weight_components: list[object]
    rho_min: float
    rho_max: float


@dataclass(frozen=True)
class FixedStratumVelocityScale:
    """Scaled face velocity that keeps a finite-difference probe local."""

    face_velocity_components: list[object]
    scale: float
    sign_margin: float
    delta_linf: float
    valid: bool
    reason: str


@dataclass(frozen=True)
class PhaseRegionForceDiagnostics:
    """Optional zero-step work/Hodge diagnostics for a force candidate."""

    valid: bool
    reason: str
    self_velocity: FixedStratumVelocityScale | None
    probe_velocity: FixedStratumVelocityScale | None
    self_work: object | None
    probe_work: object | None
    hodge: object | None
    reaction: object | None
    metrics: dict[str, float]


@dataclass(frozen=True)
class PhaseRegionForceAdmission:
    """Zero-step PhaseRegion force candidate with explicit admission status."""

    valid: bool
    reason: str
    force_admissible: bool
    runtime_steps: int
    owner_map: object | None
    face_metric: PhaseRegionFaceMassMetric | None
    cochain: object | None
    metrics: dict[str, float]
    diagnostics: PhaseRegionForceDiagnostics | None = None


@dataclass(frozen=True)
class PhaseRegionForceAdmissionReport:
    """Stable scalar report for zero-step adapter diagnostics."""

    valid: bool
    reason: str
    force_admissible: bool
    runtime_steps: int
    diagnostics_valid: bool
    complement_used: bool | None
    bc_type: str | None
    grid_alpha: float | None
    min_dx: float | None
    max_dx: float | None
    face_component_shapes: tuple[tuple[int, ...], ...]
    required_metric_keys: tuple[str, ...]
    missing_metric_keys: tuple[str, ...]
    metrics: dict[str, float]


def two_phase_nodal_density(
    *,
    xp,
    psi,
    rho_l: float,
    rho_g: float,
    indicator_tolerance: float = 1.0e-12,
):
    """Return nodal two-phase density from a runtime phase indicator."""
    psi_arr = xp.asarray(psi, dtype=float)
    if psi_arr.ndim != 2:
        raise ValueError("psi must be a 2D nodal array")
    psi_host = array_to_numpy(xp, psi_arr)
    if not np.all(np.isfinite(psi_host)):
        raise ValueError("psi must be finite")
    tol = float(indicator_tolerance)
    if not np.isfinite(tol) or tol < 0.0:
        raise ValueError("indicator_tolerance must be finite and nonnegative")
    if float(np.min(psi_host)) < -tol or float(np.max(psi_host)) > 1.0 + tol:
        raise ValueError("psi must stay within [0, 1] up to indicator_tolerance")
    rho_l_value = float(rho_l)
    rho_g_value = float(rho_g)
    if not np.isfinite(rho_l_value) or not np.isfinite(rho_g_value):
        raise ValueError("rho_l and rho_g must be finite")
    if rho_l_value <= 0.0 or rho_g_value <= 0.0:
        raise ValueError("rho_l and rho_g must be positive")
    return rho_g_value + (rho_l_value - rho_g_value) * psi_arr


def build_phase_region_force_admission_candidate(
    *,
    xp,
    grid,
    fccd,
    psi,
    q_source,
    cell_area,
    source_phase: CellMeasurePhase | int | str,
    owner_phase: CellMeasurePhase | int | str,
    rho_l: float,
    rho_g: float,
    sigma: float,
    capacity_tolerance: float = 1.0e-12,
    runtime_steps: int = 0,
    phase_threshold: float = 0.5,
) -> PhaseRegionForceAdmission:
    """Build a zero-step force candidate without admitting it to runtime use."""
    steps = int(runtime_steps)
    if steps != 0:
        return _invalid_admission("runtime_steps_must_be_zero", steps)
    try:
        owner_map = map_cell_measure_to_phase_owner(
            q_source,
            cell_area,
            source_phase=source_phase,
            owner_phase=owner_phase,
            capacity_tolerance=float(capacity_tolerance),
        )
        face_metric = phase_region_face_mass_metric(
            xp=xp,
            grid=grid,
            psi=psi,
            rho_l=float(rho_l),
            rho_g=float(rho_g),
        )
        cochain = closed_interface_riesz_cochain(
            xp=xp,
            grid=grid,
            psi=psi,
            fccd=fccd,
            sigma=float(sigma),
            face_weight_components=face_metric.face_weight_components,
            phase_threshold=float(phase_threshold),
        )
    except (AtlasValidationError, ValueError, np.linalg.LinAlgError) as exc:
        return _invalid_admission(str(exc), steps)
    metrics = _candidate_metrics(
        xp=xp,
        runtime_steps=steps,
        owner_map=owner_map,
        face_metric=face_metric,
        cochain=cochain,
    )
    return PhaseRegionForceAdmission(
        valid=True,
        reason="ok",
        force_admissible=False,
        runtime_steps=steps,
        owner_map=owner_map,
        face_metric=face_metric,
        cochain=cochain,
        metrics=metrics,
    )


def build_phase_region_force_admission_report(
    *,
    admission: PhaseRegionForceAdmission,
    grid=None,
    compatibility_residual_linf: float | None = None,
    required_metric_keys: tuple[str, ...] = (),
) -> PhaseRegionForceAdmissionReport:
    """Build a fail-closed scalar report for a zero-step force candidate.

    The report is for diagnostics and adapter admission checks only.  It does
    not make the force consumable by a pressure/velocity projection path.
    """
    metrics = dict(admission.metrics)
    if compatibility_residual_linf is not None:
        metrics["compat_linf"] = float(compatibility_residual_linf)
    bc_type = _grid_bc_type(grid)
    grid_alpha = _grid_alpha(grid)
    min_dx, max_dx = _grid_spacing_range(grid)
    if grid_alpha is not None:
        metrics["grid_alpha"] = float(grid_alpha)
    if min_dx is not None:
        metrics["min_dx"] = float(min_dx)
    if max_dx is not None:
        metrics["max_dx"] = float(max_dx)
    face_shapes = _face_component_shapes(admission)
    required = tuple(str(key) for key in required_metric_keys)
    missing = tuple(key for key in required if key not in metrics)
    diagnostics = admission.diagnostics
    diagnostics_valid = bool(diagnostics is not None and diagnostics.valid)
    valid, reason = _report_validity(
        admission=admission,
        diagnostics_valid=diagnostics_valid,
        diagnostics_reason=None if diagnostics is None else diagnostics.reason,
        min_dx=min_dx,
        max_dx=max_dx,
        missing_metric_keys=missing,
    )
    complement_used = None
    if admission.owner_map is not None:
        complement_used = bool(admission.owner_map.complement_used)
    return PhaseRegionForceAdmissionReport(
        valid=bool(valid),
        reason=reason,
        force_admissible=bool(admission.force_admissible),
        runtime_steps=int(admission.runtime_steps),
        diagnostics_valid=diagnostics_valid,
        complement_used=complement_used,
        bc_type=bc_type,
        grid_alpha=grid_alpha,
        min_dx=min_dx,
        max_dx=max_dx,
        face_component_shapes=face_shapes,
        required_metric_keys=required,
        missing_metric_keys=missing,
        metrics=metrics,
    )


def attach_phase_region_force_diagnostics(
    *,
    xp,
    grid,
    fccd,
    div_op,
    admission: PhaseRegionForceAdmission,
    probe_face_velocity_components=None,
    fd_eps: float = 1.0e-7,
    sign_fraction: float = 2.0e-2,
    riesz_tolerance: float = 1.0e-12,
    fd_power_tolerance: float = 1.0e-5,
    divergence_tolerance: float = 1.0e-8,
) -> PhaseRegionForceAdmission:
    """Return ``admission`` with zero-step work/Hodge diagnostics attached."""
    if not admission.valid or admission.cochain is None:
        diagnostics = _invalid_diagnostics("candidate_not_valid")
        return _admission_with_diagnostics(admission, diagnostics)
    cochain = admission.cochain
    self_velocity = scale_face_velocity_to_fixed_stratum(
        xp=xp,
        fccd=fccd,
        psi=cochain.psi,
        face_velocity_components=cochain.surface_acceleration,
        fd_eps=float(fd_eps),
        sign_fraction=float(sign_fraction),
    )
    if not self_velocity.valid:
        diagnostics = _invalid_diagnostics(
            f"self_velocity:{self_velocity.reason}",
            self_velocity=self_velocity,
        )
        return _admission_with_diagnostics(admission, diagnostics)
    self_work = fixed_stratum_virtual_work_check(
        xp=xp,
        grid=grid,
        fccd=fccd,
        cochain=cochain,
        face_velocity_components=self_velocity.face_velocity_components,
        epsilon=float(fd_eps),
    )
    probe_velocity = None
    probe_work = None
    if probe_face_velocity_components is not None:
        probe_velocity = scale_face_velocity_to_fixed_stratum(
            xp=xp,
            fccd=fccd,
            psi=cochain.psi,
            face_velocity_components=probe_face_velocity_components,
            fd_eps=float(fd_eps),
            sign_fraction=float(sign_fraction),
        )
        if not probe_velocity.valid:
            diagnostics = _invalid_diagnostics(
                f"probe_velocity:{probe_velocity.reason}",
                self_velocity=self_velocity,
                self_work=self_work,
                probe_velocity=probe_velocity,
            )
            return _admission_with_diagnostics(admission, diagnostics)
        probe_work = fixed_stratum_virtual_work_check(
            xp=xp,
            grid=grid,
            fccd=fccd,
            cochain=cochain,
            face_velocity_components=probe_velocity.face_velocity_components,
            epsilon=float(fd_eps),
        )
    hodge = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=cochain.surface_acceleration,
        face_weight_components=cochain.face_weight_components,
    )
    reaction = component_reaction_hodge_gate(
        xp=xp,
        div_op=div_op,
        cochain=cochain,
    )
    valid, reason = _diagnostic_validity(
        self_work=self_work,
        probe_work=probe_work,
        hodge=hodge,
        reaction=reaction,
        riesz_tolerance=float(riesz_tolerance),
        fd_power_tolerance=float(fd_power_tolerance),
        divergence_tolerance=float(divergence_tolerance),
    )
    diagnostics = PhaseRegionForceDiagnostics(
        valid=bool(valid),
        reason=reason,
        self_velocity=self_velocity,
        probe_velocity=probe_velocity,
        self_work=self_work,
        probe_work=probe_work,
        hodge=hodge,
        reaction=reaction,
        metrics=_diagnostic_metrics(
            self_velocity=self_velocity,
            probe_velocity=probe_velocity,
            self_work=self_work,
            probe_work=probe_work,
            hodge=hodge,
            reaction=reaction,
            valid=bool(valid),
        ),
    )
    return _admission_with_diagnostics(admission, diagnostics)


def phase_region_face_mass_metric(
    *,
    xp,
    grid,
    psi,
    rho_l: float,
    rho_g: float,
    indicator_tolerance: float = 1.0e-12,
) -> PhaseRegionFaceMassMetric:
    """Build ``M_f`` from runtime nodal ``psi`` without accepting cell density."""
    psi_arr = xp.asarray(psi, dtype=float)
    if tuple(psi_arr.shape) != tuple(grid.shape):
        raise ValueError(
            "psi must have nodal grid shape; cell-density input is not allowed"
        )
    rho_node = two_phase_nodal_density(
        xp=xp,
        psi=psi_arr,
        rho_l=float(rho_l),
        rho_g=float(rho_g),
        indicator_tolerance=float(indicator_tolerance),
    )
    weights = face_mass_components(xp=xp, grid=grid, rho=rho_node)
    rho_host = array_to_numpy(xp, rho_node)
    return PhaseRegionFaceMassMetric(
        rho_node=rho_node,
        face_weight_components=weights,
        rho_min=float(np.min(rho_host)),
        rho_max=float(np.max(rho_host)),
    )


def scale_face_velocity_to_fixed_stratum(
    *,
    xp,
    fccd,
    psi,
    face_velocity_components,
    fd_eps: float,
    sign_fraction: float = 2.0e-2,
    phase_threshold: float = 0.5,
) -> FixedStratumVelocityScale:
    """Scale a virtual face velocity so ``psi +/- eps*T(u)`` remains local."""
    eps = float(fd_eps)
    fraction = float(sign_fraction)
    threshold = float(phase_threshold)
    if not np.isfinite(eps) or eps <= 0.0:
        raise ValueError("fd_eps must be finite and positive")
    if not np.isfinite(fraction) or fraction <= 0.0 or fraction > 1.0:
        raise ValueError("sign_fraction must be in (0, 1]")
    if not np.isfinite(threshold):
        raise ValueError("phase_threshold must be finite")

    psi_arr = xp.asarray(psi, dtype=float)
    psi_host = array_to_numpy(xp, psi_arr)
    sign_margin = float(np.min(np.abs(psi_host - threshold)))
    if sign_margin <= 0.0:
        return FixedStratumVelocityScale(
            face_velocity_components=[
                xp.asarray(component) for component in face_velocity_components
            ],
            scale=0.0,
            sign_margin=sign_margin,
            delta_linf=0.0,
            valid=False,
            reason="zero_sign_margin",
        )

    delta = transport_increment_from_face_velocity(
        xp=xp,
        fccd=fccd,
        psi=psi_arr,
        face_velocity_components=face_velocity_components,
    )
    delta_linf = float(np.max(np.abs(array_to_numpy(xp, delta))))
    if delta_linf <= 0.0:
        return FixedStratumVelocityScale(
            face_velocity_components=[
                xp.asarray(component) for component in face_velocity_components
            ],
            scale=1.0,
            sign_margin=sign_margin,
            delta_linf=0.0,
            valid=True,
            reason="zero_transport_increment",
        )
    scale = min(1.0, fraction * sign_margin / (eps * delta_linf))
    return FixedStratumVelocityScale(
        face_velocity_components=[
            float(scale) * xp.asarray(component) for component in face_velocity_components
        ],
        scale=float(scale),
        sign_margin=sign_margin,
        delta_linf=delta_linf,
        valid=True,
        reason="ok",
    )


def _invalid_admission(reason: str, runtime_steps: int) -> PhaseRegionForceAdmission:
    return PhaseRegionForceAdmission(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        runtime_steps=int(runtime_steps),
        owner_map=None,
        face_metric=None,
        cochain=None,
        metrics={
            "runtime_steps": float(runtime_steps),
            "force_admissible": 0.0,
            "valid": 0.0,
        },
    )


def _invalid_diagnostics(
    reason: str,
    *,
    self_velocity=None,
    probe_velocity=None,
    self_work=None,
    probe_work=None,
) -> PhaseRegionForceDiagnostics:
    return PhaseRegionForceDiagnostics(
        valid=False,
        reason=str(reason),
        self_velocity=self_velocity,
        probe_velocity=probe_velocity,
        self_work=self_work,
        probe_work=probe_work,
        hodge=None,
        reaction=None,
        metrics={
            "diagnostics_valid": 0.0,
            "force_admissible": 0.0,
        },
    )


def _admission_with_diagnostics(
    admission: PhaseRegionForceAdmission,
    diagnostics: PhaseRegionForceDiagnostics,
) -> PhaseRegionForceAdmission:
    metrics = dict(admission.metrics)
    metrics.update(diagnostics.metrics)
    return PhaseRegionForceAdmission(
        valid=admission.valid,
        reason=admission.reason,
        force_admissible=False,
        runtime_steps=admission.runtime_steps,
        owner_map=admission.owner_map,
        face_metric=admission.face_metric,
        cochain=admission.cochain,
        metrics=metrics,
        diagnostics=diagnostics,
    )


def _diagnostic_validity(
    *,
    self_work,
    probe_work,
    hodge,
    reaction,
    riesz_tolerance: float,
    fd_power_tolerance: float,
    divergence_tolerance: float,
) -> tuple[bool, str]:
    if not self_work.valid:
        return False, f"self_work:{self_work.reason}"
    if self_work.riesz_residual > riesz_tolerance:
        return False, "self_riesz_residual"
    if self_work.finite_difference_power_residual > fd_power_tolerance:
        return False, "self_fd_power_residual"
    if probe_work is not None:
        if not probe_work.valid:
            return False, f"probe_work:{probe_work.reason}"
        if probe_work.riesz_residual > riesz_tolerance:
            return False, "probe_riesz_residual"
        if probe_work.finite_difference_power_residual > fd_power_tolerance:
            return False, "probe_fd_power_residual"
    if hodge.hodge_divergence_linf > divergence_tolerance:
        return False, "hodge_divergence_linf"
    if reaction.residual_divergence_linf > divergence_tolerance:
        return False, "reaction_residual_divergence_linf"
    return True, "ok"


def _diagnostic_metrics(
    *,
    self_velocity,
    probe_velocity,
    self_work,
    probe_work,
    hodge,
    reaction,
    valid: bool,
) -> dict[str, float]:
    metrics = {
        "diagnostics_valid": float(valid),
        "force_admissible": 0.0,
        "stratum_sign_margin": float(self_velocity.sign_margin),
        "self_velocity_scale": float(self_velocity.scale),
        "self_velocity_delta_linf": float(self_velocity.delta_linf),
        "self_fd_power_residual": float(
            self_work.finite_difference_power_residual
        ),
        "self_riesz_residual": float(self_work.riesz_residual),
        "self_finite_difference": float(self_work.finite_difference),
        "self_capillary_power": float(self_work.capillary_power),
        "component_weighted_l2": float(hodge.component_weighted_l2),
        "range_weighted_l2": float(hodge.range_weighted_l2),
        "hodge_weighted_l2": float(hodge.hodge_weighted_l2),
        "hodge_divergence_linf": float(hodge.hodge_divergence_linf),
        "reaction_beta": float(reaction.beta),
        "reaction_residual_weighted_l2": float(reaction.residual_weighted_l2),
        "reaction_residual_ratio": float(reaction.residual_ratio),
        "reaction_residual_divergence_linf": float(
            reaction.residual_divergence_linf
        ),
    }
    if probe_velocity is not None and probe_work is not None:
        metrics.update(
            {
                "probe_velocity_scale": float(probe_velocity.scale),
                "probe_velocity_delta_linf": float(probe_velocity.delta_linf),
                "probe_fd_power_residual": float(
                    probe_work.finite_difference_power_residual
                ),
                "probe_riesz_residual": float(probe_work.riesz_residual),
                "probe_finite_difference": float(probe_work.finite_difference),
                "probe_capillary_power": float(probe_work.capillary_power),
            }
        )
    return metrics


def _candidate_metrics(
    *,
    xp,
    runtime_steps: int,
    owner_map,
    face_metric: PhaseRegionFaceMassMetric,
    cochain,
) -> dict[str, float]:
    weights = [
        array_to_numpy(xp, component)
        for component in face_metric.face_weight_components
    ]
    weight_min = min(float(np.min(component)) for component in weights)
    weight_max = max(float(np.max(component)) for component in weights)
    return {
        "runtime_steps": float(runtime_steps),
        "force_admissible": 0.0,
        "valid": 1.0,
        "complement_used": float(owner_map.complement_used),
        "source_volume": float(owner_map.source_volume),
        "owner_volume": float(owner_map.owner_volume),
        "rho_min": float(face_metric.rho_min),
        "rho_max": float(face_metric.rho_max),
        "face_weight_min": weight_min,
        "face_weight_max": weight_max,
        "phase_threshold": float(cochain.phase_threshold),
        "sigma": float(cochain.sigma),
    }


def _report_validity(
    *,
    admission: PhaseRegionForceAdmission,
    diagnostics_valid: bool,
    diagnostics_reason: str | None,
    min_dx: float | None,
    max_dx: float | None,
    missing_metric_keys: tuple[str, ...],
) -> tuple[bool, str]:
    if not admission.valid:
        return False, f"candidate:{admission.reason}"
    if admission.force_admissible:
        return False, "force_admissible_true"
    if admission.runtime_steps != 0:
        return False, "runtime_steps_must_be_zero"
    if not diagnostics_valid:
        if diagnostics_reason is None:
            return False, "diagnostics_missing"
        return False, f"diagnostics:{diagnostics_reason}"
    if min_dx is not None:
        if not np.isfinite(min_dx) or not np.isfinite(max_dx) or min_dx <= 0.0:
            return False, "grid_spacing_invalid"
    if missing_metric_keys:
        return False, "missing_metrics:" + ",".join(missing_metric_keys)
    return True, "ok"


def _face_component_shapes(
    admission: PhaseRegionForceAdmission,
) -> tuple[tuple[int, ...], ...]:
    if admission.cochain is not None:
        return tuple(
            tuple(int(axis) for axis in component.shape)
            for component in admission.cochain.surface_acceleration
        )
    if admission.face_metric is not None:
        return tuple(
            tuple(int(axis) for axis in component.shape)
            for component in admission.face_metric.face_weight_components
        )
    return ()


def _grid_bc_type(grid) -> str | None:
    if grid is None:
        return None
    return str(getattr(grid, "bc_type", "unknown"))


def _grid_alpha(grid) -> float | None:
    if grid is None:
        return None
    config = getattr(grid, "_gc", None)
    if config is None or not hasattr(config, "alpha_grid"):
        return None
    return float(config.alpha_grid)


def _grid_spacing_range(grid) -> tuple[float | None, float | None]:
    if grid is None:
        return None, None
    widths = [
        np.diff(np.asarray(coords, dtype=float))
        for coords in getattr(grid, "coords", ())
    ]
    if not widths:
        return None, None
    min_dx = min(float(np.min(axis_widths)) for axis_widths in widths)
    max_dx = max(float(np.max(axis_widths)) for axis_widths in widths)
    return min_dx, max_dx
