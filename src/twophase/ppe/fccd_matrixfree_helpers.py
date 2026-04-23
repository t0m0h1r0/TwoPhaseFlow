"""Helper utilities for `PPESolverFCCDMatrixFree`."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FCCDGeometryCache:
    h_min: list[float]
    node_width: list


@dataclass(frozen=True)
class FCCDPhaseGaugeState:
    pin_dofs: tuple[int, ...]
    phase_threshold: float | None


def build_fccd_geometry_cache(*, xp, grid, ndim: int) -> FCCDGeometryCache:
    h_min = []
    node_width = []
    for axis in range(ndim):
        coords = np.asarray(grid.coords[axis], dtype=np.float64)
        face_width = coords[1:] - coords[:-1]
        node_axis = np.empty_like(coords)
        node_axis[0] = 0.5 * face_width[0]
        node_axis[-1] = 0.5 * face_width[-1]
        node_axis[1:-1] = 0.5 * (coords[2:] - coords[:-2])
        h_min.append(float(np.min(face_width)))
        node_width.append(xp.asarray(node_axis))
    return FCCDGeometryCache(h_min=h_min, node_width=node_width)


def compute_fccd_phase_gauges(
    *,
    rho_host,
    coefficient_scheme: str,
    default_pin_dof: int,
) -> FCCDPhaseGaugeState:
    if coefficient_scheme != "phase_separated":
        return FCCDPhaseGaugeState(pin_dofs=(default_pin_dof,), phase_threshold=None)
    rho_np = np.asarray(rho_host, dtype=np.float64)
    rho_min = float(np.min(rho_np))
    rho_max = float(np.max(rho_np))
    if not np.isfinite(rho_min + rho_max) or abs(rho_max - rho_min) < 1.0e-14:
        return FCCDPhaseGaugeState(pin_dofs=(default_pin_dof,), phase_threshold=None)

    threshold = 0.5 * (rho_min + rho_max)
    gas = np.flatnonzero(rho_np.ravel() < threshold)
    liquid = np.flatnonzero(rho_np.ravel() >= threshold)
    pins = []
    if gas.size:
        pins.append(int(gas[0]))
    if liquid.size:
        pins.append(int(liquid[0]))
    return FCCDPhaseGaugeState(
        pin_dofs=tuple(sorted(set(pins))) or (default_pin_dof,),
        phase_threshold=threshold,
    )


def build_fccd_face_inverse_density(
    *,
    xp,
    rho,
    axis: int,
    ndim: int,
    grid,
    coefficient_scheme: str,
    phase_threshold: float | None,
):
    rho_arr = xp.asarray(rho)
    n_axis = grid.N[axis]

    def sl(start, stop):
        slices = [slice(None)] * ndim
        slices[axis] = slice(start, stop)
        return tuple(slices)

    rho_lo = rho_arr[sl(0, n_axis)]
    rho_hi = rho_arr[sl(1, n_axis + 1)]
    coeff = 2.0 / (rho_lo + rho_hi)
    if coefficient_scheme != "phase_separated" or phase_threshold is None:
        return coeff
    same_phase = (rho_lo >= phase_threshold) == (rho_hi >= phase_threshold)
    return xp.where(same_phase, coeff, 0.0)


def build_fccd_jacobi_inverse(
    *,
    xp,
    rho_dev,
    h_min: list[float],
    pin_dofs: tuple[int, ...],
):
    diag = xp.zeros_like(rho_dev)
    for axis_h in h_min:
        diag -= 2.0 / (rho_dev * float(axis_h) * float(axis_h))
    flat = diag.ravel()
    for dof in pin_dofs:
        flat[dof] = 1.0
    return 1.0 / xp.where(xp.abs(diag) > 1.0e-30, diag, 1.0)
