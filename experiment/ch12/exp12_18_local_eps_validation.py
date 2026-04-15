#!/usr/bin/env python3
"""[12-18] Local epsilon validation: fixed ε vs ε(x) = C_ε · h_local(x).

Paper ref: §12 (WIKI-T-032 verification)

Validates the spatially varying epsilon theory on static droplet.
Reinitialization is enabled on the uniform baseline and disabled on
non-uniform cases because the current split reinitializer is uniform-grid
calibrated and creates large non-uniform-grid mass drift.
Three configurations at N=32, 48, 64:
  A: uniform grid (α=1), scalar ε = 1.5·h        (baseline)
  B: non-uniform (α=2), scalar ε = 1.5·h_uniform  (fixed-ε mismatch)
  C: non-uniform (α=2), ε(x) = 1.5·h_local(x)   (local-ε fix)

Expected (from WIKI-T-032):
  - C improves Laplace pressure over B (ε/h_local restored to ~C_ε)
  - C maintains mass conservation advantage of B
  - C reduces parasitic currents vs B

Output
------
  experiment/ch12/results/18_local_eps_validation/
    local_eps.pdf    — 4-panel comparison A/B/C
    data.npz

Usage
-----
  python experiment/ch12/exp12_18_local_eps_validation.py
  python experiment/ch12/exp12_18_local_eps_validation.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.tools.experiment import (
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


def run_case(N: int, alpha_grid: float, use_local_eps: bool, label: str) -> dict:
    solver = TwoPhaseNSSolver(
        N, N, 1.0, 1.0, bc_type="wall",
        alpha_grid=alpha_grid, use_local_eps=use_local_eps,
        reinit_every=2 if alpha_grid <= 1.0 else 0,
    )
    X, Y = solver.X, solver.Y
    dist = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = solver.psi_from_phi(R - dist)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    if alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v)

    dV0 = solver._grid.cell_volumes()
    M0 = float(np.sum(psi * dV0))

    from twophase.simulation.config_io import PhysicsCfg
    ph = PhysicsCfg(rho_l=RHO_L, rho_g=RHO_G, sigma=SIGMA, mu=MU)
    dt = solver.dt_max(u, u, ph, cfl=0.10)

    mass_err_hist = []
    u_max_hist = []

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

        if step % 50 == 0:
            print(f"    [{label},N={N}] step={step+1:4d}  "
                  f"mass={mass_err_hist[-1]:.2e}  max|u|={vel_max:.2e}")

        if np.isnan(vel_max) or vel_max > 1e6:
            print(f"    [{label},N={N}] BLOWUP at step {step+1}")
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
        "N": N, "alpha": alpha_grid, "local_eps": use_local_eps, "label": label,
        "reinit_every": 2 if alpha_grid <= 1.0 else 0,
        "mass_err": np.array(mass_err_hist),
        "u_max": np.array(u_max_hist),
        "dp_err": dp_err, "dp_meas": dp_meas,
        "u_max_peak": max(u_max_hist),
        "final_mass_err": mass_err_hist[-1],
    }


def plot_all(results_A, results_B, results_C):
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    Ns = [r["N"] for r in results_A]
    hs = [1.0 / N for N in Ns]

    # (a) Parasitic current convergence
    ax = axes[0, 0]
    for rlist, c, mk, lbl in [(results_A, "C0", "o", r"A: $\alpha{=}1$"),
                                (results_B, "C1", "s", r"B: $\alpha{=}2$, fixed $\varepsilon$"),
                                (results_C, "C2", "^", r"C: $\alpha{=}2$, local $\varepsilon$")]:
        peaks = [r["u_max_peak"] for r in rlist]
        ax.loglog(hs, peaks, f"{mk}-", color=c, label=lbl)
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$\max|\mathbf{u}|$")
    ax.set_title("(a) Parasitic currents"); ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    # (b) Laplace pressure error
    ax = axes[0, 1]
    for rlist, c, mk, lbl in [(results_A, "C0", "o", r"A: $\alpha{=}1$"),
                                (results_B, "C1", "s", r"B: $\alpha{=}2$, fixed $\varepsilon$"),
                                (results_C, "C2", "^", r"C: $\alpha{=}2$, local $\varepsilon$")]:
        dp = [r["dp_err"] for r in rlist]
        ax.loglog(hs, dp, f"{mk}-", color=c, label=lbl)
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$|\Delta p - \sigma/R|/(\sigma/R)$")
    ax.set_title("(b) Laplace pressure error"); ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    # (c) Mass conservation (N=64 time history)
    ax = axes[1, 0]
    for rlist, c, lbl in [(results_A, "C0", "A"),
                           (results_B, "C1", "B"),
                           (results_C, "C2", "C")]:
        r64 = [r for r in rlist if r["N"] == 64]
        if r64:
            steps = np.arange(1, len(r64[0]["mass_err"]) + 1)
            ax.semilogy(steps, r64[0]["mass_err"], color=c, label=lbl)
    ax.set_xlabel("Step"); ax.set_ylabel(r"$|\Delta M|/M_0$")
    ax.set_title("(c) Mass conservation ($N{=}64$)"); ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (d) Parasitic current time history (N=64)
    ax = axes[1, 1]
    for rlist, c, lbl in [(results_A, "C0", "A"),
                           (results_B, "C1", "B"),
                           (results_C, "C2", "C")]:
        r64 = [r for r in rlist if r["N"] == 64]
        if r64:
            steps = np.arange(1, len(r64[0]["u_max"]) + 1)
            ax.semilogy(steps, r64[0]["u_max"], color=c, label=lbl)
    ax.set_xlabel("Step"); ax.set_ylabel(r"$\max|\mathbf{u}|$")
    ax.set_title("(d) Parasitic current history ($N{=}64$)"); ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "local_eps")


def main():
    args = experiment_argparser("[12-18] Local eps validation").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["A"], d["B"], d["C"])
        return

    print("=" * 70)
    print("  [12-18] Local epsilon: fixed ε vs ε(x) = C_ε · h_local(x)")
    print("=" * 70)

    results_A, results_B, results_C = [], [], []

    for N in GRIDS:
        print(f"\n--- N={N} ---")
        results_A.append(run_case(N, alpha_grid=1.0, use_local_eps=False, label="A"))
        results_B.append(run_case(N, alpha_grid=2.0, use_local_eps=False, label="B"))
        results_C.append(run_case(N, alpha_grid=2.0, use_local_eps=True,  label="C"))

    # Summary
    print("\n" + "=" * 85)
    print(f"{'Case':>5} {'N':>4} {'alpha':>6} {'local_eps':>10} "
          f"{'max|u|':>12} {'dp_err':>12} {'mass_err':>12}")
    print("-" * 85)
    for rA, rB, rC in zip(results_A, results_B, results_C):
        for r in [rA, rB, rC]:
            print(f"{r['label']:>5} {r['N']:>4} {r['alpha']:>6.1f} "
                  f"{'yes' if r['local_eps'] else 'no':>10} "
                  f"{r['u_max_peak']:>12.2e} {r['dp_err']:>12.2e} "
                  f"{r['final_mass_err']:>12.2e}")
    print("=" * 85)

    save_results(OUT / "data.npz", {
        "A": results_A, "B": results_B, "C": results_C,
    })
    plot_all(results_A, results_B, results_C)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
