"""Explicit phase-owner maps for finite-volume cell measures.

Symbol mapping
--------------
``q_l`` -> runtime liquid cell measure, e.g. ``GeometricPhaseState.q``.
``q_g`` -> gas cell measure owned by the current ``PhaseRegionBatch`` theory.
``|C|`` -> finite-volume cell capacity ``cell_area``.
``q_owner`` -> cell measure after declaring the target owner phase.

This module only converts already-owned finite-volume measures between phase
owners.  It does not build charts, reconstruct ``phi``, solve admission,
transport volume, build forces, or project pressure/velocity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from ..backend import array_namespace, scalar_value
from .interface_atlas import AtlasValidationError


class CellMeasurePhase(IntEnum):
    """Finite-volume phase owner of one cell-measure array."""

    LIQUID = 1
    GAS = 2


@dataclass(frozen=True)
class PhaseOwnerMapResult:
    """Result of an explicit phase-owner conversion."""

    q_owner: object
    q_source: object
    cell_area: object
    source_phase: CellMeasurePhase
    owner_phase: CellMeasurePhase
    complement_used: bool
    source_volume: float
    owner_volume: float
    q_min: float
    capacity_excess_linf: float


def map_cell_measure_to_phase_owner(
    q_source: object,
    cell_area: object,
    *,
    source_phase: CellMeasurePhase | int | str,
    owner_phase: CellMeasurePhase | int | str,
    capacity_tolerance: float = 1.0e-12,
) -> PhaseOwnerMapResult:
    """Map a cell measure to an explicitly declared owner phase.

    The only admitted cross-phase map at this layer is the exact finite-volume
    complement:

    ```text
    q_owner = |C| - q_source,  source_phase != owner_phase.
    ```

    Args:
        q_source: Source cell measure.
        cell_area: Cell capacity with the same shape as ``q_source``.
        source_phase: Phase currently owned by ``q_source``.
        owner_phase: Phase required by the consumer.
        capacity_tolerance: Allowed lower/upper capacity tolerance.

    Returns:
        ``PhaseOwnerMapResult`` with the converted measure and a visible
        ``complement_used`` flag.
    """
    xp = array_namespace(q_source)
    q = xp.asarray(q_source, dtype=float)
    area = xp.asarray(cell_area, dtype=float)
    if q.shape != area.shape:
        raise AtlasValidationError("q_source and cell_area must have the same shape")
    if q.ndim == 0:
        raise AtlasValidationError("q_source must be an array of cell measures")
    if not _bool_scalar(xp.all(xp.isfinite(q))):
        raise AtlasValidationError("q_source must be finite")
    if not _bool_scalar(xp.all(xp.isfinite(area))) or _bool_scalar(xp.any(area <= 0.0)):
        raise AtlasValidationError("cell_area must be positive and finite")

    tol = float(capacity_tolerance)
    if not np.isfinite(tol) or tol < 0.0:
        raise AtlasValidationError("capacity_tolerance must be finite and nonnegative")
    _validate_capacity(q, area, tol, "q_source", xp=xp)

    source = _coerce_phase(source_phase, "source_phase")
    owner = _coerce_phase(owner_phase, "owner_phase")
    complement_used = source != owner
    q_owner = area - q if complement_used else q.copy()
    _validate_capacity(q_owner, area, tol, "q_owner", xp=xp)

    return PhaseOwnerMapResult(
        q_owner=q_owner,
        q_source=q.copy(),
        cell_area=area.copy(),
        source_phase=source,
        owner_phase=owner,
        complement_used=bool(complement_used),
        source_volume=scalar_value(xp.sum(q)),
        owner_volume=scalar_value(xp.sum(q_owner)),
        q_min=scalar_value(xp.min(q_owner)),
        capacity_excess_linf=scalar_value(xp.max(q_owner - area)),
    )


def _coerce_phase(value: CellMeasurePhase | int | str, name: str) -> CellMeasurePhase:
    if isinstance(value, CellMeasurePhase):
        return value
    if isinstance(value, str):
        key = value.strip().upper()
        if key in CellMeasurePhase.__members__:
            return CellMeasurePhase[key]
        raise AtlasValidationError(f"{name} must be LIQUID or GAS")
    try:
        return CellMeasurePhase(int(value))
    except (TypeError, ValueError) as exc:
        raise AtlasValidationError(f"{name} must be LIQUID or GAS") from exc


def _validate_capacity(q: object, area: object, tol: float, name: str, *, xp) -> None:
    if scalar_value(xp.min(q)) < -tol:
        raise AtlasValidationError(f"{name} is below zero beyond tolerance")
    if scalar_value(xp.max(q - area)) > tol:
        raise AtlasValidationError(f"{name} exceeds cell capacity beyond tolerance")


def _bool_scalar(value: object) -> bool:
    return bool(scalar_value(value))
