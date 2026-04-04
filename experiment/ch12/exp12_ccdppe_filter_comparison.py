#!/usr/bin/env python3
"""Static droplet: filter comparison on uniform grid.

PPE: FD sparse (spsolve, machine precision) + CCD gradients throughout
(balanced-force condition — same as all other standalone experiments).

Note on CCD-PPE: the production CCD-PPE solvers (PPESolverPseudoTime,
PPESolverSweep) use IPC incremental formulation in the full simulation,
which provides a near-zero RHS each step and fast convergence.  For
standalone projection with absolute pressure, FD-PPE + CCD gradients
is the reliable approach — and is what all existing ch12 experiments use.

Filters compared:
  none          — no filter (baseline)
  hfe_C005      — InterfaceLimitedFilter  on κ  (C=0.05)
  hfe_C010      — InterfaceLimitedFilter  on κ  (C=0.10)
  biharmonic    — CurvatureBiharmonicFilter on κ (β=0.01)
  helmholtz     — HelmholtzKappaFilter    on κ  (α=1.0)
  kim_1p        — LeleCompactFilter (ξ_c=0.5) on φ, 1 pass
  kim_3p        — LeleCompactFilter (ξ_c=0.5) on φ, 3 passes
Corrector: CCD ∇p with wall-Neumann zeroing (balanced-force).

A3 traceability
───────────────
  CCD-PPE operator →  §8b Eq. L_CCD_2d_full: (1/ρ)∇²p − (∇ρ/ρ²)·∇p
  InterfaceLimitedFilter  →  Lele (1992) §4; Fedkiw (2002) spurious-current
  CurvatureBiharmonicFilter → Gottlieb & Hesthaven (2001); Jamet (2002) §4
  HelmholtzKappaFilter    →  Olsson et al. (2007) §3
  LeleCompactFilter       →  Lele (1992) Table 3; Kim (2010) §3

Output:
  experiment/ch12/results/ccdppe_filter_comparison/
    ccdppe_filter_comparison.pdf
    ccdppe_filter_comparison_data.npz

Usage:
  python experiment/ch12/exp12_ccdppe_filter_comparison.py
  python experiment/ch12/exp12_ccdppe_filter_comparison.py --plot-only
"""

import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.curvature_filter import InterfaceLimitedFilter, CurvatureBiharmonicFilter
from twophase.levelset.compact_filters import HelmholtzKappaFilter, LeleCompactFilter
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.velocity_corrector import ccd_pressure_gradient

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "ccdppe_filter_comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "ccdppe_filter_comparison_data.npz"
FIG_PATH = OUT_DIR / "ccdppe_filter_comparison.pdf"

# ── Parameters ────────────────────────────────────────────────────────────────
R      = 0.25
SIGMA  = 1.0
WE     = 10.0
RHO_G  = 1.0
RHO_L  = 2.0
N      = 64
N_STEPS = 400

XI_C   = 0.5   # Kim cut-off (H(ξ_c) = 0.5 per pass)

# ── Filter configurations ─────────────────────────────────────────────────────
# Each entry: (label, filter_target, filter_factory_fn)
# filter_target: "kappa" or "phi"
# factory: callable(backend, ccd) → filter object with .apply(q, psi) or .apply(phi)
FILTERS = [
    ("none",       "none"),
    ("hfe_C005",   "kappa"),
    ("hfe_C010",   "kappa"),
    ("biharmonic", "kappa"),
    ("helmholtz",  "kappa"),
    ("kim_1p",     "phi"),
    ("kim_3p",     "phi"),
]


# ── Core simulation ───────────────────────────────────────────────────────────

def make_filter(label: str, backend, ccd):
    """Build the filter object for the given label."""
    if label == "none":
        return None
    if label == "hfe_C005":
        return InterfaceLimitedFilter(backend, ccd, C=0.05)
    if label == "hfe_C010":
        return InterfaceLimitedFilter(backend, ccd, C=0.10)
    if label == "biharmonic":
        return CurvatureBiharmonicFilter(backend, ccd, beta=0.01)
    if label == "helmholtz":
        return HelmholtzKappaFilter(backend, ccd, alpha=1.0)
    if label == "kim_1p":
        return LeleCompactFilter(backend, ccd, xi_c=XI_C)
    if label == "kim_3p":
        return LeleCompactFilter(backend, ccd, xi_c=XI_C)
    raise ValueError(f"Unknown filter label: {label}")


