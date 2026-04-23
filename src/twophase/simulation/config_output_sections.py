"""Output-section parsing helpers for experiment configs."""

from __future__ import annotations

from .config_models import OutputCfg


def parse_output(d: dict) -> OutputCfg:
    """Parse the output section from experiment YAML."""
    return OutputCfg(
        dir=str(d.get("dir", "results")),
        save_npz=bool(d.get("save_npz", True)),
        figures=list(d.get("figures", [])),
    )
