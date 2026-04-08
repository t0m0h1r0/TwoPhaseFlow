#!/usr/bin/env python3
"""Static droplet — FD-PPE baseline vs HFE curvature filter.

HFE (High-Frequency Extraction / InterfaceLimitedFilter) applied to
curvature κ before computing f_csf, to damp high-frequency κ oscillations:

    κ* = κ + C h² w(ψ) ∇²κ        (InterfaceLimitedFilter, §curvature_filter)

where w(ψ) = 4ψ(1−ψ) concentrates the filter near the interface.
C = 0 → no filter (baseline); C > 0 → increasing damping.
Stable for C < 0.125 in 2D.

The balanced-force property is preserved because p is untouched.

Compares: no filter / C=0.03 / C=0.05 / C=0.08

A3 traceability
───────────────
  HFE filter    → curvature_filter.InterfaceLimitedFilter.apply()
  Balanced-force → §7 warnbox (CCD ∇p corrector)

Output:
  experiment/ch12/results/ipc_ccdlu_droplet/
    ipc_ccdlu_droplet.pdf
    ipc_ccdlu_droplet_data.npz

Usage:
  python experiment/ch12/exp12_ipc_ccdlu_droplet.py
  python experiment/ch12/exp12_ipc_ccdlu_droplet.py --plot-only
"""

import sys, pathlib, argparse
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
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.rhie_chow import RhieChowInterpolator
from twophase.pressure.velocity_corrector import ccd_pressure_gradient
from twophase.pressure.dccd_ppe_filter import DCCDPPEFilter
from twophase.levelset.curvature_filter import InterfaceLimitedFilter

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "ipc_ccdlu_droplet"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "ipc_ccdlu_droplet_data.npz"
FIG_PATH = OUT_DIR / "ipc_ccdlu_droplet.pdf"

# ── Parameters ────────────────────────────────────────────────────────────────
R       = 0.25
SIGMA   = 1.0
WE      = 10.0
RHO_G   = 1.0
RHO_L   = 2.0
N       = 64
N_STEPS = 400

# Filter strengths to compare: C=0 is baseline (no filter)
C_LIST = [0.0, 0.03, 0.05, 0.08]


# ── Core simulation ───────────────────────────────────────────────────────────

def run(C: float):
    """Run static droplet with HFE pressure filter strength C.

    Parameters
    ----------
    C : float — HFE strength (0 = no filter, stable for C < 0.125)
    """
    backend = Backend(use_gpu=False)
    xp = backend.xp

    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")

    X, Y    = grid.meshgrid()
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

    # HFE curvature filter: κ* = κ + C h² w(ψ) ∇²κ
    hfe = InterfaceLimitedFilter(backend, ccd, C=C) if C > 0.0 else None
    if hfe is not None:
        kappa = np.asarray(hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi)))
    else:
        kappa = kappa_raw

    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x   = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y   = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u = np.zeros_like(X); v = np.zeros_like(X); p = np.zeros_like(X)
    u_max_hist = []

    for _ in range(N_STEPS):
        # Predictor
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE RHS: DCCD-filtered CCD divergence (§7 §sec:checkerboard_solution)
        # + RC Balanced-Force face divergence (§7 eq:rc-face-balanced)
        div_dccd = dccd_filt.compute_filtered_divergence([u_star, v_star])
        div_rc   = rhie_chow.face_velocity_divergence(
            [u_star, v_star], p, rho, dt,
            kappa=xp.asarray(kappa), psi=xp.asarray(psi), we=WE,
        )
        # DCCD = CCD-native RHS (§7 primary); FD spsolve as comparison solver
        rhs_vec = np.asarray(div_dccd).ravel() / dt
        rhs_vec[pin] = 0.0
        p = spsolve(A_fd, rhs_vec).reshape(grid.shape)

        # Corrector: CCD ∇p (balanced-force)
        grad_p = ccd_pressure_gradient(ccd, xp.asarray(p), grid.ndim)
        u = u_star - dt / rho * np.asarray(grad_p[0])
        v = v_star - dt / rho * np.asarray(grad_p[1])
        wall_bc(u); wall_bc(v)

        u_max_hist.append(float(np.max(np.sqrt(u**2 + v**2))))
        if np.isnan(u_max_hist[-1]) or u_max_hist[-1] > 1e6:
            print(f"  [C={C}] BLOWUP at step={len(u_max_hist)}")
            break

    label = f"C={C:.2f}" if C > 0 else "no filter"

    inside   = phi_raw >  3.0 / N
    outside  = phi_raw < -3.0 / N
    dp_exact = SIGMA / (R * WE)
    dp_meas  = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_err   = abs(dp_meas - dp_exact) / dp_exact

    near            = np.abs(phi_raw) < 2.0 * eps
    kappa_mean      = float(np.mean(kappa[near]))     if np.any(near) else float("nan")
    kappa_std       = float(np.std(kappa[near]))      if np.any(near) else float("nan")
    kappa_raw_std   = float(np.std(kappa_raw[near]))  if np.any(near) else float("nan")

    return {
        "label":         label,
        "C":             C,
        "u_max":         float(np.max(np.sqrt(u**2 + v**2))),
        "u_max_hist":    np.array(u_max_hist),
        "dp_meas":       dp_meas,
        "dp_exact":      dp_exact,
        "dp_err":        dp_err,
        "kappa_mean":    kappa_mean,
        "kappa_std":     kappa_std,
        "kappa_raw_std": kappa_raw_std,
        "phi_raw":       phi_raw,
        "p":             p,
        "vel_mag":       np.sqrt(u**2 + v**2),
        "kappa":         kappa,
        "kappa_raw":     kappa_raw,
    }


