"""Run-section context extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config_run_layout_sections import parse_numerics_layout


@dataclass(frozen=True)
class RunParseContext:
    time_cfg: dict[str, Any]
    snapshots: dict[str, Any]
    reinit: dict[str, Any]
    reinit_profile: dict[str, Any]
    reinit_schedule: dict[str, Any]
    interface_curvature: dict[str, Any]
    layout: dict[str, Any]
    tracking: dict[str, Any]
    projection: dict[str, Any]
    debug: dict[str, Any]


def build_run_parse_context(
    *,
    run_section: dict[str, Any],
    interface: dict[str, Any],
    numerics: dict[str, Any],
    output: dict[str, Any] | None = None,
) -> RunParseContext:
    """Extract normalized run-section context from raw YAML fragments."""
    output = output or {}
    reinit = interface["reinitialization"]
    interface_geometry = interface.get("geometry", {}) or {}
    layout = parse_numerics_layout(numerics)
    return RunParseContext(
        time_cfg=run_section["time"],
        snapshots=output.get("snapshots", {}) or {},
        reinit=reinit,
        reinit_profile=reinit.get("profile", {}) or {},
        reinit_schedule=reinit["schedule"],
        interface_curvature=interface_geometry.get("curvature", {}) or {},
        layout=layout,
        tracking=layout["tracking"],
        projection=layout["projection"],
        debug=run_section.get("debug", {}) or {},
    )
