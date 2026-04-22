"""ParameterSweepHandler — sweep a single scalar parameter and plot metric vs param.

YAML type: parameter_sweep

Runs the scheme at each value of `sweep.param` (replacing the named param in
scheme.params), records the adapter's compute_result() output, and plots
one or more metrics vs the parameter value.
"""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import numpy as np

from ..registry import (
    ExperimentHandler, SCHEME_REGISTRY, SOLUTION_REGISTRY, register_handler,
)
from twophase.tools.experiment import save_results, load_results, save_figure


@register_handler("parameter_sweep")
class ParameterSweepHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        scheme_name = cfg.scheme.get("operator")
        factory = SCHEME_REGISTRY.get(scheme_name)
        if factory is None:
            raise ValueError(f"Unknown scheme '{scheme_name}'. Registered: {sorted(SCHEME_REGISTRY)}")

        base_params = dict(cfg.scheme.get("params", {}))
        sweep_cfg: dict = dict(cfg.sweep or {})
        param_name: str = sweep_cfg.get("param", "")
        param_values: list = list(sweep_cfg.get("values", []))
        domain: dict = dict(cfg.input.get("domain", {"Lx": 1.0, "Ly": 1.0}))
        N: int = int(cfg.input.get("N", cfg.input.get("grid_sizes", [64])[0]))

        rows: list[dict] = []
        for val in param_values:
            params = {**base_params, param_name: val}
            adapter = factory(N=N, domain=domain, **params)
            result = adapter.compute_result()
            row = {param_name: val, **result}
            rows.append(row)

        save_results(outdir / "data.npz", {"results": rows})
        return {"results": rows}

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            raw = load_results(outdir / "data.npz")
            results = {"results": list(raw.get("results", []))}

        rows = list(results["results"])
        vis = cfg.visualization
        panels = vis.get("panels", [{}])
        layout = vis.get("layout", f"1x{len(panels)}")
        nrows, ncols = [int(x) for x in layout.split("x")]

        sweep_cfg = dict(cfg.sweep or {})
        param_name = sweep_cfg.get("param", list(rows[0].keys())[0])

        figw = max(4.5 * ncols, 5.0)
        figh = max(3.5 * nrows, 3.5)
        fig, axes = plt.subplots(nrows, ncols, figsize=(figw, figh), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            metric_keys: list[str] = list(panel.get("metric_keys", []))
            scale = panel.get("scale", "loglog")   # loglog / semilogy / semilogx / linear

            xs = [float(r[param_name]) for r in rows]
            for key in metric_keys:
                ys = [float(r.get(key, float("nan"))) for r in rows]
                label = panel.get("series_labels", {}).get(key, key)
                if scale == "loglog":
                    ax.loglog(xs, ys, "o-", label=label)
                elif scale == "semilogy":
                    ax.semilogy(xs, ys, "o-", label=label)
                elif scale == "semilogx":
                    ax.semilogx(xs, ys, "o-", label=label)
                else:
                    ax.plot(xs, ys, "o-", label=label)

            if panel.get("ref_orders") and scale == "loglog":
                x_arr = np.array(xs)
                ys_first = [float(r.get(metric_keys[0], 1.0)) for r in rows] if metric_keys else [1.0]
                for order in panel["ref_orders"]:
                    y_ref = ys_first[0] * (x_arr / x_arr[0]) ** order
                    ax.loglog(x_arr, y_ref, ":", color="gray", alpha=0.4,
                              label=f"$O(x^{{{order}}})$")

            ax.set_xlabel(panel.get("xlabel", param_name))
            ax.set_ylabel(panel.get("ylabel", "metric"))
            if panel.get("title"):
                ax.set_title(panel["title"])
            if metric_keys:
                ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)

        fig.tight_layout()
        save_figure(fig, outdir / vis.get("output_stem", "parameter_sweep"))
