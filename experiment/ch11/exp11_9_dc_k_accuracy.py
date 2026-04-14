#!/usr/bin/env python3
"""[11-9] Defect correction: iteration count k vs spatial accuracy.

Validates: Ch9b -- Defect correction method with DC+LU.

Test:
  2D Poisson div^2 p = f on [0,1]^2, Dirichlet BC, p* = sin(pi*x)*sin(pi*y).
  L_H = CCD (O(h^6)), L_L = FD 5-point (O(h^2)), solved by spsolve.
  k = 1, 2, 3, 5, 10 iterations.

Expected: k=1 -> O(h^2); k=2 -> O(h^4); k>=3 -> O(h^7) (Dirichlet super-convergence).
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
    COLORS, MARKERS, FIGSIZE_1COL,
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


def build_fd_laplacian_dirichlet(N, h):
    nx = ny = N + 1; n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                    rows.append(k); cols.append((i+di)*ny+(j+dj)); vals.append(1.0/h**2)
                rows.append(k); cols.append(k); vals.append(-4.0/h**2)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


def defect_correction(rhs, ccd, backend, L_L, k_max):
    p = np.zeros_like(rhs)
    for _ in range(k_max):
        Lp = eval_LH(p, ccd, backend)
        d = rhs - Lp
        d[0,:] = 0; d[-1,:] = 0; d[:,0] = 0; d[:,-1] = 0
        dp = spsolve(L_L, d.ravel()).reshape(rhs.shape)
        p = p + dp
        p[0,:] = 0; p[-1,:] = 0; p[:,0] = 0; p[:,-1] = 0
    return p


def run_experiment():
    backend = Backend()
    Ns = [8, 16, 32, 64, 128]; Ks = [1, 2, 3, 5, 10]
    errors = {k: [] for k in Ks}

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        # Defect-correction loop below goes through scipy.sparse.spsolve,
        # so p_exact / rhs are kept on host; CCD evaluation in eval_LH
        # still runs on device via xp.asarray(p) internally.
        X, Y = grid.meshgrid()
        X_h = backend.to_host(X); Y_h = backend.to_host(Y)
        p_exact = np.sin(np.pi * X_h) * np.sin(np.pi * Y_h)
        rhs = -2.0 * np.pi**2 * p_exact
        rhs[0,:] = 0; rhs[-1,:] = 0; rhs[:,0] = 0; rhs[:,-1] = 0
        L_L = build_fd_laplacian_dirichlet(N, h)

        row = f"  N={N:>4}:"
        for k in Ks:
            p_dc = defect_correction(rhs, ccd, backend, L_L, k)
            err = float(np.max(np.abs(p_dc - p_exact)))
            errors[k].append({"N": N, "h": h, "Li": err})
            row += f"  k={k}:{err:.2e}"
        print(row)

    # Compute slopes
    for k in Ks:
        for i in range(1, len(errors[k])):
            r0, r1 = errors[k][i-1], errors[k][i]
            if r0["Li"] > 0 and r1["Li"] > 0:
                r1["Li_slope"] = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])

    return errors, Ns, Ks


def plot_all(errors, Ns, Ks):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 1, figsize=FIGSIZE_1COL)
    markers = ["o", "s", "D", "^", "v"]
    for ki, k in enumerate(Ks):
        hs = [e["h"] for e in errors[str(k)]]
        es = [e["Li"] for e in errors[str(k)]]
        ax.loglog(hs, es, f"{markers[ki]}-", label=f"$k={k}$", markersize=6)
    h_ref = np.array([1.0/Ns[0], 1.0/Ns[-1]])
    e_top = errors[str(Ks[0])][0]["Li"]
    for order, ls in [(2, ":"), (4, "-."), (6, "--")]:
        ax.loglog(h_ref, e_top*(h_ref/h_ref[0])**order, ls,
                  color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("DC iteration count $k$ vs spatial accuracy")
    ax.legend(fontsize=7, ncol=2); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, OUT / "dc_k_accuracy")


def main():
    args = experiment_argparser("[11-9] DC k Accuracy").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["errors"], list(d["Ns"]), list(d["Ks"]))
        return

    errors, Ns, Ks = run_experiment()
    save_results(OUT / "data.npz", {
        "errors": {str(k): v for k, v in errors.items()},
        "Ns": np.array(Ns), "Ks": np.array(Ks),
    })
    plot_all({str(k): v for k, v in errors.items()}, Ns, Ks)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
