#!/usr/bin/env python3
"""[11-14] TVD-RK3 time integration accuracy.

Validates: Ch6 -- TVD-RK3 (Shu-Osher SSP 3-stage).

Tests:
  (a) ODE: dq/dt = -q, q(0)=1, exact q(T=1)=e^{-1}
  (b) Temporal convergence: scalar advection on fixed N=256 grid
  (c) Space-time coupled convergence: CFL=0.3

Expected: O(dt^3) temporal accuracy.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.time_integration.tvd_rk3 import tvd_rk3
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__)


def ode_test():
    backend = Backend(); xp = backend.xp; T = 1.0
    n_list = [4, 8, 16, 32, 64, 128, 256, 512]
    results = []
    for n in n_list:
        dt = T / n; q = xp.array([[1.0]])
        for _ in range(n):
            q = tvd_rk3(xp, q, dt, lambda q: -q)
        err = float(abs(q[0, 0] - np.exp(-T)))
        results.append({"n": n, "dt": dt, "err": err})
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r0["err"] > 1e-15 and r1["err"] > 1e-15:
            r1["slope"] = np.log(r1["err"]/r0["err"]) / np.log(r1["dt"]/r0["dt"])
    return results


def temporal_convergence(N=256):
    backend = Backend(); xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend); ccd = CCDSolver(grid, backend, bc_type="periodic")
    X, Y = grid.meshgrid(); k = 2*np.pi; q0 = xp.sin(k*X)
    rhs_fn = lambda q: -1.0 * ccd.differentiate(q, 0)[0]
    T = 1.0; n_list = [10, 20, 40, 80, 160, 320, 640]
    results = []
    for n in n_list:
        dt = T / n; q = q0.copy()
        for _ in range(n):
            q = tvd_rk3(xp, q, dt, rhs_fn)
        err = float(xp.sqrt(xp.mean((q - q0)**2)))
        results.append({"n": n, "dt": dt, "L2": err})
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r0["L2"] > 1e-15 and r1["L2"] > 1e-15:
            r1["L2_slope"] = np.log(r1["L2"]/r0["L2"]) / np.log(r1["dt"]/r0["dt"])
    return results


def plot_all(ode, temporal):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    ax = axes[0]
    dt = [r["dt"] for r in ode]
    ax.loglog(dt, [r["err"] for r in ode], "o-", label="TVD-RK3")
    d_ref = np.array([dt[0], dt[-1]])
    ax.loglog(d_ref, ode[0]["err"]*(d_ref/d_ref[0])**3, "--", color="gray", alpha=0.5, label="$O(\\Delta t^3)$")
    ax.set_xlabel(r"$\Delta t$"); ax.set_ylabel(r"$|q-e^{-1}|$")
    ax.set_title("(a) ODE: $dq/dt=-q$"); ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    ax = axes[1]
    dt = [r["dt"] for r in temporal]
    ax.loglog(dt, [r["L2"] for r in temporal], "o-", label=r"$L_2$")
    d_ref = np.array([dt[0], dt[-1]])
    for order in [2, 3]:
        ax.loglog(d_ref, temporal[0]["L2"]*(d_ref/d_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(\\Delta t^{order})$")
    ax.set_xlabel(r"$\Delta t$"); ax.set_ylabel("Error")
    ax.set_title("(b) Advection ($N=256$)"); ax.legend(fontsize=8); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "tvd_rk3")


def main():
    args = experiment_argparser("[11-14] TVD-RK3").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["ode"], d["temporal"])
        return

    print("\n--- (a) ODE ---")
    ode = ode_test()
    for r in ode:
        s = r.get("slope", float("nan"))
        print(f"  n={r['n']:>4}: err={r['err']:.3e}, slope={s:.2f}")

    print("\n--- (b) Temporal convergence ---")
    temporal = temporal_convergence()
    for r in temporal:
        s = r.get("L2_slope", float("nan"))
        print(f"  n={r['n']:>4}: L2={r['L2']:.3e}, slope={s:.2f}")

    save_results(OUT / "data.npz", {"ode": ode, "temporal": temporal})
    plot_all(ode, temporal)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
