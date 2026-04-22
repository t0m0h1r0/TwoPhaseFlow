"""All experiment handlers — registered via @register_handler.

Handler types:
  convergence_study  — spatial accuracy vs grid size (loglog)
  time_accuracy      — temporal convergence vs dt (loglog)
  scheme_comparison  — multi-case overlay or bar chart
  parameter_sweep    — scalar param sweep, metric vs param
  time_history       — metric trajectories over timesteps
"""

from __future__ import annotations

import pathlib

import matplotlib.pyplot as plt
import numpy as np

from ..registry import (
    ExperimentHandler, SCHEME_REGISTRY, SOLUTION_REGISTRY, register_handler,
)
from twophase.tools.experiment import save_results, load_results, save_figure, convergence_loglog


# ── Shared helpers ────────────────────────────────────────────────────────────

def _parse_layout(layout: str) -> tuple[int, int]:
    nrows, ncols = layout.split("x")
    return int(nrows), int(ncols)


def _compute_slopes(rows: list[dict]) -> None:
    """Add *_slope keys (log-log pairwise convergence rates) in-place."""
    numeric_keys = [k for k in rows[0] if k not in ("N", "h") and not k.endswith("_slope")]
    for i in range(1, len(rows)):
        r0, r1 = rows[i - 1], rows[i]
        log_h = np.log(float(r1["h"]) / float(r0["h"]))
        if abs(log_h) < 1e-15:
            continue
        for k in numeric_keys:
            v0, v1 = float(r0.get(k, 0)), float(r1.get(k, 0))
            r1[f"{k}_slope"] = float(np.log(v1 / v0) / log_h) if v0 > 0 and v1 > 0 else float("nan")


def _add_slopes(rows: list[dict], x_key: str, y_key: str) -> None:
    for i in range(1, len(rows)):
        r0, r1 = rows[i - 1], rows[i]
        log_x = np.log(float(r1[x_key]) / float(r0[x_key]))
        if abs(log_x) < 1e-15 or r0[y_key] <= 0 or r1[y_key] <= 0:
            continue
        r1["slope"] = float(np.log(float(r1[y_key]) / float(r0[y_key])) / log_x)


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


def _plot_bar_panel(ax, results, plot_cases, error_keys, xlabel, ylabel, title):
    """Grouped bar chart: x-axis = cases, bars = error_keys (log y-scale)."""
    n_cases = len(plot_cases)
    n_keys = max(len(error_keys), 1)
    width = 0.7 / n_keys
    x = np.arange(n_cases)
    for ki, key in enumerate(error_keys):
        vals = []
        for cl in plot_cases:
            rows = results.get(cl, [])
            vals.append(float(rows[-1].get(key, float("nan"))) if rows else float("nan"))
        offset = (ki - (n_keys - 1) / 2.0) * width
        ax.bar(x + offset, vals, width=width * 0.9, label=key)
    ax.set_xticks(x)
    ax.set_xticklabels(plot_cases, rotation=20, ha="right")
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if error_keys:
        ax.legend()


# ── Handlers ──────────────────────────────────────────────────────────────────

