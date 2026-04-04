#!/usr/bin/env python3
"""【10-9】Defect correction vs FD direct solve: accuracy-cost comparison.

Paper ref: §8.3 (tab:dc_ppe_methods), §11.3.7 (sec:dc_iteration_accuracy)

Compares:
  (A) FD direct solve: L_L p = b  (single solve, O(h²))
  (B) Defect correction k=3: L_H residual + L_L correction × 3  (O(h⁶))

Both use the same FD sparse direct solve as the core linear algebra.
DC adds CCD residual evaluation cost per iteration.

Metrics: L∞ error, wall-clock time, effective accuracy per unit cost.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import time
from scipy import sparse
from scipy.sparse.linalg import spsolve
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver

OUT = pathlib.Path(__file__).resolve().parent / "results" / "dc_vs_fd"
OUT.mkdir(parents=True, exist_ok=True)


# ── Analytical solution ──────────────────────────────────────────────────────

def analytical_solution(X, Y):
    """p* = sin(πx)sin(πy), f = -2π² sin(πx)sin(πy). Dirichlet BC."""
    p = np.sin(np.pi * X) * np.sin(np.pi * Y)
    lap_p = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
    return p, lap_p


# ── Operators ────────────────────────────────────────────────────────────────

def eval_LH(p, ccd, backend):
    """L_H p = ∇²p via CCD (O(h⁶))."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        _, d2p = ccd.differentiate(p_dev, ax)
        Lp += d2p
    return np.asarray(backend.to_host(Lp))


def build_fd_laplacian(Nx, Ny, hx, hy):
    """2D 5-point FD Laplacian, Dirichlet BC (boundary = identity rows)."""
    nx, ny = Nx + 1, Ny + 1
    n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == Nx or j == 0 or j == Ny:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                rows.append(k); cols.append((i-1)*ny+j); vals.append(1.0/hx**2)
                rows.append(k); cols.append((i+1)*ny+j); vals.append(1.0/hx**2)
                rows.append(k); cols.append(i*ny+(j-1)); vals.append(1.0/hy**2)
                rows.append(k); cols.append(i*ny+(j+1)); vals.append(1.0/hy**2)
                rows.append(k); cols.append(k);           vals.append(-2.0/hx**2-2.0/hy**2)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


# ── Solvers ──────────────────────────────────────────────────────────────────

def solve_fd_direct(rhs, L_L):
    """(A) FD direct: L_L p = b → O(h²)."""
    return spsolve(L_L, rhs.ravel()).reshape(rhs.shape)


def solve_dc(rhs, ccd, backend, L_L, k_max=3):
    """(B) Defect correction: k iterations of L_H residual + L_L correction."""
    p = np.zeros_like(rhs)
    for _ in range(k_max):
        Lp = eval_LH(p, ccd, backend)
        d = rhs - Lp
        d[0, :] = 0.0; d[-1, :] = 0.0; d[:, 0] = 0.0; d[:, -1] = 0.0
        dp = spsolve(L_L, d.ravel()).reshape(rhs.shape)
        p = p + dp
        p[0, :] = 0.0; p[-1, :] = 0.0; p[:, 0] = 0.0; p[:, -1] = 0.0
    return p


# ── Experiment ───────────────────────────────────────────────────────────────

def run_comparison():
    backend = Backend(use_gpu=False)

    Ns = [8, 16, 32, 64, 128]
    k_dc = 3  # defect correction iterations

    results_fd = []
    results_dc = []

    header = f"{'N':>5} | {'FD L∞':>12} {'p':>6} {'t(ms)':>8} | {'DC(k=3) L∞':>12} {'p':>6} {'t(ms)':>8} | {'ratio':>8}"
    print(header)
    print("-" * len(header))

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N

        X, Y = grid.meshgrid()
        p_exact, rhs = analytical_solution(X, Y)
        rhs[0, :] = 0.0; rhs[-1, :] = 0.0; rhs[:, 0] = 0.0; rhs[:, -1] = 0.0

        L_L = build_fd_laplacian(N, N, h, h)

        # (A) FD direct
        t0 = time.perf_counter()
        p_fd = solve_fd_direct(rhs, L_L)
        t_fd = (time.perf_counter() - t0) * 1000  # ms

        err_fd = float(np.max(np.abs(p_fd - p_exact)))
        results_fd.append({"N": N, "h": h, "Li": err_fd, "time_ms": t_fd})

        # (B) DC k=3
        t0 = time.perf_counter()
        p_dc = solve_dc(rhs, ccd, backend, L_L, k_max=k_dc)
        t_dc = (time.perf_counter() - t0) * 1000  # ms

        err_dc = float(np.max(np.abs(p_dc - p_exact)))
        results_dc.append({"N": N, "h": h, "Li": err_dc, "time_ms": t_dc})

        # Accuracy ratio
        ratio = err_fd / err_dc if err_dc > 0 else float("inf")

        # Slopes
        slope_fd = "---"
        slope_dc = "---"
        if len(results_fd) > 1:
            r0, r1 = results_fd[-2], results_fd[-1]
            if r0["Li"] > 0 and r1["Li"] > 0:
                slope_fd = f"{np.log(r1['Li']/r0['Li'])/np.log(r1['h']/r0['h']):.2f}"
            r0, r1 = results_dc[-2], results_dc[-1]
            if r0["Li"] > 0 and r1["Li"] > 0:
                slope_dc = f"{np.log(r1['Li']/r0['Li'])/np.log(r1['h']/r0['h']):.2f}"

        print(f"{N:>5} | {err_fd:>12.3e} {slope_fd:>6} {t_fd:>7.1f}  | "
              f"{err_dc:>12.3e} {slope_dc:>6} {t_dc:>7.1f}  | {ratio:>8.1f}x")

    return results_fd, results_dc


