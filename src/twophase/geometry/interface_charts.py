"""Discrete interface chart primitives for q-manifold projection.

Symbol mapping
--------------
``Gamma_h`` -> chart-owned interface configuration.
``eta`` -> periodic graph-chart height coordinates.
``X`` -> periodic closed-curve vertices.
``E[Gamma_h]`` -> graph segment-length surface energy.
``dE`` -> nodal covector of the graph segment energy.

This module owns chart geometry only.  It does not transport cell volume,
rebuild a level-set field, compute pressure, or project velocity.  Cell volume
measurements live in ``q_manifold_projection``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

import numpy as np


@dataclass(frozen=True)
class GraphModeCoefficient:
    """Cosine/sine coefficient pair for one periodic graph mode."""

    mode: int
    cos: object
    sin: object


@dataclass(frozen=True)
class GraphChartState:
    """Owned periodic graph-chart state.

    ``eta`` is stored on periodic grid edges and has shape ``(..., nx + 1)``.
    The last value duplicates the first value along the last axis; callers that
    need unique nodes should use ``eta[..., :-1]``.
    """

    eta: object
    mean: object
    modes: tuple[GraphModeCoefficient, ...]

    @property
    def max_mode(self) -> int:
        """Largest admitted mode represented by this chart state."""
        return max((entry.mode for entry in self.modes), default=0)

    def coefficient_map(self) -> dict[str, object]:
        """Return a diagnostic coefficient map compatible with old oracles."""
        coeffs = {"mean": _scalar_or_array(self.mean)}
        for entry in self.modes:
            coeffs[f"cos_{entry.mode}"] = _scalar_or_array(entry.cos)
            coeffs[f"sin_{entry.mode}"] = _scalar_or_array(entry.sin)
        return coeffs


@dataclass(frozen=True)
class GraphEnergyGradient:
    """Surface energy, nodal covector, and quadrature weights for a graph."""

    energy: object
    nodal_gradient: object
    weights: object


@dataclass(frozen=True)
class ClosedRadialModeCoefficient:
    """Cosine/sine coefficient pair for one radial closed-curve mode."""

    mode: int
    cos: object
    sin: object


@dataclass(frozen=True)
class ClosedRadialChartState:
    """Owned star-shaped closed-curve chart state."""

    center: object
    theta: object
    radius: object
    vertices: object
    base_radius: object
    modes: tuple[ClosedRadialModeCoefficient, ...]

    def coefficient_map(self) -> dict[str, object]:
        """Return a diagnostic coefficient map for radial modes."""
        coeffs = {"base_radius": _scalar_or_array(self.base_radius)}
        for entry in self.modes:
            coeffs[f"cos_{entry.mode}"] = _scalar_or_array(entry.cos)
            coeffs[f"sin_{entry.mode}"] = _scalar_or_array(entry.sin)
        return coeffs


@dataclass(frozen=True)
class ClosedPolygonGeometry:
    """Closed polygon area, length, and exact vertex covectors."""

    area: object
    length: object
    surface_gradient: object
    area_gradient: object


def periodic_mode_basis(x: object, *, mode: int) -> tuple[object, object]:
    """Return cosine and sine basis values for a periodic graph mode."""
    x_arr = np.asarray(x, dtype=float)
    phase = 2.0 * pi * int(mode) * x_arr
    return np.cos(phase), np.sin(phase)


def eta_from_cosine_modes(
    x_edges: object,
    *,
    base_height: float,
    modes: tuple[tuple[int, float], ...],
) -> object:
    """Build a periodic graph height from cosine modes."""
    x_arr = np.asarray(x_edges, dtype=float)
    eta = np.full_like(x_arr, float(base_height), dtype=float)
    for mode, amplitude in modes:
        eta = eta + float(amplitude) * np.cos(2.0 * pi * int(mode) * x_arr)
    eta[-1] = eta[0]
    return eta


def graph_segment_energy_gradient(
    x_edges: object,
    eta_nodes: object,
    *,
    sigma: float,
) -> GraphEnergyGradient:
    """Return ``E_h[eta]`` and its nodal covector for a periodic graph."""
    x_arr = np.asarray(x_edges, dtype=float)
    eta_arr = np.asarray(eta_nodes, dtype=float)
    dx = np.diff(x_arr)
    if eta_arr.shape[-1:] == x_arr.shape:
        _validate_periodic_eta(eta_arr)
        eta_unique = eta_arr[..., :-1]
    elif eta_arr.shape[-1:] == dx.shape:
        eta_unique = eta_arr
    else:
        raise ValueError("eta_nodes must have trailing shape (nx,) or (nx + 1,)")
    if np.any(dx <= 0.0):
        raise ValueError("graph chart requires strictly increasing x_edges")
    eta_next = np.roll(eta_unique, -1, axis=-1)
    d_eta = eta_next - eta_unique
    segment_length = np.sqrt(dx * dx + d_eta * d_eta)
    if np.any(segment_length <= 0.0) or np.any(~np.isfinite(segment_length)):
        raise ValueError("graph segment lengths must be positive and finite")
    slope_right = d_eta / segment_length
    slope_left = np.roll(slope_right, 1, axis=-1)
    nodal_gradient = float(sigma) * (slope_left - slope_right)
    weights = 0.5 * (dx + np.roll(dx, 1))
    energy = _scalar_or_array(float(sigma) * np.sum(segment_length, axis=-1))
    return GraphEnergyGradient(energy=energy, nodal_gradient=nodal_gradient, weights=weights)


def project_column_height_to_graph(
    x_edges: object,
    column_height: object,
    *,
    max_mode: int,
) -> GraphChartState:
    """Project column heights to admitted low graph modes.

    This is the F0 graph-chart projection from ``WIKI-T-175``.  It assumes a
    uniform periodic x-grid, because the cell-average correction from column
    centers to edge modes is analytic only on that chart.
    """
    x_arr = np.asarray(x_edges, dtype=float)
    height = np.asarray(column_height, dtype=float)
    dx = np.diff(x_arr)
    if height.shape[-1:] != dx.shape:
        raise ValueError("column_height must have trailing shape (nx,)")
    if int(max_mode) < 0:
        raise ValueError("max_mode must be nonnegative")
    if np.any(dx <= 0.0):
        raise ValueError("graph projection requires strictly increasing x_edges")
    if not np.allclose(dx, dx[0], rtol=1.0e-13, atol=1.0e-15):
        raise ValueError("graph F0 mode projection currently requires uniform x spacing")

    x_center = 0.5 * (x_arr[:-1] + x_arr[1:])
    mean = np.sum(dx * height, axis=-1) / np.sum(dx)
    eta = np.zeros(height.shape[:-1] + x_arr.shape, dtype=float)
    eta = eta + np.asarray(mean, dtype=float)[..., None]
    centered = height - np.asarray(mean, dtype=float)[..., None]
    n = int(height.shape[-1])
    coefficients: list[GraphModeCoefficient] = []
    for mode in range(1, int(max_mode) + 1):
        cos_c, sin_c = periodic_mode_basis(x_center, mode=mode)
        cos_coef_center = _weighted_projection(centered, cos_c, dx)
        sin_coef_center = _weighted_projection(centered, sin_c, dx)
        cell_average_factor = np.cos(pi * mode / n)
        if abs(cell_average_factor) < 1.0e-14:
            cos_coef = 0.0
            sin_coef = 0.0
        else:
            cos_coef = cos_coef_center / cell_average_factor
            sin_coef = sin_coef_center / cell_average_factor
        cos_e, sin_e = periodic_mode_basis(x_arr, mode=mode)
        eta = eta + np.asarray(cos_coef)[..., None] * cos_e
        eta = eta + np.asarray(sin_coef)[..., None] * sin_e
        coefficients.append(
            GraphModeCoefficient(
                mode=int(mode),
                cos=_scalar_or_array(cos_coef),
                sin=_scalar_or_array(sin_coef),
            )
        )
    eta[..., -1] = eta[..., 0]
    return GraphChartState(eta=eta, mean=_scalar_or_array(mean), modes=tuple(coefficients))


def closed_radial_chart_from_modes(
    theta: object,
    *,
    center: object,
    base_radius: object,
    modes: tuple[tuple[int, float], ...],
) -> ClosedRadialChartState:
    """Build a star-shaped closed curve from radial cosine modes."""
    theta_arr = np.asarray(theta, dtype=float)
    center_arr = np.asarray(center, dtype=float)
    if center_arr.shape[-1:] != (2,):
        raise ValueError("center must have trailing shape (2,)")
    base = np.asarray(base_radius, dtype=float)
    radius = np.zeros(base.shape + theta_arr.shape, dtype=float) + base[..., None]
    coefficients: list[ClosedRadialModeCoefficient] = []
    for mode, amplitude in modes:
        cos_t = np.cos(int(mode) * theta_arr)
        radius = radius + float(amplitude) * cos_t
        coefficients.append(
            ClosedRadialModeCoefficient(mode=int(mode), cos=float(amplitude), sin=0.0)
        )
    if np.any(radius <= 0.0) or np.any(~np.isfinite(radius)):
        raise ValueError("closed radial chart requires positive finite radii")
    unit = np.stack((np.cos(theta_arr), np.sin(theta_arr)), axis=-1)
    vertices = center_arr[..., None, :] + radius[..., :, None] * unit
    return ClosedRadialChartState(
        center=center_arr,
        theta=theta_arr,
        radius=_scalar_or_array(radius),
        vertices=_scalar_or_array(vertices),
        base_radius=_scalar_or_array(base),
        modes=tuple(coefficients),
    )


def closed_polygon_geometry(vertices: object, *, sigma: float = 1.0) -> ClosedPolygonGeometry:
    """Return polygon area, length, and exact vertex covectors."""
    verts = np.asarray(vertices, dtype=float)
    if verts.shape[-1:] != (2,) or verts.shape[-2] < 3:
        raise ValueError("vertices must have shape (..., M, 2) with M >= 3")
    edge = np.roll(verts, -1, axis=-2) - verts
    edge_length = np.sqrt(np.sum(edge * edge, axis=-1))
    if np.any(edge_length <= 0.0) or np.any(~np.isfinite(edge_length)):
        raise ValueError("closed polygon edges must be positive and finite")
    x = verts[..., :, 0]
    y = verts[..., :, 1]
    x_next = np.roll(x, -1, axis=-1)
    y_next = np.roll(y, -1, axis=-1)
    area = 0.5 * np.sum(x * y_next - y * x_next, axis=-1)
    unit_edge = edge / edge_length[..., None]
    surface_gradient = float(sigma) * (
        np.roll(unit_edge, 1, axis=-2) - unit_edge
    )
    x_prev = np.roll(x, 1, axis=-1)
    y_prev = np.roll(y, 1, axis=-1)
    area_gradient = 0.5 * np.stack(
        (y_next - y_prev, x_prev - x_next),
        axis=-1,
    )
    return ClosedPolygonGeometry(
        area=_scalar_or_array(area),
        length=_scalar_or_array(np.sum(edge_length, axis=-1)),
        surface_gradient=_scalar_or_array(surface_gradient),
        area_gradient=_scalar_or_array(area_gradient),
    )


def _weighted_projection(values: object, basis: object, weights: object) -> object:
    values_arr = np.asarray(values, dtype=float)
    basis_arr = np.asarray(basis, dtype=float)
    weights_arr = np.asarray(weights, dtype=float)
    denom = float(np.sum(weights_arr * basis_arr * basis_arr))
    if denom <= 0.0:
        return 0.0
    return _scalar_or_array(np.sum(weights_arr * values_arr * basis_arr, axis=-1) / denom)


def _validate_periodic_eta(eta: object) -> None:
    eta_arr = np.asarray(eta, dtype=float)
    if eta_arr.ndim < 1 or eta_arr.shape[-1] < 2:
        raise ValueError("eta must have a periodic node axis")
    if not np.isfinite(eta_arr).all():
        raise ValueError("eta values must be finite")
    if np.max(np.abs(eta_arr[..., -1] - eta_arr[..., 0])) > 1.0e-12:
        raise ValueError("eta must be periodic: eta[-1] must equal eta[0]")


def _scalar_or_array(value: object) -> object:
    arr = np.asarray(value, dtype=float)
    if arr.shape == ():
        return float(arr)
    return arr
