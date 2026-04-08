#!/usr/bin/env python3
"""[12-02] Laplace pressure / balanced-force verification.

Validates: CSF surface-tension model with balanced-force projection.

Setup
-----
  Domain [0,1]², wall BC, R=0.25, center (0.5, 0.5)
  ρ_l = 1000, ρ_g = 1,  σ = 1.0,  We = 1
  Single-step non-incremental projection with CSF body force
  Grid: N = 32, 64, 128, 256

Expected
--------
  - Δp ≈ σ / (R * We) = 4.0  (Laplace jump)
  - Parasitic current ||u_para||_∞ → 0 with refinement
  - Δp relative error converges

Output
------
  - Pressure jump Δp and relative error vs N
  - Parasitic current ||u||_∞ vs N
  - Figure: convergence + pressure cross-section
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure, COLORS,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# -- Physical parameters -------------------------------------------------------
RHO_L = 1000.0
RHO_G = 1.0
SIGMA = 1.0
WE = 1.0
R = 0.25
DP_EXACT = SIGMA / (R * WE)   # = 4.0


# -- PPE solver ----------------------------------------------------------------

def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


# -- Single-grid run -----------------------------------------------------------

def run(N):
    """Single-step balanced-force projection on N×N grid."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()

    # Level-set and Heaviside
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    # Curvature and CSF force
    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    # Single-step predictor (zero initial velocity)
    u_star = dt / rho * f_csf_x
    v_star = dt / rho * f_csf_y
    wall_bc(u_star); wall_bc(v_star)

    # PPE
    du_dx, _ = ccd.differentiate(u_star, 0)
    dv_dy, _ = ccd.differentiate(v_star, 1)
    rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
    p = _solve_ppe(rhs, rho, ppe_builder)

    # Corrector
    dp_dx, _ = ccd.differentiate(p, 0)
    dp_dy, _ = ccd.differentiate(p, 1)
    u = u_star - dt / rho * np.asarray(dp_dx)
    v = v_star - dt / rho * np.asarray(dp_dy)
    wall_bc(u); wall_bc(v)

    # Diagnostics: Laplace pressure jump
    inside = phi > 3 * h
    outside = phi < -3 * h
    if np.any(inside) and np.any(outside):
        dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    else:
        dp_meas = float("nan")
    dp_rel_err = abs(dp_meas - DP_EXACT) / DP_EXACT

    # Parasitic current
    vel_mag = np.sqrt(u**2 + v**2)
    u_para_inf = float(np.max(vel_mag))

    # Pressure cross-section at y = 0.5
    mid = N // 2
    p_cross = np.asarray(p[:, mid]).copy()
    x_cross = np.asarray(X[:, mid]).copy()

    return {
        "N": N, "h": h,
        "dp_meas": dp_meas, "dp_exact": DP_EXACT,
        "dp_rel_err": dp_rel_err,
        "u_para_inf": u_para_inf,
        "p_cross": p_cross,
        "x_cross": x_cross,
    }


# -- Plotting ------------------------------------------------------------------

def make_figures(results):
    Ns = [r["N"] for r in results]
    hs = [r["h"] for r in results]
    dp_errs = [r["dp_rel_err"] for r in results]
    u_paras = [r["u_para_inf"] for r in results]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # (a) Parasitic current vs h
    ax = axes[0]
    ax.loglog(hs, u_paras, "o-", color=COLORS[0], linewidth=1.5, markersize=7,
              label=r"$\|\mathbf{u}_{\mathrm{para}}\|_\infty$")
    h_ref = np.array(hs)
    ax.loglog(h_ref, u_paras[0] * (h_ref / hs[0])**1, "k--", alpha=0.5,
              label=r"$O(h^1)$")
    ax.loglog(h_ref, u_paras[0] * (h_ref / hs[0])**2, "k:", alpha=0.5,
              label=r"$O(h^2)$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$\|\mathbf{u}_{\mathrm{para}}\|_\infty$")
    ax.set_title("(a) Parasitic current"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    # (b) Laplace pressure error vs h
    ax = axes[1]
    ax.loglog(hs, dp_errs, "s-", color=COLORS[1], linewidth=1.5, markersize=7,
              label=r"$|\Delta p - \sigma/R|/(\sigma/R)$")
    ax.loglog(h_ref, dp_errs[0] * (h_ref / hs[0])**1, "k--", alpha=0.5,
              label=r"$O(h^1)$")
    ax.loglog(h_ref, dp_errs[0] * (h_ref / hs[0])**2, "k:", alpha=0.5,
              label=r"$O(h^2)$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$\Delta p$ relative error")
    ax.set_title("(b) Laplace pressure error"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    # (c) Pressure cross-section at y = 0.5
    ax = axes[2]
    for i, r in enumerate(results):
        ax.plot(r["x_cross"], r["p_cross"], "-",
                color=COLORS[i % len(COLORS)], linewidth=1.2,
                label=f"N={r['N']}")
    ax.axhline(DP_EXACT, color="k", linestyle="--", linewidth=1, alpha=0.6,
               label=rf"$\sigma/(RWe)={DP_EXACT:.1f}$")
    ax.axvline(0.5 - R, color="gray", linestyle=":", alpha=0.4)
    ax.axvline(0.5 + R, color="gray", linestyle=":", alpha=0.4)
    ax.set_xlabel("$x$"); ax.set_ylabel("$p$")
    ax.set_title("(c) Pressure cross-section ($y=0.5$)"); ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "laplace_bf")


# -- Table ---------------------------------------------------------------------

def print_table(results):
    print(f"\n{'='*72}")
    print("  [12-02] Laplace Pressure / Balanced-Force Verification")
    print(f"{'='*72}")
    print(f"  {'N':>5} | {'h':>10} | {'Δp_meas':>10} | {'Δp_err%':>10} | "
          f"{'||u_para||':>12}")
    print("  " + "-" * 58)
    for r in results:
        print(f"  {r['N']:>5} | {r['h']:>10.5f} | {r['dp_meas']:>10.4f} | "
              f"{r['dp_rel_err']:>9.2%} | {r['u_para_inf']:>12.4e}")

    print(f"\n  Exact Δp = σ/(R·We) = {DP_EXACT:.4f}")
    print("\n  Convergence rates:")
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        log_h = np.log(r0["h"] / r1["h"])
        rate_dp = np.log(r0["dp_rel_err"] / r1["dp_rel_err"]) / log_h if r1["dp_rel_err"] > 0 else float("nan")
        rate_u = np.log(r0["u_para_inf"] / r1["u_para_inf"]) / log_h if r1["u_para_inf"] > 0 else float("nan")
        print(f"    N={r0['N']:>3}->{r1['N']:>3}:  Δp rate={rate_dp:+.2f},  ||u|| rate={rate_u:+.2f}")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser("[12-02] Laplace BF").parse_args()

    if args.plot_only:
        data = load_results(NPZ)
        make_figures(data["results"])
        return

    Ns = [32, 64, 128, 256]
    results = []

    for N in Ns:
        print(f"  Running N={N} ...")
        r = run(N)
        results.append(r)

    print_table(results)

    # Save
    save_data = {
        "results": [{k: v for k, v in r.items()
                      if k not in ("p_cross", "x_cross")} for r in results],
    }
    for i, r in enumerate(results):
        save_data[f"p_cross_{i}"] = r["p_cross"]
        save_data[f"x_cross_{i}"] = r["x_cross"]
    save_results(NPZ, save_data)

    make_figures(results)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
