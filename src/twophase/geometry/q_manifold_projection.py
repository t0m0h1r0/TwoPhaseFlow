"""Fast graph q-manifold projection helpers.

Symbol mapping
--------------
``q_T`` -> transported finite-volume measurement.
``Gamma*`` -> selected admissible graph-chart state.
``Q_h(Gamma*)`` -> measured physical cell volume ``q_phys``.
``r`` -> exposed off-manifold residual ``q_T - q_phys``.

Graph F0 and closed radial F0 oracle projections are implemented here.
Runtime adapters, nonlinear optimization, and face-cochain force coupling are
separate gates and intentionally absent.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .gpu_runtime_guard import reject_device_value, reject_gpu_namespace
from .interface_charts import (
    ClosedRadialChartState,
    ClosedPolygonGeometry,
    GraphChartState,
    GraphEnergyGradient,
    closed_polygon_geometry,
    closed_radial_chart_from_modes,
    graph_segment_energy_gradient,
    project_column_height_to_graph,
)
from .p1_cut_geometry import cut_geometry_2d


@dataclass(frozen=True)
class GraphQMeasurement:
    """Cell-volume measurement produced from a graph chart."""

    q: object
    phi: object
    sign_margin: float


@dataclass(frozen=True)
class ClosedQMeasurement:
    """Cell-volume measurement produced from a closed radial chart."""

    q: object
    phi: object
    sign_margin: float


@dataclass(frozen=True)
class ResidualReport:
    """Norm and moment diagnostics for ``r = q_T - Q_h(Gamma*)``."""

    l2: float
    relative_l2: float
    linf: float
    total_volume: float
    total_volume_abs: float
    column_linf: float


@dataclass(frozen=True)
class ProjectionResult:
    """Projection result that always exposes the off-manifold residual."""

    chart_kind: str
    stage: str
    gamma_state: object
    q_phys: object
    residual: object
    constraint_report: dict[str, float]
    energy_report: dict[str, object]
    residual_report: ResidualReport
    validity_report: dict[str, object]


def graph_q_from_eta(grid, eta_nodes: object, *, level: float = 0.0) -> GraphQMeasurement:
    """Measure ``Q_h(eta)`` by generating a graph gauge and applying P1 cuts."""
    reject_gpu_namespace(grid.xp, context="graph q-manifold projection")
    reject_device_value(eta_nodes, context="graph q-manifold projection")
    eta_arr = np.asarray(eta_nodes, dtype=float)
    y_nodes = np.asarray(grid.coords[1], dtype=float)
    if eta_arr.shape != (grid.N[0] + 1,):
        raise ValueError("eta_nodes must have shape (grid.N[0] + 1,)")
    if abs(float(eta_arr[-1] - eta_arr[0])) > 1.0e-12:
        raise ValueError("eta_nodes must be periodic")
    _x, y = np.meshgrid(np.asarray(grid.coords[0], dtype=float), y_nodes, indexing="ij")
    phi = y - eta_arr.reshape((-1, 1))
    geometry = cut_geometry_2d(grid, phi, level=float(level))
    return GraphQMeasurement(
        q=np.asarray(geometry.q, dtype=float),
        phi=phi,
        sign_margin=float(geometry.sign_margin),
    )


def closed_radial_q_from_chart(
    grid,
    state: ClosedRadialChartState,
    *,
    level: float = 0.0,
) -> ClosedQMeasurement:
    """Measure ``Q_h(X)`` by a radial gauge derived from the closed chart."""
    reject_gpu_namespace(grid.xp, context="closed radial q-manifold projection")
    reject_device_value(state.vertices, context="closed radial q-manifold projection")
    center = np.asarray(state.center, dtype=float)
    if center.shape != (2,):
        raise ValueError("closed radial Q_h measurement currently accepts one center")
    x_nodes = np.asarray(grid.coords[0], dtype=float)
    y_nodes = np.asarray(grid.coords[1], dtype=float)
    x, y = np.meshgrid(x_nodes, y_nodes, indexing="ij")
    dx = x - float(center[0])
    dy = y - float(center[1])
    node_theta = np.mod(np.arctan2(dy, dx), 2.0 * np.pi)
    node_radius = np.sqrt(dx * dx + dy * dy)
    chart_radius = _closed_radial_radius_at_theta(state, node_theta)
    phi = node_radius - chart_radius
    geometry = cut_geometry_2d(grid, phi, level=float(level))
    return ClosedQMeasurement(
        q=np.asarray(geometry.q, dtype=float),
        phi=phi,
        sign_margin=float(geometry.sign_margin),
    )


def column_height_from_q(grid, q: object) -> object:
    """Return graph column heights from integrated cell volume."""
    reject_device_value(q, context="graph q-manifold projection")
    q_arr = np.asarray(q, dtype=float)
    if q_arr.shape != tuple(grid.N):
        raise ValueError("q must have shape grid.N")
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    return np.sum(q_arr, axis=1) / dx


def project_graph_q_f0(
    grid,
    q_target: object,
    *,
    max_mode: int,
    sigma: float = 1.0,
    level: float = 0.0,
) -> ProjectionResult:
    """Project ``q_T`` to graph ``Gamma*`` by column moments and split residual."""
    reject_gpu_namespace(grid.xp, context="graph q-manifold projection")
    reject_device_value(q_target, context="graph q-manifold projection")
    q_arr = np.asarray(q_target, dtype=float)
    if q_arr.shape != tuple(grid.N):
        raise ValueError("q_target must have shape grid.N")

    x_edges = np.asarray(grid.coords[0], dtype=float)
    column_height = column_height_from_q(grid, q_arr)
    gamma_state = project_column_height_to_graph(
        x_edges,
        column_height,
        max_mode=int(max_mode),
    )
    measurement = graph_q_from_eta(grid, gamma_state.eta, level=float(level))
    q_phys = np.asarray(measurement.q, dtype=float)
    residual = q_arr - q_phys
    energy = graph_segment_energy_gradient(
        x_edges,
        np.asarray(gamma_state.eta, dtype=float),
        sigma=float(sigma),
    )
    residual_report = residual_report_for_q(grid, residual=residual, q_target=q_arr)
    column_residual = column_height_from_q(grid, residual)
    constraint_report = {
        "target_volume": float(np.sum(q_arr)),
        "physical_volume": float(np.sum(q_phys)),
        "residual_volume": float(np.sum(residual)),
        "column_residual_linf": float(np.max(np.abs(column_residual))),
    }
    energy_report = {
        "surface_energy": float(energy.energy),
        "nodal_gradient": energy.nodal_gradient,
        "weights": energy.weights,
    }
    validity_report = {
        "chart_regular": True,
        "sign_margin": float(measurement.sign_margin),
        "backend": "cpu",
        "stage": "F0",
        "max_mode": int(max_mode),
    }
    return ProjectionResult(
        chart_kind="graph",
        stage="F0",
        gamma_state=gamma_state,
        q_phys=q_phys,
        residual=residual,
        constraint_report=constraint_report,
        energy_report=energy_report,
        residual_report=residual_report,
        validity_report=validity_report,
    )


def project_closed_radial_mode_f0(
    grid,
    q_target: object,
    *,
    center: tuple[float, float],
    mode: int = 2,
    theta_count: int = 192,
    sigma: float = 1.0,
    level: float = 0.0,
) -> ProjectionResult:
    """Project ``q_T`` to one closed radial cosine mode and split residual.

    This is an oracle-grade F0 approximation.  It preserves total area through
    the radial base mode and estimates one admitted deformation mode from the
    corresponding angular area moment.
    """
    reject_gpu_namespace(grid.xp, context="closed radial q-manifold projection")
    reject_device_value(q_target, context="closed radial q-manifold projection")
    q_arr = np.asarray(q_target, dtype=float)
    if q_arr.shape != tuple(grid.N):
        raise ValueError("q_target must have shape grid.N")
    if int(theta_count) < 16:
        raise ValueError("theta_count must be at least 16")
    center_arr = np.asarray(center, dtype=float)
    if center_arr.shape != (2,):
        raise ValueError("center must have shape (2,)")

    target_area = float(np.sum(q_arr))
    if target_area <= 0.0:
        raise ValueError("closed radial projection requires positive target area")
    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    x_center = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_center = 0.5 * (y_edges[:-1] + y_edges[1:])
    x, y = np.meshgrid(x_center, y_center, indexing="ij")
    theta_cells = np.mod(
        np.arctan2(y - float(center_arr[1]), x - float(center_arr[0])),
        2.0 * np.pi,
    )
    moment_basis = np.cos(int(mode) * theta_cells)
    moment = float(np.sum(q_arr * moment_basis))
    radius_guess = float(np.sqrt(target_area / np.pi))
    amplitude = moment / (np.pi * max(radius_guess, 1.0e-30))
    base_sq = target_area / np.pi - 0.5 * amplitude * amplitude
    if base_sq <= 0.0:
        raise ValueError("closed radial area correction produced nonpositive base radius")
    base_radius = float(np.sqrt(base_sq))
    theta = np.linspace(0.0, 2.0 * np.pi, int(theta_count), endpoint=False)
    gamma_state = closed_radial_chart_from_modes(
        theta,
        center=center_arr,
        base_radius=base_radius,
        modes=((int(mode), amplitude),),
    )
    measurement = closed_radial_q_from_chart(grid, gamma_state, level=float(level))
    q_phys = np.asarray(measurement.q, dtype=float)
    residual = q_arr - q_phys
    polygon = closed_polygon_geometry(gamma_state.vertices, sigma=float(sigma))
    residual_report = residual_report_for_q(grid, residual=residual, q_target=q_arr)
    constraint_report = {
        "target_area": target_area,
        "physical_area": float(np.sum(q_phys)),
        "residual_area": float(np.sum(residual)),
        "polygon_area": float(polygon.area),
    }
    energy_report = {
        "surface_energy": float(sigma) * float(polygon.length),
        "polygon_area": float(polygon.area),
        "surface_gradient": polygon.surface_gradient,
        "area_gradient": polygon.area_gradient,
    }
    validity_report = {
        "chart_regular": True,
        "sign_margin": float(measurement.sign_margin),
        "backend": "cpu",
        "stage": "F0",
        "mode": int(mode),
        "min_radius": float(np.min(np.asarray(gamma_state.radius, dtype=float))),
    }
    return ProjectionResult(
        chart_kind="closed_radial",
        stage="F0",
        gamma_state=gamma_state,
        q_phys=q_phys,
        residual=residual,
        constraint_report=constraint_report,
        energy_report=energy_report,
        residual_report=residual_report,
        validity_report=validity_report,
    )


def residual_report_for_q(grid, *, residual: object, q_target: object) -> ResidualReport:
    """Build residual diagnostics without converting ``r`` into geometry."""
    reject_device_value(residual, context="q-manifold residual diagnostics")
    reject_device_value(q_target, context="q-manifold residual diagnostics")
    residual_arr = np.asarray(residual, dtype=float)
    q_arr = np.asarray(q_target, dtype=float)
    if residual_arr.shape != tuple(grid.N) or q_arr.shape != tuple(grid.N):
        raise ValueError("residual and q_target must have shape grid.N")
    column_residual = column_height_from_q(grid, residual_arr)
    l2 = float(np.sqrt(np.sum(residual_arr * residual_arr)))
    q_norm = float(np.sqrt(np.sum(q_arr * q_arr)))
    total_volume = float(np.sum(residual_arr))
    return ResidualReport(
        l2=l2,
        relative_l2=l2 / max(q_norm, 1.0e-30),
        linf=float(np.max(np.abs(residual_arr))),
        total_volume=total_volume,
        total_volume_abs=abs(total_volume),
        column_linf=float(np.max(np.abs(column_residual))),
    )


def closed_mode_restoring_action(
    polygon: ClosedPolygonGeometry | dict[str, object],
    vertices: object,
    theta: object,
    *,
    mode: int,
) -> float:
    """Return area-reaction-free restoring action on one radial mode."""
    if isinstance(polygon, dict):
        surface_gradient = np.asarray(polygon["surface_gradient"], dtype=float)
        area_gradient = np.asarray(polygon["area_gradient"], dtype=float)
    else:
        surface_gradient = np.asarray(polygon.surface_gradient, dtype=float)
        area_gradient = np.asarray(polygon.area_gradient, dtype=float)
    verts = np.asarray(vertices, dtype=float)
    theta_arr = np.asarray(theta, dtype=float)
    center = np.mean(verts, axis=-2)
    radial = verts - center[..., None, :]
    radial_norm = np.linalg.norm(radial, axis=-1)
    radial_unit = radial / radial_norm[..., None]
    mode_direction = np.cos(int(mode) * theta_arr)[..., None] * radial_unit
    area_norm = float(np.sum(area_gradient * area_gradient))
    beta = 0.0 if area_norm <= 0.0 else float(np.sum(surface_gradient * area_gradient) / area_norm)
    constrained_gradient = surface_gradient - beta * area_gradient
    return float(np.sum(-constrained_gradient * mode_direction))


def graph_force_projection(
    energy: GraphEnergyGradient | dict[str, object],
    x_edges: object,
    *,
    mode: int,
) -> float:
    """Project the restoring graph force ``-dE/deta`` onto one cosine mode."""
    x_unique = np.asarray(x_edges, dtype=float)[:-1]
    cos_mode = np.cos(2.0 * np.pi * int(mode) * x_unique)
    if isinstance(energy, dict):
        weights = np.asarray(energy["weights"], dtype=float)
        nodal_gradient = np.asarray(energy["nodal_gradient"], dtype=float)
    else:
        weights = np.asarray(energy.weights, dtype=float)
        nodal_gradient = np.asarray(energy.nodal_gradient, dtype=float)
    force = -nodal_gradient / weights
    denom = float(np.sum(weights * cos_mode * cos_mode))
    if denom <= 0.0:
        return 0.0
    return float(np.sum(weights * force * cos_mode) / denom)


def _closed_radial_radius_at_theta(state: ClosedRadialChartState, theta: object) -> object:
    theta_arr = np.asarray(theta, dtype=float)
    radius = np.zeros_like(theta_arr, dtype=float) + float(state.base_radius)
    for entry in state.modes:
        radius = radius + float(entry.cos) * np.cos(int(entry.mode) * theta_arr)
        radius = radius + float(entry.sin) * np.sin(int(entry.mode) * theta_arr)
    if np.any(radius <= 0.0):
        raise ValueError("closed radial chart radius became nonpositive")
    return radius