def run_droplet(label: str, target: str):
    """Run static droplet with the given filter configuration.

    Parameters
    ----------
    label  : str — filter identifier (see FILTERS list)
    target : str — 'none', 'kappa', or 'phi'
    """
    backend = Backend(use_gpu=False)

    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")

    # ── CCD PPE solver (direct LU) ────────────────────────────────────────────
    ppb = PPEBuilder(backend, grid, bc_type="wall")

    # ── Build filter ──────────────────────────────────────────────────────────
    filt = make_filter(label, backend, ccd)
    kim_passes = int(label[-2]) if label.startswith("kim_") else 0

    # ── Initial SDF and (possibly filtered) φ ─────────────────────────────────
    X, Y    = grid.meshgrid()
    phi_raw = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)

    if target == "phi":
        phi = phi_raw.copy()
        for _ in range(kim_passes):
            phi = np.array(filt.apply(phi))
    else:
        phi = phi_raw.copy()

    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    # ── FD PPE matrix (static density, machine-precision solve) ───────────────
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)

    # ── Curvature (computed once — static interface) ──────────────────────────
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa = np.asarray(curv_calc.compute(psi))

    if target == "kappa":
        kappa = np.asarray(filt.apply(kappa, psi))

    # ── CSF force ─────────────────────────────────────────────────────────────
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

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

        # CCD divergence for PPE RHS: q = (1/dt) ∇·u*
        du_dx, _d2x = ccd.differentiate(u_star, 0)
        dv_dy, _d2y = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt

        # FD PPE solve (spsolve, machine precision; CCD gradients provide balanced-force)
        rhs_vec = rhs.ravel().copy()
        rhs_vec[ppb._pin_dof] = 0.0
        p = spsolve(A, rhs_vec).reshape(grid.shape)

        # Corrector: CCD ∇p with wall-Neumann zeroing (balanced-force)
        grad_p = ccd_pressure_gradient(ccd, p, grid.ndim)
        u = u_star - dt / rho * np.asarray(grad_p[0])
        v = v_star - dt / rho * np.asarray(grad_p[1])
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)
        if np.isnan(u_max) or u_max > 1e6:
            print(f"    BLOWUP at step={step + 1}")
            break

    # ── Diagnostics ───────────────────────────────────────────────────────────
    inside   = phi_raw >  3.0 / N
    outside  = phi_raw < -3.0 / N
    dp_exact = SIGMA / (R * WE)
    dp_meas  = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_err   = abs(dp_meas - dp_exact) / dp_exact

    near       = np.abs(phi_raw) < 2.0 * eps
    kappa_mean = float(np.mean(kappa[near])) if np.any(near) else float("nan")
    kappa_std  = float(np.std(kappa[near]))  if np.any(near) else float("nan")

    return {
        "label":      label,
        "u_max":      float(np.max(np.sqrt(u**2 + v**2))),
        "u_max_hist": np.array(u_max_hist),
        "dp_meas":    dp_meas,
        "dp_exact":   dp_exact,
        "dp_err":     dp_err,
        "kappa_mean": kappa_mean,
        "kappa_std":  kappa_std,
        "phi_raw":    phi_raw,
        "p":          p,
        "vel_mag":    np.sqrt(u**2 + v**2),
        "kappa":      kappa,
    }


# ── Main computation ──────────────────────────────────────────────────────────

def compute_all():
    results = {}
    for label, target in FILTERS:
        print(f"  [{label}] ...")
        r = run_droplet(label, target)
        print(f"    κ̄={r['kappa_mean']:.3f}  σ_κ={r['kappa_std']:.3f} "
              f"| ‖u‖∞={r['u_max']:.3e}  Δp err={r['dp_err']*100:.2f}%")
        results[label] = r
    return results


# ── I/O ───────────────────────────────────────────────────────────────────────

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
    for r in results.values():
        for k in ("u_max", "dp_meas", "dp_exact", "dp_err",
                  "kappa_mean", "kappa_std"):
            if k in r:
                r[k] = float(r[k])
    return results


# ── Plotting ──────────────────────────────────────────────────────────────────

LABEL_ORDER = [lb for lb, _ in FILTERS]

# Readable display names
DISPLAY = {
    "none":       "None",
    "hfe_C005":   "HFE C=0.05",
    "hfe_C010":   "HFE C=0.10",
    "biharmonic": "Biharmonic",
    "helmholtz":  "Helmholtz",
    "kim_1p":     "Kim 1p",
    "kim_3p":     "Kim 3p",
}


