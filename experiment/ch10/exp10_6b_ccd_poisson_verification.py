#!/usr/bin/env python3
"""【10-6b】CCD-Poisson solver standalone verification (Tests C-1, C-2, C-3).

Dirichlet BC verification using LGMRES on CCD Kronecker product operator.
Results output: results/ch10_ppe_verification/

Paper ref: §10.3.3 (11b3_ppe_verification.tex)

Test C-1: Grid convergence  (Dirichlet, uniform rho, N=8..256)
Test C-2: LGMRES residual history  (Dirichlet, N=16..128)
Test C-3: Variable-density self-consistency  (rho_l/rho_g = 10, 100, 1000)
"""

import sys, pathlib, os, time, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse.linalg as spla
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig, SolverConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.pressure.ppe_solver_pseudotime import PPESolverPseudoTime

OUT = pathlib.Path(__file__).resolve().parents[2] / "results" / "ch10_ppe_verification"
FIG_OUT = OUT / "figures"
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG_OUT.mkdir(parents=True, exist_ok=True)
PAPER_FIG.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_solver(N: int):
    """Create Grid, Backend, CCDSolver, PPESolverPseudoTime for NxN grid."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    sc = SolverConfig(ppe_solver_type="pseudotime", pseudo_tol=1e-12,
                      pseudo_maxiter=5000)
    config = SimulationConfig(solver=sc)
    solver = PPESolverPseudoTime(backend, config, grid, ccd=ccd)
    return grid, backend, ccd, solver


def _build_dirichlet_system(solver, rho, rhs, p_bc, N):
    """Build CCD Kronecker operator with Dirichlet BC on boundary rows."""
    rho_np = np.asarray(rho, dtype=float)
    xp = solver.xp
    rho_dev = xp.asarray(rho_np)
    drho_np = []
    for ax in range(solver.ndim):
        dr, _ = solver.ccd.differentiate(rho_dev, ax)
        drho_np.append(np.asarray(solver.backend.to_host(dr), dtype=float))

    L = solver._build_sparse_operator(rho_np, drho_np)
    L_lil = L.tolil()
    b = rhs.ravel().copy()
    n_pts = N + 1

    for i in range(n_pts):
        for j in range(n_pts):
            if i == 0 or i == N or j == 0 or j == N:
                dof = i * n_pts + j
                L_lil[dof, :] = 0.0
                L_lil[dof, dof] = 1.0
                b[dof] = p_bc.ravel()[dof]

    return L_lil.tocsr(), b


def _lgmres_solve(A, b, tol=1e-12, maxiter=5000, track_residuals=False):
    """LGMRES solve. Returns (x, info, n_iters, [residuals])."""
    residuals = []
    counter = [0]

    def callback(xk):
        counter[0] += 1
        if track_residuals:
            residuals.append(float(np.linalg.norm(b - A @ xk)))

    atol = max(1e-14, tol * float(np.linalg.norm(b)))
    x, info = spla.lgmres(A, b, rtol=tol, maxiter=maxiter, atol=atol,
                          callback=callback)
    if track_residuals:
        return x, info, counter[0], np.array(residuals)
    return x, info, counter[0]


# ---------------------------------------------------------------------------
# Test C-1: Grid Convergence (extended to N=256)
# ---------------------------------------------------------------------------

def test_c1():
    """2D Poisson, Dirichlet BC, uniform rho=1, N=8..256.
    p* = sin(pi x) sin(pi y), f = -2 pi^2 sin(pi x) sin(pi y).
    """
    print("\n" + "=" * 70)
    print("Test C-1: Grid Convergence (Dirichlet BC, LGMRES)")
    print("=" * 70)

    Ns = [8, 16, 32, 64, 128, 256]
    errors, iters_list, times = [], [], []

    for N in Ns:
        grid, backend, ccd, solver = _make_solver(N)
        x = np.linspace(0, 1, N + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")

        p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)
        rhs = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
        rho = np.ones_like(X)

        A, b = _build_dirichlet_system(solver, rho, rhs, p_exact, N)
        t0 = time.perf_counter()
        p_flat, info, n_iters = _lgmres_solve(A, b)
        t_wall = time.perf_counter() - t0
        p_sol = p_flat.reshape(grid.shape)

        err = np.max(np.abs(p_sol - p_exact))
        errors.append(err)
        iters_list.append(n_iters)
        times.append(t_wall)
        print(f"  N={N:4d}  E_inf={err:.3e}  iters={n_iters}  time={t_wall:.3f}s")

    errors = np.array(errors)
    hs = np.array([1.0 / N for N in Ns])
    orders = np.log(errors[:-1] / errors[1:]) / np.log(2.0)
    for k, o in enumerate(orders):
        print(f"  order N={Ns[k]}->{Ns[k+1]}: p={o:.2f}")

    np.savez(OUT / "c1.npz",
             Ns=Ns, hs=hs, errors=errors, orders=orders,
             iters=np.array(iters_list), times=np.array(times))
    return Ns, hs, errors, orders, iters_list, times


# ---------------------------------------------------------------------------
# Test C-2: LGMRES Convergence Behaviour (extended to N=128)
# ---------------------------------------------------------------------------

def test_c2():
    """Track LGMRES residual history at N=16, 32, 64, 128 (Dirichlet BC)."""
    print("\n" + "=" * 70)
    print("Test C-2: LGMRES Convergence History")
    print("=" * 70)

    Ns = [16, 32, 64, 128]
    results = {}

    for N in Ns:
        grid, backend, ccd, solver = _make_solver(N)
        x = np.linspace(0, 1, N + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")

        p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)
        rhs = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
        rho = np.ones_like(X)

        A, b = _build_dirichlet_system(solver, rho, rhs, p_exact, N)

        # Record initial residual
        r0 = float(np.linalg.norm(b))

        p_flat, info, n_iters, res_hist = _lgmres_solve(
            A, b, track_residuals=True)

        err = np.max(np.abs(p_flat.reshape(grid.shape) - p_exact))
        results[N] = {
            "error": err, "n_iters": n_iters,
            "residuals": res_hist, "r0": r0
        }
        res_str = " -> ".join(f"{r:.2e}" for r in res_hist)
        print(f"  N={N:3d}  iters={n_iters}  E_inf={err:.3e}  r0={r0:.2e}")
        print(f"         residuals: {res_str}")

    save_dict = {"Ns": np.array(Ns)}
    for N in Ns:
        save_dict[f"N{N}_error"] = results[N]["error"]
        save_dict[f"N{N}_residuals"] = results[N]["residuals"]
        save_dict[f"N{N}_r0"] = results[N]["r0"]
        save_dict[f"N{N}_iters"] = results[N]["n_iters"]
    np.savez(OUT / "c2.npz", **save_dict)
    return Ns, results


# ---------------------------------------------------------------------------
# Test C-3: Variable Density (multiple density ratios)
# ---------------------------------------------------------------------------

def test_c3():
    """Variable-density Poisson, Dirichlet BC.
    Tests rho_l/rho_g = 10, 100, 1000 at N=16, 32, 64.
    CCD-consistent RHS (rhs = L_CCD^rho p*).
    """
    print("\n" + "=" * 70)
    print("Test C-3: Variable Density (Dirichlet, LGMRES)")
    print("=" * 70)

    Ns = [16, 32, 64]
    ratios = [10, 100, 1000]
    all_results = {}

    for ratio in ratios:
        rho_l, rho_g = float(ratio), 1.0
        print(f"\n  --- rho_l/rho_g = {ratio} ---")
        errors, iters_list = [], []

        for N in Ns:
            grid, backend, ccd, solver = _make_solver(N)
            h = 1.0 / N
            eps = 3.0 * h
            x = np.linspace(0, 1, N + 1)
            X, Y = np.meshgrid(x, x, indexing="ij")

            s = X - 0.5
            H = np.where(s < -eps, 0.0,
                np.where(s > eps, 1.0, 0.5 * (1.0 + s / eps)))
            rho = rho_g + (rho_l - rho_g) * H
            p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)

            # CCD-consistent RHS
            xp = backend.xp
            p_dev = xp.asarray(p_exact)
            rho_dev = xp.asarray(rho)
            dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
            dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
            drho_x, _ = ccd.differentiate(rho_dev, 0)
            drho_y, _ = ccd.differentiate(rho_dev, 1)

            rhs = (np.asarray(d2p_dx2 + d2p_dy2) / rho
                   - np.asarray(drho_x) / rho**2 * np.asarray(dp_dx)
                   - np.asarray(drho_y) / rho**2 * np.asarray(dp_dy))

            A, b = _build_dirichlet_system(solver, rho, rhs, p_exact, N)

            try:
                p_flat, info, n_iters = _lgmres_solve(A, b, maxiter=10000)
                err = np.max(np.abs(p_flat.reshape(grid.shape) - p_exact))
            except Exception as e:
                err = float("nan")
                n_iters = -1
                info = -1
                print(f"    N={N:3d}  FAILED: {e}")

            errors.append(err)
            iters_list.append(n_iters)

            status = "OK" if info == 0 else f"info={info}"
            print(f"    N={N:3d}  E_inf={err:.3e}  iters={n_iters}  [{status}]")

        all_results[ratio] = {
            "Ns": Ns, "errors": np.array(errors),
            "iters": np.array(iters_list),
            "rho_l": rho_l, "rho_g": rho_g
        }

    np.savez(OUT / "c3.npz", **{
        f"ratio{r}_{k}": v for r, d in all_results.items()
        for k, v in d.items() if isinstance(v, (np.ndarray, float))
    }, ratios=np.array(ratios), Ns=np.array(Ns))
    return all_results


# ---------------------------------------------------------------------------
# LaTeX tables
# ---------------------------------------------------------------------------

def _fmt_exp(x):
    """Format number as LaTeX exponential."""
    if np.isnan(x) or np.isinf(x):
        return "---"
    exp = int(np.floor(np.log10(abs(x))))
    mantissa = x / 10**exp
    return f"${mantissa:.2f} \\times 10^{{{exp}}}$"


def save_table_c1(Ns, hs, errors, orders, iters, times):
    path = OUT / "table_c1.tex"
    with open(path, "w") as fp:
        fp.write("% Test C-1: CCD-Poisson grid convergence (Dirichlet BC)\n")
        fp.write("\\begin{tabular}{cccccr}\n\\toprule\n")
        fp.write("$N$ & $h$ & $E_p$（$L^\\infty$） & "
                 "収束次数 $p$ & LGMRES 反復 & 時間 [s] \\\\\n\\midrule\n")
        for k, N in enumerate(Ns):
            o_str = f"${orders[k-1]:.2f}$" if k > 0 else "---"
            fp.write(f"${N}$ & $1/{N}$ & {_fmt_exp(errors[k])} & "
                     f"{o_str} & {iters[k]} & {times[k]:.3f} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {path}")


def save_table_c2(Ns, results):
    path = OUT / "table_c2.tex"
    with open(path, "w") as fp:
        fp.write("% Test C-2: LGMRES residual history\n")
        fp.write("\\begin{tabular}{clcc}\n\\toprule\n")
        fp.write("$N$ & 残差推移 $\\varepsilon^m$（各外部反復後） & "
                 "総反復回数 & $E_p$ \\\\\n\\midrule\n")
        for N in Ns:
            r = results[N]
            res = r["residuals"]
            if len(res) <= 3:
                res_str = " \\to ".join(_fmt_exp(v) for v in res)
            else:
                res_str = (f"{_fmt_exp(res[0])} \\to {_fmt_exp(res[1])} "
                           f"\\to \\cdots \\to {_fmt_exp(res[-1])}")
            fp.write(f"${N}$ & ${res_str}$ & "
                     f"{r['n_iters']} & {_fmt_exp(r['error'])} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {path}")


def save_table_c3(all_results):
    path = OUT / "table_c3.tex"
    with open(path, "w") as fp:
        fp.write("% Test C-3: Variable-density self-consistency\n")
        fp.write("\\begin{tabular}{cccccc}\n\\toprule\n")
        fp.write("$\\rho_l/\\rho_g$ & $N$ & $E_p$（$L^\\infty$） & "
                 "LGMRES 反復 & 判定 \\\\\n\\midrule\n")
        for ratio in sorted(all_results.keys()):
            d = all_results[ratio]
            for k, N in enumerate(d["Ns"]):
                err = d["errors"][k]
                it = d["iters"][k]
                if it < 0:
                    verdict = "発散"
                elif err < 1e-8:
                    verdict = "合格"
                else:
                    verdict = "条件付き"
                fp.write(f"${ratio}$ & ${N}$ & {_fmt_exp(err)} & "
                         f"{it} & {verdict} \\\\\n")
            if ratio != max(all_results.keys()):
                fp.write("\\midrule\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {path}")


def save_summary_table(all_results):
    path = OUT / "table_summary.tex"
    with open(path, "w") as fp:
        fp.write("% Summary: 3 tests role\n")
        fp.write("\\begin{tabular}{clll}\n\\hline\n")
        fp.write("テスト & 検証対象 & 合格基準 & 結果 \\\\\n\\hline\n")
        # Will be populated after actual results
        fp.write("\\hline\n\\end{tabular}\n")
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_c1(Ns, hs, errors, orders, iters, times):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.loglog(hs, errors, "b-o", lw=1.8, ms=7, label="LGMRES (CCD Kronecker)")
    ref6 = errors[0] * (hs / hs[0])**6
    ref4 = errors[0] * (hs / hs[0])**4
    ref7 = errors[0] * (hs / hs[0])**7
    ax.loglog(hs, ref7, "k--", lw=0.8, label=r"$O(h^7)$")
    ax.loglog(hs, ref6, "k:", lw=0.8, label=r"$O(h^6)$")
    ax.loglog(hs, ref4, "k-.", lw=0.8, label=r"$O(h^4)$")
    for k in range(len(orders)):
        hmid = np.sqrt(hs[k] * hs[k+1])
        emid = np.sqrt(errors[k] * errors[k+1])
        ax.annotate(f"p={orders[k]:.1f}", xy=(hmid, emid),
                    fontsize=9, color="blue", ha="center",
                    xytext=(0, -14), textcoords="offset points")
    ax.set_xlabel("Grid spacing $h$", fontsize=12)
    ax.set_ylabel(r"$L^\infty$ error", fontsize=12)
    ax.set_title("Test C-1: CCD-Poisson Grid Convergence (2D, Dirichlet BC)", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, which="both", ls="--", alpha=0.4)
    fig.tight_layout()
    path = FIG_OUT / "c1_convergence.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    shutil.copy2(path, PAPER_FIG / "c1_convergence.png")
    print(f"  Saved: {path}")


def fig_c2(Ns, results):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = ["#2166ac", "#d62728", "#2ca02c", "#9467bd"]
    for N, col in zip(Ns, colors):
        r = results[N]["residuals"]
        if len(r) > 0:
            ax.semilogy(range(1, len(r)+1), r, color=col, lw=1.5, marker="o",
                        ms=5, label=f"N={N} ({results[N]['n_iters']} iters)")
    ax.set_xlabel("Outer iteration", fontsize=12)
    ax.set_ylabel(r"Residual $\|Ap - b\|_2$", fontsize=12)
    ax.set_title("Test C-2: LGMRES Convergence History (Dirichlet BC)", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, which="both", ls="--", alpha=0.4)
    fig.tight_layout()
    path = FIG_OUT / "c2_convergence.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    shutil.copy2(path, PAPER_FIG / "c2_convergence.png")
    print(f"  Saved: {path}")


def fig_c3(all_results):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    colors = {10: "#2166ac", 100: "#d62728", 1000: "#2ca02c"}

    # (a) Error vs N for each density ratio
    for ratio, d in sorted(all_results.items()):
        ax1.semilogy(d["Ns"], d["errors"], "o-", color=colors[ratio],
                     lw=1.5, ms=6, label=f"$\\rho_l/\\rho_g={ratio}$")
    ax1.set_xlabel("$N$", fontsize=12)
    ax1.set_ylabel(r"$E_p$ ($L^\infty$)", fontsize=12)
    ax1.set_title("(a) Self-consistency error", fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    # (b) Iteration count vs N for each density ratio
    for ratio, d in sorted(all_results.items()):
        valid = d["iters"] > 0
        ax2.plot(np.array(d["Ns"])[valid], d["iters"][valid], "s-",
                 color=colors[ratio], lw=1.5, ms=6,
                 label=f"$\\rho_l/\\rho_g={ratio}$")
    ax2.set_xlabel("$N$", fontsize=12)
    ax2.set_ylabel("LGMRES iterations", fontsize=12)
    ax2.set_title("(b) Iteration count scaling", fontsize=12)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    path = FIG_OUT / "c3_variable_density.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    shutil.copy2(path, PAPER_FIG / "c3_variable_density.png")
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("  CCD-Poisson Standalone Verification (C-1, C-2, C-3)")
    print("=" * 70)

    Ns_c1, hs, errors, orders, iters, times = test_c1()
    Ns_c2, c2_results = test_c2()
    c3_results = test_c3()

    print("\n--- Generating LaTeX tables ---")
    save_table_c1(Ns_c1, hs, errors, orders, iters, times)
    save_table_c2(Ns_c2, c2_results)
    save_table_c3(c3_results)

    print("\n--- Generating figures ---")
    fig_c1(Ns_c1, hs, errors, orders, iters, times)
    fig_c2(Ns_c2, c2_results)
    fig_c3(c3_results)

    print("\nAll C-1/C-2/C-3 tests complete.")
    print(f"Results in: {OUT}")
