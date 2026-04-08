#!/usr/bin/env python3
"""exp12_11  Split PPE recovery at high density ratios.

Paper ref: §11.5.3 (sec:split_ppe_recovery)

Compares two PPE strategies on a manufactured solution p* = sin(pi*x)*sin(pi*y)
with a circular interface (R=0.25, smoothed Heaviside, eps=1.5*h):

  1. Smoothed Heaviside (monolithic):
       RHS: q = CCD eval_LH(p*) = (1/rho)*Lap(p*) - (1/rho^2)*(grad rho . grad p*)
       Solve: A_FD_varrho @ p = q_discrete  (FD O(h^2))
       Error measured inside liquid (phi > 3h).

  2. Split PPE (per-phase, constant-density):
       RHS: q = Lap(p*) = -2*pi^2 * sin(pi*x)*sin(pi*y)  (analytical)
       Solve: A_FD_lap @ p = q_discrete  (FD O(h^2), constant coefficient)
       Error measured inside liquid (phi > 3h).
       Since rho is constant, the Poisson problem is well-conditioned
       regardless of the density ratio.

Key insight: The split PPE RHS is the simple Laplacian of p* (density-independent),
while the monolithic RHS involves (1/rho^2)(grad rho . grad p*) which is O(Δρ/h)
at the interface and pollutes the solution globally.

Sweep
-----
  Density ratios: 1, 2, 5, 10, 20, 50, 100, 1000  (N = 64)
  Grid convergence: N = 16, 32, 64, 128  at rho_l/rho_g = 10 and 1000
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__, "11_split_ppe")
R = 0.25


def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


# ── CCD high-accuracy RHS ─────────────────────────────────────────────────

def eval_LH_varrho(p, rho, ccd, backend):
    """(1/ρ)Δp - (1/ρ²)(∇ρ·∇p) via CCD O(h^6)."""
    xp = backend.xp
    p_dev = xp.asarray(p); rho_dev = xp.asarray(rho)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        dp, d2p = ccd.differentiate(p_dev, ax)
        drho, _ = ccd.differentiate(rho_dev, ax)
        Lp += d2p / rho_dev - (drho / rho_dev**2) * dp
    return np.asarray(backend.to_host(Lp))


# ── FD matrices ────────────────────────────────────────────────────────────

def build_fd_varrho_dirichlet(N, h, rho):
    """FD for (1/ρ)Δp - (1/ρ²)(∇ρ·∇p), Dirichlet BC."""
    nx = ny = N + 1; n = nx * ny
    drho_dx = np.zeros_like(rho); drho_dy = np.zeros_like(rho)
    for i in range(1, N):
        drho_dx[i, :] = (rho[i + 1, :] - rho[i - 1, :]) / (2 * h)
    for j in range(1, N):
        drho_dy[:, j] = (rho[:, j + 1] - rho[:, j - 1]) / (2 * h)

    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                inv_rho = 1.0 / rho[i, j]
                cx = drho_dx[i, j] / rho[i, j]**2
                cy = drho_dy[i, j] / rho[i, j]**2
                rows.append(k); cols.append((i + 1) * ny + j)
                vals.append(inv_rho / h**2 - cx / (2 * h))
                rows.append(k); cols.append((i - 1) * ny + j)
                vals.append(inv_rho / h**2 + cx / (2 * h))
                rows.append(k); cols.append(i * ny + (j + 1))
                vals.append(inv_rho / h**2 - cy / (2 * h))
                rows.append(k); cols.append(i * ny + (j - 1))
                vals.append(inv_rho / h**2 + cy / (2 * h))
                center = -4.0 * inv_rho / h**2
                rows.append(k); cols.append(k); vals.append(center)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


def build_fd_laplacian_dirichlet(N, h):
    """FD for Δp (constant coefficient), Dirichlet BC."""
    nx = ny = N + 1; n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                coeff = 1.0 / h**2
                rows.append(k); cols.append((i + 1) * ny + j); vals.append(coeff)
                rows.append(k); cols.append((i - 1) * ny + j); vals.append(coeff)
                rows.append(k); cols.append(i * ny + (j + 1)); vals.append(coeff)
                rows.append(k); cols.append(i * ny + (j - 1)); vals.append(coeff)
                rows.append(k); cols.append(k); vals.append(-4.0 * coeff)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


# ── Experiment ─────────────────────────────────────────────────────────────

def run_comparison(N, rho_ratio):
    """Compare smoothed-Heaviside and split PPE at given N and density ratio."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N; eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="dirichlet")
    X, Y = grid.meshgrid()

    # Manufactured solution (Dirichlet: p*=0 on boundary)
    p_star = np.sin(np.pi * X) * np.sin(np.pi * Y)

    # Level-set and density
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)  # phi>0 = liquid
    rho_g = 1.0 / rho_ratio
    H = smoothed_heaviside(phi, eps)
    rho = 1.0 + (rho_g - 1.0) * (1.0 - H)  # rho_l=1 inside, rho_g outside

    # Liquid interior mask (well inside interface)
    liquid_mask = phi > 3 * h

    # ── Method 1: Smoothed Heaviside (variable rho) ──
    # RHS from CCD O(h^6) evaluation
    rhs_var = eval_LH_varrho(p_star, rho, ccd, backend)
    # Zero Dirichlet BC
    rhs_var_flat = rhs_var.ravel().copy()
    for i in range(N + 1):
        for j in range(N + 1):
            if i == 0 or i == N or j == 0 or j == N:
                rhs_var_flat[i * (N + 1) + j] = 0.0

    A_var = build_fd_varrho_dirichlet(N, h, rho)
    p_smooth = spsolve(A_var, rhs_var_flat).reshape(p_star.shape)
    err_smooth = float(np.max(np.abs(p_smooth - p_star)))
    err_smooth_liq = float(np.max(np.abs((p_smooth - p_star)[liquid_mask]))) \
        if np.any(liquid_mask) else err_smooth

    # ── Method 2: Split PPE (constant-density Laplacian) ──
    # Analytical RHS: Δp* = -2π² sin(πx)sin(πy)
    rhs_lap = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
    rhs_lap_flat = rhs_lap.ravel().copy()
    for i in range(N + 1):
        for j in range(N + 1):
            if i == 0 or i == N or j == 0 or j == N:
                rhs_lap_flat[i * (N + 1) + j] = 0.0

    A_lap = build_fd_laplacian_dirichlet(N, h)
    p_split = spsolve(A_lap, rhs_lap_flat).reshape(p_star.shape)
    err_split = float(np.max(np.abs(p_split - p_star)))
    err_split_liq = float(np.max(np.abs((p_split - p_star)[liquid_mask]))) \
        if np.any(liquid_mask) else err_split

    return {
        "N": N, "h": h, "rho_ratio": float(rho_ratio),
        "err_smooth": err_smooth, "err_smooth_liq": err_smooth_liq,
        "err_split": err_split, "err_split_liq": err_split_liq,
    }


