#!/usr/bin/env python3
"""[13-5] Two-droplet head-on collision — coalescence and bouncing regimes.

Paper ref: §13.5 (sec:val_droplet_collision)

Two equal liquid droplets approach each other along the y-axis.
The Weber number (We = ρ_l v₀² d / σ) controls the outcome:
  We ≪ 1  →  coalescence (surface tension dominates)
  We ≫ 1  →  bouncing / reflexive separation (inertia dominates)

Tests topology change (CLS natural merging), volume conservation across
coalescence, and high-density-ratio stability of the balanced-force
projection.

Setup
-----
  Domain : [0, 1] × [0, 2],  wall BC (all sides)
  Droplets: R = 0.25, centers at (0.5, 0.65) and (0.5, 1.35)
            initial velocity: ±v₀ toward each other
  ρ_l / ρ_g = 5  (moderate; split PPE + HFE needed for ρ_l/ρ_g = 1000)
  σ = 1.0 (We = ρ_l v₀² d / σ  →  v₀ = sqrt(We σ / (ρ_l d)))
  no gravity
  Grid: 64 × 128
  We sweep: We = {0.5, 2.0, 5.0}

Metrics
-------
  - Volume conservation: |ΔV|/V₀ < 0.1 % through coalescence
  - Coalescence (We < We_crit): R_final / R₀ → 2^(1/3) ≈ 1.26 (mass cons.)
  - Bouncing (We > We_crit): max deformation D_max, rebound time

Reference
---------
  Nobari & Tryggvason (1996) J. Comput. Phys. 125, 70–90.
  Pan & Kawachi (2007) Phys. Fluids 19, 122105.

Output
------
  experiment/ch13/results/13_droplet_collision/
    collision_We{XXX}.pdf    — psi snapshots + volume + deformation history
    data_We{XXX}.npz         — raw data per We case
    summary.pdf              — outcome map (We vs deformation)

Usage
-----
  python experiment/ch13/exp13_05_droplet_collision.py
  python experiment/ch13/exp13_05_droplet_collision.py --plot-only
  python experiment/ch13/exp13_05_droplet_collision.py --we 2.0
"""

import sys, pathlib, argparse
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
    COLORS, MARKERS, FIGSIZE_2COL, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__, "13_droplet_collision")

# ── Physical parameters ──────────────────────────────────────────────────────
RHO_L    = 5.0    # liquid (inside droplets)
RHO_G    = 1.0    # gas    (outside)
RHO_REF  = 0.5 * (RHO_L + RHO_G)
MU       = 0.02   # uniform viscosity
SIGMA    = 1.0
R        = 0.25
D_DROP   = 2.0 * R
NX, NY   = 64, 128
LX, LY   = 1.0, 2.0
# Droplet centers — separated along y, approaching each other
Y1, Y2   = LY / 2.0 - 0.35, LY / 2.0 + 0.35   # (0.65, 1.35)
XC       = LX / 2.0
WE_CASES = [0.5, 2.0, 5.0]


