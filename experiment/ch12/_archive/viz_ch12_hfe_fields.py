#!/usr/bin/env python3
"""§12.3 HFE comparison: OFF vs ON, 2D field visualization.

Runs static droplet at N=64, 50 steps with two conditions:
  OFF: standard projection (no HFE on pressure)
  ON:  HermiteFieldExtension applied to p before gradient (→ parasitic currents explode)

Shows why HFE must NOT be applied to smoothed-Heaviside solver pressure fields.

Output: results/ch12_static_droplet/ch12_hfe_comparison_fields.pdf
        paper/figures/ch12_hfe_comparison_fields.pdf
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
from twophase.hfe.field_extension import HermiteFieldExtension

OUT_RES = pathlib.Path(__file__).resolve().parent / "results" / "static_droplet"
OUT_FIG = pathlib.Path(__file__).resolve().parent / "results" / "static_droplet"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

N = 64
RHO_L, RHO_G = 2.0, 1.0
WE = 10.0
R = 0.25
SIGMA = 1.0
N_STEPS = 50  # fewer steps needed — HFE ON blows up quickly


def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run(use_hfe: bool):
    """Run static droplet simulation with or without HFE on pressure."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    hfe = HermiteFieldExtension(grid, ccd, backend) if use_hfe else None

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

        # HFE ON: extend pressure across interface before gradient computation
        # This overwrites target-phase values with source-phase extrapolation,
        # creating artificial discontinuities in ∇p for a field that is smooth.
        if use_hfe:
            p = hfe.extend(p, phi, source_sign=-1.0)  # extend gas→liquid

        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)

        if np.isnan(u_max) or u_max > 1e4:
            print(f"    {'HFE ON' if use_hfe else 'HFE OFF'}: blowup at step {step+1}")
            break

    vel_mag = np.sqrt(u**2 + v**2)
    return phi, p, vel_mag, u_max_hist


def make_figure(phi, p_off, vm_off, hist_off, p_on, vm_on, hist_on):
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    Ng = p_off.shape[0]
    x1d = np.linspace(0, 1, Ng)
    y1d = np.linspace(0, 1, Ng)

    def _plot_field(ax, data, phi, cmap, title, vmax=None):
        if vmax is None:
            vmax = max(abs(data.min()), abs(data.max()), 1e-12)
        im = ax.pcolormesh(x1d, y1d, data.T, cmap=cmap,
                           vmin=-vmax if cmap == 'RdBu_r' else 0,
                           vmax=vmax, shading='auto')
        ax.contour(x1d, y1d, phi.T, levels=[0.0], colors='k', linewidths=1.5)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('$x$'); ax.set_ylabel('$y$')
        ax.set_aspect('equal')
        return im

    # Shared scales across both rows for fair comparison
    vmax_p = max(abs(p_off.min()), abs(p_off.max()), abs(p_on.min()), abs(p_on.max()))
    vmax_u = max(vm_off.max(), vm_on.max(), 1e-10)

    # Row 0: HFE OFF
    im_p0 = _plot_field(axes[0, 0], p_off, phi, 'RdBu_r',
                        f'HFE OFF — Pressure\n$\\|\\mathbf{{u}}\\|_\\infty={vm_off.max():.2e}$',
                        vmax=vmax_p)
    im_u0 = _plot_field(axes[0, 1], vm_off, phi, 'hot_r',
                        f'HFE OFF — Parasitic velocity\npeak={vm_off.max():.2e}',
                        vmax=vmax_u)

    # Row 1: HFE ON
    im_p1 = _plot_field(axes[1, 0], p_on, phi, 'RdBu_r',
                        f'HFE ON — Pressure\n$\\|\\mathbf{{u}}\\|_\\infty={vm_on.max():.2e}$',
                        vmax=vmax_p)
    im_u1 = _plot_field(axes[1, 1], vm_on, phi, 'hot_r',
                        f'HFE ON — Parasitic velocity\npeak={vm_on.max():.2e}',
                        vmax=vmax_u)

    # Shared colorbars — one per column, placed to the right of all rows
    fig.colorbar(im_p0, ax=axes[:, 0].tolist(), label='$p$', shrink=0.6)
    fig.colorbar(im_u0, ax=axes[:, 1].tolist(), label=r'$\|\mathbf{u}\|$', shrink=0.6)

    ratio = vm_on.max() / max(vm_off.max(), 1e-30)
    plt.suptitle(
        f'HFE ON vs OFF: $\\rho_l/\\rho_g=2$, $N=64$, {N_STEPS} steps\n'
        f'Parasitic velocity ratio ON/OFF: {ratio:.1e}x',
        fontsize=12, y=1.01
    )
    plt.tight_layout()

    fname = "ch12_hfe_comparison_fields.pdf"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    print("viz_ch12_hfe_fields: HFE OFF ...")
    phi, p_off, vm_off, hist_off = run(use_hfe=False)
    print(f"  HFE OFF: ||u||_inf = {vm_off.max():.3e}")

    print("viz_ch12_hfe_fields: HFE ON ...")
    _, p_on, vm_on, hist_on = run(use_hfe=True)
    print(f"  HFE ON:  ||u||_inf = {vm_on.max():.3e}")

    ratio = vm_on.max() / max(vm_off.max(), 1e-30)
    print(f"  Ratio HFE ON / OFF = {ratio:.2e}")
    make_figure(phi, p_off, vm_off, hist_off, p_on, vm_on, hist_on)
    print("Done.")


if __name__ == "__main__":
    main()