def save_latex_table(results_fd, results_dc):
    with open(OUT / "table_dc_vs_fd.tex", "w") as fp:
        fp.write("% Auto-generated by exp10_9_dc_vs_fd_comparison.py\n")
        fp.write("\\begin{tabular}{crrcrrcc}\n\\toprule\n")
        fp.write("$N$ & \\multicolumn{2}{c}{FD 直接法 ($\\Ord{h^2}$)} "
                 "& & \\multicolumn{2}{c}{欠陥補正 $k=3$ ($\\Ord{h^6}$)} "
                 "& 精度比 & コスト比 \\\\\n")
        fp.write("\\cmidrule{2-3} \\cmidrule{5-6}\n")
        fp.write(" & $L^\\infty$ 誤差 & 次数 & & $L^\\infty$ 誤差 & 次数 & $E_{\\text{FD}}/E_{\\text{DC}}$ & $t_{\\text{DC}}/t_{\\text{FD}}$ \\\\\n")
        fp.write("\\midrule\n")

        for i in range(len(results_fd)):
            N = results_fd[i]["N"]
            e_fd = results_fd[i]["Li"]
            e_dc = results_dc[i]["Li"]
            t_fd = results_fd[i]["time_ms"]
            t_dc = results_dc[i]["time_ms"]

            s_fd = "---"
            s_dc = "---"
            if i > 0:
                r0, r1 = results_fd[i-1], results_fd[i]
                if r0["Li"] > 0 and r1["Li"] > 0:
                    s_fd = f"{np.log(r1['Li']/r0['Li'])/np.log(r1['h']/r0['h']):.2f}"
                r0, r1 = results_dc[i-1], results_dc[i]
                if r0["Li"] > 0 and r1["Li"] > 0:
                    s_dc = f"{np.log(r1['Li']/r0['Li'])/np.log(r1['h']/r0['h']):.2f}"

            ratio_acc = e_fd / e_dc if e_dc > 0 else float("inf")
            ratio_cost = t_dc / t_fd if t_fd > 0 else float("inf")

            fp.write(f"${N}$ & ${e_fd:.2e}$ & {s_fd} & & ${e_dc:.2e}$ & {s_dc} "
                     f"& ${ratio_acc:.0f}\\times$ & ${ratio_cost:.1f}\\times$ \\\\\n")

        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_dc_vs_fd.tex'}")


def save_plot(results_fd, results_dc):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    hs_fd = [r["h"] for r in results_fd]
    hs_dc = [r["h"] for r in results_dc]

    # (a) Accuracy comparison
    ax = axes[0]
    ax.loglog(hs_fd, [r["Li"] for r in results_fd], "s--", label="FD direct ($O(h^2)$)", markersize=7)
    ax.loglog(hs_dc, [r["Li"] for r in results_dc], "o-",  label="DC $k=3$ ($O(h^6)$)",  markersize=7)

    h_ref = np.array([hs_fd[0], hs_fd[-1]])
    e_top = results_fd[0]["Li"]
    for order, ls in [(2, ":"), (6, "-.")]:
        ax.loglog(h_ref, e_top * (h_ref / h_ref[0])**order, ls,
                  color="gray", alpha=0.5, label=f"$O(h^{order})$")

    ax.set_xlabel("$h$"); ax.set_ylabel("$L^\\infty$ error")
    ax.set_title("(a) Accuracy: FD direct vs Defect Correction")
    ax.legend(fontsize=8); ax.grid(True, which="both", alpha=0.3)

    # (b) Cost comparison
    ax = axes[1]
    ts_fd = [r["time_ms"] for r in results_fd]
    ts_dc = [r["time_ms"] for r in results_dc]
    Ns = [r["N"] for r in results_fd]

    x = np.arange(len(Ns))
    w = 0.35
    ax.bar(x - w/2, ts_fd, w, label="FD direct", color="steelblue", alpha=0.8)
    ax.bar(x + w/2, ts_dc, w, label="DC $k=3$",  color="coral",     alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels([str(n) for n in Ns])
    ax.set_xlabel("$N$"); ax.set_ylabel("Wall time (ms)")
    ax.set_title("(b) Computational cost")
    ax.legend(fontsize=8)
    ax.set_yscale("log")

    fig.tight_layout()
    fig.savefig(OUT / "dc_vs_fd_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'dc_vs_fd_comparison.png'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-9】Defect Correction vs FD Direct Solve")
    print("=" * 80 + "\n")

    results_fd, results_dc = run_comparison()
    save_latex_table(results_fd, results_dc)
    save_plot(results_fd, results_dc)

    np.savez(OUT / "dc_vs_fd_data.npz",
             fd=results_fd, dc=results_dc)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "dc_vs_fd_data.npz", allow_pickle=True)
        save_plot(list(_d["fd"]), list(_d["dc"]))
    else:
        main()