def run_sweep():
    """Density ratio sweep at N=64."""
    ratios = [1, 2, 5, 10, 20, 50, 100, 1000]
    results = []
    for dr in ratios:
        r = run_comparison(64, dr)
        results.append(r)
        ratio_str = f"  rho={dr:>5}: smooth={r['err_smooth_liq']:.4e}  split={r['err_split_liq']:.4e}"
        if r['err_smooth_liq'] > 0 and r['err_split_liq'] > 0:
            ratio_str += f"  improvement={r['err_smooth_liq']/r['err_split_liq']:.0f}x"
        print(ratio_str)
    return results


def run_convergence(rho_ratio):
    """Grid convergence at given density ratio."""
    Ns = [16, 32, 64, 128]
    results = []
    for N in Ns:
        r = run_comparison(N, rho_ratio)
        results.append(r)
    return results


def compute_rates(results, key):
    """Compute convergence rates."""
    rates = []
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0[key] > 0 and r1[key] > 0:
            rates.append(np.log(r0[key] / r1[key]) / np.log(r0["h"] / r1["h"]))
        else:
            rates.append(float("nan"))
    return rates


def make_figures(sweep, conv_10, conv_1000):
    """Generate comparison plots."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # ── Left: Error vs density ratio (N=64) ──
    ax = axes[0]
    ratios = [r["rho_ratio"] for r in sweep]
    err_s = [r["err_smooth_liq"] for r in sweep]
    err_p = [r["err_split_liq"] for r in sweep]

    ax.semilogy(ratios, err_s, f"{MARKERS[0]}-", color=COLORS[0],
                linewidth=1.5, markersize=7, label="Smoothed Heaviside")
    ax.semilogy(ratios, err_p, f"{MARKERS[1]}--", color=COLORS[1],
                linewidth=1.5, markersize=7, label=r"Split PPE ($\nabla^2 p = f$)")
    ax.set_xlabel(r"$\rho_l/\rho_g$")
    ax.set_ylabel(r"$L_\infty$ error (liquid interior)")
    ax.set_title(r"PPE Accuracy ($N=64$)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xscale("log")

    # ── Middle: Grid convergence at rho=10 ──
    ax = axes[1]
    hs = [r["h"] for r in conv_10]
    err_s = [r["err_smooth_liq"] for r in conv_10]
    err_p = [r["err_split_liq"] for r in conv_10]
    ax.loglog(hs, err_s, f"{MARKERS[0]}-", color=COLORS[0],
              linewidth=1.5, markersize=7, label="Smoothed Heaviside")
    ax.loglog(hs, err_p, f"{MARKERS[1]}--", color=COLORS[1],
              linewidth=1.5, markersize=7, label="Split PPE")
    h_ref = np.array([hs[0], hs[-1]])
    ax.loglog(h_ref, err_p[0] * (h_ref / h_ref[0])**2,
              "k:", alpha=0.4, label=r"$O(h^2)$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title(r"Grid convergence ($\rho_l/\rho_g = 10$)")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    # ── Right: Grid convergence at rho=1000 ──
    ax = axes[2]
    hs = [r["h"] for r in conv_1000]
    err_s = [r["err_smooth_liq"] for r in conv_1000]
    err_p = [r["err_split_liq"] for r in conv_1000]
    ax.loglog(hs, err_s, f"{MARKERS[0]}-", color=COLORS[0],
              linewidth=1.5, markersize=7, label="Smoothed Heaviside")
    ax.loglog(hs, err_p, f"{MARKERS[1]}--", color=COLORS[1],
              linewidth=1.5, markersize=7, label="Split PPE")
    h_ref = np.array([hs[0], hs[-1]])
    ax.loglog(h_ref, err_p[0] * (h_ref / h_ref[0])**2,
              "k:", alpha=0.4, label=r"$O(h^2)$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title(r"Grid convergence ($\rho_l/\rho_g = 1000$)")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    fig.tight_layout()
    save_figure(fig, OUT / "split_ppe_comparison")


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    args = experiment_argparser("Split PPE recovery test").parse_args()
    if args.plot_only:
        d = load_results(OUT / "split_ppe.npz")
        n_sweep = int(d["n_sweep"])
        n_conv_10 = int(d["n_conv_10"])
        n_conv_1000 = int(d["n_conv_1000"])
        sweep = _rebuild_list(d, "sweep", n_sweep)
        conv_10 = _rebuild_list(d, "conv_10", n_conv_10)
        conv_1000 = _rebuild_list(d, "conv_1000", n_conv_1000)
        make_figures(sweep, conv_10, conv_1000)
        return

    print("\n" + "=" * 70)
    print("  exp12_11  Split PPE Recovery (corrected: analytical RHS)")
    print("=" * 70)

    # ── Density sweep ──
    print("\n  Density sweep (N=64):")
    sweep = run_sweep()

    # ── Grid convergence ──
    for rho_ratio in [10, 1000]:
        print(f"\n  Grid convergence (rho_l/rho_g = {rho_ratio}):")
        conv = run_convergence(rho_ratio)
        for r in conv:
            print(f"    N={r['N']:>3}: smooth={r['err_smooth_liq']:.4e}"
                  f"  split={r['err_split_liq']:.4e}")
        rates_s = compute_rates(conv, "err_smooth_liq")
        rates_p = compute_rates(conv, "err_split_liq")
        for i, (rs, rp) in enumerate(zip(rates_s, rates_p)):
            print(f"      N={conv[i]['N']}→{conv[i+1]['N']}:"
                  f" smooth={rs:.2f}  split={rp:.2f}")

    conv_10 = run_convergence(10)
    conv_1000 = run_convergence(1000)

    # ── Save ──
    flat = {}
    for i, r in enumerate(sweep):
        for k, v in r.items():
            flat[f"sweep__r{i}_{k}"] = v
    flat["n_sweep"] = len(sweep)
    for i, r in enumerate(conv_10):
        for k, v in r.items():
            flat[f"conv_10__r{i}_{k}"] = v
    flat["n_conv_10"] = len(conv_10)
    for i, r in enumerate(conv_1000):
        for k, v in r.items():
            flat[f"conv_1000__r{i}_{k}"] = v
    flat["n_conv_1000"] = len(conv_1000)
    save_results(OUT / "split_ppe.npz", flat)

    make_figures(sweep, conv_10, conv_1000)
    print(f"\n  Results saved to {OUT}")


def _rebuild_list(data, prefix, n):
    keys = ["N", "h", "rho_ratio", "err_smooth", "err_smooth_liq",
            "err_split", "err_split_liq"]
    results = []
    for i in range(n):
        r = {}
        for k in keys:
            full = f"{prefix}__r{i}_{k}"
            if full in data:
                r[k] = data[full]
        results.append(r)
    return results


if __name__ == "__main__":
    main()
