#!/usr/bin/env python3
"""[V2] CCD spatial residual on periodic single-phase NS — Tier A.

Paper ref: §13.1 (sec:energy_conservation; companion to V1).

Verifies that the project's CCD spatial discretization (periodic BC) achieves
its design order O(h^4) or higher in the full NS advection-diffusion residual
on a manufactured periodic single-phase NS solution. V1 covers single-phase
time integration order; V2's role here is the *spatial* anchor for §13.1
and complements V7's two-phase IMEX-BDF2 time-order test.

Sub-test
--------
  CCD spatial residual order. Manufactured solution:
    u(x,y,t) = sin(x)*cos(y)*exp(-2*nu*t),
    v(x,y,t) = -cos(x)*sin(y)*exp(-2*nu*t),
  divergence-free for all t (the chosen profile satisfies div(u)=0
  identically and du/dt = -2*nu*u). Hence the analytic NS RHS reduces to
    -(u·grad)u + nu*lap(u) = du/dt = -2*nu*u.
  We compute the project's CCD evaluation of -(u·grad)u + nu*lap(u) at t=0
  and measure the L_inf residual against the analytic du/dt.
  N in {32, 64, 128, 256}; expected slope >= 4 (interior CCD on periodic
  grid is O(h^6), but the saturated NS combination is at least O(h^4)).

Usage
-----
  python experiment/ch13/exp_V2_kovasznay_imex_bdf2.py
  python experiment/ch13/exp_V2_kovasznay_imex_bdf2.py --plot-only
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
    compute_convergence_rates,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

NU = 0.025  # Re ~ 40
L_BOX = 2.0 * np.pi


def _setup_periodic_grid(N: int, backend: Backend):
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(L_BOX, L_BOX)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    h = L_BOX / N
    X, Y = grid.meshgrid()
    X = np.asarray(backend.to_host(X))
    Y = np.asarray(backend.to_host(Y))
    return grid, ccd, h, X, Y


def _manufactured(t: float, X, Y) -> tuple[np.ndarray, np.ndarray]:
    decay = np.exp(-2.0 * NU * t)
    u = np.sin(X) * np.cos(Y) * decay
    v = -np.cos(X) * np.sin(Y) * decay
    return u, v


def _ccd_grad(field, ccd, axis: int, backend: Backend) -> np.ndarray:
    d1, _ = ccd.differentiate(field, axis)
    return np.asarray(backend.to_host(d1))


def _ccd_lap(field, ccd, backend: Backend) -> np.ndarray:
    _, d2x = ccd.differentiate(field, 0)
    _, d2y = ccd.differentiate(field, 1)
    return np.asarray(backend.to_host(d2x)) + np.asarray(backend.to_host(d2y))


# ── (a) Spatial residual order ───────────────────────────────────────────────

def _spatial_residual(N: int, backend: Backend) -> dict:
    grid, ccd, h, X, Y = _setup_periodic_grid(N, backend)
    u, v = _manufactured(0.0, X, Y)
    # Full 2D Taylor-Green analytic pressure (decay² = 1 at t=0):
    #   p_ex = (cos(2x) + cos(2y)) / 4
    # NS form: du/dt = -(u·grad)u + ν·∆u − ∂p/∂x
    # Hence the CCD-computed RHS must converge to:
    #   target_u = -2ν*u + ∂p/∂x = -2ν*u - (1/2)*sin(2x)
    dudt_ex_u = -2.0 * NU * u - 0.5 * np.sin(2.0 * X)
    dudt_ex_v = -2.0 * NU * v - 0.5 * np.sin(2.0 * Y)

    du_dx = _ccd_grad(u, ccd, 0, backend)
    du_dy = _ccd_grad(u, ccd, 1, backend)
    dv_dx = _ccd_grad(v, ccd, 0, backend)
    dv_dy = _ccd_grad(v, ccd, 1, backend)
    lap_u = _ccd_lap(u, ccd, backend)
    lap_v = _ccd_lap(v, ccd, backend)

    rhs_u = -(u * du_dx + v * du_dy) + NU * lap_u
    rhs_v = -(u * dv_dx + v * dv_dy) + NU * lap_v
    res_u = float(np.max(np.abs(rhs_u - dudt_ex_u)))
    res_v = float(np.max(np.abs(rhs_v - dudt_ex_v)))
    return {"N": N, "h": h, "Linf_res_u": res_u, "Linf_res_v": res_v,
            "Linf_res": float(max(res_u, res_v))}


def run_V2a():
    backend = Backend(use_gpu=False)
    rows = [_spatial_residual(N, backend) for N in (32, 64, 128, 256)]
    return {"spatial": rows}


def run_all() -> dict:
    return {"V2a": run_V2a()}


# ── Plotting + summary ──────────────────────────────────────────────────────

def make_figures(results: dict) -> None:
    fig, ax_s = plt.subplots(figsize=(6.5, 4.4))

    rows_a = results["V2a"]["spatial"]
    hs = np.array([r["h"] for r in rows_a])
    res = np.array([r["Linf_res"] for r in rows_a])
    ax_s.loglog(hs, res, "o-", color="C0", label="$L_\\infty$ residual")
    ref4 = res[0] * (hs / hs[0]) ** 4
    ref6 = res[0] * (hs / hs[0]) ** 6
    ax_s.loglog(hs, ref4, "k--", alpha=0.4, label="$O(h^4)$")
    ax_s.loglog(hs, ref6, "k:",  alpha=0.4, label="$O(h^6)$")
    ax_s.invert_xaxis(); ax_s.set_xlabel("$h$"); ax_s.set_ylabel("$L_\\infty$ NS residual")
    ax_s.set_title("V2: CCD spatial residual on periodic NS"); ax_s.legend()

    save_figure(fig, OUT / "V2_ccd_periodic_ns_orders")


def print_summary(results: dict) -> None:
    print("V2-a (CCD spatial residual on periodic NS):")
    rows = results["V2a"]["spatial"]
    hs = np.array([r["h"] for r in rows])
    rs = np.array([r["Linf_res"] for r in rows])
    rates = compute_convergence_rates(rs, hs)
    for r, rate in zip(rows, [None] + list(rates)):
        rs_s = "" if rate is None else f"  slope={rate:.2f}"
        print(f"  N={r['N']:>4}  h={r['h']:.4e}  Linf_res={r['Linf_res']:.3e}{rs_s}")
    if len(rates):
        print(f"  → asymptotic CCD spatial order ≈ {rates[-1]:.2f}  (expected ≥ 4)")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V2 outputs in {OUT}")


if __name__ == "__main__":
    main()
