#!/usr/bin/env python3
"""Diagnose V7 IMEX-BDF2 coupled-stack order loss.

This script is intentionally a probe, not a production fix.  It keeps the
Chapter 13 V7 physical setup and varies only reinitialization cadence and
reference depth so hypotheses can be separated by measurement.

Usage
-----
  make run EXP=experiment/ch13/diagnose_V7_imex_bdf2_order.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np

from ch14_stack_common import ch14_circle_config, run_ch14_case, to_host
from twophase.tools.experiment import experiment_argparser, experiment_dir, save_results, load_results

OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 1.0
RHO_L = 10.0
RHO_G = 1.0
MU_L = 1.0e-3
MU_G = 1.0e-4
N_GRID = 24
T_FINAL = 0.02
U_AMP = 0.02
N_STEPS_LIST = (8, 16, 32, 64, 128)


def _wall_bc(arr: np.ndarray) -> None:
    arr[0, :] = 0.0
    arr[-1, :] = 0.0
    arr[:, 0] = 0.0
    arr[:, -1] = 0.0


def _perturbed_velocity(solver, psi) -> tuple[np.ndarray, np.ndarray]:
    X = to_host(solver, solver.X)
    Y = to_host(solver, solver.Y)
    psi_h = to_host(solver, psi)
    u = U_AMP * np.cos(2.0 * np.pi * Y) * psi_h
    v = -U_AMP * np.cos(2.0 * np.pi * X) * psi_h
    _wall_bc(u)
    _wall_bc(v)
    return u, v


def _reinit_every(variant: str, n_steps: int) -> int:
    if variant == "each_step":
        return 1
    if variant == "fixed_reinit_count":
        return max(1, n_steps // 4)
    if variant == "no_reinit":
        return 0
    raise ValueError(f"unknown variant {variant!r}")


def _reinit_count(n_steps: int, every: int) -> int:
    return sum(1 for step in range(n_steps) if every > 0 and step > 0 and step % every == 0)


def _case_config(n_steps: int, variant: str):
    return ch14_circle_config(
        N=N_GRID,
        out_dir=OUT,
        radius=R,
        center=CENTER,
        rho_l=RHO_L,
        rho_g=RHO_G,
        mu_l=MU_L,
        mu_g=MU_G,
        sigma=SIGMA,
        max_steps=n_steps,
        final_time=T_FINAL,
        dt=T_FINAL / n_steps,
        reinit_every=_reinit_every(variant, n_steps),
    )


def _run_one(n_steps: int, variant: str) -> dict:
    every = _reinit_every(variant, n_steps)
    out = run_ch14_case(
        cfg=_case_config(n_steps, variant),
        label=f"V7 diagnose {variant} n={n_steps}",
        radius=R,
        center=CENTER,
        velocity_builder=_perturbed_velocity,
    )
    out.update(
        {
            "variant": variant,
            "n_steps": n_steps,
            "dt": T_FINAL / n_steps,
            "reinit_every": every,
            "reinit_count": _reinit_count(n_steps, every),
        }
    )
    return out


def _rates(values: list[float], dts: list[float]) -> list[float]:
    values_arr = np.asarray(values, dtype=float)
    dts_arr = np.asarray(dts, dtype=float)
    return list(np.log(values_arr[:-1] / values_arr[1:]) / np.log(dts_arr[:-1] / dts_arr[1:]))


def _variant_rows(runs: list[dict]) -> list[dict]:
    ref = runs[-1]
    ref_psi = ref["psi"]
    bulk_mask = (ref_psi > 0.99) | (ref_psi < 0.01)
    band_mask = ~bulk_mask
    rows: list[dict] = []
    for run in runs[:-1]:
        speed_err = np.sqrt((run["u"] - ref["u"]) ** 2 + (run["v"] - ref["v"]) ** 2)
        psi_err = np.abs(run["psi"] - ref_psi)
        pressure_err = np.abs(run["pressure"] - ref["pressure"])
        rows.append(
            {
                "variant": run["variant"],
                "n_steps": run["n_steps"],
                "dt": run["dt"],
                "reinit_every": run["reinit_every"],
                "reinit_count": run["reinit_count"],
                "u_inf_final": run["u_inf_final"],
                "volume_drift_final": run["volume_drift_final"],
                "velocity_linf": float(np.max(speed_err)),
                "velocity_l2": float(np.sqrt(np.mean(speed_err * speed_err))),
                "velocity_bulk_linf": float(np.max(speed_err[bulk_mask])),
                "velocity_band_linf": float(np.max(speed_err[band_mask])),
                "psi_linf": float(np.max(psi_err)),
                "psi_l2": float(np.sqrt(np.mean(psi_err * psi_err))),
                "pressure_linf": float(np.max(pressure_err)),
            }
        )
    metric_names = [
        "velocity_linf",
        "velocity_l2",
        "velocity_bulk_linf",
        "velocity_band_linf",
        "psi_linf",
        "psi_l2",
        "pressure_linf",
    ]
    dts = [row["dt"] for row in rows]
    for metric in metric_names:
        rates = _rates([row[metric] for row in rows], dts)
        for row, rate in zip(rows[1:], rates):
            row[f"{metric}_rate"] = float(rate)
        if rows:
            rows[0][f"{metric}_rate"] = None
    return rows


def run_all() -> dict:
    variants = ("each_step", "fixed_reinit_count", "no_reinit")
    all_runs: dict[str, list[dict]] = {}
    all_rows: dict[str, list[dict]] = {}
    for variant in variants:
        print(f"[V7-diagnose] variant={variant}")
        runs = []
        for n_steps in N_STEPS_LIST:
            every = _reinit_every(variant, n_steps)
            count = _reinit_count(n_steps, every)
            print(
                f"  n_steps={n_steps}, dt={T_FINAL / n_steps:.3e}, "
                f"reinit_every={every}, reinit_count={count}"
            )
            runs.append(_run_one(n_steps, variant))
        all_runs[variant] = runs
        all_rows[variant] = _variant_rows(runs)
    return {
        "reference_n_steps": N_STEPS_LIST[-1],
        "steps": N_STEPS_LIST,
        "runs": all_runs,
        "rows": all_rows,
        "meta": {
            "N": N_GRID,
            "T_final": T_FINAL,
            "rho_ratio": RHO_L / RHO_G,
        },
    }


def print_summary(results: dict) -> None:
    for variant, rows in results["rows"].items():
        print(f"V7 diagnostic variant={variant}, ref={results['reference_n_steps']}:")
        for row in rows:
            rate = row.get("velocity_linf_rate")
            rate_s = "" if rate is None else f"  slope={rate:.2f}"
            print(
                f"  n={row['n_steps']:>3}  dt={row['dt']:.3e}  "
                f"reinit={row['reinit_count']:>3}  "
                f"vel_linf={row['velocity_linf']:.3e}{rate_s}  "
                f"bulk_linf={row['velocity_bulk_linf']:.3e}  "
                f"psi_linf={row['psi_linf']:.3e}"
            )


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    print_summary(results)
    print(f"==> V7 diagnostic outputs in {OUT}")


if __name__ == "__main__":
    main()
