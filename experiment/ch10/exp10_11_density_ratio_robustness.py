#!/usr/bin/env python3
"""【10-11】High density ratio PPE solver robustness.

Paper ref: §8.5 (condition number κ = O(ρ_l/ρ_g · h⁻²)),
           §8.3 (defect correction with LTS, eq:dtau_lts)

Tests:
  Variable-density Poisson ∇·((1/ρ)∇p) = f on [0,1]², Dirichlet BC.
  Circular interface (R=0.25, smoothed Heaviside).
  ρ_l/ρ_g = 1, 10, 100, 1000.

Compare:
  (A) Defect correction with uniform Δτ (global optimal)
  (B) Defect correction with LTS Δτ_ij ∝ ρ_ij (density-adaptive)

Metrics: iteration count to ε_tol, residual decay history.
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

OUT = pathlib.Path(__file__).resolve().parent / "results" / "density_ratio"
OUT.mkdir(parents=True, exist_ok=True)


# ── Variable-density operators ───────────────────────────────────────────────

def eval_LH_varrho(p, rho, drho_x, drho_y, ccd, backend):
    """L_H p = ∇·((1/ρ)∇p) via CCD (O(h⁶)), variable density."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    rho_dev = xp.asarray(rho)

    dp_dx, d2p_dx2 = ccd.differentiate(p_dev, axis=0)
    dp_dy, d2p_dy2 = ccd.differentiate(p_dev, axis=1)

    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))

    Lp = (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2
    return Lp


def build_fd_laplacian_varrho(Nx, Ny, hx, hy, rho, drho_x, drho_y):
    """2D FD variable-density Laplacian ∇·((1/ρ)∇p), Dirichlet BC.

    Interior: (1/ρ)(p[i-1]-2p[i]+p[i+1])/h² - (ρ_x/ρ²)(p[i+1]-p[i-1])/(2h) + y-terms
    """
    nx, ny = Nx + 1, Ny + 1
    n = nx * ny

    def idx(i, j):
        return i * ny + j

    rows, cols, vals = [], [], []

    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)
            if i == 0 or i == Nx or j == 0 or j == Ny:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                inv_rho = 1.0 / rho[i, j]
                drx = drho_x[i, j] / rho[i, j]**2
                dry = drho_y[i, j] / rho[i, j]**2

                # x-direction: (1/ρ)(p[i±1,j])/hx² ∓ (ρ_x/ρ²)/(2hx)
                cx_m = inv_rho / hx**2 + drx / (2*hx)   # p[i-1,j]
                cx_p = inv_rho / hx**2 - drx / (2*hx)   # p[i+1,j]
                # y-direction
                cy_m = inv_rho / hy**2 + dry / (2*hy)   # p[i,j-1]
                cy_p = inv_rho / hy**2 - dry / (2*hy)   # p[i,j+1]
                # center
                cc = -2.0 * inv_rho / hx**2 - 2.0 * inv_rho / hy**2

                rows.append(k); cols.append(idx(i-1, j)); vals.append(cx_m)
                rows.append(k); cols.append(idx(i+1, j)); vals.append(cx_p)
                rows.append(k); cols.append(idx(i, j-1)); vals.append(cy_m)
                rows.append(k); cols.append(idx(i, j+1)); vals.append(cy_p)
                rows.append(k); cols.append(k);            vals.append(cc)

    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


# ── Defect correction with variable density ──────────────────────────────────

def dc_solve_varrho(rhs, rho, drho_x, drho_y, ccd, backend, L_L, tol, maxiter,
                    omega=0.3):
    """Defect correction for variable-density PPE with relaxation.

    Algorithm (eq:dc_three_step):
      d^(k) = b - L_H p^(k)
      L_L δp = d^(k)
      p^(k+1) = p^(k) + ω δp

    Returns (p, residuals, n_iter).
    """
    p = np.zeros_like(rhs)
    residuals = []

    for k in range(maxiter):
        Lp = eval_LH_varrho(p, rho, drho_x, drho_y, ccd, backend)
        d = rhs - Lp
        d[0, :] = 0.0; d[-1, :] = 0.0; d[:, 0] = 0.0; d[:, -1] = 0.0

        res = float(np.sqrt(np.mean(d**2)))
        residuals.append(res)
        if res < tol:
            return p, residuals, k + 1

        dp = spsolve(L_L, d.ravel()).reshape(rhs.shape)
        p = p + omega * dp
        p[0, :] = 0.0; p[-1, :] = 0.0; p[:, 0] = 0.0; p[:, -1] = 0.0

    return p, residuals, maxiter


# ── Experiment ───────────────────────────────────────────────────────────────

