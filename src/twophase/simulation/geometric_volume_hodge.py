"""AO geometric cell-face finite-volume Hodge projection.

Symbol mapping
--------------
``F0``
    Unprojected integrated geometric cell-face volume flux.
``F``
    Projected integrated geometric cell-face volume flux.
``B_g``
    Oriented cell-face incidence on the geometric cell complex.
``G_g``
    Metric gradient ``M_g^{-1} B_g^T`` with face coefficient
    ``area / distance`` on the current nonuniform grid.
``p``
    Cell potential used only for the projection correction.

The projection solves the finite-dimensional variational problem used by the
active-geometry volume update in WIKI-T-169:

``min 1/2 ||F - F0||^2_Mg`` subject to ``B_g F = 0``.

The Euler equation is ``A p = -B_g F0`` with ``A = -B_g G_g`` and
``F = F0 - G_g p``.  The code below keeps the operator independent from the NS
pipeline so nonuniform metrics, boundary quotient semantics, and PCG policy are
explicit inputs rather than hidden solver state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class GeometricVolumeHodgePolicy:
    """Numerical policy for the AO geometric volume-flux Hodge projection."""

    absolute_tolerance: float = 1.0e-11
    pcg_tolerance: float = 1.0e-12
    pcg_max_iterations: int = 256
    pcg_roundoff_floor: float | None = 1.0e-14

    def validated(self) -> "GeometricVolumeHodgePolicy":
        """Return a finite, positive, fail-closed policy instance."""
        absolute_tolerance = _positive_float(
            self.absolute_tolerance,
            "absolute_tolerance",
        )
        pcg_tolerance = _positive_float(self.pcg_tolerance, "pcg_tolerance")
        max_iterations = int(self.pcg_max_iterations)
        if max_iterations <= 0:
            raise ValueError("pcg_max_iterations must be positive")
        roundoff_floor = self.pcg_roundoff_floor
        if roundoff_floor is not None:
            roundoff_floor = _positive_float(roundoff_floor, "pcg_roundoff_floor")
            if roundoff_floor > pcg_tolerance:
                raise ValueError(
                    "pcg_roundoff_floor must not exceed pcg_tolerance"
                )
        return GeometricVolumeHodgePolicy(
            absolute_tolerance=absolute_tolerance,
            pcg_tolerance=pcg_tolerance,
            pcg_max_iterations=max_iterations,
            pcg_roundoff_floor=roundoff_floor,
        )


@dataclass(frozen=True)
class GeometricVolumeMetrics2D:
    """Device-resident metric coefficients for one 2-D geometric cell complex."""

    dx: Any
    dy: Any
    nx: int
    ny: int
    boundary: tuple[str, str]


@dataclass(frozen=True)
class GeometricVolumeHodgeProjection:
    """Projected velocity plus scalar residual certificate."""

    face_velocity_components: list[Any]
    volume_flux_components: tuple[Any, Any]
    raw_volume_residual: float
    projected_volume_residual: float


def geometric_cell_face_shapes(grid_shape: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return AO geometric x/y face shapes for ``grid_shape=(nx, ny)``."""
    nx, ny = _grid_shape_2d(grid_shape)
    return (nx + 1, ny), (nx, ny + 1)


