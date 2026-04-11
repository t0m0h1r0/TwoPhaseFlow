#!/usr/bin/env python3
"""[11-15] GMRES + FD-LU preconditioner for high-density CCD-PPE.

Idea B: Wrap DC as a GMRES preconditioner.
  - matvec: eval_LH (CCD, matrix-free)
  - preconditioner: L_FD^{-1} via spsolve (same as DC Step 2)
  - GMRES provides optimal polynomial acceleration over the
    eigenvalue cluster [alpha_min, alpha_max]

Baseline comparison: standard DC+LU (exp11_13).

Test:
  Neumann BC, variable density PPE, p* = cos(pi*x)*cos(pi*y),
  density_ratios=[1, 2, 5, 10, 50, 100, 1000],
  N=[32, 64].
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve, gmres, LinearOperator
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__)


def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


# ── CCD operator ───────────────────────────────────────────────────────────

def eval_LH(p_2d, rho, drho_x, drho_y, ccd, backend):
    """Full L_H p = (1/ρ)Δp - (1/ρ²)(∇ρ·∇p)."""
    xp = backend.xp; p_dev = xp.asarray(p_2d)
    dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


# ── FD matrix ──────────────────────────────────────────────────────────────

def build_fd_full(rho, drho_x, drho_y, h, N, pin_dof):
    """FD for full (1/ρ)Δp - (1/ρ²)(∇ρ·∇p)."""
    nx = ny = N + 1; n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j; inv_rho = 1.0 / rho[i, j]; cc = 0.0
            for coord, dr, lo, hi in [
                (i, drho_x[i, j], (i - 1) * ny + j, (i + 1) * ny + j),
                (j, drho_y[i, j], i * ny + (j - 1), i * ny + (j + 1)),
            ]:
                coeff_bc = 2.0 * inv_rho / h**2
                if 0 < coord < N:
                    dr_term = dr * inv_rho**2
                    cm = inv_rho / h**2 + dr_term / (2 * h)
                    cp = inv_rho / h**2 - dr_term / (2 * h)
                    rows.append(k); cols.append(lo); vals.append(cm); cc -= cm
                    rows.append(k); cols.append(hi); vals.append(cp); cc -= cp
                elif coord == 0:
                    rows.append(k); cols.append(hi); vals.append(coeff_bc); cc -= coeff_bc
                else:
                    rows.append(k); cols.append(lo); vals.append(coeff_bc); cc -= coeff_bc
            rows.append(k); cols.append(k); vals.append(cc)
    pin_mask = [r != pin_dof for r in rows]
    rows_p = [r for r, m in zip(rows, pin_mask) if m]
    cols_p = [c for c, m in zip(cols, pin_mask) if m]
    vals_p = [v for v, m in zip(vals, pin_mask) if m]
    rows_p.append(pin_dof); cols_p.append(pin_dof); vals_p.append(1.0)
    return sparse.csr_matrix((vals_p, (rows_p, cols_p)), shape=(n, n))


# ── Solvers ────────────────────────────────────────────────────────────────

def dc_lu_baseline(rhs_flat, rho, drho_x, drho_y, ccd, backend,
                   h, N, tol, maxiter, pin_dof, omega, shape):
    """Standard DC+LU."""
    L_FD = build_fd_full(rho, drho_x, drho_y, h, N, pin_dof)
    p = np.zeros_like(rhs_flat); residuals = []
    for k in range(maxiter):
        Lp = eval_LH(p.reshape(shape), rho, drho_x, drho_y, ccd, backend).ravel()
        d = rhs_flat - Lp; d[pin_dof] = 0.0
        res = float(np.linalg.norm(d))
        residuals.append(res)
        if res < tol:
            return p, residuals, k + 1, "conv"
        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, "divg"
        if k >= 10 and residuals[-10] > 0 and res / residuals[-10] > 0.99:
            return p, residuals, k + 1, "stag"
        dp = spsolve(L_FD, d)
        p = p + omega * dp; p[pin_dof] = 0.0
    return p, residuals, maxiter, "stag"


class GMRESCounter:
    """Callback to record residual at each GMRES iteration."""
    def __init__(self):
        self.residuals = []
        self.n_calls = 0
    def __call__(self, residual):
        if isinstance(residual, np.ndarray):
            residual = float(np.linalg.norm(residual))
        self.residuals.append(residual)
        self.n_calls += 1


def gmres_fd_precond(rhs_flat, rho, drho_x, drho_y, ccd, backend,
                     h, N, tol, maxiter, pin_dof, shape):
    """GMRES with FD-LU preconditioner (Idea B)."""
    n = len(rhs_flat)
    L_FD = build_fd_full(rho, drho_x, drho_y, h, N, pin_dof)

    eval_count = [0]

    def matvec(p_flat):
        eval_count[0] += 1
        result = eval_LH(p_flat.reshape(shape), rho, drho_x, drho_y,
                         ccd, backend).ravel()
        result[pin_dof] = p_flat[pin_dof]  # gauge pin row
        return result

    def precond_matvec(r_flat):
        return spsolve(L_FD, r_flat)

    A = LinearOperator((n, n), matvec=matvec, dtype=np.float64)
    M = LinearOperator((n, n), matvec=precond_matvec, dtype=np.float64)

    counter = GMRESCounter()
    p, info = gmres(A, rhs_flat, M=M, atol=tol, rtol=0,
                    maxiter=maxiter, callback=counter,
                    callback_type='pr_norm')

    # Compute final true residual
    Lp = eval_LH(p.reshape(shape), rho, drho_x, drho_y, ccd, backend).ravel()
    Lp[pin_dof] = p[pin_dof]
    true_res = float(np.linalg.norm(rhs_flat - Lp))

    status = "conv" if info == 0 else ("divg" if info < 0 else "stag")
    return p, counter.residuals, eval_count[0], status, true_res


# ── Experiment ─────────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend()
    density_ratios = [1, 2, 5, 10, 50, 100, 1000]
    grid_sizes = [32, 64]
    tol = 1e-8
    dc_maxiter = 300
    gmres_maxiter = 100
    all_results = {}

    for N in grid_sizes:
        h = 1.0 / N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        xp = backend.xp; X, Y = grid.meshgrid()
        # DC/GMRES loops use scipy.sparse (CPU-only); keep host copies.
        # eval_LH routes CCD through device via xp.asarray + to_host.
        X = backend.to_host(X); Y = backend.to_host(Y)
        p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
        shape = p_exact.shape
        pin_dof = (N // 2) * (N + 1) + (N // 2)
        phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
        eps = 1.5 * h

        print(f"\n{'='*70}")
        print(f"  N = {N}")
        print(f"{'='*70}")

        for rho_ratio in density_ratios:
            rho_g = 1.0 / rho_ratio
            H = smoothed_heaviside(phi, eps)
            rho = 1.0 + (rho_g - 1.0) * H
            drho_x_dev, _ = ccd.differentiate(xp.asarray(rho), 0)
            drho_y_dev, _ = ccd.differentiate(xp.asarray(rho), 1)
            drho_x = np.asarray(backend.to_host(drho_x_dev))
            drho_y = np.asarray(backend.to_host(drho_y_dev))
            rhs_2d = eval_LH(p_exact, rho, drho_x, drho_y, ccd, backend)
            rhs_2d.ravel()[pin_dof] = 0.0
            rhs_flat = rhs_2d.ravel().copy()

            # ── Baseline: DC+LU ω=0.5 ──
            _, res_dc, evals_dc, st_dc = dc_lu_baseline(
                rhs_flat, rho, drho_x, drho_y, ccd, backend,
                h, N, tol, dc_maxiter, pin_dof, omega=0.5, shape=shape)
            sym_dc = {"conv": "V", "stag": "~", "divg": "X"}[st_dc]

            # Solution error for DC
            if st_dc == "conv":
                p_dc = _  # already returned
            err_dc = res_dc[-1]

            all_results[f"N{N}_r{rho_ratio}_dc"] = dict(
                N=N, rho_ratio=rho_ratio, method="dc",
                evals=evals_dc, iters=len(res_dc), status=st_dc,
                final_res=res_dc[-1], residuals=np.array(res_dc))

            # ── GMRES + FD-LU preconditioner ──
            p_gm, res_gm, evals_gm, st_gm, true_res_gm = gmres_fd_precond(
                rhs_flat, rho, drho_x, drho_y, ccd, backend,
                h, N, tol, gmres_maxiter, pin_dof, shape)
            sym_gm = {"conv": "V", "stag": "~", "divg": "X"}[st_gm]

            # Solution error
            sol_err_gm = float(np.linalg.norm(p_gm - p_exact.ravel()))

            all_results[f"N{N}_r{rho_ratio}_gmres"] = dict(
                N=N, rho_ratio=rho_ratio, method="gmres",
                evals=evals_gm, iters=len(res_gm), status=st_gm,
                final_res=true_res_gm, sol_error=sol_err_gm,
                residuals=np.array(res_gm))

            print(f"  rho={rho_ratio:>5}  DC(w=0.5): {evals_dc:>4} evals {sym_dc}"
                  f"  res={res_dc[-1]:.2e}"
                  f"  |  GMRES: {evals_gm:>3} evals {sym_gm}"
                  f"  res={true_res_gm:.2e}  err={sol_err_gm:.2e}")

    return all_results


def plot_results(all_results):
    import matplotlib.pyplot as plt

    density_ratios = sorted(set(v["rho_ratio"] for v in all_results.values()))
    grid_sizes = sorted(set(v["N"] for v in all_results.values()))

    for N in grid_sizes:
        # ── Fig 1: GMRES iterations vs density ratio ──
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

        dc_iters = []
        dc_status = []
        gm_iters = []
        gm_status = []
        for rr in density_ratios:
            kd = f"N{N}_r{rr}_dc"
            kg = f"N{N}_r{rr}_gmres"
            if kd in all_results:
                dc_iters.append(all_results[kd]["iters"])
                dc_status.append(all_results[kd]["status"])
            if kg in all_results:
                gm_iters.append(all_results[kg]["iters"])
                gm_status.append(all_results[kg]["status"])

        x = np.arange(len(density_ratios))
        bars_dc = ax1.bar(x - 0.2, dc_iters, 0.35, label="DC+LU ($\\omega$=0.5)",
                          color=COLORS[0], alpha=0.8)
        bars_gm = ax1.bar(x + 0.2, gm_iters, 0.35, label="GMRES+FD-prec",
                          color=COLORS[1], alpha=0.8)

        # Mark stagnation/divergence
        for i, (st, bar) in enumerate(zip(dc_status, bars_dc)):
            if st != "conv":
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                         "~" if st == "stag" else "X",
                         ha="center", va="bottom", fontsize=9, color="red")
        for i, (st, bar) in enumerate(zip(gm_status, bars_gm)):
            if st != "conv":
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                         "~" if st == "stag" else "X",
                         ha="center", va="bottom", fontsize=9, color="red")

        ax1.set_xticks(x)
        ax1.set_xticklabels([str(r) for r in density_ratios])
        ax1.set_xlabel(r"$\rho_l/\rho_g$")
        ax1.set_ylabel("Iterations")
        ax1.set_title(f"Iteration count ($N={N}$)")
        ax1.legend()
        ax1.set_yscale("log")

        # ── Fig 2: Final residual comparison ──
        dc_res = [all_results[f"N{N}_r{rr}_dc"]["final_res"]
                  for rr in density_ratios if f"N{N}_r{rr}_dc" in all_results]
        gm_res = [all_results[f"N{N}_r{rr}_gmres"]["final_res"]
                  for rr in density_ratios if f"N{N}_r{rr}_gmres" in all_results]

        ax2.semilogy(density_ratios[:len(dc_res)], dc_res, "o-",
                     color=COLORS[0], label="DC+LU ($\\omega$=0.5)")
        ax2.semilogy(density_ratios[:len(gm_res)], gm_res, "s-",
                     color=COLORS[1], label="GMRES+FD-prec")
        ax2.axhline(1e-8, color="gray", linestyle=":", linewidth=0.5, label="tol")
        ax2.set_xscale("log")
        ax2.set_xlabel(r"$\rho_l/\rho_g$")
        ax2.set_ylabel("Final residual $\\|q - L_H p\\|$")
        ax2.set_title(f"Residual vs density ratio ($N={N}$)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        fig.tight_layout()
        save_figure(fig, OUT / f"gmres_vs_dc_N{N}")

        # ── Fig 3: Residual histories at selected density ratios ──
        fig2, axes = plt.subplots(1, 3, figsize=(14, 4.5))
        for ai, rr in enumerate([1, 10, 1000]):
            ax = axes[ai]
            kd = f"N{N}_r{rr}_dc"
            kg = f"N{N}_r{rr}_gmres"
            if kd in all_results:
                v = all_results[kd]
                ax.semilogy(v["residuals"], "--", color=COLORS[0], linewidth=2,
                            label=f"DC ({v['status']})")
            if kg in all_results:
                v = all_results[kg]
                if len(v["residuals"]) > 0:
                    ax.semilogy(v["residuals"], "-", color=COLORS[1], linewidth=2,
                                label=f"GMRES ({v['status']})")
            ax.set_xlabel("Iteration")
            ax.set_ylabel("Residual")
            ax.set_title(rf"$\rho_l/\rho_g = {rr}$, $N={N}$")
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.axhline(1e-8, color="gray", linestyle=":", linewidth=0.5)
        fig2.tight_layout()
        save_figure(fig2, OUT / f"gmres_residuals_N{N}")

    print(f"\nPlots saved to {OUT}")


def main():
    args = experiment_argparser("[11-15] GMRES + FD-LU preconditioner").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_results(d)
        return
    all_results = run_experiment()
    save_results(OUT / "data.npz", all_results)
    plot_results(all_results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
