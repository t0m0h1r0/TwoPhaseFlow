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


def build_fccd_interface_jump_context(*, xp, backend, psi, kappa, sigma: float) -> dict:
    return {
        "psi": xp.asarray(psi),
        "kappa": xp.asarray(kappa),
        "psi_host": np.asarray(backend.to_host(psi)),
        "kappa_host": np.asarray(backend.to_host(kappa)),
        "sigma": float(sigma),
    }


def fccd_interface_jump_is_active(
    *,
    coefficient_scheme: str,
    interface_coupling_scheme: str,
    interface_jump_context: dict | None,
) -> bool:
    """Return whether the SP-M pressure-jump decomposition is active."""
    return (
        coefficient_scheme == "phase_separated"
        and interface_coupling_scheme == "jump_decomposition"
        and interface_jump_context is not None
        and float(interface_jump_context.get("sigma", 0.0)) > 0.0
    )


def apply_fccd_interface_jump(
    *,
    pressure,
    coefficient_scheme: str,
    interface_coupling_scheme: str,
    interface_jump_context: dict | None,
    backend,
    xp,
    is_device_array,
):
    if (
        coefficient_scheme != "phase_separated"
        or interface_coupling_scheme != "jump_decomposition"
        or interface_jump_context is None
    ):
        return pressure
    sigma = interface_jump_context["sigma"]
    if sigma <= 0.0:
        return pressure
    if backend.is_gpu() and is_device_array(pressure):
        pressure_arr = xp.asarray(pressure)
        psi = interface_jump_context["psi"]
        kappa = interface_jump_context["kappa"]
        return pressure_arr + sigma * kappa * (1.0 - psi)
    pressure_arr = np.asarray(pressure)
    psi = interface_jump_context["psi_host"]
    kappa = interface_jump_context["kappa_host"]
    return pressure_arr + sigma * kappa * (1.0 - psi)


def project_fccd_rhs_compatibility(
    *,
    rhs,
    xp,
    coefficient_scheme: str,
    phase_threshold: float | None,
    rho_dev,
    rho_host,
    pin_dofs: tuple[int, ...],
    interface_coupling_scheme: str,
    use_device_density: bool,
    to_scalar,
):
    rhs_projected = xp.asarray(rhs).copy()
    stats = {
        "ppe_phase_count": 1.0,
        "ppe_pin_count": float(len(pin_dofs)),
        "ppe_rhs_phase_mean_before_max": 0.0,
        "ppe_rhs_phase_mean_after_max": 0.0,
        "ppe_interface_coupling_jump": float(
            interface_coupling_scheme == "jump_decomposition"
        ),
    }
    if (
        coefficient_scheme != "phase_separated"
        or phase_threshold is None
        or rho_host is None
    ):
        _pin_zero(rhs_projected.ravel(), pin_dofs)
        return rhs_projected, stats

    rho_view = rho_dev if use_device_density else rho_host
    phase_masks = (
        rho_view < phase_threshold,
        rho_view >= phase_threshold,
    )
    means_before = []
    means_after = []
    phase_count = 0
    for mask in phase_masks:
        count = int(to_scalar(xp.sum(mask)))
        if count == 0:
            continue
        phase_count += 1
        mean = xp.sum(xp.where(mask, rhs_projected, 0.0)) / count
        means_before.append(abs(to_scalar(mean)))
        rhs_projected = xp.where(mask, rhs_projected - mean, rhs_projected)
        mean_after = xp.sum(xp.where(mask, rhs_projected, 0.0)) / count
        means_after.append(abs(to_scalar(mean_after)))

    _pin_zero(rhs_projected.ravel(), pin_dofs)
    stats.update(
        {
            "ppe_phase_count": float(phase_count),
            "ppe_pin_count": float(len(pin_dofs)),
            "ppe_rhs_phase_mean_before_max": max(means_before, default=0.0),
            "ppe_rhs_phase_mean_after_max": max(means_after, default=0.0),
        }
    )
    return rhs_projected, stats


def _pin_zero(flat, pin_dofs: tuple[int, ...]) -> None:
    for dof in pin_dofs:
        flat[dof] = 0.0