# ── Main computation ──────────────────────────────────────────────────────────

def compute_all():
    results = {}
    for C in C_LIST:
        label = f"C={C:.2f}" if C > 0 else "no filter"
        print(f"  [{label}] ...")
        r = run(C)
        print(f"    κ̄={r['kappa_mean']:.3f}  σ_κ(raw)={r['kappa_raw_std']:.3f}"
              f"→σ_κ(filt)={r['kappa_std']:.3f} "
              f"| ‖u‖∞={r['u_max']:.3e}  Δp err={r['dp_err']*100:.2f}%")
        results[label] = r
    return results


# ── I/O ───────────────────────────────────────────────────────────────────────

def save_npz(results):
    flat = {}
    for label, r in results.items():
        key = label.replace("=", "_").replace(".", "p")
        for k, v in r.items():
            flat[f"{key}__{k}"] = np.asarray(v)
    np.savez(NPZ_PATH, **flat)
    print(f"Saved data → {NPZ_PATH}")


def load_npz():
    data = np.load(NPZ_PATH, allow_pickle=False)
    results = {}
    for fullkey, val in data.items():
        key, subkey = fullkey.split("__", 1)
        results.setdefault(key, {})[subkey] = val
    for r in results.values():
        for k in ("u_max", "dp_meas", "dp_exact", "dp_err", "C",
                  "kappa_mean", "kappa_std", "kappa_raw_std"):
            if k in r:
                r[k] = float(r[k])
    return results


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot(results):
    labels = [f"C={C:.2f}" if C > 0 else "no filter" for C in C_LIST
              if (f"C={C:.2f}" if C > 0 else "no filter") in results]
    ncols  = len(labels)
    x1d    = np.linspace(0, 1, N + 1)
    eps    = 1.5 / N

    all_p = np.concatenate([results[lb]["p"].ravel() for lb in labels])
    vmax_p = float(np.nanpercentile(np.abs(all_p), 99)) * 1.05 or 0.1
    vmax_u = max(float(results[lb]["vel_mag"].max()) for lb in labels) or 1e-10

    fig = plt.figure(figsize=(4.5 * ncols, 11))
    gs  = fig.add_gridspec(4, ncols, hspace=0.5, wspace=0.3,
                           height_ratios=[1, 1, 1, 1.2])

    for col, label in enumerate(labels):
        r   = results[label]
        phi = r["phi_raw"]

        # Row 0: κ (filtered)
        ax0 = fig.add_subplot(gs[0, col])
        near = np.abs(phi) < 2.0 * eps
        all_kap = r["kappa_raw"][near]
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
        km = float(np.mean(r["kappa"][near])) if np.any(near) else float("nan")
        ks = float(np.std(r["kappa"][near]))  if np.any(near) else float("nan")
        ks_raw = float(np.std(r["kappa_raw"][near])) if np.any(near) else float("nan")
        ax0.text(0.02, 0.03,
                 fr"$\bar\kappa$={km:.3f}  $\sigma_{{raw}}$={ks_raw:.3f}→{ks:.3f}",
                 transform=ax0.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

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

    # Row 3: ||u||_∞ history
    ax3    = fig.add_subplot(gs[3, :])
    colors = plt.cm.tab10(np.linspace(0, 0.5, len(labels)))
    for i, label in enumerate(labels):
        hist = results[label]["u_max_hist"]
        t_ax = np.arange(1, len(hist) + 1) * (0.25 / N)
        ax3.semilogy(t_ax, hist, lw=1.8, color=colors[i], label=label)
    ax3.set_xlabel("Physical time $t$", fontsize=9)
    ax3.set_ylabel(r"$\|\mathbf{u}\|_\infty$", fontsize=9)
    ax3.legend(fontsize=8, ncol=2)
    ax3.grid(True, which="both", ls="--", alpha=0.4)
    ax3.set_title(
        "Spurious current history — HFE pressure filter comparison",
        fontsize=9,
    )

    dp_exact = float(results[labels[0]]["dp_exact"])
    rows = [f"{'Label':12s}  {'σ_κ':>8}  {'‖u‖∞':>10}  {'Δp err':>8}"]
    for label in labels:
        r = results[label]
        rows.append(
            f"{label:12s}  {r['kappa_std']:8.3f}  "
            f"{r['u_max']:10.3e}  {r['dp_err']*100:7.2f}%"
        )
    fig.text(0.01, 0.005, "\n".join(rows), fontsize=8,
             family="monospace", va="bottom",
             bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    fig.suptitle(
        f"Static droplet — HFE pressure filter (InterfaceLimitedFilter)\n"
        f"$N={N}$, $R={R}$, $\\rho_l/\\rho_g={int(RHO_L)}$, "
        f"$We={WE}$, {N_STEPS} steps.  $\\Delta p_{{exact}}={dp_exact:.4f}$",
        fontsize=10, y=1.003,
    )

    fig.savefig(FIG_PATH, format="pdf", bbox_inches="tight")
    print(f"Saved figure → {FIG_PATH}")
    plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()

    if args.plot_only:
        results = load_npz()
    else:
        results = compute_all()
        save_npz(results)

    plot(results)


if __name__ == "__main__":
    main()
