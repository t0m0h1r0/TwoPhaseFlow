#!/usr/bin/env python3
"""【10-19】Ghost-cell BC alignment: CCD filter with consistent Neumann BC.

exp10_17 failure root cause:
    CCD uses 4-point one-sided compact BC (O(h⁵)) at walls.
    FD  uses ghost-cell reflection p[-1]=p[1] (O(h²)) at walls.
    Different BC → different eigenvectors → CCD filter amplifies wrong modes.

Fix (user suggestion): make L_H use the same ghost-cell BC as L_FD.
    After CCD differentiation, override boundary rows:
        dp/dx|_wall  = 0
        d²p/dx²|_wall = 2(p[1]-p[0])/h²    (ghost-cell)
    This gives L_H = L_FD exactly at boundary nodes → shared eigenvectors.

With consistent BC, the CCD filter theory should hold:
    |μ_combined| = |1 − λ_H/λ_FD| / (1 + α|λ_H|) < 1  for α > ~0.12 h²

Caveat: ghost-cell BC reduces CCD accuracy to O(h²) AT boundary nodes.
Interior nodes keep full CCD O(h⁶) accuracy.

Solvers:
  baseline  — DC + LU, CCD BC (original, exp10_16/17 behavior)
  fd_filter — DC + LU + FD filter (exp10_18, best previous result)
  ghost_fix — DC + LU, ghost-cell L_H (no filter, just BC-aligned DC)
  ghost_ccd_filter_α — DC + LU + CCD filter using ghost-cell L_H

Grid: N = 16, 32;  ρ_l/ρ_g = 1, 10, 100, 1000
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


# ── CCD L_H evaluators ────────────────────────────────────────────────────────

def eval_LH_ccd_bc(p, rho, drho_x, drho_y, ccd, backend):
    """Original: CCD one-sided compact BC at walls."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    dp_dx,  d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy,  d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx   = np.asarray(backend.to_host(dp_dx))
    dp_dy   = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


