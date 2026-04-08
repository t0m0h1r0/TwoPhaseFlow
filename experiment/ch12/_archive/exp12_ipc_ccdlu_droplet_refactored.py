#!/usr/bin/env python3
"""Static droplet — FD-PPE baseline vs HFE curvature filter.

Refactored version using twophase.experiment toolkit.
Compare with exp12_ipc_ccdlu_droplet.py (original).

Usage:
  python experiment/ch12/exp12_ipc_ccdlu_droplet_refactored.py
  python experiment/ch12/exp12_ipc_ccdlu_droplet_refactored.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    field_panel, time_history, summary_text, figsize_grid,
)
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.rhie_chow import RhieChowInterpolator
from twophase.pressure.velocity_corrector import ccd_pressure_gradient
from twophase.pressure.dccd_ppe_filter import DCCDPPEFilter
from twophase.levelset.curvature_filter import InterfaceLimitedFilter

apply_style()

OUT = experiment_dir(__file__)                       # ← auto: results/ipc_ccdlu_droplet_refactored/
NPZ = OUT / "ipc_ccdlu_droplet_refactored_data.npz"

# ── Parameters ────────────────────────────────────────────────────────────────
R, SIGMA, WE     = 0.25, 1.0, 10.0
RHO_G, RHO_L     = 1.0, 2.0
N, N_STEPS        = 64, 400
C_LIST            = [0.0, 0.03, 0.05, 0.08]


# ── Core simulation (unchanged) ──────────────────────────────────────────────

def run(C: float):
    backend = Backend(use_gpu=False)
    xp = backend.xp
    h, eps, dt = 1.0 / N, 1.5 / N, 0.25 / N

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    X, Y = grid.meshgrid()

    phi_raw = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi     = np.asarray(heaviside(np, phi_raw, eps))
    rho     = RHO_G + (RHO_L - RHO_G) * psi

    rhie_chow = RhieChowInterpolator(backend, grid, ccd, bc_type="wall")
    dccd_filt = DCCDPPEFilter(backend, grid, ccd, bc_type="wall")
    ppb       = PPEBuilder(backend, grid, bc_type="wall")
    triplet, A_shape = ppb.build(rho)
    A_fd = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    pin  = ppb._pin_dof

    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa_raw = np.asarray(curv_calc.compute(psi))

    hfe = InterfaceLimitedFilter(backend, ccd, C=C) if C > 0 else None
    kappa = (np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
             if hfe else kappa_raw)

    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0; arr[-1, :] = 0; arr[:, 0] = 0; arr[:, -1] = 0

    u, v, p = (np.zeros_like(X) for _ in range(3))
    u_max_hist = []

    for _ in range(N_STEPS):
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        div_dccd = dccd_filt.compute_filtered_divergence([u_star, v_star])
        rhs_vec = np.asarray(div_dccd).ravel() / dt
        rhs_vec[pin] = 0.0
        p = spsolve(A_fd, rhs_vec).reshape(grid.shape)

        grad_p = ccd_pressure_gradient(ccd, xp.asarray(p), grid.ndim)
        u = u_star - dt / rho * np.asarray(grad_p[0])
        v = v_star - dt / rho * np.asarray(grad_p[1])
        wall_bc(u); wall_bc(v)

        u_max_hist.append(float(np.max(np.sqrt(u**2 + v**2))))
        if np.isnan(u_max_hist[-1]) or u_max_hist[-1] > 1e6:
            break

    inside  = phi_raw >  3.0 / N
    outside = phi_raw < -3.0 / N
    dp_exact = SIGMA / (R * WE)
    dp_meas  = float(np.mean(p[inside]) - np.mean(p[outside]))
    near     = np.abs(phi_raw) < 2.0 * eps

    return {
        "C": C,
        "u_max": float(np.max(np.sqrt(u**2 + v**2))),
        "u_max_hist": np.array(u_max_hist),
        "dp_meas": dp_meas,  "dp_exact": dp_exact,
        "dp_err": abs(dp_meas - dp_exact) / dp_exact,
        "kappa_mean": float(np.mean(kappa[near])),
        "kappa_std":  float(np.std(kappa[near])),
        "kappa_raw_std": float(np.std(kappa_raw[near])),
        "phi_raw": phi_raw, "p": p,
        "vel_mag": np.sqrt(u**2 + v**2),
        "kappa": kappa, "kappa_raw": kappa_raw,
    }


def compute_all():
    results = {}
    for C in C_LIST:
        label = f"C={C:.2f}" if C > 0 else "no filter"
        print(f"  [{label}] ...")
        results[label] = run(C)
    return results


# ── Plotting (refactored) ────────────────────────────────────────────────────

def plot(results):
    labels = [lb for lb in results if not lb.startswith("_")]
    ncols  = len(labels)
    x1d    = np.linspace(0, 1, N + 1)
    eps    = 1.5 / N

    # Shared colour limits
    all_p  = np.concatenate([results[lb]["p"].ravel() for lb in labels])
    vmax_p = float(np.nanpercentile(np.abs(all_p), 99)) * 1.05 or 0.1
    vmax_u = max(float(results[lb]["vel_mag"].max()) for lb in labels) or 1e-10

    fig = plt.figure(figsize=(4.5 * ncols, 11))
    gs  = fig.add_gridspec(4, ncols, hspace=0.5, wspace=0.3,
                           height_ratios=[1, 1, 1, 1.2])

    for col, label in enumerate(labels):
        r   = results[label]
        phi = r["phi_raw"]
        near = np.abs(phi) < 2.0 * eps
        kap_lim = float(np.nanpercentile(np.abs(r["kappa_raw"][near]), 98))

        km = float(np.mean(r["kappa"][near]))
        ks = float(np.std(r["kappa"][near]))
        ks_raw = float(np.std(r["kappa_raw"][near]))

        # Row 0: κ (filtered) — field_panel replaces 12 lines of boilerplate
        ax0 = fig.add_subplot(gs[0, col])
        field_panel(ax0, x1d, x1d, r["kappa"].T,
                    cmap="RdBu_r", vlim=kap_lim,
                    contour_field=phi.T, title=label,
                    annotation=fr"$\bar\kappa$={km:.3f}  $\sigma_{{raw}}$={ks_raw:.3f}→{ks:.3f}")
        if col == 0:
            ax0.set_ylabel(r"$\kappa$ (filtered)", fontsize=9)

        # Row 1: pressure
        ax1 = fig.add_subplot(gs[1, col])
        field_panel(ax1, x1d, x1d, r["p"].T,
                    cmap="RdBu_r", vlim=vmax_p,
                    contour_field=phi.T,
                    annotation=fr"$\Delta p$={r['dp_meas']:.4f}  (err {r['dp_err']*100:.1f}%)")
        if col == 0:
            ax1.set_ylabel("$p$", fontsize=9)

        # Row 2: |u|
        ax2 = fig.add_subplot(gs[2, col])
        field_panel(ax2, x1d, x1d, r["vel_mag"].T,
                    cmap="hot_r", vlim=(0, vmax_u),
                    contour_field=phi.T, contour_color="w",
                    annotation=fr"$\|u\|_\infty$={r['u_max']:.2e}")
        if col == 0:
            ax2.set_ylabel(r"$|\mathbf{u}|$", fontsize=9)

    # Row 3: ||u||_∞ history — time_history replaces 8 lines
    ax3 = fig.add_subplot(gs[3, :])
    dt = 0.25 / N
    series = {lb: (np.arange(1, len(results[lb]["u_max_hist"]) + 1) * dt,
                   results[lb]["u_max_hist"])
              for lb in labels}
    time_history(ax3, series, ylabel=r"$\|\mathbf{u}\|_\infty$",
                 title="Spurious current history — HFE pressure filter comparison")

    # Summary table — summary_text replaces 8 lines
    rows = [f"{'Label':12s}  {'σ_κ':>8}  {'‖u‖∞':>10}  {'Δp err':>8}"]
    for lb in labels:
        r = results[lb]
        rows.append(f"{lb:12s}  {r['kappa_std']:8.3f}  "
                    f"{r['u_max']:10.3e}  {r['dp_err']*100:7.2f}%")
    summary_text(fig, rows)

    fig.suptitle(
        f"Static droplet — HFE pressure filter\n"
        f"$N={N}$, $R={R}$, $\\rho_l/\\rho_g={int(RHO_L)}$, "
        f"$We={WE}$, {N_STEPS} steps",
        fontsize=10, y=1.003,
    )

    save_figure(fig, OUT / "ipc_ccdlu_droplet_refactored")  # ← 1 line replaces 3


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser("IPC+CCD-LU droplet").parse_args()  # ← 1 line replaces 3

    if args.plot_only:
        results = load_results(NPZ)          # ← 1 line replaces 10 (load + float restore)
    else:
        results = compute_all()
        save_results(NPZ, results)           # ← 1 line replaces 6 (flatten + savez)

    plot(results)


if __name__ == "__main__":
    main()
