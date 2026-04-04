#!/usr/bin/env python3
"""Static droplet benchmark: uniform vs interface-fitted non-uniform grid.

No filter applied.  Compares four grid configurations:
  alpha=1.0  — uniform grid (baseline)
  alpha=2.0  — interface-fitted, concentration factor 2
  alpha=4.0  — interface-fitted, concentration factor 4
  alpha=8.0  — interface-fitted, concentration factor 8

Metrics:
  - Spurious current ||u||_∞ history
  - Laplace pressure error |Δp_meas − σ/(R·We)| / (σ/(R·We))
  - Curvature mean κ̄ and std σ_κ at interface
  - Minimum grid spacing h_min (shows how much the grid concentrates)

A3 traceability
───────────────
  Grid fitting  →  §6 eq:grid_delta: ω = 1 + (α−1)·δ*(φ), δ* = Gaussian delta
  PPE           →  §7.3 Eq.63: FVM variable-density Poisson (non-uniform path)
  CCD gradients →  §4.9 chain-rule metric transform for non-uniform spacing
  CSF force     →  §2b: f_σ = (σ/We)·κ·∇ψ

Output:
  experiment/ch12/results/uniform_vs_nonuniform_droplet/
    uniform_vs_nonuniform_droplet.pdf
    uniform_vs_nonuniform_droplet_data.npz

Usage:
  python experiment/ch12/exp12_uniform_vs_nonuniform_droplet.py
  python experiment/ch12/exp12_uniform_vs_nonuniform_droplet.py --plot-only
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

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "uniform_vs_nonuniform_droplet"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "uniform_vs_nonuniform_droplet_data.npz"
FIG_PATH = OUT_DIR / "uniform_vs_nonuniform_droplet.pdf"

# ── Parameters ────────────────────────────────────────────────────────────────
R       = 0.25
SIGMA   = 1.0
WE      = 10.0
RHO_G   = 1.0
RHO_L   = 2.0
N       = 64
N_STEPS = 400

ALPHA_LIST  = [1.0, 2.0, 3.0, 4.0]   # 1.0 = uniform
MAX_STEPS   = 6000                    # cap to prevent excessive runtime


# ── Core simulation ───────────────────────────────────────────────────────────

def run_droplet(alpha: float):
    """Run static droplet on uniform (alpha=1) or interface-fitted (alpha>1) grid.

    Parameters
    ----------
    alpha : float — grid concentration factor (1.0 = uniform)
    """
    backend = Backend(use_gpu=False)

    # ── Build grid ────────────────────────────────────────────────────────────
    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha)
    grid = Grid(gc, backend)

    # Initial uniform spacing (before fitting) — used for eps
    h_unif = 1.0 / N
    eps    = 1.5 * h_unif

    # Initial SDF on uniform grid (needed for grid fitting)
    X0, Y0 = grid.meshgrid()
    phi_sdf = R - np.sqrt((X0 - 0.5)**2 + (Y0 - 0.5)**2)   # φ > 0 inside

    # Apply interface-fitted grid (no-op when alpha=1.0)
    if alpha > 1.0:
        ccd_tmp = CCDSolver(grid, backend, bc_type="wall")
        grid.update_from_levelset(phi_sdf, eps, ccd_tmp)

    # Recompute coords after fitting
    X, Y   = grid.meshgrid()
    phi    = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)

    h_min  = float(min(grid.h[0].min(), grid.h[1].min()))
    # dt based on actual h_min — non-uniform grids have smaller spacing near interface
    dt     = 0.25 * h_min

    # ── Solvers on final grid ─────────────────────────────────────────────────
    ccd      = CCDSolver(grid, backend, bc_type="wall")
    ppb      = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    # ── PPE matrix (static density) ───────────────────────────────────────────
    triplet, A_shape = ppb.build(rho)
    A = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    # ── CSF force (static interface — computed once) ───────────────────────────
    kappa    = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x  = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y  = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    u = np.zeros_like(X)
    v = np.zeros_like(X)
    p = np.zeros_like(X)
    u_max_hist = []
    # Keep same physical end time as uniform baseline: T = N_STEPS * dt_unif
    T_final  = N_STEPS * (0.25 * h_unif)
    n_steps  = min(MAX_STEPS, max(N_STEPS, int(np.ceil(T_final / dt))))
    T_actual = n_steps * dt
    print(f"    T_final={T_final:.4f}  dt={dt:.5f}  n_steps={n_steps}  T_actual={T_actual:.4f}")

    for step in range(n_steps):
        # Predictor
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE RHS
        du_dx, _ddx = ccd.differentiate(u_star, 0)
        dv_dy, _ddy = ccd.differentiate(v_star, 1)
        rhs     = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
        rhs_vec = rhs.ravel().copy()
        rhs_vec[ppb._pin_dof] = 0.0

        # Solve PPE
        p = spsolve(A, rhs_vec).reshape(grid.shape)

        # Corrector
        dp_dx, _d2x = ccd.differentiate(p, 0)
        dp_dy, _d2y = ccd.differentiate(p, 1)
        ccd.enforce_wall_neumann(dp_dx, 0)
        ccd.enforce_wall_neumann(dp_dy, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)
        if np.isnan(u_max) or u_max > 1e6:
            print(f"    BLOWUP at step={step + 1}")
            break

    # ── Diagnostics ───────────────────────────────────────────────────────────
    inside   = phi >  3.0 / N   # φ > 0 inside droplet
    outside  = phi < -3.0 / N   # φ < 0 outside droplet
    dp_exact = SIGMA / (R * WE)
    dp_meas  = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_err   = abs(dp_meas - dp_exact) / dp_exact

    kappa_np  = np.asarray(kappa)
    near      = np.abs(phi) < 2.0 * eps
    kappa_mean = float(np.mean(kappa_np[near])) if np.any(near) else float("nan")
    kappa_std  = float(np.std(kappa_np[near]))  if np.any(near) else float("nan")

    return {
        "alpha":      alpha,
        "h_min":      h_min,
        "h_unif":     h_unif,
        "dt":         dt,
        "n_steps":    float(len(u_max_hist)),   # actual steps run
        "u_max":      float(np.max(np.sqrt(u**2 + v**2))),
        "u_max_hist": np.array(u_max_hist),
        "dp_meas":    dp_meas,
        "dp_exact":   dp_exact,
        "dp_err":     dp_err,
        "kappa_mean": kappa_mean,
        "kappa_std":  kappa_std,
        "phi":        phi,
        "psi":        psi,
        "p":          p,
        "vel_mag":    np.sqrt(u**2 + v**2),
        "kappa":      kappa_np,
        "coords_x":   grid.coords[0],
        "coords_y":   grid.coords[1],
    }


# ── Main computation ──────────────────────────────────────────────────────────

def compute_all():
    results = {}
    for alpha in ALPHA_LIST:
        label = _alpha_label(alpha)
        print(f"  [{label}] alpha={alpha} ...")
        r = run_droplet(alpha)
        print(f"    h_min={r['h_min']:.4f}  κ̄={r['kappa_mean']:.3f}  "
              f"σ_κ={r['kappa_std']:.3f} | ||u||∞={r['u_max']:.3e}  "
              f"Δp err={r['dp_err']*100:.2f}%")
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
        for k in ("alpha", "h_min", "u_max", "dp_meas", "dp_exact",
                  "dp_err", "kappa_mean", "kappa_std"):
            if k in r:
                r[k] = float(r[k])
    return results


# ── Plotting ──────────────────────────────────────────────────────────────────

def _label_order():
    return ["Uniform"] + [f"α={a:.0f}" for a in ALPHA_LIST if a > 1.0]


def _alpha_label(alpha: float) -> str:
    return "Uniform" if alpha == 1.0 else f"α={alpha:.0f}"


def plot(results):
    labels = [lb for lb in _label_order() if lb in results]
    ncols  = len(labels)

    # ── Shared colour limits ───────────────────────────────────────────────
    all_p   = np.concatenate([results[lb]["p"].ravel() for lb in labels])
    vmax_p  = float(np.nanpercentile(np.abs(all_p), 99)) * 1.05
    vmax_u  = max(float(results[lb]["vel_mag"].max()) for lb in labels)
    all_kap = np.concatenate([
        results[lb]["kappa"][np.abs(results[lb]["phi"]) < 2.0 * 1.5 / N].ravel()
        for lb in labels
    ])
    kap_lim = float(np.nanpercentile(np.abs(all_kap), 98)) if len(all_kap) else 1.0

    fig = plt.figure(figsize=(4 * ncols, 13))
    gs  = fig.add_gridspec(
        5, ncols,
        hspace=0.5, wspace=0.35,
        height_ratios=[1, 1, 1, 0.6, 1.2],
    )

    for col, label in enumerate(labels):
        r    = results[label]
        phi  = r["phi"]
        cx   = np.asarray(r["coords_x"])
        cy   = np.asarray(r["coords_y"])
        near = np.abs(phi) < 2.0 * 1.5 / N

        # ── Row 0: κ field ────────────────────────────────────────────────
        ax0 = fig.add_subplot(gs[0, col])
        im0 = ax0.pcolormesh(cx, cy, r["kappa"].T,
                             cmap="RdBu_r", vmin=-kap_lim, vmax=kap_lim,
                             shading="auto")
        ax0.contour(cx, cy, phi.T, levels=[0], colors="k", linewidths=0.8)
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

        # ── Row 1: pressure ───────────────────────────────────────────────
        ax1 = fig.add_subplot(gs[1, col])
        im1 = ax1.pcolormesh(cx, cy, r["p"].T,
                             cmap="RdBu_r", vmin=-vmax_p, vmax=vmax_p,
                             shading="auto")
        ax1.contour(cx, cy, phi.T, levels=[0], colors="k", linewidths=0.8)
        ax1.set_aspect("equal")
        ax1.tick_params(labelsize=7)
        if col == 0:
            ax1.set_ylabel("Pressure $p$", fontsize=8)
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        ax1.text(0.02, 0.03,
                 f"$\\Delta p$={r['dp_meas']:.4f}\nerr {r['dp_err']*100:.1f}%",
                 transform=ax1.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 2: velocity magnitude ─────────────────────────────────────
        ax2 = fig.add_subplot(gs[2, col])
        im2 = ax2.pcolormesh(cx, cy, r["vel_mag"].T,
                             cmap="hot_r", vmin=0, vmax=vmax_u,
                             shading="auto")
        ax2.contour(cx, cy, phi.T, levels=[0], colors="w", linewidths=0.8)
        ax2.set_aspect("equal")
        ax2.tick_params(labelsize=7)
        if col == 0:
            ax2.set_ylabel("$|\\mathbf{u}|$", fontsize=8)
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        ax2.text(0.02, 0.03,
                 f"$\\|u\\|_\\infty$={r['u_max']:.2e}",
                 transform=ax2.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 3: grid density (x-spacing) ───────────────────────────────
        ax3 = fig.add_subplot(gs[3, col])
        dx  = np.diff(cx)
        ax3.bar(0.5 * (cx[:-1] + cx[1:]), dx, width=dx,
                color="steelblue", alpha=0.7, linewidth=0)
        ax3.axvline(0.5 - R, color="r", lw=0.8, ls="--")
        ax3.axvline(0.5 + R, color="r", lw=0.8, ls="--")
        ax3.set_xlim(0, 1)
        ax3.tick_params(labelsize=6)
        ax3.set_ylabel("$\\Delta x$", fontsize=7)
        h_min_val = float(r["h_min"])
        ax3.text(0.02, 0.97, f"$h_{{min}}$={h_min_val:.4f}",
                 transform=ax3.transAxes, fontsize=7, va="top",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

    # ── Row 4: ||u||_∞ history ────────────────────────────────────────────
    ax4    = fig.add_subplot(gs[4, :])
    colors = plt.cm.tab10(np.linspace(0, 0.6, len(labels)))
    for i, label in enumerate(labels):
        hist = results[label]["u_max_hist"]
        dt_r = float(results[label]["dt"])
        t_ax = np.arange(1, len(hist) + 1) * dt_r
        ax4.semilogy(t_ax, hist, lw=1.5, color=colors[i], label=label)
    ax4.set_xlabel("Physical time $t$", fontsize=9)
    ax4.set_ylabel("$\\|\\mathbf{u}\\|_\\infty$ (parasitic velocity)", fontsize=9)
    ax4.legend(fontsize=8, loc="upper right")
    ax4.grid(True, which="both", ls="--", alpha=0.4)
    ax4.set_title("Spurious current history", fontsize=9)

    # ── Summary table ─────────────────────────────────────────────────────
    dp_exact = float(results["Uniform"]["dp_exact"])
    rows = []
    for label in labels:
        r = results[label]
        rows.append(
            f"{label:10s}  h_min={r['h_min']:.4f}  "
            f"σ_κ={r['kappa_std']:6.3f}  "
            f"||u||∞={r['u_max']:.2e}  "
            f"Δp err={r['dp_err']*100:.1f}%"
        )
    fig.text(0.01, 0.005, "\n".join(rows), fontsize=7,
             family="monospace", va="bottom",
             bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    fig.suptitle(
        f"Static droplet: uniform vs interface-fitted grid (no filter)\n"
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
