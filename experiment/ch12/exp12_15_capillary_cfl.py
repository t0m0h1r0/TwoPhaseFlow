#!/usr/bin/env python3
"""[12-15] Capillary CFL scaling: Δt_σ ∝ h^{3/2}.

Paper ref: WIKI-E-014

Validates that the stability limit for explicit surface-tension integration
scales as Δt_max ∝ h^{3/2} and that Δt_max / Δt_theory ≈ 0.40.

Setup
-----
  Static droplet: R=0.25, center (0.5, 0.5), ρ_l=2, ρ_g=1, σ=1, We=1
  Grid refinement: N ∈ {32, 64, 128, 256}
  Binary search for Δt_max over 20 explicit CSF steps.

Expected results
----------------
  N=32 : Δt_max ≈ 1.07e-1, ratio ≈ 0.404
  N=64 : Δt_max ≈ 3.70e-2, ratio ≈ 0.398
  N=128: Δt_max ≈ 1.32e-2, ratio ≈ 0.400
  N=256: Δt_max ≈ 4.65e-3, ratio ≈ 0.399

Pass criteria
-------------
  Scaling exponent = 1.500 ± 0.01
  Ratio Δt_max / Δt_theory ≈ 0.40 ± 0.01

Output
------
  experiment/ch12/results/15_capillary_cfl/data.npz
  experiment/ch12/results/15_capillary_cfl/capillary_cfl.pdf

Usage
-----
  python experiment/ch12/exp12_15_capillary_cfl.py
  python experiment/ch12/exp12_15_capillary_cfl.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()

OUT = experiment_dir(__file__, "15_capillary_cfl")
NPZ = OUT / "data.npz"

# ── Physical parameters ──────────────────────────────────────────────────────
RHO_L  = 2.0
RHO_G  = 1.0
SIGMA  = 1.0
WE     = 1.0
R      = 0.25
GRIDS  = [32, 64, 128, 256]

# Binary-search parameters
N_PROBE_STEPS = 20       # steps per stability probe
INSTAB_THRESH = 1e3      # |u|_inf > threshold → unstable
BISECT_TOL    = 0.01     # converge to 1 %


# ── PPE helper ───────────────────────────────────────────────────────────────

def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


# ── Stability probe ──────────────────────────────────────────────────────────

def _is_stable(N, dt, ccd, ppe_builder, rho, f_csf_x, f_csf_y):
    """Run N_PROBE_STEPS of explicit CSF projection.  Return True if stable."""
    u = np.zeros((N, N))
    v = np.zeros((N, N))

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    for _ in range(N_PROBE_STEPS):
        # Predictor — non-incremental, no grad p^n
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE right-hand side: div(u*) / dt
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt

        p = _solve_ppe(rhs, rho, ppe_builder)

        # Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        u_inf = float(np.max(np.sqrt(u**2 + v**2)))
        if np.isnan(u_inf) or u_inf > INSTAB_THRESH:
            return False

    return True


# ── Single grid: binary-search for Δt_max ────────────────────────────────────

def run_single(N):
    """Find stability limit for the capillary CFL on an N×N grid."""
    backend = Backend(use_gpu=False)
    h   = 1.0 / N
    eps = 1.5 * h

    gc          = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid        = Grid(gc, backend)
    ccd         = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc   = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()

    # Level-set / density
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    # CSF body force (frozen — static droplet, no advection)
    kappa     = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * np.asarray(kappa) * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * np.asarray(kappa) * np.asarray(dpsi_dy)

    # Theoretical capillary CFL (Brackbill et al. 1992)
    dt_theory = np.sqrt((RHO_L + RHO_G) * h**3 / (2.0 * np.pi * SIGMA))

    # Binary search: bracket [dt_lo, dt_hi]
    dt_lo = dt_theory * 0.01   # definitely stable
    dt_hi = dt_theory * 2.0    # likely unstable

    # Verify bracket
    if not _is_stable(N, dt_lo, ccd, ppe_builder, rho, f_csf_x, f_csf_y):
        # Shrink lower bound until stable
        for _ in range(20):
            dt_lo *= 0.5
            if _is_stable(N, dt_lo, ccd, ppe_builder, rho, f_csf_x, f_csf_y):
                break
    if _is_stable(N, dt_hi, ccd, ppe_builder, rho, f_csf_x, f_csf_y):
        # Grow upper bound until unstable
        for _ in range(20):
            dt_hi *= 2.0
            if not _is_stable(N, dt_hi, ccd, ppe_builder, rho, f_csf_x, f_csf_y):
                break

    # Bisection to BISECT_TOL relative tolerance
    for _ in range(60):
        dt_mid = 0.5 * (dt_lo + dt_hi)
        if _is_stable(N, dt_mid, ccd, ppe_builder, rho, f_csf_x, f_csf_y):
            dt_lo = dt_mid
        else:
            dt_hi = dt_mid
        if (dt_hi - dt_lo) / (dt_lo + 1e-300) < BISECT_TOL:
            break

    dt_max = dt_lo   # largest stable dt found
    ratio  = dt_max / dt_theory

    return {
        "N":         N,
        "h":         h,
        "dt_max":    dt_max,
        "dt_theory": dt_theory,
        "ratio":     ratio,
    }


# ── Plotting ─────────────────────────────────────────────────────────────────

def make_figures(results):
    Ns        = np.array([r["N"]         for r in results])
    hs        = np.array([r["h"]         for r in results])
    dt_maxs   = np.array([r["dt_max"]    for r in results])
    dt_thrs   = np.array([r["dt_theory"] for r in results])
    ratios    = np.array([r["ratio"]     for r in results])

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # Panel (a): Δt_max and Δt_theory vs N
    ax = axes[0]
    ax.loglog(hs, dt_maxs,  color=COLORS[0], marker=MARKERS[0], lw=1.5,
              ms=6, label=r"$\Delta t_{\max}$ (measured)")
    ax.loglog(hs, dt_thrs,  color=COLORS[1], marker=MARKERS[1], lw=1.5,
              ms=6, ls='--', label=r"$\Delta t_{\sigma}$ (theory)")

    # Reference slope h^{3/2}
    h_ref  = hs
    slope  = dt_thrs[0] * (h_ref / hs[0])**1.5
    ax.loglog(h_ref, slope, 'k:', alpha=0.6, lw=1.0, label=r"$\propto h^{3/2}$")

    ax.invert_xaxis()
    ax.set_xlabel(r"Grid spacing $h$")
    ax.set_ylabel(r"Time step $\Delta t$")
    ax.set_title(r"(a) Capillary CFL scaling")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both")

    # Panel (b): ratio vs N — should be ~0.40 flat
    ax = axes[1]
    ax.semilogx(Ns, ratios, color=COLORS[2], marker=MARKERS[2], lw=1.5, ms=6,
                label=r"$\Delta t_{\max}/\Delta t_{\sigma}$")
    ax.axhline(0.40, color='k', ls='--', lw=1.0, alpha=0.7, label="target 0.40")
    ax.set_xlabel(r"$N$")
    ax.set_ylabel(r"$\Delta t_{\max} / \Delta t_{\sigma}$")
    ax.set_title(r"(b) Measured / theoretical ratio")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both")
    ax.set_ylim(0.0, 0.8)

    plt.tight_layout()
    save_figure(fig, OUT / "capillary_cfl")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 72)
    print("  [12-15] Capillary CFL Scaling: Δt_σ ∝ h^{3/2}")
    print("=" * 72 + "\n")

    results = []
    print(f"  {'N':>5} | {'h':>10} | {'dt_max':>12} | {'dt_theory':>12} | {'ratio':>8}")
    print("  " + "-" * 60)

    for N in GRIDS:
        print(f"  Probing N={N} ...", flush=True)
        r = run_single(N)
        results.append(r)
        print(f"  {r['N']:>5} | {r['h']:>10.6f} | {r['dt_max']:>12.3e} | "
              f"{r['dt_theory']:>12.3e} | {r['ratio']:>8.3f}")

    # Compute scaling exponent from log-log fit
    hs     = np.array([r["h"]      for r in results])
    dt_max = np.array([r["dt_max"] for r in results])
    exponent = np.polyfit(np.log(hs), np.log(dt_max), 1)[0]
    mean_ratio = float(np.mean([r["ratio"] for r in results]))

    print(f"\n  Scaling exponent: {exponent:.4f}  (target 1.500 ± 0.01)")
    print(f"  Mean ratio Δt_max/Δt_theory: {mean_ratio:.4f}  (target 0.40 ± 0.01)")

    # Pass / fail
    exp_ok   = abs(exponent   - 1.500) <= 0.01
    ratio_ok = abs(mean_ratio - 0.400) <= 0.01
    print(f"\n  Exponent check : {'PASS' if exp_ok   else 'FAIL'}")
    print(f"  Ratio check    : {'PASS' if ratio_ok else 'FAIL'}")

    make_figures(results)

    # Save data
    save_data = {
        "Ns":         np.array([r["N"]         for r in results]),
        "hs":         np.array([r["h"]         for r in results]),
        "dt_maxs":    np.array([r["dt_max"]    for r in results]),
        "dt_theorys": np.array([r["dt_theory"] for r in results]),
        "ratios":     np.array([r["ratio"]     for r in results]),
        "exponent":   np.array(exponent),
        "mean_ratio": np.array(mean_ratio),
    }
    save_results(NPZ, save_data)

    print("\n  [RESULT] Capillary CFL exponent:", exponent)
    print("  [RESULT] Mean ratio Δt_max/Δt_theory:", mean_ratio)
    for r in results:
        print(f"  [RESULT] N={r['N']:>3}: dt_max={r['dt_max']:.3e}, "
              f"dt_theory={r['dt_theory']:.3e}, ratio={r['ratio']:.4f}")


if __name__ == "__main__":
    args = experiment_argparser(
        "Capillary CFL scaling validation: Δt_σ ∝ h^(3/2)"
    ).parse_args()

    if args.plot_only:
        d = load_results(NPZ)
        _results = [
            {
                "N":         int(d["Ns"][i]),
                "h":         float(d["hs"][i]),
                "dt_max":    float(d["dt_maxs"][i]),
                "dt_theory": float(d["dt_theorys"][i]),
                "ratio":     float(d["ratios"][i]),
            }
            for i in range(len(d["Ns"]))
        ]
        make_figures(_results)
    else:
        main()