@register_handler("convergence_study")
class ConvergenceStudyHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        scheme_name = cfg.scheme.get("operator")
        factory = SCHEME_REGISTRY.get(scheme_name)
        if factory is None:
            raise ValueError(f"Unknown scheme '{scheme_name}'. Registered: {sorted(SCHEME_REGISTRY)}")

        base_params = dict(cfg.scheme.get("params", {}))
        raw_cases = cfg.scheme.get("cases")
        if raw_cases:
            cases = list(raw_cases)
        else:
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
                raise ValueError(f"Unknown test function '{tf_name}'. Registered: {sorted(SOLUTION_REGISTRY)}")
            diff_axes = case.get("diff_axes")
            if diff_axes is not None:
                case_params["diff_axes"] = diff_axes
            case_rows: list[dict] = []
            for N in grid_sizes:
                adapter = factory(N=N, domain=domain, **case_params)
                case_rows.append(adapter.compute_errors(test_fn))
            _compute_slopes(case_rows)
            all_results[label] = case_rows

        save_results(outdir / "data.npz", all_results)
        return all_results

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            results = {k: list(v) for k, v in load_results(outdir / "data.npz").items()}

        vis = cfg.visualization
        nrows, ncols = _parse_layout(vis.get("layout", "1x1"))
        panels: list[dict] = vis.get("panels", [])
        fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            error_keys = list(panel.get("error_keys", []))
            ref_orders = list(panel.get("ref_orders", [2, 4, 6]))
            xlabel = str(panel.get("xlabel", "$h$"))
            ylabel = str(panel.get("ylabel", r"$L_\infty$ error"))
            title = str(panel.get("title", ""))

            if panel.get("all_cases"):
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
                            series = f"{case_label} {k}" if len(error_keys) > 1 else case_label
                            combined_errs[series] = [float(r[k]) for r in rows]
                if combined_hs and combined_errs:
                    convergence_loglog(ax, combined_hs, combined_errs,
                                       ref_orders=ref_orders, xlabel=xlabel, ylabel=ylabel, title=title)
            else:
                case_label = panel.get("case", list(results.keys())[0])
                rows = results.get(case_label, [])
                if rows:
                    hs = [float(r["h"]) for r in rows]
                    errs = {k: [float(r[k]) for r in rows] for k in error_keys if k in rows[0]}
                    convergence_loglog(ax, hs, errs,
                                       ref_orders=ref_orders, xlabel=xlabel, ylabel=ylabel, title=title)

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)
        save_figure(fig, outdir / vis.get("output_stem", "convergence"))


@register_handler("time_accuracy")
class TimeAccuracyHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        n_steps_list: list[int] = [int(n) for n in cfg.input.get("n_steps_list", [16, 32, 64, 128, 256, 512])]
        T_final: float = float(cfg.input.get("T_final", 1.0))
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
            scheme_params = {**dict(cfg.scheme.get("params", {})), **dict(case.get("params", {}))}
            ref_sol_name = case.get("ref_solution") or cfg.reference.get("solution", "")
            ref_params = {**dict(cfg.reference.get("params", {})), **dict(case.get("ref_params", {}))}
            ref_fn = SOLUTION_REGISTRY.get(ref_sol_name)
            if ref_fn is None:
                raise ValueError(f"Unknown reference solution '{ref_sol_name}'. Registered: {sorted(SOLUTION_REGISTRY)}")
            q_exact = ref_fn(**{**ref_params, "T": T_final})
            adapter = factory(**scheme_params)
            rows: list[dict] = []
            for n in n_steps_list:
                out = adapter.run(n_steps=n, T_final=T_final)
                dt = T_final / n
                rows.append({"n": n, "dt": dt, "err": float(abs(out["q_final"] - q_exact))})
            _add_slopes(rows, "dt", "err")
            all_results[label] = rows

        save_results(outdir / "data.npz", all_results)
        return all_results

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            results = {k: list(v) for k, v in load_results(outdir / "data.npz").items()}

        vis = cfg.visualization
        panels = vis.get("panels", [{}])
        nrows, ncols = _parse_layout(vis.get("layout", f"1x{len(panels)}"))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            error_key = panel.get("error_key", "err")
            ref_orders = panel.get("ref_orders", [1, 2])
            case_label = panel.get("case", list(results.keys())[0])
            series_label = panel.get("series_label", case_label)
            rows = list(results.get(case_label, []))
            if not rows:
                continue
            dts = [float(r["dt"]) for r in rows]
            errs = [float(r[error_key]) for r in rows]
            ax.loglog(dts, errs, "o-", label=series_label)
            dt_arr = np.array([dts[0], dts[-1]])
            for order in ref_orders:
                ax.loglog(dt_arr, errs[0] * (dt_arr / dts[0]) ** order,
                          ":", color="gray", label=f"$O(\\Delta t^{{{order}}})$")
            ax.set_xlabel(panel.get("xlabel", r"$\Delta t$"))
            ax.set_ylabel(panel.get("ylabel", "Error"))
            if panel.get("title"):
                ax.set_title(panel["title"])
            ax.legend()

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)
        save_figure(fig, outdir / vis.get("output_stem", "time_accuracy"))


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
                case_rows.append(adapter.compute_errors(test_fn))
            _compute_slopes(case_rows)
            all_results[label] = case_rows

        save_results(outdir / "data.npz", all_results)
        return all_results

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            results = {k: list(v) for k, v in load_results(outdir / "data.npz").items()}

        vis = cfg.visualization
        nrows, ncols = _parse_layout(vis.get("layout", "1x1"))
        panels = vis.get("panels", [{}])
        fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            error_keys = list(panel.get("error_keys", []))
            ref_orders = list(panel.get("ref_orders", [2, 4]))
            xlabel = str(panel.get("xlabel", "$h$"))
            ylabel = str(panel.get("ylabel", r"$L_\infty$ error"))
            title = str(panel.get("title", ""))
            scale = str(panel.get("scale", "loglog"))
            plot_cases = list(results.keys())

            if scale == "bar":
                _plot_bar_panel(ax, results, plot_cases, error_keys,
                                xlabel=xlabel, ylabel=ylabel, title=title)
            else:
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
                            series = f"{case_label} {k}" if len(error_keys) > 1 else case_label
                            combined_errs[series] = [float(r[k]) for r in rows]
                if combined_hs and combined_errs:
                    convergence_loglog(ax, combined_hs, combined_errs,
                                       ref_orders=ref_orders, xlabel=xlabel, ylabel=ylabel, title=title)

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)
        save_figure(fig, outdir / vis.get("output_stem", "scheme_comparison"))


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
            rows.append({param_name: val, **adapter.compute_result()})
        save_results(outdir / "data.npz", {"results": rows})
        return {"results": rows}

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            raw = load_results(outdir / "data.npz")
            results = {"results": list(raw.get("results", []))}

        rows = list(results["results"])
        vis = cfg.visualization
        panels = vis.get("panels", [{}])
        nrows, ncols = _parse_layout(vis.get("layout", f"1x{len(panels)}"))
        sweep_cfg = dict(cfg.sweep or {})
        param_name = sweep_cfg.get("param", list(rows[0].keys())[0])
        fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            metric_keys = list(panel.get("metric_keys", []))
            scale = panel.get("scale", "loglog")
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
            if panel.get("ref_orders") and scale == "loglog" and metric_keys:
                x_arr = np.array(xs)
                y0 = float(rows[0].get(metric_keys[0], 1.0))
                for order in panel["ref_orders"]:
                    ax.loglog(x_arr, y0 * (x_arr / x_arr[0]) ** order,
                              ":", color="gray", label=f"$O(x^{{{order}}})$")
            ax.set_xlabel(panel.get("xlabel", param_name))
            ax.set_ylabel(panel.get("ylabel", "metric"))
            if panel.get("title"):
                ax.set_title(panel["title"])
            if metric_keys:
                ax.legend()

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)
        save_figure(fig, outdir / vis.get("output_stem", "parameter_sweep"))


