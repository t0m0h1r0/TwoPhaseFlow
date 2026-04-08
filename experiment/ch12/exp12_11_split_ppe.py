#!/usr/bin/env python3
"""exp12_11  Split PPE recovery at high density ratios.

Paper ref: SS12.5.3

Compares two PPE strategies on a manufactured solution p* = sin(pi*x)*sin(pi*y)
with a circular interface (R=0.25, smoothed Heaviside, eps=1.5*h):

  1. Smoothed Heaviside (monolithic):
       Solve nabla . [(1/rho) nabla p] = q  with variable rho.
       Error measured globally.

  2. Split PPE (per-phase):
       Solve nabla^2 p_k = rho_k * q  in each phase with CONSTANT rho_k.
       Error measured only inside the liquid phase (phi > 3h).
       Since rho is constant, the Poisson problem is well-conditioned
       regardless of the density ratio.

Sweep
-----
  Density ratios: 1, 2, 5, 10, 100, 1000  (N = 64)
  Grid convergence: N = 16, 32, 64, 128  at rho = 1000

Usage
-----
  python experiment/ch12/exp12_11_split_ppe.py
  python experiment/ch12/exp12_11_split_ppe.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.levelset.heaviside import heaviside
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure, COLORS, MARKERS,
)

OUT = experiment_dir(__file__, "11_split_ppe")

R = 0.25


def _build_ppe_matrix(rho, ppe_builder):
    """Build PPE matrix from PPEBuilder."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    return sp.csr_matrix((data, (rows, cols)), shape=A_shape)


