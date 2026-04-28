#!/usr/bin/env python3
"""[U9] DCCD-on-pressure prohibition — Tier VI (negation test).

Paper ref: Chapter 11 U9 (sec:U9_dccd_pressure_prohibition; paper/sections/12u9_dccd_pressure_prohibition.tex).

Goal
----
Verify the design constraint introduced in §sec:dccd_pressure_nofilt that
the DCCD 3-point filter MUST NOT be applied to the pressure field.
We negate the rule and quantify the resulting incompressibility-violation
error scale: ‖∇²p − ∇²p̃‖_∞ where p̃ is the DCCD-filtered pressure.

Setup
-----
  Manufactured solution  p = sin(2πx) sin(2πy)   (periodic on [0,1]²)
  Exact Laplacian        ∇²p = −8π² · p
  CCD Laplacian (no filter): expected O(h^6) convergence to ∇²p
  DCCD filter (ε_d ∈ {0.05, 0.25}) applied to p:
      p̃_i = (1 − 2ε_d) p_i + ε_d (p_{i−1} + p_{i+1})  per axis
  Diagnostic:  ‖∇²p − ∇²p̃‖_∞  expected O(h²) blow-up
  Paper ε_d = 0.25 reference: N=32 → 1.51, N=256 → 2.38×10⁻²

Usage
-----
  python experiment/ch12/exp_U9_dccd_pressure_prohibition.py
  python experiment/ch12/exp_U9_dccd_pressure_prohibition.py --plot-only
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    convergence_loglog, compute_convergence_rates,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u9_dccd_pressure_prohibition"

GRID_SIZES = [32, 64, 128, 256]
EPS_D_LIST = [0.05, 0.25]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _grid_2d(N: int, backend) -> Grid:
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    return Grid(cfg.grid, backend)


def _ccd_laplacian(ccd: CCDSolver, p: np.ndarray) -> np.ndarray:
    _, d2x = ccd.differentiate(p, axis=0)
    _, d2y = ccd.differentiate(p, axis=1)
    return np.asarray(d2x) + np.asarray(d2y)


def _filter_1d_periodic(p: np.ndarray, eps_d: float, axis: int) -> np.ndarray:
    """3-point DCCD filter along ``axis`` with periodic wrap.

    Grid convention: p has shape …×(N+1)×… along ``axis`` with p[0]=p[N]
    (duplicate endpoint).  The filter operates on the unique cycle of N
    points and re-emits the duplicate endpoint.

    p̃_i = (1 − 2ε_d) p_i + ε_d (p_{i−1} + p_{i+1})  (modulo N)
    """
    N_plus_1 = p.shape[axis]
    N = N_plus_1 - 1

    sl_base = [slice(None)] * p.ndim
    sl_base[axis] = slice(0, N)
    base = p[tuple(sl_base)]

    base_left = np.roll(base, 1, axis=axis)
    base_right = np.roll(base, -1, axis=axis)
    base_filt = (1.0 - 2.0 * eps_d) * base + eps_d * (base_left + base_right)

    sl_zero = [slice(None)] * p.ndim
    sl_zero[axis] = slice(0, 1)
    return np.concatenate([base_filt, base_filt[tuple(sl_zero)]], axis=axis)


def _filter_2d_periodic(p: np.ndarray, eps_d: float) -> np.ndarray:
    p_f = _filter_1d_periodic(p, eps_d, axis=0)
    return _filter_1d_periodic(p_f, eps_d, axis=1)


# ── U9 main computation ─────────────────────────────────────────────────────

def _u9_one(N: int, eps_d: float, backend) -> dict:
    grid = _grid_2d(N, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    p = np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    lap_exact = -8.0 * np.pi**2 * p

    lap_unfilt = _ccd_laplacian(ccd, p)
    err_unfilt = float(np.max(np.abs(lap_unfilt - lap_exact)))

    p_filt = _filter_2d_periodic(p, eps_d)
    lap_filt = _ccd_laplacian(ccd, p_filt)
    diff = lap_unfilt - lap_filt
    err_diff = float(np.max(np.abs(diff)))

    return {
        "N": N, "h": 1.0 / N, "eps_d": eps_d,
        "Linf_unfiltered": err_unfilt,
        "Linf_diff": err_diff,
    }


def run_U9() -> dict:
    backend = Backend(use_gpu=False)
    rows = []
    for N in GRID_SIZES:
        for eps_d in EPS_D_LIST:
            rows.append(_u9_one(N, eps_d, backend))
    return {"diff": rows}


def run_all() -> dict:
    return {"U9": run_U9()}


# ── Plotting + summary ──────────────────────────────────────────────────────

def _slope_summary(rows: list[dict], err_key: str) -> str:
    hs = [r["h"] for r in rows]
    errs = [r[err_key] for r in rows]
    rates = compute_convergence_rates(errs, hs)
    finite = [r for r in rates if np.isfinite(r)]
    return f"mean={np.mean(finite):.2f}" if finite else "n/a"


def make_figures(results: dict) -> None:
    fig, (ax_unfilt, ax_diff) = plt.subplots(1, 2, figsize=(11, 4.5))

    rows_all = results["U9"]["diff"]
    # Unfiltered baseline (one curve, take eps=0.25 rows since same p across eps)
    rows_e25 = [r for r in rows_all if r["eps_d"] == 0.25]
    hs_u = [r["h"] for r in rows_e25]
    errs_u = [r["Linf_unfiltered"] for r in rows_e25]
    convergence_loglog(
        ax_unfilt, hs_u, {"$L_\\infty$ unfiltered": errs_u},
        ref_orders=[6], xlabel="$h$", ylabel="$L_\\infty$ error vs $\\nabla^2 p$",
        title="(unfilt) CCD Laplacian baseline")

    # Diff curves: one per eps_d
    series = {}
    for eps_d in EPS_D_LIST:
        rows_e = [r for r in rows_all if r["eps_d"] == eps_d]
        series[f"$\\varepsilon_d={eps_d}$"] = [r["Linf_diff"] for r in rows_e]
    hs_d = [r["h"] for r in [rr for rr in rows_all if rr["eps_d"] == EPS_D_LIST[0]]]
    convergence_loglog(
        ax_diff, hs_d, series,
        ref_orders=[2], xlabel="$h$",
        ylabel="$\\|\\nabla^2 p - \\nabla^2 \\tilde p\\|_\\infty$",
        title="(diff) DCCD-on-pressure error blow-up")

    save_figure(fig, OUT / "U9_dccd_pressure_prohibition", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    rows_all = results["U9"]["diff"]
    rows_e25 = [r for r in rows_all if r["eps_d"] == 0.25]
    print("U9 unfiltered CCD-Lap slope:", _slope_summary(rows_e25, "Linf_unfiltered"))
    for eps_d in EPS_D_LIST:
        rows_e = [r for r in rows_all if r["eps_d"] == eps_d]
        print(f"U9 ‖∇²p−∇²p̃‖∞ slope (ε_d={eps_d}):",
              _slope_summary(rows_e, "Linf_diff"))
    print("U9 ε_d=0.25 reference values:")
    for r in [rr for rr in rows_all if rr["eps_d"] == 0.25]:
        print(f"  N={r['N']:>3}  Linf_diff = {r['Linf_diff']:.4e}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> U9 outputs in {OUT}")


if __name__ == "__main__":
    main()
