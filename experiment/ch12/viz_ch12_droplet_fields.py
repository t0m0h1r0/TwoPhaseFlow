#!/usr/bin/env python3
"""§12.2 Static droplet 2D field visualization.

Runs static droplet (N=64, 200 steps, ρ_l/ρ_g=2, We=10) and produces:
  - 2D pressure field with interface contour (Laplace pressure jump)
  - 2D velocity magnitude (parasitic currents) with interface contour

Output: results/ch12_static_droplet/ch12_droplet_fields.pdf
        paper/figures/ch12_droplet_fields.pdf
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
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.visualization.plot_vector import compute_vorticity_2d
from twophase.visualization.plot_fields import (
    field_with_contour, streamlines_colored, velocity_arrows,
)

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
    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)

    X, Y = grid.meshgrid()

    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    xp = backend.xp
    kappa_raw = curv_calc.compute(psi)
    kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
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
    omega = np.asarray(compute_vorticity_2d(u, v, ccd))
    return X, Y, phi, psi, p, u, v, vel_mag, u_max_hist, omega, grid, ccd


def make_figure(X, Y, phi, psi, p, u, v, vel_mag, u_max_hist, omega, grid, ccd):
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    x1d, y1d = X[:, 0], Y[0, :]
    vmax_u = max(float(vel_mag.max()), 1e-10)

    # ── (0,0) Pressure field ──
    vmax_p = max(abs(p.min()), abs(p.max())) * 1.05
    dp_exact = SIGMA / (R * WE)
    inside, outside = phi > 3.0 / N, phi < -3.0 / N
    dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    im = field_with_contour(
        axes[0, 0], x1d, y1d, p, cmap='RdBu_r', vmin=-vmax_p, vmax=vmax_p,
        contour_field=phi, contour_level=0.0, contour_color='k', contour_lw=1.5,
        title=f'Pressure $p(x,y)$\n'
              fr'$\Delta p_\mathrm{{exact}}={dp_exact:.3f}$,'
              fr' $\Delta p_\mathrm{{meas}}={dp_meas:.3f}$',
        ylabel='$y$')
    fig.colorbar(im, ax=axes[0, 0], label='$p$', shrink=0.9)

    # ── (0,1) Velocity magnitude ──
    im2 = field_with_contour(
        axes[0, 1], x1d, y1d, vel_mag, cmap='hot_r', vmin=0, vmax=vmax_u,
        contour_field=phi, contour_level=0.0, contour_color='w', contour_lw=1.5,
        title=r'Parasitic velocity $\|\mathbf{u}(x,y)\|$' + '\n'
              fr'$\|\mathbf{{u}}\|_\infty={vmax_u:.2e}$',
        ylabel='$y$')
    fig.colorbar(im2, ax=axes[0, 1], label=r'$\|\mathbf{u}\|$', shrink=0.9)

    # ── (0,2) Velocity time history ──
    ax = axes[0, 2]
    ax.semilogy(np.arange(1, len(u_max_hist) + 1), u_max_hist, 'b-', lw=1.2)
    ax.set(xlabel='Time step', ylabel=r'$\|\mathbf{u}\|_\infty$',
           title='Parasitic velocity history\n(200 steps)', xlim=(0, N_STEPS))
    ax.grid(True, alpha=0.3)

    # ── (1,0) Vorticity ──
    vmax_om = max(abs(float(omega.min())), abs(float(omega.max())), 1e-10) * 1.05
    im3 = field_with_contour(
        axes[1, 0], x1d, y1d, omega, cmap='RdBu_r', vmin=-vmax_om, vmax=vmax_om,
        contour_field=phi, contour_level=0.0, contour_color='k',
        contour_lw=1.5, contour_ls='--',
        title=r'Vorticity $\omega = \partial v/\partial x - \partial u/\partial y$',
        ylabel='$y$')
    fig.colorbar(im3, ax=axes[1, 0], label=r'$\omega$', shrink=0.9)

    # ── (1,1) Streamlines ──
    streamlines_colored(
        axes[1, 1], x1d, y1d, u, v, density=2.0,
        contour_field=phi, contour_level=0.0, contour_color='r')
    axes[1, 1].set(xlabel='$x$', ylabel='$y$',
                   title='Streamlines (colored by speed)')

    # ── (1,2) Velocity vectors ──
    velocity_arrows(
        axes[1, 2], X, Y, u, v, x1d, y1d,
        speed_vmax=vmax_u, contour_field=phi, contour_level=0.0)
    axes[1, 2].set(xlabel='$x$', ylabel='$y$', title='Velocity vectors')

    plt.suptitle(r'Static droplet: $\rho_l/\rho_g=2$, $We=10$, $N=64$',
                 fontsize=12, y=1.01)
    plt.tight_layout()

    fname = "ch12_droplet_fields.pdf"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    print("viz_ch12_droplet_fields: running N=64 static droplet ...")
    X, Y, phi, psi, p, u, v, vel_mag, u_max_hist, omega, grid, ccd = run()
    print(f"  ||u||_inf = {vel_mag.max():.3e}")
    make_figure(X, Y, phi, psi, p, u, v, vel_mag, u_max_hist, omega, grid, ccd)
    print("Done.")


if __name__ == "__main__":
    main()
