"""Certified swept-volume phase flux for SP-AO q transport.

Symbol mapping
--------------
``q_C`` -> physical liquid cell volume before transport.
``Phi_l`` -> oriented liquid swept-volume flux per unit time on cell faces.
``Phi_V`` -> oriented total volume flux per unit time on the same faces.
``Phi_m`` -> common mass flux, ``rho_g Phi_V + (rho_l-rho_g) Phi_l``.
``B Phi_l`` -> finite-volume face divergence used by the q update.
``V_out`` -> directional liquid volume swept out of a donor cell.
``V_in`` -> directional liquid volume swept into a receiver cell.
``u_f`` -> explicit face-normal velocity used by the strip constructor.

This module constructs a first P1 face-normal swept-strip ``Phi_l`` and also
certifies/applies supplied geometric swept fluxes.  The acceptor enforces the
contract that a candidate flux must be conservative under the declared closure,
must not sweep more liquid/gas volume through any cell than the cell owns, and
must keep ``0 <= q_C <= |C|`` without clipping.
"""

from __future__ import annotations

import math
from contextlib import nullcontext
from dataclasses import dataclass

from .cell_complex import MetricCellComplex
from .gpu_runtime_guard import reject_device_value, reject_gpu_namespace
from .p1_cut_geometry import (
    _case_field,
    _edge_crossing,
    _liquid_polygon_rings,
    _token_point,
    _validate_regular_values,
)


_BOUNDARY_KINDS = frozenset({"wall", "periodic"})


@dataclass(frozen=True)
class SweptFluxCertificate:
    """Conservation and boundedness certificate for one q transport update."""

    dt: float
    boundary: tuple[str, str]
    initial_volume: float
    final_volume: float
    volume_drift: float
    closure_residual_linf: float
    min_q: float
    max_q: float
    min_bound_margin: float
    min_donor_margin: float
    min_receiver_margin: float


@dataclass(frozen=True)
class SweptFluxTransportResult:
    """Result of applying a certified swept-volume flux to q."""

    q: object
    certificate: SweptFluxCertificate


@dataclass(frozen=True)
class P1SweptFluxCertificate:
    """Diagnostics for the P1 face-normal swept-strip constructor."""

    dt: float
    boundary: tuple[str, str]
    max_courant_linf: float
    max_abs_phase_flux: float
    closure_residual_linf: float


@dataclass(frozen=True)
class P1SweptFluxResult:
    """Constructed oriented swept-volume phase fluxes."""

    phase_fluxes: tuple[object, object]
    certificate: P1SweptFluxCertificate


def construct_p1_swept_flux_2d(
    grid,
    phi,
    face_velocity,
    *,
    dt: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    level: float = 0.0,
    tolerance: float = 1.0e-12,
) -> P1SweptFluxResult:
    """Construct ``Phi_l`` from P1 face-normal swept strips.

    The constructor assumes each face-normal velocity is constant during the
    step and sweeps only inside the immediate donor cell.  Each strip clips the
    donor cell's ``Q_h`` liquid polygon rings from ``cut_geometry_2d``, so
    non-affine mixed donor cells use the same geometry as the cell-volume
    carrier.  The constructor fail-closes when a face displacement exceeds the
    donor cell width.
    """
    if grid.ndim != 2:
        raise ValueError("construct_p1_swept_flux_2d supports 2D grids")
    reject_gpu_namespace(grid.xp, context="construct_p1_swept_flux_2d")
    dt = float(dt)
    tolerance = float(tolerance)
    if not (math.isfinite(dt) and dt > 0.0):
        raise ValueError("dt must be positive and finite")
    if not (math.isfinite(tolerance) and tolerance >= 0.0):
        raise ValueError("tolerance must be finite and non-negative")
    boundary = _normalize_boundary(boundary)

    complex_h = MetricCellComplex.from_grid(grid)
    xp = complex_h.xp
    phi_dev = xp.asarray(phi, dtype=complex_h.cell_measures.dtype)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    phi_rel = phi_dev - float(level)
    _validate_regular_values(xp, phi_rel)

    velocity_x, velocity_y = _validate_face_arrays(
        grid,
        face_velocity,
        dtype=phi_dev.dtype,
        x_name="x-face velocity",
        y_name="y-face velocity",
    )
    _validate_velocity_boundary_closure(
        xp,
        velocity_x,
        velocity_y,
        boundary,
        tolerance,
    )

    flux_x, max_courant_x = _construct_x_swept_flux(
        grid,
        xp,
        complex_h,
        phi_rel,
        velocity_x,
        dt,
        boundary[0],
        tolerance,
    )
    flux_y, max_courant_y = _construct_y_swept_flux(
        grid,
        xp,
        complex_h,
        phi_rel,
        velocity_y,
        dt,
        boundary[1],
        tolerance,
    )
    closure_residual = _closure_residual_linf(xp, flux_x, flux_y, boundary)
    if closure_residual > tolerance:
        raise ValueError("constructed swept phase flux violates boundary closure")
    max_abs_phase_flux = max(
        _scalar_float(xp, xp.max(xp.abs(flux_x))),
        _scalar_float(xp, xp.max(xp.abs(flux_y))),
    )
    return P1SweptFluxResult(
        phase_fluxes=(flux_x, flux_y),
        certificate=P1SweptFluxCertificate(
            dt=dt,
            boundary=boundary,
            max_courant_linf=max(max_courant_x, max_courant_y),
            max_abs_phase_flux=max_abs_phase_flux,
            closure_residual_linf=closure_residual,
        ),
    )