@register_handler("time_history")
class TimeHistoryHandler(ExperimentHandler):

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        base_operator = cfg.scheme.get("operator", "")
        base_params = dict(cfg.scheme.get("params", {}))
        raw_cases = cfg.scheme.get("cases", []) or [{"label": "default"}]
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
                raise ValueError(f"Unknown scheme '{operator}'. Registered: {sorted(SCHEME_REGISTRY)}")
            case_params = {"N": N, "domain": domain, **base_params, **dict(case.get("params", {}))}
            adapter = factory(**case_params)
            all_results[label] = adapter.run_history(
                n_steps=n_steps, dt=dt, checkpoint_interval=checkpoint_interval)

        save_results(outdir / "data.npz", all_results)
        return all_results

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        if results is None:
            results = {k: list(v) for k, v in load_results(outdir / "data.npz").items()}

        vis = cfg.visualization
        panels = vis.get("panels", [{}])
        nrows, ncols = _parse_layout(vis.get("layout", f"1x{len(panels)}"))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)

        for idx, panel in enumerate(panels):
            ax = axes[idx // ncols][idx % ncols]
            metric_keys = list(panel.get("metric_keys", []))
            exact_keys = list(panel.get("exact_keys", []))
            plot_cases = panel.get("cases", list(results.keys()))
            scale = panel.get("scale", "linear")

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
                ax.legend()

        for idx in range(len(panels), nrows * ncols):
            axes[idx // ncols][idx % ncols].set_visible(False)
        save_figure(fig, outdir / vis.get("output_stem", "time_history"))
