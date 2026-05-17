"""Phase-region component-measure reductions.

Symbol mapping
--------------
``R_h`` -> ``PhaseRegionBatch`` discrete phase-region owner.
``Q_h(R_h)`` -> batch cell measure assembled from component measures.
``E_h(R_h)`` -> batch perimeter sum assembled from component perimeters.
``q_T`` -> optional transported finite-volume measure.
``r`` -> optional residual ``q_T - Q_h(R_h)``.

This module only reduces already-measured component arrays.  It does not
construct chart gauges, reconstruct ``phi``, solve an admission problem, build
capillary forces, or project pressure/velocity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .interface_atlas import AtlasValidationError, PhaseRegionBatch


@dataclass(frozen=True)
class PhaseRegionMeasurement:
    """Batched phase-region measure and residual diagnostics."""

    q_phys: object
    residual: object | None
    component_volumes: object
    batch_volumes: object
    component_perimeters: object
    batch_perimeters: object
    residual_l2: float | None
    residual_linf: float | None
    residual_volume: object | None
    q_min: float | None
    capacity_excess_linf: float | None
    force_admissible: bool


def assemble_phase_region_measurement(
    region: PhaseRegionBatch,
    component_q: object,
    component_perimeters: object,
    *,
    q_target: object | None = None,
    cell_area: object | None = None,
    capacity_tolerance: float = 1.0e-12,
) -> PhaseRegionMeasurement:
    """Assemble ``q_phys`` and perimeter sums from component measures.

    Args:
        region: Phase-region owner whose atlas maps components to batches.
        component_q: Component cell measures with shape
            ``(n_components, *grid_shape)``.
        component_perimeters: Per-component perimeter values with shape
            ``(n_components,)``.
        q_target: Optional transported target measure.  Shape may be
            ``grid_shape`` for one batch or ``(batch_size, *grid_shape)``.
        cell_area: Optional cell capacity with shape ``grid_shape``.
        capacity_tolerance: Allowed numerical tolerance for lower/upper cell
            capacity checks when ``cell_area`` is provided.

    Returns:
        A ``PhaseRegionMeasurement``.  ``force_admissible`` is always false at
        this stage because force admission requires a later ``T_h^*`` work
        identity gate.
    """
    if not isinstance(region, PhaseRegionBatch):
        raise AtlasValidationError("region must be a PhaseRegionBatch")
    q_comp = np.asarray(component_q, dtype=float)
    if q_comp.ndim < 2:
        raise AtlasValidationError("component_q must have shape (n_components, *grid)")
    if q_comp.shape[0] != region.n_components:
        raise AtlasValidationError("component_q first axis must match atlas components")
    if not np.all(np.isfinite(q_comp)):
        raise AtlasValidationError("component_q must be finite")

    perimeters = np.asarray(component_perimeters, dtype=float)
    if perimeters.shape != (region.n_components,):
        raise AtlasValidationError("component_perimeters must have shape (n_components,)")
    if not np.all(np.isfinite(perimeters)):
        raise AtlasValidationError("component_perimeters must be finite")
    if np.any(perimeters < 0.0):
        raise AtlasValidationError("component_perimeters must be nonnegative")

    grid_shape = q_comp.shape[1:]
    q_phys = np.zeros((region.batch_size,) + grid_shape, dtype=float)
    np.add.at(q_phys, region.atlas.component_to_batch, q_comp)
    component_volumes = np.sum(q_comp, axis=tuple(range(1, q_comp.ndim)))
    batch_volumes = np.bincount(
        region.atlas.component_to_batch,
        weights=component_volumes,
        minlength=region.batch_size,
    )
    batch_perimeters = np.bincount(
        region.atlas.component_to_batch,
        weights=perimeters,
        minlength=region.batch_size,
    )

    q_min: float | None = None
    capacity_excess_linf: float | None = None
    if cell_area is not None:
        area = np.asarray(cell_area, dtype=float)
        if area.shape != grid_shape:
            raise AtlasValidationError("cell_area must have shape grid_shape")
        if not np.all(np.isfinite(area)) or np.any(area <= 0.0):
            raise AtlasValidationError("cell_area must be positive and finite")
        q_min = float(np.min(q_phys))
        capacity_excess_linf = float(np.max(q_phys - area[None, ...]))
        tol = float(capacity_tolerance)
        if q_min < -tol:
            raise AtlasValidationError("q_phys is below zero beyond tolerance")
        if capacity_excess_linf > tol:
            raise AtlasValidationError("q_phys exceeds cell capacity beyond tolerance")

    residual = None
    residual_l2 = None
    residual_linf = None
    residual_volume = None
    if q_target is not None:
        target = _target_with_batch_axis(q_target, region.batch_size, grid_shape)
        residual = target - q_phys
        residual_l2 = float(np.sqrt(np.sum(residual * residual)))
        residual_linf = float(np.max(np.abs(residual)))
        residual_volume = np.sum(residual, axis=tuple(range(1, residual.ndim)))

    return PhaseRegionMeasurement(
        q_phys=q_phys,
        residual=residual,
        component_volumes=component_volumes,
        batch_volumes=batch_volumes,
        component_perimeters=perimeters,
        batch_perimeters=batch_perimeters,
        residual_l2=residual_l2,
        residual_linf=residual_linf,
        residual_volume=residual_volume,
        q_min=q_min,
        capacity_excess_linf=capacity_excess_linf,
        force_admissible=False,
    )


def _target_with_batch_axis(target: object, batch_size: int, grid_shape: tuple[int, ...]) -> object:
    arr = np.asarray(target, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise AtlasValidationError("q_target must be finite")
    if batch_size == 1 and arr.shape == grid_shape:
        return arr[None, ...]
    if arr.shape == (int(batch_size),) + grid_shape:
        return arr
    raise AtlasValidationError("q_target shape must be grid_shape or (batch_size, *grid_shape)")