def projection_native_face_shapes(grid_shape: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return FCCD/projection-native x/y face shapes for nodal velocities."""
    nx, ny = _grid_shape_2d(grid_shape)
    return (nx, ny + 1), (nx + 1, ny)


def project_geometric_cell_face_velocity(
    backend,
    coords,
    grid_shape: tuple[int, int],
    face_velocity,
    *,
    dt: float,
    boundary: tuple[str, str],
    policy: GeometricVolumeHodgePolicy,
) -> GeometricVolumeHodgeProjection:
    """Project geometric cell-face velocities onto ``B_g Phi_V = 0``.

    ``face_velocity`` is a velocity cochain on AO geometric cell faces.  The
    projection is performed on integrated volume fluxes, because the preserved
    phase variable is physical liquid volume ``q_C`` rather than normalized
    fraction ``theta_C``.
    """
    xp = backend.xp
    policy = policy.validated()
    if not np.isfinite(float(dt)) or float(dt) <= 0.0:
        raise ValueError("dt must be positive and finite")
    metrics = build_geometric_volume_metrics(
        xp,
        coords,
        grid_shape,
        dtype=xp.asarray(face_velocity[0]).dtype,
        boundary=boundary,
    )
    velocity_x, velocity_y = _as_shape_checked_face_pair(
        xp,
        face_velocity,
        geometric_cell_face_shapes((metrics.nx, metrics.ny)),
        "geometric cell-face velocity",
    )
    flux_x = velocity_x * metrics.dy.reshape((1, -1))
    flux_y = velocity_y * metrics.dx.reshape((-1, 1))
    flux_x, flux_y = close_geometric_volume_flux_boundary(
        xp,
        flux_x,
        flux_y,
        boundary=metrics.boundary,
    )
    projected_flux, raw_residual, projected_residual = project_geometric_volume_flux_pair(
        backend,
        coords,
        (metrics.nx, metrics.ny),
        (flux_x, flux_y),
        dt=dt,
        boundary=metrics.boundary,
        policy=policy,
    )
    projected_x, projected_y = projected_flux
    return GeometricVolumeHodgeProjection(
        face_velocity_components=[
            projected_x / metrics.dy.reshape((1, -1)),
            projected_y / metrics.dx.reshape((-1, 1)),
        ],
        volume_flux_components=projected_flux,
        raw_volume_residual=raw_residual,
        projected_volume_residual=projected_residual,
    )


def build_geometric_volume_metrics(
    xp,
    coords,
    grid_shape: tuple[int, int],
    *,
    dtype,
    boundary: tuple[str, str],
) -> GeometricVolumeMetrics2D:
    """Build validated nonuniform-grid metric arrays on the active backend."""
    nx, ny = _grid_shape_2d(grid_shape)
    boundary = _boundary_2d(boundary)
    if boundary[0] == "periodic" and nx < 2:
        raise ValueError("periodic x geometric Hodge requires at least two cells")
    if boundary[1] == "periodic" and ny < 2:
        raise ValueError("periodic y geometric Hodge requires at least two cells")
    dx_host = _cell_widths_host(coords[0], nx, "x")
    dy_host = _cell_widths_host(coords[1], ny, "y")
    return GeometricVolumeMetrics2D(
        dx=xp.asarray(dx_host, dtype=dtype),
        dy=xp.asarray(dy_host, dtype=dtype),
        nx=nx,
        ny=ny,
        boundary=boundary,
    )


def close_geometric_volume_flux_boundary(
    xp,
    flux_x,
    flux_y,
    *,
    boundary: tuple[str, str],
):
    """Materialise wall or periodic quotient closure on cell-face fluxes."""
    boundary = _boundary_2d(boundary)
    flux_x = xp.array(flux_x, copy=True)
    flux_y = xp.array(flux_y, copy=True)
    if boundary[0] == "periodic":
        seam = 0.5 * (flux_x[0, :] + flux_x[-1, :])
        flux_x[0, :] = seam
        flux_x[-1, :] = seam
    else:
        flux_x[0, :] = 0.0
        flux_x[-1, :] = 0.0
    if boundary[1] == "periodic":
        seam = 0.5 * (flux_y[:, 0] + flux_y[:, -1])
        flux_y[:, 0] = seam
        flux_y[:, -1] = seam
    else:
        flux_y[:, 0] = 0.0
        flux_y[:, -1] = 0.0
    return flux_x, flux_y


def project_geometric_volume_flux_pair(
    backend,
    coords,
    grid_shape: tuple[int, int],
    volume_flux,
    *,
    dt: float,
    boundary: tuple[str, str],
    policy: GeometricVolumeHodgePolicy,
):
    """Return finite-volume Hodge projection of integrated cell-face fluxes."""
    xp = backend.xp
    policy = policy.validated()
    flux_x, flux_y = _as_shape_checked_face_pair(
        xp,
        volume_flux,
        geometric_cell_face_shapes(grid_shape),
        "geometric volume flux",
    )
    metrics = build_geometric_volume_metrics(
        xp,
        coords,
        grid_shape,
        dtype=flux_x.dtype,
        boundary=boundary,
    )
    div0 = geometric_volume_flux_divergence(flux_x, flux_y)
    rhs = -div0
    rhs = rhs - xp.mean(rhs)
    diag = geometric_volume_flux_projection_diagonal(xp, metrics, dtype=flux_x.dtype)
    potential = solve_geometric_volume_flux_projection_pcg(
        xp,
        metrics,
        rhs,
        diag,
        pcg_tolerance=policy.pcg_tolerance,
        max_iterations=policy.pcg_max_iterations,
        roundoff_floor=policy.pcg_roundoff_floor,
    )
    grad_x, grad_y = geometric_volume_flux_gradient(
        xp,
        metrics,
        potential,
        dtype=flux_x.dtype,
    )
    projected_x = flux_x - grad_x
    projected_y = flux_y - grad_y
    projected_x, projected_y = close_geometric_volume_flux_boundary(
        xp,
        projected_x,
        projected_y,
        boundary=metrics.boundary,
    )
    div1 = geometric_volume_flux_divergence(projected_x, projected_y)
    residual_packet = xp.stack(
        [
            xp.max(xp.abs(div0)) * xp.asarray(dt, dtype=flux_x.dtype),
            xp.max(xp.abs(div1)) * xp.asarray(dt, dtype=flux_x.dtype),
        ]
    )
    raw_residual, projected_residual = np.asarray(
        backend.to_host(residual_packet),
        dtype=float,
    ).reshape(2)
    if projected_residual > policy.absolute_tolerance:
        raise ValueError(
            "geometric_cell_fraction AO transport requires B_g Phi_V=0 "
            "on the geometric cell-face lattice; "
            f"projection residual {projected_residual:.6e} exceeds "
            f"q-volume tolerance {policy.absolute_tolerance:.6e} "
            f"(raw {raw_residual:.6e})"
        )
    return (projected_x, projected_y), raw_residual, projected_residual


def geometric_volume_flux_gradient(
    xp,
    metrics: GeometricVolumeMetrics2D,
    potential,
    *,
    dtype,
):
    """Return integrated cell-face flux ``G_g potential``."""
    p = xp.asarray(potential, dtype=dtype)
    nx, ny = metrics.nx, metrics.ny
    dx, dy = metrics.dx, metrics.dy
    grad_x = xp.zeros((nx + 1, ny), dtype=dtype)
    grad_y = xp.zeros((nx, ny + 1), dtype=dtype)
    if nx > 1:
        dist_x = 0.5 * (dx[:-1] + dx[1:])
        coeff_x = dy.reshape((1, -1)) / dist_x.reshape((-1, 1))
        grad_x[1:nx, :] = coeff_x * (p[1:, :] - p[:-1, :])
    if metrics.boundary[0] == "periodic":
        dist = 0.5 * (dx[-1] + dx[0])
        seam = dy * (p[0, :] - p[-1, :]) / dist
        grad_x[0, :] = seam
        grad_x[-1, :] = seam
    if ny > 1:
        dist_y = 0.5 * (dy[:-1] + dy[1:])
        coeff_y = dx.reshape((-1, 1)) / dist_y.reshape((1, -1))
        grad_y[:, 1:ny] = coeff_y * (p[:, 1:] - p[:, :-1])
    if metrics.boundary[1] == "periodic":
        dist = 0.5 * (dy[-1] + dy[0])
        seam = dx * (p[:, 0] - p[:, -1]) / dist
        grad_y[:, 0] = seam
        grad_y[:, -1] = seam
    return grad_x, grad_y


def geometric_volume_flux_divergence(flux_x, flux_y):
    """Return integrated finite-volume divergence ``B_g F``."""
    return (flux_x[1:, :] - flux_x[:-1, :]) + (
        flux_y[:, 1:] - flux_y[:, :-1]
    )


def geometric_volume_flux_projection_diagonal(
    xp,
    metrics: GeometricVolumeMetrics2D,
    *,
    dtype,
):
    """Return Jacobi diagonal for ``A=-B_g G_g``."""
    nx, ny = metrics.nx, metrics.ny
    dx, dy = metrics.dx, metrics.dy
    diag = xp.zeros((nx, ny), dtype=dtype)
    if nx > 1:
        dist_x = 0.5 * (dx[:-1] + dx[1:])
        coeff_x = dy.reshape((1, -1)) / dist_x.reshape((-1, 1))
        diag[:-1, :] = diag[:-1, :] + coeff_x
        diag[1:, :] = diag[1:, :] + coeff_x
    if metrics.boundary[0] == "periodic":
        coeff = dy / (0.5 * (dx[-1] + dx[0]))
        diag[0, :] = diag[0, :] + coeff
        diag[-1, :] = diag[-1, :] + coeff
    if ny > 1:
        dist_y = 0.5 * (dy[:-1] + dy[1:])
        coeff_y = dx.reshape((-1, 1)) / dist_y.reshape((1, -1))
        diag[:, :-1] = diag[:, :-1] + coeff_y
        diag[:, 1:] = diag[:, 1:] + coeff_y
    if metrics.boundary[1] == "periodic":
        coeff = dx / (0.5 * (dy[-1] + dy[0]))
        diag[:, 0] = diag[:, 0] + coeff
        diag[:, -1] = diag[:, -1] + coeff
    return xp.maximum(diag, xp.asarray(1.0e-30, dtype=dtype))


def solve_geometric_volume_flux_projection_pcg(
    xp,
    metrics: GeometricVolumeMetrics2D,
    rhs,
    diag,
    *,
    pcg_tolerance: float,
    max_iterations: int,
    roundoff_floor: float | None,
):
    """Device-resident fixed-loop PCG for ``A=-B_g G_g``."""

    def apply_operator(value):
        grad_x, grad_y = geometric_volume_flux_gradient(
            xp,
            metrics,
            value,
            dtype=rhs.dtype,
        )
        return -geometric_volume_flux_divergence(grad_x, grad_y)

    x = xp.zeros_like(rhs)
    r = rhs - apply_operator(x)
    z = r / diag
    p = z.copy()
    rz = xp.sum(r * z)
    rhs_linf = xp.max(xp.abs(rhs))
    residual_tolerance = xp.asarray(pcg_tolerance, dtype=rhs.dtype) * xp.maximum(
        rhs_linf,
        xp.asarray(1.0, dtype=rhs.dtype),
    )
    algebra_floor = 1.0e-30 if roundoff_floor is None else max(
        float(roundoff_floor) ** 2,
        1.0e-30,
    )
    eps = xp.asarray(algebra_floor, dtype=rhs.dtype)
    for _ in range(int(max_iterations)):
        ap = apply_operator(p)
        denom = xp.sum(p * ap)
        residual_linf = xp.max(xp.abs(r))
        active_iteration = (
            (residual_linf > residual_tolerance)
            & (xp.abs(denom) > eps)
            & (xp.abs(rz) > eps)
        )
        safe_denom = xp.where(active_iteration, denom, xp.ones_like(denom))
        alpha = xp.where(active_iteration, rz / safe_denom, xp.zeros_like(denom))
        x_next = x + alpha * p
        r_next = r - alpha * ap
        z_next = r_next / diag
        rz_next = xp.sum(r_next * z_next)
        safe_rz = xp.where(active_iteration, rz, xp.ones_like(rz))
        beta = xp.where(active_iteration, rz_next / safe_rz, xp.zeros_like(rz))
        x = xp.where(active_iteration, x_next, x)
        r = xp.where(active_iteration, r_next, r)
        z = xp.where(active_iteration, z_next, z)
        p = xp.where(active_iteration, z_next + beta * p, p)
        rz = xp.where(active_iteration, rz_next, rz)
    return x


def _grid_shape_2d(grid_shape: tuple[int, int]) -> tuple[int, int]:
    if len(tuple(grid_shape)) != 2:
        raise ValueError("geometric volume Hodge currently supports 2-D only")
    nx, ny = (int(grid_shape[0]), int(grid_shape[1]))
    if nx <= 0 or ny <= 0:
        raise ValueError("grid_shape entries must be positive")
    return nx, ny


def _boundary_2d(boundary: tuple[str, str]) -> tuple[str, str]:
    axes = tuple(str(axis).strip().lower() for axis in boundary)
    if len(axes) != 2 or any(axis not in {"wall", "periodic"} for axis in axes):
        raise ValueError(f"boundary must be two wall|periodic axes, got {boundary!r}")
    return axes


def _cell_widths_host(coord, n_cells: int, axis_name: str) -> np.ndarray:
    values = np.asarray(coord, dtype=float)
    if values.shape != (n_cells + 1,):
        raise ValueError(
            f"{axis_name}-coords shape {values.shape} does not match "
            f"{n_cells + 1} grid nodes"
        )
    widths = np.diff(values)
    if not np.all(np.isfinite(widths)) or not np.all(widths > 0.0):
        raise ValueError(f"{axis_name}-coords must be finite and strictly increasing")
    return widths


def _as_shape_checked_face_pair(xp, face_pair, expected_shapes, label: str):
    if len(face_pair) != 2:
        raise ValueError(f"{label} must contain x and y components")
    x_face = xp.asarray(face_pair[0])
    y_face = xp.asarray(face_pair[1])
    actual = (tuple(x_face.shape), tuple(y_face.shape))
    expected = tuple(tuple(shape) for shape in expected_shapes)
    if actual != expected:
        raise ValueError(
            f"{label} shapes {actual!r} do not match expected {expected!r}"
        )
    return x_face, y_face


def _positive_float(value: float, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return result
