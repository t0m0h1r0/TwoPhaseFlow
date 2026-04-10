#!/usr/bin/env python3
"""[13-6] Two-bubble Drafting–Kissing–Tumbling (DKT) interaction.

Paper ref: §13.6 (sec:val_two_bubble_dkt)

Two identical gas bubbles aligned vertically in liquid.
The trailing bubble drafts in the wake of the leading bubble
(accelerates), then approaches near-contact (kissing), then
tumbles laterally (DKT instability).

This validates wake-mediated hydrodynamic interaction and multi-body
variable-density solver stability under long-time integration.

Setup
-----
  Domain : [0, 1] × [0, 4],  wall BC (all sides)
  Two bubbles: R = 0.25, centers at (0.5, 0.5) and (0.5, 1.1)
               trailing bubble (bottom), leading bubble (top)
  ρ_l / ρ_g = 5  (moderate; ρ_l/ρ_g = 1000 with split PPE + HFE)
  Re = ρ_l U_ref R / μ = 35,  Eo = g ρ_l (2R)² / σ = 10
  Non-dim: R = 0.25, ρ_l = 5, g = Eo σ / (ρ_l d²) = Eo σ / (ρ_l 4R²)
  Grid: 64 × 256

Metrics
-------
  - Δy(t) = y_lead - y_trail time series showing DKT phases:
      drafting (Δy decreasing), kissing (Δy ≈ 0.1R), tumbling (Δx grows)
  - Peak v_trail ≥ 1.2 × v_lead (drafting enhancement)
  - Volume conservation: |ΔV|/V₀ < 0.5% per bubble

Reference
---------
  Esmaeeli & Tryggvason (1998) J. Fluid Mech. 376, 81–111.
  Krishna & van Baten (1999) Chem. Eng. Sci. 54, 5501–5510.

Output
------
  experiment/ch13/results/13_two_bubble_dkt/
    dkt_snapshots.pdf        — psi snapshots at characteristic times
    dkt_trajectories.pdf     — y-centroid and x-separation vs time
    data.npz                 — raw trajectory + volume data

Usage
-----
  python experiment/ch13/exp13_06_two_bubble_dkt.py
  python experiment/ch13/exp13_06_two_bubble_dkt.py --plot-only
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
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__, "13_two_bubble_dkt")

# ── Non-dimensional parameters (Hysing-like) ────────────────────────────────
# Eo = g ρ_l d² / σ = 10   (Eötvös number)
# Re = ρ_l U_ref d / μ = 35  (U_ref = sqrt(g d))
# ρ_l / ρ_g = 5  (moderate; target = 1000 with split PPE)
NX, NY    = 64, 256
LX, LY    = 1.0, 4.0
R         = 0.25
D_BUB     = 2.0 * R
RHO_L     = 5.0
RHO_G     = 1.0
RHO_REF   = 0.5 * (RHO_L + RHO_G)
# g, σ from Eo and Re:  Eo = g ρ_l d² / σ,  Re = ρ_l sqrt(g d) d / μ
EO        = 10.0
RE        = 35.0
G_ACC     = 1.0
SIGMA     = G_ACC * RHO_L * D_BUB**2 / EO          # = ρ_l g d² / Eo
MU        = RHO_L * np.sqrt(G_ACC * D_BUB) * D_BUB / RE
# Initial bubble positions (trailing bottom, leading top)
YC_TRAIL  = 0.5        # trailing (bottom) bubble center
YC_LEAD   = 1.1        # leading  (top)    bubble center  (gap ≈ 0.1R)
XC        = LX / 2.0
T_FINAL   = 4.0


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def _bubble_centroid(psi_inv, X, Y, h):
    """Return (x_c, y_c) of gas bubble from (1 - psi) indicator."""
    mass = float(np.sum(psi_inv) * h**2)
    if mass < 1e-12:
        return float(np.mean(X)), float(np.mean(Y))
    xc = float(np.sum(X * psi_inv) * h**2) / mass
    yc = float(np.sum(Y * psi_inv) * h**2) / mass
    return xc, yc


def run(T_final=T_FINAL, cfl=0.15, print_every=200):
    backend = Backend(use_gpu=False)
    h   = LX / NX
    eps = 1.5 * h

    gc  = GridConfig(ndim=2, N=(NX, NY), L=(LX, LY))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    ppb  = PPEBuilder(backend, grid, bc_type="wall")
    curv = CurvatureCalculator(backend, ccd, eps)
    hfe  = InterfaceLimitedFilter(backend, ccd, C=0.05)
    adv  = DissipativeCCDAdvection(backend, grid, ccd)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)

    X, Y = grid.meshgrid()

    # Two gas bubbles: phi = r - R,  phi > 0 outside → psi = 1 outside = liquid
    phi_trail = np.sqrt((X - XC)**2 + (Y - YC_TRAIL)**2) - R
    phi_lead  = np.sqrt((X - XC)**2 + (Y - YC_LEAD )**2) - R
    phi  = np.minimum(phi_trail, phi_lead)   # in liquid only outside BOTH bubbles
    psi  = np.asarray(heaviside(np, phi, eps))

    # psi_inv_*: (1 - psi) indicator used for centroid tracking
    psi_inv_trail = np.asarray(heaviside(np, -phi_trail, eps))
    psi_inv_lead  = np.asarray(heaviside(np, -phi_lead,  eps))

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    rho = RHO_G + (RHO_L - RHO_G) * psi
    dt_visc = 0.25 * h**2 / (MU / RHO_G)
    V0_each = np.pi * R**2   # analytical gas volume per bubble

    # Trajectory storage
    times = []
    xc_trail_hist, yc_trail_hist = [], []
    xc_lead_hist,  yc_lead_hist  = [], []
    vc_trail_hist, vc_lead_hist  = [], []
    vol_trail_hist, vol_lead_hist = [], []
    snapshots = []
    snap_times = [0.0, 0.5, 1.0, 2.0, T_final]
    snap_idx = 0
    t = 0.0; step = 0

    print(f"  DKT: Re={RE:.1f}  Eo={EO:.1f}  σ={SIGMA:.4f}  μ={MU:.5f}")

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

        # Track individual bubble indicators
        psi_inv_trail = np.clip(1.0 - psi - 0.5 * np.asarray(
            heaviside(np, -phi_lead + eps, eps)), 0.0, 1.0)
        psi_inv_lead  = np.clip(1.0 - psi - 0.5 * np.asarray(
            heaviside(np, -phi_trail + eps, eps)), 0.0, 1.0)

        # 2. Curvature + CSF
        xp = backend.xp
        kappa_raw = curv.compute(psi)
        kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_x = SIGMA * kappa * np.asarray(dpsi_dx)
        f_y = SIGMA * kappa * np.asarray(dpsi_dy)

        # 3. NS predictor with buoyancy
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
        _wall_bc(u_star); _wall_bc(v_star)

        # 4. PPE + balanced-force CSF
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
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_y / rho
        _wall_bc(u); _wall_bc(v)

        t += dt; step += 1

        # Diagnostics: track total liquid-free psi region for each bubble
        psi_gas = 1.0 - psi  # gas indicator (1 inside any bubble)
        # Partition gas between bubbles by proximity to initial centers
        d_trail = np.sqrt((X - XC)**2 + (Y - YC_TRAIL)**2)
        d_lead  = np.sqrt((X - XC)**2 + (Y - YC_LEAD)**2)
        mask_trail = (d_trail < d_lead) & (psi < 0.5)
        mask_lead  = (d_trail >= d_lead) & (psi < 0.5)

        vol_trail = float(np.sum(mask_trail) * h**2)
        vol_lead  = float(np.sum(mask_lead)  * h**2)
        yc_t = float(np.sum(Y[mask_trail]) * h**2) / max(vol_trail, 1e-12)
        yc_l = float(np.sum(Y[mask_lead])  * h**2) / max(vol_lead,  1e-12)
        xc_t = float(np.sum(X[mask_trail]) * h**2) / max(vol_trail, 1e-12)
        xc_l = float(np.sum(X[mask_lead])  * h**2) / max(vol_lead,  1e-12)
        vc_t = float(np.sum(v[mask_trail] * 1.0)   * h**2) / max(vol_trail, 1e-12)
        vc_l = float(np.sum(v[mask_lead]  * 1.0)   * h**2) / max(vol_lead,  1e-12)
        ke   = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)

        times.append(t)
        yc_trail_hist.append(yc_t); yc_lead_hist.append(yc_l)
        xc_trail_hist.append(xc_t); xc_lead_hist.append(xc_l)
        vc_trail_hist.append(vc_t); vc_lead_hist.append(vc_l)
        vol_trail_hist.append(vol_trail); vol_lead_hist.append(vol_lead)

        if step % print_every == 0 or step <= 2:
            dy = yc_l - yc_t
            dx = abs(xc_l - xc_t)
            print(f"    step={step:5d}  t={t:.4f}  Δy={dy:.3f}  Δx={dx:.3f}"
                  f"  v_trail={vc_t:.4f}  v_lead={vc_l:.4f}  KE={ke:.3e}")

        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.4f}")
            break

        if snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snapshots.append({"t": float(t), "psi": psi.copy(),
                               "u": u.copy(), "v": v.copy()})
            snap_idx += 1

    return {
        "times":    np.array(times),
        "yc_trail": np.array(yc_trail_hist),
        "yc_lead":  np.array(yc_lead_hist),
        "xc_trail": np.array(xc_trail_hist),
        "xc_lead":  np.array(xc_lead_hist),
        "vc_trail": np.array(vc_trail_hist),
        "vc_lead":  np.array(vc_lead_hist),
        "vol_trail": np.array(vol_trail_hist),
        "vol_lead":  np.array(vol_lead_hist),
        "V0_each":  V0_each,
        "snapshots": snapshots,
    }


def plot(res):
    apply_style()
    times = res["times"]

    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE_2COL + (2.0,) if hasattr(FIGSIZE_2COL, "__add__") else (12, 4))

    # Panel 1: y-centroid trajectories
    ax = axes[0]
    ax.plot(times, res["yc_trail"], color=COLORS[0], label="trailing")
    ax.plot(times, res["yc_lead"],  color=COLORS[1], label="leading")
    ax.set_xlabel("$t$"); ax.set_ylabel("$y_c$")
    ax.set_title("Bubble centroid height"); ax.legend(fontsize=8)

    # Panel 2: separation Δy(t) and Δx(t)
    ax = axes[1]
    dy = np.array(res["yc_lead"]) - np.array(res["yc_trail"])
    dx = np.abs(np.array(res["xc_lead"]) - np.array(res["xc_trail"]))
    ax.plot(times, dy, color=COLORS[0], label=r"$\Delta y$")
    ax.plot(times, dx, color=COLORS[1], ls="--", label=r"$\Delta x$")
    ax.axhline(0, color="k", lw=0.5, ls=":")
    ax.set_xlabel("$t$"); ax.set_ylabel("separation")
    ax.set_title("DKT separation"); ax.legend(fontsize=8)

    # Panel 3: rise velocities
    ax = axes[2]
    ax.plot(times, res["vc_trail"], color=COLORS[0], label="trailing $v_c$")
    ax.plot(times, res["vc_lead"],  color=COLORS[1], label="leading $v_c$")
    ax.set_xlabel("$t$"); ax.set_ylabel("$v_c$")
    ax.set_title("Rise velocity"); ax.legend(fontsize=8)

    fig.suptitle("Two-bubble DKT (Drafting–Kissing–Tumbling)", fontsize=11)
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
    save_figure(fig, OUT / "dkt_trajectories.pdf")
    print(f"[exp13-6] saved → {OUT}")


if __name__ == "__main__":
    main()
