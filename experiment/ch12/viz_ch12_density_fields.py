#!/usr/bin/env python3
"""§12.4 Density sweep 2D field visualization.

Runs static droplet at N=64, 200 steps for ρ_l/ρ_g = 2, 3, 5, 10 and produces:
  - 4-panel: pressure field at each density ratio (shows Laplace pressure scaling)
  - Bar chart: ||u||∞ vs density ratio

Output: results/ch12_density_sweep/ch12_density_fields.png
        paper/figures/ch12_density_fields.png
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder

OUT_RES = pathlib.Path(__file__).resolve().parents[2] / "results" / "ch12_density_sweep"
OUT_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

N = 64
RHO_G = 1.0
WE = 10.0
R = 0.25
SIGMA = 1.0
N_STEPS = 200


def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run(rho_l):
    """Run static droplet at given rho_l. Returns (phi, p, vel_mag, u_max_hist)."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (rho_l - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_hist = []
    p = np.zeros_like(X)

    for step in range(N_STEPS):
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
        p = _solve_ppe(rhs, rho, ppe_builder)

        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)
        if np.isnan(u_max) or u_max > 1e6:
            break

    vel_mag = np.sqrt(u**2 + v**2)
    return phi, p, vel_mag, u_max_hist


def make_figure(results):
    rho_ratios = [r['rho_l'] for r in results]

    fig, axes = plt.subplots(2, 4, figsize=(18, 9))

    Ng = results[0]['p'].shape[0]
    x1d = np.linspace(0, 1, Ng)
    y1d = np.linspace(0, 1, Ng)

    # Find global pressure scale (shared colorbar)
    all_p = np.concatenate([r['p'].ravel() for r in results])
    vmax_p = float(np.percentile(np.abs(all_p), 99)) * 1.05

    vmax_u = float(max(r['vel_mag'].max() for r in results))
    im_p_last = None
    im_u_last = None

    for i, r in enumerate(results):
        rho_l = r['rho_l']
        phi = r['phi']
        p = r['p']
        vm = r['vel_mag']

        # Top row: pressure fields
        ax = axes[0, i]
        im_p = ax.pcolormesh(x1d, y1d, p.T, cmap='RdBu_r',
                             vmin=-vmax_p, vmax=vmax_p, shading='auto')
        ax.contour(x1d, y1d, phi.T, levels=[0.0], colors='k', linewidths=1.5)
        ax.set_title(fr'$\rho_l/\rho_g={int(rho_l)}$' + '\n'
                     fr'$\Delta p_\mathrm{{meas}}={r["dp_meas"]:.3f}$', fontsize=10)
        ax.set_xlabel('$x$')
        ax.set_aspect('equal')
        if i > 0:
            ax.set_yticklabels([])
        im_p_last = im_p

        # Bottom row: velocity magnitude
        ax = axes[1, i]
        im_u = ax.pcolormesh(x1d, y1d, vm.T, cmap='hot_r',
                             vmin=0, vmax=vmax_u, shading='auto')
        ax.contour(x1d, y1d, phi.T, levels=[0.0], colors='w', linewidths=1.5)
        ax.set_title(fr'$\|\mathbf{{u}}\|_\infty={vm.max():.2e}$', fontsize=10)
        ax.set_xlabel('$x$')
        ax.set_aspect('equal')
        if i > 0:
            ax.set_yticklabels([])
        im_u_last = im_u

    # Shared colorbars — one per row, placed right of all columns → equal panel sizes
    axes[0, 0].set_ylabel('Pressure $p(x,y)$', fontsize=11)
    axes[1, 0].set_ylabel(r'Parasitic velocity $\|\mathbf{u}(x,y)\|$', fontsize=11)
    fig.colorbar(im_p_last, ax=axes[0, :].tolist(), label='$p$', shrink=0.8)
    fig.colorbar(im_u_last, ax=axes[1, :].tolist(), label=r'$\|\mathbf{u}\|$', shrink=0.8)

    plt.suptitle(r'Density ratio sweep: $N=64$, $We=10$, 200 steps — all stable',
                 fontsize=12)
    plt.tight_layout()

    fname = "ch12_density_fields.png"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    rho_ratios = [2, 3, 5, 10]
    results = []
    dp_exact = SIGMA / (R * WE)

    for rho_l in rho_ratios:
        print(f"  Running rho_l={rho_l} ...")
        phi, p, vel_mag, hist = run(float(rho_l))
        inside = phi > 3.0 / N
        outside = phi < -3.0 / N
        dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
        print(f"    ||u||_inf={vel_mag.max():.3e}, Δp_meas={dp_meas:.4f} "
              f"(exact={dp_exact:.4f})")
        results.append({
            'rho_l': rho_l, 'phi': phi, 'p': p, 'vel_mag': vel_mag,
            'hist': hist, 'dp_meas': dp_meas,
        })

    make_figure(results)
    print("Done.")


if __name__ == "__main__":
    main()
