"""Reinitialization and projection helpers for run-section parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config_run_tracking_sections import (
    coefficient_to_projection_mode,
    parse_projection_mode,
)

_REINIT_METHODS = (
    "split", "unified", "dgr", "hybrid",
    "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
)


@dataclass(frozen=True)
class RunReinitProjectionState:
    reproject_mode: str
    reinit_method: str | None
    ridge_sigma_0: float


def parse_run_reinit_projection(
    *,
    reinit: dict[str, Any],
    reinit_profile: dict[str, Any],
    projection: dict[str, Any],
    poisson_coefficient: str,
    projection_mode_path: str,
) -> RunReinitProjectionState:
    reproject_mode = parse_projection_mode(
        projection.get(
            "mode",
            coefficient_to_projection_mode(poisson_coefficient),
        ),
        projection_mode_path,
    )
    reinit_method = reinit["algorithm"]
    if reinit_method is not None and reinit_method not in _REINIT_METHODS:
        raise ValueError(
            f"interface.reinitialization.algorithm must be one of {_REINIT_METHODS}, "
            f"got {reinit_method!r}"
        )
    ridge_sigma_0 = float(reinit_profile.get("ridge_sigma_0", 3.0))
    if ridge_sigma_0 <= 0.0:
        raise ValueError(
            "interface.reinitialization.profile.ridge_sigma_0 must be > 0, "
            f"got {ridge_sigma_0}"
        )
    return RunReinitProjectionState(
        reproject_mode=reproject_mode,
        reinit_method=reinit_method,
        ridge_sigma_0=ridge_sigma_0,
    )
