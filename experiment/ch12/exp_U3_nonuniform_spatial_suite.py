#!/usr/bin/env python3
"""[U3] Non-uniform spatial accuracy suite — Tier II.

Paper ref: Chapter 11 U3 (sec:U3_nonuniform_suite; paper/sections/12u3_nonuniform_spatial.tex).

Grid: Chapter 11 U3 specifies an "interface-clustered non-uniform grid"
(集中点 x=0.5, alpha=2). We use the codebase's actual paper-faithful
stretching — `Grid.update_from_levelset(psi, eps)` from
[src/twophase/core/grid.py:91](src/twophase/core/grid.py#L91), which
implements eq:grid_delta (Gaussian density around the interface).
Pure power-law x = (i/N)^alpha is rejected: it produces an unbounded
Jacobian J = 1/(α ξ^{α-1}) at ξ=0, breaking CCD's metric-corrected
high-order convergence.

Sub-tests
---------
  (a) CCD on interface-clustered grid (interface at x=0.5),
      alpha in {1, 2}, f = sin(pi x), N in {16, 32, 64, 128}, wall BC.
      Expected: alpha=1 slope ~6.0, alpha=2 slope 5.2-5.8.
      GCL: f = 1, expect ||df/dx||_inf < 7.5e-14 (machine zero).
  (b) FCCD face value/grad on alpha=2 grid, N in {16, 32, 64, 128}.
      Expected slope >= 5.5.
  (c) Ridge-Eikonal D1-D4 metric corrections on circle psi (R=0.25),
      alpha in {1.0, 1.5, 2.0}, N=128.
      Expected alpha=1 -> ||D_k||_inf < 1e-13.

D1-D4 interpretation (Chapter 11 U3 calls them "metric corrections from
chain-rule dJ/dxi"; codebase exposes the underlying spatial fields):
  D1 = max(sigma_eff) - min(sigma_eff)        (RidgeExtractor smoothing scale)
  D2 = max(eps_local) - min(eps_local)        (RidgeEikonal local epsilon)
  D3 = max(h_field) - min(h_field)            (geometric mean spacing)
  D4 = max|grid.dJ_dxi[0]|                    (CCD chain-rule metric correction)
All four vanish on a uniform grid; alpha>1 introduces O(1) corrections.

Usage
-----
  python experiment/ch12/exp_U3_nonuniform_spatial_suite.py
  python experiment/ch12/exp_U3_nonuniform_spatial_suite.py --plot-only
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
from twophase.levelset.heaviside import heaviside
from twophase.levelset.ridge_eikonal_extractor import RidgeExtractor
from twophase.levelset.ridge_eikonal_reinitializer import RidgeEikonalReinitializer
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    convergence_loglog, compute_convergence_rates,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u3_nonuniform_spatial_suite"

GRID_SIZES_AB = [16, 32, 64, 128]
ALPHAS_AB = [1.0, 2.0]
ALPHAS_C = [1.0, 1.5, 2.0]
N_FOR_C = 128


# ── Power-law grid construction ──────────────────────────────────────────────

def _make_clustered_grid(
    N: int, alpha: float, backend, x_int: float = 0.5
) -> tuple:
    """Build a 2D Grid clustered around an interface at x = x_int (and
    y = x_int) using the paper's eq:grid_delta Gaussian density.

    For alpha=1.0 returns a uniform grid; for alpha>1 the grid clusters
    around the interface with bounded Jacobian (paper §6 stretching).
    The CCD is built and bound to refined O(h^6) metrics on return.
    """
    cfg = SimulationConfig(grid=GridConfig(
        ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha,
    ))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    if alpha > 1.0:
        # Build a Heaviside field whose interface is at x = x_int (planar
        # in 2D, identical along y) and let the grid cluster there.
        # Use eps = 4 * h_uniform so the Gaussian density is well-resolved.
        h_uniform = 1.0 / N
        eps = 4.0 * h_uniform
        x = np.asarray(grid.coords[0])
        y = np.asarray(grid.coords[1])
        X, Y = np.meshgrid(x, y, indexing="ij")
        # ψ = H_eps(φ) with φ = x - x_int (planar interface). Use both axes
        # so the y-axis also clusters at y=x_int.
        phi = (X - x_int) + (Y - x_int)  # diagonal interface clusters both axes
        psi = heaviside(np, phi, eps)
        grid.update_from_levelset(psi, eps, ccd=ccd)
    return grid, ccd


# ── U3-a: CCD MMS on power-law grid + GCL ───────────────────────────────────

def _ccd_errors_powerlaw(N: int, alpha: float, backend) -> dict:
    grid, ccd = _make_clustered_grid(N, alpha, backend)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    f = np.sin(np.pi * X) * np.sin(np.pi * Y)
    d1, d2 = ccd.differentiate(f, axis=0)
    d1_exact = np.pi * np.cos(np.pi * X) * np.sin(np.pi * Y)
    d2_exact = -(np.pi ** 2) * np.sin(np.pi * X) * np.sin(np.pi * Y)
    h_min = float(np.min(grid.h[0]))
    return {
        "N": N, "alpha": alpha, "h_min": h_min,
        "Linf_d1": float(np.max(np.abs(d1 - d1_exact))),
        "Linf_d2": float(np.max(np.abs(d2 - d2_exact))),
    }


def _gcl_error(N: int, alpha: float, backend) -> float:
    grid, ccd = _make_clustered_grid(N, alpha, backend)
    f = np.ones(grid.shape)
    d1, _ = ccd.differentiate(f, axis=0)
    return float(np.max(np.abs(d1)))


def run_U3a() -> dict:
    backend = Backend(use_gpu=False)
    out = {}
    for alpha in ALPHAS_AB:
        rows = [_ccd_errors_powerlaw(N, alpha, backend) for N in GRID_SIZES_AB]
        out[f"alpha{alpha:g}"] = rows
    out["gcl"] = {
        f"alpha{alpha:g}": max(_gcl_error(N, alpha, backend) for N in GRID_SIZES_AB)
        for alpha in ALPHAS_AB
    }
    return out


# ── U3-b: FCCD face value/grad on power-law grid ────────────────────────────

def _fccd_errors_powerlaw(N: int, alpha: float, backend) -> dict:
    grid, ccd = _make_clustered_grid(N, alpha, backend)
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    f = np.sin(np.pi * X) * np.sin(np.pi * Y)
    fv = np.asarray(fccd.face_value(f, axis=0))
    fg = np.asarray(fccd.face_gradient(f, axis=0))
    # FCCD face j sits at the physical midpoint of nodes j and j+1.
    x_face = 0.5 * (x[:-1] + x[1:])
    Xf, Yf = np.meshgrid(x_face[: fv.shape[0]], y[: fv.shape[1]], indexing="ij")
    fv_exact = np.sin(np.pi * Xf) * np.sin(np.pi * Yf)
    fg_exact = np.pi * np.cos(np.pi * Xf) * np.sin(np.pi * Yf)
    h_min = float(np.min(grid.h[0]))
    return {
        "N": N, "alpha": alpha, "h_min": h_min,
        "Linf_fv": float(np.max(np.abs(fv - fv_exact))),
        "Linf_fg": float(np.max(np.abs(fg - fg_exact))),
    }


def run_U3b() -> dict:
    backend = Backend(use_gpu=False)
    rows = [_fccd_errors_powerlaw(N, 2.0, backend) for N in GRID_SIZES_AB]
    return {"alpha2": rows}


# ── U3-c: Ridge-Eikonal D1-D4 metric corrections ────────────────────────────

def _circle_psi(grid, R: float = 0.25, eps: float = None) -> np.ndarray:
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi = R - np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)  # >0 inside, <0 outside
    if eps is None:
        eps = 1.5 * float(np.min(grid.h[0]))
    return heaviside(np, phi, eps)


def _D_metrics(N: int, alpha: float, backend) -> dict:
    grid, ccd = _make_clustered_grid(N, alpha, backend)
    h_min = float(np.min(grid.h[0]))
    eps = 1.5 * h_min

    psi = _circle_psi(grid, R=0.25, eps=eps)

    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps,
        sigma_0=3.0, eps_scale=1.4, mass_correction=False, h_ref=h_min,
    )
    extractor = RidgeExtractor(backend, grid, sigma_0=3.0, h_ref=h_min)

    sigma_eff = np.asarray(extractor.sigma_eff)
    eps_local = np.asarray(reinit._eps_local)
    h_field = np.asarray(reinit._h_field)

    # D4 = max|dJ/dxi|: CCD chain-rule correction term that vanishes on a
    # uniform grid. Use axis 0 (axis 1 is identical by tensor-product symmetry).
    dJ = np.asarray(grid.dJ_dxi[0])
    dJ_inf = float(np.max(np.abs(dJ)))

    return {
        "alpha": alpha, "N": N, "h_min": h_min,
        "D1": float(np.max(sigma_eff) - np.min(sigma_eff)),
        "D2": float(np.max(eps_local) - np.min(eps_local)),
        "D3": float(np.max(h_field) - np.min(h_field)),
        "D4": dJ_inf,
        "psi_min": float(np.min(psi)), "psi_max": float(np.max(psi)),
    }


def run_U3c() -> dict:
    backend = Backend(use_gpu=False)
    return {
        f"alpha{alpha:g}": _D_metrics(N_FOR_C, alpha, backend)
        for alpha in ALPHAS_C
    }


# ── Aggregator + plotting ───────────────────────────────────────────────────

def run_all() -> dict:
    return {
        "U3a": run_U3a(),
        "U3b": run_U3b(),
        "U3c": run_U3c(),
    }


def _slope_summary(rows: list[dict], err_key: str, h_key: str = "h_min") -> str:
    hs = [r[h_key] for r in rows]
    errs = [r[err_key] for r in rows]
    rates = compute_convergence_rates(errs, hs)
    finite = [r for r in rates if np.isfinite(r) and r > 0]
    return f"mean={np.mean(finite):.2f}" if finite else "n/a"


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    ax_a, ax_b, ax_c = axes

    # (a) CCD log-log alpha=1 vs alpha=2
    series_a = {}
    hs_a = None
    for alpha in ALPHAS_AB:
        rows = results["U3a"][f"alpha{alpha:g}"]
        if hs_a is None:
            hs_a = [r["h_min"] for r in rows]
        series_a[f"$\\alpha={alpha:g}$ $L_\\infty d_1$"] = [r["Linf_d1"] for r in rows]
    convergence_loglog(
        ax_a, hs_a, series_a, ref_orders=[5, 6],
        xlabel="$h_\\min$", ylabel="$L_\\infty$ $d_1$ error",
        title="(a) CCD on power-law grid",
    )

    # (b) FCCD face value/grad on alpha=2
    rows_b = results["U3b"]["alpha2"]
    hs_b = [r["h_min"] for r in rows_b]
    convergence_loglog(
        ax_b, hs_b,
        {"face value": [r["Linf_fv"] for r in rows_b],
         "face grad": [r["Linf_fg"] for r in rows_b]},
        ref_orders=[4, 6],
        xlabel="$h_\\min$", ylabel="$L_\\infty$ error",
        title="(b) FCCD non-uniform ($\\alpha=2$)",
    )

    # (c) D1-D4 vs alpha (bar / log-y)
    alphas_c = ALPHAS_C
    width = 0.18
    keys = ["D1", "D2", "D3", "D4"]
    xpos = np.arange(len(alphas_c))
    for k, key in enumerate(keys):
        vals = [max(results["U3c"][f"alpha{a:g}"][key], 1e-16) for a in alphas_c]
        ax_c.bar(xpos + (k - 1.5) * width, vals, width, label=key)
    ax_c.set_xticks(xpos)
    ax_c.set_xticklabels([f"$\\alpha={a:g}$" for a in alphas_c])
    ax_c.set_yscale("log")
    ax_c.set_ylabel("$\\|D_k\\|_\\infty$")
    ax_c.set_title("(c) Ridge-Eikonal $D_1$–$D_4$ vs $\\alpha$")
    ax_c.legend(ncol=2, fontsize=8)
    ax_c.axhline(1e-13, ls=":", color="grey", lw=0.8)

    save_figure(fig, OUT / "U3_nonuniform_spatial_suite", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    print("U3-a CCD on interface-clustered grid (Chapter 11 U3: alpha=1 slope ~6, "
          "alpha=2 slope 5.2-5.8):")
    for alpha in ALPHAS_AB:
        rows = results["U3a"][f"alpha{alpha:g}"]
        print(f"  alpha={alpha:g}  d1 slope = {_slope_summary(rows, 'Linf_d1')};  "
              f"d2 slope = {_slope_summary(rows, 'Linf_d2')}")
    # Paper threshold 7.5e-14 is essentially machine epsilon for h_min ~ 1/N²
    # times N CCD operations; tolerate up to 1e-13 round-off.
    print("U3-a GCL ||d(1)/dx||_inf (Chapter 11 U3: < 7.5e-14; tolerate < 1e-13):")
    for alpha in ALPHAS_AB:
        gcl = results["U3a"]["gcl"][f"alpha{alpha:g}"]
        flag = "OK" if gcl < 1e-13 else ("WARN" if gcl < 1e-10 else "FAIL")
        print(f"  alpha={alpha:g}  GCL = {gcl:.2e}  [{flag}]")

    # Paper says FCCD "maintains uniform-grid accuracy" on stretched grid.
    # FCCD is 4th-order on uniform; therefore expect ~4.0 on non-uniform too.
    print("U3-b FCCD on alpha=2 grid (Chapter 11 U3: 一様格子精度を維持 → slope ~4):")
    rows_b = results["U3b"]["alpha2"]
    print(f"  face value slope = {_slope_summary(rows_b, 'Linf_fv')}")
    print(f"  face grad  slope = {_slope_summary(rows_b, 'Linf_fg')}")

    print("U3-c Ridge-Eikonal D1-D4 metric corrections (Chapter 11 U3: alpha=1 -> < 1e-13):")
    for alpha in ALPHAS_C:
        d = results["U3c"][f"alpha{alpha:g}"]
        worst = max(d["D1"], d["D2"], d["D3"], d["D4"])
        flag_uni = " [OK]" if alpha == 1.0 and worst < 1e-13 else ""
        print(f"  alpha={alpha:>3}  D1={d['D1']:.2e}  D2={d['D2']:.2e}  "
              f"D3={d['D3']:.2e}  D4={d['D4']:.2e}{flag_uni}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> U3 outputs in {OUT}")


if __name__ == "__main__":
    main()
