"""YAML → ComponentConfig dataclass for ch11/ch12 component-level experiments."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComponentConfig:
    """Parsed YAML config for a component-level experiment (ch11/ch12)."""
    experiment: dict = field(default_factory=dict)
    scheme: dict = field(default_factory=dict)
    schemes: list = field(default_factory=list)   # for scheme_comparison
    input: dict = field(default_factory=dict)
    reference: dict = field(default_factory=dict)
    diagnostics: list = field(default_factory=list)
    visualization: dict = field(default_factory=dict)
    sweep: list | None = None


def load_component_config(path: str | pathlib.Path) -> ComponentConfig:
    """Load a YAML file and return a ComponentConfig."""
    try:
        import yaml
    except ImportError as e:
        raise ImportError("PyYAML required: pip install pyyaml") from e

    path = pathlib.Path(path)
    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    return ComponentConfig(
        experiment=dict(raw.get("experiment", {})),
        scheme=dict(raw.get("scheme", {})),
        schemes=list(raw.get("schemes", [])),
        input=dict(raw.get("input", {})),
        reference=dict(raw.get("reference", {})),
        diagnostics=list(raw.get("diagnostics", [])),
        visualization=dict(raw.get("visualization", {})),
        sweep=raw.get("sweep") or None,
    )
