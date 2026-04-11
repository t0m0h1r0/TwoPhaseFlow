#!/usr/bin/env python3
"""[11-14] Picard-DC: density-gradient splitting for high density ratios.

Idea:
  Split L_H p = (1/ρ)Δp - (1/ρ²)(∇ρ·∇p) = q into:
    Outer Picard: (1/ρ)Δp^{k+1} = q + (1/ρ²)(∇ρ · ∇p^{k})
    Inner DC+LU:  solve (1/ρ)Δ_CCD p = f  with ω-relaxation

  Inner problem has NO ∇ρ term → eigenvalue ratio [1, 2.4] regardless
  of density ratio → DC always converges with ω < 0.833.

  Outer Picard convergence depends on ‖A⁻¹B‖ where A=(1/ρ)Δ, B=(1/ρ²)(∇ρ·∇).

Test:
  Neumann BC, variable density PPE, p* = cos(πx)cos(πy),
  density_ratios=[1, 2, 5, 10, 50, 100, 1000],
  beta (outer relaxation)=[0.1, 0.3, 0.5, 0.7, 1.0],
  inner omega=0.5 (fixed), N=[32, 64].

Compare: standard DC+LU (exp11_13 baseline).
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
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


# ── CCD operators ──────────────────────────────────────────────────────────

def eval_LH_full(p, rho, drho_x, drho_y, ccd, backend):
    """Full L_H p = (1/ρ)Δp - (1/ρ²)(∇ρ·∇p)."""
    xp = backend.xp; p_dev = xp.asarray(p)
    dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


def eval_LH_laplacian(p, rho, ccd, backend):
    """Laplacian-only: (1/ρ)Δ_CCD p  (no ∇ρ·∇p term)."""
    xp = backend.xp; p_dev = xp.asarray(p)
    _, d2p_dx2 = ccd.differentiate(p_dev, 0)
    _, d2p_dy2 = ccd.differentiate(p_dev, 1)
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho


def eval_coupling(p, rho, drho_x, drho_y, ccd, backend):
    """Coupling term: (1/ρ²)(∇ρ·∇p) — moved to RHS in Picard."""
    xp = backend.xp; p_dev = xp.asarray(p)
    dp_dx, _ = ccd.differentiate(p_dev, 0)
    dp_dy, _ = ccd.differentiate(p_dev, 1)
    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))
    return (drho_x * dp_dx + drho_y * dp_dy) / rho**2


# ── FD matrices ────────────────────────────────────────────────────────────

def build_fd_laplacian_only(rho, h, N, pin_dof, backend):
    """FD for (1/ρ)Δp — NO ∇ρ terms."""
    nx = ny = N + 1; n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j; inv_rho = 1.0 / rho[i, j]; cc = 0.0
            for coord, lo, hi in [
                (i, (i - 1) * ny + j, (i + 1) * ny + j),
                (j, i * ny + (j - 1), i * ny + (j + 1)),
            ]:
                coeff = inv_rho / h**2
                coeff_bc = 2.0 * coeff
                if 0 < coord < N:
                    rows.append(k); cols.append(lo); vals.append(coeff); cc -= coeff
                    rows.append(k); cols.append(hi); vals.append(coeff); cc -= coeff
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
    return backend.sparse.csr_matrix((vals_p, (rows_p, cols_p)), shape=(n, n))


def build_fd_full(rho, drho_x, drho_y, h, N, pin_dof, backend):
    """FD for full (1/ρ)Δp - (1/ρ²)(∇ρ·∇p) — for baseline DC."""
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
    return backend.sparse.csr_matrix((vals_p, (rows_p, cols_p)), shape=(n, n))


# ── Solvers ────────────────────────────────────────────────────────────────

def dc_lu_baseline(rhs, rho, drho_x, drho_y, ccd, backend, h, N,
                   tol, maxiter, pin_dof, omega):
    """Standard DC+LU (exp11_13 baseline)."""
    spsolve = backend.sparse_linalg.spsolve
    L_FD = build_fd_full(rho, drho_x, drho_y, h, N, pin_dof, backend)
    p = np.zeros_like(rhs); residuals = []
    for k in range(maxiter):
        Lp = eval_LH_full(p, rho, drho_x, drho_y, ccd, backend)
        d = rhs - Lp; d.ravel()[pin_dof] = 0.0
        res = float(np.linalg.norm(d))
        residuals.append(res)
        if res < tol:
            return p, residuals, k + 1, "conv"
        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, "divg"
        if k >= 10 and residuals[-10] > 0 and res / residuals[-10] > 0.99:
            return p, residuals, k + 1, "stag"
        dp = np.asarray(backend.to_host(
            spsolve(L_FD, backend.xp.asarray(d.ravel()))
        )).reshape(rhs.shape)
        p = p + omega * dp; p.ravel()[pin_dof] = 0.0
    return p, residuals, maxiter, "stag"


def picard_dc(rhs, rho, drho_x, drho_y, ccd, backend, h, N,
              tol, outer_maxiter, inner_k, pin_dof, omega_inner, beta):
    """Picard-DC: outer Picard + inner DC+LU on (1/ρ)Δp = f.

    Parameters
    ----------
    inner_k : int
        Number of inner DC iterations per outer Picard step.
    omega_inner : float
        Relaxation for inner DC (eigenvalue ratio [1,2.4] → ω<0.833).
    beta : float
        Outer Picard under-relaxation (1.0 = no relaxation).
    """
    spsolve = backend.sparse_linalg.spsolve
    L_FD_lap = build_fd_laplacian_only(rho, h, N, pin_dof, backend)
    p = np.zeros_like(rhs)
    residuals = []
    total_evals = 0

    for outer in range(outer_maxiter):
        # Full residual check
        Lp = eval_LH_full(p, rho, drho_x, drho_y, ccd, backend)
        total_evals += 1
        d_full = rhs - Lp; d_full.ravel()[pin_dof] = 0.0
        res = float(np.linalg.norm(d_full))
        residuals.append(res)
        if res < tol:
            return p, residuals, total_evals, "conv"
        if res > 1e20 or np.isnan(res):
            return p, residuals, total_evals, "divg"
        if outer >= 10 and residuals[-10] > 0 and res / residuals[-10] > 0.99:
            return p, residuals, total_evals, "stag"

        # Picard: move coupling to RHS
        coupling = eval_coupling(p, rho, drho_x, drho_y, ccd, backend)
        total_evals += 1
        inner_rhs = rhs + coupling
        inner_rhs.ravel()[pin_dof] = 0.0

        # Inner DC solve: (1/ρ)Δ_CCD p_new = inner_rhs
        p_inner = p.copy()
        for _ in range(inner_k):
            Ap = eval_LH_laplacian(p_inner, rho, ccd, backend)
            total_evals += 1
            d_inner = inner_rhs - Ap; d_inner.ravel()[pin_dof] = 0.0
            dp = np.asarray(backend.to_host(
                spsolve(L_FD_lap, backend.xp.asarray(d_inner.ravel()))
            )).reshape(rhs.shape)
            p_inner = p_inner + omega_inner * dp
            p_inner.ravel()[pin_dof] = 0.0

        # Outer under-relaxation
        p = (1.0 - beta) * p + beta * p_inner
        p.ravel()[pin_dof] = 0.0

    return p, residuals, total_evals, "stag"


# ── Experiment ─────────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend()
    density_ratios = [1, 2, 5, 10, 50, 100, 1000]
    betas = [0.05, 0.1, 0.3, 0.5, 0.7, 1.0]
    grid_sizes = [32, 64]
    omega_inner = 0.5
    inner_k = 3  # DC k=3 per Picard step
    outer_maxiter = 200
    dc_maxiter = 300
    tol = 1e-8
    all_results = {}

    for N in grid_sizes:
        h = 1.0 / N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        xp = backend.xp
        X_dev, Y_dev = grid.meshgrid()
        X = np.asarray(backend.to_host(X_dev))
        Y = np.asarray(backend.to_host(Y_dev))
        p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
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
            rhs = eval_LH_full(p_exact, rho, drho_x, drho_y, ccd, backend)
            rhs.ravel()[pin_dof] = 0.0

            # ── Baseline: standard DC+LU ω=0.5 ──
            _, res_bl, evals_bl, st_bl = dc_lu_baseline(
                rhs, rho, drho_x, drho_y, ccd, backend,
                h, N, tol, dc_maxiter, pin_dof, omega=0.5)
            sym_bl = {"conv": "V", "stag": "~", "divg": "X"}[st_bl]
            all_results[f"N{N}_r{rho_ratio}_baseline"] = dict(
                N=N, rho_ratio=rho_ratio, method="baseline",
                beta=np.nan, evals=evals_bl, status=st_bl,
                final_res=res_bl[-1], residuals=np.array(res_bl))
            print(f"\n  rho={rho_ratio:>5}  baseline(w=0.5): {evals_bl:>4} evals {sym_bl}"
                  f"  res={res_bl[-1]:.2e}")

            # ── Picard-DC ──
            for beta in betas:
                _, res_pd, evals_pd, st_pd = picard_dc(
                    rhs, rho, drho_x, drho_y, ccd, backend,
                    h, N, tol, outer_maxiter, inner_k, pin_dof,
                    omega_inner, beta)
                sym_pd = {"conv": "V", "stag": "~", "divg": "X"}[st_pd]
                all_results[f"N{N}_r{rho_ratio}_b{beta:.2f}"] = dict(
                    N=N, rho_ratio=rho_ratio, method="picard_dc",
                    beta=beta, evals=evals_pd, status=st_pd,
                    final_res=res_pd[-1], residuals=np.array(res_pd))
                print(f"           picard(b={beta:.2f}): {evals_pd:>4} evals {sym_pd}"
                      f"  res={res_pd[-1]:.2e}")

    return all_results


def plot_results(all_results):
    import matplotlib.pyplot as plt

    density_ratios = sorted(set(v["rho_ratio"] for v in all_results.values()))
    grid_sizes = sorted(set(v["N"] for v in all_results.values()))
    betas = sorted(set(v["beta"] for v in all_results.values()
                       if v["method"] == "picard_dc"))

    for N in grid_sizes:
        # ── Fig 1: convergence map (beta vs density ratio) ──
        fig, ax = plt.subplots(figsize=(8, 5))
        mat = np.full((len(betas) + 1, len(density_ratios)), np.nan)
        labels = ["baseline"] + [f"$\\beta={b}$" for b in betas]

        for ri, rr in enumerate(density_ratios):
            key_bl = f"N{N}_r{rr}_baseline"
            if key_bl in all_results:
                v = all_results[key_bl]
                mat[0, ri] = v["evals"] if v["status"] == "conv" else np.nan

            for bi, beta in enumerate(betas):
                key = f"N{N}_r{rr}_b{beta:.2f}"
                if key in all_results:
                    v = all_results[key]
                    mat[bi + 1, ri] = v["evals"] if v["status"] == "conv" else np.nan

        im = ax.imshow(mat, aspect="auto", origin="lower", cmap="viridis_r",
                        vmin=1, vmax=500)
        for yi in range(mat.shape[0]):
            for xi in range(mat.shape[1]):
                rr = density_ratios[xi]
                if yi == 0:
                    key = f"N{N}_r{rr}_baseline"
                else:
                    key = f"N{N}_r{rr}_b{betas[yi-1]:.2f}"
                if key in all_results:
                    v = all_results[key]
                    if v["status"] != "conv":
                        sym = "~" if v["status"] == "stag" else "X"
                        ax.text(xi, yi, sym, ha="center", va="center",
                                fontsize=9, color="orange" if sym == "~" else "red")
                    else:
                        ax.text(xi, yi, str(v["evals"]), ha="center", va="center",
                                fontsize=7, color="white")
        ax.set_xticks(range(len(density_ratios)))
        ax.set_xticklabels([str(r) for r in density_ratios])
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlabel(r"$\rho_l/\rho_g$")
        ax.set_title(f"Picard-DC convergence map ($N={N}$, inner $k$=3, $\\omega$=0.5)")
        plt.colorbar(im, ax=ax, label="Total CCD evals")
        fig.tight_layout()
        save_figure(fig, OUT / f"picard_dc_map_N{N}")

        # ── Fig 2: residual histories at selected conditions ──
        fig2, axes = plt.subplots(1, 3, figsize=(14, 4.5))
        for ai, rr in enumerate([1, 10, 1000]):
            if ai >= len(axes):
                break
            ax2 = axes[ai]
            # Baseline
            key_bl = f"N{N}_r{rr}_baseline"
            if key_bl in all_results:
                v = all_results[key_bl]
                ax2.semilogy(v["residuals"], "k--", linewidth=2,
                             label=f"DC baseline ({v['status']})")
            # Picard-DC at selected betas
            for ci, beta in enumerate(betas):
                key = f"N{N}_r{rr}_b{beta:.2f}"
                if key not in all_results:
                    continue
                v = all_results[key]
                ax2.semilogy(v["residuals"], color=COLORS[ci % len(COLORS)],
                             label=rf"$\beta={beta}$ ({v['status']})")
            ax2.set_xlabel("Outer iteration")
            ax2.set_ylabel("$\\|q - L_H p\\|$")
            ax2.set_title(rf"$\rho_l/\rho_g = {rr}$, $N={N}$")
            ax2.legend(fontsize=6, ncol=2)
            ax2.grid(True, alpha=0.3)
            ax2.axhline(1e-8, color="gray", linestyle=":", linewidth=0.5)
        fig2.tight_layout()
        save_figure(fig2, OUT / f"picard_dc_residuals_N{N}")

    print(f"\nPlots saved to {OUT}")


def main():
    args = experiment_argparser("[11-14] Picard-DC density splitting").parse_args()
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