def _v0_from_we(We):
    """Initial approach speed from Weber number: We = ρ_l v₀² (2R) / σ."""
    return np.sqrt(We * SIGMA / (RHO_L * D_DROP))


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def run(We, T_final=2.0, cfl=0.15, print_every=200):
    """Run two-droplet head-on collision at given Weber number."""
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

    # Two liquid droplets: phi > 0 inside → psi = 1 inside = liquid
    phi1 = R - np.sqrt((X - XC)**2 + (Y - Y1)**2)
    phi2 = R - np.sqrt((X - XC)**2 + (Y - Y2)**2)
    phi  = np.maximum(phi1, phi2)      # union: inside either droplet
    psi  = np.asarray(heaviside(np, phi, eps))

    # Initial velocity: droplet 1 (bottom) moves +y, droplet 2 (top) moves -y
    v0 = _v0_from_we(We)
    psi1 = np.asarray(heaviside(np, phi1, eps))
    psi2 = np.asarray(heaviside(np, phi2, eps))
    u = np.zeros_like(X)
    v = v0 * psi1 - v0 * psi2         # smooth velocity initialization

    rho = RHO_G + (RHO_L - RHO_G) * psi
    dt_visc = 0.25 * h**2 / (MU / RHO_G)
    V0 = float(np.sum(psi) * h**2)    # initial total liquid volume

    times, vol_err, deform = [], [], []
    snapshots = []
    snap_times = [0.0, 0.3, 0.6, 1.0, T_final]
    snap_idx = 0
    t = 0.0; step = 0

    print(f"  We={We:.2f}  v0={v0:.4f}  T_final={T_final}")

    while t < T_final and step < 300000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(cfl * h / u_max, dt_visc, T_final - t)
        if dt < 1e-12:
            break

        # 1. Advect + reinitialize
        psi = np.asarray(adv.advance(psi, [u, v], dt))
        if step % 2 == 0:
            psi = np.asarray(reinit.reinitialize(psi))
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # 2. Curvature (HFE-filtered) + CSF force
        xp = backend.xp
        kappa_raw = curv.compute(psi)
        kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_x = SIGMA * kappa * np.asarray(dpsi_dx)
        f_y = SIGMA * kappa * np.asarray(dpsi_dy)

        # 3. NS predictor (convection + viscous; no gravity)
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

        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v)
        _wall_bc(u_star); _wall_bc(v_star)

        # 4. PPE with CSF divergence source (balanced-force)
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s_dx) + np.asarray(dv_s_dy)) / dt
        df_x, _ = ccd.differentiate(f_x / rho, 0)
        df_y, _ = ccd.differentiate(f_y / rho, 1)
        rhs += np.asarray(df_x) + np.asarray(df_y)
        p = _solve_ppe(rhs, rho, ppb)

        # 5. Velocity corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_y / rho
        _wall_bc(u); _wall_bc(v)

        t += dt; step += 1

        # Diagnostics
        V = float(np.sum(psi) * h**2)
        dV = abs(V - V0) / V0
        # Deformation: bounding box aspect ratio of psi > 0.5 region
        mask = psi > 0.5
        if np.any(mask):
            ys = Y[mask]; xs = X[mask]
            L_ = float(ys.max() - ys.min())
            B_ = float(xs.max() - xs.min())
            D = abs(L_ - B_) / (L_ + B_) if (L_ + B_) > 0 else 0.0
        else:
            D = float("nan")
        ke = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)

        times.append(t); vol_err.append(dV); deform.append(D)

        if step % print_every == 0 or step <= 2:
            print(f"    step={step:5d}  t={t:.4f}  dt={dt:.5f}"
                  f"  |ΔV|/V₀={dV:.2e}  D={D:.3f}  KE={ke:.3e}")
        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.4f}")
            break

        # Snapshots
        if snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snapshots.append({"t": float(t), "psi": psi.copy(),
                               "u": u.copy(), "v": v.copy()})
            snap_idx += 1

    return {"We": We, "times": np.array(times),
            "vol_err": np.array(vol_err), "deform": np.array(deform),
            "snapshots": snapshots, "V0": V0}


def plot(results_list):
    """Summary figure: snapshots + diagnostics."""
    apply_style()
    fig, axes = plt.subplots(2, len(results_list),
                             figsize=(4.5 * len(results_list), 7.0))
    if len(results_list) == 1:
        axes = axes[:, None]

    for col, res in enumerate(results_list):
        We  = res["We"]
        snaps = res["snapshots"]
        t_end_snap = snaps[-1] if snaps else None

        # Top row: final psi snapshot
        ax = axes[0, col]
        if t_end_snap is not None:
            psi_snap = t_end_snap["psi"]
            ax.contourf(psi_snap.T, levels=[0.45, 0.55], colors=[COLORS[col]])
            ax.contour(psi_snap.T, levels=[0.5], colors=["k"], linewidths=0.8)
        ax.set_title(f"We = {We:.1f}  ($t = {t_end_snap['t']:.2f}$)"
                     if t_end_snap else f"We = {We:.1f}", fontsize=9)
        ax.set_aspect("equal"); ax.axis("off")

        # Bottom row: volume error + deformation
        ax2 = axes[1, col]
        ax2.semilogy(res["times"], res["vol_err"] + 1e-16,
                     color=COLORS[col], label=r"$|\Delta V|/V_0$")
        ax2_r = ax2.twinx()
        ax2_r.plot(res["times"], res["deform"],
                   color=COLORS[col], ls="--", alpha=0.7, label="$D$")
        ax2.set_xlabel("$t$"); ax2.set_ylabel(r"$|\Delta V|/V_0$")
        ax2_r.set_ylabel("deformation $D$")
        ax2.set_title(f"We = {We:.1f}", fontsize=9)

    fig.suptitle("Two-droplet head-on collision", fontsize=11)
    fig.tight_layout()
    return fig


def main():
    parser = experiment_argparser(description=__doc__)
    parser.add_argument("--we", type=float, default=None,
                        help="Single We case (default: all WE_CASES)")
    args = parser.parse_args()

    npz_path = OUT / "data.npz"

    if args.plot_only:
        data = load_results(npz_path)
        results = [{"We": float(w), **data[f"We{int(w*10):03d}"]}
                   for w in WE_CASES if f"We{int(w*10):03d}" in data]
    else:
        cases = [args.we] if args.we is not None else WE_CASES
        results = [run(We) for We in cases]

        save_dict = {}
        for res in results:
            key = f"We{int(res['We'] * 10):03d}"
            save_dict[key] = {k: v for k, v in res.items()
                              if isinstance(v, np.ndarray)}
        save_results(npz_path, save_dict)

    fig = plot(results)
    save_figure(fig, OUT / "collision_summary.pdf")
    print(f"[exp13-5] saved → {OUT}")


if __name__ == "__main__":
    main()
