"""Diagnostic gates for PhaseRegion pressure/velocity face-space coupling.

Symbol mapping
--------------
``s_f`` -> PhaseRegion capillary face acceleration cochain.
``u_f`` -> runtime FCCD face velocity.
``p_f`` -> pressure reaction faces.
``M_f`` -> PhaseRegion face mass metric.

The helpers in this module are zero-step diagnostics only.  G4 may expose
``s_f`` as a face payload for a later explicit consumer, but this module does
not connect it to runtime projection or advance a velocity field.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from twophase.coupling.phase_region_force_admission import (
    PhaseRegionForceAdapterDecision,
    PhaseRegionForceAdmission,
)
from twophase.coupling.closed_interface_riesz import (
    fixed_stratum_virtual_work_check,
    weighted_hodge_decomposition,
)
from twophase.coupling.closed_interface_stratum import array_to_numpy

from .face_boundary import (
    apply_direct_face_boundary_space,
    normalise_boundary_face_space,
)
from .face_projection import apply_pressure_projection


@dataclass(frozen=True)
class PhaseRegionPressureVelocityG0Report:
    """Shape/boundary/metric report before pressure-velocity work or projection."""

    valid: bool
    reason: str
    force_admissible: bool
    bc_type: str
    boundary_face_space: str
    surface_face_shapes: tuple[tuple[int, ...], ...]
    velocity_face_shapes: tuple[tuple[int, ...], ...]
    pressure_face_shapes: tuple[tuple[int, ...], ...]
    metric_face_shapes: tuple[tuple[int, ...], ...]
    boundary_residual_linf: float
    surface_velocity_work: float
    pressure_velocity_work: float
    surface_weighted_l2: float
    velocity_weighted_l2: float
    pressure_weighted_l2: float
    metrics: dict[str, float]


@dataclass(frozen=True)
class PhaseRegionPressureVelocityG1Report:
    """Pressure-range report under the same face metric as G0."""

    valid: bool
    reason: str
    force_admissible: bool
    pressure_hodge_weighted_l2: float
    pressure_range_weighted_l2: float
    pressure_component_weighted_l2: float
    pressure_hodge_ratio: float
    pressure_hodge_divergence_linf: float
    surface_hodge_weighted_l2: float
    surface_range_weighted_l2: float
    surface_component_weighted_l2: float
    surface_hodge_ratio: float
    surface_hodge_divergence_linf: float
    metrics: dict[str, float]


@dataclass(frozen=True)
class PhaseRegionPressureVelocityG2Report:
    """Virtual-work report under the same face metric as G0/G1."""

    valid: bool
    reason: str
    force_admissible: bool
    finite_difference: float
    capillary_power: float
    pressure_velocity_work: float
    work_closure_residual: float
    riesz_residual: float
    same_weight_surface_work_residual: float
    pressure_work_finite: bool
    metrics: dict[str, float]


@dataclass(frozen=True)
class PhaseRegionPressureVelocityG3Report:
    """Explicit face-projection oracle report."""

    valid: bool
    reason: str
    force_admissible: bool
    dt: float
    projected_face_shapes: tuple[tuple[int, ...], ...]
    projection_identity_linf: float
    pressure_update_weighted_l2: float
    surface_update_weighted_l2: float
    projected_weighted_l2: float
    metrics: dict[str, float]


@dataclass(frozen=True)
class PhaseRegionPressureVelocityG4Report:
    """Final face-force exposure decision after G0--G3."""

    valid: bool
    reason: str
    force_admissible: bool
    withheld_force_reason: str
    face_force_components: tuple[object, ...] | None
    face_force_shapes: tuple[tuple[int, ...], ...]
    face_force_weighted_l2: float
    surface_update_consistency_residual: float
    metrics: dict[str, float]


@dataclass(frozen=True)
class PhaseRegionPressureVelocityG5Report:
    """Zero-step consumer probe for an admitted face force."""

    valid: bool
    reason: str
    force_admissible: bool
    projected_face_components: tuple[object, ...] | None
    projected_face_shapes: tuple[tuple[int, ...], ...]
    projection_identity_linf: float
    projected_weighted_l2: float
    metrics: dict[str, float]


def build_phase_region_pressure_velocity_g0_report(
    *,
    xp,
    admission: PhaseRegionForceAdmission,
    decision: PhaseRegionForceAdapterDecision,
    runtime_face_velocity_components,
    pressure_face_components,
    bc_type: str | None = None,
    boundary_face_space: str | None = "full_face",
    boundary_tolerance: float = 0.0,
) -> PhaseRegionPressureVelocityG0Report:
    """Check that PhaseRegion ``s_f`` already lives in the runtime face space.

    Equation -> Discretization -> Code:
    ``s_f=-M_f^{-1}T_h^*dE_h`` is provided by ``admission.cochain``;
    ``u_f`` and ``p_f`` are caller-supplied runtime face arrays; all scalar
    products use ``admission.face_metric.face_weight_components``.
    """
    space = normalise_boundary_face_space(boundary_face_space)
    bc_value = str(
        bc_type
        if bc_type is not None
        else decision.report.bc_type
        if decision.report.bc_type is not None
        else "unknown"
    )
    tol = float(boundary_tolerance)
    if not np.isfinite(tol) or tol < 0.0:
        return _invalid_g0_report(
            reason="boundary_tolerance_invalid",
            bc_type=bc_value,
            boundary_face_space=space,
        )
    if not decision.valid:
        return _invalid_g0_report(
            reason=f"decision:{decision.reason}",
            bc_type=bc_value,
            boundary_face_space=space,
        )
    if not admission.valid:
        return _invalid_g0_report(
            reason=f"candidate:{admission.reason}",
            bc_type=bc_value,
            boundary_face_space=space,
        )
    if admission.force_admissible or decision.force_admissible:
        return _invalid_g0_report(
            reason="force_admissible_true",
            bc_type=bc_value,
            boundary_face_space=space,
        )
    if admission.cochain is None or admission.face_metric is None:
        return _invalid_g0_report(
            reason="missing_face_cochain_or_metric",
            bc_type=bc_value,
            boundary_face_space=space,
        )

    surface_faces = [xp.asarray(face) for face in admission.cochain.surface_acceleration]
    velocity_faces = [xp.asarray(face) for face in runtime_face_velocity_components]
    pressure_faces = [xp.asarray(face) for face in pressure_face_components]
    weights = [xp.asarray(weight) for weight in admission.face_metric.face_weight_components]

    surface_shapes = _component_shapes(surface_faces)
    velocity_shapes = _component_shapes(velocity_faces)
    pressure_shapes = _component_shapes(pressure_faces)
    metric_shapes = _component_shapes(weights)
    valid, reason = _g0_shape_validity(
        surface_shapes=surface_shapes,
        velocity_shapes=velocity_shapes,
        pressure_shapes=pressure_shapes,
        metric_shapes=metric_shapes,
    )
    if not valid:
        return _invalid_g0_report(
            reason=reason,
            bc_type=bc_value,
            boundary_face_space=space,
            surface_face_shapes=surface_shapes,
            velocity_face_shapes=velocity_shapes,
            pressure_face_shapes=pressure_shapes,
            metric_face_shapes=metric_shapes,
        )

    weight_min = min(_component_min(xp, weight) for weight in weights)
    if not np.isfinite(weight_min) or weight_min <= 0.0:
        return _invalid_g0_report(
            reason="metric_weight_nonpositive",
            bc_type=bc_value,
            boundary_face_space=space,
            surface_face_shapes=surface_shapes,
            velocity_face_shapes=velocity_shapes,
            pressure_face_shapes=pressure_shapes,
            metric_face_shapes=metric_shapes,
        )

    bounded_surface = apply_direct_face_boundary_space(
        surface_faces,
        xp=xp,
        bc_type=bc_value,
        boundary_face_space=space,
    )
    boundary_residual = _component_linf_difference(
        xp,
        bounded_surface,
        surface_faces,
    )
    if boundary_residual > tol:
        return _invalid_g0_report(
            reason="surface_face_boundary_space_mismatch",
            bc_type=bc_value,
            boundary_face_space=space,
            surface_face_shapes=surface_shapes,
            velocity_face_shapes=velocity_shapes,
            pressure_face_shapes=pressure_shapes,
            metric_face_shapes=metric_shapes,
            boundary_residual_linf=boundary_residual,
        )

    surface_velocity_work = _weighted_dot(xp, surface_faces, velocity_faces, weights)
    pressure_velocity_work = _weighted_dot(xp, pressure_faces, velocity_faces, weights)
    surface_l2 = _weighted_l2(xp, surface_faces, weights)
    velocity_l2 = _weighted_l2(xp, velocity_faces, weights)
    pressure_l2 = _weighted_l2(xp, pressure_faces, weights)
    metrics = {
        "g0_valid": 1.0,
        "force_admissible": 0.0,
        "boundary_residual_linf": float(boundary_residual),
        "surface_velocity_work": float(surface_velocity_work),
        "pressure_velocity_work": float(pressure_velocity_work),
        "surface_weighted_l2": float(surface_l2),
        "velocity_weighted_l2": float(velocity_l2),
        "pressure_weighted_l2": float(pressure_l2),
        "face_component_count": float(len(surface_shapes)),
        "metric_weight_min": float(weight_min),
    }
    return PhaseRegionPressureVelocityG0Report(
        valid=True,
        reason="ok",
        force_admissible=False,
        bc_type=bc_value,
        boundary_face_space=space,
        surface_face_shapes=surface_shapes,
        velocity_face_shapes=velocity_shapes,
        pressure_face_shapes=pressure_shapes,
        metric_face_shapes=metric_shapes,
        boundary_residual_linf=float(boundary_residual),
        surface_velocity_work=float(surface_velocity_work),
        pressure_velocity_work=float(pressure_velocity_work),
        surface_weighted_l2=float(surface_l2),
        velocity_weighted_l2=float(velocity_l2),
        pressure_weighted_l2=float(pressure_l2),
        metrics=metrics,
    )


def build_phase_region_pressure_velocity_g1_report(
    *,
    xp,
    div_op,
    admission: PhaseRegionForceAdmission,
    g0_report: PhaseRegionPressureVelocityG0Report,
    pressure_face_components,
    pressure_hodge_tolerance: float = 1.0e-10,
    divergence_tolerance: float = 1.0e-8,
) -> PhaseRegionPressureVelocityG1Report:
    """Check that pressure faces are in ``range(M_f^{-1}D_f^T)``.

    The capillary surface cochain is decomposed with the same ``D_f`` and
    ``M_f`` only as a diagnostic; its Hodge component is not modified or
    projected into the pressure range.
    """
    if not g0_report.valid:
        return _invalid_g1_report(reason=f"g0:{g0_report.reason}")
    if not admission.valid or admission.cochain is None or admission.face_metric is None:
        return _invalid_g1_report(reason=f"candidate:{admission.reason}")
    if admission.force_admissible or g0_report.force_admissible:
        return _invalid_g1_report(reason="force_admissible_true")
    hodge_tol = float(pressure_hodge_tolerance)
    div_tol = float(divergence_tolerance)
    if not np.isfinite(hodge_tol) or hodge_tol < 0.0:
        return _invalid_g1_report(reason="pressure_hodge_tolerance_invalid")
    if not np.isfinite(div_tol) or div_tol < 0.0:
        return _invalid_g1_report(reason="divergence_tolerance_invalid")

    weights = admission.face_metric.face_weight_components
    pressure_hodge = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=pressure_face_components,
        face_weight_components=weights,
    )
    surface_hodge = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=admission.cochain.surface_acceleration,
        face_weight_components=weights,
    )
    pressure_ratio = pressure_hodge.hodge_weighted_l2 / max(
        pressure_hodge.component_weighted_l2,
        1.0e-30,
    )
    surface_ratio = surface_hodge.hodge_weighted_l2 / max(
        surface_hodge.component_weighted_l2,
        1.0e-30,
    )
    valid = True
    reason = "ok"
    if pressure_hodge.hodge_weighted_l2 > hodge_tol:
        valid = False
        reason = "pressure_hodge_weighted_l2"
    elif pressure_hodge.hodge_divergence_linf > div_tol:
        valid = False
        reason = "pressure_hodge_divergence_linf"
    metrics = {
        "g1_valid": float(valid),
        "force_admissible": 0.0,
        "pressure_hodge_weighted_l2": float(pressure_hodge.hodge_weighted_l2),
        "pressure_range_weighted_l2": float(pressure_hodge.range_weighted_l2),
        "pressure_component_weighted_l2": float(
            pressure_hodge.component_weighted_l2
        ),
        "pressure_hodge_ratio": float(pressure_ratio),
        "pressure_hodge_divergence_linf": float(
            pressure_hodge.hodge_divergence_linf
        ),
        "surface_hodge_weighted_l2": float(surface_hodge.hodge_weighted_l2),
        "surface_range_weighted_l2": float(surface_hodge.range_weighted_l2),
        "surface_component_weighted_l2": float(
            surface_hodge.component_weighted_l2
        ),
        "surface_hodge_ratio": float(surface_ratio),
        "surface_hodge_divergence_linf": float(
            surface_hodge.hodge_divergence_linf
        ),
    }
    return PhaseRegionPressureVelocityG1Report(
        valid=bool(valid),
        reason=reason,
        force_admissible=False,
        pressure_hodge_weighted_l2=float(pressure_hodge.hodge_weighted_l2),
        pressure_range_weighted_l2=float(pressure_hodge.range_weighted_l2),
        pressure_component_weighted_l2=float(pressure_hodge.component_weighted_l2),
        pressure_hodge_ratio=float(pressure_ratio),
        pressure_hodge_divergence_linf=float(pressure_hodge.hodge_divergence_linf),
        surface_hodge_weighted_l2=float(surface_hodge.hodge_weighted_l2),
        surface_range_weighted_l2=float(surface_hodge.range_weighted_l2),
        surface_component_weighted_l2=float(surface_hodge.component_weighted_l2),
        surface_hodge_ratio=float(surface_ratio),
        surface_hodge_divergence_linf=float(surface_hodge.hodge_divergence_linf),
        metrics=metrics,
    )


def build_phase_region_pressure_velocity_g2_report(
    *,
    xp,
    grid,
    fccd,
    admission: PhaseRegionForceAdmission,
    g0_report: PhaseRegionPressureVelocityG0Report,
    g1_report: PhaseRegionPressureVelocityG1Report,
    runtime_face_velocity_components,
    fd_eps: float = 1.0e-7,
    fd_power_tolerance: float = 1.0e-5,
    riesz_tolerance: float = 1.0e-12,
    same_weight_tolerance: float = 1.0e-12,
) -> PhaseRegionPressureVelocityG2Report:
    """Check ``dE[T_h(u_f)] + <s_f,u_f>_M = 0`` for admitted faces."""
    if not g0_report.valid:
        return _invalid_g2_report(reason=f"g0:{g0_report.reason}")
    if not g1_report.valid:
        return _invalid_g2_report(reason=f"g1:{g1_report.reason}")
    if not admission.valid or admission.cochain is None:
        return _invalid_g2_report(reason=f"candidate:{admission.reason}")
    if (
        admission.force_admissible
        or g0_report.force_admissible
        or g1_report.force_admissible
    ):
        return _invalid_g2_report(reason="force_admissible_true")
    fd_tol = float(fd_power_tolerance)
    rz_tol = float(riesz_tolerance)
    same_tol = float(same_weight_tolerance)
    eps = float(fd_eps)
    if not np.isfinite(eps) or eps <= 0.0:
        return _invalid_g2_report(reason="fd_eps_invalid")
    if not np.isfinite(fd_tol) or fd_tol < 0.0:
        return _invalid_g2_report(reason="fd_power_tolerance_invalid")
    if not np.isfinite(rz_tol) or rz_tol < 0.0:
        return _invalid_g2_report(reason="riesz_tolerance_invalid")
    if not np.isfinite(same_tol) or same_tol < 0.0:
        return _invalid_g2_report(reason="same_weight_tolerance_invalid")

    work = fixed_stratum_virtual_work_check(
        xp=xp,
        grid=grid,
        fccd=fccd,
        cochain=admission.cochain,
        face_velocity_components=runtime_face_velocity_components,
        epsilon=eps,
    )
    if not work.valid:
        return _invalid_g2_report(reason=f"virtual_work:{work.reason}")

    same_weight_residual = _relative_residual(
        float(g0_report.surface_velocity_work),
        float(work.capillary_power),
    )
    pressure_work_finite = bool(np.isfinite(float(g0_report.pressure_velocity_work)))
    valid = True
    reason = "ok"
    if work.finite_difference_power_residual > fd_tol:
        valid = False
        reason = "work_closure_residual"
    elif work.riesz_residual > rz_tol:
        valid = False
        reason = "riesz_residual"
    elif same_weight_residual > same_tol:
        valid = False
        reason = "same_weight_surface_work_residual"
    elif not pressure_work_finite:
        valid = False
        reason = "pressure_velocity_work_not_finite"

    metrics = {
        "g2_valid": float(valid),
        "force_admissible": 0.0,
        "finite_difference": float(work.finite_difference),
        "capillary_power": float(work.capillary_power),
        "pressure_velocity_work": float(g0_report.pressure_velocity_work),
        "work_closure_residual": float(work.finite_difference_power_residual),
        "riesz_residual": float(work.riesz_residual),
        "same_weight_surface_work_residual": float(same_weight_residual),
        "pressure_work_finite": float(pressure_work_finite),
    }
    return PhaseRegionPressureVelocityG2Report(
        valid=bool(valid),
        reason=reason,
        force_admissible=False,
        finite_difference=float(work.finite_difference),
        capillary_power=float(work.capillary_power),
        pressure_velocity_work=float(g0_report.pressure_velocity_work),
        work_closure_residual=float(work.finite_difference_power_residual),
        riesz_residual=float(work.riesz_residual),
        same_weight_surface_work_residual=float(same_weight_residual),
        pressure_work_finite=pressure_work_finite,
        metrics=metrics,
    )


def build_phase_region_pressure_velocity_g3_report(
    *,
    xp,
    admission: PhaseRegionForceAdmission,
    g0_report: PhaseRegionPressureVelocityG0Report,
    g1_report: PhaseRegionPressureVelocityG1Report,
    g2_report: PhaseRegionPressureVelocityG2Report,
    runtime_face_velocity_components,
    pressure_face_components,
    dt: float,
    projection_tolerance: float = 1.0e-12,
) -> PhaseRegionPressureVelocityG3Report:
    """Call the explicit face-array projection oracle without runtime admission."""
    if not g0_report.valid:
        return _invalid_g3_report(reason=f"g0:{g0_report.reason}")
    if not g1_report.valid:
        return _invalid_g3_report(reason=f"g1:{g1_report.reason}")
    if not g2_report.valid:
        return _invalid_g3_report(reason=f"g2:{g2_report.reason}")
    if not admission.valid or admission.cochain is None or admission.face_metric is None:
        return _invalid_g3_report(reason=f"candidate:{admission.reason}")
    if (
        admission.force_admissible
        or g0_report.force_admissible
        or g1_report.force_admissible
        or g2_report.force_admissible
    ):
        return _invalid_g3_report(reason="force_admissible_true")
    dt_value = float(dt)
    tol = float(projection_tolerance)
    if not np.isfinite(dt_value) or dt_value <= 0.0:
        return _invalid_g3_report(reason="dt_invalid")
    if not np.isfinite(tol) or tol < 0.0:
        return _invalid_g3_report(reason="projection_tolerance_invalid")

    velocity_faces = [xp.asarray(face) for face in runtime_face_velocity_components]
    pressure_faces = [xp.asarray(face) for face in pressure_face_components]
    surface_faces = [xp.asarray(face) for face in admission.cochain.surface_acceleration]
    weights = [xp.asarray(weight) for weight in admission.face_metric.face_weight_components]
    expected_shapes = tuple(g0_report.surface_face_shapes)
    velocity_shapes = _component_shapes(velocity_faces)
    pressure_shapes = _component_shapes(pressure_faces)
    surface_shapes = _component_shapes(surface_faces)
    metric_shapes = _component_shapes(weights)
    valid, reason = _g0_shape_validity(
        surface_shapes=surface_shapes,
        velocity_shapes=velocity_shapes,
        pressure_shapes=pressure_shapes,
        metric_shapes=metric_shapes,
    )
    if not valid:
        return _invalid_g3_report(reason=reason)
    if surface_shapes != expected_shapes:
        return _invalid_g3_report(reason="g0_face_shape_mismatch")

    projected_faces = apply_pressure_projection(
        velocity_faces,
        pressure_faces,
        surface_faces,
        dt_value,
    )
    projected_shapes = _component_shapes(projected_faces)
    balance = [
        xp.asarray(projected)
        - xp.asarray(velocity)
        + dt_value * xp.asarray(pressure)
        - dt_value * xp.asarray(surface)
        for projected, velocity, pressure, surface in zip(
            projected_faces,
            velocity_faces,
            pressure_faces,
            surface_faces,
        )
    ]
    identity_linf = _component_linf(xp, balance)
    pressure_update = [-dt_value * xp.asarray(face) for face in pressure_faces]
    surface_update = [dt_value * xp.asarray(face) for face in surface_faces]
    valid = bool(identity_linf <= tol)
    reason = "ok" if valid else "projection_identity_linf"
    metrics = {
        "g3_valid": float(valid),
        "force_admissible": 0.0,
        "dt": float(dt_value),
        "projection_identity_linf": float(identity_linf),
        "pressure_update_weighted_l2": _weighted_l2(xp, pressure_update, weights),
        "surface_update_weighted_l2": _weighted_l2(xp, surface_update, weights),
        "projected_weighted_l2": _weighted_l2(xp, projected_faces, weights),
    }
    return PhaseRegionPressureVelocityG3Report(
        valid=valid,
        reason=reason,
        force_admissible=False,
        dt=float(dt_value),
        projected_face_shapes=projected_shapes,
        projection_identity_linf=float(identity_linf),
        pressure_update_weighted_l2=metrics["pressure_update_weighted_l2"],
        surface_update_weighted_l2=metrics["surface_update_weighted_l2"],
        projected_weighted_l2=metrics["projected_weighted_l2"],
        metrics=metrics,
    )


def build_phase_region_pressure_velocity_g4_report(
    *,
    xp,
    admission: PhaseRegionForceAdmission,
    adapter_decision: PhaseRegionForceAdapterDecision,
    g0_report: PhaseRegionPressureVelocityG0Report,
    g1_report: PhaseRegionPressureVelocityG1Report,
    g2_report: PhaseRegionPressureVelocityG2Report,
    g3_report: PhaseRegionPressureVelocityG3Report,
    boundary_tolerance: float = 0.0,
    pressure_hodge_tolerance: float = 1.0e-10,
    work_closure_tolerance: float = 1.0e-5,
    same_weight_tolerance: float = 1.0e-12,
    projection_tolerance: float = 1.0e-12,
    surface_update_consistency_tolerance: float = 1.0e-12,
) -> PhaseRegionPressureVelocityG4Report:
    """Expose only the admitted face cochain, never nodal force components."""
    if not adapter_decision.valid:
        return _invalid_g4_report(reason=f"adapter:{adapter_decision.reason}")
    if adapter_decision.force_admissible:
        return _invalid_g4_report(reason="adapter_force_admissible_true")
    if adapter_decision.withheld_force_reason != "pressure_velocity_work_gate_missing":
        return _invalid_g4_report(reason="adapter_withheld_force_reason")
    if not g0_report.valid:
        return _invalid_g4_report(reason=f"g0:{g0_report.reason}")
    if not g1_report.valid:
        return _invalid_g4_report(reason=f"g1:{g1_report.reason}")
    if not g2_report.valid:
        return _invalid_g4_report(reason=f"g2:{g2_report.reason}")
    if not g3_report.valid:
        return _invalid_g4_report(reason=f"g3:{g3_report.reason}")
    if not admission.valid or admission.cochain is None or admission.face_metric is None:
        return _invalid_g4_report(reason=f"candidate:{admission.reason}")
    if (
        admission.force_admissible
        or g0_report.force_admissible
        or g1_report.force_admissible
        or g2_report.force_admissible
        or g3_report.force_admissible
    ):
        return _invalid_g4_report(reason="pre_gate_force_admissible_true")

    tolerances = {
        "boundary_tolerance": float(boundary_tolerance),
        "pressure_hodge_tolerance": float(pressure_hodge_tolerance),
        "work_closure_tolerance": float(work_closure_tolerance),
        "same_weight_tolerance": float(same_weight_tolerance),
        "projection_tolerance": float(projection_tolerance),
        "surface_update_consistency_tolerance": float(
            surface_update_consistency_tolerance
        ),
    }
    for name, value in tolerances.items():
        if not np.isfinite(value) or value < 0.0:
            return _invalid_g4_report(reason=f"{name}_invalid")

    face_force = tuple(
        xp.asarray(component).copy()
        for component in admission.cochain.surface_acceleration
    )
    weights = [
        xp.asarray(weight) for weight in admission.face_metric.face_weight_components
    ]
    face_force_shapes = _component_shapes(face_force)
    if face_force_shapes != tuple(g0_report.surface_face_shapes):
        return _invalid_g4_report(reason="g0_face_shape_mismatch")
    if face_force_shapes != tuple(g3_report.projected_face_shapes):
        return _invalid_g4_report(reason="g3_face_shape_mismatch")
    if face_force_shapes != _component_shapes(weights):
        return _invalid_g4_report(reason="metric_face_shape_mismatch")

    face_force_l2 = _weighted_l2(xp, face_force, weights)
    surface_update_residual = _relative_residual(
        float(g3_report.surface_update_weighted_l2),
        float(g3_report.dt) * float(face_force_l2),
    )
    if g0_report.boundary_residual_linf > tolerances["boundary_tolerance"]:
        return _invalid_g4_report(reason="boundary_residual_linf")
    if g1_report.pressure_hodge_weighted_l2 > tolerances["pressure_hodge_tolerance"]:
        return _invalid_g4_report(reason="pressure_hodge_weighted_l2")
    if g2_report.work_closure_residual > tolerances["work_closure_tolerance"]:
        return _invalid_g4_report(reason="work_closure_residual")
    if g2_report.same_weight_surface_work_residual > tolerances["same_weight_tolerance"]:
        return _invalid_g4_report(reason="same_weight_surface_work_residual")
    if g3_report.projection_identity_linf > tolerances["projection_tolerance"]:
        return _invalid_g4_report(reason="projection_identity_linf")
    if surface_update_residual > tolerances["surface_update_consistency_tolerance"]:
        return _invalid_g4_report(reason="surface_update_consistency_residual")

    metrics = {
        "g4_valid": 1.0,
        "force_admissible": 1.0,
        "face_force_exposed": 1.0,
        "face_force_component_count": float(len(face_force_shapes)),
        "face_force_weighted_l2": float(face_force_l2),
        "surface_update_consistency_residual": float(surface_update_residual),
        "final_boundary_residual_linf": float(g0_report.boundary_residual_linf),
        "final_pressure_hodge_weighted_l2": float(
            g1_report.pressure_hodge_weighted_l2
        ),
        "final_work_closure_residual": float(g2_report.work_closure_residual),
        "final_projection_identity_linf": float(g3_report.projection_identity_linf),
    }
    return PhaseRegionPressureVelocityG4Report(
        valid=True,
        reason="ok",
        force_admissible=True,
        withheld_force_reason="",
        face_force_components=face_force,
        face_force_shapes=face_force_shapes,
        face_force_weighted_l2=float(face_force_l2),
        surface_update_consistency_residual=float(surface_update_residual),
        metrics=metrics,
    )


def build_phase_region_pressure_velocity_g5_report(
    *,
    xp,
    admission: PhaseRegionForceAdmission,
    g4_report: PhaseRegionPressureVelocityG4Report,
    runtime_face_velocity_components,
    pressure_face_components,
    dt: float,
    projection_tolerance: float = 1.0e-12,
    force_consistency_tolerance: float = 1.0e-12,
    force_component_tolerance: float = 1.0e-12,
) -> PhaseRegionPressureVelocityG5Report:
    """Consume an admitted face force without nodal reconstruction or state update."""
    if not g4_report.valid:
        return _invalid_g5_report(reason=f"g4:{g4_report.reason}")
    if not g4_report.force_admissible or g4_report.face_force_components is None:
        return _invalid_g5_report(reason="g4_force_not_admissible")
    if not admission.valid or admission.cochain is None or admission.face_metric is None:
        return _invalid_g5_report(reason=f"candidate:{admission.reason}")
    dt_value = float(dt)
    tol = float(projection_tolerance)
    force_tol = float(force_consistency_tolerance)
    force_component_tol = float(force_component_tolerance)
    if not np.isfinite(dt_value) or dt_value <= 0.0:
        return _invalid_g5_report(reason="dt_invalid")
    if not np.isfinite(tol) or tol < 0.0:
        return _invalid_g5_report(reason="projection_tolerance_invalid")
    if not np.isfinite(force_tol) or force_tol < 0.0:
        return _invalid_g5_report(reason="force_consistency_tolerance_invalid")
    if not np.isfinite(force_component_tol) or force_component_tol < 0.0:
        return _invalid_g5_report(reason="force_component_tolerance_invalid")

    velocity_faces = tuple(xp.asarray(face) for face in runtime_face_velocity_components)
    pressure_faces = tuple(xp.asarray(face) for face in pressure_face_components)
    force_faces = tuple(xp.asarray(face) for face in g4_report.face_force_components)
    weights = tuple(
        xp.asarray(weight) for weight in admission.face_metric.face_weight_components
    )
    force_shapes = tuple(g4_report.face_force_shapes)
    if _component_shapes(velocity_faces) != force_shapes:
        return _invalid_g5_report(reason="velocity_face_shape_mismatch")
    if _component_shapes(pressure_faces) != force_shapes:
        return _invalid_g5_report(reason="pressure_face_shape_mismatch")
    if _component_shapes(force_faces) != force_shapes:
        return _invalid_g5_report(reason="force_face_shape_mismatch")
    if _component_shapes(weights) != force_shapes:
        return _invalid_g5_report(reason="metric_face_shape_mismatch")

    admitted_force_faces = tuple(
        xp.asarray(face) for face in admission.cochain.surface_acceleration
    )
    if _component_shapes(admitted_force_faces) != force_shapes:
        return _invalid_g5_report(reason="admitted_force_face_shape_mismatch")
    force_component_linf = _component_linf_difference(
        xp,
        force_faces,
        admitted_force_faces,
    )
    if force_component_linf > force_component_tol:
        return _invalid_g5_report(reason="face_force_component_linf")

    force_l2 = _weighted_l2(xp, force_faces, weights)
    force_consistency_residual = _relative_residual(
        float(g4_report.face_force_weighted_l2),
        float(force_l2),
    )
    if (
        not np.isfinite(force_l2)
        or not np.isfinite(float(g4_report.face_force_weighted_l2))
        or force_consistency_residual > force_tol
    ):
        return _invalid_g5_report(reason="face_force_consistency_residual")

    projected_faces = tuple(
        apply_pressure_projection(
            list(velocity_faces),
            list(pressure_faces),
            list(force_faces),
            dt_value,
        )
    )
    balance = [
        xp.asarray(projected)
        - xp.asarray(velocity)
        + dt_value * xp.asarray(pressure)
        - dt_value * xp.asarray(force)
        for projected, velocity, pressure, force in zip(
            projected_faces,
            velocity_faces,
            pressure_faces,
            force_faces,
        )
    ]
    identity_linf = _component_linf(xp, balance)
    valid = bool(identity_linf <= tol)
    reason = "ok" if valid else "projection_identity_linf"
    metrics = {
        "g5_valid": float(valid),
        "force_admissible": 1.0 if valid else 0.0,
        "face_force_consumed": 1.0 if valid else 0.0,
        "face_force_component_linf": float(force_component_linf),
        "face_force_weighted_l2": float(force_l2),
        "face_force_consistency_residual": float(force_consistency_residual),
        "face_projection_identity_linf": float(identity_linf),
        "face_projected_weighted_l2": _weighted_l2(xp, projected_faces, weights),
    }
    return PhaseRegionPressureVelocityG5Report(
        valid=valid,
        reason=reason,
        force_admissible=valid,
        projected_face_components=projected_faces if valid else None,
        projected_face_shapes=_component_shapes(projected_faces) if valid else (),
        projection_identity_linf=float(identity_linf),
        projected_weighted_l2=metrics["face_projected_weighted_l2"],
        metrics=metrics,
    )


def _invalid_g0_report(
    *,
    reason: str,
    bc_type: str,
    boundary_face_space: str,
    surface_face_shapes: tuple[tuple[int, ...], ...] = (),
    velocity_face_shapes: tuple[tuple[int, ...], ...] = (),
    pressure_face_shapes: tuple[tuple[int, ...], ...] = (),
    metric_face_shapes: tuple[tuple[int, ...], ...] = (),
    boundary_residual_linf: float = float("nan"),
) -> PhaseRegionPressureVelocityG0Report:
    return PhaseRegionPressureVelocityG0Report(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        bc_type=str(bc_type),
        boundary_face_space=str(boundary_face_space),
        surface_face_shapes=surface_face_shapes,
        velocity_face_shapes=velocity_face_shapes,
        pressure_face_shapes=pressure_face_shapes,
        metric_face_shapes=metric_face_shapes,
        boundary_residual_linf=float(boundary_residual_linf),
        surface_velocity_work=float("nan"),
        pressure_velocity_work=float("nan"),
        surface_weighted_l2=float("nan"),
        velocity_weighted_l2=float("nan"),
        pressure_weighted_l2=float("nan"),
        metrics={
            "g0_valid": 0.0,
            "force_admissible": 0.0,
        },
    )


def _invalid_g1_report(*, reason: str) -> PhaseRegionPressureVelocityG1Report:
    return PhaseRegionPressureVelocityG1Report(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        pressure_hodge_weighted_l2=float("nan"),
        pressure_range_weighted_l2=float("nan"),
        pressure_component_weighted_l2=float("nan"),
        pressure_hodge_ratio=float("nan"),
        pressure_hodge_divergence_linf=float("nan"),
        surface_hodge_weighted_l2=float("nan"),
        surface_range_weighted_l2=float("nan"),
        surface_component_weighted_l2=float("nan"),
        surface_hodge_ratio=float("nan"),
        surface_hodge_divergence_linf=float("nan"),
        metrics={
            "g1_valid": 0.0,
            "force_admissible": 0.0,
        },
    )


def _invalid_g2_report(*, reason: str) -> PhaseRegionPressureVelocityG2Report:
    return PhaseRegionPressureVelocityG2Report(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        finite_difference=float("nan"),
        capillary_power=float("nan"),
        pressure_velocity_work=float("nan"),
        work_closure_residual=float("nan"),
        riesz_residual=float("nan"),
        same_weight_surface_work_residual=float("nan"),
        pressure_work_finite=False,
        metrics={
            "g2_valid": 0.0,
            "force_admissible": 0.0,
        },
    )


def _invalid_g3_report(*, reason: str) -> PhaseRegionPressureVelocityG3Report:
    return PhaseRegionPressureVelocityG3Report(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        dt=float("nan"),
        projected_face_shapes=(),
        projection_identity_linf=float("nan"),
        pressure_update_weighted_l2=float("nan"),
        surface_update_weighted_l2=float("nan"),
        projected_weighted_l2=float("nan"),
        metrics={
            "g3_valid": 0.0,
            "force_admissible": 0.0,
        },
    )


def _invalid_g4_report(*, reason: str) -> PhaseRegionPressureVelocityG4Report:
    return PhaseRegionPressureVelocityG4Report(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        withheld_force_reason=str(reason),
        face_force_components=None,
        face_force_shapes=(),
        face_force_weighted_l2=float("nan"),
        surface_update_consistency_residual=float("nan"),
        metrics={
            "g4_valid": 0.0,
            "force_admissible": 0.0,
            "face_force_exposed": 0.0,
        },
    )


def _invalid_g5_report(*, reason: str) -> PhaseRegionPressureVelocityG5Report:
    return PhaseRegionPressureVelocityG5Report(
        valid=False,
        reason=str(reason),
        force_admissible=False,
        projected_face_components=None,
        projected_face_shapes=(),
        projection_identity_linf=float("nan"),
        projected_weighted_l2=float("nan"),
        metrics={
            "g5_valid": 0.0,
            "force_admissible": 0.0,
            "face_force_consumed": 0.0,
        },
    )


def _g0_shape_validity(
    *,
    surface_shapes: tuple[tuple[int, ...], ...],
    velocity_shapes: tuple[tuple[int, ...], ...],
    pressure_shapes: tuple[tuple[int, ...], ...],
    metric_shapes: tuple[tuple[int, ...], ...],
) -> tuple[bool, str]:
    if not surface_shapes:
        return False, "surface_faces_missing"
    if surface_shapes != velocity_shapes:
        return False, "velocity_face_shape_mismatch"
    if surface_shapes != pressure_shapes:
        return False, "pressure_face_shape_mismatch"
    if surface_shapes != metric_shapes:
        return False, "metric_face_shape_mismatch"
    return True, "ok"


def _component_shapes(components) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(int(axis) for axis in component.shape)
        for component in components
    )


def _component_min(xp, component) -> float:
    return float(np.min(array_to_numpy(xp, xp.asarray(component))))


def _component_linf_difference(xp, left, right) -> float:
    residuals = [
        float(np.max(np.abs(array_to_numpy(xp, xp.asarray(a) - xp.asarray(b)))))
        for a, b in zip(left, right)
    ]
    return max(residuals) if residuals else float("nan")


def _component_linf(xp, components) -> float:
    residuals = [
        float(np.max(np.abs(array_to_numpy(xp, xp.asarray(component)))))
        for component in components
    ]
    return max(residuals) if residuals else float("nan")


def _weighted_dot(xp, left, right, weights) -> float:
    total = None
    for left_component, right_component, weight in zip(left, right, weights):
        component = xp.sum(
            xp.asarray(weight) * xp.asarray(left_component) * xp.asarray(right_component)
        )
        total = component if total is None else total + component
    if total is None:
        return float("nan")
    return float(array_to_numpy(xp, total))


def _weighted_l2(xp, components, weights) -> float:
    dot = _weighted_dot(xp, components, components, weights)
    if dot < 0.0:
        return float("nan")
    return float(np.sqrt(dot))


def _relative_residual(left: float, right: float) -> float:
    scale = max(abs(float(left)), abs(float(right)), 1.0)
    return abs(float(left) - float(right)) / scale