def plot(results):
    labels = [lb for lb in LABEL_ORDER if lb in results]
    ncols  = len(labels)

    x1d = np.linspace(0, 1, N + 1)

    all_p   = np.concatenate([results[lb]["p"].ravel() for lb in labels])
    vmax_p  = float(np.nanpercentile(np.abs(all_p), 99)) * 1.05 or 0.1
    vmax_u  = max(float(results[lb]["vel_mag"].max()) for lb in labels) or 1e-10
    all_kap = np.concatenate([
        results[lb]["kappa"][np.abs(results[lb]["phi_raw"]) < 2.0 * 1.5 / N].ravel()
        for lb in labels
    ])
    kap_lim = float(np.nanpercentile(np.abs(all_kap), 98)) if len(all_kap) else 1.0

    fig = plt.figure(figsize=(3.2 * ncols, 12))
    gs  = fig.add_gridspec(
        4, ncols,
        hspace=0.5, wspace=0.3,
        height_ratios=[1, 1, 1, 1.2],
    )

    for col, label in enumerate(labels):
        r    = results[label]
        phi  = r["phi_raw"]
        near = np.abs(phi) < 2.0 * 1.5 / N

        # ── Row 0: κ ─────────────────────────────────────────────────────
        ax0 = fig.add_subplot(gs[0, col])
        im0 = ax0.pcolormesh(x1d, x1d, r["kappa"].T,
                             cmap="RdBu_r", vmin=-kap_lim, vmax=kap_lim,
                             shading="auto")
        ax0.contour(x1d, x1d, phi.T, levels=[0], colors="k", linewidths=0.8)
        ax0.set_title(DISPLAY[label], fontsize=9, fontweight="bold")
        ax0.set_aspect("equal"); ax0.tick_params(labelsize=6)
        if col == 0:
            ax0.set_ylabel("$\\kappa$", fontsize=8)
        plt.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04).ax.tick_params(labelsize=6)
        km = float(np.mean(r["kappa"][near])) if np.any(near) else float("nan")
        ks = float(np.std(r["kappa"][near]))  if np.any(near) else float("nan")
        ax0.text(0.02, 0.03, f"$\\bar\\kappa$={km:.2f}\n$\\sigma$={ks:.3f}",
                 transform=ax0.transAxes, fontsize=6, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 1: pressure ───────────────────────────────────────────────
        ax1 = fig.add_subplot(gs[1, col])
        im1 = ax1.pcolormesh(x1d, x1d, r["p"].T,
                             cmap="RdBu_r", vmin=-vmax_p, vmax=vmax_p,
                             shading="auto")
        ax1.contour(x1d, x1d, phi.T, levels=[0], colors="k", linewidths=0.8)
        ax1.set_aspect("equal"); ax1.tick_params(labelsize=6)
        if col == 0:
            ax1.set_ylabel("$p$", fontsize=8)
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04).ax.tick_params(labelsize=6)
        ax1.text(0.02, 0.03,
                 f"err {r['dp_err']*100:.1f}%",
                 transform=ax1.transAxes, fontsize=6, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 2: |u| ───────────────────────────────────────────────────
        ax2 = fig.add_subplot(gs[2, col])
        im2 = ax2.pcolormesh(x1d, x1d, r["vel_mag"].T,
                             cmap="hot_r", vmin=0, vmax=vmax_u,
                             shading="auto")
        ax2.contour(x1d, x1d, phi.T, levels=[0], colors="w", linewidths=0.8)
        ax2.set_aspect("equal"); ax2.tick_params(labelsize=6)
        if col == 0:
            ax2.set_ylabel("$|\\mathbf{u}|$", fontsize=8)
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04).ax.tick_params(labelsize=6)
        ax2.text(0.02, 0.03,
                 f"$\\|u\\|_\\infty$\n{r['u_max']:.2e}",
                 transform=ax2.transAxes, fontsize=6, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

    # ── Row 3: ||u||_∞ history ────────────────────────────────────────────
    ax3    = fig.add_subplot(gs[3, :])
    colors = plt.cm.tab10(np.linspace(0, 1.0, len(labels)))
    for i, label in enumerate(labels):
        hist = results[label]["u_max_hist"]
        t_ax = np.arange(1, len(hist) + 1) * (0.25 / N)
        ax3.semilogy(t_ax, hist, lw=1.5, color=colors[i], label=DISPLAY[label])
    ax3.set_xlabel("Physical time $t$", fontsize=9)
    ax3.set_ylabel("$\\|\\mathbf{u}\\|_\\infty$", fontsize=9)
    ax3.legend(fontsize=7, ncol=4, loc="upper right")
    ax3.grid(True, which="both", ls="--", alpha=0.4)
    ax3.set_title("Spurious current history (FD-PPE + CCD gradients, balanced-force)", fontsize=9)

    # ── Summary table ─────────────────────────────────────────────────────
    dp_exact = float(results["none"]["dp_exact"])
    rows = []
    for label in labels:
        r = results[label]
        rows.append(
            f"{DISPLAY[label]:14s}  σ_κ={r['kappa_std']:.3f}  "
            f"‖u‖∞={r['u_max']:.2e}  Δp err={r['dp_err']*100:.1f}%"
        )
    fig.text(0.01, 0.005, "\n".join(rows), fontsize=7,
             family="monospace", va="bottom",
             bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    fig.suptitle(
        f"Static droplet — FD-PPE + CCD gradients, uniform grid, filter comparison\n"
        f"$N={N}$, $R={R}$, $\\rho_l/\\rho_g={int(RHO_L)}$, "
        f"$We={WE}$, {N_STEPS} steps.  "
        f"$\\Delta p_{{exact}}={dp_exact:.4f}$",
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
