"""Pressure-adjoint split for geometric AO capillary face cochains.

Symbol mapping:
    ``r_sigma`` -> ``raw_source_face_acceleration`` in the active face metric.
    ``B`` -> ``component_reaction_face_accelerations``.
    ``L_A`` -> pressure-range projection induced by ``div_op``/``ppe_solver``.
    ``Z_A`` -> Hodge residual ``c - L_A(c)``.

This simulation-layer service keeps the SP-AO geometric source separate from
the Navier--Stokes pressure-reaction algebra.  Geometry code owns the bundle
covector; this module owns the pressure-adjoint split used by predictor, PPE,
and corrector stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .interface_projection_diagnostics import (
    capillary_external_component_saddle_projection,
)


@dataclass(frozen=True)
class GeometricCapillaryReactionSplit:
    """Face-native pressure-reaction split for one AO capillary source."""

    raw_source_face_acceleration: tuple[Any, Any]
    component_reaction_face_accelerations: tuple[tuple[Any, Any], ...]
    corrected_source_face_acceleration: tuple[Any, Any]
    pressure_range_face_acceleration: tuple[Any, Any]
    pressure_range_coordinate: Any
    balanced_face_acceleration: tuple[Any, Any]
    face_weight_components: tuple[Any, Any]
    component_coefficients: Any
    component_denominator: Any
    pressure_adjoint_residual: Any
    saddle_constraint_linf: Any
    raw_source_weighted_l2: Any
    corrected_source_weighted_l2: Any
    pressure_range_weighted_l2: Any
    balanced_weighted_l2: Any
    max_abs_balanced_face_acceleration: Any
    status: str


def build_geometric_capillary_reaction_split(
    *,
    xp,
    div_op,
    ppe_solver,
    rho,
    pressure_flux_kwargs: dict[str, Any],
    raw_source_face_acceleration,
    component_reaction_face_accelerations,
    face_weight_components=None,
    rcond: float = 1.0e-12,
) -> GeometricCapillaryReactionSplit:
    """Project AO capillarity through the active pressure-adjoint split.

    A3 mapping:
      Equation: ``corrected = r_sigma - B mu`` and
      ``balanced = corrected - L_A(corrected)``.
      Discretization: ``capillary_external_component_saddle_projection`` builds
      the small component saddle after applying the same pressure range
      operator ``L_A`` used by the PPE.
      Code: return predictor, pressure-reaction, and balanced face
      accelerations on the projection-native face lattice.
    """
    raw_faces = tuple(xp.asarray(component) for component in raw_source_face_acceleration)
    component_faces = tuple(
        tuple(xp.asarray(axis_component) for axis_component in component)
        for component in component_reaction_face_accelerations
    )
    projection = capillary_external_component_saddle_projection(
        xp=xp,
        div_op=div_op,
        ppe_solver=ppe_solver,
        rho=rho,
        pressure_flux_kwargs=pressure_flux_kwargs,
        raw_components=raw_faces,
        component_reaction_components=component_faces,
        face_weight_components=face_weight_components,
        rcond=float(rcond),
    )
    weights = tuple(xp.asarray(component) for component in projection["face_weight_components"])
    corrected = tuple(
        xp.asarray(component) for component in projection["corrected_jump_components"]
    )
    pressure_range = tuple(
        xp.asarray(component) for component in projection["range_projection_components"]
    )
    balanced = tuple(
        xp.asarray(component) for component in projection["hodge_residual_components"]
    )
    return GeometricCapillaryReactionSplit(
        raw_source_face_acceleration=raw_faces,
        component_reaction_face_accelerations=component_faces,
        corrected_source_face_acceleration=corrected,
        pressure_range_face_acceleration=pressure_range,
        pressure_range_coordinate=xp.asarray(projection["pressure_coordinate"]),
        balanced_face_acceleration=balanced,
        face_weight_components=weights,
        component_coefficients=projection["component_hodge_coefficients"],
        component_denominator=projection["component_hodge_denominator"],
        pressure_adjoint_residual=projection["contract_pressure_adjoint_residual"],
        saddle_constraint_linf=projection["contract_saddle_constraint_linf"],
        raw_source_weighted_l2=_face_weighted_l2(xp, raw_faces, weights),
        corrected_source_weighted_l2=_face_weighted_l2(xp, corrected, weights),
        pressure_range_weighted_l2=_face_weighted_l2(xp, pressure_range, weights),
        balanced_weighted_l2=_face_weighted_l2(xp, balanced, weights),
        max_abs_balanced_face_acceleration=_max_abs_face_pair(xp, balanced),
        status="pressure_component_hodge_split",
    )


def _face_weighted_l2(xp, components, weights):
    total = None
    for component, weight in zip(components, weights, strict=True):
        contribution = xp.sum(xp.asarray(weight) * xp.asarray(component) ** 2)
        total = contribution if total is None else total + contribution
    if total is None:
        total = xp.asarray(0.0)
    return xp.sqrt(xp.maximum(total, xp.asarray(0.0, dtype=total.dtype)))


def _max_abs_face_pair(xp, components):
    maxima = [xp.max(xp.abs(xp.asarray(component))) for component in components]
    if not maxima:
        return xp.asarray(0.0)
    result = maxima[0]
    for value in maxima[1:]:
        result = xp.maximum(result, value)
    return result
