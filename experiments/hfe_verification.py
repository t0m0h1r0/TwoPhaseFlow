#!/usr/bin/env python3
"""
HFE verification experiments for §10.2.2.

Test (a): 1D field extension convergence — upwind O(h^1) vs Hermite O(h^6)
Test (c): 2D field extension convergence — circular interface, tensor-product

Usage:
    python experiments/hfe_verification.py

Outputs:
    experiments/results/hfe_1d_convergence.txt
    experiments/results/hfe_2d_convergence.txt
    experiments/figures/hfe_convergence.pdf
"""

import sys
import os
import pathlib

# Add src to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.hfe.hermite_interp import hermite5_coeffs, hermite5_eval
from twophase.hfe.field_extension import HermiteFieldExtension


class _GridConfig:
    """Minimal GridConfig stub."""
    def __init__(self, N, L):
        self.ndim = len(N)
        self.N = list(N)
        self.L = list(L)
        self.alpha_grid = 1.0


# ══════════════════════════════════════════════════════════════════════════
# Test (a): 1D field extension convergence
# ══════════════════════════════════════════════════════════════════════════

def test_a_1d_convergence():
    """1D convergence: upwind O(h^1) vs Hermite O(h^6).

    Setup (§10.2.2 Test (a)):
      - Effective 1D (y-uniform 2D grid), x ∈ [0,1], φ = x - 0.5
      - Source field: q(x) = 1 + cos(πx) (smooth everywhere)
      - Exact extension: q_ext = q(0.5) = 1 (constant along normal)
      - Error measured in x ∈ [0.52, 0.55]
      - N = 32, 64, 128, 256
    """
    print("=" * 70)
    print("Test (a): 1D field extension convergence")
    print("=" * 70)

    grid_sizes = [32, 64, 128, 256]
    results_upwind = []
    results_hermite = []

    for N in grid_sizes:
        h = 1.0 / N
        x = np.linspace(0.0, 1.0, N + 1)

        # Source field: q(x) = 1 + cos(πx)
        q = 1.0 + np.cos(np.pi * x)
        # Exact extension: q_ext(x) = q(x_Γ) = q(0.5) = 1.0
        q_exact = 1.0

        i_iface = N // 2  # x[i_iface] = 0.5

        # --- Upwind baseline (Aslam 2004) ---
        # Nearest source cell: x[i_iface - 1] = 0.5 - h
        q_upwind = np.copy(q)
        for i in range(i_iface, N + 1):
            q_upwind[i] = q[i_iface - 1]  # nearest source value

        # --- Hermite (HFE) 1D ---
        # CCD on 1D grid (embedded in 2D for CCD solver)
        backend = Backend(use_gpu=False)
        gc = _GridConfig(N=[N, N], L=[1.0, 1.0])
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")

        # Compute CCD derivatives of q along x (use 2D embedding)
        q_2d = np.outer(q, np.ones(N + 1))
        dq_dx, d2q_dx2 = ccd.differentiate(q_2d, axis=0)

        # Hermite interpolation at x_Γ = 0.5 for each target point
        q_hermite = np.copy(q)
        x_gamma = 0.5  # closest point = interface
        # Bracket containing x_Γ: [x[i_iface-1], x[i_iface]]
        ia, ib = i_iface - 1, i_iface
        xi = (x_gamma - x[ia]) / h
        j_mid = N // 2  # arbitrary y-row
        coeffs = hermite5_coeffs(
            float(q_2d[ia, j_mid]), float(dq_dx[ia, j_mid]), float(d2q_dx2[ia, j_mid]),
            float(q_2d[ib, j_mid]), float(dq_dx[ib, j_mid]), float(d2q_dx2[ib, j_mid]),
            h,
        )
        q_at_gamma = hermite5_eval(coeffs, xi)
        for i in range(i_iface, N + 1):
            q_hermite[i] = q_at_gamma

        # Error in [0.52, 0.55] (fixed physical coordinates)
        mask = (x >= 0.52) & (x <= 0.55)
        if not np.any(mask):
            mask = (x >= 0.5 + h) & (x <= 0.5 + 3 * h)  # fallback
        err_upwind = float(np.max(np.abs(q_upwind[mask] - q_exact)))
        err_hermite = float(np.max(np.abs(q_hermite[mask] - q_exact)))

        results_upwind.append(err_upwind)
        results_hermite.append(err_hermite)

    # Print table
    print(f"\n{'N':>6s}  {'Upwind L∞':>12s}  {'order':>6s}  {'Hermite L∞':>12s}  {'order':>6s}")
    print("-" * 55)
    for k, N in enumerate(grid_sizes):
        o_u = f"{np.log2(results_upwind[k-1]/results_upwind[k]):.1f}" if k > 0 and results_upwind[k] > 0 else "---"
        o_h = f"{np.log2(results_hermite[k-1]/results_hermite[k]):.1f}" if k > 0 and results_hermite[k] > 0 and results_hermite[k-1] > 0 else "---"
        print(f"{N:6d}  {results_upwind[k]:12.2e}  {o_u:>6s}  {results_hermite[k]:12.2e}  {o_h:>6s}")

    return grid_sizes, results_upwind, results_hermite


# ══════════════════════════════════════════════════════════════════════════
# Test (c): 2D field extension convergence
# ══════════════════════════════════════════════════════════════════════════