def apply_certified_swept_flux_2d(
    grid,
    q,
    phase_fluxes,
    *,
    dt: float,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-12,
) -> SweptFluxTransportResult:
    """Apply ``q^{n+1}=q^n-dt B Phi_l`` after fail-closed certification."""
    if grid.ndim != 2:
        raise ValueError("apply_certified_swept_flux_2d supports 2D grids")
    reject_gpu_namespace(grid.xp, context="apply_certified_swept_flux_2d")
    dt = float(dt)
    tolerance = float(tolerance)
    if not (math.isfinite(dt) and dt > 0.0):
        raise ValueError("dt must be positive and finite")
    if not (math.isfinite(tolerance) and tolerance >= 0.0):
        raise ValueError("tolerance must be finite and non-negative")
    boundary = _normalize_boundary(boundary)

    complex_h = MetricCellComplex.from_grid(grid)
    xp = complex_h.xp
    q_dev = xp.asarray(q, dtype=complex_h.cell_measures.dtype)
    if tuple(q_dev.shape) != complex_h.shape:
        raise ValueError("q shape must match the grid cell shape")
    _validate_finite(xp, q_dev, "q")
    _validate_q_bounds(xp, q_dev, complex_h.cell_measures, tolerance)

    flux_x, flux_y = _validate_fluxes(grid, phase_fluxes, dtype=q_dev.dtype)
    closure_residual = _closure_residual_linf(xp, flux_x, flux_y, boundary)
    if closure_residual > tolerance:
        raise ValueError("swept phase flux violates declared boundary closure")

    swept_x, swept_y = _swept_phase_volumes_2d(xp, flux_x, flux_y, dt)
    min_donor_margin, min_receiver_margin = _directional_capacity_margins_2d(
        xp,
        q_dev,
        complex_h.cell_measures,
        swept_x,
        swept_y,
        boundary,
    )
    if min_donor_margin < -tolerance:
        raise ValueError("swept phase flux exceeds donor liquid capacity")
    if min_receiver_margin < -tolerance:
        raise ValueError("swept phase flux exceeds receiver gas capacity")

    with _errstate(xp):
        swept_divergence = (swept_x[1:, :] - swept_x[:-1, :]) + (
            swept_y[:, 1:] - swept_y[:, :-1]
        )
        q_next = q_dev - swept_divergence
    _validate_finite(xp, q_next, "transported q")
    min_margin_dev = xp.minimum(q_next, complex_h.cell_measures - q_next)
    min_bound_margin = _scalar_float(xp, xp.min(min_margin_dev))
    if min_bound_margin < -tolerance:
        raise ValueError("swept phase flux violates q boundedness certificate")

    initial_volume = _scalar_float(xp, xp.sum(q_dev))
    final_volume = _scalar_float(xp, xp.sum(q_next))
    volume_drift = final_volume - initial_volume
    if abs(volume_drift) > tolerance:
        raise ValueError("swept phase flux violates global q conservation")

    return SweptFluxTransportResult(
        q=q_next,
        certificate=SweptFluxCertificate(
            dt=dt,
            boundary=boundary,
            initial_volume=initial_volume,
            final_volume=final_volume,
            volume_drift=volume_drift,
            closure_residual_linf=closure_residual,
            min_q=_scalar_float(xp, xp.min(q_next)),
            max_q=_scalar_float(xp, xp.max(q_next)),
            min_bound_margin=min_bound_margin,
            min_donor_margin=min_donor_margin,
            min_receiver_margin=min_receiver_margin,
        ),
    )


