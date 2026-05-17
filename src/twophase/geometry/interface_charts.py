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

    This is the F0 graph-chart projection from ``WIKI-T-175``.  Column heights
    are interpreted as P1 graph cell averages.  The admitted low-mode
    coefficients are found by a weighted small least-squares solve in the
    chart space, so nonuniform x-spacing changes only the projection metric,
    not the state owner.
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

    mean = np.sum(dx * height, axis=-1) / np.sum(dx)
    eta = np.zeros(height.shape[:-1] + x_arr.shape, dtype=float)
    if int(max_mode) == 0:
        eta = eta + np.asarray(mean, dtype=float)[..., None]
        eta[..., -1] = eta[..., 0]
        return GraphChartState(eta=eta, mean=_scalar_or_array(mean), modes=())

    cell_basis_columns = []
    edge_basis_columns = []
    coefficients: list[GraphModeCoefficient] = []
    for mode in range(1, int(max_mode) + 1):
        cos_e, sin_e = periodic_mode_basis(x_arr, mode=mode)
        edge_basis_columns.extend((cos_e, sin_e))
        cell_basis_columns.extend(
            (
                0.5 * (cos_e[:-1] + cos_e[1:]),
                0.5 * (sin_e[:-1] + sin_e[1:]),
            )
        )
    cell_basis = np.stack(cell_basis_columns, axis=-1)
    edge_basis = np.stack(edge_basis_columns, axis=-1)
    basis_mean = np.sum(dx[:, None] * cell_basis, axis=0) / np.sum(dx)
    centered_basis = cell_basis - basis_mean[None, :]
    centered_height = height - np.asarray(mean, dtype=float)[..., None]
    gram = np.einsum("nk,nl,n->kl", centered_basis, centered_basis, dx)
    rhs = np.einsum("nk,...n,n->...k", centered_basis, centered_height, dx)
    try:
        flat_rhs = rhs.reshape((-1, rhs.shape[-1]))
        flat_coeffs = np.linalg.solve(gram, flat_rhs.T).T
    except np.linalg.LinAlgError as exc:
        raise ValueError("graph F0 mode projection basis is singular") from exc
    coeffs = flat_coeffs.reshape(rhs.shape)
    corrected_mean = mean - np.einsum("...k,k->...", coeffs, basis_mean)
    eta = eta + np.asarray(corrected_mean, dtype=float)[..., None]
    eta = eta + np.einsum("...k,nk->...n", coeffs, edge_basis)
    for mode_index, mode in enumerate(range(1, int(max_mode) + 1)):
        cos_coef = coeffs[..., 2 * mode_index]
        sin_coef = coeffs[..., 2 * mode_index + 1]
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
