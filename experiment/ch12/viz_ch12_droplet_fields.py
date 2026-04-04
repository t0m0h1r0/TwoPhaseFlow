#!/usr/bin/env python3
"""§12.2 Static droplet 2D field visualization.

Runs static droplet (N=64, 200 steps, ρ_l/ρ_g=2, We=10) and produces:
  - 2D pressure field with interface contour (Laplace pressure jump)
  - 2D velocity magnitude (parasitic currents) with interface contour

Output: results/ch12_static_droplet/ch12_droplet_fields.png
        paper/figures/ch12_droplet_fields.png
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder

OUT_RES = pathlib.Path(__file__).resolve().parent / "results" / "static_droplet"
OUT_FIG = pathlib.Path(__file__).resolve().parent / "results" / "static_droplet"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

N = 64
RHO_L, RHO_G = 2.0, 1.0
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


def run():
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
    rho = RHO_G + (RHO_L - RHO_G) * psi

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

        u_max_hist.append(float(np.max(np.sqrt(u**2 + v**2))))

    vel_mag = np.sqrt(u**2 + v**2)
    return X, Y, phi, psi, p, u, v, vel_mag, u_max_hist


def make_figure(X, Y, phi, psi, p, u, v, vel_mag, u_max_hist):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # ── Panel A: Pressure field ──
    ax = axes[0]
    x1d = X[:, 0]
    y1d = Y[0, :]
    vmax = max(abs(p.min()), abs(p.max())) * 1.05
    im = ax.pcolormesh(x1d, y1d, p.T, cmap='RdBu_r', vmin=-vmax, vmax=vmax,
                       shading='auto')
    ax.contour(x1d, y1d, phi.T, levels=[0.0], colors='k', linewidths=1.5)
    ax.contour(x1d, y1d, psi.T, levels=[0.5], colors='w', linewidths=1.0,
               linestyles='--')
    plt.colorbar(im, ax=ax, label='$p$')
    dp_exact = SIGMA / (R * WE)
    inside = phi > 3.0 / N
    outside = phi < -3.0 / N
    dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    ax.set_title(
        r'Pressure $p(x,y)$' + '\n'
        fr'$\Delta p_\mathrm{{exact}}={dp_exact:.3f}$,'
        fr' $\Delta p_\mathrm{{meas}}={dp_meas:.3f}$',
        fontsize=10
    )
    ax.set_xlabel('$x$'); ax.set_ylabel('$y$')
    ax.set_aspect('equal')
    plt.colorbar(im, ax=ax, label='$p$')

    # ── Panel B: Velocity magnitude (parasitic currents) ──
    ax = axes[1]
    vmax_u = max(vel_mag.max(), 1e-10)
    im2 = ax.pcolormesh(x1d, y1d, vel_mag.T, cmap='hot_r', vmin=0, vmax=vmax_u,
                        shading='auto')
    ax.contour(x1d, y1d, phi.T, levels=[0.0], colors='w', linewidths=1.5)
    ax.set_title(r'Parasitic velocity $\|\mathbf{u}(x,y)\|$' + '\n'
                 fr'$\|\mathbf{{u}}\|_\infty={vmax_u:.2e}$', fontsize=10)
    ax.set_xlabel('$x$'); ax.set_ylabel('$y$')
    ax.set_aspect('equal')
    plt.colorbar(im2, ax=ax, label=r'$\|\mathbf{u}\|$')

    # ── Panel C: Velocity time history ──
    ax = axes[2]
    steps = np.arange(1, len(u_max_hist) + 1)
    ax.semilogy(steps, u_max_hist, 'b-', linewidth=1.2)
    ax.set_xlabel('Time step')
    ax.set_ylabel(r'$\|\mathbf{u}\|_\infty$')
    ax.set_title('Parasitic velocity history\n(200 steps)', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, N_STEPS)

    plt.suptitle(r'Static droplet: $\rho_l/\rho_g=2$, $We=10$, $N=64$',
                 fontsize=12, y=1.01)
    plt.tight_layout()

    fname = "ch12_droplet_fields.png"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    print("viz_ch12_droplet_fields: running N=64 static droplet ...")
    X, Y, phi, psi, p, u, v, vel_mag, u_max_hist = run()
    print(f"  ||u||_inf = {vel_mag.max():.3e}")
    make_figure(X, Y, phi, psi, p, u, v, vel_mag, u_max_hist)
    print("Done.")


if __name__ == "__main__":
    main()
