"""Figure generation from YAML ``figures:`` specs.

This module is a thin compatibility facade that dispatches to specialized
snapshot and time-series renderers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .plot_series_figures import (
    convergence,
    deformation_comparison,
    time_series,
)
from .plot_snapshot_figures import (
    density_snapshot,
    pressure_snapshot,
    snapshot,
    snapshot_series,
    velocity_snapshot,
)

if TYPE_CHECKING:
    from ..simulation.config_models import ExperimentConfig


FigureRenderer = Callable[[dict, dict, "ExperimentConfig"], plt.Figure]


_FIGURE_RENDERERS: dict[str, FigureRenderer] = {
    "snapshot": snapshot,
    "time_series": time_series,
    "convergence": convergence,
    "deformation_comparison": deformation_comparison,
    "velocity_snapshot": velocity_snapshot,
    "pressure_snapshot": pressure_snapshot,
    "density_snapshot": density_snapshot,
}


def generate_figures(cfg: "ExperimentConfig", results: dict, outdir: str | Path) -> None:
    """Generate and save all figures defined in ``cfg.output.figures``."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for spec in cfg.output.figures:
        fig_type = spec.get("type", "")
        try:
            if fig_type == "snapshot_series":
                snapshot_series(spec, results, cfg, outdir)
                continue
            fig = _make_figure(fig_type, spec, results, cfg)
            fig.savefig(outdir / spec.get("file", f"{fig_type}.pdf"), bbox_inches="tight")
            plt.close(fig)
        except Exception as exc:
            print(f"[plot_factory] WARNING: failed to generate '{fig_type}': {exc}")


def _make_figure(
    fig_type: str,
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    """Dispatch one figure spec to the registered renderer."""
    renderer = _FIGURE_RENDERERS.get(fig_type)
    if renderer is None:
        raise ValueError(f"Unknown figure type '{fig_type}'.")
    return renderer(spec, results, cfg)


__all__ = ["generate_figures"]
