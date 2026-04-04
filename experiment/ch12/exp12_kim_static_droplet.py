#!/usr/bin/env python3
"""Kim compact filter effect on static droplet spurious currents.

Compares baseline (no filter) vs Kim (2010) compact filter applied to φ
before curvature computation.  Measures:
  - Parasitic (spurious) current: ||u||_∞ over time
  - Laplace pressure error: |Δp_meas − σ/(R·We)| / (σ/(R·We))
  - Final pressure and velocity fields

Kim filter (Padé compact, 4th-order):
  α_f = −cos(ξ_c)/2,   H(ξ_c) = 0.5 per pass
  ξ_c = 0.5 rad  →  α_f ≈ −0.439
  Applied once at initialization (static interface → φ fixed).

Output:
  experiment/ch12/results/kim_static_droplet/
    kim_static_droplet.pdf
    kim_static_droplet_data.npz

Usage:
  python experiment/ch12/exp12_kim_static_droplet.py
  python experiment/ch12/exp12_kim_static_droplet.py --plot-only
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
from twophase.levelset.compact_filters import LeleCompactFilter
from twophase.pressure.ppe_builder import PPEBuilder

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "kim_static_droplet"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "kim_static_droplet_data.npz"
FIG_PATH = OUT_DIR / "kim_static_droplet.pdf"

# ── Parameters ────────────────────────────────────────────────────────────
R       = 0.25
SIGMA   = 1.0
WE      = 10.0
RHO_G   = 1.0
RHO_L   = 2.0        # density ratio = 2

N       = 64
N_STEPS = 500        # longer run to reach steady state

# Kim filter
XI_C    = 0.5        # cut-off kh targeting m=8 perturbation (and higher)
KIM_PASSES_LIST = [0, 1, 3, 5]   # 0 = no filter (baseline)


# ── Core simulation ───────────────────────────────────────────────────────

def run_droplet(kim_passes: int):
    """Run static droplet with optional Kim compact filter on φ.

    Parameters
    ----------
    kim_passes : int — number of Kim filter passes applied to φ at init.
                       0 = baseline (no filter).
    """
    backend = Backend(use_gpu=False)
    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    ppb  = PPEBuilder(backend, grid, bc_type="wall")

    X, Y = grid.meshgrid()
    phi_raw = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R   # SDF (negative inside)

    # ── Apply Kim compact filter to φ ─────────────────────────────────────
    if kim_passes > 0:
        kim = LeleCompactFilter(backend, ccd, xi_c=XI_C)
        phi = phi_raw.copy()
        for _ in range(kim_passes):
            phi = np.array(kim.apply(phi))
    else:
        phi = phi_raw.copy()

    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    # ── Curvature from (possibly filtered) φ ─────────────────────────────
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa = curv_calc.compute(psi)

    # ── CSF force (computed once — static interface) ──────────────────────
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    # ── PPE matrix (static density) ───────────────────────────────────────
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u = np.zeros_like(X)
    v = np.zeros_like(X)
    p = np.zeros_like(X)
    u_max_hist = []

    for step in range(N_STEPS):
        # Predictor
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # Divergence (CCD)
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs_raw   = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
        rhs_vec   = rhs_raw.ravel().copy()
        rhs_vec[ppb._pin_dof] = 0.0

        # PPE solve (FD sparse — exact, zero residual)
        p = spsolve(A, rhs_vec).reshape(grid.shape)

        # Corrector (CCD gradient with wall-Neumann zeroing)
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)
        if np.isnan(u_max) or u_max > 1e6:
            print(f"    BLOWUP at step={step+1}")
            break

    # ── Diagnostics ───────────────────────────────────────────────────────
    vel_mag    = np.sqrt(u**2 + v**2)
    inside     = phi_raw < -3.0 / N
    outside    = phi_raw >  3.0 / N
    dp_exact   = SIGMA / (R * WE)
    dp_meas    = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_err     = abs(dp_meas - dp_exact) / dp_exact

    kappa_np   = np.asarray(kappa)
    near       = np.abs(phi_raw) < 2.0 * eps
    kappa_std  = float(np.std(kappa_np[near])) if np.any(near) else float("nan")
    kappa_mean = float(np.mean(kappa_np[near])) if np.any(near) else float("nan")

    return {
        "kim_passes": kim_passes,
        "u_max":      float(vel_mag.max()),
        "u_max_hist": np.array(u_max_hist),
        "dp_meas":    dp_meas,
        "dp_exact":   dp_exact,
        "dp_err":     dp_err,
        "kappa_std":  kappa_std,
        "kappa_mean": kappa_mean,
        "phi":        phi,
        "phi_raw":    phi_raw,
        "psi":        psi,
        "p":          p,
        "vel_mag":    vel_mag,
        "kappa":      kappa_np,
    }


# ── Main computation ──────────────────────────────────────────────────────

def compute_all():
    results = {}
    for passes in KIM_PASSES_LIST:
        label = "No filter" if passes == 0 else f"Kim {passes}p"
        print(f"  {label} (ξ_c={XI_C}, α_f={-np.cos(XI_C)/2:.3f}) ...")
        r = run_droplet(passes)
        print(f"    κ̄={r['kappa_mean']:.3f}  σ_κ={r['kappa_std']:.3f} "
              f"| ||u||∞={r['u_max']:.3e}  Δp err={r['dp_err']*100:.2f}%")
        results[label] = r
    return results


# ── I/O ───────────────────────────────────────────────────────────────────

def save_npz(results):
    flat = {}
    for label, r in results.items():
        for k, v in r.items():
            flat[f"{label}__{k}"] = np.asarray(v)
    np.savez(NPZ_PATH, **flat)
    print(f"Saved data → {NPZ_PATH}")


def load_npz():
    data = np.load(NPZ_PATH, allow_pickle=False)
    results = {}
    for fullkey, val in data.items():
        label, subkey = fullkey.split("__", 1)
        results.setdefault(label, {})[subkey] = val
    # restore scalar types
    for r in results.values():
        for k in ("kim_passes", "u_max", "dp_meas", "dp_exact",
                  "dp_err", "kappa_std", "kappa_mean"):
            if k in r:
                r[k] = float(r[k])
        r["kim_passes"] = int(r["kim_passes"])
    return results


# ── Plotting ──────────────────────────────────────────────────────────────

def plot(results):
    labels   = ["No filter"] + [f"Kim {p}p" for p in KIM_PASSES_LIST if p > 0]
    n_filter = len(labels)

    x1d = np.linspace(0, 1, N + 1)

    # ── Figure layout: 3 rows × n_filter cols + 1 history panel ──────────
    fig = plt.figure(figsize=(4 * n_filter, 12))
    gs  = fig.add_gridspec(
        4, n_filter,
        hspace=0.45, wspace=0.35,
        height_ratios=[1, 1, 1, 1.2],
    )

    # Shared colour limits
    all_p = np.concatenate([results[lb]["p"].ravel() for lb in labels])
    vmax_p = float(np.nanpercentile(np.abs(all_p), 99)) * 1.05
    vmax_u = max(float(results[lb]["vel_mag"].max()) for lb in labels)

    all_kap = np.concatenate([
        results[lb]["kappa"][np.abs(results[lb]["phi_raw"]) < 2.0 * 1.5 / N].ravel()
        for lb in labels
    ])
    kap_lim = float(np.nanpercentile(np.abs(all_kap), 98))

    for col, label in enumerate(labels):
        r = results[label]
        phi_raw = r["phi_raw"]
        near = np.abs(phi_raw) < 2.0 * 1.5 / N

        # ── Row 0: κ field ─────────────────────────────────────────────
        ax0 = fig.add_subplot(gs[0, col])
        im0 = ax0.pcolormesh(x1d, x1d, r["kappa"].T, cmap="RdBu_r",
                             vmin=-kap_lim, vmax=kap_lim, shading="auto")
        ax0.contour(x1d, x1d, phi_raw.T, levels=[0], colors="k", linewidths=0.8)
        ax0.set_title(label, fontsize=10, fontweight="bold")
        ax0.set_aspect("equal")
        ax0.tick_params(labelsize=7)
        if col == 0:
            ax0.set_ylabel("$\\kappa$ field", fontsize=8)
        plt.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        km = float(np.mean(r["kappa"][near])) if np.any(near) else float("nan")
        ks = float(np.std(r["kappa"][near]))  if np.any(near) else float("nan")
        ax0.text(0.02, 0.03, f"$\\bar\\kappa$={km:.2f}  $\\sigma$={ks:.2f}",
                 transform=ax0.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 1: pressure ────────────────────────────────────────────
        ax1 = fig.add_subplot(gs[1, col])
        im1 = ax1.pcolormesh(x1d, x1d, r["p"].T, cmap="RdBu_r",
                             vmin=-vmax_p, vmax=vmax_p, shading="auto")
        ax1.contour(x1d, x1d, phi_raw.T, levels=[0], colors="k", linewidths=0.8)
        ax1.set_aspect("equal")
        ax1.tick_params(labelsize=7)
        if col == 0:
            ax1.set_ylabel("Pressure $p$", fontsize=8)
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        ax1.text(0.02, 0.03,
                 f"$\\Delta p$={r['dp_meas']:.4f}\nerr {r['dp_err']*100:.1f}%",
                 transform=ax1.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 2: velocity magnitude ──────────────────────────────────
        ax2 = fig.add_subplot(gs[2, col])
        im2 = ax2.pcolormesh(x1d, x1d, r["vel_mag"].T, cmap="hot_r",
                             vmin=0, vmax=vmax_u, shading="auto")
        ax2.contour(x1d, x1d, phi_raw.T, levels=[0], colors="w", linewidths=0.8)
        ax2.set_aspect("equal")
        ax2.tick_params(labelsize=7)
        if col == 0:
            ax2.set_ylabel("$|\\mathbf{u}|$", fontsize=8)
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        ax2.text(0.02, 0.03,
                 f"$\\|u\\|_\\infty$={r['u_max']:.2e}",
                 transform=ax2.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

    # ── Row 3: u_max history (shared, all configs) ────────────────────
    ax3 = fig.add_subplot(gs[3, :])
    colors = plt.cm.tab10(np.linspace(0, 0.6, len(labels)))
    for i, label in enumerate(labels):
        hist = results[label]["u_max_hist"]
        ax3.semilogy(np.arange(1, len(hist) + 1), hist,
                     lw=1.5, color=colors[i], label=label)
    ax3.set_xlabel("Time step", fontsize=9)
    ax3.set_ylabel("$\\|\\mathbf{u}\\|_\\infty$ (parasitic velocity)", fontsize=9)
    ax3.legend(fontsize=8, loc="upper right")
    ax3.grid(True, which="both", ls="--", alpha=0.4)
    ax3.set_title("Spurious current history", fontsize=9)

    # ── Table annotation ──────────────────────────────────────────────
    dp_exact = float(results["No filter"]["dp_exact"])
    rows = []
    for label in labels:
        r = results[label]
        rows.append(f"{label:12s}  σ_κ={r['kappa_std']:6.2f}  "
                    f"||u||∞={r['u_max']:.2e}  Δp err={r['dp_err']*100:.1f}%")
    fig.text(0.01, 0.005, "\n".join(rows), fontsize=7,
             family="monospace", va="bottom",
             bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    af_kim = -np.cos(XI_C) / 2.0
    fig.suptitle(
        f"Kim compact filter effect on static droplet — "
        f"$N={N}$, $\\rho_l/\\rho_g={int(RHO_L)}$, $We={WE}$, {N_STEPS} steps\n"
        f"Kim: $\\xi_c={XI_C}$, $\\alpha_f={af_kim:.3f}$, "
        f"$H(\\xi_c)=0.5$ per pass.  $\\Delta p_{{exact}}={dp_exact:.4f}$",
        fontsize=10, y=1.002,
    )

    fig.savefig(FIG_PATH, format="pdf", bbox_inches="tight")
    print(f"Saved figure → {FIG_PATH}")
    plt.close(fig)


# ── Entry point ───────────────────────────────────────────────────────────

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
