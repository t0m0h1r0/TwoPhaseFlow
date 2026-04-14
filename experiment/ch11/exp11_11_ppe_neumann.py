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
from scipy import sparse
from scipy.sparse.linalg import spsolve
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
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
    return np.asarray(backend.to_host(Lp))


def build_fd_neumann(N, h):
    nx = ny = N + 1; n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j; center = 0.0
            for coord, lo, hi in [(i, (i-1)*ny+j, (i+1)*ny+j), (j, i*ny+(j-1), i*ny+(j+1))]:
                if 0 < coord < N:
                    rows.append(k); cols.append(lo); vals.append(1.0/h**2); center -= 1.0/h**2
                    rows.append(k); cols.append(hi); vals.append(1.0/h**2); center -= 1.0/h**2
                elif coord == 0:
                    rows.append(k); cols.append(hi); vals.append(2.0/h**2); center -= 2.0/h**2
                else:
                    rows.append(k); cols.append(lo); vals.append(2.0/h**2); center -= 2.0/h**2
            rows.append(k); cols.append(k); vals.append(center)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


def pin_gauge(L, rhs_flat, pin_dof, pin_val):
    L_lil = L.tolil(); L_lil[pin_dof, :] = 0.0; L_lil[pin_dof, pin_dof] = 1.0
    rhs_flat[pin_dof] = pin_val
    return L_lil.tocsr(), rhs_flat


def run_experiment():
    backend = Backend()
    Ns = [8, 16, 32, 64, 128]; k_dc = 3
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend); ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N; X, Y = grid.meshgrid()
        # Defect-correction loop uses scipy.sparse.spsolve (CPU-only); keep
        # p_exact / rhs on host while eval_LH still routes CCD through device.
        X = backend.to_host(X); Y = backend.to_host(Y)
        p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
        rhs = -2 * np.pi**2 * p_exact

        L_L = build_fd_neumann(N, h)
        pin_dof = 0; pin_val = float(p_exact.ravel()[0])
        rhs_flat = rhs.ravel().copy()
        L_L_pinned, rhs_flat = pin_gauge(L_L.copy(), rhs_flat, pin_dof, pin_val)

        p = np.zeros_like(rhs)
        for _ in range(k_dc):
            Lp = eval_LH(p, ccd, backend)
            d = rhs - Lp; d_flat = d.ravel().copy()
            d_flat[pin_dof] = pin_val - p.ravel()[pin_dof]
            dp = spsolve(L_L_pinned, d_flat).reshape(rhs.shape)
            p = p + dp

        err = float(np.max(np.abs(p - p_exact)))
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
