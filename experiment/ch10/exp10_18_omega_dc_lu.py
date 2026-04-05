#!/usr/bin/env python3
"""【10-18】DC + LU with ω 緩和: 密度比 vs ω 収束マップ.

Paper ref: §8d (defect correction)
Motivation: exp10_16 で DC+LU (ω=1) が発散を確認。
            理論解析: ω_max = 2/r_max = 2/2.4 = 0.833。
            ω ∈ (0, 0.833) で DC+LU は収束するはず。

Problem: 同 exp10_16。

Solver: DC + sparse LU (spsolve) with ω-relaxation
  p ← p + ω L_FD^{-1} (q − L_H p)
  L_FD: Neumann BC 可変密度 FD Laplacian (exp10_16 と同じ行列)

Sweep:
  ω = 0.1, 0.2, 0.3, 0.5, 0.7, 0.83
  ρ_l/ρ_g = 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000
  N = 32, 64
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
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


# ── Smoothed Heaviside ───────────────────────────────────────────────────────

def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


# ── CCD variable-density Laplacian (O(h⁶)) ─────────────────────────────────

def eval_LH(p, rho, drho_x, drho_y, ccd, backend):
    xp = backend.xp
    p_dev = xp.asarray(p)
    dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx   = np.asarray(backend.to_host(dp_dx))
    dp_dy   = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


# ── FD Laplacian (Neumann BC, variable density) ──────────────────────────────

def build_fd_laplacian(rho, drho_x, drho_y, h, N, pin_dof):
    """可変密度 FD Laplacian (Neumann BC) + ゲージピン."""
    nx, ny = N + 1, N + 1
    n_dof = nx * ny
    h2 = h * h

    def idx(i, j):
        return i * ny + j

    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)
            inv_rho     = 1.0 / rho[i, j]
            inv_rho_sq  = inv_rho * inv_rho
            cc = 0.0

            for coord, drho_ax, nb_lo, nb_hi in [
                (i, drho_x[i, j], idx(i-1, j), idx(i+1, j)),
                (j, drho_y[i, j], idx(i, j-1), idx(i, j+1)),
            ]:
                coeff_bc = 2.0 * inv_rho / h2
                if 0 < coord < N:
                    dr = drho_ax * inv_rho_sq
                    cm = inv_rho / h2 + dr / (2*h)
                    cp = inv_rho / h2 - dr / (2*h)
                    rows.append(k); cols.append(nb_lo); vals.append(cm); cc -= cm
                    rows.append(k); cols.append(nb_hi); vals.append(cp); cc -= cp
                elif coord == 0:
                    rows.append(k); cols.append(nb_hi); vals.append(coeff_bc); cc -= coeff_bc
                else:
                    rows.append(k); cols.append(nb_lo); vals.append(coeff_bc); cc -= coeff_bc

            rows.append(k); cols.append(k); vals.append(cc)

    # Gauge pin in COO
    pin_mask = [r != pin_dof for r in rows]
    rows_p = [r for r, m in zip(rows, pin_mask) if m]
    cols_p = [c for c, m in zip(cols, pin_mask) if m]
    vals_p = [v for v, m in zip(vals, pin_mask) if m]
    rows_p.append(pin_dof); cols_p.append(pin_dof); vals_p.append(1.0)
    return sparse.csr_matrix((vals_p, (rows_p, cols_p)), shape=(n_dof, n_dof))


# ── DC + LU with ω relaxation ─────────────────────────────────────────────

def dc_lu_omega_solve(rhs, rho, drho_x, drho_y, ccd, backend,
                      h, N, tol, maxiter, pin_dof, omega):
    """DC + direct LU with ω-relaxation.

    p ← p + ω L_FD^{-1} (q − L_H p)
    収束条件: ω < 2 / max_k(λ_H/λ_FD) = 0.833
    """
    L_FD = build_fd_laplacian(rho, drho_x, drho_y, h, N, pin_dof)

    shape = rhs.shape
    p = np.zeros(shape, dtype=float)
    residuals = []

    for k in range(maxiter):
        Lp = eval_LH(p, rho, drho_x, drho_y, ccd, backend)
        d  = rhs - Lp
        d.ravel()[pin_dof] = 0.0

        d_flat = d.ravel().copy()
        res = float(np.sqrt(np.dot(d_flat, d_flat)))
        residuals.append(res)

        if res < tol:
            return p, residuals, k + 1, True
        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, False

        dp = spsolve(L_FD, d_flat).reshape(shape)
        p = p + omega * dp
        p.ravel()[pin_dof] = 0.0

    return p, residuals, maxiter, False


# ── Experiment ───────────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend(use_gpu=False)

    omegas         = [0.1, 0.2, 0.3, 0.5, 0.7, 0.83]
    density_ratios = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    grid_sizes     = [32, 64]
    tol     = 1e-8
    maxiter = 300

    all_results = {}

    for N in grid_sizes:
        h  = 1.0 / N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd  = CCDSolver(grid, backend, bc_type="wall")
        xp   = backend.xp

        X, Y = grid.meshgrid()
        p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
        pin_dof = (N // 2) * (N + 1) + (N // 2)

        phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
        eps = 1.5 * h

        print(f"\n{'='*80}")
        print(f"  N={N}")
        print(f"{'='*80}")
        hdr = f"  {'ρ_l/ρ_g':>8}" + "".join(f"  ω={w:.2f}(it)" for w in omegas)
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))

        for rho_ratio in density_ratios:
            rho_g = 1.0 / rho_ratio
            H     = smoothed_heaviside(phi, eps)
            rho   = 1.0 + (rho_g - 1.0) * H

            drho_x_dev, _ = ccd.differentiate(xp.asarray(rho), 0)
            drho_y_dev, _ = ccd.differentiate(xp.asarray(rho), 1)
            drho_x = np.asarray(backend.to_host(drho_x_dev))
            drho_y = np.asarray(backend.to_host(drho_y_dev))

            rhs = eval_LH(p_exact, rho, drho_x, drho_y, ccd, backend)
            rhs.ravel()[pin_dof] = 0.0

            row = f"  {rho_ratio:>8}"
            for omega in omegas:
                p_sol, res_list, n_it, conv = dc_lu_omega_solve(
                    rhs, rho, drho_x, drho_y, ccd, backend,
                    h, N, tol, maxiter, pin_dof, omega,
                )
                tag = f"{n_it:3d}{'✓' if conv else '✗'}"
                row += f"  {tag:>9}"

                key = f"N{N}_r{rho_ratio}_w{omega:.2f}"
                all_results[key] = {
                    "N": N, "h": h, "rho_ratio": rho_ratio, "omega": omega,
                    "iters":      n_it,
                    "converged":  int(conv),
                    "final_res":  res_list[-1] if res_list else np.nan,
                    "residuals":  np.array(res_list),
                }
            print(row)

    return all_results


# ── Plot ─────────────────────────────────────────────────────────────────────

def plot_results(all_results):
    import matplotlib.pyplot as plt

    omegas         = sorted(set(v["omega"]       for v in all_results.values()))
    density_ratios = sorted(set(v["rho_ratio"]   for v in all_results.values()))
    grid_sizes     = sorted(set(v["N"]           for v in all_results.values()))

    # (a) Convergence map: iterations heatmap (N=32)
    for N in grid_sizes:
        fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

        # Left: iteration count
        ax = axes[0]
        mat_iters = np.full((len(omegas), len(density_ratios)), np.nan)
        mat_conv  = np.zeros((len(omegas), len(density_ratios)), dtype=bool)
        for ri, rr in enumerate(density_ratios):
            for wi, w in enumerate(omegas):
                key = f"N{N}_r{rr}_w{w:.2f}"
                if key in all_results:
                    v = all_results[key]
                    mat_iters[wi, ri] = v["iters"] if v["converged"] else np.nan
                    mat_conv[wi, ri]  = bool(v["converged"])

        im = ax.imshow(mat_iters, aspect="auto", origin="lower",
                       cmap="viridis_r", vmin=1, vmax=300)
        # Mark non-converged
        for wi in range(len(omegas)):
            for ri in range(len(density_ratios)):
                if not mat_conv[wi, ri]:
                    ax.text(ri, wi, "✗", ha="center", va="center",
                            fontsize=9, color="red")

        ax.set_xticks(range(len(density_ratios)))
        ax.set_xticklabels([str(r) for r in density_ratios], rotation=45, ha="right")
        ax.set_yticks(range(len(omegas)))
        ax.set_yticklabels([f"{w:.2f}" for w in omegas])
        ax.set_xlabel(r"$\rho_l / \rho_g$")
        ax.set_ylabel(r"$\omega$")
        ax.set_title(f"Iterations to convergence ($N={N}$)")
        plt.colorbar(im, ax=ax, label="Iterations")

        # Right: residual history for selected cases
        ax2 = axes[1]
        selected = [(0.3, 1), (0.3, 100), (0.5, 1), (0.5, 100)]
        for ci, (w, rr) in enumerate(selected):
            key = f"N{N}_r{rr}_w{w:.2f}"
            if key not in all_results:
                continue
            v = all_results[key]
            res = v["residuals"]
            style = "-" if v["converged"] else "--"
            ax2.semilogy(range(1, len(res)+1), res, style,
                         color=COLORS[ci % len(COLORS)],
                         label=rf"$\omega={w}, \rho_l/\rho_g={rr}$")
        ax2.set_xlabel("Iteration")
        ax2.set_ylabel("Residual (RMS)")
        ax2.set_title(f"Residual history ($N={N}$)")
        ax2.legend(fontsize=8)
        ax2.grid(True, which="both", alpha=0.3)

        fig.tight_layout()
        save_figure(fig, OUT / f"omega_convergence_map_N{N}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser("DC+LU omega sweep vs density ratio").parse_args()

    if args.plot_only:
        results = load_results(OUT / "data.npz")
        plot_results(results)
        return

    print("\n" + "=" * 80)
    print("  【10-18】DC + LU with ω 緩和: 密度比 vs ω 収束マップ")
    print("=" * 80)

    all_results = run_experiment()
    save_results(OUT / "data.npz", all_results)
    plot_results(all_results)

    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
