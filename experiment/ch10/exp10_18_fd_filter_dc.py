#!/usr/bin/env python3
"""【10-18】FD-Helmholtz filter inside DC: stabilization experiment.

exp10_17 showed CCD filter FAILS: L_H (CCD BC) and L_FD (FD ghost-cell) have
different eigenvectors, so the filter theory breaks down and divergence worsens.

Fix: use (I − α L_FD)^{-1} as filter.
  - L_FD and (I − α L_FD) are polynomials of each other → same eigenvectors.
  - Filter theory is exact in the L_FD eigenbasis.
  - Nyquist convergence condition: 1.47 / (1 + 4α/h²) < 1 → α > 0.12 h².

Combined spectral radius at Nyquist (λ_H/λ_FD ≈ 2.47):
    |μ_combined| = |1 − λ_H/λ_FD| / (1 + α |λ_FD| / h²... wait, α * |λ_FD|)
    = 1.47 / (1 + 4α/h²)

For α = h²: 1.47/5 = 0.294 < 1  ✓
For α = 2h²: 1.47/9 = 0.163 < 1  ✓

Concern: fixed-point bias.  Fixed point satisfies (L_FD + α L_FD L_H) p* = L_FD q, i.e.
(I + α L_H) p* = q (if L_FD invertible), which is NOT L_H p* = q unless α = 0.
Actually: for the filter applied AFTER the DC update, fixed point analysis gives:
    (I − α L_FD) p* = p* + L_FD^{-1}(q − L_H p*) at fixed point
    ⟹  −α L_FD p* = L_FD^{-1}(q − L_H p*)
    ⟹  L_H p* = q + α L_FD² p*  ≠  L_H p* = q (biased).

So fixed α ≠ 0 introduces a bias proportional to α ‖L_FD‖² ‖p*‖ ~ O(α/h⁴).

Strategies:
  1. Fixed α = 0.5h² — convergent but biased
  2. Fixed α = h²   — stronger, more biased
  3. fade_10 / fade_50 — α fades to 0; may lose stability after fade

Grid: N = 16, 32, 64;  ρ_l/ρ_g = 1, 10, 100, 1000
maxiter = 1000

Paper ref: §8d, Appendix E.5
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__)

# (suffix, alpha_factor × h², fade_over_k)
VARIANTS = [
    ("no_filter", 0.0,  0),
    ("alpha_025", 0.25, 0),
    ("alpha_05",  0.5,  0),
    ("alpha_10",  1.0,  0),
    ("fade_10",   1.0,  200),
    ("fade_50",   1.0,  500),
]
VARIANT_LABELS = [
    "No filter",
    r"FD filter $\alpha=0.25h^2$",
    r"FD filter $\alpha=0.5h^2$",
    r"FD filter $\alpha=h^2$",
    r"FD filter $\alpha=h^2$ (fade k=200)",
    r"FD filter $\alpha=h^2$ (fade k=500)",
]


# ── Field helpers ─────────────────────────────────────────────────────────────

def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


def eval_LH(p, rho, drho_x, drho_y, ccd, backend):
    xp = backend.xp
    p_dev = xp.asarray(p)
    dp_dx,  d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy,  d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx   = np.asarray(backend.to_host(dp_dx))
    dp_dy   = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


# ── Matrix builders ───────────────────────────────────────────────────────────

def build_FD_sparse(N, h, rho, drho_x, drho_y, pin_dof):
    """2nd-order FD matrix for ∇·(1/ρ ∇) with Neumann BC + gauge pin."""
    ny = N + 1
    n_dof = (N + 1) ** 2
    h2 = h * h

    def idx(i, j):
        return i * ny + j

    rows, cols, vals = [], [], []
    for i in range(N + 1):
        for j in range(N + 1):
            k = idx(i, j)
            inv_rho = 1.0 / rho[i, j]
            cc = 0.0
            for coord, drho_ax, nb_lo, nb_hi in [
                (i, drho_x[i, j], idx(i - 1, j), idx(i + 1, j)),
                (j, drho_y[i, j], idx(i, j - 1), idx(i, j + 1)),
            ]:
                coeff_bc = 2.0 * inv_rho / h2
                if 0 < coord < N:
                    dr = drho_ax / rho[i, j] ** 2
                    cm = inv_rho / h2 + dr / (2 * h)
                    cp = inv_rho / h2 - dr / (2 * h)
                    rows += [k, k]; cols += [nb_lo, nb_hi]; vals += [cm, cp]
                    cc -= cm + cp
                elif coord == 0:
                    rows.append(k); cols.append(nb_hi); vals.append(coeff_bc)
                    cc -= coeff_bc
                else:
                    rows.append(k); cols.append(nb_lo); vals.append(coeff_bc)
                    cc -= coeff_bc
            rows.append(k); cols.append(k); vals.append(cc)

    mask = [r != pin_dof for r in rows]
    rows_p = [r for r, m in zip(rows, mask) if m] + [pin_dof]
    cols_p = [c for c, m in zip(cols, mask) if m] + [pin_dof]
    vals_p = [v for v, m in zip(vals, mask) if m] + [1.0]
    return sparse.csr_matrix((vals_p, (rows_p, cols_p)), shape=(n_dof, n_dof))


def build_fd_filter_lu(L_FD_raw, alpha, n_dof, pin_dof):
    """Factor F = (I − α L_FD) with pin row = identity.

    L_FD_raw: FD matrix WITHOUT pin constraint (pure Neumann).
    The pin row is replaced by identity so the filter fixes p[pin_dof] = 0.
    """
    I = sparse.eye(n_dof, format="lil")
    F = I - alpha * L_FD_raw.tolil()
    F[pin_dof, :] = 0.0
    F[pin_dof, pin_dof] = 1.0
    return splu(F.tocsr())


def build_FD_raw(N, h, rho, drho_x, drho_y):
    """FD matrix WITHOUT pin constraint (pure Neumann, singular)."""
    ny = N + 1
    n_dof = (N + 1) ** 2
    h2 = h * h

    def idx(i, j):
        return i * ny + j

    rows, cols, vals = [], [], []
    for i in range(N + 1):
        for j in range(N + 1):
            k = idx(i, j)
            inv_rho = 1.0 / rho[i, j]
            cc = 0.0
            for coord, drho_ax, nb_lo, nb_hi in [
                (i, drho_x[i, j], idx(i - 1, j), idx(i + 1, j)),
                (j, drho_y[i, j], idx(i, j - 1), idx(i, j + 1)),
            ]:
                coeff_bc = 2.0 * inv_rho / h2
                if 0 < coord < N:
                    dr = drho_ax / rho[i, j] ** 2
                    cm = inv_rho / h2 + dr / (2 * h)
                    cp = inv_rho / h2 - dr / (2 * h)
                    rows += [k, k]; cols += [nb_lo, nb_hi]; vals += [cm, cp]
                    cc -= cm + cp
                elif coord == 0:
                    rows.append(k); cols.append(nb_hi); vals.append(coeff_bc)
                    cc -= coeff_bc
                else:
                    rows.append(k); cols.append(nb_lo); vals.append(coeff_bc)
                    cc -= coeff_bc
            rows.append(k); cols.append(k); vals.append(cc)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n_dof, n_dof))


# ── DC + LU solver with FD filter ─────────────────────────────────────────────

def dc_lu_fd_filter(rhs, rho, drho_x, drho_y, ccd, backend,
                    LU_FD, filter_lus,
                    alpha_factor, h, fade_k,
                    shape, tol, maxiter, pin_dof):
    """DC + LU with optional FD-Helmholtz filter (I − α L_FD)^{-1} after each step."""
    p = np.zeros(shape, dtype=float)
    residuals = []
    alpha0 = alpha_factor * h ** 2

    for k in range(maxiter):
        Lp = eval_LH(p, rho, drho_x, drho_y, ccd, backend)
        d = rhs - Lp
        d.ravel()[pin_dof] = 0.0

        res = float(np.linalg.norm(d.ravel()))
        residuals.append(res)

        if res < tol:
            return p, residuals, k + 1, True
        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, False

        # DC step: L_FD dp = d,  p ← p + dp
        dp = LU_FD.solve(d.ravel()).reshape(shape)
        p = p + dp
        p.ravel()[pin_dof] = 0.0

        # FD filter: (I − α L_FD) p_new = p_old
        if alpha0 > 0.0:
            alpha = alpha0 * (max(0.0, 1.0 - k / fade_k) if fade_k > 0 else 1.0)
            if alpha > 1e-15:
                flu = filter_lus[alpha_factor]
                p = flu.solve(p.ravel()).reshape(shape)
                p.ravel()[pin_dof] = 0.0

    return p, residuals, maxiter, False


# ── Experiment ────────────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend(use_gpu=False)

    density_ratios = [1, 10, 100, 1000]
    grid_sizes = [16, 32, 64]
    tol = 1e-10
    maxiter = 1000

    all_results = {}

    for N in grid_sizes:
        h = 1.0 / N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        xp = backend.xp
        n_dof = (N + 1) ** 2

        X, Y = grid.meshgrid()
        p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
        pin_dof = (N // 2) * (N + 1) + (N // 2)

        phi = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - 0.25
        eps = 1.5 * h

        for rho_ratio in density_ratios:
            rho = 1.0 + (1.0 / rho_ratio - 1.0) * smoothed_heaviside(phi, eps)

            drho_x_dev, _ = ccd.differentiate(xp.asarray(rho), 0)
            drho_y_dev, _ = ccd.differentiate(xp.asarray(rho), 1)
            drho_x = np.asarray(backend.to_host(drho_x_dev))
            drho_y = np.asarray(backend.to_host(drho_y_dev))

            rhs = eval_LH(p_exact, rho, drho_x, drho_y, ccd, backend)
            rhs.ravel()[pin_dof] = 0.0

            print(f"\nN={N}, ρ_l/ρ_g={rho_ratio}")

            # Build pinned FD matrix (for DC solve)
            L_FD = build_FD_sparse(N, h, rho, drho_x, drho_y, pin_dof)
            LU_FD = splu(L_FD)

            # Build raw FD (for filter construction: needs pure Neumann, then pin row fixed)
            L_FD_raw = build_FD_raw(N, h, rho, drho_x, drho_y)

            # Pre-factor FD filter matrices
            alpha_factors = sorted({af for _, af, _ in VARIANTS if af > 0})
            filter_lus = {}
            for af in alpha_factors:
                alpha = af * h ** 2
                filter_lus[af] = build_fd_filter_lu(L_FD_raw, alpha, n_dof, pin_dof)
            print(f"  FD filter LU ready: α/h² ∈ {alpha_factors}")

            shape = (N + 1, N + 1)
            print(f"  {'Solver':30s}  {'iters':>5}  {'residual':>10}  {'err_inf':>10}  status")
            print("  " + "-" * 72)

            for suffix, af, fade_k in VARIANTS:
                p_sol, res_hist, n_iter, converged = dc_lu_fd_filter(
                    rhs, rho, drho_x, drho_y, ccd, backend,
                    LU_FD, filter_lus,
                    af, h, fade_k,
                    shape, tol, maxiter, pin_dof,
                )
                err_inf = float(np.max(np.abs(p_sol - p_exact)))
                final_res = float(res_hist[-1])
                status = "OK" if converged else ("DIV" if final_res > 1e15 else "STALL")
                print(f"  {suffix:30s}  {n_iter:>5}  {final_res:>10.2e}  {err_inf:>10.2e}  {status}")

                key = f"N{N}_r{rho_ratio}_{suffix}"
                all_results[key] = {
                    "N": N,
                    "rho_ratio": rho_ratio,
                    "n_iter": n_iter,
                    "converged": int(converged),
                    "final_res": final_res,
                    "final_err": err_inf,
                    "residuals": np.array(res_hist),
                }

    return all_results


# ── Plot ──────────────────────────────────────────────────────────────────────

def plot_results(all_results):
    import matplotlib.pyplot as plt

    grid_sizes = sorted({v["N"] for v in all_results.values()})
    density_ratios = sorted({v["rho_ratio"] for v in all_results.values()})
    suffixes = [s for s, _, _ in VARIANTS]
    styles = ["-", "-", "-", "-", "--", ":"]

    # (a) Residual history: ρ=1 and ρ=1000 for each N
    for N in grid_sizes:
        fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)
        for ax, rr in zip(axes, [1, 1000]):
            for ci, (suf, label, ls) in enumerate(
                    zip(suffixes, VARIANT_LABELS, styles)):
                key = f"N{N}_r{rr}_{suf}"
                if key not in all_results:
                    continue
                res = all_results[key]["residuals"]
                ax.semilogy(range(1, len(res) + 1), res,
                            ls, color=COLORS[ci % len(COLORS)],
                            label=label, linewidth=1.4)
            ax.set_xlabel("Iteration")
            ax.set_ylabel(r"$\|q - L_H p\|_2$")
            ax.set_title(rf"FD filter, $N={N}$, $\rho_l/\rho_g={rr}$")
            ax.legend(fontsize=7)
            ax.grid(True, which="both", alpha=0.3)
        fig.tight_layout()
        save_figure(fig, OUT / f"residual_N{N}")

    # (b) Final solution error bar chart
    for N in grid_sizes:
        fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
        x = np.arange(len(density_ratios))
        n_var = len(VARIANTS)
        width = 0.8 / n_var
        for si, (suf, label) in enumerate(zip(suffixes, VARIANT_LABELS)):
            errs = [all_results.get(f"N{N}_r{rr}_{suf}", {}).get("final_err", np.nan)
                    for rr in density_ratios]
            ax.bar(x + si * width, errs, width, label=label,
                   color=COLORS[si % len(COLORS)])
        ax.set_yscale("log")
        ax.set_xticks(x + width * (n_var / 2 - 0.5))
        ax.set_xticklabels([str(r) for r in density_ratios])
        ax.set_xlabel(r"$\rho_l / \rho_g$")
        ax.set_ylabel(r"$\|p - p^*\|_\infty$")
        ax.set_title(f"FD filter: solution error ($N={N}$)")
        ax.legend(fontsize=7)
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        save_figure(fig, OUT / f"error_N{N}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser(
        "FD-Helmholtz filter inside DC: stabilization experiment"
    ).parse_args()

    if args.plot_only:
        plot_results(load_results(OUT / "data.npz"))
        return

    print("\n" + "=" * 70)
    print("  【10-18】FD-Helmholtz Filter Inside DC Loop")
    print("=" * 70)

    all_results = run_experiment()
    save_results(OUT / "data.npz", all_results)
    plot_results(all_results)
    print(f"\nResults → {OUT}")


if __name__ == "__main__":
    main()
