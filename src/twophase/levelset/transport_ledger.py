"""Stage-native conservative transport ledgers.

Symbol mapping:
    ``q`` -> CLS phase field ``psi``.
    ``F_q`` -> phase face flux used by FCCD transport.
    ``F_V`` -> face-normal volume flux, equal to the projected face velocity.
    ``F_M`` -> mass flux reconstructed by consumers from ``F_q`` and ``F_V``.

The ledger stores backend arrays as-is.  CPU/GPU transfers are intentionally
left to explicit diagnostic boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TransportStageLedger:
    """One Shu-Osher stage of projection-native CLS transport."""

    name: str
    phase_fluxes: tuple[Any, ...]
    base_weight: float
    candidate_weight: float
    post_stage_projected: bool = False


@dataclass
class TransportLedger:
    """Flux ledger for one physical transport step."""

    dt: float
    face_volume_fluxes: tuple[Any, ...]
    stages: tuple[TransportStageLedger, ...]
    psi_before: Any
    psi_after_transport: Any
    clip_bounds: tuple[float, float] | None = None
    mass_correction_applied: bool = False
    zero_velocity: bool = False

