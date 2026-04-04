#!/usr/bin/env python3
"""【12-2】Static droplet grid convergence (parasitic current + Laplace pressure).

Paper ref: §12.2 (sec:val_static_drop)

Extends §11.4a (exp11_9) with finer grid sweep to measure convergence rates
of parasitic currents and Laplace pressure error.

Setup
-----
  Static droplet: R=0.25, center (0.5, 0.5), wall BC, gravity=0
  ρ_l/ρ_g = 2,  We = 10
  Non-incremental projection (200 steps per grid)
  Grid: N = 32, 48, 64, 96, 128

Output
------
  - Parasitic current ||u||_∞ vs N  (log-log, convergence rate)
  - Laplace pressure error vs N
  - Figure: convergence plot
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "static_droplet"
OUT.mkdir(parents=True, exist_ok=True)

RHO_L = 2.0
RHO_G = 1.0
WE = 10.0
R = 0.25
SIGMA = 1.0
N_STEPS = 200


def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run_convergence(N):
    """Run static droplet for N×N grid, return diagnostics."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    dp_exact = SIGMA / (R * WE)

    # Initial conditions
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    # Precompute CSF (static: doesn't change)
    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_history = []

    for step in range(N_STEPS):
        # Predictor (non-incremental: no −∇p^n)
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
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

        vel_mag = np.sqrt(u**2 + v**2)
        u_max_history.append(float(np.max(vel_mag)))

        if np.isnan(u_max_history[-1]) or u_max_history[-1] > 1e6:
            print(f"    [N={N}] BLOWUP at step {step+1}")
            break

    # Laplace pressure
    inside  = phi >  3 * h
    outside = phi < -3 * h
    if np.any(inside) and np.any(outside):
        dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    else:
        dp_meas = float('nan')
    dp_err = abs(dp_meas - dp_exact) / dp_exact

    u_max_peak = max(u_max_history)
    u_max_final = u_max_history[-1]

    return {
        "N": N, "h": h,
        "u_max_peak": u_max_peak,
        "u_max_final": u_max_final,
        "dp_meas": dp_meas, "dp_exact": dp_exact,
        "dp_rel_err": dp_err,
        "u_max_history": np.array(u_max_history),
        "n_steps": len(u_max_history),
    }


