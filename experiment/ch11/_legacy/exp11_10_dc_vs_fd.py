#!/usr/bin/env python3
"""[11-10] DC k=3 vs FD direct: accuracy-cost comparison.

Validates: Ch9b -- Practical advantage of defect correction.

Test:
  2D Poisson, p*=sin(pi*x)*sin(pi*y), Dirichlet BC, N=[8,16,32,64,128].
  (A) FD direct: L_L p = b -> O(h^2)
  (B) DC k=3: CCD residual + FD correction x3 -> O(h^6+)

Expected: DC 4.9e7x better accuracy at N=128 for 3.4x cost.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np, time
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment.gpu import (
    fd_laplacian_dirichlet_2d,
    max_abs_error,
    sparse_solve_2d,
    zero_dirichlet_boundary,
)
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def eval_LH(p, ccd, backend):
    xp = backend.xp; p_dev = xp.asarray(p)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        _, d2p = ccd.differentiate(p_dev, ax)
        Lp += d2p
    return Lp


def sync(backend):
    if backend.is_gpu():
        backend.xp.cuda.Stream.null.synchronize()


def run_comparison():
    backend = Backend()
    Ns = [8, 16, 32, 64, 128]
    res_fd, res_dc = [], []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend); ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N; X, Y = grid.meshgrid()
        xp = backend.xp
        p_exact = xp.sin(np.pi * X) * xp.sin(np.pi * Y)
        rhs = -2 * np.pi**2 * p_exact
        zero_dirichlet_boundary(rhs)
        L_L = fd_laplacian_dirichlet_2d(N, h, backend)

        # FD direct
        sync(backend)
        t0 = time.perf_counter()
        p_fd = sparse_solve_2d(backend, L_L, rhs)
        sync(backend)
        t_fd = (time.perf_counter() - t0) * 1000

        # DC k=3
        sync(backend)
        t0 = time.perf_counter()
        p = xp.zeros_like(rhs)
        for _ in range(3):
            Lp = eval_LH(p, ccd, backend)
            d = rhs - Lp
            zero_dirichlet_boundary(d)
            p = p + sparse_solve_2d(backend, L_L, d)
            zero_dirichlet_boundary(p)
        sync(backend)
        t_dc = (time.perf_counter() - t0) * 1000

        e_fd = max_abs_error(backend, p_fd, p_exact)
        e_dc = max_abs_error(backend, p, p_exact)
        res_fd.append({"N": N, "h": h, "Li": e_fd, "time_ms": t_fd})
        res_dc.append({"N": N, "h": h, "Li": e_dc, "time_ms": t_dc})
        ratio = e_fd / e_dc if e_dc > 0 else float("inf")
        print(f"  N={N:>4}: FD={e_fd:.3e} ({t_fd:.1f}ms), DC={e_dc:.3e} ({t_dc:.1f}ms), ratio={ratio:.0f}x")

    for res in [res_fd, res_dc]:
        for i in range(1, len(res)):
            r0, r1 = res[i-1], res[i]
            if r0["Li"] > 0 and r1["Li"] > 0:
                r1["Li_slope"] = np.log(r1["Li"]/r0["Li"]) / np.log(r1["h"]/r0["h"])
    return res_fd, res_dc


def plot_all(res_fd, res_dc):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    ax = axes[0]
    hs = [r["h"] for r in res_fd]
    ax.loglog(hs, [r["Li"] for r in res_fd], "s--", label=r"FD direct ($O(h^2)$)")
    ax.loglog(hs, [r["Li"] for r in res_dc], "o-", label=r"DC $k=3$ ($O(h^6)$)")
    h_ref = np.array([hs[0], hs[-1]])
    for order, ls in [(2, ":"), (6, "-.")]:
        ax.loglog(h_ref, res_fd[0]["Li"]*(h_ref/h_ref[0])**order,
                  ls, color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("(a) Accuracy"); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    ax = axes[1]
    Ns = [r["N"] for r in res_fd]; x = np.arange(len(Ns)); w = 0.35
    ax.bar(x-w/2, [r["time_ms"] for r in res_fd], w, label="FD", color=COLORS[0])
    ax.bar(x+w/2, [r["time_ms"] for r in res_dc], w, label="DC k=3", color=COLORS[1])
    ax.set_xticks(x); ax.set_xticklabels([str(n) for n in Ns])
    ax.set_xlabel("$N$"); ax.set_ylabel("Wall time (ms)"); ax.set_yscale("log")
    ax.set_title("(b) Cost"); ax.legend(fontsize=8)
    fig.tight_layout()
    save_figure(fig, OUT / "dc_vs_fd")


def main():
    args = experiment_argparser("[11-10] DC vs FD").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["fd"], d["dc"])
        return

    res_fd, res_dc = run_comparison()
    save_results(OUT / "data.npz", {"fd": res_fd, "dc": res_dc})
    plot_all(res_fd, res_dc)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
