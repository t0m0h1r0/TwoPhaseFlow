"""
CN viscous time-advance strategies (Strategy pattern).

Each strategy implements ICNAdvance and represents a different way to advance
the viscous predictor step u^n -> u*. The canonical production behaviour is
PicardCNAdvance (1-step Picard on CN = Heun predictor-corrector); Richardson
extrapolation and Padé-(2,2) variants are introduced in later Extended CN
phases.

See docs/memo/extended_cn_impl_design.md for the design rationale.
"""
from __future__ import annotations
from .base import ICNAdvance
from .picard_cn import PicardCNAdvance
from .richardson_cn import RichardsonCNAdvance

__all__ = [
    "ICNAdvance",
    "PicardCNAdvance",
    "RichardsonCNAdvance",
    "make_cn_advance",
]


def make_cn_advance(backend, mode: str = "picard") -> ICNAdvance:
    """Factory: map ``config.numerics.cn_mode`` string to a strategy instance.

    Parameters
    ----------
    backend : Backend
    mode    : 'picard'            — 1-step Picard / Heun (default, current
                                    production).
              'richardson_picard' — Richardson(4 u_{Δt/2,2} − u_Δt)/3
                                    wrapping Picard. O(Δt^3) viscous
                                    diagonal (Richardson +1 gain on a
                                    non-symmetric base; NOT +2 to O(Δt^4) —
                                    that requires a symmetric base, see
                                    Phase 3/4 in the design memo); explicit
                                    stability floor inherited from Picard.
              Future: 'implicit', 'pade22', 'richardson_pade22' (Phases 3–6).

    Raises
    ------
    ValueError
        If ``mode`` is not a known strategy.
    """
    if mode == "picard":
        return PicardCNAdvance(backend)
    if mode == "richardson_picard":
        return RichardsonCNAdvance(PicardCNAdvance(backend))
    raise ValueError(
        f"Unknown cn_mode={mode!r}; supported in this build: "
        f"'picard', 'richardson_picard'. Implicit/Pade22 variants are "
        f"tracked in docs/memo/extended_cn_impl_design.md."
    )