def face_volume_fluxes_2d(
    grid,
    face_velocity,
    *,
    boundary: tuple[str, str] = ("wall", "wall"),
    tolerance: float = 1.0e-12,
) -> tuple[object, object]:
    """Return oriented total-volume face fluxes ``Phi_V`` from face velocities.

    Boundary closure is checked in physical volume-flux units, matching the
    conservation certificate used for ``Phi_l``.
    """
    if grid.ndim != 2:
        raise ValueError("face_volume_fluxes_2d supports 2D grids")
    reject_gpu_namespace(grid.xp, context="face_volume_fluxes_2d")
    tolerance = float(tolerance)
    if not (math.isfinite(tolerance) and tolerance >= 0.0):
        raise ValueError("tolerance must be finite and non-negative")
    boundary = _normalize_boundary(boundary)

    complex_h = MetricCellComplex.from_grid(grid)
    xp = complex_h.xp
    velocity_x, velocity_y = _validate_face_arrays(
        grid,
        face_velocity,
        dtype=complex_h.cell_measures.dtype,
        x_name="x-face velocity",
        y_name="y-face velocity",
    )
    _validate_velocity_boundary_closure(
        xp,
        velocity_x,
        velocity_y,
        boundary,
        tolerance,
    )
    x = complex_h.x_edges
    y = complex_h.y_edges
    dx = x[1:] - x[:-1]
    dy = y[1:] - y[:-1]
    with _errstate(xp):
        volume_x = velocity_x * dy.reshape((1, -1))
        volume_y = velocity_y * dx.reshape((-1, 1))
    _validate_finite(xp, volume_x, "x-face volume flux")
    _validate_finite(xp, volume_y, "y-face volume flux")
    closure_residual = _closure_residual_linf(xp, volume_x, volume_y, boundary)
    if closure_residual > tolerance:
        raise ValueError("volume flux violates declared boundary closure")
    return volume_x, volume_y


def common_mass_fluxes_2d(
    grid,
    phase_fluxes,
    volume_fluxes,
    *,
    rho_l: float,
    rho_g: float,
) -> tuple[object, object]:
    """Return ``Phi_m`` from the exact same ``Phi_l`` face arrays."""
    if grid.ndim != 2:
        raise ValueError("common_mass_fluxes_2d supports 2D grids")
    reject_gpu_namespace(grid.xp, context="common_mass_fluxes_2d")
    rho_l = float(rho_l)
    rho_g = float(rho_g)
    if not (math.isfinite(rho_l) and math.isfinite(rho_g)):
        raise ValueError("rho_l and rho_g must be finite")
    xp = grid.xp
    phase_x, phase_y = _validate_fluxes(grid, phase_fluxes)
    volume_x, volume_y = _validate_fluxes(grid, volume_fluxes)
    drho = rho_l - rho_g
    with _errstate(xp):
        mass_x = rho_g * xp.asarray(volume_x) + drho * xp.asarray(phase_x)
        mass_y = rho_g * xp.asarray(volume_y) + drho * xp.asarray(phase_y)
    _validate_finite(xp, mass_x, "x-face mass flux")
    _validate_finite(xp, mass_y, "y-face mass flux")
    return mass_x, mass_y


def _normalize_boundary(boundary) -> tuple[str, str]:
    if isinstance(boundary, str):
        boundary = (boundary, boundary)
    if len(boundary) != 2:
        raise ValueError("boundary must provide one kind per axis")
    normalized = tuple(str(kind) for kind in boundary)
    if any(kind not in _BOUNDARY_KINDS for kind in normalized):
        raise ValueError("boundary entries must be 'wall' or 'periodic'")
    return normalized


