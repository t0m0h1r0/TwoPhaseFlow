"""SchemeComparisonHandler — compare multiple schemes on the same problem.

YAML type: scheme_comparison

Like convergence_study but each case may specify its own operator.
Results are overlaid on a single convergence loglog panel.
"""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import numpy as np

from ..registry import (
    ExperimentHandler, SCHEME_REGISTRY, SOLUTION_REGISTRY, register_handler,
)
from twophase.tools.experiment import (
    save_results, load_results, save_figure, convergence_loglog,
)


@register_handler("scheme_comparison")
class SchemeComparisonHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        base_operator = cfg.scheme.get("operator", "")
        base_params = dict(cfg.scheme.get("params", {}))
        raw_cases = cfg.scheme.get("cases", [])

        grid_sizes: list[int] = list(cfg.input.get("grid_sizes", [16, 32, 64, 128]))
        domain: dict = dict(cfg.input.get("domain", {"Lx": 1.0, "Ly": 1.0}))

        all_results: dict[str, list[dict]] = {}

        for case in raw_cases:
            label = case.get("label", "default")
            operator = case.get("operator") or base_operator
            factory = SCHEME_REGISTRY.get(operator)
            if factory is None:
                raise ValueError(f"Unknown scheme '{operator}'. Registered: {sorted(SCHEME_REGISTRY)}")

            case_params = {**base_params, **dict(case.get("params", {}))}
            tf_name = case.get("test_function") or cfg.input.get("test_function", "")
            test_fn = SOLUTION_REGISTRY.get(tf_name) if tf_name else None

            case_rows: list[dict] = []
            for N in grid_sizes:
                adapter = factory(N=N, domain=domain, **case_params)
                row = adapter.compute_errors(test_fn)
                case_rows.append(row)

            _compute_slopes(case_rows)
            all_results[label] = case_rows

        save_results(outdir / "data.npz", all_results)
        return all_results

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            raw = load_results(outdir / "data.npz")
            results = {k: list(v) for k, v in raw.items()}

        vis = cfg.visualization
        layout = vis.get("layout", "1x1")
        nrows, ncols = [int(x) for x in layout.split("x")]
        panels = vis.get("panels", [{}])

        figw = max(4.5 * ncols, 5.0)
        figh = max(3.5 * nrows, 3.5)
        fig, axes = plt.subplots(nrows, ncols, figsize=(figw, figh), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            error_keys: list[str] = list(panel.get("error_keys", []))
            ref_orders = list(panel.get("ref_orders", [2, 4]))
            xlabel = str(panel.get("xlabel", "$h$"))
            ylabel = str(panel.get("ylabel", r"$L_\infty$ error"))
            title = str(panel.get("title", ""))

            # Limit to listed cases if specified; else all
            plot_cases = panel.get("cases", list(results.keys()))

            combined_hs = None
            combined_errs: dict = {}
            for case_label in plot_cases:
                rows = results.get(case_label, [])
                if not rows:
                    continue
                hs = [float(r["h"]) for r in rows]
                if combined_hs is None:
                    combined_hs = hs
                for k in error_keys:
                    if k in rows[0]:
                        series = (f"{case_label} {k}"
                                  if len(error_keys) > 1 else case_label)
                        combined_errs[series] = [float(r[k]) for r in rows]

            if combined_hs and combined_errs:
                convergence_loglog(ax, combined_hs, combined_errs,
                                   ref_orders=ref_orders,
                                   xlabel=xlabel, ylabel=ylabel, title=title)

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)

        fig.tight_layout()
        save_figure(fig, outdir / vis.get("output_stem", "scheme_comparison"))


def _compute_slopes(rows: list[dict]) -> None:
    numeric_keys = [k for k in rows[0] if k not in ("N", "h") and not k.endswith("_slope")]
    for i in range(1, len(rows)):
        r0, r1 = rows[i - 1], rows[i]
        log_h = np.log(float(r1["h"]) / float(r0["h"]))
        if abs(log_h) < 1e-15:
            continue
        for k in numeric_keys:
            v0, v1 = float(r0.get(k, 0)), float(r1.get(k, 0))
            r1[f"{k}_slope"] = float(np.log(v1 / v0) / log_h) if v0 > 0 and v1 > 0 else float("nan")
