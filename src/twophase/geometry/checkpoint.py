"""Checkpoint codec for SP-AO geometric phase state.

Symbol mapping
--------------
``q_C`` -> ``geometric_phase/q``, physical liquid cell-volume owner.
``phi`` -> ``geometric_phase/phi``, compatible nodal gauge.
``S`` -> stored sign/case stratum used to reject stale restart geometry.

This module only serializes already-built :class:`GeometricPhaseState`
instances.  It does not activate the geometric state space in chapter-14
runtime paths.
"""

from __future__ import annotations

import math

from .compatibility_projection import CompatibilityProjectionLedger
from .phase_state import GeometricPhaseState

GEOMETRIC_PHASE_CHECKPOINT_PREFIX = "solver/geometric_phase"

_REQUIRED_KEYS = (
    "q",
    "phi",
    "node_signs",
    "cell_cases",
    "metadata",
    "has_ledger",
)
_LEDGER_FIELDS = (
    "iterations",
    "initial_residual_linf",
    "final_residual_linf",
    "final_residual_l2",
    "sign_margin",
    "delta_surface",
    "min_step_fraction",
)


def has_geometric_phase_checkpoint(
    arrays: dict[str, object],
    *,
    prefix: str = GEOMETRIC_PHASE_CHECKPOINT_PREFIX,
) -> bool:
    """Return whether ``arrays`` contain any geometric phase payload."""
    return any(key.startswith(f"{prefix}/") for key in arrays)


def capture_geometric_phase_checkpoint(
    arrays: dict[str, object],
    state: GeometricPhaseState,
    backend,
    *,
    grid=None,
    prefix: str = GEOMETRIC_PHASE_CHECKPOINT_PREFIX,
    tolerance: float = 1.0e-11,
    require_compatible: bool = True,
) -> None:
    """Store a geometric phase restart payload in ``arrays``.

    Device arrays cross the host boundary only at this explicit checkpoint I/O
    edge.  The restart payload keeps ``q`` and ``phi`` plus the fixed sign/case
    stratum so a later load cannot silently continue on a different
    geometric branch.  ``require_compatible=False`` is reserved for diagnostic
    payloads that are not restartable continuation states.
    """
    if not isinstance(state, GeometricPhaseState):
        raise TypeError("state must be a GeometricPhaseState")
    tolerance = _validate_tolerance(tolerance)
    if require_compatible:
        if grid is None:
            raise ValueError(
                "geometric phase checkpoint requires grid revalidation for "
                "restart state"
            )
        try:
            state = type(state).from_q_phi(
                grid,
                state.q,
                state.phi,
                level=state.stratum.level,
                tolerance=tolerance,
                require_compatible=True,
                ledger=state.ledger,
            )
        except ValueError as exc:
            raise ValueError(
                "geometric phase checkpoint requires compatible q/phi restart state"
            ) from exc
    _put(arrays, f"{prefix}/q", state.q, backend)
    _put(arrays, f"{prefix}/phi", state.phi, backend)
    _put(arrays, f"{prefix}/node_signs", state.stratum.node_signs, backend)
    _put(arrays, f"{prefix}/cell_cases", state.stratum.cell_cases, backend)
    arrays[f"{prefix}/metadata"] = _np(backend).asarray(
        [
            float(state.stratum.level),
            float(state.stratum.sign_margin),
            float(state.compatibility_residual_linf),
            float(state.compatibility_residual_l2),
        ],
        dtype=float,
    )
    has_ledger = state.ledger is not None
    arrays[f"{prefix}/has_ledger"] = _np(backend).asarray(has_ledger, dtype=bool)
    if has_ledger:
        arrays[f"{prefix}/ledger"] = _np(backend).asarray(
            [getattr(state.ledger, field) for field in _LEDGER_FIELDS],
            dtype=float,
        )


