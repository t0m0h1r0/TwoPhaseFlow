#!/usr/bin/env python3
"""[13-7] Multiple bubble swarm rising in periodic domain (N = 9 bubbles).

Paper ref: §13.7 (sec:val_bubble_swarm)

N = 9 gas bubbles in a doubly-periodic liquid domain.
Bubbles rise collectively; hydrodynamic interaction reduces mean rise
velocity compared to a single bubble.

Measures:
  - U_swarm / U_single  vs. void fraction α
  - Volume conservation of the swarm (total liquid volume)
  - Long-time stability (no bubble escape through periodic boundary)

Setup
-----
  Domain : [0, 3] × [0, 3],  **doubly periodic** BC
  9 bubbles in 3 × 3 grid,  R = 0.25, small random perturbation
  ρ_l / ρ_g = 3,  Re = 50,  Eo = 4
  Grid: 128 × 128
  T_final = 10 (dimensionless)

Void fraction
-------------
  α = N π R² / (Lx Ly) = 9 × π × 0.25² / (3 × 3) ≈ 0.196

Metrics
-------
  - U_swarm: mean rise velocity averaged over all bubbles and T > 2
  - U_single: single-bubble rise velocity at same Re, Eo (from §13.3 or
    a separate single-bubble run)
  - |ΔV_total| / V_total,0 < 1 %

Reference
---------
  Tryggvason et al. (2001) J. Comput. Phys. 169, 708–759.
  Bunner & Tryggvason (2002) J. Fluid Mech. 466, 17–52.

Output
------
  experiment/ch13/results/13_bubble_swarm/
    swarm_snapshots.pdf      — psi snapshots at t = 0, 2, 5, 10
    swarm_velocity.pdf       — mean rise velocity and total volume vs time
    data.npz                 — raw data

Usage
-----
  python experiment/ch13/exp13_07_bubble_swarm.py
  python experiment/ch13/exp13_07_bubble_swarm.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__, "13_bubble_swarm")

# ── Parameters ──────────────────────────────────────────────────────────────
NX, NY   = 128, 128
LX, LY   = 3.0, 3.0
R        = 0.25
D_BUB    = 2.0 * R
RHO_L    = 3.0
RHO_G    = 1.0
RHO_REF  = 0.5 * (RHO_L + RHO_G)
EO       = 4.0
RE       = 50.0
G_ACC    = 1.0
SIGMA    = G_ACC * RHO_L * D_BUB**2 / EO
MU       = RHO_L * np.sqrt(G_ACC * D_BUB) * D_BUB / RE
T_FINAL  = 10.0

# 3×3 bubble grid centers (periodic domain [0,3]×[0,3])
_CENTERS = [(0.5 + 1.0 * i, 0.5 + 1.0 * j)
            for i in range(3) for j in range(3)]
N_BUB    = len(_CENTERS)
VOID_FRAC = N_BUB * np.pi * R**2 / (LX * LY)

rng = np.random.default_rng(42)
PERT = 0.01 * R   # small random perturbation to break symmetry


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _periodic_bc_vel(arr, axis=None):
    """No-op: periodic BC is handled by CCD and PPE operators."""
    pass


def run(T_final=T_FINAL, cfl=0.15, print_every=200):
    backend = Backend(use_gpu=False)
    h   = LX / NX
    eps = 1.5 * h

    gc  = GridConfig(ndim=2, N=(NX, NY), L=(LX, LY))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="periodic")
    ppb  = PPEBuilder(backend, grid, bc_type="periodic")
    curv = CurvatureCalculator(backend, ccd, eps)
    hfe  = InterfaceLimitedFilter(backend, ccd, C=0.05)
    adv  = DissipativeCCDAdvection(backend, grid, ccd)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)

    X, Y = grid.meshgrid()

    # Initial level set: phi = min_i( r_i - R ),  psi = 1 in liquid
    pert = rng.uniform(-PERT, PERT, (N_BUB, 2))
    phi  = np.full_like(X, np.inf)
    for k, (cx, cy) in enumerate(_CENTERS):
        cx += pert[k, 0]; cy += pert[k, 1]
        phi = np.minimum(phi, np.sqrt((X - cx)**2 + (Y - cy)**2) - R)
    psi = np.asarray(heaviside(np, phi, eps))

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    rho = RHO_G + (RHO_L - RHO_G) * psi
    dt_visc = 0.25 * h**2 / (MU / RHO_G)
    V_liq_0 = float(np.sum(psi) * h**2)

    times = []
    v_mean_hist = []
    vol_err_hist = []
    snapshots = []
    snap_times = [0.0, 2.0, 5.0, T_final]
    snap_idx = 0
    t = 0.0; step = 0

    alpha_str = f"{VOID_FRAC:.3f}"
    print(f"  Swarm: N={N_BUB}  α={alpha_str}  Re={RE:.1f}  Eo={EO:.1f}"
          f"  σ={SIGMA:.4f}  μ={MU:.5f}")

    while t < T_final and step < 500000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(cfl * h / u_max, dt_visc, T_final - t)
        if dt < 1e-12:
            break

        # 1. Advect + reinitialize
        psi = np.asarray(adv.advance(psi, [u, v], dt))
        if step % 2 == 0:
            psi = np.asarray(reinit.reinitialize(psi))
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # 2. Curvature + CSF
        xp = backend.xp
        kappa_raw = curv.compute(psi)
        kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_x = SIGMA * kappa * np.asarray(dpsi_dx)
        f_y = SIGMA * kappa * np.asarray(dpsi_dy)

        # 3. NS predictor with buoyancy (periodic: no wall BC)
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

        # 4. PPE
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s_dx) + np.asarray(dv_s_dy)) / dt
        df_x, _ = ccd.differentiate(f_x / rho, 0)
        df_y, _ = ccd.differentiate(f_y / rho, 1)
        rhs += np.asarray(df_x) + np.asarray(df_y)
        p = _solve_ppe(rhs, rho, ppb)

        # 5. Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_y / rho

        t += dt; step += 1

        # Diagnostics: mean rise velocity of gas phase
        gas_mask = psi < 0.5
        vol_gas  = float(np.sum(gas_mask) * h**2)
        if vol_gas > 1e-12:
            v_mean = float(np.sum(v[gas_mask]) * h**2) / vol_gas
        else:
            v_mean = 0.0
        V_liq = float(np.sum(psi) * h**2)
        dV_rel = abs(V_liq - V_liq_0) / V_liq_0
        ke = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)

        times.append(t)
        v_mean_hist.append(v_mean)
        vol_err_hist.append(dV_rel)

        if step % print_every == 0 or step <= 2:
            print(f"    step={step:5d}  t={t:.4f}  dt={dt:.5f}"
                  f"  v_mean={v_mean:.4f}  |ΔV|/V₀={dV_rel:.2e}  KE={ke:.3e}")
        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.4f}")
            break

        if snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snapshots.append({"t": float(t), "psi": psi.copy()})
            snap_idx += 1

    return {
        "times":    np.array(times),
        "v_mean":   np.array(v_mean_hist),
        "vol_err":  np.array(vol_err_hist),
        "snapshots": snapshots,
        "alpha":    VOID_FRAC,
    }


def plot(res):
    apply_style()
    times = res["times"]
    snaps = res["snapshots"]

    n_snaps = min(4, len(snaps))
    fig, axes = plt.subplots(1, n_snaps + 2,
                             figsize=(3.5 * (n_snaps + 2), 4))

    for i, snap in enumerate(snaps[:n_snaps]):
        ax = axes[i]
        ax.contourf(snap["psi"].T, levels=[0.45, 0.55], colors=[COLORS[0]])
        ax.contour(snap["psi"].T, levels=[0.5], colors=["k"], linewidths=0.8)
        ax.set_title(f"$t = {snap['t']:.1f}$", fontsize=9)
        ax.set_aspect("equal"); ax.axis("off")

    # Mean rise velocity
    ax = axes[n_snaps]
    ax.plot(times, res["v_mean"], color=COLORS[1])
    if len(times) > 100:
        t_stat = times[len(times) // 5:]  # skip transient
        v_stat = np.array(res["v_mean"])[len(times) // 5:]
        U_swarm = float(np.mean(v_stat))
        ax.axhline(U_swarm, color="r", ls="--", lw=0.8,
                   label=f"$U_\\mathrm{{swarm}} = {U_swarm:.3f}$")
        ax.legend(fontsize=8)
    ax.set_xlabel("$t$"); ax.set_ylabel("$v_\\mathrm{mean}$")
    ax.set_title(r"Mean rise velocity")

    # Volume error
    ax = axes[n_snaps + 1]
    ax.semilogy(times, np.array(res["vol_err"]) + 1e-16, color=COLORS[2])
    ax.set_xlabel("$t$"); ax.set_ylabel(r"$|\Delta V|/V_0$")
    ax.set_title("Volume conservation")

    α = res["alpha"]
    fig.suptitle(f"Bubble swarm  (N=9,  α={α:.3f},  Re={RE:.0f},  Eo={EO:.0f})",
                 fontsize=11)
    fig.tight_layout()
    return fig


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()

    npz_path = OUT / "data.npz"

    if args.plot_only:
        res = load_results(npz_path)
    else:
        res = run()
        save_results(npz_path, {k: v for k, v in res.items()
                                if isinstance(v, np.ndarray)})

    fig = plot(res)
    save_figure(fig, OUT / "swarm_velocity.pdf")
    print(f"[exp13-7] saved → {OUT}")


if __name__ == "__main__":
    main()
