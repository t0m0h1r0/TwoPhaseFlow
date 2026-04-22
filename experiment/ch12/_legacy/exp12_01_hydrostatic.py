#!/usr/bin/env python3
"""[12-01] Hydrostatic pressure equilibrium test.

Validates: steady-state pressure field under uniform gravity with no-slip walls.

Setup
-----
  Domain [0,1]², wall BC, ρ=1.0, gravity g_y = -1.0
  Initial: u = v = 0
  Non-incremental projection: 100 steps per grid
  Grid: N = 32, 64, 128;  dt = 0.1 * h

Expected
--------
  - ||u||_∞ ≈ 0  (velocity stays quiescent)
  - p → ρ * |g| * (1 - y)  up to a constant (hydrostatic balance)

Output
------
  - Velocity magnitude ||u||_∞ vs N
  - Pressure error |p − ρ*g*(1−y)|_∞ vs N
  - Figure: convergence + pressure profile
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.tools.experiment.gpu import sparse_solve_2d
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure, COLORS,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# -- Physical parameters ------------------------------------------------------
RHO = 1.0
G_Y = -1.0
N_STEPS = 100


# -- PPE solver ---------------------------------------------------------------

def _solve_ppe(rhs, rho, ppe_builder, backend):
    """Assemble and solve the variable-coefficient PPE."""
    triplet, A_shape = ppe_builder.build(rho)  # always host (numpy) arrays
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=A_shape)
    xp = backend.xp
    rhs_flat = xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return sparse_solve_2d(backend, A, rhs_flat).reshape(rho.shape)


# -- Wall BC helper ------------------------------------------------------------

def wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


# -- Single-grid run -----------------------------------------------------------

def run(N):
    """Run hydrostatic test on N×N grid, return diagnostics."""
    backend = Backend()
    xp = backend.xp
    h = 1.0 / N
    dt = 0.1 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")

    X, Y = grid.meshgrid()
    rho = xp.full_like(X, RHO)

    u = xp.zeros_like(X)
    v = xp.zeros_like(X)

    # IPC: initialize pressure to exact hydrostatic solution
    p = RHO * abs(G_Y) * (1.0 - Y)

    u_max_hist = []

    for step in range(N_STEPS):
        # IPC Predictor: gravity + pressure gradient from previous step
        dp_dx_n, _ = ccd.differentiate(p, 0)
        dp_dy_n, _ = ccd.differentiate(p, 1)
        u_star = u - dt / rho * dp_dx_n
        v_star = v + dt * G_Y - dt / rho * dp_dy_n
        wall_bc(u_star); wall_bc(v_star)

        # PPE for pressure correction: ∇·(1/ρ ∇φ) = ∇·u* / dt
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (du_dx + dv_dy) / dt
        phi = _solve_ppe(rhs, rho, ppe_builder, backend)

        # Corrector
        dphi_dx, _ = ccd.differentiate(phi, 0)
        dphi_dy, _ = ccd.differentiate(phi, 1)
        u = u_star - dt / rho * dphi_dx
        v = v_star - dt / rho * dphi_dy
        wall_bc(u); wall_bc(v)

        # Update pressure (IPC)
        p = p + phi

        vel_mag = xp.sqrt(u**2 + v**2)
        u_max_hist.append(float(xp.max(vel_mag)))

        if np.isnan(u_max_hist[-1]) or u_max_hist[-1] > 1e6:
            print(f"    [N={N}] BLOWUP at step {step+1}")
            break

    # Exact hydrostatic pressure: p_exact = ρ*|g|*(1 - y) + C
    # Shift measured p so that mean matches exact mean
    p_exact = RHO * abs(G_Y) * (1.0 - Y)
    p_shifted = p - xp.mean(p) + xp.mean(p_exact)

    # Exclude boundary nodes for clean interior comparison
    s = slice(2, -2)
    p_err_inf = float(xp.max(xp.abs(p_shifted[s, s] - p_exact[s, s])))
    u_inf_final = u_max_hist[-1]

    return {
        "N": N, "h": h, "dt": dt,
        "u_inf_final": u_inf_final,
        "u_inf_peak": max(u_max_hist),
        "p_err_inf": p_err_inf,
        "u_max_hist": np.array(u_max_hist),
        "p_profile_center": backend.to_host(p_shifted[N // 2, :]).copy(),
        "y_center": backend.to_host(Y[N // 2, :]).copy(),
        "n_steps": len(u_max_hist),
    }


# -- Plotting ------------------------------------------------------------------

def make_figures(results):
    Ns = [r["N"] for r in results]
    hs = [r["h"] for r in results]
    u_finals = [r["u_inf_final"] for r in results]
    p_errs = [r["p_err_inf"] for r in results]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # (a) Velocity residual vs h
    ax = axes[0]
    ax.loglog(hs, u_finals, "o-", color=COLORS[0], linewidth=1.5, markersize=7,
              label=r"$\|\mathbf{u}\|_\infty$ (final)")
    h_ref = np.array(hs)
    ax.loglog(h_ref, u_finals[0] * (h_ref / hs[0])**2, "k:", alpha=0.5,
              label=r"$O(h^2)$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax.set_title("(a) Velocity residual"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    # (b) Pressure error vs h
    ax = axes[1]
    ax.loglog(hs, p_errs, "s-", color=COLORS[1], linewidth=1.5, markersize=7,
              label=r"$\|p - p_{\mathrm{exact}}\|_\infty$")
    ax.loglog(h_ref, p_errs[0] * (h_ref / hs[0])**2, "k:", alpha=0.5,
              label=r"$O(h^2)$")
    ax.loglog(h_ref, p_errs[0] * (h_ref / hs[0])**4, "k--", alpha=0.4,
              label=r"$O(h^4)$")
    ax.set_xlabel("$h$"); ax.set_ylabel("Pressure error")
    ax.set_title("(b) Pressure error"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    # (c) Pressure profile at x = 0.5
    ax = axes[2]
    for i, r in enumerate(results):
        ax.plot(r["y_center"], r["p_profile_center"], "-",
                color=COLORS[i % len(COLORS)], linewidth=1.2,
                label=f"N={r['N']}")
    y_ex = np.linspace(0, 1, 200)
    p_ex = RHO * abs(G_Y) * (1.0 - y_ex)
    ax.plot(y_ex, p_ex, "k--", linewidth=1.5, label="Exact")
    ax.set_xlabel("$y$"); ax.set_ylabel("$p$")
    ax.set_title("(c) Pressure profile ($x=0.5$)"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "hydrostatic")

    # Time history
    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    for i, r in enumerate(results):
        ax2.semilogy(np.arange(1, r["n_steps"] + 1), r["u_max_hist"],
                     color=COLORS[i % len(COLORS)], linewidth=1.2,
                     label=f"N={r['N']}")
    ax2.set_xlabel("Time step"); ax2.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax2.set_title("Velocity magnitude history"); ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    save_figure(fig2, OUT / "hydrostatic_time_history")


# -- Convergence rates ---------------------------------------------------------

def print_table(results):
    print(f"\n{'='*70}")
    print("  [12-01] Hydrostatic Pressure Equilibrium")
    print(f"{'='*70}")
    print(f"  {'N':>5} | {'h':>10} | {'||u||_inf':>12} | {'|p_err|_inf':>12} | {'steps':>6}")
    print("  " + "-" * 58)
    for r in results:
        print(f"  {r['N']:>5} | {r['h']:>10.5f} | {r['u_inf_final']:>12.4e} | "
              f"{r['p_err_inf']:>12.4e} | {r['n_steps']:>6}")

    print("\n  Convergence rates:")
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        log_h = np.log(r0["h"] / r1["h"])
        rate_u = np.log(r0["u_inf_final"] / r1["u_inf_final"]) / log_h if r1["u_inf_final"] > 0 else float("nan")
        rate_p = np.log(r0["p_err_inf"] / r1["p_err_inf"]) / log_h if r1["p_err_inf"] > 0 else float("nan")
        print(f"    N={r0['N']:>3}->{r1['N']:>3}:  ||u|| rate={rate_u:+.2f},  p_err rate={rate_p:+.2f}")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser("[12-01] Hydrostatic").parse_args()

    if args.plot_only:
        data = load_results(NPZ)
        make_figures(data["results"])
        return

    Ns = [32, 64, 128]
    results = []

    for N in Ns:
        print(f"  Running N={N} ...")
        r = run(N)
        results.append(r)

    print_table(results)

    # Save
    save_data = {
        "results": [{k: v for k, v in r.items()
                      if k not in ("u_max_hist", "p_profile_center", "y_center")}
                     for r in results],
    }
    for i, r in enumerate(results):
        save_data[f"u_max_hist_{i}"] = r["u_max_hist"]
        save_data[f"p_profile_{i}"] = r["p_profile_center"]
        save_data[f"y_center_{i}"] = r["y_center"]
    save_results(NPZ, save_data)

    make_figures(results)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
