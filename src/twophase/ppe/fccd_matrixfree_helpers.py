"""Helper utilities for `PPESolverFCCDMatrixFree`."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..backend import fuse as _fuse


@dataclass(frozen=True)
class FCCDGeometryCache:
    h_min: list[float]
    node_width: list
    cell_volume: object


@dataclass(frozen=True)
class FCCDPhaseGaugeState:
    pin_dofs: tuple[int, ...]
    phase_threshold: float | None


@dataclass(frozen=True)
class FCCDPhaseMeanGaugeCache:
    masks: tuple
    weights: tuple
    weight_sums: tuple
    weight_stack: object
    weight_sum_stack: object


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
    return FCCDGeometryCache(
        h_min=h_min,
        node_width=node_width,
        cell_volume=xp.asarray(grid.cell_volumes()),
    )


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
    pins = []
    gas_pin = _select_bulk_phase_gauge_pin(
        rho_np,
        phase_mask=rho_np < threshold,
        threshold=threshold,
        rho_extreme=rho_min,
        prefer_low_density=True,
    )
    liquid_pin = _select_bulk_phase_gauge_pin(
        rho_np,
        phase_mask=rho_np >= threshold,
        threshold=threshold,
        rho_extreme=rho_max,
        prefer_low_density=False,
    )
    if gas_pin is not None:
        pins.append(gas_pin)
    if liquid_pin is not None:
        pins.append(liquid_pin)
    return FCCDPhaseGaugeState(
        pin_dofs=tuple(sorted(set(pins))) or (default_pin_dof,),
        phase_threshold=threshold,
    )


def build_fccd_phase_mean_gauge_cache(
    *,
    xp,
    rho,
    cell_volume,
    phase_threshold: float | None,
) -> FCCDPhaseMeanGaugeCache | None:
    if phase_threshold is None:
        return None
    rho_arr = xp.asarray(rho)
    volume = xp.asarray(cell_volume)
    masks = (
        rho_arr < phase_threshold,
        rho_arr >= phase_threshold,
    )
    weights = tuple(xp.where(mask, volume, 0.0) for mask in masks)
    weight_sums = tuple(xp.sum(weight) for weight in weights)
    return FCCDPhaseMeanGaugeCache(
        masks=masks,
        weights=weights,
        weight_sums=weight_sums,
        weight_stack=xp.stack(weights),
        weight_sum_stack=xp.stack(weight_sums),
    )


def compute_fccd_phase_weighted_means(*, xp, arr, cache: FCCDPhaseMeanGaugeCache):
    arr_view = xp.asarray(arr)
    if len(cache.weights) == 2:
        reduction_axes = tuple(range(1, cache.weight_stack.ndim))
        weighted_sums = xp.sum(cache.weight_stack * arr_view, axis=reduction_axes)
        return tuple(
            weighted_sums[i] / cache.weight_sum_stack[i]
            for i in range(len(cache.weights))
        )
    return tuple(
        xp.sum(weight * arr_view) / weight_sum
        for weight, weight_sum in zip(cache.weights, cache.weight_sums)
    )


@_fuse
def _subtract_two_phase_mean_kernel(arr, mask, mean0, mean1):
    return arr - (mask * mean0 + (~mask) * mean1)


def subtract_fccd_phase_means(*, xp, arr, cache: FCCDPhaseMeanGaugeCache, means):
    """Return the phase-gauge projection without copying ``arr`` first.

    A3 mapping: for each phase ``Ω_k``, enforce
    ``p <- p - <p>_k`` with ``<p>_k = Σ_{Ω_k} V_i p_i / Σ_{Ω_k} V_i``.
    """
    arr_view = xp.asarray(arr)
    if len(means) == 2:
        return _subtract_two_phase_mean_kernel(
            arr_view,
            cache.masks[0],
            means[0],
            means[1],
        )
    result = arr_view.copy()
    for mask, mean in zip(cache.masks, means):
        result = xp.where(mask, result - mean, result)
    return result


def _select_bulk_phase_gauge_pin(
    rho_np: np.ndarray,
    *,
    phase_mask: np.ndarray,
    threshold: float,
    rho_extreme: float,
    prefer_low_density: bool,
) -> int | None:
    """Choose a phase gauge in the bulk, away from walls and the interface.

    The Neumann PPE gauge removes only a per-phase constant null mode.  Placing
    the gauge on a diffuse-interface/contact-line row changes a physical
    pressure-jump row into a Dirichlet row, so the selected DOF must be a bulk
    representative whenever such a cell exists.
    """
    if not np.any(phase_mask):
        return None

    denom = abs(threshold - rho_extreme)
    if denom <= 1.0e-14:
        purity = np.ones_like(rho_np, dtype=np.float64)
    elif prefer_low_density:
        purity = (threshold - rho_np) / denom
    else:
        purity = (rho_np - threshold) / denom
    purity = np.clip(purity, 0.0, 1.0)

    bulk_mask = phase_mask & (purity >= 0.95)
    candidate_mask = bulk_mask if np.any(bulk_mask) else phase_mask
    boundary_distance = _grid_boundary_distance(rho_np.shape)
    score = np.where(candidate_mask, boundary_distance + 1.0e-3 * purity, -np.inf)
    return int(np.argmax(score))


def _grid_boundary_distance(shape: tuple[int, ...]) -> np.ndarray:
    """Return index-space distance to the nearest domain boundary."""
    distance = np.full(shape, np.inf, dtype=np.float64)
    ndim = len(shape)
    for axis, size in enumerate(shape):
        axis_index = np.arange(size, dtype=np.float64).reshape(
            (1,) * axis + (size,) + (1,) * (ndim - axis - 1)
        )
        axis_distance = np.minimum(axis_index, size - 1 - axis_index)
        distance = np.minimum(distance, axis_distance)
    return distance


def build_fccd_face_inverse_density(
    *,
    xp,
    rho,
    axis: int,
    ndim: int,
    grid,
    coefficient_scheme: str,
    phase_threshold: float | None,
    interface_coupling_scheme: str = "none",
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
    if (
        coefficient_scheme != "phase_separated"
        or phase_threshold is None
        or interface_coupling_scheme == "affine_jump"
    ):
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
    kappa_dev = xp.asarray(kappa)
    pressure_jump_gas_minus_liquid = -float(sigma) * kappa_dev
    return {
        "psi": xp.asarray(psi),
        "kappa": kappa_dev,
        "pressure_jump_gas_minus_liquid": pressure_jump_gas_minus_liquid,
        "psi_host": None,
        "kappa_host": None,
        "pressure_jump_gas_minus_liquid_host": None,
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
        pressure_jump = interface_jump_context.get("pressure_jump_gas_minus_liquid")
        if pressure_jump is None:
            pressure_jump = -sigma * interface_jump_context["kappa"]
        return pressure_arr + pressure_jump * (1.0 - psi)
    pressure_arr = np.asarray(pressure)
    psi = interface_jump_context.get("psi_host")
    pressure_jump = interface_jump_context.get("pressure_jump_gas_minus_liquid_host")
    if psi is None:
        psi = np.asarray(backend.to_host(interface_jump_context["psi"]))
        interface_jump_context["psi_host"] = psi
    if pressure_jump is None:
        pressure_jump_dev = interface_jump_context.get("pressure_jump_gas_minus_liquid")
        if pressure_jump_dev is None:
            pressure_jump_dev = -sigma * interface_jump_context["kappa"]
        pressure_jump = np.asarray(backend.to_host(pressure_jump_dev))
        interface_jump_context["pressure_jump_gas_minus_liquid_host"] = pressure_jump
    return pressure_arr + pressure_jump * (1.0 - psi)


def project_fccd_rhs_compatibility(
    *,
    rhs,
    xp,
    coefficient_scheme: str,
    phase_threshold: float | None,
    rho_dev,
    rho_host,
    cell_volume_dev,
    cell_volume_host,
    phase_masks,
    phase_weights,
    phase_weight_sums,
    phase_weight_stack,
    phase_weight_sum_stack,
    pin_dofs: tuple[int, ...],
    interface_coupling_scheme: str,
    use_device_density: bool,
    to_scalar,
    pin_rhs: bool = True,
    record_stats: bool = True,
):
    rhs_view = xp.asarray(rhs)
    stats = {
        "ppe_phase_count": 1.0,
        "ppe_pin_count": float(len(pin_dofs) if pin_rhs else 0),
        "ppe_mean_gauge": float(not pin_rhs),
        "ppe_rhs_phase_mean_before_max": 0.0,
        "ppe_rhs_phase_mean_after_max": 0.0,
        "ppe_interface_coupling_jump": float(
            interface_coupling_scheme == "jump_decomposition"
        ),
        "ppe_interface_coupling_affine_jump": float(
            interface_coupling_scheme == "affine_jump"
        ),
    }
    if (
        coefficient_scheme != "phase_separated"
        or phase_threshold is None
        or rho_host is None
    ):
        rhs_projected = rhs_view.copy() if pin_rhs else rhs_view
        if pin_rhs:
            _pin_zero(rhs_projected.ravel(), pin_dofs)
        return rhs_projected, stats

    if phase_masks is None or phase_weights is None or phase_weight_sums is None:
        rho_view = rho_dev if use_device_density else rho_host
        weight_view = cell_volume_dev if use_device_density else cell_volume_host
        cache = build_fccd_phase_mean_gauge_cache(
            xp=xp,
            rho=rho_view,
            cell_volume=weight_view,
            phase_threshold=phase_threshold,
        )
        phase_masks = cache.masks
        phase_weights = cache.weights
        phase_weight_sums = cache.weight_sums
        phase_weight_stack = cache.weight_stack
        phase_weight_sum_stack = cache.weight_sum_stack
    if phase_weight_stack is None:
        phase_weight_stack = xp.stack(phase_weights)
    if phase_weight_sum_stack is None:
        phase_weight_sum_stack = xp.stack(phase_weight_sums)
    means_before_max = 0.0
    means_after_max = 0.0
    phase_cache = FCCDPhaseMeanGaugeCache(
        masks=phase_masks,
        weights=phase_weights,
        weight_sums=phase_weight_sums,
        weight_stack=phase_weight_stack,
        weight_sum_stack=phase_weight_sum_stack,
    )
    phase_means = compute_fccd_phase_weighted_means(
        xp=xp,
        arr=rhs_view,
        cache=phase_cache,
    )
    if record_stats:
        means_before_max = abs(to_scalar(xp.max(xp.abs(xp.stack(phase_means)))))
    rhs_projected = subtract_fccd_phase_means(
        xp=xp,
        arr=rhs_view,
        cache=phase_cache,
        means=phase_means,
    )
    if record_stats:
        means_after_max = abs(
            to_scalar(
                xp.max(
                    xp.abs(
                        xp.stack(
                            compute_fccd_phase_weighted_means(
                                xp=xp,
                                arr=rhs_projected,
                                cache=phase_cache,
                            )
                        )
                    )
                )
            )
        )

    if pin_rhs:
        _pin_zero(rhs_projected.ravel(), pin_dofs)
    stats.update(
        {
            "ppe_phase_count": float(len(phase_means)),
            "ppe_pin_count": float(len(pin_dofs) if pin_rhs else 0),
            "ppe_mean_gauge": float(not pin_rhs),
            "ppe_rhs_phase_mean_before_max": means_before_max,
            "ppe_rhs_phase_mean_after_max": means_after_max,
        }
    )
    return rhs_projected, stats


def _pin_zero(flat, pin_dofs: tuple[int, ...]) -> None:
    for dof in pin_dofs:
        flat[dof] = 0.0
