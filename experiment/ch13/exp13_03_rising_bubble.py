#!/usr/bin/env python3
"""[13-3] Single rising bubble — Hysing et al. (2009) benchmark (Case 1, modified).

Paper ref: §13.3 (sec:val_rising_bubble)

A gas bubble in a heavier liquid rises under gravity.  The bubble shape and
terminal rise velocity depend on the Reynolds (Re) and Eötvös (Eo) numbers.

Original Hysing Case 1 parameters:
  ρ_l/ρ_g = 1000,  μ_l/μ_g = 100,  Re = 35,  Eo = 10

This implementation uses ρ_l/ρ_g = 10 (monolithic PPE; the full density
ratio of 1000 requires the split-PPE + HFE pipeline — see §13.1 notes).
Re and Eo are held at the Case 1 values; μ and σ are derived from them.

Derivation (g = 1, d = 2R = 0.5)
----------------------------------
  Eo = g ρ_l d² / σ  →  σ = g ρ_l d² / Eo = 1 × 10 × 0.25 / 10 = 0.25
  Re = ρ_l sqrt(g d) d / μ_l  →  μ_l = ρ_l sqrt(g d) d / Re
     = 10 × sqrt(0.5) × 0.5 / 35 ≈ 0.1010

Setup
-----
  Domain  : [0, 1] × [0, 2],  wall BC (all sides)
  Bubble  : R = 0.25, centre (0.5, 0.5) at t = 0
  ρ_l = 10,  ρ_g = 1,  μ = μ_l (uniform approximation)
  Grid    : 64 × 128
  T_final : 3.0

Note: for the physical Hysing benchmark (ρ_l/ρ_g = 1000), variable
viscosity and split PPE are required for stability (§13 future work).

Metrics
-------
  - Terminal rise velocity v_t vs time  (steady when dv_t/dt ≈ 0)
  - Bubble centroid height y_c(t)
  - Circularity C = π (6V/π)^(2/3) / A  (sphericity in 2D)
  - Volume conservation: |ΔV|/V₀ < 0.5%

Reference
---------
  Hysing et al. (2009) Int. J. Num. Meth. Fluids 60, 1259–1288.

Output
------
  experiment/ch13/results/13_rising_bubble/
    rising_bubble.pdf    — centroid/velocity + snapshots
    data.npz             — raw data

Usage
-----
  python experiment/ch13/exp13_03_rising_bubble.py
  python experiment/ch13/exp13_03_rising_bubble.py --plot-only
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
OUT = experiment_dir(__file__, "13_rising_bubble")

# ── Parameters ──────────────────────────────────────────────────────────────
NX, NY   = 64, 128
LX, LY   = 1.0, 2.0
XC0, YC0 = 0.5, 0.5    # initial bubble centre
R        = 0.25
D_BUB    = 2.0 * R

# Hysing Case 1 non-dimensional numbers
RE       = 35.0
EO       = 10.0
G_ACC    = 1.0

# Density ratio  (reduced from Hysing's 1000 for monolithic PPE stability)
RHO_L    = 10.0
RHO_G    = 1.0
RHO_REF  = 0.5 * (RHO_L + RHO_G)

# Derived physical parameters
SIGMA    = G_ACC * RHO_L * D_BUB**2 / EO        # = 0.25
MU       = RHO_L * np.sqrt(G_ACC * D_BUB) * D_BUB / RE   # ≈ 0.1010

T_FINAL  = 3.0


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def _bubble_diagnostics(psi, u, v, X, Y, h):
    """Centroid, rise velocity, and circularity of the gas phase."""
    gas  = psi < 0.5
    vol  = float(np.sum(gas) * h**2)
    if vol < 1e-12:
        return 0.5, 0.5, 0.0, 1.0
    xc = float(np.sum(X[gas]) * h**2) / vol
    yc = float(np.sum(Y[gas]) * h**2) / vol
    vc = float(np.sum(v[gas]) * h**2) / vol   # mean y-velocity of gas

    # Circularity (2D): C = perimeter_circle / perimeter_actual
    # Approximated by: C = 2π sqrt(A/π) / perimeter
    # Perimeter via ∑ |∇psi| h  (interface length)
    dpsi_x = 0.5 * (np.roll(psi, -1, axis=0) - np.roll(psi, 1, axis=0)) / h
    dpsi_y = 0.5 * (np.roll(psi, -1, axis=1) - np.roll(psi, 1, axis=1)) / h
    perim = float(np.sum(np.sqrt(dpsi_x**2 + dpsi_y**2)) * h**2)
    r_eff = np.sqrt(vol / np.pi)
    circ  = 2.0 * np.pi * r_eff / perim if perim > 1e-12 else 1.0
    return xc, yc, vc, float(circ)


def run(T_final=T_FINAL, cfl=0.15, print_every=200):
    backend = Backend(use_gpu=False)
    h   = LX / NX
    eps = 1.5 * h

    gc   = GridConfig(ndim=2, N=(NX, NY), L=(LX, LY))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    ppb  = PPEBuilder(backend, grid, bc_type="wall")
    curv = CurvatureCalculator(backend, ccd, eps)
    hfe  = InterfaceLimitedFilter(backend, ccd, C=0.05)
    adv  = DissipativeCCDAdvection(backend, grid, ccd)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)

    X, Y = grid.meshgrid()

    # Gas bubble: phi > 0 inside bubble → psi = 0 inside (gas), 1 outside (liquid)
    phi = np.sqrt((X - XC0)**2 + (Y - YC0)**2) - R
    psi = np.asarray(heaviside(np, phi, eps))   # 1 in liquid, 0 in gas
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    dt_visc  = 0.25 * h**2 / (MU / RHO_G)
    dt_sigma = 0.25 * np.sqrt((RHO_L + RHO_G) * h**3 / (2.0 * np.pi * SIGMA))
    V0 = float(np.sum(1.0 - psi) * h**2)   # initial gas volume

    print(f"  Re={RE:.1f}  Eo={EO:.1f}  σ={SIGMA:.4f}  μ={MU:.5f}"
          f"  ρ_l/ρ_g={RHO_L/RHO_G:.0f}")

    times = []; yc_hist = []; vc_hist = []; circ_hist = []; vol_err_hist = []
    snap_times = [0.0, 1.0, 2.0, T_final]
    snapshots  = []
    snap_idx   = 0
    t = 0.0; step = 0

    while t < T_final and step < 300000:
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt = min(cfl * h / u_max, dt_visc, dt_sigma, T_final - t)
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

        # 4. PPE (balanced-force)
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

        xc, yc, vc, circ = _bubble_diagnostics(psi, u, v, X, Y, h)
        V_gas = float(np.sum(psi < 0.5) * h**2)
        dV    = abs(V_gas - V0) / V0
        ke    = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)

        times.append(t); yc_hist.append(yc); vc_hist.append(vc)
        circ_hist.append(circ); vol_err_hist.append(dV)

        if step % print_every == 0 or step <= 2:
            print(f"    step={step:5d}  t={t:.4f}  dt={dt:.5f}"
                  f"  yc={yc:.4f}  vc={vc:.4f}  C={circ:.4f}"
                  f"  |ΔV|/V₀={dV:.2e}  KE={ke:.3e}")
        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step={step}, t={t:.4f}")
            break

        if snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
            snapshots.append({"t": float(t), "psi": psi.copy()})
            snap_idx += 1

    return {
        "times":    np.array(times),
        "yc":       np.array(yc_hist),
        "vc":       np.array(vc_hist),
        "circ":     np.array(circ_hist),
        "vol_err":  np.array(vol_err_hist),
        "snapshots": snapshots,
    }


def plot(res):
    apply_style()
    times = res["times"]
    snaps = res["snapshots"]
    n_snaps = min(4, len(snaps))

    fig, axes = plt.subplots(2, n_snaps + 1,
                             figsize=(3.5 * (n_snaps + 1), 7))

    # Snapshots (top row)
    for i, snap in enumerate(snaps[:n_snaps]):
        ax = axes[0, i]
        ax.contourf(snap["psi"].T, levels=[0, 0.5], colors=[COLORS[0]])
        ax.contour(snap["psi"].T, levels=[0.5], colors=["k"], linewidths=0.8)
        ax.set_title(f"$t={snap['t']:.1f}$", fontsize=9)
        ax.set_aspect("equal"); ax.axis("off")

    # Centroid + velocity (bottom-left panel)
    ax = axes[1, 0]
    ax.plot(times, res["yc"], color=COLORS[0], label="$y_c$")
    ax.set_xlabel("$t$"); ax.set_ylabel("$y_c$")
    ax.set_title("Centroid height")

    ax2 = ax.twinx()
    ax2.plot(times, res["vc"], color=COLORS[1], ls="--", label="$v_c$")
    ax2.set_ylabel("Rise velocity $v_c$")

    # Circularity + volume error
    ax = axes[0, n_snaps]
    ax.plot(times, res["circ"], color=COLORS[2])
    ax.axhline(1.0, color="k", ls=":", lw=0.8)
    ax.set_xlabel("$t$"); ax.set_ylabel("Circularity $C$")
    ax.set_title("Circularity")

    ax = axes[1, n_snaps]
    ax.semilogy(times, np.array(res["vol_err"]) + 1e-16, color=COLORS[3])
    ax.set_xlabel("$t$"); ax.set_ylabel("$|\\Delta V|/V_0$")
    ax.set_title("Volume conservation")

    fig.suptitle(
        f"Single rising bubble  (Re={RE:.0f}, Eo={EO:.0f},"
        f"  $\\rho_l/\\rho_g={RHO_L/RHO_G:.0f}$)",
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
    save_figure(fig, OUT / "rising_bubble.pdf")
    print(f"[exp13-3] saved → {OUT}")


if __name__ == "__main__":
    main()
