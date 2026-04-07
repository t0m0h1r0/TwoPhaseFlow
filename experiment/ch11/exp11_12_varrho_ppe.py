#!/usr/bin/env python3
"""[11-12] Variable-density PPE convergence (DC k=3).

Validates: Ch9b + Ch8b -- Variable-coefficient operator with CCD product rule.

Tests:
  (a) Smooth density: rho=1+A*sin(pi*x)*cos(pi*y), A=[0, 0.8, 0.98, 0.998]
  (b) Interface-type density: smoothed Heaviside, rho_l/rho_g=[10,100,1000]
      (expected divergence -- known limitation)

Expected: (a) O(h^6-7) maintained; (b) divergence for ratio>=10.
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
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def eval_LH_varrho(p, rho, ccd, backend):
    xp = backend.xp
    p_dev = xp.asarray(p); rho_dev = xp.asarray(rho)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        dp, d2p = ccd.differentiate(p_dev, ax)
        drho, _ = ccd.differentiate(rho_dev, ax)
        Lp += d2p / rho_dev - (drho / rho_dev**2) * dp
    return np.asarray(backend.to_host(Lp))


def build_fd_varrho(N, h, rho):
    nx = ny = N + 1; n = nx * ny
    drho_dx = np.zeros_like(rho); drho_dy = np.zeros_like(rho)
    for i in range(1, N):
        drho_dx[i, :] = (rho[i+1, :] - rho[i-1, :]) / (2*h)
    for j in range(1, N):
        drho_dy[:, j] = (rho[:, j+1] - rho[:, j-1]) / (2*h)

    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                inv_rho = 1.0 / rho[i, j]
                cx = drho_dx[i, j] / rho[i, j]**2
                cy = drho_dy[i, j] / rho[i, j]**2
                # (1/rho) d2p/dx2: standard 3-point stencil
                rows.append(k); cols.append((i+1)*ny+j); vals.append(inv_rho/h**2)
                rows.append(k); cols.append((i-1)*ny+j); vals.append(inv_rho/h**2)
                # (1/rho) d2p/dy2
                rows.append(k); cols.append(i*ny+(j+1)); vals.append(inv_rho/h**2)
                rows.append(k); cols.append(i*ny+(j-1)); vals.append(inv_rho/h**2)
                # center
                center = -2.0*inv_rho/h**2 - 2.0*inv_rho/h**2
                # -(drho_x/rho^2)(dp/dx): central diff contribution
                rows.append(k); cols.append((i+1)*ny+j); vals.append(-cx/(2*h))
                rows.append(k); cols.append((i-1)*ny+j); vals.append(cx/(2*h))
                # -(drho_y/rho^2)(dp/dy)
                rows.append(k); cols.append(i*ny+(j+1)); vals.append(-cy/(2*h))
                rows.append(k); cols.append(i*ny+(j-1)); vals.append(cy/(2*h))
                rows.append(k); cols.append(k); vals.append(center)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


def run_smooth_density():
    backend = Backend(use_gpu=False)
    Ns = [16, 32, 64, 128]; k_dc = 3
    cases = [
        {"label": "1", "A": 0.0},
        {"label": "9", "A": 0.8},
        {"label": "99", "A": 0.98},
        {"label": "999", "A": 0.998},
    ]
    all_results = {}

    for case in cases:
        A = case["A"]; label = case["label"]
        all_results[label] = []
        print(f"\n  rho_ratio ~ {label} (A={A}):")

        for N in Ns:
            gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
            grid = Grid(gc, backend); ccd = CCDSolver(grid, backend, bc_type="wall")
            h = 1.0 / N; X, Y = grid.meshgrid()
            p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)
            rho = 1.0 + A * np.sin(np.pi * X) * np.cos(np.pi * Y)

            # Analytical RHS
            pi = np.pi; sinx = np.sin(pi*X); cosx = np.cos(pi*X)
            siny = np.sin(pi*Y); cosy = np.cos(pi*Y)
            drho_dx = A * pi * cosx * cosy
            drho_dy = -A * pi * sinx * siny
            rhs = (-2*pi**2*sinx*siny) / rho - (drho_dx*pi*cosx*siny + drho_dy*pi*sinx*cosy) / rho**2
            rhs[0,:]=0; rhs[-1,:]=0; rhs[:,0]=0; rhs[:,-1]=0

            L_L = build_fd_varrho(N, h, rho)
            p = np.zeros_like(rhs)
            for _ in range(k_dc):
                Lp = eval_LH_varrho(p, rho, ccd, backend)
                d = rhs - Lp; d[0,:]=0; d[-1,:]=0; d[:,0]=0; d[:,-1]=0
                dp = spsolve(L_L, d.ravel()).reshape(rhs.shape)
                p = p + dp; p[0,:]=0; p[-1,:]=0; p[:,0]=0; p[:,-1]=0

            err = float(np.max(np.abs(p - p_exact)))
            all_results[label].append({"N": N, "h": h, "Li": err})

            order_str = "---"
            if len(all_results[label]) > 1:
                r0, r1 = all_results[label][-2], all_results[label][-1]
                if r0["Li"] > 1e-15 and r1["Li"] > 1e-15:
                    order_str = f"{np.log(r1['Li']/r0['Li'])/np.log(r1['h']/r0['h']):.2f}"
            print(f"    N={N:>4}: Li={err:.3e}, order={order_str}")

    return all_results


def plot_all(all_results):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 1, figsize=(7, 5))
    for ci, (label, res) in enumerate(all_results.items()):
        hs = [r["h"] for r in res]
        ax.loglog(hs, [r["Li"] for r in res], f"{MARKERS[ci]}-",
                  color=COLORS[ci], label=rf"$\rho_{{\max}}/\rho_{{\min}} \approx {label}$")
    hs = [r["h"] for r in list(all_results.values())[0]]
    h_ref = np.array([hs[0], hs[-1]])
    for order in [5, 6, 7]:
        ax.loglog(h_ref, 1e-2*(h_ref/h_ref[0])**order,
                  ":", color="gray", alpha=0.4, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("Variable-density PPE (smooth, DC $k=3$)")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, OUT / "varrho_ppe")


def main():
    args = experiment_argparser("[11-12] Variable-density PPE").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d)
        return

    all_results = run_smooth_density()
    save_results(OUT / "data.npz", all_results)
    plot_all(all_results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