def _validate_fluxes(grid, fluxes, *, dtype=None):
    return _validate_face_arrays(
        grid,
        fluxes,
        dtype=dtype,
        x_name="x-face flux",
        y_name="y-face flux",
    )


def _validate_face_arrays(
    grid,
    arrays,
    *,
    dtype=None,
    x_name: str,
    y_name: str,
):
    if len(arrays) != 2:
        raise ValueError("2D face arrays must contain x- and y-face arrays")
    xp = grid.xp
    flux_x = xp.asarray(arrays[0], dtype=dtype)
    flux_y = xp.asarray(arrays[1], dtype=dtype)
    expected_x = (grid.N[0] + 1, grid.N[1])
    expected_y = (grid.N[0], grid.N[1] + 1)
    if tuple(flux_x.shape) != expected_x:
        raise ValueError(f"{x_name} shape must be {expected_x}")
    if tuple(flux_y.shape) != expected_y:
        raise ValueError(f"{y_name} shape must be {expected_y}")
    _validate_finite(xp, flux_x, x_name)
    _validate_finite(xp, flux_y, y_name)
    return flux_x, flux_y


def _closure_residual_linf(xp, flux_x, flux_y, boundary: tuple[str, str]) -> float:
    residuals = []
    if boundary[0] == "wall":
        residuals.extend([xp.max(xp.abs(flux_x[0, :])), xp.max(xp.abs(flux_x[-1, :]))])
    else:
        residuals.append(xp.max(xp.abs(flux_x[0, :] - flux_x[-1, :])))
    if boundary[1] == "wall":
        residuals.extend([xp.max(xp.abs(flux_y[:, 0])), xp.max(xp.abs(flux_y[:, -1]))])
    else:
        residuals.append(xp.max(xp.abs(flux_y[:, 0] - flux_y[:, -1])))
    return max(_scalar_float(xp, residual) for residual in residuals)


def _validate_velocity_boundary_closure(
    xp,
    velocity_x,
    velocity_y,
    boundary: tuple[str, str],
    tolerance: float,
) -> None:
    residual = _closure_residual_linf(xp, velocity_x, velocity_y, boundary)
    if residual > tolerance:
        raise ValueError("face velocity violates declared boundary closure")


def _construct_x_swept_flux(
    grid,
    xp,
    complex_h,
    phi,
    velocity_x,
    dt: float,
    boundary_kind: str,
    tolerance: float,
):
    x = _astype_like(complex_h.x_edges, phi)
    y = _astype_like(complex_h.y_edges, phi)
    dx = x[1:] - x[:-1]
    flux = xp.zeros_like(velocity_x)
    courant_values = []

    internal_velocity = velocity_x[1:-1, :]
    if internal_velocity.size:
        displacement = dt * xp.abs(internal_velocity)
        positive_displacement = xp.where(
            internal_velocity >= 0.0, displacement, 0.0
        )
        negative_displacement = xp.where(
            internal_velocity < 0.0, displacement, 0.0
        )
        donor_width = xp.where(
            internal_velocity >= 0.0,
            dx[:-1].reshape((-1, 1)),
            dx[1:].reshape((-1, 1)),
        )
        courant_values.append(
            _validate_swept_courant(
                xp,
                displacement,
                donor_width,
                tolerance,
                "x-face swept displacement",
            )
        )
        positive_area = _right_side_vertical_strip_area(
            xp,
            y,
            x[1:-1].reshape((-1, 1)),
            positive_displacement,
            dx[:-1].reshape((-1, 1)),
            phi[:-2, :-1],
            phi[1:-1, :-1],
            phi[:-2, 1:],
            phi[1:-1, 1:],
        )
        negative_area = _left_side_vertical_strip_area(
            xp,
            y,
            x[1:-1].reshape((-1, 1)),
            negative_displacement,
            dx[1:].reshape((-1, 1)),
            phi[1:-1, :-1],
            phi[2:, :-1],
            phi[1:-1, 1:],
            phi[2:, 1:],
        )
        with _errstate(xp):
            flux[1:-1, :] = xp.where(
                internal_velocity >= 0.0,
                positive_area / dt,
                -negative_area / dt,
            )

    if boundary_kind == "periodic":
        boundary_velocity = velocity_x[0:1, :]
        displacement = dt * xp.abs(boundary_velocity)
        positive_displacement = xp.where(
            boundary_velocity >= 0.0, displacement, 0.0
        )
        negative_displacement = xp.where(
            boundary_velocity < 0.0, displacement, 0.0
        )
        donor_width = xp.where(
            boundary_velocity >= 0.0,
            dx[-1],
            dx[0],
        )
        courant_values.append(
            _validate_swept_courant(
                xp,
                displacement,
                donor_width,
                tolerance,
                "periodic x-face swept displacement",
            )
        )
        positive_area = _right_side_vertical_strip_area(
            xp,
            y,
            x[-1:].reshape((1, 1)),
            positive_displacement,
            dx[-1],
            phi[-2:-1, :-1],
            phi[-1:, :-1],
            phi[-2:-1, 1:],
            phi[-1:, 1:],
        )
        negative_area = _left_side_vertical_strip_area(
            xp,
            y,
            x[0:1].reshape((1, 1)),
            negative_displacement,
            dx[0],
            phi[0:1, :-1],
            phi[1:2, :-1],
            phi[0:1, 1:],
            phi[1:2, 1:],
        )
        with _errstate(xp):
            boundary_flux = xp.where(
                boundary_velocity >= 0.0,
                positive_area / dt,
                -negative_area / dt,
            )
        flux[0, :] = boundary_flux[0, :]
        flux[-1, :] = boundary_flux[0, :]

    _validate_finite(xp, flux, "constructed x-face phase flux")
    return flux, max(courant_values, default=0.0)


