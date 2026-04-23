"""Tracking and projection parsing helpers for run-section config handling."""

from __future__ import annotations

from typing import Any

_PROJECTION_MODES = (
    "legacy", "variable_density", "iim", "gfm", "consistent_iim", "consistent_gfm",
)
_PROJECTION_MODE_ALIASES = {
    "standard": "legacy",
    "variable_density_only": "variable_density",
    "pressure_jump": "consistent_gfm",
}
_PROJECTION_TO_REPROJECT_MODE = {
    "legacy": "legacy",
    "variable_density": "variable_density_only",
    "iim": "iim",
    "gfm": "gfm",
    "consistent_iim": "consistent_iim",
    "consistent_gfm": "consistent_gfm",
}


def parse_enabled(raw: Any) -> bool:
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"true", "yes", "on", "1", "enabled"}:
            return True
        if value in {"false", "no", "off", "0", "disabled"}:
            return False
    return bool(raw)


def parse_tracking_method(
    tracking: dict,
    path: str = "numerics.interface.tracking.primary",
) -> str:
    if not parse_tracking_enabled(tracking):
        return "none"
    primary = str(tracking["primary"]).strip().lower()
    if primary == "phi":
        return "phi_primary"
    if primary == "psi":
        return "psi_direct"
    if primary == "none":
        return "none"
    raise ValueError(f"{path} must be phi|psi|none, got {primary!r}")


def parse_tracking_enabled(tracking: dict) -> bool:
    if "enabled" in tracking:
        return parse_enabled(tracking.get("enabled"))
    return str(tracking["primary"]).strip().lower() != "none"


def parse_tracking_primary(
    tracking: dict,
    path: str = "numerics.interface.tracking.primary",
) -> bool:
    return parse_tracking_method(tracking, path) == "phi_primary"


def tracking_redistance(tracking: dict) -> dict:
    return tracking.get("redistance", {}) or {}


def parse_tracking_redistance_every(
    tracking: dict,
    path: str = "numerics.interface.tracking.redistance.schedule.every_steps",
) -> int:
    schedule = (tracking_redistance(tracking).get("schedule", {}) or {})
    every = int(schedule.get("every_steps", 4))
    if every <= 0:
        raise ValueError(f"{path} must be > 0")
    return every


def parse_projection_mode(raw: Any, path: str = "numerics.projection.mode") -> str:
    mode = str(raw).strip().lower()
    mode = _PROJECTION_MODE_ALIASES.get(mode, mode)
    if mode not in _PROJECTION_MODES:
        raise ValueError(f"{path} must be one of {_PROJECTION_MODES}, got {raw!r}")
    return _PROJECTION_TO_REPROJECT_MODE[mode]


def coefficient_to_projection_mode(coefficient: str) -> str:
    if coefficient == "phase_density":
        return "variable_density"
    if coefficient == "phase_separated":
        return "gfm"
    raise ValueError(f"Unsupported PPE coefficient model: {coefficient!r}")
