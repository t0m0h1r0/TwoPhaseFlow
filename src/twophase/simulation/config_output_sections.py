"""Output-section parsing helpers for experiment configs."""

from __future__ import annotations

from .config_models import OutputCfg


def parse_output(d: dict) -> OutputCfg:
    """Parse the output section from experiment YAML."""
    checkpoints = d.get("checkpoints", {}) or {}
    checkpoint_interval = checkpoints.get("interval", d.get("checkpoint_interval"))
    return OutputCfg(
        dir=str(d.get("dir", "results")),
        save_npz=bool(d.get("save_npz", True)),
        figures=list(d.get("figures", [])),
        checkpoint_interval=(
            None if checkpoint_interval is None else float(checkpoint_interval)
        ),
    )