def _construct_y_swept_flux(
    grid,
    xp,
    complex_h,
    phi,
    velocity_y,
    dt: float,
    boundary_kind: str,
    tolerance: float,
):
    x = _astype_like(complex_h.x_edges, phi)
    y = _astype_like(complex_h.y_edges, phi)
    dy = y[1:] - y[:-1]
    flux = xp.zeros_like(velocity_y)
    courant_values = []

    internal_velocity = velocity_y[:, 1:-1]
    if internal_velocity.size:
        displacement = dt * xp.abs(internal_velocity)
        positive_displacement = xp.where(
            internal_velocity >= 0.0, displacement, 0.0
        )
        negative_displacement = xp.where(
            internal_velocity < 0.0, displacement, 0.0
        )
        donor_width = xp.where(
            internal_velocity >= 0.0,
            dy[:-1].reshape((1, -1)),
            dy[1:].reshape((1, -1)),
        )
        courant_values.append(
            _validate_swept_courant(
                xp,
                displacement,
                donor_width,
                tolerance,
                "y-face swept displacement",
            )
        )
        positive_area = _top_side_horizontal_strip_area(
            xp,
            x,
            y[1:-1].reshape((1, -1)),
            positive_displacement,
            dy[:-1].reshape((1, -1)),
            phi[:-1, :-2],
            phi[1:, :-2],
            phi[:-1, 1:-1],
            phi[1:, 1:-1],
        )
        negative_area = _bottom_side_horizontal_strip_area(
            xp,
            x,
            y[1:-1].reshape((1, -1)),
            negative_displacement,
            dy[1:].reshape((1, -1)),
            phi[:-1, 1:-1],
            phi[1:, 1:-1],
            phi[:-1, 2:],
            phi[1:, 2:],
        )
        with _errstate(xp):
            flux[:, 1:-1] = xp.where(
                internal_velocity >= 0.0,
                positive_area / dt,
                -negative_area / dt,
            )

    if boundary_kind == "periodic":
        boundary_velocity = velocity_y[:, 0:1]
        displacement = dt * xp.abs(boundary_velocity)
        positive_displacement = xp.where(
            boundary_velocity >= 0.0, displacement, 0.0
        )
        negative_displacement = xp.where(
            boundary_velocity < 0.0, displacement, 0.0
        )
        donor_width = xp.where(
            boundary_velocity >= 0.0,
            dy[-1],
            dy[0],
        )
        courant_values.append(
            _validate_swept_courant(
                xp,
                displacement,
                donor_width,
                tolerance,
                "periodic y-face swept displacement",
            )
        )
        positive_area = _top_side_horizontal_strip_area(
            xp,
            x,
            y[-1:].reshape((1, 1)),
            positive_displacement,
            dy[-1],
            phi[:-1, -2:-1],
            phi[1:, -2:-1],
            phi[:-1, -1:],
            phi[1:, -1:],
        )
        negative_area = _bottom_side_horizontal_strip_area(
            xp,
            x,
            y[0:1].reshape((1, 1)),
            negative_displacement,
            dy[0],
            phi[:-1, 0:1],
            phi[1:, 0:1],
            phi[:-1, 1:2],
            phi[1:, 1:2],
        )
        with _errstate(xp):
            boundary_flux = xp.where(
                boundary_velocity >= 0.0,
                positive_area / dt,
                -negative_area / dt,
            )
        flux[:, 0] = boundary_flux[:, 0]
        flux[:, -1] = boundary_flux[:, 0]

    _validate_finite(xp, flux, "constructed y-face phase flux")
    return flux, max(courant_values, default=0.0)


