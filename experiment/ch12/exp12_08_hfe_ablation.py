#!/usr/bin/env python3
"""【12-8】HFE ablation — curvature filter strength comparison on static droplet.

Paper ref: §12.8 (sec:val_hfe_ablation)

Compares the InterfaceLimitedFilter (HFE curvature filter) at multiple
strengths C on a static droplet. The filter damps high-frequency kappa
oscillations near the interface:

    kappa* = kappa + C h^2 w(psi) Laplacian(kappa)

where w(psi) = 4 psi (1 - psi) concentrates the filter at the interface.

Variants
--------
  C = 0.00  (baseline, no filter)
  C = 0.03
  C = 0.05
  C = 0.08

Setup
-----
  Static droplet: R=0.25, center (0.5, 0.5), wall BC, gravity=0
  rho_l/rho_g = 2,  We = 10,  N = 64,  400 steps

Output
------
  experiment/ch12/results/hfe_ablation/
    hfe_ablation.pdf       — 4-panel comparison (kappa, p, |u|, history)
    hfe_ablation_data.npz  — raw data

Usage
-----
  python experiment/ch12/exp12_08_hfe_ablation.py
  python experiment/ch12/exp12_08_hfe_ablation.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np

from twophase.backend import Backend
from twophase.tools.experiment.gpu import sparse_solve_2d
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)

# Try importing optional modules (may not exist yet)
try:
    from twophase.levelset.curvature_filter import InterfaceLimitedFilter
    _HAS_FILTER = True
except ImportError:
    _HAS_FILTER = False
    print("[WARN] InterfaceLimitedFilter not available — only baseline will run")

OUT = experiment_dir(__file__, "hfe_ablation")
NPZ_PATH = OUT / "hfe_ablation_data.npz"
FIG_PATH = OUT / "hfe_ablation.pdf"

# ── Physical parameters ─────────────────────────────────────────────────────
R       = 0.25
SIGMA   = 1.0
WE      = 10.0
RHO_G   = 1.0
RHO_L   = 2.0
N       = 64
N_STEPS = 400
C_LIST  = [0.0, 0.03, 0.05, 0.08]


# ── PPE solver ───────────────────────────────────────────────────────────────

def _solve_ppe(rhs, rho, ppe_builder, backend):
    triplet, A_shape = ppe_builder.build(rho)  # always host (numpy) arrays
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=A_shape)
    xp = backend.xp
    rhs_flat = xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return sparse_solve_2d(backend, A, rhs_flat).reshape(rho.shape)


# ── Single run ───────────────────────────────────────────────────────────────

def run(C: float):
    """Run static droplet with HFE curvature filter strength C."""
    backend = Backend()
    xp = backend.xp

    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc   = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    dp_exact = SIGMA / (R * WE)

    # Initial conditions
    phi = R - xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = heaviside(xp, phi, eps)
    rho = RHO_G + (RHO_L - RHO_G) * psi

    # Curvature (raw + filtered)
    kappa_raw = curv_calc.compute(psi)

    if C > 0.0 and _HAS_FILTER:
        hfe = InterfaceLimitedFilter(backend, ccd, C=C)
        kappa = hfe.apply(kappa_raw, psi)
    else:
        kappa = kappa_raw.copy()

    # CSF body force (static)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * dpsi_dx
    f_csf_y = (SIGMA / WE) * kappa * dpsi_dy

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u = xp.zeros_like(X)
    v = xp.zeros_like(X)
    p = xp.zeros_like(X)
    u_max_hist = []

    for _ in range(N_STEPS):
        # Predictor
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (du_dx + dv_dy) / dt
        p = _solve_ppe(rhs, rho, ppe_builder, backend)

        # Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * dp_dx
        v = v_star - dt / rho * dp_dy
        wall_bc(u); wall_bc(v)

        u_max_hist.append(float(xp.max(xp.sqrt(u**2 + v**2))))
        if np.isnan(u_max_hist[-1]) or u_max_hist[-1] > 1e6:
            print(f"  [C={C}] BLOWUP at step={len(u_max_hist)}")
            break

    # Diagnostics
    inside  = phi >  3.0 / N
    outside = phi < -3.0 / N
    dp_meas = (float(xp.mean(p[inside]) - xp.mean(p[outside]))
               if bool(xp.any(inside)) and bool(xp.any(outside)) else float('nan'))
    dp_err  = abs(dp_meas - dp_exact) / dp_exact

    near = xp.abs(phi) < 2.0 * eps
    kappa_mean    = float(xp.mean(kappa[near]))     if bool(xp.any(near)) else float('nan')
    kappa_std     = float(xp.std(kappa[near]))      if bool(xp.any(near)) else float('nan')
    kappa_raw_std = float(xp.std(kappa_raw[near]))  if bool(xp.any(near)) else float('nan')

    label = f"C={C:.2f}" if C > 0 else "no filter"
    print(f"    [{label}] kappa_mean={kappa_mean:.3f}  "
          f"sigma_kappa(raw)={kappa_raw_std:.3f} -> (filt)={kappa_std:.3f}  "
          f"||u||inf={u_max_hist[-1]:.3e}  dp_err={dp_err * 100:.2f}%")

    return {
        "label":         label,
        "C":             C,
        "u_max":         float(xp.max(xp.sqrt(u**2 + v**2))),
        "u_max_hist":    np.array(u_max_hist),
        "dp_meas":       dp_meas,
        "dp_exact":      dp_exact,
        "dp_err":        dp_err,
        "kappa_mean":    kappa_mean,
        "kappa_std":     kappa_std,
        "kappa_raw_std": kappa_raw_std,
        "phi":           backend.to_host(phi),
        "p":             backend.to_host(p),
        "vel_mag":       backend.to_host(xp.sqrt(u**2 + v**2)),
        "kappa":         backend.to_host(kappa),
        "kappa_raw":     backend.to_host(kappa_raw),
    }


# ── Compute all variants ────────────────────────────────────────────────────

def compute_all():
    c_run = C_LIST if _HAS_FILTER else [0.0]
    results = {}
    for C in c_run:
        label = f"C={C:.2f}" if C > 0 else "no filter"
        r = run(C)
        results[label] = r
    return results


# ── I/O ──────────────────────────────────────────────────────────────────────

def save_npz(results):
    save_results(NPZ_PATH, results)


def load_npz():
    results = load_results(NPZ_PATH)
    for r in results.values():
        if not isinstance(r, dict):
            continue
        for k in ("u_max", "dp_meas", "dp_exact", "dp_err", "C",
                  "kappa_mean", "kappa_std", "kappa_raw_std"):
            if k in r:
                r[k] = float(r[k])
    return results


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot(results):
    apply_style()
    import matplotlib.pyplot as plt

    labels = [f"C={C:.2f}" if C > 0 else "no filter" for C in C_LIST
              if (f"C={C:.2f}" if C > 0 else "no filter") in results]
    if not labels:
        # Fallback: use whatever keys exist
        labels = sorted(results.keys())
    ncols = len(labels)
    if ncols == 0:
        print("  [WARN] No results to plot")
        return

    x1d = np.linspace(0, 1, N + 1)
    eps = 1.5 / N

    all_p = np.concatenate([results[lb]["p"].ravel() for lb in labels])
    vmax_p = float(np.nanpercentile(np.abs(all_p), 99)) * 1.05 or 0.1
    vmax_u = max(float(results[lb]["vel_mag"].max()) for lb in labels) or 1e-10

    fig = plt.figure(figsize=(4.5 * ncols, 11))
    gs  = fig.add_gridspec(4, ncols, hspace=0.5, wspace=0.3,
                           height_ratios=[1, 1, 1, 1.2])

    for col, label in enumerate(labels):
        r   = results[label]
        phi = r["phi"]

        # Row 0: kappa (filtered)
        ax0 = fig.add_subplot(gs[0, col])
        near = np.abs(phi) < 2.0 * eps
        all_kap = r["kappa_raw"][near] if np.any(near) else r["kappa_raw"].ravel()
        kap_lim = float(np.nanpercentile(np.abs(all_kap), 98)) if len(all_kap) else 1.0
        im0 = ax0.pcolormesh(x1d, x1d, r["kappa"].T,
                             cmap="RdBu_r", vmin=-kap_lim, vmax=kap_lim,
                             shading="auto")
        ax0.contour(x1d, x1d, phi.T, levels=[0], colors="k", linewidths=0.8)
        ax0.set_title(label, fontsize=10, fontweight="bold")
        ax0.set_aspect("equal"); ax0.tick_params(labelsize=7)
        if col == 0:
            ax0.set_ylabel(r"$\kappa$ (filtered)", fontsize=9)
        plt.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)

        # Row 1: pressure
        ax1 = fig.add_subplot(gs[1, col])
        im1 = ax1.pcolormesh(x1d, x1d, r["p"].T,
                             cmap="RdBu_r", vmin=-vmax_p, vmax=vmax_p,
                             shading="auto")
        ax1.contour(x1d, x1d, phi.T, levels=[0], colors="k", linewidths=0.8)
        ax1.set_aspect("equal"); ax1.tick_params(labelsize=7)
        if col == 0:
            ax1.set_ylabel("$p$", fontsize=9)
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        ax1.text(0.02, 0.03,
                 fr"$\Delta p$={r['dp_meas']:.4f}  (err {r['dp_err']*100:.1f}%)",
                 transform=ax1.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # Row 2: |u|
        ax2 = fig.add_subplot(gs[2, col])
        im2 = ax2.pcolormesh(x1d, x1d, r["vel_mag"].T,
                             cmap="hot_r", vmin=0, vmax=vmax_u,
                             shading="auto")
        ax2.contour(x1d, x1d, phi.T, levels=[0], colors="w", linewidths=0.8)
        ax2.set_aspect("equal"); ax2.tick_params(labelsize=7)
        if col == 0:
            ax2.set_ylabel(r"$|\mathbf{u}|$", fontsize=9)
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        ax2.text(0.02, 0.03,
                 fr"$\|u\|_\infty$={r['u_max']:.2e}",
                 transform=ax2.transAxes, fontsize=8, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

    # Row 3: ||u||_inf history (shared axis)
    ax3 = fig.add_subplot(gs[3, :])
    colors = plt.cm.tab10(np.linspace(0, 0.5, len(labels)))
    for i, label in enumerate(labels):
        hist = results[label]["u_max_hist"]
        t_ax = np.arange(1, len(hist) + 1) * (0.25 / N)
        ax3.semilogy(t_ax, hist, lw=1.8, color=colors[i], label=label)
    ax3.set_xlabel("Physical time $t$")
    ax3.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax3.legend(fontsize=8, ncol=2)
    ax3.grid(True, which="both", ls="--", alpha=0.4)
    ax3.set_title("Parasitic current history -- HFE curvature filter comparison")

    # Summary text
    dp_exact = float(results[labels[0]]["dp_exact"])
    rows_txt = [f"{'Label':12s}  {'sigma_k':>8}  {'||u||inf':>10}  {'dp err':>8}"]
    for label in labels:
        r = results[label]
        rows_txt.append(
            f"{label:12s}  {r['kappa_std']:8.3f}  "
            f"{r['u_max']:10.3e}  {r['dp_err']*100:7.2f}%"
        )
    fig.text(0.01, 0.005, "\n".join(rows_txt), fontsize=8,
             family="monospace", va="bottom",
             bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    fig.suptitle(
        f"Static droplet -- HFE curvature filter ablation\n"
        f"$N={N}$, $R={R}$, $\\rho_l/\\rho_g={int(RHO_L)}$, "
        f"$We={WE}$, {N_STEPS} steps.  $\\Delta p_{{exact}}={dp_exact:.4f}$",
        fontsize=10, y=1.003,
    )

    save_figure(fig, FIG_PATH)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  [12-8] HFE Ablation: Curvature Filter Strength Comparison")
    print("=" * 80 + "\n")

    results = compute_all()
    save_npz(results)
    plot(results)

    print("\n  Done.")


if __name__ == "__main__":
    args = experiment_argparser("HFE ablation study").parse_args()

    if args.plot_only:
        results = load_npz()
        plot(results)
    else:
        main()
