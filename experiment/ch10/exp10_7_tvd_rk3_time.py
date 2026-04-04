#!/usr/bin/env python3
"""【10-7】TVD-RK3 time integration accuracy.

Tests:
(a) Scalar advection: temporal convergence order with fixed spatial resolution
(b) Coupled space-time convergence for advection equation

Expected: O(Δt³) temporal accuracy for TVD-RK3.
Paper ref: §5b
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.time_integration.tvd_rk3 import tvd_rk3

OUT = pathlib.Path(__file__).resolve().parent / "results" / "tvd_rk3"
OUT.mkdir(parents=True, exist_ok=True)


def advection_rhs_factory(ccd, grid, c=1.0, axis=0):
    """Create RHS function for scalar advection: ∂q/∂t = -c ∂q/∂x."""
    def rhs_func(q):
        d1, _ = ccd.differentiate(q, axis=axis)
        return -c * d1
    return rhs_func


def temporal_convergence(N=256):
    """Fix spatial resolution (large N), vary Δt to isolate time error."""
    backend = Backend(use_gpu=False)
    xp = backend.xp

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X, Y = grid.meshgrid()
    k = 2 * np.pi
    c = 1.0

    # Initial condition: sin(2πx) (1D-like, uniform in y)
    q0 = np.sin(k * X)

    T = 1.0  # advect one period → exact solution = q0
    rhs_func = advection_rhs_factory(ccd, grid, c=c, axis=0)

    # Vary number of time steps (coarse to fine)
    n_steps_list = [10, 20, 40, 80, 160, 320, 640]
    results = []

    for n_steps in n_steps_list:
        dt = T / n_steps
        q = q0.copy()
        for _ in range(n_steps):
            q = tvd_rk3(xp, q, dt, rhs_func)

        # Exact solution after one period (periodic BC)
        q_exact = q0.copy()

        err_L2 = float(xp.sqrt(xp.mean((q - q_exact)**2)))
        err_Li = float(xp.max(xp.abs(q - q_exact)))

        results.append({"n_steps": n_steps, "dt": dt, "L2": err_L2, "Li": err_Li})

    # Slopes
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_dt = np.log(r1["dt"] / r0["dt"])
        for key in ["L2", "Li"]:
            if r0[key] > 1e-15 and r1[key] > 1e-15:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_dt
            else:
                r1[f"{key}_slope"] = float("nan")

    return results


def space_time_convergence():
    """Coupled space-time refinement: N and Δt refined together."""
    backend = Backend(use_gpu=False)
    xp = backend.xp

    Ns = [16, 32, 64, 128, 256]
    c = 1.0
    T = 1.0
    cfl = 0.3  # dt = CFL * h / c
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")

        X, Y = grid.meshgrid()
        k = 2 * np.pi
        q0 = np.sin(k * X)

        h = 1.0 / N
        dt = cfl * h / c
        n_steps = int(np.ceil(T / dt))
        dt = T / n_steps  # exact period

        rhs_func = advection_rhs_factory(ccd, grid, c=c, axis=0)
        q = q0.copy()
        for _ in range(n_steps):
            q = tvd_rk3(xp, q, dt, rhs_func)

        q_exact = q0.copy()
        err_L2 = float(xp.sqrt(xp.mean((q - q_exact)**2)))
        err_Li = float(xp.max(xp.abs(q - q_exact)))

        results.append({"N": N, "h": h, "dt": dt, "n_steps": n_steps,
                         "L2": err_L2, "Li": err_Li})

    # Slopes (vs h, since dt ~ h)
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for key in ["L2", "Li"]:
            if r0[key] > 1e-15 and r1[key] > 1e-15:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results


def ode_verification():
    """Verify TVD-RK3 on a simple ODE: dq/dt = -q, q(0)=1, q(T)=e^{-T}."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    T = 1.0

    n_steps_list = [4, 8, 16, 32, 64, 128, 256, 512]
    results = []

    for n_steps in n_steps_list:
        dt = T / n_steps
        q = xp.array([[1.0]])  # scalar as 2D
        rhs = lambda q: -q
        for _ in range(n_steps):
            q = tvd_rk3(xp, q, dt, rhs)

        q_exact = np.exp(-T)
        err = float(abs(q[0, 0] - q_exact))
        results.append({"n_steps": n_steps, "dt": dt, "err": err})

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_dt = np.log(r1["dt"] / r0["dt"])
        if r0["err"] > 1e-15 and r1["err"] > 1e-15:
            r1["slope"] = np.log(r1["err"] / r0["err"]) / log_dt

    return results