def _right_side_vertical_strip_area(
    xp,
    y_edges,
    x_face,
    displacement,
    cell_width,
    phi_left_bottom,
    phi_right_bottom,
    phi_left_top,
    phi_right_top,
):
    return _axis_aligned_strip_area(
        xp,
        "x",
        x_face - cell_width,
        x_face,
        y_edges[:-1].reshape((1, -1)),
        y_edges[1:].reshape((1, -1)),
        x_face - displacement,
        x_face,
        phi_left_bottom,
        phi_right_bottom,
        phi_left_top,
        phi_right_top,
    )


def _left_side_vertical_strip_area(
    xp,
    y_edges,
    x_face,
    displacement,
    cell_width,
    phi_left_bottom,
    phi_right_bottom,
    phi_left_top,
    phi_right_top,
):
    return _axis_aligned_strip_area(
        xp,
        "x",
        x_face,
        x_face + cell_width,
        y_edges[:-1].reshape((1, -1)),
        y_edges[1:].reshape((1, -1)),
        x_face,
        x_face + displacement,
        phi_left_bottom,
        phi_right_bottom,
        phi_left_top,
        phi_right_top,
    )


def _top_side_horizontal_strip_area(
    xp,
    x_edges,
    y_face,
    displacement,
    cell_width,
    phi_left_bottom,
    phi_right_bottom,
    phi_left_top,
    phi_right_top,
):
    return _axis_aligned_strip_area(
        xp,
        "y",
        x_edges[:-1].reshape((-1, 1)),
        x_edges[1:].reshape((-1, 1)),
        y_face - cell_width,
        y_face,
        y_face - displacement,
        y_face,
        phi_left_bottom,
        phi_right_bottom,
        phi_left_top,
        phi_right_top,
    )


def _bottom_side_horizontal_strip_area(
    xp,
    x_edges,
    y_face,
    displacement,
    cell_width,
    phi_left_bottom,
    phi_right_bottom,
    phi_left_top,
    phi_right_top,
):
    return _axis_aligned_strip_area(
        xp,
        "y",
        x_edges[:-1].reshape((-1, 1)),
        x_edges[1:].reshape((-1, 1)),
        y_face,
        y_face + cell_width,
        y_face,
        y_face + displacement,
        phi_left_bottom,
        phi_right_bottom,
        phi_left_top,
        phi_right_top,
    )


def _axis_aligned_strip_area(
    xp,
    axis: str,
    cell_x0,
    cell_x1,
    cell_y0,
    cell_y1,
    strip_lower,
    strip_upper,
    phi_left_bottom,
    phi_right_bottom,
    phi_left_top,
    phi_right_top,
):
    values = (
        phi_left_bottom,
        phi_right_bottom,
        phi_right_top,
        phi_left_top,
    )
    points = (
        (cell_x0, cell_y0),
        (cell_x1, cell_y0),
        (cell_x1, cell_y1),
        (cell_x0, cell_y1),
    )
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_field = _case_field(xp, values)
    local_area = xp.zeros_like(values[0])
    for case_id in range(16):
        for tokens in _liquid_polygon_rings(case_id):
            if len(tokens) < 3:
                continue
            active = case_field == case_id
            for kind, index in tokens:
                if kind == "edge":
                    active = active & crossings[index]["mask"]
            vertices = tuple(
                _token_point(token, points=points, crossings=crossings)
                for token in tokens
            )
            clipped_area = _polygon_axis_strip_area(
                xp, vertices, strip_lower, strip_upper, axis
            )
            local_area = local_area + xp.where(
                active, clipped_area, xp.zeros_like(clipped_area)
            )
    return local_area


