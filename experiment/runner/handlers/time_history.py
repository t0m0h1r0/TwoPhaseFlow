"""TimeHistoryHandler — record and plot metric trajectories over time.

YAML type: time_history

Runs each case for n_steps steps, recording metrics at each checkpoint.
Plots metrics vs time, optionally overlaying exact solutions.

Scheme adapter interface:
    adapter.run_history(n_steps, dt, checkpoint_interval) -> list[dict]
    Each dict: {"t": float, metric_key: float, ...}
"""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import numpy as np

from ..registry import (
    ExperimentHandler, SCHEME_REGISTRY, SOLUTION_REGISTRY, register_handler,
)
from twophase.tools.experiment import save_results, load_results, save_figure


@register_handler("time_history")
class TimeHistoryHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        base_operator = cfg.scheme.get("operator", "")
        base_params = dict(cfg.scheme.get("params", {}))
        raw_cases = cfg.scheme.get("cases", [])
        if not raw_cases:
            raw_cases = [{"label": "default"}]

        n_steps: int = int(cfg.input.get("n_steps", 200))
        dt: float = float(cfg.input.get("dt", 0.01))
        checkpoint_interval: int = int(cfg.input.get("checkpoint_interval", 1))
        domain: dict = dict(cfg.input.get("domain", {"Lx": 1.0, "Ly": 1.0}))
        N: int = int(cfg.input.get("N", 64))

        all_results: dict[str, list[dict]] = {}

        for case in raw_cases:
            label = case.get("label", "default")
            operator = case.get("operator") or base_operator
            factory = SCHEME_REGISTRY.get(operator)
            if factory is None:
                raise ValueError(
                    f"Unknown scheme '{operator}'. Registered: {sorted(SCHEME_REGISTRY)}"
                )
            case_params = {"N": N, "domain": domain, **base_params,
                           **dict(case.get("params", {}))}
            adapter = factory(**case_params)
            history = adapter.run_history(
                n_steps=n_steps, dt=dt, checkpoint_interval=checkpoint_interval
            )
            all_results[label] = history

        save_results(outdir / "data.npz", all_results)
        return all_results

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            raw = load_results(outdir / "data.npz")
            results = {k: list(v) for k, v in raw.items()}

        vis = cfg.visualization
        panels = vis.get("panels", [{}])
        layout = vis.get("layout", f"1x{len(panels)}")
        nrows, ncols = [int(x) for x in layout.split("x")]

        figw = max(4.5 * ncols, 5.0)
        figh = max(3.5 * nrows, 3.5)
        fig, axes = plt.subplots(nrows, ncols, figsize=(figw, figh), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            metric_keys: list[str] = list(panel.get("metric_keys", []))
            exact_keys: list[str] = list(panel.get("exact_keys", []))
            plot_cases = panel.get("cases", list(results.keys()))
            scale = panel.get("scale", "linear")  # linear / semilogy / loglog

            for case_label in plot_cases:
                rows = results.get(case_label, [])
                if not rows:
                    continue
                ts = [float(r["t"]) for r in rows]
                prefix = f"{case_label} " if len(plot_cases) > 1 else ""

                for key in metric_keys:
                    ys = [float(r.get(key, float("nan"))) for r in rows]
                    label = panel.get("series_labels", {}).get(key, f"{prefix}{key}")
                    _plot_line(ax, ts, ys, label, scale)

                for key in exact_keys:
                    ys = [float(r.get(key, float("nan"))) for r in rows]
                    label = panel.get("series_labels", {}).get(key, f"{prefix}{key}")
                    _plot_line(ax, ts, ys, label, scale, ls="--", color="gray", alpha=0.7)

            ax.set_xlabel(panel.get("xlabel", "$t$"))
            ax.set_ylabel(panel.get("ylabel", "metric"))
            if panel.get("title"):
                ax.set_title(panel["title"])
            if metric_keys or exact_keys:
                ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)

        fig.tight_layout()
        save_figure(fig, outdir / vis.get("output_stem", "time_history"))


def _plot_line(ax, xs, ys, label, scale, ls="-", color=None, alpha=1.0):
    kw = dict(label=label, linestyle=ls, alpha=alpha)
    if color is not None:
        kw["color"] = color
    if scale == "semilogy":
        ax.semilogy(xs, ys, **kw)
    elif scale == "loglog":
        ax.loglog(xs, ys, **kw)
    else:
        ax.plot(xs, ys, **kw)
