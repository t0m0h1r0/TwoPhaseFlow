#!/usr/bin/env python3
"""Filter comparison: curvature and surface tension for a static circle.

Compares 5 filter configurations on curvature κ and CSF force f_σ = κ∇ψ/We:
  (A) No filter         — baseline (perturbed circle, no smoothing)
  (B) NormalVectorFilter — diffusion on n = ∇φ/|∇φ|  (existing)
  (C) HFE filter        — explicit Laplacian on κ   (existing, near-Nyquist)
  (D) Helmholtz κ       — implicit Helmholtz on κ   (NEW, intermediate-k)
  (E) Kim compact φ     — Padé compact filter on φ  (NEW, prescribed cut-off)

Visualizes:
  Row 1: curvature κ field (RdBu_r)
  Row 2: |f_σ| magnitude  (hot_r)
  Row 3: κ slice at y = 0.5

Output:
  experiment/ch12/results/filter_comparison/filter_comparison.{eps,pdf}
  experiment/ch12/results/filter_comparison/filter_comparison_data.npz

Usage:
  python experiment/ch12/viz_ch12_filter_comparison.py          # compute + plot
  python experiment/ch12/viz_ch12_filter_comparison.py --plot-only
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
from twophase.levelset.normal_filter import NormalVectorFilter, kappa_from_normals
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.levelset.compact_filters import HelmholtzKappaFilter, LeleCompactFilter
from twophase.ns_terms.surface_tension import SurfaceTensionTerm

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "filter_comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "filter_comparison_data.npz"
FIG_PATH = OUT_DIR / "filter_comparison.eps"

# ── Simulation parameters ─────────────────────────────────────────────────
N = 64
R = 0.25
WE = 1.0          # We=1 → f_σ = κ∇ψ (amplified for visualization)

# Filter strengths
ALPHA_NF   = 0.10  # NormalVectorFilter   (C < 0.125, 2D stable)
C_HFE      = 0.10  # InterfaceLimitedFilter (explicit Laplacian)
ALPHA_HELM = 1.0   # HelmholtzKappaFilter  (α > 0, unconditionally stable)
XI_C_KIM   = 0.5   # LeleCompactFilter cut-off kh (targets m=8 on N=64)
                   # α_f = -cos(0.5)/2 ≈ -0.439 → H(0.5)=0.5 per pass

N_PASSES = 5       # filter passes (accumulates smoothing effect)

# Sinusoidal perturbation: R(θ) = R + δ cos(m θ)
# Mode m=8 → spatial wavenumber kh = 2πm/N ≈ 0.785 rad (angular), but
# physical kh = m/R × h = 8/0.25 / 64 ≈ 0.5 rad — right in middle of spectrum.
PERTURB_AMP  = 0.015   # δ ≈ 1.5% of R
PERTURB_MODE = 8       # m: angular wavenumber

# (label, use_nf, use_hfe, use_helm, use_pade)
CONFIGS = [
    ("No filter",        False, False, False, False),
    ("NF",               True,  False, False, False),
    ("Kim (φ)",          False, False, False, True),
    ("NF + Kim",         True,  False, False, True),
]


# ── Computation ───────────────────────────────────────────────────────────────

def compute_all():
    backend = Backend(use_gpu=False)
    h   = 1.0 / N
    eps = 1.5 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend)
    xp   = backend.xp

    # ── Perturbed circle SDF ───────────────────────────────────────────────
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    dx, dy = X - 0.5, Y - 0.5
    theta   = np.arctan2(dy, dx)
    r_local = R + PERTURB_AMP * np.cos(PERTURB_MODE * theta)
    phi     = np.sqrt(dx ** 2 + dy ** 2) - r_local
    psi     = heaviside(xp, phi, eps)

    kappa_theory = -1.0 / R

    # ── Filter instances ───────────────────────────────────────────────────
    nf   = NormalVectorFilter(backend, ccd, eps, alpha=ALPHA_NF)
    hfe  = InterfaceLimitedFilter(backend, ccd, C=C_HFE)
    helm = HelmholtzKappaFilter(backend, ccd, alpha=ALPHA_HELM)
    pade = LeleCompactFilter(backend, ccd, xi_c=XI_C_KIM)
    sf   = SurfaceTensionTerm(backend, WE)

    curv_base = CurvatureCalculator(backend, ccd, eps)

    psi_xp = xp.asarray(np.array(psi))
    phi_xp = xp.asarray(phi)

    # Initial n from original phi
    d1_phi  = [ccd.differentiate(phi_xp, ax)[0] for ax in range(2)]
    grad_sq = sum(g * g for g in d1_phi)
    grad_nrm = xp.sqrt(xp.maximum(grad_sq, 1e-3 ** 2))
    n_init  = [g / grad_nrm for g in d1_phi]

    kappa_base = xp.asarray(np.array(curv_base.compute(psi)))

    results = {}
    for label, use_nf, use_hfe, use_helm, use_pade in CONFIGS:
        print(f"  Computing: {label}")

        if use_pade:
            # Kim compact filter: apply to φ before CCD, then compute κ cleanly
            phi_f = phi.copy()
            for _ in range(N_PASSES):
                phi_f = np.array(pade.apply(phi_f))
            psi_f   = heaviside(xp, phi_f, eps)
            kappa   = np.array(curv_base.compute(psi_f))

        elif not use_nf and not use_hfe and not use_helm:
            # Baseline: no filter
            kappa = np.array(kappa_base)

        else:
            # Iterative n/κ filtering passes
            n_cur    = list(n_init)
            kappa_cur = kappa_base.copy()

            for _ in range(N_PASSES):
                if use_nf:
                    n_cur     = nf.apply(n_cur, phi_xp)
                    kappa_cur = kappa_from_normals(xp, ccd, n_cur)
                if use_hfe:
                    kappa_cur = hfe.apply(kappa_cur, psi_xp)
                if use_helm:
                    kappa_cur = helm.apply(kappa_cur, psi_xp)

            kappa = np.array(kappa_cur)

        fsigma_list = sf.compute(xp.asarray(kappa), psi, ccd)
        fsigma_mag  = np.sqrt(sum(np.array(f) ** 2 for f in fsigma_list))

        results[label] = {"kappa": kappa, "fsigma_mag": fsigma_mag}

    results["_meta"] = {
        "phi":          phi,
        "psi":          np.array(psi),
        "X":            X,
        "Y":            Y,
        "kappa_theory": kappa_theory,
        "N":            N,
        "R":            R,
        "eps":          eps,
        "alpha_nf":     ALPHA_NF,
        "C_hfe":        C_HFE,
        "alpha_helm":   ALPHA_HELM,
        "xi_c_kim":     XI_C_KIM,
        "n_passes":     N_PASSES,
    }
    return results


# ── I/O ───────────────────────────────────────────────────────────────────────

def save_npz(results):
    flat = {}
    for key, val in results.items():
        if isinstance(val, dict):
            for k2, v2 in val.items():
                flat[f"{key}__{k2}"] = v2
    np.savez(NPZ_PATH, **flat)
    print(f"Saved data → {NPZ_PATH}")


def load_npz():
    data = np.load(NPZ_PATH, allow_pickle=False)
    results = {}
    for fullkey, val in data.items():
        if "__" in fullkey:
            label, subkey = fullkey.split("__", 1)
            results.setdefault(label, {})[subkey] = val
        else:
            results[fullkey] = val
    return results


# ── Plotting ──────────────────────────────────────────────────────────────────

def plot(results):
    meta = results["_meta"]
    X, Y = meta["X"], meta["Y"]
    phi  = meta["phi"]
    kappa_theory = float(meta["kappa_theory"])
    N_grid = int(meta["N"])

    labels = [cfg[0] for cfg in CONFIGS]
    ncols  = len(labels)
    mid    = N_grid // 2
    x_coords = np.linspace(0, 1, N_grid + 1)

    fig, axes = plt.subplots(
        3, ncols,
        figsize=(3.5 * ncols, 9),
        gridspec_kw={"hspace": 0.42, "wspace": 0.32},
    )

    # ── Shared colour limits ─────────────────────────────────────────────
    near = np.abs(phi) < 3 * float(meta["eps"])
    all_kappa_near = np.concatenate([results[lb]["kappa"][near] for lb in labels])
    kappa_lim = float(np.nanpercentile(np.abs(all_kappa_near), 98))

    fsig_lim = max(
        float(np.nanpercentile(results[lb]["fsigma_mag"], 99.0)) * 1.05
        for lb in labels
    )

    for col, label in enumerate(labels):
        kappa      = results[label]["kappa"]
        fsigma_mag = results[label]["fsigma_mag"]

        # ── Row 0: κ field ─────────────────────────────────────────────
        ax0 = axes[0, col]
        im0 = ax0.pcolormesh(X, Y, kappa, cmap="RdBu_r",
                             vmin=-kappa_lim, vmax=kappa_lim, shading="auto")
        ax0.contour(X, Y, phi, levels=[0], colors="k", linewidths=0.8)
        ax0.set_title(label, fontsize=9, fontweight="bold")
        ax0.set_aspect("equal")
        ax0.set_xticks([0, 0.5, 1]); ax0.set_yticks([0, 0.5, 1])
        ax0.tick_params(labelsize=7)
        if col == 0:
            ax0.set_ylabel("$y$", fontsize=8)
        plt.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)

        near_local = np.abs(phi) < 2 * float(meta["eps"])
        if np.any(near_local):
            km = float(np.mean(kappa[near_local]))
            ks = float(np.std(kappa[near_local]))
        else:
            km = ks = float("nan")
        ax0.text(0.02, 0.03,
                 f"$\\bar{{\\kappa}}$={km:.2f}  $\\sigma_\\kappa$={ks:.2f}",
                 transform=ax0.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 1: |f_σ| ───────────────────────────────────────────────
        ax1 = axes[1, col]
        im1 = ax1.pcolormesh(X, Y, fsigma_mag, cmap="hot_r",
                             vmin=0, vmax=fsig_lim, shading="auto")
        ax1.contour(X, Y, phi, levels=[0], colors="w", linewidths=0.8)
        ax1.set_aspect("equal")
        ax1.set_xticks([0, 0.5, 1]); ax1.set_yticks([0, 0.5, 1])
        ax1.tick_params(labelsize=7)
        if col == 0:
            ax1.set_ylabel("$y$", fontsize=8)
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)

        # ── Row 2: κ slice at y = 0.5 ──────────────────────────────────
        ax2 = axes[2, col]
        ax2.plot(x_coords, kappa[:, mid], "b-", lw=1.2, label="$\\kappa$")
        ax2.axhline(kappa_theory, color="r", lw=0.8, ls="--", label="theory")
        ax2.axvline(0.5 - R, color="gray", lw=0.6, ls=":")
        ax2.axvline(0.5 + R, color="gray", lw=0.6, ls=":")
        clip = abs(kappa_theory) * 3.0
        ax2.set_xlim(0, 1)
        ax2.set_ylim(-clip, clip * 0.5)
        ax2.set_xlabel("$x$", fontsize=8)
        if col == 0:
            ax2.set_ylabel("$\\kappa$", fontsize=8)
        ax2.tick_params(labelsize=7)
        if col == ncols - 1:
            ax2.legend(fontsize=7, loc="lower right")

    # Row labels
    for row, rl in enumerate(["$\\kappa$ field", "$|f_\\sigma|$ field",
                               "$\\kappa$ slice ($y=0.5$)"]):
        axes[row, 0].annotate(rl, xy=(-0.38, 0.5), xycoords="axes fraction",
                              ha="center", va="center", fontsize=9, rotation=90)

    n_passes  = int(meta.get("n_passes", N_PASSES))
    alpha_helm = float(meta.get("alpha_helm", ALPHA_HELM))
    xi_c       = float(meta.get("xi_c_kim",   XI_C_KIM))
    af_kim     = -np.cos(xi_c) / 2.0
    fig.suptitle(
        f"Filter comparison — perturbed circle $R={R}$, $N={N}$, {n_passes} passes "
        f"| NF $\\alpha={ALPHA_NF}$, HFE $C={C_HFE}$, "
        f"Helm $\\alpha={alpha_helm}$, Kim $\\xi_c={xi_c:.2f}$ ($\\alpha_f={af_kim:.3f}$)",
        fontsize=9, y=0.998,
    )

    fig.savefig(FIG_PATH, format="eps", bbox_inches="tight", dpi=150)
    pdf_path = FIG_PATH.with_suffix(".pdf")
    fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
    print(f"Saved figure → {FIG_PATH}")
    print(f"Saved figure → {pdf_path}")
    plt.close(fig)


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