def make_figures(results):
    """Generate convergence plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Ns = [r["N"] for r in results]
    hs = [r["h"] for r in results]
    u_peaks = [r["u_max_peak"] for r in results]
    dp_errs = [r["dp_rel_err"] for r in results]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # ── Left: Parasitic current vs h ──
    ax = axes[0]
    ax.loglog(hs, u_peaks, 'bo-', linewidth=1.5, markersize=8,
              label="$\\|\\mathbf{u}_{\\mathrm{para}}\\|_\\infty$")
    # Reference slopes
    h_ref = np.array(hs)
    ax.loglog(h_ref, u_peaks[0] * (h_ref / hs[0])**1, 'k--', alpha=0.5,
              label="$O(h^1)$")
    ax.loglog(h_ref, u_peaks[0] * (h_ref / hs[0])**2, 'k:', alpha=0.5,
              label="$O(h^2)$")
    ax.set_xlabel("Grid spacing $h$", fontsize=12)
    ax.set_ylabel("$\\|\\mathbf{u}_{\\mathrm{para}}\\|_\\infty$", fontsize=12)
    ax.set_title("Parasitic Current Convergence", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    # ── Right: Laplace pressure error vs h ──
    ax = axes[1]
    ax.loglog(hs, dp_errs, 'rs-', linewidth=1.5, markersize=8,
              label="$|\\Delta p - \\sigma/R| / (\\sigma/R)$")
    ax.loglog(h_ref, dp_errs[0] * (h_ref / hs[0])**1, 'k--', alpha=0.5,
              label="$O(h^1)$")
    ax.loglog(h_ref, dp_errs[0] * (h_ref / hs[0])**2, 'k:', alpha=0.5,
              label="$O(h^2)$")
    ax.set_xlabel("Grid spacing $h$", fontsize=12)
    ax.set_ylabel("$\\Delta p$ relative error", fontsize=12)
    ax.set_title("Laplace Pressure Convergence", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    plt.tight_layout()
    fig.savefig(OUT / "static_droplet_convergence.eps", dpi=150,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure saved: {OUT / 'static_droplet_convergence.eps'}")

    # ── Time history of parasitic current for each N ──
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    for r in results:
        ax2.semilogy(np.arange(1, r["n_steps"] + 1), r["u_max_history"],
                      linewidth=1.2, label=f"$N={r['N']}$")
    ax2.set_xlabel("Time step", fontsize=12)
    ax2.set_ylabel("$\\|\\mathbf{u}_{\\mathrm{para}}\\|_\\infty$", fontsize=12)
    ax2.set_title("Parasitic Current Time History", fontsize=13)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    fig2.savefig(OUT / "parasitic_time_history.eps", dpi=150,
                 bbox_inches="tight")
    plt.close(fig2)
    print(f"  Figure saved: {OUT / 'parasitic_time_history.eps'}")


def main():
    print("\n" + "=" * 80)
    print("  【12-2】Static Droplet Grid Convergence (§12.2)")
    print("=" * 80 + "\n")

    Ns = [32, 48, 64, 96, 128]
    results = []

    print(f"  {'N':>5} | {'h':>10} | {'||u||∞_peak':>12} | "
          f"{'Δp_err':>10} | {'steps':>6}")
    print("  " + "-" * 60)

    for N in Ns:
        r = run_convergence(N)
        results.append(r)
        print(f"  {N:>5} | {r['h']:>10.5f} | {r['u_max_peak']:>12.4e} | "
              f"{r['dp_rel_err']:>9.2%} | {r['n_steps']:>6}")

    # Compute convergence rates
    print("\n  Convergence rates (successive pairs):")
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r1["u_max_peak"] > 0 and r0["u_max_peak"] > 0:
            rate_u = np.log(r0["u_max_peak"] / r1["u_max_peak"]) / np.log(r0["h"] / r1["h"])
        else:
            rate_u = float('nan')
        if r1["dp_rel_err"] > 0 and r0["dp_rel_err"] > 0:
            rate_dp = np.log(r0["dp_rel_err"] / r1["dp_rel_err"]) / np.log(r0["h"] / r1["h"])
        else:
            rate_dp = float('nan')
        print(f"    N={r0['N']:>3}→{r1['N']:>3}: "
              f"||u||∞ rate={rate_u:+.2f},  Δp rate={rate_dp:+.2f}")

    make_figures(results)

    # Save LaTeX table
    with open(OUT / "table_convergence.tex", "w") as fp:
        fp.write("% Auto-generated by exp12_2_static_droplet_convergence.py\n")
        fp.write("\\begin{tabular}{rcccc}\n\\toprule\n")
        fp.write("$N$ & $h$ & $\\|\\bu_{\\mathrm{para}}\\|_\\infty$ & "
                 "$\\Delta p$ 相対誤差 & 収束次数 \\\\\n")
        fp.write("\\midrule\n")
        for i, r in enumerate(results):
            if i > 0:
                r0 = results[i-1]
                rate = np.log(r0["dp_rel_err"] / r["dp_rel_err"]) / np.log(r0["h"] / r["h"])
                rate_str = f"${rate:.2f}$"
            else:
                rate_str = "---"
            fp.write(f"{r['N']} & ${r['h']:.4f}$ & "
                     f"${r['u_max_peak']:.2e}$ & "
                     f"${r['dp_rel_err']:.2e}$ & {rate_str} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")

    np.savez(OUT / "convergence_data.npz",
             results=[{k: v for k, v in r.items() if k != "u_max_history"}
                      for r in results],
             **{f"u_max_hist_{i}": np.array(r["u_max_history"]) for i, r in enumerate(results)})
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "convergence_data.npz", allow_pickle=True)
        _results = [dict(r.item()) if hasattr(r, 'item') else dict(r) for r in _d["results"]]
        for _i, _r in enumerate(_results):
            _r["u_max_history"] = list(_d[f"u_max_hist_{_i}"])
        make_figures(_results)
    else:
        main()
