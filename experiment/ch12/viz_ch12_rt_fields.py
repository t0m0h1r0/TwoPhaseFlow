#!/usr/bin/env python3
"""§12.1 RT instability 2D field snapshots visualization.

Re-runs RT instability (64×256, T=2.5) with 2D snapshot saving:
  - density field ρ(x,y) at t=0, 1.0, 1.5, 2.5
  - pressure field p(x,y) at t=1.5, 2.5
  - velocity magnitude |u|(x,y) at t=1.5, 2.5

Output: results/ch12_rt/ch12_rt_fields.png
        paper/figures/ch12_rt_fields.png
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
                      'p': p.copy(), 'vel_mag': np.zeros_like(X)})
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
            snapshots.append({'t': float(SNAP_TIMES[snap_idx]),
                               'rho': rho.copy(), 'psi': psi.copy(),
                               'p': p.copy(), 'vel_mag': vm.copy()})
            print(f"    Snapshot t={SNAP_TIMES[snap_idx]:.1f}, step={step}, "
                  f"KE={ke:.4e}")
            snap_idx += 1

        if step % 500 == 0:
            print(f"    step={step:6d}, t={t:.4f}")

    # Capture final snapshot if t=2.5 was missed (loop exits at t>=T_FINAL)
    if snap_idx < len(SNAP_TIMES):
        vm = np.sqrt(u**2 + v**2)
        snapshots.append({'t': float(t),
                           'rho': rho.copy(), 'psi': psi.copy(),
                           'p': p.copy(), 'vel_mag': vm.copy()})
        print(f"    Snapshot t={t:.3f} (final), step={step}")

    print(f"  Finished: step={step}, t={t:.3f}")
    return snapshots


def make_figure(snapshots):
    # Use t=0, 1.0, 1.5, 2.5 for density, t=1.5, 2.5 for p and vel
    fig, axes = plt.subplots(3, 4, figsize=(16, 16))

    rho0 = snapshots[0]['rho']
    x1d = np.linspace(0, 1, rho0.shape[0])
    y1d = np.linspace(0, 4, rho0.shape[1])

    # Row 0: density field ρ at 4 snapshots
    all_rho = np.concatenate([s['rho'].ravel() for s in snapshots])
    vmin_rho, vmax_rho = float(np.min(all_rho)), float(np.max(all_rho))

    # Row 1: pressure p at 4 snapshots
    all_p = np.concatenate([s['p'].ravel() for s in snapshots[1:]])
    vmax_p = float(np.percentile(np.abs(all_p), 98)) * 1.05

    # Row 2: velocity magnitude at 4 snapshots
    all_vm = np.concatenate([s['vel_mag'].ravel() for s in snapshots[1:]])
    vmax_vm = float(np.percentile(all_vm, 99)) * 1.05

    for i, snap in enumerate(snapshots):
        t_snap = snap['t']
        rho_s = snap['rho']
        psi_s = snap['psi']
        p_s = snap['p']
        vm_s = snap['vel_mag']

        # Density
        ax = axes[0, i]
        im_rho = ax.pcolormesh(x1d, y1d, rho_s.T, cmap='Blues',
                               vmin=vmin_rho, vmax=vmax_rho, shading='auto')
        ax.contour(x1d, y1d, psi_s.T, levels=[0.5], colors='r', linewidths=1.5)
        ax.set_title(f'$t={t_snap:.1f}$', fontsize=11)
        ax.set_xlabel('$x$')
        ax.set_xlim(0, 1); ax.set_ylim(0.5, 3.5)
        ax.set_aspect('equal')

        # Pressure
        ax = axes[1, i]
        im_p = ax.pcolormesh(x1d, y1d, p_s.T, cmap='RdBu_r',
                             vmin=-vmax_p, vmax=vmax_p, shading='auto')
        ax.contour(x1d, y1d, psi_s.T, levels=[0.5], colors='k', linewidths=1.2)
        ax.set_xlabel('$x$')
        ax.set_xlim(0, 1); ax.set_ylim(0.5, 3.5)
        ax.set_aspect('equal')

        # Velocity magnitude
        ax = axes[2, i]
        im_vm = ax.pcolormesh(x1d, y1d, vm_s.T, cmap='hot_r',
                              vmin=0, vmax=vmax_vm, shading='auto')
        ax.contour(x1d, y1d, psi_s.T, levels=[0.5], colors='w', linewidths=1.2)
        ax.set_xlabel('$x$')
        ax.set_xlim(0, 1); ax.set_ylim(0.5, 3.5)
        ax.set_aspect('equal')

    # Row labels
    axes[0, 0].set_ylabel(r'Density $\rho(x,y)$', fontsize=11)
    axes[1, 0].set_ylabel(r'Pressure $p(x,y)$', fontsize=11)
    axes[2, 0].set_ylabel(r'Velocity $\|\mathbf{u}(x,y)\|$', fontsize=11)

    # Shared colorbars — one per row → equal panel sizes
    fig.colorbar(im_rho, ax=axes[0, :].tolist(), label=r'$\rho$', shrink=0.7)
    fig.colorbar(im_p,   ax=axes[1, :].tolist(), label='$p$',      shrink=0.7)
    fig.colorbar(im_vm,  ax=axes[2, :].tolist(), label=r'$\|\mathbf{u}\|$', shrink=0.7)

    plt.suptitle(
        r'RT instability: $64\times256$, $At=0.5$, $\sigma=0$'
        '\n(red line = interface $\\psi=0.5$)',
        fontsize=13
    )
    plt.tight_layout()

    fname = "ch12_rt_fields.png"
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
