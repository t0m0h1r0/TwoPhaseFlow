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

__all__ = ["ICNAdvance", "PicardCNAdvance", "make_cn_advance"]


def make_cn_advance(backend, mode: str = "picard") -> ICNAdvance:
    """Factory: map ``config.numerics.cn_mode`` string to a strategy instance.

    Parameters
    ----------
    backend : Backend
    mode    : 'picard' — current production (1-step Picard / Heun).
              Future: 'richardson_picard', 'implicit', 'pade22',
              'richardson_pade22' (Phase 2-6).

    Raises
    ------
    ValueError
        If ``mode`` is not a known strategy.
    """
    if mode == "picard":
        return PicardCNAdvance(backend)
    raise ValueError(
        f"Unknown cn_mode={mode!r}; supported in this build: 'picard'. "
        f"Richardson/Implicit/Pade22 variants are tracked in "
        f"docs/memo/extended_cn_impl_design.md."
    )