def test_c_2d_convergence():
    """2D convergence: circular interface, tensor-product Hermite.

    Setup:
      - φ = √((x-0.5)²+(y-0.5)²) - 0.25 (circle R=0.25)
      - source_sign = -1 (source = inside circle, φ < 0)
      - q = cos(πx)·cos(πy) (smooth)
      - Exact extension: q(x_Γ) where x_Γ = x - φ·n̂
      - Error in target narrow band: φ > 0, φ ≤ 3h
      - N = 32, 64, 128, 256
    """
    print("\n" + "=" * 70)
    print("Test (c): 2D HFE convergence (circular interface)")
    print("=" * 70)

    grid_sizes = [32, 64, 128, 256]
    errors = []

    cx, cy, R = 0.5, 0.5, 0.25

    for N in grid_sizes:
        backend = Backend(use_gpu=False)
        gc = _GridConfig(N=[N, N], L=[1.0, 1.0])
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        hfe = HermiteFieldExtension(grid, ccd, backend, band_cells=6)

        X, Y = grid.meshgrid()
        h = 1.0 / N

        phi = np.sqrt((X - cx)**2 + (Y - cy)**2) - R
        q = np.cos(np.pi * X) * np.cos(np.pi * Y)

        q_ext = hfe.extend(q, phi, source_sign=-1.0)

        # Exact extension: q at closest point
        r = np.sqrt((X - cx)**2 + (Y - cy)**2)
        r = np.maximum(r, 1e-14)
        x_g = X - phi * (X - cx) / r
        y_g = Y - phi * (Y - cy) / r
        q_ref = np.cos(np.pi * x_g) * np.cos(np.pi * y_g)

        # Error in target narrow band
        target_band = (phi > 0) & (phi <= 3.0 * h)
        if np.any(target_band):
            err = float(np.max(np.abs(q_ext[target_band] - q_ref[target_band])))
        else:
            err = 0.0
        errors.append(err)

    # Print table
    print(f"\n{'N':>6s}  {'L∞ error':>12s}  {'order':>6s}")
    print("-" * 30)
    for k, N in enumerate(grid_sizes):
        o = f"{np.log2(errors[k-1]/errors[k]):.2f}" if k > 0 and errors[k] > 0 else "---"
        print(f"{N:6d}  {errors[k]:12.2e}  {o:>6s}")

    return grid_sizes, errors


# ══════════════════════════════════════════════════════════════════════════
# Output and figure generation
# ══════════════════════════════════════════════════════════════════════════

def save_results(grid_sizes, res_1d_up, res_1d_herm, res_2d):
    """Save results to text files."""
    outdir = pathlib.Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)

    # 1D
    with open(outdir / "hfe_1d_convergence.txt", "w") as f:
        f.write("# 1D field extension convergence: upwind vs Hermite\n")
        f.write("# N  upwind_Linf  hermite_Linf\n")
        for k, N in enumerate(grid_sizes):
            f.write(f"{N}  {res_1d_up[k]:.6e}  {res_1d_herm[k]:.6e}\n")

    # 2D
    with open(outdir / "hfe_2d_convergence.txt", "w") as f:
        f.write("# 2D HFE convergence (circular interface)\n")
        f.write("# N  Linf_error\n")
        for k, N in enumerate(grid_sizes):
            f.write(f"{N}  {res_2d[k]:.6e}\n")

    print(f"\nResults saved to {outdir}/")


def generate_figure(grid_sizes, res_1d_up, res_1d_herm, res_2d):
    """Generate convergence plot."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available; skipping figure generation")
        return

    figdir = pathlib.Path(__file__).resolve().parent / "figures"
    figdir.mkdir(exist_ok=True)

    h_vals = [1.0 / N for N in grid_sizes]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # (a) 1D
    ax1.loglog(h_vals, res_1d_up, "rs-", label="Upwind (Aslam 2004)", markersize=7)
    valid = [e for e in res_1d_herm if e > 0]
    h_valid = h_vals[:len(valid)]
    ax1.loglog(h_valid, valid, "bo-", label="HFE (Hermite)", markersize=7)
    # Reference slopes
    h_ref = np.array([h_vals[0], h_vals[-1]])
    ax1.loglog(h_ref, 0.5 * h_ref, "r--", alpha=0.4, label="$O(h^1)$")
    if len(valid) >= 2:
        ax1.loglog(h_ref, valid[0] * (h_ref / h_valid[0])**6, "b--", alpha=0.4, label="$O(h^6)$")
    ax1.set_xlabel("$h$")
    ax1.set_ylabel("$L^\\infty$ error")
    ax1.set_title("(a) 1D field extension")
    ax1.legend(fontsize=9)
    ax1.grid(True, which="both", alpha=0.3)

    # (c) 2D
    ax2.loglog(h_vals, res_2d, "go-", label="HFE 2D (tensor-product)", markersize=7)
    ax2.loglog(h_ref, res_2d[0] * (h_ref / h_vals[0])**3, "g--", alpha=0.4, label="$O(h^3)$")
    ax2.set_xlabel("$h$")
    ax2.set_ylabel("$L^\\infty$ error")
    ax2.set_title("(c) 2D circular interface extension")
    ax2.legend(fontsize=9)
    ax2.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    outpath = figdir / "hfe_convergence.pdf"
    fig.savefig(outpath, dpi=150)
    print(f"Figure saved to {outpath}")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    Ns, up, herm = test_a_1d_convergence()
    _, errs_2d = test_c_2d_convergence()
    save_results(Ns, up, herm, errs_2d)
    generate_figure(Ns, up, herm, errs_2d)
