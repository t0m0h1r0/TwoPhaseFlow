"""Trace-vertex Riesz cochains for closed-interface capillarity.

Symbol mapping
--------------
``C_K`` -> trace velocity map on fixed stratum ``K``
``d_z S_h`` -> :func:`trace_surface_vertex_covectors`
``d_z V_m`` -> :func:`trace_component_area_vertex_covectors`
``s_K`` -> ``-M_f^{-1} C_K^T d_z(sigma S_h)``
``B_K`` -> `` M_f^{-1} C_K^T d_z V_m``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .closed_interface_riesz import (
    face_mass_components,
    face_weighted_dot,
    face_weighted_norm,
    weighted_hodge_decomposition,
)
from .closed_interface_trace import TraceGraph2D
from .closed_interface_trace import build_trace_graph_2d
from .closed_interface_trace import trace_component_area_vertex_covectors
from .closed_interface_trace import trace_surface_vertex_covectors
from .closed_interface_trace import trace_vertex_covector_action
from .closed_interface_trace_velocity import ReconstructedNodalP1TraceVelocityMap


@dataclass(frozen=True)
class ClosedInterfaceTraceRieszCochain:
    """Trace-vertex surface and component-reaction cochains."""

    trace_graph: TraceGraph2D
    trace_velocity_map: ReconstructedNodalP1TraceVelocityMap
    surface_vertex_covectors: dict[int, np.ndarray]
    volume_vertex_covectors: list[dict[int, np.ndarray]]
    surface_force_covector: list[Any]
    volume_reaction_force_covectors: list[list[Any]]
    surface_acceleration: list[Any]
    volume_reaction_accelerations: list[list[Any]]
    face_weight_components: list[Any]
    phase_threshold: float
    sigma: float


@dataclass(frozen=True)
class TraceRieszWorkCheck:
    """Face-space work identity residual for one face velocity."""

    surface_gradient_action: float
    surface_power: float
    surface_riesz_residual: float
    volume_gradient_actions: tuple[float, ...]
    volume_powers: tuple[float, ...]
    volume_riesz_residuals: tuple[float, ...]


@dataclass(frozen=True)
class TraceComponentHodgeProjection:
    """Component-augmented weighted Hodge projection result."""

    corrected_capillary_components: list[Any]
    range_components: list[Any]
    hodge_residual_components: list[Any]
    component_hodge_residual_components: list[list[Any]]
    component_hodge_coefficients: Any
    component_hodge_denominator: Any
    face_weight_components: list[Any]
    capillary_jump_components: list[Any]
    range_projection_components: list[Any]


def closed_interface_trace_riesz_cochain(
    *,
    xp,
    grid,
    psi,
    sigma: float,
    rho=None,
    phase_threshold: float = 0.5,
    threshold_tol: float = 0.0,
    bc_type: str = "wall",
) -> ClosedInterfaceTraceRieszCochain:
    """Build ``s_K`` and ``B_K`` from trace-vertex virtual work."""
    graph = build_trace_graph_2d(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=float(phase_threshold),
        threshold_tol=float(threshold_tol),
    )
    trace_velocity_map = ReconstructedNodalP1TraceVelocityMap(grid=grid, bc_type=bc_type)
    dtype = xp.asarray(psi).dtype
    weights = face_mass_components(xp=xp, grid=grid, rho=rho)
    surface_vertex = trace_surface_vertex_covectors(graph, sigma=float(sigma))
    volume_vertex = trace_component_area_vertex_covectors(graph)
    surface_pullback = trace_velocity_map.pullback_vertex_covectors(
        xp=xp,
        graph=graph,
        vertex_covectors=surface_vertex,
        dtype=dtype,
    )
    surface_force = [-component for component in surface_pullback]
    volume_forces = [
        trace_velocity_map.pullback_vertex_covectors(
            xp=xp,
            graph=graph,
            vertex_covectors=covectors,
            dtype=dtype,
        )
        for covectors in volume_vertex
    ]
    return ClosedInterfaceTraceRieszCochain(
        trace_graph=graph,
        trace_velocity_map=trace_velocity_map,
        surface_vertex_covectors=surface_vertex,
        volume_vertex_covectors=volume_vertex,
        surface_force_covector=surface_force,
        volume_reaction_force_covectors=volume_forces,
        surface_acceleration=_divide_face_components(xp, surface_force, weights),
        volume_reaction_accelerations=[
            _divide_face_components(xp, volume_force, weights)
            for volume_force in volume_forces
        ],
        face_weight_components=weights,
        phase_threshold=float(phase_threshold),
        sigma=float(sigma),
    )


def trace_riesz_work_check(
    *,
    xp,
    cochain: ClosedInterfaceTraceRieszCochain,
    face_velocity_components,
) -> TraceRieszWorkCheck:
    """Check surface and component Riesz identities."""
    vertex_velocity = cochain.trace_velocity_map.vertex_velocities(
        xp=xp,
        graph=cochain.trace_graph,
        face_components=face_velocity_components,
    )
    surface_gradient_action = trace_vertex_covector_action(
        cochain.surface_vertex_covectors,
        vertex_velocity,
    )
    surface_power = face_weighted_dot(
        xp=xp,
        left_components=cochain.surface_acceleration,
        right_components=face_velocity_components,
        face_weight_components=cochain.face_weight_components,
    )
    volume_gradient_actions = []
    volume_powers = []
    volume_residuals = []
    for covectors, acceleration in zip(
        cochain.volume_vertex_covectors,
        cochain.volume_reaction_accelerations,
        strict=True,
    ):
        gradient_action = trace_vertex_covector_action(covectors, vertex_velocity)
        power = face_weighted_dot(
            xp=xp,
            left_components=acceleration,
            right_components=face_velocity_components,
            face_weight_components=cochain.face_weight_components,
        )
        volume_gradient_actions.append(float(gradient_action))
        volume_powers.append(float(power))
        volume_residuals.append(_relative_residual(gradient_action, power))
    return TraceRieszWorkCheck(
        surface_gradient_action=float(surface_gradient_action),
        surface_power=float(surface_power),
        surface_riesz_residual=_relative_residual(surface_gradient_action, -surface_power),
        volume_gradient_actions=tuple(volume_gradient_actions),
        volume_powers=tuple(volume_powers),
        volume_riesz_residuals=tuple(volume_residuals),
    )


def trace_component_hodge_projection(
    *,
    xp,
    div_op,
    cochain: ClosedInterfaceTraceRieszCochain,
    rcond: float = 1.0e-12,
) -> TraceComponentHodgeProjection:
    """Remove component-reaction Hodge directions from ``s_K``."""
    surface = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=cochain.surface_acceleration,
        face_weight_components=cochain.face_weight_components,
        rcond=float(rcond),
    )
    component_decompositions = [
        weighted_hodge_decomposition(
            xp=xp,
            div_op=div_op,
            face_components=reaction,
            face_weight_components=cochain.face_weight_components,
            rcond=float(rcond),
        )
        for reaction in cochain.volume_reaction_accelerations
    ]
    if not component_decompositions:
        beta = xp.asarray([], dtype=xp.asarray(cochain.surface_acceleration[0]).dtype)
        corrected = [xp.asarray(component) for component in cochain.surface_acceleration]
        return TraceComponentHodgeProjection(
            corrected_capillary_components=corrected,
            range_components=surface.range_components,
            hodge_residual_components=surface.hodge_components,
            component_hodge_residual_components=[],
            component_hodge_coefficients=beta,
            component_hodge_denominator=xp.asarray(0.0),
            face_weight_components=cochain.face_weight_components,
            capillary_jump_components=corrected,
            range_projection_components=surface.range_components,
        )
    matrix = np.zeros((len(component_decompositions), len(component_decompositions)))
    rhs = np.zeros(len(component_decompositions))
    for row, left in enumerate(component_decompositions):
        rhs[row] = face_weighted_dot(
            xp=xp,
            left_components=surface.hodge_components,
            right_components=left.hodge_components,
            face_weight_components=cochain.face_weight_components,
        )
        for col, right in enumerate(component_decompositions):
            matrix[row, col] = face_weighted_dot(
                xp=xp,
                left_components=left.hodge_components,
                right_components=right.hodge_components,
                face_weight_components=cochain.face_weight_components,
            )
    beta_host = np.linalg.lstsq(matrix, rhs, rcond=float(rcond))[0]
    corrected = [xp.asarray(component) for component in cochain.surface_acceleration]
    for coefficient, decomposition in zip(beta_host, component_decompositions, strict=True):
        corrected = [
            component - float(coefficient) * reaction_component
            for component, reaction_component in zip(
                corrected,
                decomposition.hodge_components,
                strict=True,
            )
        ]
    corrected_decomposition = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=corrected,
        face_weight_components=cochain.face_weight_components,
        rcond=float(rcond),
    )
    return TraceComponentHodgeProjection(
        corrected_capillary_components=corrected,
        range_components=corrected_decomposition.range_components,
        hodge_residual_components=corrected_decomposition.hodge_components,
        component_hodge_residual_components=[
            decomposition.hodge_components
            for decomposition in component_decompositions
        ],
        component_hodge_coefficients=xp.asarray(
            beta_host,
            dtype=xp.asarray(cochain.surface_acceleration[0]).dtype,
        ),
        component_hodge_denominator=xp.asarray(
            matrix[0, 0] if matrix.size else 0.0,
            dtype=xp.asarray(cochain.surface_acceleration[0]).dtype,
        ),
        face_weight_components=cochain.face_weight_components,
        capillary_jump_components=cochain.surface_acceleration,
        range_projection_components=corrected_decomposition.range_components,
    )


def trace_hodge_weighted_l2(*, xp, projection: TraceComponentHodgeProjection) -> float:
    """Return weighted norm of the component-constrained Hodge residual."""
    return face_weighted_norm(
        xp=xp,
        face_components=projection.hodge_residual_components,
        face_weight_components=projection.face_weight_components,
    )


def _divide_face_components(xp, numerator_components, denominator_components):
    return [
        xp.asarray(numerator) / xp.asarray(denominator)
        for numerator, denominator in zip(
            numerator_components,
            denominator_components,
            strict=True,
        )
    ]


def _relative_residual(left: float, right: float) -> float:
    denominator = abs(left) + abs(right) + 1.0e-30
    return abs(left - right) / denominator
