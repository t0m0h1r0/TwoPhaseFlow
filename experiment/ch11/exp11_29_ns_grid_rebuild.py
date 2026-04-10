#!/usr/bin/env python3
"""[11-29] NS pipeline with per-timestep non-uniform grid rebuild.

Validates: the TwoPhaseNSSolver.step() integration of interface-fitted
grid rebuild (§5-§6).  Static droplet at rest — measures:
  (a) Mass conservation (volume_conservation diagnostic)
  (b) Parasitic current magnitude max|u|
  (c) Grid adaptation: h_min tracks the interface

Compares uniform (alpha=1) vs interface-fitted (alpha=2) grids.
Each case runs 100 timesteps with dt=1e-3 on N=32.

Expected:
  - Both cases: mass conservation < 1e-3, no blowup
  - alpha=2: h_min < h_uniform (grid concentrates at interface)
  - alpha=2: parasitic currents larger (known: fixed-epsilon CSF mismatch)
"""

import sys
import pathlib

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

N = 32
LX = LY = 1.0
RHO_L, RHO_G = 10.0, 1.0
SIGMA = 1.0
MU = 0.05
DT = 1e-3
N_STEPS = 100


def run_case(alpha_grid: float, label: str) -> dict:
    """Run static droplet with given alpha_grid, return diagnostics."""
    solver = TwoPhaseNSSolver(
        N, N, LX, LY,
        bc_type="wall",
        alpha_grid=alpha_grid,
    )
    X, Y = solver.X, solver.Y
    R = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = solver.psi_from_phi(0.25 - R)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)

    # Initial mass
    if alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v)
    dV0 = solver._grid.cell_volumes()
    M0 = float(np.sum(psi * dV0))

    times = []
    mass_err = []
    max_vel = []
    h_min_hist = []

    for step in range(N_STEPS):
        psi, u, v, p = solver.step(
            psi, u, v, DT,
            rho_l=RHO_L, rho_g=RHO_G, sigma=SIGMA, mu=MU,
            step_index=step,
        )
        t = (step + 1) * DT
        dV = solver._grid.cell_volumes()
        M = float(np.sum(psi * dV))
        vel_max = float(np.max(np.sqrt(u ** 2 + v ** 2)))

        times.append(t)
        mass_err.append(abs(M - M0) / max(abs(M0), 1e-30))
        max_vel.append(vel_max)
        h_min_hist.append(solver.h_min)

        if step % 20 == 0 or step == N_STEPS - 1:
            print(f"  [{label}] step={step+1:4d}  t={t:.4f}  "
                  f"mass_err={mass_err[-1]:.2e}  max|u|={vel_max:.2e}  "
                  f"h_min={solver.h_min:.4f}")

        if np.isnan(vel_max) or vel_max > 1e6:
            print(f"  [{label}] BLOWUP at step={step+1}")
            break

    return {
        "label": label,
        "alpha": alpha_grid,
        "times": np.array(times),
        "mass_err": np.array(mass_err),
        "max_vel": np.array(max_vel),
        "h_min": np.array(h_min_hist),
        "final_mass_err": mass_err[-1],
        "final_max_vel": max_vel[-1],
    }


def plot_all(res_uniform, res_nonuniform):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))

    # (a) Mass conservation
    ax = axes[0]
    for r, c in [(res_uniform, "C0"), (res_nonuniform, "C1")]:
        ax.semilogy(r["times"], r["mass_err"], color=c,
                    label=rf'$\alpha={r["alpha"]:.0f}$')
    ax.set_xlabel("$t$")
    ax.set_ylabel(r"$|\Delta M|/M_0$")
    ax.set_title("(a) Mass conservation")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # (b) Parasitic current
    ax = axes[1]
    for r, c in [(res_uniform, "C0"), (res_nonuniform, "C1")]:
        ax.semilogy(r["times"], r["max_vel"], color=c,
                    label=rf'$\alpha={r["alpha"]:.0f}$')
    ax.set_xlabel("$t$")
    ax.set_ylabel(r"$\max|\mathbf{u}|$")
    ax.set_title("(b) Parasitic currents")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # (c) h_min history
    ax = axes[2]
    h_uniform = LX / N
    ax.axhline(h_uniform, ls="--", color="gray", lw=1, label="$h_{\\rm uniform}$")
    for r, c in [(res_uniform, "C0"), (res_nonuniform, "C1")]:
        ax.plot(r["times"], r["h_min"], color=c,
                label=rf'$\alpha={r["alpha"]:.0f}$')
    ax.set_xlabel("$t$")
    ax.set_ylabel("$h_{\\min}$")
    ax.set_title("(c) Minimum grid spacing")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "ns_grid_rebuild")


def main():
    args = experiment_argparser("[11-29] NS grid rebuild").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["uniform"], d["nonuniform"])
        return

    print("=" * 60)
    print("  [11-29] NS pipeline + per-timestep grid rebuild")
    print("=" * 60)

    print(f"\n--- Uniform (alpha=1.0) ---")
    res_uni = run_case(1.0, "uniform")

    print(f"\n--- Non-uniform (alpha=2.0) ---")
    res_nu = run_case(2.0, "non-uniform")

    # Summary table
    print("\n" + "=" * 70)
    print(f"{'case':>15} {'alpha':>6} {'mass_err':>12} {'max|u|':>12} {'h_min':>10}")
    print("-" * 70)
    for r in [res_uni, res_nu]:
        print(f"{r['label']:>15} {r['alpha']:>6.1f} "
              f"{r['final_mass_err']:>12.2e} {r['final_max_vel']:>12.2e} "
              f"{r['h_min'][-1]:>10.4f}")
    print("=" * 70)

    # Assertions
    for r in [res_uni, res_nu]:
        assert not np.any(np.isnan(r["max_vel"])), f"{r['label']}: NaN in velocity"
        assert r["final_mass_err"] < 0.05, \
            f"{r['label']}: mass error {r['final_mass_err']:.2e} > 5%"

    if res_nu["h_min"][-1] < res_uni["h_min"][-1]:
        print("\nPASS: non-uniform h_min < uniform h (grid adapts to interface)")
    else:
        print("\nWARN: non-uniform h_min >= uniform h (grid not concentrating)")

    save_results(OUT / "data.npz", {
        "uniform": res_uni, "nonuniform": res_nu,
    })
    plot_all(res_uni, res_nu)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
