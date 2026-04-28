#!/usr/bin/env python3
"""[U1] CCD operator family suite — Tier I (uniform grid).

Paper ref: Chapter 12 U1 (sec:U1_ccd_suite; paper/sections/12u1_ccd_operator.tex).

Sub-tests
---------
  (a) CCD 1D MMS d1/d2 6-order convergence (periodic + wall BC)
  (b) DCCD modified wavenumber + smooth-mode preservation (analytic)
  (c) FCCD face value/grad 6-order convergence (periodic)
  (d) UCCD6 nodal d1 6-order convergence + hyperviscosity diagnostic

Usage
-----
  python experiment/ch12/exp_U1_ccd_operator_suite.py
  python experiment/ch12/exp_U1_ccd_operator_suite.py --plot-only
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
from twophase.ccd.fccd import FCCDSolver
from twophase.ccd.uccd6 import UCCD6Operator
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    convergence_loglog, compute_convergence_rates,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u1_ccd_operator_suite"

GRID_SIZES = [16, 32, 64, 128, 256]


# ── Grid helpers ─────────────────────────────────────────────────────────────

def _grid_2d(N: int, backend) -> Grid:
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    return Grid(cfg.grid, backend)


def _grid_1d_strip(N: int, backend) -> Grid:
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, 4), L=(1.0, 1.0)))
    return Grid(cfg.grid, backend)


# ── U1-a: CCD 1D MMS d1/d2 (periodic + wall) ────────────────────────────────

def _ccd_periodic_errors(N: int, backend):
    grid = _grid_2d(N, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    f = np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    d1, d2 = ccd.differentiate(f, axis=0)
    d1_exact = 2 * np.pi * np.cos(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    d2_exact = -(2 * np.pi) ** 2 * np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    return {
        "L2_d1": float(np.sqrt(np.mean((d1 - d1_exact) ** 2))),
        "Linf_d1": float(np.max(np.abs(d1 - d1_exact))),
        "L2_d2": float(np.sqrt(np.mean((d2 - d2_exact) ** 2))),
        "Linf_d2": float(np.max(np.abs(d2 - d2_exact))),
    }


def _ccd_wall_errors(N: int, backend):
    grid = _grid_2d(N, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    x = np.linspace(0.0, 1.0, N + 1)
    y = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, y, indexing="ij")
    f = np.exp(np.sin(np.pi * X)) * np.exp(np.cos(np.pi * Y))
    d1, _ = ccd.differentiate(f, axis=0)
    d1_exact = np.pi * np.cos(np.pi * X) * f
    return {"Linf_d1": float(np.max(np.abs(d1 - d1_exact)))}


def run_U1a():
    backend = Backend(use_gpu=False)
    rows_periodic, rows_wall = [], []
    for N in GRID_SIZES:
        rows_periodic.append({"N": N, "h": 1.0 / N, **_ccd_periodic_errors(N, backend)})
        rows_wall.append({"N": N, "h": 1.0 / N, **_ccd_wall_errors(N, backend)})
    return {"periodic": rows_periodic, "wall": rows_wall}


# ── U1-b: DCCD modified wavenumber (analytic) ────────────────────────────────

def run_U1b():
    eps_values = [0.0, 0.05, 0.25]
    xi = np.linspace(0.0, np.pi, 256)
    rows = []
    for eps_d in eps_values:
        H = 1.0 - 4.0 * eps_d * np.sin(xi / 2.0) ** 2
        rows.append({
            "eps_d": eps_d,
            "H_at_pi": float(1.0 - 4.0 * eps_d),
            "H_curve": H.tolist(),
            "xi": xi.tolist(),
        })
    return {"transfer": rows}


# ── U1-c: FCCD face value/grad ──────────────────────────────────────────────

def _fccd_errors(N: int, backend):
    grid = _grid_2d(N, backend)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    f = np.sin(2 * np.pi * X) * np.sin(2 * np.pi * Y)
    fv = np.asarray(fccd.face_value(f, axis=0))
    fg = np.asarray(fccd.face_gradient(f, axis=0))
    h = 1.0 / N
    x_face = x[:fv.shape[0]] + 0.5 * h
    y_eval = x[:fv.shape[1]]
    Xf, Yf = np.meshgrid(x_face, y_eval, indexing="ij")
    fv_exact = np.sin(2 * np.pi * Xf) * np.sin(2 * np.pi * Yf)
    fg_exact = 2 * np.pi * np.cos(2 * np.pi * Xf) * np.sin(2 * np.pi * Yf)
    return {
        "Linf_fv": float(np.max(np.abs(fv - fv_exact))),
        "Linf_fg": float(np.max(np.abs(fg - fg_exact))),
    }


def run_U1c():
    backend = Backend(use_gpu=False)
    rows = [{"N": N, "h": 1.0 / N, **_fccd_errors(N, backend)} for N in GRID_SIZES[:-1]]
    return {"face": rows}


# ── U1-d: UCCD6 nodal d1 ─────────────────────────────────────────────────────

def _uccd6_errors(N: int, backend):
    grid = _grid_1d_strip(N, backend)
    op = UCCD6Operator(grid, backend, sigma=1.0, bc_type="periodic")
    x = np.linspace(0.0, 1.0, N + 1)
    f1d = np.sin(2 * np.pi * x)
    f = np.broadcast_to(f1d[:, None], (N + 1, 5)).copy()
    rhs = np.asarray(op.apply_rhs(f, axis=0, a=1.0))
    df_exact = -2 * np.pi * np.cos(2 * np.pi * x)[:, None]
    return {"Linf_d1": float(np.max(np.abs(rhs - df_exact)))}


def run_U1d():
    backend = Backend(use_gpu=False)
    rows = [{"N": N, "h": 1.0 / N, **_uccd6_errors(N, backend)} for N in GRID_SIZES[:-1]]
    return {"nodal": rows}


# ── Aggregator + plotting ─────────────────────────────────────────────────────

def run_all() -> dict:
    return {
        "U1a": run_U1a(),
        "U1b": run_U1b(),
        "U1c": run_U1c(),
        "U1d": run_U1d(),
    }


def _slope_summary(rows: list[dict], err_key: str) -> str:
    hs = [r["h"] for r in rows]
    errs = [r[err_key] for r in rows]
    rates = compute_convergence_rates(errs, hs)
    finite = [r for r in rates if np.isfinite(r)]
    return f"mean={np.mean(finite):.2f}" if finite else "n/a"


def make_figures(results: dict) -> None:
    # Panel layout: 2x2 (CCD periodic d1/d2, FCCD face, UCCD6, DCCD transfer)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    ax_a, ax_b = axes[0]
    ax_c, ax_d = axes[1]

    rows_p = results["U1a"]["periodic"]
    hs_p = [r["h"] for r in rows_p]
    convergence_loglog(
        ax_a, hs_p,
        {"$L_\\infty$ $d_1$": [r["Linf_d1"] for r in rows_p],
         "$L_\\infty$ $d_2$": [r["Linf_d2"] for r in rows_p]},
        ref_orders=[4, 6], xlabel="$h$", ylabel="$L_\\infty$ error",
        title="(a) CCD periodic MMS")

    rows_b = results["U1b"]["transfer"]
    for r in rows_b:
        ax_b.plot(r["xi"], r["H_curve"], label=f"$\\varepsilon_d={r['eps_d']}$")
    ax_b.set_xlabel("$\\xi$"); ax_b.set_ylabel("$H(\\xi)$")
    ax_b.set_title("(b) DCCD transfer function"); ax_b.legend()

    rows_c = results["U1c"]["face"]
    hs_c = [r["h"] for r in rows_c]
    convergence_loglog(
        ax_c, hs_c,
        {"$L_\\infty$ face value": [r["Linf_fv"] for r in rows_c],
         "$L_\\infty$ face grad": [r["Linf_fg"] for r in rows_c]},
        ref_orders=[4, 6], xlabel="$h$", ylabel="$L_\\infty$ error",
        title="(c) FCCD face value/grad")

    rows_d = results["U1d"]["nodal"]
    hs_d = [r["h"] for r in rows_d]
    convergence_loglog(
        ax_d, hs_d,
        {"$L_\\infty$ UCCD6 RHS": [r["Linf_d1"] for r in rows_d]},
        ref_orders=[5, 6], xlabel="$h$", ylabel="$L_\\infty$ error",
        title="(d) UCCD6 nodal RHS")
    save_figure(fig, OUT / "U1_ccd_operator_suite", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    print("U1-a CCD periodic d1 slope:", _slope_summary(results["U1a"]["periodic"], "Linf_d1"))
    print("U1-a CCD periodic d2 slope:", _slope_summary(results["U1a"]["periodic"], "Linf_d2"))
    print("U1-a CCD wall d1 slope    :", _slope_summary(results["U1a"]["wall"], "Linf_d1"))
    print("U1-b DCCD H(pi)           :",
          ", ".join(f"eps={r['eps_d']}->{r['H_at_pi']:.4f}" for r in results["U1b"]["transfer"]))
    print("U1-c FCCD face value slope:", _slope_summary(results["U1c"]["face"], "Linf_fv"))
    print("U1-c FCCD face grad slope :", _slope_summary(results["U1c"]["face"], "Linf_fg"))
    print("U1-d UCCD6 RHS slope      :", _slope_summary(results["U1d"]["nodal"], "Linf_d1"))


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> U1 outputs in {OUT}")


if __name__ == "__main__":
    main()
