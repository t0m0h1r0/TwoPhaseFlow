#!/usr/bin/env python3
"""[12-17] Static droplet — uniform vs non-uniform grid comparison.

Paper ref: §12 (system-level non-uniform grid validation)

Compares the TwoPhaseNSSolver pipeline on uniform (α=1) and interface-fitted
(α=2) grids across multiple resolutions.  Measures:
  (a) Parasitic current peak magnitude
  (b) Laplace pressure relative error
  (c) Mass conservation
  (d) h_min adaptation

Setup
-----
  Static droplet: R=0.25, center (0.5, 0.5), wall BC, gravity=0
  rho_l/rho_g = 10, sigma = 1.0, mu = 0.05
  200 steps per grid, dt = 0.25 * h_min
  Grid: N = 32, 48, 64

Output
------
  experiment/ch12/results/17_static_droplet_nonuniform/
    comparison.pdf           — 4-panel diagnostic comparison
    data.npz                 — raw data

Usage
-----
  python experiment/ch12/exp12_17_static_droplet_nonuniform.py
  python experiment/ch12/exp12_17_static_droplet_nonuniform.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.ns_pipeline import TwoPhaseNSSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)

apply_style()
OUT = experiment_dir(__file__)

# ── Parameters ───────────────────────────────────────────────────────────────

RHO_L, RHO_G = 10.0, 1.0
SIGMA = 1.0
MU = 0.05
R = 0.25
N_STEPS = 200
GRIDS = [32, 48, 64]


def run_case(N: int, alpha_grid: float) -> dict:
    """Run static droplet simulation, return diagnostics."""
    solver = TwoPhaseNSSolver(
        N, N, 1.0, 1.0,
        bc_type="wall",
        alpha_grid=alpha_grid,
    )
    X, Y = solver.X, solver.Y
    dist = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = solver.psi_from_phi(R - dist)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    # Initial grid fit for non-uniform
    if alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v)

    dV0 = solver._grid.cell_volumes()
    M0 = float(np.sum(psi * dV0))

    h_uniform = 1.0 / N
    from twophase.config_io import PhysicsCfg
    ph = PhysicsCfg(rho_l=RHO_L, rho_g=RHO_G, sigma=SIGMA, mu=MU)
    dt = solver.dt_max(u, u, ph, cfl=0.10)

    mass_err_hist = []
    u_max_hist = []
    h_min_hist = []

    for step in range(N_STEPS):
        psi, u, v, p = solver.step(
            psi, u, v, dt,
            rho_l=RHO_L, rho_g=RHO_G, sigma=SIGMA, mu=MU,
            step_index=step,
        )
        dV = solver._grid.cell_volumes()
        M = float(np.sum(psi * dV))
        vel_max = float(np.max(np.sqrt(u ** 2 + v ** 2)))

        mass_err_hist.append(abs(M - M0) / max(abs(M0), 1e-30))
        u_max_hist.append(vel_max)
        h_min_hist.append(solver.h_min)

        if step % 50 == 0:
            print(f"    [N={N},α={alpha_grid}] step={step+1:4d}  "
                  f"mass={mass_err_hist[-1]:.2e}  max|u|={vel_max:.2e}  "
                  f"h_min={solver.h_min:.4f}")

        if np.isnan(vel_max) or vel_max > 1e6:
            print(f"    [N={N},α={alpha_grid}] BLOWUP at step {step+1}")
            break

    # Laplace pressure
    X_f, Y_f = solver.X, solver.Y
    dist_f = np.sqrt((X_f - 0.5) ** 2 + (Y_f - 0.5) ** 2)
    inside = dist_f < R * 0.7
    outside = dist_f > R * 1.5
    if np.any(inside) and np.any(outside):
        dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    else:
        dp_meas = float("nan")
    dp_exact = SIGMA / R
    dp_err = abs(dp_meas - dp_exact) / dp_exact if dp_exact > 0 else 0.0

    return {
        "N": N, "alpha": alpha_grid, "h_uniform": h_uniform,
        "mass_err": np.array(mass_err_hist),
        "u_max": np.array(u_max_hist),
        "h_min": np.array(h_min_hist),
        "dp_meas": dp_meas, "dp_exact": dp_exact, "dp_err": dp_err,
        "u_max_peak": max(u_max_hist),
        "final_mass_err": mass_err_hist[-1],
        "final_h_min": h_min_hist[-1],
    }


def plot_all(results_uni, results_nu):
    """4-panel comparison: parasitic, Laplace, mass, h_min."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    # (a) Parasitic current convergence
    ax = axes[0, 0]
    Ns_u = [r["N"] for r in results_uni]
    hs_u = [1.0 / N for N in Ns_u]
    peaks_u = [r["u_max_peak"] for r in results_uni]
    peaks_n = [r["u_max_peak"] for r in results_nu]
    ax.loglog(hs_u, peaks_u, "o-", color="C0", label=r"$\alpha=1$")
    ax.loglog(hs_u, peaks_n, "s-", color="C1", label=r"$\alpha=2$")
    h_ref = np.array(hs_u)
    ax.loglog(h_ref, peaks_u[0] * (h_ref / hs_u[0]) ** 1,
              "k--", alpha=0.4, label=r"$O(h)$")
    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$\max|\mathbf{u}|$")
    ax.set_title("(a) Parasitic current convergence")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    # (b) Laplace pressure error
    ax = axes[0, 1]
    dp_u = [r["dp_err"] for r in results_uni]
    dp_n = [r["dp_err"] for r in results_nu]
    ax.loglog(hs_u, dp_u, "o-", color="C0", label=r"$\alpha=1$")
    ax.loglog(hs_u, dp_n, "s-", color="C1", label=r"$\alpha=2$")
    ax.loglog(h_ref, dp_u[0] * (h_ref / hs_u[0]) ** 1,
              "k--", alpha=0.4, label=r"$O(h)$")
    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$|\Delta p - \sigma/R|/(\sigma/R)$")
    ax.set_title("(b) Laplace pressure error")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    # (c) Mass conservation (time history, N=64)
    ax = axes[1, 0]
    for rlist, c, lbl in [(results_uni, "C0", r"$\alpha=1$"),
                           (results_nu, "C1", r"$\alpha=2$")]:
        r64 = [r for r in rlist if r["N"] == 64]
        if r64:
            r = r64[0]
            steps = np.arange(1, len(r["mass_err"]) + 1)
            ax.semilogy(steps, r["mass_err"], color=c, label=lbl)
    ax.set_xlabel("Step")
    ax.set_ylabel(r"$|\Delta M|/M_0$")
    ax.set_title("(c) Mass conservation ($N=64$)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (d) h_min history (N=64)
    ax = axes[1, 1]
    for rlist, c, lbl in [(results_uni, "C0", r"$\alpha=1$"),
                           (results_nu, "C1", r"$\alpha=2$")]:
        r64 = [r for r in rlist if r["N"] == 64]
        if r64:
            r = r64[0]
            steps = np.arange(1, len(r["h_min"]) + 1)
            ax.plot(steps, r["h_min"], color=c, label=lbl)
    ax.axhline(1.0 / 64, ls="--", color="gray", lw=1, label="$h_{\\rm uniform}$")
    ax.set_xlabel("Step")
    ax.set_ylabel("$h_{\\min}$")
    ax.set_title("(d) Grid adaptation ($N=64$)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "comparison")


def main():
    args = experiment_argparser("[12-17] Static droplet non-uniform").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["uniform"], d["nonuniform"])
        return

    print("=" * 70)
    print("  [12-17] Static droplet: uniform vs non-uniform grid")
    print("=" * 70)

    results_uni = []
    results_nu = []

    for N in GRIDS:
        print(f"\n--- N={N}, uniform (α=1) ---")
        results_uni.append(run_case(N, alpha_grid=1.0))

        print(f"\n--- N={N}, non-uniform (α=2) ---")
        results_nu.append(run_case(N, alpha_grid=2.0))

    # Summary table
    print("\n" + "=" * 80)
    print(f"{'N':>5} {'alpha':>6} {'max|u|':>12} {'dp_err':>12} "
          f"{'mass_err':>12} {'h_min':>10}")
    print("-" * 80)
    for ru, rn in zip(results_uni, results_nu):
        for r in [ru, rn]:
            print(f"{r['N']:>5} {r['alpha']:>6.1f} "
                  f"{r['u_max_peak']:>12.2e} {r['dp_err']:>12.2e} "
                  f"{r['final_mass_err']:>12.2e} {r['final_h_min']:>10.4f}")
    print("=" * 80)

    save_results(OUT / "data.npz", {
        "uniform": results_uni, "nonuniform": results_nu,
    })
    plot_all(results_uni, results_nu)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