def _polygon_axis_strip_area(xp, vertices, strip_lower, strip_upper, axis: str):
    local_area = xp.zeros_like(strip_lower + strip_upper)
    origin = vertices[0]
    for index in range(1, len(vertices) - 1):
        triangle = (origin, vertices[index], vertices[index + 1])
        upper_area = _triangle_axis_below_area(xp, triangle, strip_upper, axis)
        lower_area = _triangle_axis_below_area(xp, triangle, strip_lower, axis)
        local_area = local_area + upper_area - lower_area
    return local_area


def _triangle_axis_below_area(xp, triangle, bound, axis: str):
    coordinate_index = 0 if axis == "x" else 1
    values = tuple(point[coordinate_index] - bound for point in triangle)
    return _local_triangle_cut_area(xp, values, triangle, inclusive=True)


def _local_triangle_cut_area(xp, values, points, *, inclusive: bool = False):
    crossings = tuple(
        _triangle_edge_crossing(xp, values, points, edge, inclusive=inclusive)
        for edge in range(3)
    )
    case_field = _triangle_case_field(xp, values, inclusive=inclusive)
    local_area = xp.zeros_like(values[0])
    for case_id in range(8):
        tokens = _triangle_liquid_polygon_tokens(case_id)
        if len(tokens) < 3:
            continue
        active = case_field == case_id
        for kind, index in tokens:
            if kind == "edge":
                active = active & crossings[index]["mask"]
        shoelace = xp.zeros_like(values[0])
        for token, next_token in zip(tokens, tokens[1:] + tokens[:1], strict=True):
            x, y = _triangle_token_point(token, points=points, crossings=crossings)
            next_x, next_y = _triangle_token_point(
                next_token, points=points, crossings=crossings
            )
            shoelace = shoelace + x * next_y - y * next_x
        local_area = local_area + xp.where(
            active, 0.5 * shoelace, xp.zeros_like(shoelace)
        )
    return local_area


def _triangle_edge_crossing(xp, values, points, edge: int, *, inclusive: bool):
    edge_corners = ((0, 1), (1, 2), (2, 0))
    lo, hi = edge_corners[edge]
    value_lo = values[lo]
    value_hi = values[hi]
    if inclusive:
        mask = (value_lo <= 0.0) != (value_hi <= 0.0)
    else:
        mask = value_lo * value_hi < 0.0
    denominator = value_hi - value_lo
    safe_denominator = xp.where(mask, denominator, xp.ones_like(denominator))
    theta = xp.where(mask, -value_lo / safe_denominator, 0.0)
    x = points[lo][0] + theta * (points[hi][0] - points[lo][0])
    y = points[lo][1] + theta * (points[hi][1] - points[lo][1])
    return {"mask": mask, "x": x, "y": y}


def _triangle_case_field(xp, values, *, inclusive: bool):
    if inclusive:
        inside = tuple(value <= 0.0 for value in values)
    else:
        inside = tuple(value < 0.0 for value in values)
    case_field = xp.zeros_like(values[0], dtype=xp.uint8)
    for corner, mask in enumerate(inside):
        case_field = case_field + mask.astype(xp.uint8) * (1 << corner)
    return case_field


def _triangle_liquid_polygon_tokens(case_id: int):
    edge_corners = ((0, 1), (1, 2), (2, 0))
    inside = tuple(bool(case_id & (1 << corner)) for corner in range(3))
    tokens = []
    for edge, (lo, hi) in enumerate(edge_corners):
        if inside[lo]:
            tokens.append(("corner", lo))
        if inside[lo] != inside[hi]:
            tokens.append(("edge", edge))
    return tuple(tokens)


