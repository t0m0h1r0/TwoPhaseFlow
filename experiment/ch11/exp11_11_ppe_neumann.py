#!/usr/bin/env python3
"""[11-11] PPE Neumann BC + gauge fixing verification.

Validates: Ch9c -- Neumann BC treatment with gauge pinning.

Test:
  2D Poisson, p*=cos(pi*x)*cos(pi*y), all-Neumann BC,
  gauge pin p_{0,0}=p*(0,0), DC k=3, N=[8,16,32,64,128].

Expected: O(h^5) convergence (CCD boundary scheme O(h^5) bottleneck).
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment.gpu import (
    fd_laplacian_neumann_2d,
    max_abs_error,
    pin_gauge,
    sparse_solve_2d,
)
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    FIGSIZE_1COL,
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


def run_experiment():
    backend = Backend()
    Ns = [8, 16, 32, 64, 128]; k_dc = 3
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend); ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N; X, Y = grid.meshgrid()
        xp = backend.xp
        p_exact = xp.cos(np.pi * X) * xp.cos(np.pi * Y)
        rhs = -2 * np.pi**2 * p_exact

        L_L = fd_laplacian_neumann_2d(N, h, backend)
        pin_dof = 0
        pin_val = float(np.asarray(backend.to_host(p_exact.ravel()[0])))
        L_L_pinned, _ = pin_gauge(L_L, rhs.ravel(), pin_dof, pin_val, backend)

        p = xp.zeros_like(rhs)
        for _ in range(k_dc):
            Lp = eval_LH(p, ccd, backend)
            d = rhs - Lp
            d.ravel()[pin_dof] = pin_val - p.ravel()[pin_dof]
            dp = sparse_solve_2d(backend, L_L_pinned, d)
            p = p + dp

        err = max_abs_error(backend, p, p_exact)
        results.append({"N": N, "h": h, "Li": err})

        order_str = "---"
        if len(results) > 1:
            r0, r1 = results[-2], results[-1]
            if r0["Li"] > 0 and r1["Li"] > 0:
                order_str = f"{np.log(r1['Li']/r0['Li'])/np.log(r1['h']/r0['h']):.2f}"
        print(f"  N={N:>4}: Li={err:.3e}, order={order_str}")

    return results


def plot_all(results):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE_1COL)
    hs = [r["h"] for r in results]
    ax.loglog(hs, [r["Li"] for r in results], "o-", label=r"DC $k=3$ (Neumann)")
    h_ref = np.array([hs[0], hs[-1]])
    for order, ls in [(4, ":"), (5, "--"), (6, "-.")]:
        ax.loglog(h_ref, results[0]["Li"]*(h_ref/h_ref[0])**order,
                  ls, color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("PPE Neumann BC + gauge pin")
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, OUT / "ppe_neumann")


def main():
    args = experiment_argparser("[11-11] PPE Neumann").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["results"])
        return

    results = run_experiment()
    save_results(OUT / "data.npz", {"results": results})
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
