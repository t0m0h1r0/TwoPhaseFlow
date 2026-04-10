#!/usr/bin/env python3
"""[13-1] Static droplet parasitic current — grid convergence study.

Paper ref: §13.1 (sec:val_static_drop)

A static liquid droplet in quiescent gas is in mechanical equilibrium:
the Laplace pressure jump Δp = σ / R balances the surface tension force.
Any residual flow (parasitic / spurious current) indicates an imbalance
in the numerical surface tension implementation.

Setup
-----
  Domain  : [0, 1] × [0, 1],  wall BC
  Droplet : R = 0.25, centred at (0.5, 0.5)
  ρ_l / ρ_g = 100,  μ = 0.01 (uniform),  σ = 1.0,  no gravity
  Grid sweep : N ∈ {32, 64, 128, 256}
  T_run : 500 steps per grid (sufficient to reach quasi-steady parasitic level)

Metrics
-------
  - ‖u_para‖_∞ = max(|u|, |v|) at end of run vs. N  (target: O(h²) or better)
  - Δp error : |Δp_sim − σ/R| / (σ/R) < 0.1 %  for N ≥ 128
    where Δp_sim = mean(p inside) − mean(p outside)

Reference
---------
  Popinet (2009) J. Comput. Phys. 228, 5838–5866.
  Francois et al. (2006) J. Comput. Phys. 213, 141–173.

Output
------
  experiment/ch13/results/13_static_droplet/
    parasitic_convergence.pdf   — ‖u_para‖_∞ and Δp error vs N
    data.npz                    — raw data

Usage
-----
  python experiment/ch13/exp13_01_static_droplet.py
  python experiment/ch13/exp13_01_static_droplet.py --plot-only
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
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__, "13_static_droplet")

# ── Parameters ──────────────────────────────────────────────────────────────
R        = 0.25
LX, LY   = 1.0, 1.0
XC, YC   = 0.5, 0.5
RHO_L    = 100.0
RHO_G    = 1.0
RHO_REF  = 0.5 * (RHO_L + RHO_G)
MU       = 0.01
SIGMA    = 1.0
N_GRIDS  = [32, 64, 128, 256]
N_STEPS  = 500    # steps per grid


def _solve_ppe(rhs, rho, ppb):
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppb._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _wall_bc(arr):
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def run_one(N, n_steps=N_STEPS):
    backend = Backend(use_gpu=False)
    h   = LX / N
    eps = 1.5 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(LX, LY))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    ppb  = PPEBuilder(backend, grid, bc_type="wall")
    curv = CurvatureCalculator(backend, ccd, eps)
    hfe  = InterfaceLimitedFilter(backend, ccd, C=0.05)
    adv  = DissipativeCCDAdvection(backend, grid, ccd)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)

    X, Y = grid.meshgrid()
    phi  = R - np.sqrt((X - XC)**2 + (Y - YC)**2)
    psi  = np.asarray(heaviside(np, phi, eps))
    rho  = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    dt_visc = 0.25 * h**2 / (MU / RHO_G)
    dt_sigma = 0.25 * np.sqrt((RHO_L + RHO_G) * h**3 / (2.0 * np.pi * SIGMA))
    dt = min(dt_visc, dt_sigma)

    u_max_hist = []

    for step in range(n_steps):
        # Advect + reinitialize (even for "static" droplet, keeps psi smooth)
        psi = np.asarray(adv.advance(psi, [u, v], dt))
        if step % 2 == 0:
            psi = np.asarray(reinit.reinitialize(psi))
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # Curvature + CSF
        xp = backend.xp
        kappa_raw = curv.compute(psi)
        kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_x = SIGMA * kappa * np.asarray(dpsi_dx)
        f_y = SIGMA * kappa * np.asarray(dpsi_dy)

        # NS predictor (no gravity, uniform viscosity)
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

        # PPE (balanced-force)
        du_s_dx, _ = ccd.differentiate(u_star, 0)
        dv_s_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_s_dx) + np.asarray(dv_s_dy)) / dt
        df_x, _ = ccd.differentiate(f_x / rho, 0)
        df_y, _ = ccd.differentiate(f_y / rho, 1)
        rhs += np.asarray(df_x) + np.asarray(df_y)
        p = _solve_ppe(rhs, rho, ppb)

        # Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx) + dt * f_x / rho
        v = v_star - dt / rho * np.asarray(dp_dy) + dt * f_y / rho
        _wall_bc(u); _wall_bc(v)

        u_max = float(np.max(np.abs(u)**2 + np.abs(v)**2)**0.5)
        u_max_hist.append(u_max)
        if np.isnan(u_max) or u_max > 1e4:
            print(f"    N={N}: BLOWUP at step={step}")
            break

    # Laplace pressure error
    inside  = psi > 0.5
    outside = psi < 0.5
    p_in  = float(np.mean(p[inside]))  if np.any(inside)  else 0.0
    p_out = float(np.mean(p[outside])) if np.any(outside) else 0.0
    dp_sim    = p_in - p_out
    dp_theory = SIGMA / R
    dp_err    = abs(dp_sim - dp_theory) / dp_theory

    u_para = float(np.max(np.sqrt(u**2 + v**2)))

    print(f"  N={N:4d}  h={h:.5f}  u_para={u_para:.3e}"
          f"  Δp_err={dp_err:.3e}")
    return {"N": N, "h": h, "u_para": u_para,
            "dp_err": dp_err, "u_max_hist": np.array(u_max_hist)}


def run():
    results = []
    for N in N_GRIDS:
        results.append(run_one(N))
    return results


def plot(results):
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    hs     = np.array([r["h"]      for r in results])
    u_para = np.array([r["u_para"] for r in results])
    dp_err = np.array([r["dp_err"] for r in results])

    # Left: parasitic current vs h (log-log)
    ax = axes[0]
    ax.loglog(hs, u_para, "o-", color=COLORS[0], label="$\\|u_\\mathrm{para}\\|_\\infty$")
    # O(h^2) reference line
    h_ref = np.array([hs[0], hs[-1]])
    ax.loglog(h_ref, u_para[0] * (h_ref / hs[0])**2,
              "k--", lw=0.8, label="$O(h^2)$")
    ax.set_xlabel("$h$"); ax.set_ylabel("$\\|u_\\mathrm{para}\\|_\\infty$")
    ax.set_title("Parasitic current convergence")
    ax.legend(fontsize=8)

    # Right: Laplace pressure error vs h
    ax = axes[1]
    ax.loglog(hs, dp_err, "s-", color=COLORS[1],
              label="$|\\Delta p_\\mathrm{sim} - \\sigma/R| / (\\sigma/R)$")
    ax.axhline(0.001, color="r", ls=":", lw=0.8, label="0.1 % target")
    ax.set_xlabel("$h$"); ax.set_ylabel("Relative $\\Delta p$ error")
    ax.set_title("Laplace pressure error")
    ax.legend(fontsize=8)

    fig.suptitle(
        f"Static droplet  ($\\rho_l/\\rho_g = {int(RHO_L/RHO_G)}$,"
        f"  $\\sigma = {SIGMA}$,  $R = {R}$)",
        fontsize=11)
    fig.tight_layout()
    return fig


def main():
    parser = experiment_argparser(description=__doc__)
    args = parser.parse_args()

    npz_path = OUT / "data.npz"

    if args.plot_only:
        raw = load_results(npz_path)
        results = [{"N": int(raw[f"N{n}"]), "h": float(raw[f"h{n}"]),
                    "u_para": float(raw[f"u_para{n}"]),
                    "dp_err": float(raw[f"dp_err{n}"])}
                   for n in N_GRIDS if f"N{n}" in raw]
    else:
        results = run()
        save_dict = {}
        for r in results:
            n = r["N"]
            save_dict[f"N{n}"]      = np.array([r["N"]])
            save_dict[f"h{n}"]      = np.array([r["h"]])
            save_dict[f"u_para{n}"] = np.array([r["u_para"]])
            save_dict[f"dp_err{n}"] = np.array([r["dp_err"]])
            save_dict[f"hist{n}"]   = r["u_max_hist"]
        save_results(npz_path, save_dict)

    fig = plot(results)
    save_figure(fig, OUT / "parasitic_convergence.pdf")
    print(f"[exp13-1] saved → {OUT}")


if __name__ == "__main__":
    main()