def plot_results(time_res, spacetime_res, ode_res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    # (a) Pure temporal convergence
    ax = axes[0]
    dt = [r["dt"] for r in time_res]
    ax.loglog(dt, [r["L2"] for r in time_res], "o-", label=r"$L_2$")
    ax.loglog(dt, [r["Li"] for r in time_res], "s--", label=r"$L_\infty$")
    dt_ref = np.array([dt[0], dt[-1]])
    for order in [2, 3, 4]:
        e0 = time_res[0]["L2"]
        ax.loglog(dt_ref, e0*(dt_ref/dt_ref[0])**order, ":", color="gray", alpha=0.4,
                  label=f"$O(\\Delta t^{order})$")
    ax.set_xlabel("$\\Delta t$"); ax.set_ylabel("Error")
    ax.set_title(f"(a) Temporal convergence ($N=256$)")
    ax.legend(fontsize=6); ax.grid(True, which="both", alpha=0.3)

    # (b) Space-time convergence
    ax = axes[1]
    h = [r["h"] for r in spacetime_res]
    ax.loglog(h, [r["L2"] for r in spacetime_res], "o-", label=r"$L_2$")
    ax.loglog(h, [r["Li"] for r in spacetime_res], "s--", label=r"$L_\infty$")
    h_ref = np.array([h[0], h[-1]])
    for order in [3, 6]:
        e0 = spacetime_res[0]["L2"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, ":", color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel("Error")
    ax.set_title("(b) Space-time (CFL=0.3)")
    ax.legend(fontsize=6); ax.grid(True, which="both", alpha=0.3)

    # (c) ODE verification
    ax = axes[2]
    dt_ode = [r["dt"] for r in ode_res]
    ax.loglog(dt_ode, [r["err"] for r in ode_res], "o-", label="TVD-RK3")
    dt_ref = np.array([dt_ode[0], dt_ode[-1]])
    e0 = ode_res[0]["err"]
    ax.loglog(dt_ref, e0*(dt_ref/dt_ref[0])**3, "--", color="gray", alpha=0.5,
              label="$O(\\Delta t^3)$")
    ax.set_xlabel("$\\Delta t$"); ax.set_ylabel("$|q - e^{-1}|$")
    ax.set_title("(c) ODE: $dq/dt = -q$")
    ax.legend(fontsize=7); ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT / "tvd_rk3_convergence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'tvd_rk3_convergence.png'}")


def print_and_save(time_res, spacetime_res, ode_res):
    print(f"\n{'='*70}")
    print("  Temporal convergence (N=256 fixed)")
    print(f"{'='*70}")
    print(f"  {'n_steps':>8} {'dt':>10} {'L2':>12} {'slope':>6} {'Li':>12} {'slope':>6}")
    for r in time_res:
        sl2 = r.get("L2_slope", float("nan"))
        sli = r.get("Li_slope", float("nan"))
        print(f"  {r['n_steps']:>8} {r['dt']:>10.4e} {r['L2']:>12.3e} {sl2:>6.2f} "
              f"{r['Li']:>12.3e} {sli:>6.2f}")

    print(f"\n  Space-time convergence (CFL=0.3)")
    print(f"  {'N':>6} {'h':>10} {'L2':>12} {'slope':>6}")
    for r in spacetime_res:
        s = r.get("L2_slope", float("nan"))
        print(f"  {r['N']:>6} {r['h']:>10.4e} {r['L2']:>12.3e} {s:>6.2f}")

    print(f"\n  ODE verification (dq/dt = -q)")
    print(f"  {'n_steps':>8} {'dt':>10} {'err':>12} {'slope':>6}")
    for r in ode_res:
        s = r.get("slope", float("nan"))
        print(f"  {r['n_steps']:>8} {r['dt']:>10.4e} {r['err']:>12.3e} {s:>6.2f}")

    # LaTeX
    with open(OUT / "table_temporal.tex", "w") as fp:
        fp.write("% TVD-RK3 temporal convergence\n")
        fp.write("\\begin{tabular}{rrrr}\n\\toprule\n")
        fp.write("$n$ & $\\Delta t$ & $L_2$ & slope \\\\\n\\midrule\n")
        for r in time_res:
            s = r.get("L2_slope", float("nan"))
            s_s = f"{s:.2f}" if not np.isnan(s) else "---"
            fp.write(f"{r['n_steps']} & {r['dt']:.3e} & {r['L2']:.2e} & {s_s} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")


def main():
    print("\n" + "="*80)
    print("  【10-7】TVD-RK3 Time Integration Accuracy")
    print("="*80)

    print("\n--- (a) ODE verification ---")
    ode_res = ode_verification()

    print("\n--- (b) Temporal convergence (N=256, spatial error negligible) ---")
    time_res = temporal_convergence(N=256)

    print("\n--- (c) Space-time coupled convergence ---")
    spacetime_res = space_time_convergence()

    print_and_save(time_res, spacetime_res, ode_res)
    plot_results(time_res, spacetime_res, ode_res)

    np.savez(OUT / "tvd_rk3_data.npz",
             temporal=time_res, spacetime=spacetime_res, ode=ode_res)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "tvd_rk3_data.npz", allow_pickle=True)
        plot_results(list(_d["temporal"]), list(_d["spacetime"]), list(_d["ode"]))
    else:
        main()