def eval_LH_ghost_bc(p, rho, drho_x, drho_y, ccd, backend, h):
    """Ghost-cell Neumann BC at walls — consistent with FD ghost-cell."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    dp_dx,  d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy,  d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx   = np.asarray(backend.to_host(dp_dx))
    dp_dy   = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))

    h2 = h * h
    # Override boundary rows with ghost-cell values: f'=0, f''=2(f₁−f₀)/h²
    dp_dx[0, :]    = 0.0;  d2p_dx2[0, :]  = 2.0 * (p[1, :]  - p[0, :])  / h2
    dp_dx[-1, :]   = 0.0;  d2p_dx2[-1, :] = 2.0 * (p[-2, :] - p[-1, :]) / h2
    dp_dy[:, 0]    = 0.0;  d2p_dy2[:, 0]  = 2.0 * (p[:, 1]  - p[:, 0])  / h2
    dp_dy[:, -1]   = 0.0;  d2p_dy2[:, -1] = 2.0 * (p[:, -2] - p[:, -1]) / h2

    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


# ── Matrix builders ───────────────────────────────────────────────────────────

def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


def build_FD_sparse(N, h, rho, drho_x, drho_y, pin_dof):
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


def build_LH_sparse(N, h, rho, drho_x, drho_y, ccd, backend, pin_dof,
                    use_ghost_bc=False):
    """Build L_H via column-by-column eval_LH calls.

    use_ghost_bc=True: override boundary rows with ghost-cell Neumann (FD-consistent).
    use_ghost_bc=False: use CCD's own one-sided compact BC.
    """
    n_dof = (N + 1) ** 2
    r_list, c_list, v_list = [], [], []
    e = np.zeros(n_dof, dtype=float)
    for j in range(n_dof):
        e[j] = 1.0
        p_j = e.reshape(N + 1, N + 1)
        if use_ghost_bc:
            lp = eval_LH_ghost_bc(p_j, rho, drho_x, drho_y, ccd, backend, h).ravel()
        else:
            lp = eval_LH_ccd_bc(p_j, rho, drho_x, drho_y, ccd, backend).ravel()
        lp[pin_dof] = 0.0
        nz = np.where(np.abs(lp) > 1e-14)[0]
        r_list.extend(nz.tolist())
        c_list.extend([j] * len(nz))
        v_list.extend(lp[nz].tolist())
        e[j] = 0.0
        if (j + 1) % 200 == 0 or j == n_dof - 1:
            print(f"    col {j+1}/{n_dof}", end="\r", flush=True)
    print()
    LH = sparse.csr_matrix((v_list, (r_list, c_list)), shape=(n_dof, n_dof))
    LH = LH.tolil(); LH[pin_dof, :] = 0.0
    return LH.tocsr()


def build_filter_lu(LH, alpha, n_dof, pin_dof):
    F = sparse.eye(n_dof, format="lil") - alpha * LH.tolil()
    F[pin_dof, :] = 0.0; F[pin_dof, pin_dof] = 1.0
    return splu(F.tocsr())


# ── DC + LU solver ─────────────────────────────────────────────────────────────

def dc_lu_solve(rhs, rho, drho_x, drho_y, ccd, backend,
                LU_FD, filter_lu, alpha_factor, h, fade_k,
                shape, tol, maxiter, pin_dof, use_ghost_bc=False):
    p = np.zeros(shape, dtype=float)
    residuals = []
    alpha0 = alpha_factor * h ** 2

    for k in range(maxiter):
        if use_ghost_bc:
            Lp = eval_LH_ghost_bc(p, rho, drho_x, drho_y, ccd, backend, h)
        else:
            Lp = eval_LH_ccd_bc(p, rho, drho_x, drho_y, ccd, backend)
        d = rhs - Lp
        d.ravel()[pin_dof] = 0.0

        res = float(np.linalg.norm(d.ravel()))
        residuals.append(res)

        if res < tol:
            return p, residuals, k + 1, True
        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, False

        dp = LU_FD.solve(d.ravel()).reshape(shape)
        p = p + dp
        p.ravel()[pin_dof] = 0.0

        if alpha0 > 0.0 and filter_lu is not None:
            alpha = alpha0 * (max(0.0, 1.0 - k / fade_k) if fade_k > 0 else 1.0)
            if alpha > 1e-15:
                p = filter_lu.solve(p.ravel()).reshape(shape)
                p.ravel()[pin_dof] = 0.0

    return p, residuals, maxiter, False


# ── Experiment ────────────────────────────────────────────────────────────────

# (name, alpha_factor, fade_k, use_ghost_bc, which_LH)
# which_LH: 'ccd' = CCD BC, 'ghost' = ghost-cell BC
VARIANTS = [
    ("baseline",              0.0,  0,   False, None),
    ("ghost_bc_only",         0.0,  0,   True,  None),   # DC with ghost-cell L_H, no filter
    ("ccd_filter_a05",        0.5,  0,   False, "ccd"),  # original CCD filter
    ("ghost_ccd_filter_a05",  0.5,  0,   True,  "ghost"), # ghost-cell CCD filter
    ("ghost_ccd_filter_a10",  1.0,  0,   True,  "ghost"),
    ("ghost_ccd_filter_a10f", 1.0,  300, True,  "ghost"), # fade
]
VARIANT_LABELS = [
    "Baseline (CCD BC, no filter)",
    "Ghost-cell L_H (no filter)",
    r"CCD filter $\alpha=0.5h^2$ (CCD BC)",
    r"Ghost CCD filter $\alpha=0.5h^2$",
    r"Ghost CCD filter $\alpha=h^2$",
    r"Ghost CCD filter $\alpha=h^2$ (fade k=300)",
]


def run_experiment():
    backend = Backend(use_gpu=False)

    density_ratios = [1, 10, 100, 1000]
    grid_sizes = [16, 32]
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

            print(f"\nN={N}, ρ_l/ρ_g={rho_ratio}")
            L_FD = build_FD_sparse(N, h, rho, drho_x, drho_y, pin_dof)
            LU_FD = splu(L_FD)

            # RHS from CCD-BC L_H (for original DC convergence target)
            rhs_ccd = eval_LH_ccd_bc(p_exact, rho, drho_x, drho_y, ccd, backend)
            rhs_ccd.ravel()[pin_dof] = 0.0

            # RHS from ghost-cell L_H (target for ghost variants)
            rhs_ghost = eval_LH_ghost_bc(p_exact, rho, drho_x, drho_y, ccd, backend, h)
            rhs_ghost.ravel()[pin_dof] = 0.0

            # Build L_H matrices
            print(f"  Building L_H (CCD BC)  [{n_dof} cols]...")
            LH_ccd = build_LH_sparse(N, h, rho, drho_x, drho_y, ccd, backend, pin_dof,
                                     use_ghost_bc=False)

            print(f"  Building L_H (ghost BC) [{n_dof} cols]...")
            LH_ghost = build_LH_sparse(N, h, rho, drho_x, drho_y, ccd, backend, pin_dof,
                                       use_ghost_bc=True)

            # Pre-factor filters for each (LH, alpha) combo
            alpha_factors = sorted({af for _, af, _, _, lh in VARIANTS
                                    if af > 0 and lh is not None})
            filter_lus = {}
            for af in alpha_factors:
                alpha = af * h ** 2
                filter_lus[("ccd",   af)] = build_filter_lu(LH_ccd,   alpha, n_dof, pin_dof)
                filter_lus[("ghost", af)] = build_filter_lu(LH_ghost, alpha, n_dof, pin_dof)

            shape = (N + 1, N + 1)
            print(f"  {'Solver':35s}  {'iters':>5}  {'residual':>10}  {'err_inf':>10}  status")
            print("  " + "-" * 78)

            for name, af, fade_k, use_ghost, lh_key in VARIANTS:
                rhs = rhs_ghost if use_ghost else rhs_ccd
                flu = filter_lus.get((lh_key, af)) if af > 0 and lh_key else None
                p_sol, res_hist, n_iter, conv = dc_lu_solve(
                    rhs, rho, drho_x, drho_y, ccd, backend,
                    LU_FD, flu, af, h, fade_k,
                    shape, tol, maxiter, pin_dof, use_ghost_bc=use_ghost,
                )
                p_ref = p_exact  # always compare with CCD-exact
                err = float(np.max(np.abs(p_sol - p_ref)))
                final_res = float(res_hist[-1])
                status = "OK" if conv else ("DIV" if final_res > 1e15 else "STALL")
                print(f"  {name:35s}  {n_iter:>5}  {final_res:>10.2e}  {err:>10.2e}  {status}")

                all_results[f"N{N}_r{rho_ratio}_{name}"] = {
                    "N": N, "rho_ratio": rho_ratio,
                    "n_iter": n_iter, "converged": int(conv),
                    "final_res": final_res, "final_err": err,
                    "residuals": np.array(res_hist),
                }

    return all_results


# ── Plot ──────────────────────────────────────────────────────────────────────

def plot_results(all_results):
    import matplotlib.pyplot as plt

    grid_sizes = sorted({v["N"] for v in all_results.values()})
    suffixes = [n for n, *_ in VARIANTS]
    styles = ["-", "--", ":", "-", "-", "--"]

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
            ax.set_title(rf"Ghost-BC CCD filter, $N={N}$, $\rho_l/\rho_g={rr}$")
            ax.legend(fontsize=7)
            ax.grid(True, which="both", alpha=0.3)
        fig.tight_layout()
        save_figure(fig, OUT / f"residual_N{N}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser(
        "Ghost-cell BC alignment: CCD filter stabilization"
    ).parse_args()

    if args.plot_only:
        plot_results(load_results(OUT / "data.npz"))
        return

    print("\n" + "=" * 70)
    print("  【10-19】Ghost-cell BC Alignment: CCD Filter")
    print("=" * 70)

    all_results = run_experiment()
    save_results(OUT / "data.npz", all_results)
    plot_results(all_results)
    print(f"\nResults → {OUT}")


if __name__ == "__main__":
    main()
