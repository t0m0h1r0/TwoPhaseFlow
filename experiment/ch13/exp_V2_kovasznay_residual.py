#!/usr/bin/env python3
"""[V2] Kovasznay-flow CCD spatial residual — Type-A (revised criterion).

Paper ref: §13.1 (sec:kovasznay).

Applies the project's CCD operators to the analytic steady Kovasznay flow at
Re=40 and measures the steady incompressible NS residual

    u·∇u + ∇p − ν∆u = 0,    ∇·u = 0.

The previous manufactured periodic residual is retained as a C2 legacy script
under ``experiment/ch13/legacy/``.

Usage
-----
  make run EXP=experiment/ch13/exp_V2_kovasznay_residual.py
  make plot EXP=experiment/ch13/exp_V2_kovasznay_residual.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.simulation.visualization.plot_fields import (
    field_with_contour,
    streamlines_colored,
)
from twophase.tools.experiment import (
    apply_style,
    compute_convergence_rates,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIGURES = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

RE = 40.0
NU = 1.0 / RE
X0 = -0.5
LX = 1.5
LY = 1.0
N_LIST = (32, 64, 128, 256)


def _lambda_re() -> float:
    return RE / 2.0 - np.sqrt((RE / 2.0) ** 2 + 4.0 * np.pi**2)


def _setup_grid(N: int, backend: Backend):
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(LX, LY)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    X_raw, Y = grid.meshgrid()
    X = np.asarray(backend.to_host(X_raw)) + X0
    Y = np.asarray(backend.to_host(Y))
    return grid, ccd, LX / N, X, Y


def _kovasznay(X: np.ndarray, Y: np.ndarray):
    lam = _lambda_re()
    exp_lx = np.exp(lam * X)
    u = 1.0 - exp_lx * np.cos(2.0 * np.pi * Y)
    v = (lam / (2.0 * np.pi)) * exp_lx * np.sin(2.0 * np.pi * Y)
    p = 0.5 * (1.0 - np.exp(2.0 * lam * X))
    return u, v, p


def _ccd_grad(field, ccd, axis: int, backend: Backend) -> np.ndarray:
    d1, _ = ccd.differentiate(field, axis)
    return np.asarray(backend.to_host(d1))


def _ccd_lap(field, ccd, backend: Backend) -> np.ndarray:
    _, d2x = ccd.differentiate(field, 0)
    _, d2y = ccd.differentiate(field, 1)
    return np.asarray(backend.to_host(d2x)) + np.asarray(backend.to_host(d2y))


def _residual(N: int, backend: Backend) -> dict:
    _, ccd, h, X, Y = _setup_grid(N, backend)
    u, v, p = _kovasznay(X, Y)
    du_dx = _ccd_grad(u, ccd, 0, backend)
    du_dy = _ccd_grad(u, ccd, 1, backend)
    dv_dx = _ccd_grad(v, ccd, 0, backend)
    dv_dy = _ccd_grad(v, ccd, 1, backend)
    dp_dx = _ccd_grad(p, ccd, 0, backend)
    dp_dy = _ccd_grad(p, ccd, 1, backend)
    lap_u = _ccd_lap(u, ccd, backend)
    lap_v = _ccd_lap(v, ccd, backend)
    res_u = u * du_dx + v * du_dy + dp_dx - NU * lap_u
    res_v = u * dv_dx + v * dv_dy + dp_dy - NU * lap_v
    div = du_dx + dv_dy
    core = (slice(4, -4), slice(4, -4))
    res_full = np.sqrt(res_u * res_u + res_v * res_v)
    res_core = res_full[core]
    div_core = div[core]
    row = {
        "N": N,
        "h": h,
        "Linf_res": float(np.max(np.abs(res_core))),
        "Linf_res_full": float(np.max(np.abs(res_full))),
        "Linf_div": float(np.max(np.abs(div_core))),
        "Linf_div_full": float(np.max(np.abs(div))),
    }
    if N == N_LIST[-1]:
        row["_X"] = X
        row["_Y"] = Y
        row["_u"] = u
        row["_v"] = v
        row["_res_full"] = res_full
        row["_div"] = div
    return row


def run_all() -> dict:
    backend = Backend(use_gpu=False)
    rows = [_residual(N, backend) for N in N_LIST]
    field_kovasznay: dict = {}
    finest = rows[-1]
    for k in ("_X", "_Y", "_u", "_v", "_res_full", "_div"):
        if k in finest:
            field_kovasznay[k.lstrip("_")] = finest.pop(k)
    out = {
        "spatial": rows,
        "meta": {"Re": RE, "nu": NU, "domain": [X0, X0 + LX, 0.0, LY]},
    }
    if field_kovasznay:
        out["field_kovasznay"] = field_kovasznay
    return out


def make_figures(results: dict) -> None:
    rows = results["spatial"]
    hs = np.array([r["h"] for r in rows])
    errs = np.array([r["Linf_res"] for r in rows])
    divs = np.array([r["Linf_div"] for r in rows])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_r, ax_d = axes
    ax_r.loglog(hs, errs, "o-", color="C0", label="CCD residual (interior)")
    ax_r.loglog(hs, errs[0] * (hs / hs[0]) ** 6, "k--", alpha=0.5, label="O(h⁶)")
    ax_r.invert_xaxis()
    ax_r.set_xlabel("h")
    ax_r.set_ylabel(r"$\|R\|_\infty$")
    ax_r.set_title("V2: Kovasznay steady NS residual")
    ax_r.legend()
    ax_d.loglog(hs, divs, "s-", color="C2", label=r"$\|\nabla\cdot u\|_\infty$")
    ax_d.invert_xaxis()
    ax_d.set_xlabel("h")
    ax_d.set_ylabel("divergence residual")
    ax_d.set_title("Analytic incompressibility under CCD")
    ax_d.legend()
    save_figure(
        fig,
        OUT / "V2_kovasznay_orders",
        also_to=PAPER_FIGURES / "ch13_v2_kovasznay_orders",
    )
    make_kovasznay_field_figure(results)


def make_kovasznay_field_figure(results: dict) -> None:
    """1×3 panel at N=256: streamlines + log10|R| + log10|∇·u|.

    Skip silently if `field_kovasznay` is missing (e.g. legacy npz cache).
    """
    panel = results.get("field_kovasznay")
    if not panel or "u" not in panel:
        return
    X = np.asarray(panel["X"])
    Y = np.asarray(panel["Y"])
    x1d = X[:, 0]
    y1d = Y[0, :]
    u = np.asarray(panel["u"])
    v = np.asarray(panel["v"])
    res_full = np.asarray(panel["res_full"])
    div = np.asarray(panel["div"])
    speed = np.sqrt(u * u + v * v)
    log_res = np.log10(np.maximum(res_full, 1e-16))
    log_div = np.log10(np.maximum(np.abs(div), 1e-16))

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    ax_s, ax_r, ax_d = axes

    streamlines_colored(
        ax_s, x1d, y1d, u, v,
        cmap="viridis", density=1.6, linewidth=0.9, arrowsize=0.9,
    )
    sm = plt.cm.ScalarMappable(
        cmap="viridis",
        norm=plt.Normalize(vmin=float(speed.min()), vmax=float(speed.max())),
    )
    sm.set_array([])
    fig.colorbar(sm, ax=ax_s, fraction=0.046, pad=0.04, label=r"$|u|$")
    ax_s.set_title(r"(a) Kovasznay velocity (Re=40)" + "\n" + rf"$|u|\in[{speed.min():.2f},\,{speed.max():.2f}]$", fontsize=11)
    ax_s.set_xlabel("$x$")
    ax_s.set_ylabel("$y$")
    ax_s.set_xlim(x1d.min(), x1d.max())
    ax_s.set_ylim(y1d.min(), y1d.max())

    im_r = field_with_contour(
        ax_r, x1d, y1d, log_res,
        cmap="magma",
        title=rf"(b) $\log_{{10}}\|R\|$  (max $={np.max(res_full):.1e}$)",
        xlabel="$x$", ylabel="",
    )
    fig.colorbar(im_r, ax=ax_r, fraction=0.046, pad=0.04, label=r"$\log_{10}\|R\|$")

    im_d = field_with_contour(
        ax_d, x1d, y1d, log_div,
        cmap="cividis",
        title=rf"(c) $\log_{{10}}|\nabla\!\cdot u|$  (max $={np.max(np.abs(div)):.1e}$)",
        xlabel="$x$", ylabel="",
    )
    fig.colorbar(im_d, ax=ax_d, fraction=0.046, pad=0.04, label=r"$\log_{10}|\nabla\!\cdot u|$")

    fig.suptitle(
        "V2 Kovasznay (N=256): velocity streamlines + CCD residual + divergence",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1.0, 0.93))
    save_figure(
        fig,
        OUT / "V2_kovasznay_field",
        also_to=PAPER_FIGURES / "ch13_v2_kovasznay_field",
    )


def print_summary(results: dict) -> None:
    print("V2 (Kovasznay CCD spatial residual):")
    rows = results["spatial"]
    errs = np.array([r["Linf_res"] for r in rows])
    hs = np.array([r["h"] for r in rows])
    rates = compute_convergence_rates(errs, hs)
    for row, rate in zip(rows, [None] + list(rates)):
        rate_s = "" if rate is None else f"  slope={rate:.2f}"
        print(
            f"  N={row['N']:>3}  h={row['h']:.3e}  "
            f"R={row['Linf_res']:.3e}  div={row['Linf_div']:.3e}{rate_s}"
        )
    if len(rates):
        print(f"  → asymptotic residual order ≈ {rates[-1]:.2f}")


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