def _triangle_token_point(token, *, points, crossings):
    kind, index = token
    if kind == "corner":
        return points[index][0], points[index][1]
    crossing = crossings[index]
    return crossing["x"], crossing["y"]


def _validate_swept_courant(
    xp,
    displacement,
    donor_width,
    tolerance: float,
    name: str,
) -> float:
    _validate_finite(xp, displacement, name)
    with _errstate(xp):
        courant = displacement / donor_width
    _validate_finite(xp, courant, f"{name} Courant number")
    if _scalar_bool(xp, xp.any(displacement > donor_width + tolerance)):
        raise ValueError(f"{name} exceeds the donor cell width")
    return _scalar_float(xp, xp.max(courant))


def _astype_like(value, reference):
    if getattr(value, "dtype", None) == getattr(reference, "dtype", None):
        return value
    return value.astype(reference.dtype, copy=False)


def _swept_phase_volumes_2d(xp, flux_x, flux_y, dt: float):
    with _errstate(xp):
        swept_x = dt * flux_x
        swept_y = dt * flux_y
    _validate_finite(xp, swept_x, "x-face swept phase volume")
    _validate_finite(xp, swept_y, "y-face swept phase volume")
    return swept_x, swept_y


def _directional_capacity_margins_2d(
    xp,
    q,
    cell_measures,
    swept_x,
    swept_y,
    boundary: tuple[str, str],
) -> tuple[float, float]:
    outgoing = xp.zeros_like(q)
    incoming = xp.zeros_like(q)

    with _errstate(xp):
        x_internal = swept_x[1:-1, :]
        x_forward = xp.maximum(x_internal, 0.0)
        x_backward = xp.maximum(-x_internal, 0.0)
        outgoing[:-1, :] += x_forward
        incoming[1:, :] += x_forward
        outgoing[1:, :] += x_backward
        incoming[:-1, :] += x_backward

        y_internal = swept_y[:, 1:-1]
        y_forward = xp.maximum(y_internal, 0.0)
        y_backward = xp.maximum(-y_internal, 0.0)
        outgoing[:, :-1] += y_forward
        incoming[:, 1:] += y_forward
        outgoing[:, 1:] += y_backward
        incoming[:, :-1] += y_backward

        if boundary[0] == "periodic":
            x_periodic = swept_x[0, :]
            x_forward = xp.maximum(x_periodic, 0.0)
            x_backward = xp.maximum(-x_periodic, 0.0)
            outgoing[-1, :] += x_forward
            incoming[0, :] += x_forward
            outgoing[0, :] += x_backward
            incoming[-1, :] += x_backward

        if boundary[1] == "periodic":
            y_periodic = swept_y[:, 0]
            y_forward = xp.maximum(y_periodic, 0.0)
            y_backward = xp.maximum(-y_periodic, 0.0)
            outgoing[:, -1] += y_forward
            incoming[:, 0] += y_forward
            outgoing[:, 0] += y_backward
            incoming[:, -1] += y_backward

        donor_margin = xp.min(q - outgoing)
        # Incoming liquid may occupy initial gas volume plus liquid volume that
        # leaves the same cell during the step; final q bounds are checked below.
        receiver_margin = xp.min(cell_measures - q + outgoing - incoming)
    return _scalar_float(xp, donor_margin), _scalar_float(xp, receiver_margin)


def _validate_q_bounds(xp, q, cell_measures, tolerance: float) -> None:
    below = q < -tolerance
    above = q > cell_measures + tolerance
    if _scalar_bool(xp, xp.any(below | above)):
        raise ValueError("q must lie within physical cell-volume bounds")


def _validate_finite(xp, value, name: str) -> None:
    if _scalar_bool(xp, xp.any(~xp.isfinite(value))):
        raise ValueError(f"{name} must be finite")


def _errstate(xp):
    if hasattr(xp, "errstate"):
        return xp.errstate(over="ignore", invalid="ignore")
    return nullcontext()


def _scalar_bool(xp, value) -> bool:
    reject_device_value(value, context="P1 swept-flux scalar reduction")
    return bool(value)


def _scalar_float(xp, value) -> float:
    reject_device_value(value, context="P1 swept-flux scalar reduction")
    return float(value)
