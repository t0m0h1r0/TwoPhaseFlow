#!/usr/bin/env python3
"""Static droplet — uniform grid, CCD-PPE (sweep §8d), no filter.

Uses IPC (incremental pressure correction):
  - PPE RHS = (1/dt) ∇·u* computed with CCD divergence
  - Solves δp ≡ p^{n+1} − p^n each step → near-zero RHS → sweep converges
  - Pressure updated: p^{n+1} = p^n + δp
  - Corrector: CCD ∇(δp) with wall-Neumann zeroing (balanced-force)

Compares vs FD-PPE baseline (same CSF, same CCD corrector).

A3 traceability
───────────────
  IPC derivation  →  §4 sec:ipc_derivation, eq:predictor_ab2_ipc
  CCD-PPE sweep   →  §8d PPESolverSweep (defect-correction LTS)
  Balanced-force  →  §7 warnbox: CCD ∇p consistent with CCD ∇ψ in CSF

Output:
  experiment/ch12/results/ccdppe_nodroplet/
    ccdppe_nodroplet.pdf
    ccdppe_nodroplet_data.npz

Usage:
  python experiment/ch12/exp12_ccdppe_nodroplet.py
  python experiment/ch12/exp12_ccdppe_nodroplet.py --plot-only
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
from twophase.config import GridConfig, SimulationConfig, SolverConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.ppe_solver_sweep import PPESolverSweep
from twophase.pressure.rhie_chow import RhieChowInterpolator
from twophase.pressure.velocity_corrector import ccd_pressure_gradient

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "ccdppe_nodroplet"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "ccdppe_nodroplet_data.npz"
FIG_PATH = OUT_DIR / "ccdppe_nodroplet.pdf"

# ── Parameters ────────────────────────────────────────────────────────────────
R      = 0.25
SIGMA  = 1.0
WE     = 10.0
RHO_G  = 1.0
RHO_L  = 2.0
N      = 64
N_STEPS = 400


# ── Core simulation ───────────────────────────────────────────────────────────

def run(label: str, use_ccd_ppe: bool):
    """Run static droplet.

    Parameters
    ----------
    label       : str  — identifier
    use_ccd_ppe : bool — True → CCD-PPE sweep (IPC); False → FD-PPE spsolve
    """
    backend = Backend(use_gpu=False)

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

    # ── PPE solvers ───────────────────────────────────────────────────────────
    rhie_chow = RhieChowInterpolator(backend, grid, ccd, bc_type="wall")
    ppb       = PPEBuilder(backend, grid, bc_type="wall")
    triplet, A_shape = ppb.build(rho)
    A_fd      = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    pin_dof   = ppb._pin_dof

    if use_ccd_ppe:
        # Sweep refines from FD warm-start → needs few iterations
        cfg = SimulationConfig(
            grid=gc,
            solver=SolverConfig(
                ppe_solver_type="sweep",
                pseudo_tol=1e-6,
                pseudo_maxiter=100,
                pseudo_c_tau=2.0,
            ),
        )
        ppe_sweep = PPESolverSweep(backend, cfg, grid, ccd)

    # ── Curvature + CSF (static interface — computed once) ────────────────────
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa     = np.asarray(curv_calc.compute(psi))
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x   = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y   = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u = np.zeros_like(X)
    v = np.zeros_like(X)
    p = np.zeros_like(X)     # absolute pressure (p^n)
    u_max_hist = []
    warn_count = 0

    for step in range(N_STEPS):
        # ── Predictor ─────────────────────────────────────────────────────────
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # ── PPE RHS: Rhie-Chow face-velocity divergence (prevents checkerboard) ──
        # Using cell-centred CCD ∇·u* directly causes checkerboard instability.
        # Rhie-Chow adds a face-level pressure damping: §7.4 Eq.65.
        div_rc = rhie_chow.face_velocity_divergence([u_star, v_star], p, rho, dt)
        rhs    = np.asarray(div_rc) / dt

        # ── PPE solve ─────────────────────────────────────────────────────────
        # FD solve (fast, exact O(N²)) — used as baseline and as warm start
        rhs_vec = rhs.ravel().copy()
        rhs_vec[pin_dof] = 0.0
        p_fd = spsolve(A_fd, rhs_vec).reshape(grid.shape)

        if use_ccd_ppe:
            # Refine FD solution with CCD-PPE sweep (warm start → few iters needed)
            import warnings
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                p = np.asarray(ppe_sweep.solve(rhs, rho, dt, p_init=p_fd))
                if caught:
                    warn_count += 1
        else:
            p = p_fd

        # ── Corrector: CCD ∇p with wall-Neumann zeroing (balanced-force) ─────
        grad_p = ccd_pressure_gradient(ccd, p, grid.ndim)
        u = u_star - dt / rho * np.asarray(grad_p[0])
        v = v_star - dt / rho * np.asarray(grad_p[1])
        wall_bc(u); wall_bc(v)

        u_max = float(np.max(np.sqrt(u**2 + v**2)))
        u_max_hist.append(u_max)
        if np.isnan(u_max) or u_max > 1e6:
            print(f"    BLOWUP at step={step + 1}")
            break

    if warn_count > 0:
        print(f"    [warn] PPE sweep 未収束 {warn_count}/{N_STEPS} ステップ")

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

CONFIGS = [
    ("FD-PPE",  False),
    ("CCD-PPE", True),
]


def compute_all():
    results = {}
    for label, use_ccd in CONFIGS:
        print(f"  [{label}] ...")
        r = run(label, use_ccd)
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

def plot(results):
    labels = [lb for lb, _ in CONFIGS if lb in results]
    ncols  = len(labels)
    x1d    = np.linspace(0, 1, N + 1)

    all_p   = np.concatenate([results[lb]["p"].ravel() for lb in labels])
    vmax_p  = float(np.nanpercentile(np.abs(all_p), 99)) * 1.05 or 0.1
    vmax_u  = max(float(results[lb]["vel_mag"].max()) for lb in labels) or 1e-10
    all_kap = np.concatenate([
        results[lb]["kappa"][np.abs(results[lb]["phi_raw"]) < 2.0 * 1.5 / N].ravel()
        for lb in labels
    ])
    kap_lim = float(np.nanpercentile(np.abs(all_kap), 98)) if len(all_kap) else 1.0

    fig = plt.figure(figsize=(5 * ncols, 12))
    gs  = fig.add_gridspec(4, ncols, hspace=0.5, wspace=0.35,
                           height_ratios=[1, 1, 1, 1.2])

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
        ax0.set_title(label, fontsize=11, fontweight="bold")
        ax0.set_aspect("equal"); ax0.tick_params(labelsize=7)
        if col == 0:
            ax0.set_ylabel("$\\kappa$", fontsize=9)
        plt.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        km = float(np.mean(r["kappa"][near])) if np.any(near) else float("nan")
        ks = float(np.std(r["kappa"][near]))  if np.any(near) else float("nan")
        ax0.text(0.02, 0.03, f"$\\bar\\kappa$={km:.3f}  $\\sigma$={ks:.3f}",
                 transform=ax0.transAxes, fontsize=8, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 1: pressure ───────────────────────────────────────────────
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
                 f"$\\Delta p$={r['dp_meas']:.4f}  (err {r['dp_err']*100:.1f}%)",
                 transform=ax1.transAxes, fontsize=7, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

        # ── Row 2: |u| ───────────────────────────────────────────────────
        ax2 = fig.add_subplot(gs[2, col])
        im2 = ax2.pcolormesh(x1d, x1d, r["vel_mag"].T,
                             cmap="hot_r", vmin=0, vmax=vmax_u,
                             shading="auto")
        ax2.contour(x1d, x1d, phi.T, levels=[0], colors="w", linewidths=0.8)
        ax2.set_aspect("equal"); ax2.tick_params(labelsize=7)
        if col == 0:
            ax2.set_ylabel("$|\\mathbf{u}|$", fontsize=9)
        plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
        ax2.text(0.02, 0.03,
                 f"$\\|u\\|_\\infty$ = {r['u_max']:.2e}",
                 transform=ax2.transAxes, fontsize=8, va="bottom",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8))

    # ── Row 3: ||u||_∞ history ────────────────────────────────────────────
    ax3    = fig.add_subplot(gs[3, :])
    colors = ["tab:blue", "tab:orange"]
    for i, label in enumerate(labels):
        hist = results[label]["u_max_hist"]
        t_ax = np.arange(1, len(hist) + 1) * (0.25 / N)
        ax3.semilogy(t_ax, hist, lw=1.8, color=colors[i], label=label)
    ax3.set_xlabel("Physical time $t$", fontsize=9)
    ax3.set_ylabel("$\\|\\mathbf{u}\\|_\\infty$", fontsize=9)
    ax3.legend(fontsize=9)
    ax3.grid(True, which="both", ls="--", alpha=0.4)
    ax3.set_title(
        "Spurious current history — FD-PPE vs CCD-PPE (IPC, sweep §8d)",
        fontsize=9,
    )

    dp_exact = float(results[labels[0]]["dp_exact"])
    rows = []
    for label in labels:
        r = results[label]
        rows.append(
            f"{label:10s}  σ_κ={r['kappa_std']:.3f}  "
            f"‖u‖∞={r['u_max']:.2e}  Δp err={r['dp_err']*100:.1f}%"
        )
    fig.text(0.01, 0.005, "\n".join(rows), fontsize=8,
             family="monospace", va="bottom",
             bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    fig.suptitle(
        f"Static droplet — FD-PPE vs CCD-PPE, uniform grid, no filter\n"
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
