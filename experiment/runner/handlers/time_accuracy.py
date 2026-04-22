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
        scheme_name = cfg.scheme.get("operator")
        factory = SCHEME_REGISTRY.get(scheme_name)
        if factory is None:
            raise ValueError(f"Unknown scheme '{scheme_name}'. Registered: {sorted(SCHEME_REGISTRY)}")

        scheme_params = dict(cfg.scheme.get("params", {}))
        n_steps_list: list[int] = [int(n) for n in cfg.input.get("n_steps_list", [16, 32, 64, 128, 256, 512])]
        T_final: float = float(cfg.input.get("T_final", 1.0))

        ref_sol_name: str = cfg.reference.get("solution", "")
        ref_params: dict = dict(cfg.reference.get("params", {}))
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
        save_results(outdir / "data.npz", {"results": rows})
        return {"results": rows}

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            raw = load_results(outdir / "data.npz")
            results = {"results": list(raw.get("results", raw.get("results", [])))}

        rows = list(results["results"])
        vis = cfg.visualization
        panels = vis.get("panels", [{}])
        panel = panels[0] if panels else {}

        fig, ax = plt.subplots(1, 1, figsize=FIGSIZE_1COL)

        dts = [float(r["dt"]) for r in rows]
        error_key = panel.get("error_key", "err")
        label = panel.get("series_label", "")
        errs = [float(r[error_key]) for r in rows]

        ax.loglog(dts, errs, "o-", markersize=7, label=label or error_key)

        dt_ref = np.array([dts[0], dts[-1]])
        for order in panel.get("ref_orders", [1, 2]):
            ax.loglog(dt_ref, errs[0] * (dt_ref / dt_ref[0]) ** order,
                      ":", color="gray", alpha=0.5, label=f"$O(\\Delta t^{order})$")

        ax.set_xlabel(panel.get("xlabel", r"$\Delta t$"))
        ax.set_ylabel(panel.get("ylabel", "Error"))
        if panel.get("title"):
            ax.set_title(panel["title"])
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        fig.tight_layout()
        save_figure(fig, outdir / vis.get("output_stem", "time_accuracy"))


def _add_slopes(rows: list[dict], x_key: str, y_key: str) -> None:
    for i in range(1, len(rows)):
        r0, r1 = rows[i - 1], rows[i]
        log_x = np.log(float(r1[x_key]) / float(r0[x_key]))
        if abs(log_x) < 1e-15 or r0[y_key] <= 0 or r1[y_key] <= 0:
            continue
        r1["slope"] = float(np.log(float(r1[y_key]) / float(r0[y_key])) / log_x)
