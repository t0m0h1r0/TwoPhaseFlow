#!/usr/bin/env python3
"""[11-13] DC + LU omega-relaxation convergence map.

Validates: Ch9b -- omega-relaxed DC spectral radius theory.

Test:
  Neumann BC, variable density PPE,
  omega=[0.1, 0.2, 0.3, 0.5, 0.7, 0.83],
  rho_l/rho_g=[1, 2, 5, 10, 20, 50, 100, 200, 500, 1000],
  N=[32, 64].

Expected: omega_max ~ 0.833; divergence at high density ratio.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__)


def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


def eval_LH(p, rho, drho_x, drho_y, ccd, backend):
    xp = backend.xp; p_dev = xp.asarray(p)
    dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


def build_fd_varrho_neumann(rho, drho_x, drho_y, h, N, pin_dof):
    nx = ny = N + 1; n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j; inv_rho = 1.0 / rho[i, j]; cc = 0.0
            for coord, dr, lo, hi in [
                (i, drho_x[i,j], (i-1)*ny+j, (i+1)*ny+j),
                (j, drho_y[i,j], i*ny+(j-1), i*ny+(j+1))]:
                coeff_bc = 2.0 * inv_rho / h**2
                if 0 < coord < N:
                    dr_term = dr * inv_rho**2
                    cm = inv_rho/h**2 + dr_term/(2*h)
                    cp = inv_rho/h**2 - dr_term/(2*h)
                    rows.append(k); cols.append(lo); vals.append(cm); cc -= cm
                    rows.append(k); cols.append(hi); vals.append(cp); cc -= cp
                elif coord == 0:
                    rows.append(k); cols.append(hi); vals.append(coeff_bc); cc -= coeff_bc
                else:
                    rows.append(k); cols.append(lo); vals.append(coeff_bc); cc -= coeff_bc
            rows.append(k); cols.append(k); vals.append(cc)
    # Gauge pin
    pin_mask = [r != pin_dof for r in rows]
    rows_p = [r for r, m in zip(rows, pin_mask) if m]
    cols_p = [c for c, m in zip(cols, pin_mask) if m]
    vals_p = [v for v, m in zip(vals, pin_mask) if m]
    rows_p.append(pin_dof); cols_p.append(pin_dof); vals_p.append(1.0)
    return sparse.csr_matrix((vals_p, (rows_p, cols_p)), shape=(n, n))


def dc_lu_omega(rhs, rho, drho_x, drho_y, ccd, backend, h, N, tol, maxiter, pin_dof, omega):
    L_FD = build_fd_varrho_neumann(rho, drho_x, drho_y, h, N, pin_dof)
    p = np.zeros_like(rhs); residuals = []
    for k in range(maxiter):
        Lp = eval_LH(p, rho, drho_x, drho_y, ccd, backend)
        d = rhs - Lp; d.ravel()[pin_dof] = 0.0
        res = float(np.sqrt(np.dot(d.ravel(), d.ravel())))
        residuals.append(res)
        if res < tol: return p, residuals, k+1, "conv"
        if res > 1e20 or np.isnan(res): return p, residuals, k+1, "divg"
        if k >= 10 and residuals[-10] > 0 and res / residuals[-10] > 0.99:
            return p, residuals, k+1, "stag"
        dp = spsolve(L_FD, d.ravel()).reshape(rhs.shape)
        p = p + omega * dp; p.ravel()[pin_dof] = 0.0
    return p, residuals, maxiter, "stag"


def run_experiment():
    backend = Backend()
    omegas = [0.1, 0.2, 0.3, 0.5, 0.7, 0.83]
    density_ratios = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    grid_sizes = [32, 64]
    all_results = {}

    for N in grid_sizes:
        h = 1.0 / N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend); ccd = CCDSolver(grid, backend, bc_type="wall")
        xp = backend.xp; X, Y = grid.meshgrid()
        # DC loop uses scipy.sparse.spsolve (CPU-only); keep host copies for
        # FD assembly and spsolve; eval_LH routes CCD through device.
        X = backend.to_host(X); Y = backend.to_host(Y)
        p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
        pin_dof = (N//2)*(N+1)+(N//2)
        phi = np.sqrt((X-0.5)**2+(Y-0.5)**2) - 0.25; eps = 1.5*h

        print(f"\n  N={N}:")
        for rho_ratio in density_ratios:
            rho_g = 1.0 / rho_ratio
            H = smoothed_heaviside(phi, eps)
            rho = 1.0 + (rho_g - 1.0) * H
            drho_x_dev, _ = ccd.differentiate(xp.asarray(rho), 0)
            drho_y_dev, _ = ccd.differentiate(xp.asarray(rho), 1)
            drho_x = np.asarray(backend.to_host(drho_x_dev))
            drho_y = np.asarray(backend.to_host(drho_y_dev))
            rhs = eval_LH(p_exact, rho, drho_x, drho_y, ccd, backend)
            rhs.ravel()[pin_dof] = 0.0

            row = f"    rho={rho_ratio:>5}:"
            for omega in omegas:
                _, res_list, n_it, status = dc_lu_omega(
                    rhs, rho, drho_x, drho_y, ccd, backend,
                    h, N, 1e-8, 150, pin_dof, omega)
                sym = {"conv":"V","stag":"~","divg":"X"}[status]
                row += f" w={omega:.2f}:{n_it:>3}{sym}"
                key = f"N{N}_r{rho_ratio}_w{omega:.2f}"
                all_results[key] = {
                    "N": N, "rho_ratio": rho_ratio, "omega": omega,
                    "iters": n_it, "converged": int(status=="conv"),
                    "stagnated": int(status=="stag"),
                    "final_res": res_list[-1] if res_list else np.nan,
                    "residuals": np.array(res_list),
                }
            print(row)
    return all_results


def plot_results(all_results):
    import matplotlib.pyplot as plt
    omegas = sorted(set(v["omega"] for v in all_results.values()))
    density_ratios = sorted(set(v["rho_ratio"] for v in all_results.values()))
    grid_sizes = sorted(set(v["N"] for v in all_results.values()))

    for N in grid_sizes:
        fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        ax = axes[0]
        mat = np.full((len(omegas), len(density_ratios)), np.nan)
        conv_mat = np.zeros_like(mat, dtype=bool)
        stag_mat = np.zeros_like(mat, dtype=bool)
        for ri, rr in enumerate(density_ratios):
            for wi, w in enumerate(omegas):
                key = f"N{N}_r{rr}_w{w:.2f}"
                if key in all_results:
                    v = all_results[key]
                    mat[wi,ri] = v["iters"] if v["converged"] else np.nan
                    conv_mat[wi,ri] = bool(v["converged"])
                    stag_mat[wi,ri] = bool(v.get("stagnated",0))
        im = ax.imshow(mat, aspect="auto", origin="lower", cmap="viridis_r", vmin=1, vmax=150)
        for wi in range(len(omegas)):
            for ri in range(len(density_ratios)):
                if not conv_mat[wi,ri]:
                    sym = "~" if stag_mat[wi,ri] else "X"
                    ax.text(ri, wi, sym, ha="center", va="center", fontsize=8,
                            color="orange" if stag_mat[wi,ri] else "red")
        ax.set_xticks(range(len(density_ratios)))
        ax.set_xticklabels([str(r) for r in density_ratios], rotation=45, ha="right")
        ax.set_yticks(range(len(omegas)))
        ax.set_yticklabels([f"{w:.2f}" for w in omegas])
        ax.set_xlabel(r"$\rho_l/\rho_g$"); ax.set_ylabel(r"$\omega$")
        ax.set_title(f"Iterations ($N={N}$)")
        plt.colorbar(im, ax=ax, label="Iterations")

        ax2 = axes[1]
        selected = [(0.3, 1), (0.3, 100), (0.5, 1), (0.5, 100)]
        for ci, (w, rr) in enumerate(selected):
            key = f"N{N}_r{rr}_w{w:.2f}"
            if key not in all_results: continue
            v = all_results[key]; res = v["residuals"]
            ax2.semilogy(range(1,len(res)+1), res, color=COLORS[ci%len(COLORS)],
                         label=rf"$\omega={w}, \rho_l/\rho_g={rr}$")
        ax2.set_xlabel("Iteration"); ax2.set_ylabel("Residual")
        ax2.set_title(f"Residual history ($N={N}$)")
        ax2.legend(fontsize=7); ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        save_figure(fig, OUT / f"dc_omega_map_N{N}")


def main():
    args = experiment_argparser("[11-13] DC omega map").parse_args()
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