def restore_geometric_phase_checkpoint_2d(
    grid,
    arrays: dict[str, object],
    xp,
    *,
    prefix: str = GEOMETRIC_PHASE_CHECKPOINT_PREFIX,
    tolerance: float = 1.0e-11,
    require_compatible: bool = True,
) -> GeometricPhaseState:
    """Rebuild a geometric phase state from checkpoint arrays.

    The stored stratum is rechecked against the reconstructed state.  This
    makes restart equivalence fail closed if the grid, gauge, or cell-case
    branch no longer matches the saved continuation state.
    """
    missing = [key for key in _REQUIRED_KEYS if f"{prefix}/{key}" not in arrays]
    if missing:
        raise ValueError(
            "geometric phase checkpoint is incomplete; missing "
            + ", ".join(missing)
        )
    metadata = arrays[f"{prefix}/metadata"]
    if tuple(metadata.shape) != (4,):
        raise ValueError("geometric phase checkpoint metadata has invalid shape")
    level = float(metadata[0])
    ledger = _restore_ledger(arrays, prefix=prefix)
    state = GeometricPhaseState.from_q_phi(
        grid,
        xp.asarray(arrays[f"{prefix}/q"]),
        xp.asarray(arrays[f"{prefix}/phi"]),
        level=level,
        tolerance=tolerance,
        require_compatible=require_compatible,
        ledger=ledger,
    )
    _validate_stratum(
        xp,
        state,
        stored_node_signs=xp.asarray(arrays[f"{prefix}/node_signs"], dtype=bool),
        stored_cell_cases=xp.asarray(arrays[f"{prefix}/cell_cases"], dtype=int),
    )
    return state


def _restore_ledger(
    arrays: dict[str, object],
    *,
    prefix: str,
) -> CompatibilityProjectionLedger | None:
    has_ledger_value = arrays[f"{prefix}/has_ledger"]
    if tuple(has_ledger_value.shape) != ():
        raise ValueError("geometric phase checkpoint has_ledger flag has invalid shape")
    has_ledger = bool(has_ledger_value)
    if not has_ledger:
        return None
    key = f"{prefix}/ledger"
    if key not in arrays:
        raise ValueError("geometric phase checkpoint declares a missing ledger")
    values = arrays[key]
    if tuple(values.shape) != (len(_LEDGER_FIELDS),):
        raise ValueError("geometric phase checkpoint ledger has invalid shape")
    data = dict(zip(_LEDGER_FIELDS, (float(value) for value in values), strict=True))
    iterations = data["iterations"]
    if not (
        math.isfinite(iterations)
        and iterations >= 0.0
        and iterations.is_integer()
    ):
        raise ValueError("geometric phase checkpoint ledger iterations is invalid")
    data["iterations"] = int(iterations)
    for field in _LEDGER_FIELDS[1:]:
        if not math.isfinite(data[field]):
            raise ValueError(
                f"geometric phase checkpoint ledger {field} is not finite"
            )
    return CompatibilityProjectionLedger(**data)


def _validate_tolerance(tolerance: float) -> float:
    tolerance = float(tolerance)
    if not (math.isfinite(tolerance) and tolerance >= 0.0):
        raise ValueError("tolerance must be finite and non-negative")
    return tolerance


def _validate_stratum(
    xp,
    state: GeometricPhaseState,
    *,
    stored_node_signs,
    stored_cell_cases,
) -> None:
    if tuple(stored_node_signs.shape) != tuple(state.stratum.node_signs.shape):
        raise ValueError("geometric phase checkpoint node-sign stratum shape mismatch")
    if tuple(stored_cell_cases.shape) != tuple(state.stratum.cell_cases.shape):
        raise ValueError("geometric phase checkpoint cell-case stratum shape mismatch")
    if _scalar_bool(xp, xp.any(stored_node_signs != state.stratum.node_signs)):
        raise ValueError("geometric phase checkpoint node-sign stratum is stale")
    if _scalar_bool(xp, xp.any(stored_cell_cases != state.stratum.cell_cases)):
        raise ValueError("geometric phase checkpoint cell-case stratum is stale")


def _put(arrays: dict[str, object], key: str, value, backend) -> None:
    arrays[key] = _np(backend).array(backend.to_host(value), copy=True)


def _np(backend):
    # The on-disk checkpoint format is NumPy, even for CUDA-backed runs.
    import numpy

    return numpy


def _scalar_bool(xp, value) -> bool:
    if hasattr(value, "get"):
        value = value.get()
    return bool(value)
