#!/usr/bin/env python3
"""【10-16】DC sweep (Thomas ADI) convergence limit vs density ratio.

Paper ref: §8d (defect correction + LTS)

Problem:
  ∇·(1/ρ ∇p) = q on [0,1]², Neumann BC (dp/dn=0 at walls) + pin gauge.
  p* = cos(πx)cos(πy)  [satisfies Neumann BC: dp/dn=0 at all walls]
  ρ(x,y): circular interface (R=0.25), smoothed Heaviside.

Solver: DC sweep (Thomas ADI) — same algorithm as PPESolverSweep.
  LHS: 2nd-order FD (Thomas 1D solve, O(N) per line)
  RHS: CCD O(h⁶) residual
  Gauge: pin_dof = center node fixed to 0

Sweep:
  ρ_l/ρ_g = 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000
  N = 32, 64
  c_tau = 2.0 (default)

Goal: identify at which density ratio the DC sweep method diverges
or fails to converge within maxiter.
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL, FIGSIZE_WIDE,
)

apply_style()

OUT = experiment_dir(__file__)


# ── Smoothed Heaviside ───────────────────────────────────────────────────────

def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


# ── CCD variable-density Laplacian (O(h⁶)) ─────────────────────────────────

def eval_LH(p, rho, drho_x, drho_y, ccd, backend):
    xp = backend.xp
    p_dev = xp.asarray(p)
    dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


# ── Thomas sweep (1D, vectorized) ──────────────────────────────────────────

def thomas_sweep(rhs, rho, drho_ax, dtau, h, axis):
    """(1/Δτ − L_FD_axis) q = rhs, Neumann BC (ghost-cell reflection)."""
    f = np.moveaxis(rhs, axis, 0)
    rho_f = np.moveaxis(rho, axis, 0)
    drho_f = np.moveaxis(drho_ax, axis, 0)
    dtau_f = np.moveaxis(dtau, axis, 0)
    n = f.shape[0]
    h2 = h * h

    inv_dtau = 1.0 / dtau_f
    inv_rho_h2 = 1.0 / (rho_f * h2)
    drho_h = drho_f / (rho_f**2 * 2.0 * h)

    a = np.zeros_like(f)
    b = np.ones_like(f)
    c = np.zeros_like(f)
    rhs_m = f.copy()

    # Interior coefficients
    a[1:-1] = -inv_rho_h2[1:-1] + drho_h[1:-1]
    b[1:-1] = inv_dtau[1:-1] + 2.0 * inv_rho_h2[1:-1]
    c[1:-1] = -inv_rho_h2[1:-1] - drho_h[1:-1]

    # Neumann BC: ghost-cell reflection q[-1]=q[1], q[N+1]=q[N-1]
    # → first-derivative (drho_h) term vanishes at walls
    a[0]  = 0.0;                    b[0]  = inv_dtau[0]  + 2.0 * inv_rho_h2[0];  c[0]  = -2.0 * inv_rho_h2[0]
    a[-1] = -2.0 * inv_rho_h2[-1]; b[-1] = inv_dtau[-1] + 2.0 * inv_rho_h2[-1]; c[-1] = 0.0
    # rhs at boundaries is kept unchanged

    # Thomas forward elimination
    c_p = np.zeros_like(f)
    r_p = np.zeros_like(f)
    c_p[0] = c[0] / b[0]
    r_p[0] = rhs_m[0] / b[0]
    for i in range(1, n):
        denom = b[i] - a[i] * c_p[i - 1]
        c_p[i] = c[i] / denom
        r_p[i] = (rhs_m[i] - a[i] * r_p[i - 1]) / denom

    # Back substitution
    q = np.empty_like(f)
    q[-1] = r_p[-1]
    for i in range(n - 2, -1, -1):
        q[i] = r_p[i] - c_p[i] * q[i + 1]

    return np.moveaxis(q, 0, axis)


# ── DC sweep solver ────────────────────────────────────────────────────────

def dc_sweep_solve(rhs, rho, drho_x, drho_y, ccd, backend,
                   h, c_tau, tol, maxiter, pin_dof):
    """DC sweep: CCD residual + Thomas ADI correction.

    Gauge: pin_dof (one node) fixed to 0.  Boundary correction is handled
    by apply_thomas_neumann inside thomas_sweep — do NOT zero all edges.

    Returns (p, residuals, n_iter, converged).
    """
    shape = rhs.shape
    p = np.zeros(shape, dtype=float)
    residuals = []

    dtau = c_tau * rho * h**2 / 2.0

    for k in range(maxiter):
        Lp = eval_LH(p, rho, drho_x, drho_y, ccd, backend)
        R = rhs - Lp
        R.ravel()[pin_dof] = 0.0

        R_flat = R.ravel().copy()
        res = float(np.sqrt(np.dot(R_flat, R_flat)))
        residuals.append(res)

        if res < tol:
            return p, residuals, k + 1, True

        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, False

        # x-sweep then y-sweep (Thomas ADI)
        q = thomas_sweep(R, rho, drho_x, dtau, h, axis=0)
        q.ravel()[pin_dof] = 0.0

        dp = thomas_sweep(q, rho, drho_y, dtau, h, axis=1)
        dp.ravel()[pin_dof] = 0.0

        p = p + dp
        p.ravel()[pin_dof] = 0.0

    return p, residuals, maxiter, False


# ── Also compare with DC + direct LU ──────────────────────────────────────

def dc_lu_solve(rhs, rho, drho_x, drho_y, ccd, backend, h, N, tol, maxiter, pin_dof):
    """DC with direct LU (spsolve) for L_L — as reference."""
    from scipy import sparse
    from scipy.sparse.linalg import spsolve

    nx, ny = N + 1, N + 1
    n_dof = nx * ny

    def idx(i, j):
        return i * ny + j

    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                inv_rho = 1.0 / rho[i, j]
                drx = drho_x[i, j] / rho[i, j]**2
                dry = drho_y[i, j] / rho[i, j]**2
                cx_m = inv_rho / h**2 + drx / (2*h)
                cx_p = inv_rho / h**2 - drx / (2*h)
                cy_m = inv_rho / h**2 + dry / (2*h)
                cy_p = inv_rho / h**2 - dry / (2*h)
                cc = -2.0 * inv_rho / h**2 - 2.0 * inv_rho / h**2
                rows.append(k); cols.append(idx(i-1, j)); vals.append(cx_m)
                rows.append(k); cols.append(idx(i+1, j)); vals.append(cx_p)
                rows.append(k); cols.append(idx(i, j-1)); vals.append(cy_m)
                rows.append(k); cols.append(idx(i, j+1)); vals.append(cy_p)
                rows.append(k); cols.append(k);            vals.append(cc)

    L_L = sparse.csr_matrix((vals, (rows, cols)), shape=(n_dof, n_dof))

    shape = rhs.shape
    p = np.zeros(shape, dtype=float)
    residuals = []
    omega = 0.3  # relaxation — needed for stability (cf. exp10_11)

    for k in range(maxiter):
        Lp = eval_LH(p, rho, drho_x, drho_y, ccd, backend)
        d = rhs - Lp
        d.ravel()[pin_dof] = 0.0

        d_flat = d.ravel().copy()
        res = float(np.sqrt(np.dot(d_flat, d_flat)))
        residuals.append(res)
        if res < tol:
            return p, residuals, k + 1, True
        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, False

        dp = spsolve(L_L, d_flat).reshape(shape)
        p = p + omega * dp
        p.ravel()[pin_dof] = 0.0

    return p, residuals, maxiter, False


# ── Experiment ──────────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend(use_gpu=False)

    density_ratios = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    grid_sizes = [32, 64]
    c_tau = 2.0
    tol = 1e-10
    maxiter = 2000

    all_results = {}

    for N in grid_sizes:
        h = 1.0 / N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        xp = backend.xp

        X, Y = grid.meshgrid()
        # cos(πx)cos(πy): dp/dn=0 at all walls → compatible with Neumann CCD BC
        p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)

        # Pin gauge: center node (N//2, N//2)
        pin_dof = (N // 2) * (N + 1) + (N // 2)

        phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
        eps = 1.5 * h

        print(f"\n{'='*80}")
        print(f"  N={N}, h={h:.4f}, c_tau={c_tau}, tol={tol}, maxiter={maxiter}")
        print(f"{'='*80}")
        print(f"  {'ρ_l/ρ_g':>8} | {'sweep iters':>11} | {'sweep res':>12} | "
              f"{'sweep conv':>10} | {'LU iters':>8} | {'LU res':>12} | {'LU conv':>7}")
        print("  " + "-" * 95)

        for rho_ratio in density_ratios:
            rho_l = 1.0
            rho_g = 1.0 / rho_ratio

            H = smoothed_heaviside(phi, eps)
            rho = rho_l + (rho_g - rho_l) * H

            drho_x_dev, _ = ccd.differentiate(xp.asarray(rho), 0)
            drho_y_dev, _ = ccd.differentiate(xp.asarray(rho), 1)
            drho_x = np.asarray(backend.to_host(drho_x_dev))
            drho_y = np.asarray(backend.to_host(drho_y_dev))

            rhs = eval_LH(p_exact, rho, drho_x, drho_y, ccd, backend)
            # Neumann BC: no boundary zeroing. Pin gauge node only.
            rhs.ravel()[pin_dof] = 0.0

            # DC sweep (Thomas ADI)
            p_sw, res_sw, n_sw, conv_sw = dc_sweep_solve(
                rhs, rho, drho_x, drho_y, ccd, backend,
                h, c_tau, tol, maxiter, pin_dof,
            )

            # DC + direct LU (reference, omega=0.3 relaxation)
            p_lu, res_lu, n_lu, conv_lu = dc_lu_solve(
                rhs, rho, drho_x, drho_y, ccd, backend,
                h, N, tol, min(maxiter, 500), pin_dof,
            )

            key = f"N{N}_r{rho_ratio}"
            all_results[key] = {
                "N": N, "h": h, "rho_ratio": rho_ratio,
                "sweep_iters": n_sw, "sweep_converged": int(conv_sw),
                "sweep_final_res": res_sw[-1] if res_sw else np.nan,
                "sweep_residuals": np.array(res_sw),
                "lu_iters": n_lu, "lu_converged": int(conv_lu),
                "lu_final_res": res_lu[-1] if res_lu else np.nan,
                "lu_residuals": np.array(res_lu),
            }

            sw_tag = "OK" if conv_sw else "FAIL"
            lu_tag = "OK" if conv_lu else "FAIL"
            print(f"  {rho_ratio:>8} | {n_sw:>11} | {res_sw[-1]:>12.3e} | "
                  f"{sw_tag:>10} | {n_lu:>8} | {res_lu[-1]:>12.3e} | {lu_tag:>7}")

    return all_results


# ── Plot ────────────────────────────────────────────────────────────────────

def plot_results(all_results):
    import matplotlib.pyplot as plt

    grid_sizes = sorted(set(v["N"] for v in all_results.values()))

    # (a) Iteration count vs density ratio
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    for idx, N in enumerate(grid_sizes):
        ax = axes[idx]
        ratios, sw_iters, lu_iters = [], [], []
        sw_conv, lu_conv = [], []

        for key, v in sorted(all_results.items()):
            if v["N"] != N:
                continue
            ratios.append(v["rho_ratio"])
            sw_iters.append(v["sweep_iters"])
            lu_iters.append(v["lu_iters"])
            sw_conv.append(v["sweep_converged"])
            lu_conv.append(v["lu_converged"])

        ratios = np.array(ratios)
        sw_iters = np.array(sw_iters)
        lu_iters = np.array(lu_iters)
        sw_conv = np.array(sw_conv)
        lu_conv = np.array(lu_conv)

        # Plot converged as filled, failed as hollow
        ax.semilogx(ratios[sw_conv == 1], sw_iters[sw_conv == 1],
                     "o-", color=COLORS[0], label="DC sweep (Thomas ADI)",
                     markersize=7)
        if np.any(sw_conv == 0):
            ax.semilogx(ratios[sw_conv == 0], sw_iters[sw_conv == 0],
                         "o", color=COLORS[0], markerfacecolor="white",
                         markersize=9, markeredgewidth=2)

        ax.semilogx(ratios[lu_conv == 1], lu_iters[lu_conv == 1],
                     "s-", color=COLORS[1], label="DC + direct LU",
                     markersize=7)
        if np.any(lu_conv == 0):
            ax.semilogx(ratios[lu_conv == 0], lu_iters[lu_conv == 0],
                         "s", color=COLORS[1], markerfacecolor="white",
                         markersize=9, markeredgewidth=2)

        ax.set_xlabel(r"$\rho_l / \rho_g$")
        ax.set_ylabel("Iterations")
        ax.set_title(f"$N = {N}$ (hollow = not converged)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "dc_sweep_iters_vs_ratio")

    # (b) Residual history for selected cases
    fig2, axes2 = plt.subplots(1, len(grid_sizes), figsize=FIGSIZE_WIDE)
    if len(grid_sizes) == 1:
        axes2 = [axes2]

    selected_ratios = [1, 10, 100, 1000]

    for idx, N in enumerate(grid_sizes):
        ax = axes2[idx]
        for ci, rr in enumerate(selected_ratios):
            key = f"N{N}_r{rr}"
            if key not in all_results:
                continue
            v = all_results[key]
            res = v["sweep_residuals"]
            if len(res) > 0:
                label = rf"$\rho_l/\rho_g = {rr}$"
                style = "-" if v["sweep_converged"] else "--"
                ax.semilogy(range(1, len(res)+1), res,
                            style, color=COLORS[ci % len(COLORS)],
                            label=label)

        ax.set_xlabel("Iteration")
        ax.set_ylabel("Residual (RMS)")
        ax.set_title(f"DC sweep residual ($N={N}$)")
        ax.legend(fontsize=8)
        ax.grid(True, which="both", alpha=0.3)

    fig2.tight_layout()
    save_figure(fig2, OUT / "dc_sweep_residual_history")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser("DC sweep convergence limit vs density ratio").parse_args()

    if args.plot_only:
        results = load_results(OUT / "data.npz")
        # Reconstruct nested arrays
        rebuilt = {}
        for key, val in results.items():
            if isinstance(val, dict):
                rebuilt[key] = val
        plot_results(rebuilt)
        return

    print("\n" + "=" * 80)
    print("  【10-16】DC Sweep Convergence Limit vs Density Ratio")
    print("=" * 80)

    all_results = run_experiment()
    save_results(OUT / "data.npz", all_results)
    plot_results(all_results)

    # Summary table
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
