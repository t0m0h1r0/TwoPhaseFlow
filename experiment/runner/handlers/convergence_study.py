"""ConvergenceStudyHandler — spatial accuracy convergence experiments.

YAML type: convergence_study

Runs each case over a set of grid sizes, computing errors against an
analytical test function.  Results are saved as a dict of lists-of-dicts
(one list per case, one dict per grid size).
"""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import numpy as np

from ..registry import (
    ExperimentHandler, SCHEME_REGISTRY, SOLUTION_REGISTRY, register_handler,
)
from twophase.tools.experiment import (
    save_results, load_results, save_figure, convergence_loglog, apply_style,
    FIGSIZE_2COL,
)


@register_handler("convergence_study")
class ConvergenceStudyHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        scheme_name = cfg.scheme.get("operator")
        factory = SCHEME_REGISTRY.get(scheme_name)
        if factory is None:
            raise ValueError(
                f"Unknown scheme '{scheme_name}'. "
                f"Registered: {sorted(SCHEME_REGISTRY)}"
            )

        base_params = dict(cfg.scheme.get("params", {}))
        raw_cases = cfg.scheme.get("cases")
        if raw_cases:
            cases = list(raw_cases)
        else:
            # Bare scheme without cases list: single implicit case
            cases = [{"label": "default", "params": base_params,
                      "test_function": cfg.input.get("test_function", "")}]

        grid_sizes: list[int] = list(cfg.input.get("grid_sizes", [16, 32, 64, 128]))
        domain: dict = dict(cfg.input.get("domain", {"Lx": 1.0, "Ly": 1.0}))

        all_results: dict[str, list[dict]] = {}

        for case in cases:
            label = case.get("label", "default")
            case_params = {**base_params, **dict(case.get("params", {}))}
            tf_name = case.get("test_function") or cfg.input.get("test_function", "")
            test_fn = SOLUTION_REGISTRY.get(tf_name) if tf_name else None
            if tf_name and test_fn is None:
                raise ValueError(
                    f"Unknown test function '{tf_name}'. "
                    f"Registered: {sorted(SOLUTION_REGISTRY)}"
                )

            diff_axes = case.get("diff_axes")  # None → factory default (0,1)
            if diff_axes is not None:
                case_params["diff_axes"] = diff_axes

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
            # load_results returns object arrays for list-of-dicts; convert to list
            results = {k: list(v) for k, v in raw.items()}

        vis = cfg.visualization
        layout: str = vis.get("layout", "1x1")
        nrows, ncols = [int(x) for x in layout.split("x")]
        panels: list[dict] = vis.get("panels", [])

        figw = max(4.0 * ncols, 6.0)
        figh = max(3.5 * nrows, 3.5)
        fig, axes = plt.subplots(nrows, ncols, figsize=(figw, figh), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            error_keys: list[str] = list(panel.get("error_keys", []))
            ref_orders = list(panel.get("ref_orders", [2, 4, 6]))
            xlabel = str(panel.get("xlabel", "$h$"))
            ylabel = str(panel.get("ylabel", r"$L_\infty$ error"))
            title = str(panel.get("title", ""))

            if panel.get("all_cases"):
                # Build one combined errors dict → single convergence_loglog call
                combined_hs = None
                combined_errs: dict = {}
                for case_label, rows in results.items():
                    if not rows:
                        continue
                    hs = [float(r["h"]) for r in rows]
                    if combined_hs is None:
                        combined_hs = hs
                    for k in error_keys:
                        if k in rows[0]:
                            series_label = (f"{case_label} {k}"
                                            if len(error_keys) > 1 else case_label)
                            combined_errs[series_label] = [float(r[k]) for r in rows]
                if combined_hs and combined_errs:
                    convergence_loglog(ax, combined_hs, combined_errs,
                                       ref_orders=ref_orders,
                                       xlabel=xlabel, ylabel=ylabel, title=title)
            else:
                case_label = panel.get("case", list(results.keys())[0])
                rows = results.get(case_label, [])
                if not rows:
                    continue
                hs = [float(r["h"]) for r in rows]
                errs = {k: [float(r[k]) for r in rows]
                        for k in error_keys if k in rows[0]}
                convergence_loglog(ax, hs, errs,
                                   ref_orders=ref_orders,
                                   xlabel=xlabel, ylabel=ylabel, title=title)

        # Hide unused panels
        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)

        fig.tight_layout()
        stem = vis.get("output_stem", "convergence")
        save_figure(fig, outdir / stem)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_slopes(rows: list[dict]) -> None:
    """Add *_slope keys to rows (in-place, log-log pairwise rates)."""
    numeric_keys = [k for k in rows[0] if k not in ("N", "h") and not k.endswith("_slope")]
    for i in range(1, len(rows)):
        r0, r1 = rows[i - 1], rows[i]
        log_h = np.log(float(r1["h"]) / float(r0["h"]))
        if abs(log_h) < 1e-15:
            continue
        for k in numeric_keys:
            v0, v1 = float(r0.get(k, 0)), float(r1.get(k, 0))
            r1[f"{k}_slope"] = float(np.log(v1 / v0) / log_h) if v0 > 0 and v1 > 0 else float("nan")
