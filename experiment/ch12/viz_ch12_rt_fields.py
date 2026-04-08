#!/usr/bin/env python3
"""§12.1 RT instability 2D field snapshots visualization.

Re-runs RT instability (64×256, T=2.5) with 2D snapshot saving:
  - density field ρ(x,y) at t=0, 1.0, 1.5, 2.5
  - pressure field p(x,y) at t=1.5, 2.5
  - velocity magnitude |u|(x,y) at t=1.5, 2.5

Output: results/ch12_rt/ch12_rt_fields.pdf
        paper/figures/ch12_rt_fields.pdf
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
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.visualization.plot_vector import compute_vorticity_2d
from twophase.visualization.plot_fields import (
    field_with_contour, streamlines_colored, symmetric_range,
)

OUT_RES = pathlib.Path(__file__).resolve().parent / "results" / "rt"
OUT_FIG = pathlib.Path(__file__).resolve().parent / "results" / "rt"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

RHO_L = 3.0
RHO_G = 1.0
RHO_REF = 2.0
MU = 0.01
G_ACC = 1.0
A0 = 0.05
K_WAV = 2 * np.pi
OMEGA_RT = np.sqrt(0.5 * G_ACC * K_WAV)

NX, NY = 64, 256
T_FINAL = 2.5
SNAP_TIMES = [0.0, 1.0, 1.5, 2.5]


def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run():
    backend = Backend(use_gpu=False)
    h = 1.0 / NX
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(NX, NY), L=(1.0, 4.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    ls_adv = DissipativeCCDAdvection(backend, grid, ccd)

    X, Y = grid.meshgrid()

    y_interface = 2.0 + A0 * np.sin(K_WAV * X)
    phi = Y - y_interface
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi
    u = np.zeros_like(X)
    v = np.zeros_like(X)
    p = np.zeros_like(X)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    dt_visc = 0.4 * h**2 / (MU / RHO_G)

    snapshots = []
    snap_idx = 0
    t = 0.0
    step = 0

    # t=0 snapshot
    snapshots.append({'t': 0.0, 'rho': rho.copy(), 'psi': psi.copy(),
                      'p': p.copy(), 'vel_mag': np.zeros_like(X),
                      'u': u.copy(), 'v': v.copy(),
                      'omega': np.zeros_like(X)})
    snap_idx = 1

    print(f"  Running RT: {NX}×{NY}, T={T_FINAL}, omega_RT={OMEGA_RT:.4f}")

    while t < T_FINAL and step < 500000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(0.2 * h / u_max, dt_visc, T_FINAL - t, 0.002)
        if dt < 1e-8:
            break

        # Advect
        psi = np.asarray(ls_adv.advance(psi, [u, v], dt))
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # Convection + viscous + buoyancy
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)

        du_dx = np.asarray(du_dx); du_xx = np.asarray(du_xx)
        du_dy = np.asarray(du_dy); du_yy = np.asarray(du_yy)
        dv_dx = np.asarray(dv_dx); dv_xx = np.asarray(dv_xx)
        dv_dy = np.asarray(dv_dy); dv_yy = np.asarray(dv_yy)

        conv_u = -(u * du_dx + v * du_dy)
        conv_v = -(u * dv_dx + v * dv_dy)
        visc_u = (MU / rho) * (du_xx + du_yy)
        visc_v = (MU / rho) * (dv_xx + dv_yy)
        buoy_v = -(rho - RHO_REF) / rho * G_ACC

        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v + buoy_v)
        wall_bc(u_star); wall_bc(v_star)

        du_star_dx, _ = ccd.differentiate(u_star, 0)
        dv_star_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_star_dx) + np.asarray(dv_star_dy)) / dt
        p = _solve_ppe(rhs, rho, ppe_builder)

        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        t += dt
        step += 1

        ke = float(np.sum(rho * (u**2 + v**2)) * h**2) / 2
        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.3f}")
            break

        # Snapshot
        while snap_idx < len(SNAP_TIMES) and t >= SNAP_TIMES[snap_idx]:
            vm = np.sqrt(u**2 + v**2)
            omega = np.asarray(compute_vorticity_2d(u, v, ccd))
            snapshots.append({'t': float(SNAP_TIMES[snap_idx]),
                               'rho': rho.copy(), 'psi': psi.copy(),
                               'p': p.copy(), 'vel_mag': vm.copy(),
                               'u': u.copy(), 'v': v.copy(),
                               'omega': omega.copy()})
            print(f"    Snapshot t={SNAP_TIMES[snap_idx]:.1f}, step={step}, "
                  f"KE={ke:.4e}")
            snap_idx += 1

        if step % 500 == 0:
            print(f"    step={step:6d}, t={t:.4f}")

    # Capture final snapshot if t=2.5 was missed (loop exits at t>=T_FINAL)
    if snap_idx < len(SNAP_TIMES):
        vm = np.sqrt(u**2 + v**2)
        omega = np.asarray(compute_vorticity_2d(u, v, ccd))
        snapshots.append({'t': float(t),
                           'rho': rho.copy(), 'psi': psi.copy(),
                           'p': p.copy(), 'vel_mag': vm.copy(),
                           'u': u.copy(), 'v': v.copy(),
                           'omega': omega.copy()})
        print(f"    Snapshot t={t:.3f} (final), step={step}")

    print(f"  Finished: step={step}, t={t:.3f}")
    return snapshots


def make_figure(snapshots):
    fig, axes = plt.subplots(5, 4, figsize=(16, 26))
    rho0 = snapshots[0]['rho']
    x1d = np.linspace(0, 1, rho0.shape[0])
    y1d = np.linspace(0, 4, rho0.shape[1])
    lim = dict(xlim=(0, 1), ylim=(0.5, 3.5))

    # Global scales
    vmin_rho = float(np.min([s['rho'] for s in snapshots]))
    vmax_rho = float(np.max([s['rho'] for s in snapshots]))
    vmax_p = symmetric_range([s['p'] for s in snapshots[1:]])
    vmax_vm = float(np.percentile(
        np.concatenate([s['vel_mag'].ravel() for s in snapshots[1:]]), 99)) * 1.05
    vmax_omega = symmetric_range([s['omega'] for s in snapshots[1:]])

    # Row definitions: (field_key, cmap, vmin, vmax, contour_color, contour_ls, label)
    for i, snap in enumerate(snapshots):
        psi_s = snap['psi']
        kw = dict(contour_field=psi_s, contour_level=0.5, **lim)

        im_rho = field_with_contour(
            axes[0, i], x1d, y1d, snap['rho'], cmap='Blues',
            vmin=vmin_rho, vmax=vmax_rho, contour_color='r', contour_lw=1.5,
            title=f'$t={snap["t"]:.1f}$', **kw)
        im_p = field_with_contour(
            axes[1, i], x1d, y1d, snap['p'], cmap='RdBu_r',
            vmin=-vmax_p, vmax=vmax_p, contour_color='k', **kw)
        im_vm = field_with_contour(
            axes[2, i], x1d, y1d, snap['vel_mag'], cmap='hot_r',
            vmin=0, vmax=vmax_vm, contour_color='w', **kw)
        im_om = field_with_contour(
            axes[3, i], x1d, y1d, snap['omega'], cmap='RdBu_r',
            vmin=-vmax_omega, vmax=vmax_omega, contour_color='k',
            contour_ls='--', **kw)
        streamlines_colored(
            axes[4, i], x1d, y1d, snap['u'], snap['v'],
            contour_field=psi_s, contour_level=0.5, contour_color='r')
        axes[4, i].set(**lim)
        axes[4, i].set_xlabel('$x$')

    # Row labels
    for r, label in enumerate([r'Density $\rho(x,y)$', r'Pressure $p(x,y)$',
                                r'Velocity $\|\mathbf{u}(x,y)\|$',
                                r'Vorticity $\omega(x,y)$', r'Streamlines']):
        axes[r, 0].set_ylabel(label, fontsize=11)

    # Shared colorbars
    for im, row, lbl in [(im_rho, 0, r'$\rho$'), (im_p, 1, '$p$'),
                          (im_vm, 2, r'$\|\mathbf{u}\|$'),
                          (im_om, 3, r'$\omega$')]:
        fig.colorbar(im, ax=axes[row, :].tolist(), label=lbl, shrink=0.7)
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(0, vmax_vm))
    sm.set_array([])
    fig.colorbar(sm, ax=axes[4, :].tolist(), label=r'$|\mathbf{u}|$', shrink=0.7)

    plt.suptitle(
        r'RT instability: $64\times256$, $At=0.5$, $\sigma=0$'
        '\n(red line = interface $\\psi=0.5$)', fontsize=13)
    plt.tight_layout()

    fname = "ch12_rt_fields.pdf"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    snapshots = run()
    print(f"\n  Got {len(snapshots)} snapshots: {[s['t'] for s in snapshots]}")
    make_figure(snapshots)
    print("Done.")


if __name__ == "__main__":
    main()
