#!/usr/bin/env python3
"""§12 Rising bubble experiment.

Light bubble (ρ_g=1) rising in heavy fluid (ρ_l=2) under gravity.
Non-incremental projection, FD PPE + CCD gradients, no HFE.

Setup (simplified Hysing-like):
  Domain: [0,1] × [0,2], wall BC
  Bubble: center (0.5, 0.5), R=0.25
  ρ_l=2 (liquid, outside), ρ_g=1 (gas, inside)
  σ/We = surface tension, g = gravity
  Re = ρ_l * U_ref * L / μ

Output: results/ch12_rising_bubble/
        paper/figures/ch12_rising_bubble.png
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
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder

OUT_RES = pathlib.Path(__file__).resolve().parents[2] / "results" / "ch12_rising_bubble"
OUT_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"
OUT_RES.mkdir(parents=True, exist_ok=True)
OUT_FIG.mkdir(parents=True, exist_ok=True)

# Physical parameters
NX, NY = 64, 128
RHO_L = 2.0      # liquid (outside, heavy)
RHO_G = 1.0      # gas (inside bubble, light)
RHO_REF = 1.5    # reference for buoyancy
MU = 0.01         # viscosity (both phases)
G_ACC = 1.0       # gravity magnitude (downward)
SIGMA = 0.1       # surface tension coefficient
WE = 1.0          # Weber number (σ/We enters CSF)
R = 0.25          # bubble radius
T_FINAL = 1.5
SNAP_TIMES = [0.0, 0.3, 0.6, 1.0, 1.5]


def run():
    backend = Backend(use_gpu=False)
    h = 1.0 / NX
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(NX, NY), L=(1.0, 2.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppb = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    ls_adv = DissipativeCCDAdvection(backend, grid, ccd)

    X, Y = grid.meshgrid()

    # Initial level set: bubble at (0.5, 0.5)
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_L + (RHO_G - RHO_L) * psi  # inside bubble = RHO_G
    u = np.zeros_like(X)
    v = np.zeros_like(X)
    p = np.zeros_like(X)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    dt_visc = 0.25 * h**2 / (MU / RHO_G)

    snapshots = []
    snap_idx = 0
    t = 0.0
    step = 0

    # t=0 snapshot
    snapshots.append({'t': 0.0, 'rho': rho.copy(), 'psi': psi.copy(),
                      'p': p.copy(), 'u': u.copy(), 'v': v.copy(),
                      'vel_mag': np.zeros_like(X)})
    snap_idx = 1

    # Bubble centroid and rise velocity tracking
    centroid_hist = []
    rise_vel_hist = []
    time_hist = []
    ke_hist = []

    print(f"  Running rising bubble: {NX}x{NY}, T={T_FINAL}")
    print(f"  rho_l={RHO_L}, rho_g={RHO_G}, mu={MU}, sigma={SIGMA}, g={G_ACC}")

    while t < T_FINAL and step < 500000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(0.2 * h / u_max, dt_visc, T_FINAL - t, 0.005)
        if dt < 1e-10:
            break

        # 1. Advect level set
        psi = np.asarray(ls_adv.advance(psi, [u, v], dt))
        rho = RHO_L + (RHO_G - RHO_L) * psi

        # 2. Curvature and CSF force
        kappa = curv_calc.compute(psi)
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_csf_x = SIGMA * kappa * np.asarray(dpsi_dx)
        f_csf_y = SIGMA * kappa * np.asarray(dpsi_dy)

        # 3. Convection + viscous + buoyancy
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
        csf_u = f_csf_x / rho
        csf_v = f_csf_y / rho

        u_star = u + dt * (conv_u + visc_u + csf_u)
        v_star = v + dt * (conv_v + visc_v + buoy_v + csf_v)
        wall_bc(u_star); wall_bc(v_star)

        # 4. PPE (FD spsolve)
        # Rebuild PPE matrix each step (rho changes)
        triplet, A_shape = ppb.build(rho)
        A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)

        du_star_dx, _ = ccd.differentiate(u_star, 0)
        dv_star_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_star_dx) + np.asarray(dv_star_dy)) / dt

        rhs_vec = rhs.ravel().copy()
        rhs_vec[ppb._pin_dof] = 0.0
        p = spsolve(A, rhs_vec).reshape(grid.shape)

        # 5. Corrector (CCD gradient)
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        t += dt
        step += 1

        # Track bubble
        # Centroid: weighted by gas fraction psi
        psi_sum = float(np.sum(psi))
        if psi_sum > 1e-10:
            y_c = float(np.sum(Y * psi)) / psi_sum
            v_rise = float(np.sum(v * psi)) / psi_sum
        else:
            y_c = 0.5; v_rise = 0.0

        ke = float(np.sum(rho * (u**2 + v**2)) * h * (2.0/NY)) / 2
        centroid_hist.append(y_c)
        rise_vel_hist.append(v_rise)
        time_hist.append(t)
        ke_hist.append(ke)

        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.3f}")
            break

        # Snapshot
        while snap_idx < len(SNAP_TIMES) and t >= SNAP_TIMES[snap_idx]:
            vm = np.sqrt(u**2 + v**2)
            snapshots.append({'t': float(SNAP_TIMES[snap_idx]),
                               'rho': rho.copy(), 'psi': psi.copy(),
                               'p': p.copy(), 'u': u.copy(), 'v': v.copy(),
                               'vel_mag': vm.copy()})
            print(f"    Snapshot t={SNAP_TIMES[snap_idx]:.1f}, step={step}, "
                  f"y_c={y_c:.4f}, v_rise={v_rise:.4f}, KE={ke:.4e}")
            snap_idx += 1

        if step % 200 == 0:
            print(f"    step={step:6d}, t={t:.4f}, y_c={y_c:.4f}, "
                  f"v_rise={v_rise:.4f}, dt={dt:.5f}")

    # Final snapshot
    if snap_idx < len(SNAP_TIMES):
        vm = np.sqrt(u**2 + v**2)
        snapshots.append({'t': float(t), 'rho': rho.copy(), 'psi': psi.copy(),
                           'p': p.copy(), 'u': u.copy(), 'v': v.copy(),
                           'vel_mag': vm.copy()})

    print(f"  Finished: step={step}, t={t:.3f}")
    return snapshots, time_hist, centroid_hist, rise_vel_hist, ke_hist


def make_figure(snapshots, time_hist, centroid_hist, rise_vel_hist, ke_hist):
    n_snaps = len(snapshots)

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, n_snaps, hspace=0.3, wspace=0.05,
                          height_ratios=[1.5, 1.5, 0.8])

    # Row 0: density/interface at each snapshot
    axes_rho = [fig.add_subplot(gs[0, i]) for i in range(n_snaps)]
    # Row 1: velocity magnitude at each snapshot
    axes_vel = [fig.add_subplot(gs[1, i]) for i in range(n_snaps)]
    # Row 2: time histories (3 subplots spanning all columns)
    gs_bot = gs[2, :].subgridspec(1, 3, wspace=0.3)
    ax_yc = fig.add_subplot(gs_bot[0])
    ax_vr = fig.add_subplot(gs_bot[1])
    ax_ke = fig.add_subplot(gs_bot[2])

    x1d = np.linspace(0, 1, snapshots[0]['rho'].shape[0])
    y1d = np.linspace(0, 2, snapshots[0]['rho'].shape[1])

    # Shared scales
    all_vm = np.concatenate([s['vel_mag'].ravel() for s in snapshots[1:]] or [np.array([0])])
    vmax_vm = float(np.percentile(all_vm, 99)) * 1.05 if len(all_vm) > 0 else 1.0

    for i, snap in enumerate(snapshots):
        t_s = snap['t']
        # Density / interface
        ax = axes_rho[i]
        ax.pcolormesh(x1d, y1d, snap['rho'].T, cmap='Blues',
                      vmin=RHO_G, vmax=RHO_L, shading='auto')
        ax.contour(x1d, y1d, snap['psi'].T, levels=[0.5], colors='r', linewidths=1.5)
        ax.set_title(f'$t={t_s:.1f}$', fontsize=11)
        ax.set_xlim(0, 1); ax.set_ylim(0, 2)
        ax.set_aspect('equal')
        if i > 0: ax.set_yticklabels([])

        # Velocity
        ax = axes_vel[i]
        ax.pcolormesh(x1d, y1d, snap['vel_mag'].T, cmap='hot_r',
                      vmin=0, vmax=vmax_vm, shading='auto')
        ax.contour(x1d, y1d, snap['psi'].T, levels=[0.5], colors='w', linewidths=1.2)
        ax.set_xlim(0, 1); ax.set_ylim(0, 2)
        ax.set_aspect('equal')
        if i > 0: ax.set_yticklabels([])

    axes_rho[0].set_ylabel(r'Density $\rho$', fontsize=11)
    axes_vel[0].set_ylabel(r'Velocity $|\mathbf{u}|$', fontsize=11)

    # Time histories
    t_arr = np.array(time_hist)
    ax_yc.plot(t_arr, centroid_hist, 'b-', linewidth=1.5)
    ax_yc.set_xlabel('$t$'); ax_yc.set_ylabel('Bubble centroid $y_c$')
    ax_yc.set_title('Centroid position'); ax_yc.grid(True, ls='--', alpha=0.4)

    ax_vr.plot(t_arr, rise_vel_hist, 'r-', linewidth=1.5)
    ax_vr.set_xlabel('$t$'); ax_vr.set_ylabel('Rise velocity $v_{rise}$')
    ax_vr.set_title('Rise velocity'); ax_vr.grid(True, ls='--', alpha=0.4)

    ax_ke.plot(t_arr, ke_hist, 'g-', linewidth=1.5)
    ax_ke.set_xlabel('$t$'); ax_ke.set_ylabel('Kinetic energy')
    ax_ke.set_title('Kinetic energy'); ax_ke.grid(True, ls='--', alpha=0.4)

    plt.suptitle(
        fr'Rising bubble: $\rho_l/\rho_g={RHO_L/RHO_G:.0f}$, '
        fr'${NX}\times{NY}$, $\sigma={SIGMA}$, $\mu={MU}$'
        '\n(FD PPE + CCD gradient, no HFE)',
        fontsize=12
    )

    fname = "ch12_rising_bubble.png"
    fig.savefig(OUT_RES / fname, dpi=150, bbox_inches="tight")
    fig.savefig(OUT_FIG / fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT_FIG / fname}")


def main():
    snaps, t_hist, yc, vr, ke = run()
    print(f"\n  Got {len(snaps)} snapshots: {[s['t'] for s in snaps]}")
    make_figure(snaps, t_hist, yc, vr, ke)
    print("Done.")


if __name__ == "__main__":
    main()
