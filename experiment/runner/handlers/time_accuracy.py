"""TimeAccuracyHandler — temporal convergence experiments.

YAML type: time_accuracy

Runs a time-integration scheme for varying numbers of time steps (dt = T / n),
computes error against the analytical solution at T_final, and plots loglog.
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
    FIGSIZE_1COL,
)


@register_handler("time_accuracy")
class TimeAccuracyHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        n_steps_list: list[int] = [int(n) for n in cfg.input.get("n_steps_list", [16, 32, 64, 128, 256, 512])]
        T_final: float = float(cfg.input.get("T_final", 1.0))

        # Multi-case support: scheme.cases list (each may have own operator + params)
        raw_cases = cfg.scheme.get("cases")
        if raw_cases:
            cases = list(raw_cases)
        else:
            ref_sol_name = cfg.reference.get("solution", "")
            cases = [{"label": "default",
                      "operator": cfg.scheme.get("operator"),
                      "params": dict(cfg.scheme.get("params", {})),
                      "ref_solution": ref_sol_name,
                      "ref_params": dict(cfg.reference.get("params", {}))}]

        all_results: dict[str, list[dict]] = {}

        for case in cases:
            label = case.get("label", "default")
            scheme_name = case.get("operator") or cfg.scheme.get("operator")
            factory = SCHEME_REGISTRY.get(scheme_name)
            if factory is None:
                raise ValueError(f"Unknown scheme '{scheme_name}'. Registered: {sorted(SCHEME_REGISTRY)}")

            scheme_params = {**dict(cfg.scheme.get("params", {})),
                             **dict(case.get("params", {}))}

            ref_sol_name = case.get("ref_solution") or cfg.reference.get("solution", "")
            ref_params = {**dict(cfg.reference.get("params", {})),
                          **dict(case.get("ref_params", {}))}
            ref_fn = SOLUTION_REGISTRY.get(ref_sol_name)
            if ref_fn is None:
                raise ValueError(f"Unknown reference solution '{ref_sol_name}'. Registered: {sorted(SOLUTION_REGISTRY)}")

            q_exact = ref_fn(**{**ref_params, "T": T_final})

            adapter = factory(**scheme_params)
            rows: list[dict] = []
            for n in n_steps_list:
                out = adapter.run(n_steps=n, T_final=T_final)
                q_final = out["q_final"]
                err = abs(q_final - q_exact)
                dt = T_final / n
                rows.append({"n": n, "dt": dt, "err": float(err)})

            _add_slopes(rows, "dt", "err")
            all_results[label] = rows

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
        fig, axes_arr = plt.subplots(nrows, ncols, figsize=(figw, figh), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes_arr[idx // ncols][idx % ncols]
            error_key = panel.get("error_key", "err")
            ref_orders_p = panel.get("ref_orders", [1, 2])
            xlabel_p = panel.get("xlabel", r"$\Delta t$")
            ylabel_p = panel.get("ylabel", "Error")

            if panel.get("all_cases"):
                cases_to_plot = list(results.items())
            else:
                case_label = panel.get("case", list(results.keys())[0])
                series_label = panel.get("series_label", "")
                cases_to_plot = [(series_label or case_label, results.get(case_label, []))]

            first_dts = first_errs0 = None
            for case_label_p, rows in cases_to_plot:
                rows = list(rows)
                if not rows:
                    continue
                dts = [float(r["dt"]) for r in rows]
                errs = [float(r[error_key]) for r in rows]
                if first_dts is None:
                    first_dts, first_errs0 = dts, errs[0]
                ax.loglog(dts, errs, "o-", markersize=7, label=case_label_p)

            if first_dts:
                dt_ref = np.array([first_dts[0], first_dts[-1]])
                for order in ref_orders_p:
                    ax.loglog(dt_ref, first_errs0 * (dt_ref / dt_ref[0]) ** order,
                              ":", color="gray", alpha=0.5, label=f"$O(\\Delta t^{order})$")

            ax.set_xlabel(xlabel_p)
            ax.set_ylabel(ylabel_p)
            if panel.get("title"):
                ax.set_title(panel["title"])
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        for idx in range(len(panels), nrows * ncols):
            axes_arr[idx // ncols][idx % ncols].set_visible(False)

        fig.tight_layout()
        save_figure(fig, outdir / vis.get("output_stem", "time_accuracy"))


def _add_slopes(rows: list[dict], x_key: str, y_key: str) -> None:
    for i in range(1, len(rows)):
        r0, r1 = rows[i - 1], rows[i]
        log_x = np.log(float(r1[x_key]) / float(r0[x_key]))
        if abs(log_x) < 1e-15 or r0[y_key] <= 0 or r1[y_key] <= 0:
            continue
        r1["slope"] = float(np.log(float(r1[y_key]) / float(r0[y_key])) / log_x)
