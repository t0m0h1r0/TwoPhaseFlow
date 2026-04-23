"""YAML loading and top-level config assembly helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config_output_sections import parse_output


def require_pyyaml() -> Any:
    """Import PyYAML only when YAML loading is requested."""
    try:
        import yaml
        return yaml
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required to load experiment YAML files. "
            "Install it with `pip install pyyaml` or `pip install twophase[io]`."
        ) from exc


def load_experiment_config(path: str | Path):
    """Load ``ExperimentConfig`` from a YAML file."""
    from .config_models import ExperimentConfig

    return ExperimentConfig.from_yaml(path)


def parse_raw(raw: dict):
    """Assemble ``ExperimentConfig`` from a raw YAML/dict payload."""
    from .config_models import ExperimentConfig
    from .config_run_sections import parse_run
    from .config_sections import parse_grid, parse_physics

    interface = raw["interface"]
    numerics = raw["numerics"]
    grid = parse_grid(raw["grid"], interface)
    physics = parse_physics(raw["physics"])
    output = parse_output(raw.get("output", {}))
    run = parse_run(raw["run"], interface, numerics, raw.get("output", {}))
    return ExperimentConfig(
        grid=grid,
        physics=physics,
        run=run,
        output=output,
        diagnostics=list(raw.get("diagnostics", [])),
        initial_condition=dict(raw.get("initial_condition", {})),
        initial_velocity=raw.get("initial_velocity") or None,
        boundary_condition=raw.get("boundary_condition") or None,
        sweep=raw.get("sweep") or None,
    )