def run_density_ratio_test(N=64, tol=1e-10, maxiter=100):
    backend = Backend(use_gpu=False)
    h = 1.0 / N

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    xp = backend.xp

    X, Y = grid.meshgrid()

    # Manufactured solution
    p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)

    # Circle interface (R=0.25, center 0.5,0.5)
    R = 0.25
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    eps = 1.5 * h

    density_ratios = [1, 10, 100, 1000]
    omega = 0.3  # relaxation (§app:dc_convergence_theory, eq:dc_omega_opt)
    results = {}

    print(f"  N={N}, h={h:.4f}, ω={omega}, ε_tol={tol}, maxiter={maxiter}")
    print(f"\n  {'ρ_l/ρ_g':>8} | {'κ(est)':>12} | {'DC iters':>10} | {'final res':>12} | {'L∞ err':>12} | {'ρ(M)':>6}")
    print("  " + "-" * 80)

    for rho_ratio in density_ratios:
        rho_l = 1.0
        rho_g = 1.0 / rho_ratio

        # Smoothed Heaviside density
        H = 0.5 * (1.0 + np.tanh(phi / (2 * eps)))
        rho = rho_l + (rho_g - rho_l) * H

        # Density gradients (CCD, frozen)
        drho_x_dev, _ = ccd.differentiate(xp.asarray(rho), axis=0)
        drho_y_dev, _ = ccd.differentiate(xp.asarray(rho), axis=1)
        drho_x = np.asarray(backend.to_host(drho_x_dev))
        drho_y = np.asarray(backend.to_host(drho_y_dev))

        # RHS: compute L_H(p_exact) so that the exact solution is known
        rhs = eval_LH_varrho(p_exact, rho, drho_x, drho_y, ccd, backend)
        rhs[0, :] = 0.0; rhs[-1, :] = 0.0; rhs[:, 0] = 0.0; rhs[:, -1] = 0.0

        # Build FD Laplacian (L_L) with variable density
        L_L = build_fd_laplacian_varrho(N, N, h, h, rho, drho_x, drho_y)

        # Estimated condition number
        kappa_est = rho_ratio / h**2

        # Defect correction with relaxation ω
        p_dc, res_hist, n_iter = dc_solve_varrho(
            rhs, rho, drho_x, drho_y, ccd, backend, L_L, tol, maxiter,
            omega=omega)

        err_Li = float(np.max(np.abs(p_dc - p_exact)))
        final_res = res_hist[-1] if res_hist else float("nan")

        # Spectral radius estimate (geometric mean of last ratios)
        if len(res_hist) >= 6:
            rates = [res_hist[i+1]/res_hist[i] for i in range(max(1, len(res_hist)-6), len(res_hist)-1)
                     if res_hist[i] > 0]
            rho_M = np.exp(np.mean(np.log([r for r in rates if r > 0]))) if rates else float("nan")
        else:
            rho_M = float("nan")

        results[rho_ratio] = {
            "n_iter": n_iter, "err_Li": err_Li, "final_res": final_res,
            "kappa_est": kappa_est, "rho_M": rho_M, "residuals": res_hist,
            "omega": omega,
        }

        rho_str = f"{rho_M:.3f}" if not np.isnan(rho_M) else "---"
        print(f"  {rho_ratio:>8} | {kappa_est:>12.0f} | {n_iter:>10} | "
              f"{final_res:>12.3e} | {err_Li:>12.3e} | {rho_str:>6}")

    return results


def save_latex_table(results):
    with open(OUT / "table_density_ratio.tex", "w") as fp:
        fp.write("% Auto-generated by exp10_11_density_ratio_robustness.py\n")
        fp.write("\\begin{tabular}{rrrrc}\n\\toprule\n")
        fp.write("$\\rho_l/\\rho_g$ & $\\kappa$(推定) & 反復回数 & $L^\\infty$ 誤差 & $\\rho(M)$ \\\\\n")
        fp.write("\\midrule\n")
        for rr in sorted(results.keys()):
            r = results[rr]
            rho_str = f"${r['rho_M']:.3f}$" if not np.isnan(r['rho_M']) else "---"
            fp.write(f"${rr}$ & ${r['kappa_est']:.0f}$ & ${r['n_iter']}$ & "
                     f"${r['err_Li']:.2e}$ & {rho_str} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_density_ratio.tex'}")


def save_plot(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # (a) Residual history
    ax = axes[0]
    for rr in sorted(results.keys()):
        r = results[rr]
        ax.semilogy(range(1, len(r["residuals"])+1), r["residuals"],
                    "-", label=f"$\\rho_l/\\rho_g={rr}$")
    ax.set_xlabel("Iteration $k$")
    ax.set_ylabel("Residual $\\|d^{(k)}\\|_2$")
    ax.set_title("(a) DC residual decay vs density ratio")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)

    # (b) Iterations vs density ratio
    ax = axes[1]
    ratios = sorted(results.keys())
    iters = [results[rr]["n_iter"] for rr in ratios]
    ax.semilogx(ratios, iters, "o-", markersize=8)
    ax.set_xlabel("$\\rho_l/\\rho_g$")
    ax.set_ylabel("Iterations to $\\varepsilon_{\\mathrm{tol}}$")
    ax.set_title("(b) Iteration count vs density ratio")
    ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT / "density_ratio_robustness.eps", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'density_ratio_robustness.eps'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-11】High Density Ratio PPE Solver Robustness")
    print("=" * 80 + "\n")

    results = run_density_ratio_test(N=64, tol=1e-10, maxiter=100)
    save_latex_table(results)
    save_plot(results)

    # Save without residual histories (too large for npz)
    summary = {rr: {k: v for k, v in r.items() if k != "residuals"}
               for rr, r in results.items()}
    np.savez(OUT / "density_ratio_data.npz", summary=summary)
    # Save residuals separately for --plot-only
    np.savez(OUT / "density_ratio_residuals.npz",
             **{f"res_{rr}": np.array(r["residuals"]) for rr, r in results.items()},
             ratios=np.array(sorted(results.keys())))
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "density_ratio_data.npz", allow_pickle=True)
        _dr = np.load(OUT / "density_ratio_residuals.npz", allow_pickle=True)
        _summary = _d["summary"].item()
        _ratios = list(_dr["ratios"])
        for _rr in _ratios:
            _summary[_rr]["residuals"] = list(_dr[f"res_{_rr}"])
        save_plot(_summary)
    else:
        main()