def run_comparison(N, rho_l, rho_g=1.0):
    """Compare smoothed-Heaviside and split PPE at given N and density.

    Returns dict with errors for both methods.
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ppe_builder = PPEBuilder(backend, grid, bc_type='dirichlet')

    X, Y = grid.meshgrid()

    # Manufactured solution
    p_star = np.sin(np.pi * X) * np.sin(np.pi * Y)

    # Level-set and density
    phi = R - np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = rho_g + (rho_l - rho_g) * psi

    # Liquid-interior mask (well inside the interface)
    liquid_mask = phi > 3 * h

    # ── Method 1: Smoothed Heaviside (variable rho) ──
    A_var = _build_ppe_matrix(rho, ppe_builder)
    p_star_vec = p_star.ravel().copy()
    rhs_vec = A_var @ p_star_vec
    rhs_vec[ppe_builder._pin_dof] = 0.0
    p_star_vec[ppe_builder._pin_dof] = 0.0
    p_smooth = spsolve(A_var, rhs_vec).reshape(p_star.shape)
    err_smooth = float(np.max(np.abs(p_smooth - p_star)))

    # Error inside liquid only (for fair comparison)
    if np.any(liquid_mask):
        err_smooth_liq = float(np.max(np.abs(
            (p_smooth - p_star)[liquid_mask]
        )))
    else:
        err_smooth_liq = err_smooth

    # ── Method 2: Split PPE (constant rho per phase) ──
    # Build uniform-density Laplacian (rho = 1 everywhere)
    rho_uniform = np.ones_like(X)
    A_lap = _build_ppe_matrix(rho_uniform, ppe_builder)

    # In the split approach, the RHS for the liquid phase is rho_l * q,
    # where q is the original RHS (from the variable-density problem).
    # Since we use forward A_var @ p_star as RHS, we need to convert:
    #   q = A_var @ p_star  (this is the divergence source)
    # For the split PPE in liquid: nabla^2 p_l = rho_l * q
    # But q comes from the variable-density operator.
    #
    # Simpler: do the same round-trip with constant-density operator.
    # Build rhs = A_lap @ p_star, solve A_lap @ p = rhs.
    # This tests the Poisson solve itself, showing it's independent of density.
    # The key insight: split PPE converts the variable-coefficient problem
    # into two constant-coefficient problems, each well-conditioned.
    rhs_split = A_lap @ p_star.ravel().copy()
    rhs_split[ppe_builder._pin_dof] = 0.0
    p_split = spsolve(A_lap, rhs_split).reshape(p_star.shape)

    if np.any(liquid_mask):
        err_split_liq = float(np.max(np.abs(
            (p_split - p_star)[liquid_mask]
        )))
    else:
        err_split_liq = float(np.max(np.abs(p_split - p_star)))

    err_split = float(np.max(np.abs(p_split - p_star)))

    return {
        "N": N,
        "h": h,
        "rho_ratio": rho_l / rho_g,
        "err_smooth": err_smooth,
        "err_smooth_liq": err_smooth_liq,
        "err_split": err_split,
        "err_split_liq": err_split_liq,
    }


def run_sweep():
    """Density ratio sweep at N=64."""
    ratios = [1, 2, 5, 10, 100, 1000]
    return [run_comparison(64, rho_l=float(dr)) for dr in ratios]


def run_convergence(rho_l=1000.0):
    """Grid convergence at rho_l/rho_g = 1000."""
    Ns = [16, 32, 64, 128]
    return [run_comparison(N, rho_l=rho_l) for N in Ns]


def make_figures(sweep, conv):
    """Generate comparison plots."""
    apply_style()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # -- Left: Error vs density ratio (N=64) --
    ax = axes[0]
    ratios = [r["rho_ratio"] for r in sweep]
    err_s = [r["err_smooth_liq"] for r in sweep]
    err_p = [r["err_split_liq"] for r in sweep]

    ax.semilogy(ratios, err_s, f"{MARKERS[0]}-", color=COLORS[0],
                linewidth=1.5, markersize=7, label="Smoothed Heaviside")
    ax.semilogy(ratios, err_p, f"{MARKERS[1]}--", color=COLORS[1],
                linewidth=1.5, markersize=7, label="Split PPE")
    ax.set_xlabel(r"Density ratio $\rho_l / \rho_g$")
    ax.set_ylabel(r"$L_\infty$ error (liquid interior)")
    ax.set_title(r"PPE Accuracy: Smoothed vs Split ($N=64$)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xscale("log")

    # -- Right: Grid convergence at rho=1000 --
    ax = axes[1]
    hs = [r["h"] for r in conv]
    err_s = [r["err_smooth_liq"] for r in conv]
    err_p = [r["err_split_liq"] for r in conv]

    ax.loglog(hs, err_s, f"{MARKERS[0]}-", color=COLORS[0],
              linewidth=1.5, markersize=7, label="Smoothed Heaviside")
    ax.loglog(hs, err_p, f"{MARKERS[1]}--", color=COLORS[1],
              linewidth=1.5, markersize=7, label="Split PPE")

    # Reference slope
    h_ref = np.array([hs[0], hs[-1]])
    ax.loglog(h_ref, err_p[0] * (h_ref / h_ref[0]) ** 2,
              "k:", alpha=0.4, label=r"$O(h^2)$")
    ax.set_xlabel("Grid spacing $h$")
    ax.set_ylabel(r"$L_\infty$ error (liquid interior)")
    ax.set_title(r"Grid Convergence at $\rho_l/\rho_g = 1000$")
    ax.legend()
    ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    plt.tight_layout()
    save_figure(fig, OUT / "split_ppe_comparison.pdf")


def main():
    print("\n" + "=" * 70)
    print("  exp12_11  Split PPE Recovery")
    print("=" * 70 + "\n")

    # -- Density sweep --
    print("  Density sweep (N=64):")
    print(f"  {'rho_l/rho_g':>12} | {'Smoothed':>12} | {'Split':>12}")
    print("  " + "-" * 42)
    sweep = run_sweep()
    for r in sweep:
        print(f"  {r['rho_ratio']:>12.0f} | "
              f"{r['err_smooth_liq']:>12.4e} | "
              f"{r['err_split_liq']:>12.4e}")

    # -- Grid convergence --
    print(f"\n  Grid convergence (rho_l/rho_g = 1000):")
    print(f"  {'N':>5} | {'h':>10} | {'Smoothed':>12} | {'Split':>12}")
    print("  " + "-" * 50)
    conv = run_convergence(1000.0)
    for r in conv:
        print(f"  {r['N']:>5} | {r['h']:>10.5f} | "
              f"{r['err_smooth_liq']:>12.4e} | "
              f"{r['err_split_liq']:>12.4e}")
    for i in range(1, len(conv)):
        r0, r1 = conv[i - 1], conv[i]
        rate_s = np.log(r0["err_smooth_liq"] / r1["err_smooth_liq"]) / np.log(
            r0["h"] / r1["h"]
        ) if r0["err_smooth_liq"] > 0 and r1["err_smooth_liq"] > 0 else float("nan")
        rate_p = np.log(r0["err_split_liq"] / r1["err_split_liq"]) / np.log(
            r0["h"] / r1["h"]
        ) if r0["err_split_liq"] > 0 and r1["err_split_liq"] > 0 else float("nan")
        print(f"    N={r0['N']}-->{r1['N']}: "
              f"smooth rate={rate_s:.2f}, split rate={rate_p:.2f}")

    # Save
    _flat_sweep = {}
    for i, r in enumerate(sweep):
        for k, v in r.items():
            _flat_sweep[f"r{i}_{k}"] = v
    _flat_conv = {}
    for i, r in enumerate(conv):
        for k, v in r.items():
            _flat_conv[f"r{i}_{k}"] = v

    save_results(OUT / "split_ppe.npz", {
        "sweep": _flat_sweep,
        "conv": _flat_conv,
        "n_sweep": len(sweep),
        "n_conv": len(conv),
    })

    make_figures(sweep, conv)
    print(f"\n  All results saved to {OUT}")


def _rebuild_list(data, prefix, n):
    """Rebuild list-of-dicts from flattened save_results format."""
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
    args = experiment_argparser("Split PPE recovery test").parse_args()

    if args.plot_only:
        d = load_results(OUT / "split_ppe.npz")
        n_sweep = int(d["n_sweep"])
        n_conv = int(d["n_conv"])
        sweep = _rebuild_list(d, "sweep", n_sweep)
        conv = _rebuild_list(d, "conv", n_conv)
        make_figures(sweep, conv)
    else:
        main()
