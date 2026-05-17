"""Diagnostic gates for PhaseRegion pressure/velocity face-space coupling.

Symbol mapping
--------------
``s_f`` -> PhaseRegion capillary face acceleration cochain.
``u_f`` -> runtime FCCD face velocity.
``p_f`` -> pressure reaction faces.
``M_f`` -> PhaseRegion face mass metric.

The helpers in this module are zero-step diagnostics only.  They do not expose
``s_f`` as a runtime force, call projection, or advance a velocity field.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from twophase.coupling.phase_region_force_admission import (
    PhaseRegionForceAdapterDecision,
    PhaseRegionForceAdmission,
)
from twophase.coupling.closed_interface_stratum import array_to_numpy

from .face_boundary import (
    apply_direct_face_boundary_space,
    normalise_boundary_face_space,
)


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
