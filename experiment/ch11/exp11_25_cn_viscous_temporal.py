#!/usr/bin/env python3
"""[11-25] Crank-Nicolson viscous term temporal accuracy and stability.

Validates: Ch5 -- CN achieves O(dt^2) and is unconditionally stable.

Tests:
  (a) 2D diffusion u_t = nu*Laplacian(u), exact = exp(-2*nu*pi^2*t)*sin(pi*x)*sin(pi*y)
      Temporal convergence: dt refinement at fixed N=64 -> O(dt^2)
  (b) Unconditional stability: large dt (CFL >> 1) still stable

Expected: O(dt^2) convergence; no instability at CFL > 1.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy.sparse.linalg import gmres, LinearOperator
from twophase.backend import Backend  # scipy.sparse.linalg.gmres + LinearOperator stay on CPU
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)

# -- Physical parameters ------------------------------------------------------
NU = 0.01
T_FINAL = 1.0
N_GRID = 64          # fixed spatial resolution (periodic BC -> CCD essentially exact)


# -- Exact solution ------------------------------------------------------------

def exact_solution(X, Y, t):
    """u(x,y,t) = exp(-8*pi^2*nu*t) * sin(2*pi*x) * sin(2*pi*y).

    Periodic BC compatible; eigenvalue = -8*pi^2*nu.
    """
    k = 2.0 * np.pi
    return np.exp(-2.0 * k**2 * NU * t) * np.sin(k * X) * np.sin(k * Y)


# -- CN time stepper via fixed-point iteration ---------------------------------

def ccd_laplacian(u, ccd, backend):
    """Compute Laplacian = d2x + d2y using CCD (device-aware)."""
    xp = backend.xp
    u_dev = xp.asarray(u)
    _, d2x = ccd.differentiate(u_dev, axis=0)
    _, d2y = ccd.differentiate(u_dev, axis=1)
    return np.asarray(backend.to_host(d2x + d2y))


def cn_step(u, ccd, backend, dt):
    """One Crank-Nicolson time step via GMRES.

    Solves:  (I - dt*nu/2 * L) u^{n+1} = u^n + (dt*nu/2) * L u^n
    using scipy GMRES (always CPU) with CCD Laplacian as matrix-free operator.
    On GPU backend, matvec transfers u to device for CCD then back to host.
    """
    shape = u.shape
    n = u.size
    lap_n = ccd_laplacian(u, ccd, backend)
    rhs_2d = u + 0.5 * dt * NU * lap_n

    def matvec(v_flat):
        v = v_flat.reshape(shape)
        lap_v = ccd_laplacian(v, ccd, backend)
        return (v - 0.5 * dt * NU * lap_v).flatten()

    A_op = LinearOperator((n, n), matvec=matvec)
    u_new_flat, info = gmres(A_op, rhs_2d.flatten(), x0=u.flatten(),
                             atol=1e-14, restart=50, maxiter=200)
    return u_new_flat.reshape(shape)


def euler_step(u, ccd, backend, dt):
    """One explicit (forward) Euler time step."""
    lap = ccd_laplacian(u, ccd, backend)
    return u + dt * NU * lap


# -- Test A: temporal convergence ----------------------------------------------

def temporal_convergence():
    backend = Backend()
    gc = GridConfig(ndim=2, N=(N_GRID, N_GRID), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    X_dev, Y_dev = grid.meshgrid()
    X = np.asarray(backend.to_host(X_dev))
    Y = np.asarray(backend.to_host(Y_dev))

    u0 = exact_solution(X, Y, 0.0)
    u_ref = exact_solution(X, Y, T_FINAL)

    K_list = [10, 20, 40, 80, 160, 320]
    results = []

    for K in K_list:
        dt = T_FINAL / K
        u = u0.copy()
        for _ in range(K):
            u = cn_step(u, ccd, backend, dt)
        err = float(np.sqrt(np.mean((u - u_ref)**2)))
        results.append({"K": K, "dt": dt, "L2": err})
        print(f"  K={K:>4}, dt={dt:.4e}: L2={err:.4e}")

    # compute slopes
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0["L2"] > 1e-15 and r1["L2"] > 1e-15:
            r1["slope"] = np.log(r1["L2"] / r0["L2"]) / np.log(r1["dt"] / r0["dt"])

    return results


# -- Test B: unconditional stability -------------------------------------------

def stability_test():
    backend = Backend()
    gc = GridConfig(ndim=2, N=(N_GRID, N_GRID), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    X_dev, Y_dev = grid.meshgrid()
    X = np.asarray(backend.to_host(X_dev))
    Y = np.asarray(backend.to_host(Y_dev))

    h = 1.0 / N_GRID
    u0 = exact_solution(X, Y, 0.0)

    # CFL_viscous = nu * dt / h^2
    cfl_targets = [0.5, 1.0, 2.0, 5.0, 10.0]
    n_steps = 10
    results_cn = []
    results_euler = []

    for cfl in cfl_targets:
        dt = cfl * h**2 / NU

        # CN (GMRES-based)
        u = u0.copy()
        stable = True
        for _ in range(n_steps):
            try:
                u = cn_step(u, ccd, backend, dt)
            except Exception:
                stable = False
                break
            if not np.all(np.isfinite(u)):
                stable = False
                break
        max_u = float(np.max(np.abs(u))) if stable else float("inf")
        results_cn.append({"cfl": cfl, "dt": dt, "max_u": max_u, "stable": stable})
        print(f"  CN   CFL={cfl:>5.1f}: max|u|={max_u:.4e}, stable={stable}")

        # Explicit Euler
        u = u0.copy()
        stable = True
        for _ in range(n_steps):
            u = euler_step(u, ccd, backend, dt)
            if not np.all(np.isfinite(u)):
                stable = False
                break
        max_u = float(np.max(np.abs(u))) if stable else float("inf")
        results_euler.append({"cfl": cfl, "dt": dt, "max_u": max_u, "stable": stable})
        print(f"  Euler CFL={cfl:>5.1f}: max|u|={max_u:.4e}, stable={stable}")

    return results_cn, results_euler


# -- Plotting ------------------------------------------------------------------

def plot_all(conv, stab_cn, stab_euler):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # (a) Temporal convergence
    ax = axes[0]
    dt_arr = [r["dt"] for r in conv]
    err_arr = [r["L2"] for r in conv]
    ax.loglog(dt_arr, err_arr, "o-", color=COLORS[0], markersize=7,
              label="CN + CCD")
    d_ref = np.array([dt_arr[0], dt_arr[-1]])
    for order, ls, col in [(1, ":", "gray"), (2, "--", "gray")]:
        ax.loglog(d_ref, conv[0]["L2"] * (d_ref / d_ref[0])**order,
                  ls, color=col, alpha=0.5,
                  label=f"$O(\\Delta t^{order})$")
    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel(r"$L_2$ error")
    ax.set_title("(a) CN temporal convergence")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (b) Stability comparison
    ax = axes[1]
    cfl_cn = [r["cfl"] for r in stab_cn]
    max_cn = [r["max_u"] if r["stable"] else np.nan for r in stab_cn]
    cfl_eu = [r["cfl"] for r in stab_euler]
    max_eu = [r["max_u"] if r["stable"] else np.nan for r in stab_euler]

    ax.semilogy(cfl_cn, max_cn, "o-", color=COLORS[0], markersize=7,
                label="CN (implicit)")
    ax.semilogy(cfl_eu, max_eu, "s--", color=COLORS[1], markersize=7,
                label="Euler (explicit)")

    # mark unstable Euler points
    for r in stab_euler:
        if not r["stable"]:
            ax.axvline(r["cfl"], color=COLORS[1], alpha=0.3, ls=":")

    ax.axvline(0.5, color="gray", alpha=0.4, ls="--", label=r"CFL$_\nu$=0.5 limit")
    ax.set_xlabel(r"CFL$_\nu = \nu \Delta t / h^2$")
    ax.set_ylabel(r"$\max|u|$ after 10 steps")
    ax.set_title("(b) Stability: CN vs Euler")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "cn_viscous_temporal")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser("[11-25] CN Viscous Temporal").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["conv"], d["stab_cn"], d["stab_euler"])
        return

    print("\n--- (a) Temporal convergence ---")
    conv = temporal_convergence()
    for r in conv:
        s = r.get("slope", float("nan"))
        print(f"  K={r['K']:>4}: dt={r['dt']:.3e}, L2={r['L2']:.3e}, slope={s:.2f}")

    print("\n--- (b) Stability test ---")
    stab_cn, stab_euler = stability_test()

    save_results(OUT / "data.npz", {
        "conv": conv,
        "stab_cn": stab_cn,
        "stab_euler": stab_euler,
    })
    plot_all(conv, stab_cn, stab_euler)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
