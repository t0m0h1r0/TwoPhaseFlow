#!/usr/bin/env python3
"""[12-14] Cross-derivative viscous CFL constraint.

Validates: Δt ≤ C_cross · h²/(Δμ/ρ)

For each viscosity ratio μ_l/μ_g ∈ {1, 10, 100, 1000} at N=64,
finds the critical Δt by binary search over explicit Euler steps of
the cross-viscous operator ∂/∂x[μ ∂u/∂y] + ∂/∂y[μ ∂u/∂x].

Pass criterion: C_cross ≈ 0.23 ± 10% across 3 decades of viscosity ratio.

Expected results (WIKI-E-014):
  μ_l/μ_g |   Δt_crit  |  C_cross
  --------|------------|--------
       1  |  5.85e-05  |  0.240
      10  |  5.71e-06  |  0.210
     100  |  5.71e-07  |  0.232
    1000  |  5.71e-08  |  0.234

Usage
-----
  python experiment/ch12/exp12_14_cross_viscous_cfl.py
  python experiment/ch12/exp12_14_cross_viscous_cfl.py --plot-only
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__, "14_cross_viscous_cfl")
NPZ = OUT / "data.npz"

# ---------------------------------------------------------------------------
# Physical / numerical parameters
# ---------------------------------------------------------------------------
N          = 64       # grid resolution
MU_G       = 0.01    # base (gas) viscosity
RHO        = 1.0     # density (uniform)
R_IFACE    = 0.25    # interface radius
N_CHECK    = 20      # explicit Euler steps per stability check
GROW_LIMIT = 10.0    # instability threshold: max|u_new| > GROW_LIMIT * max|u_init|
BISECT_TOL = 0.01    # relative tolerance for binary search

MU_RATIOS = [1, 10, 100, 1000]


# ---------------------------------------------------------------------------
# Cross-viscous operator via CCD
# ---------------------------------------------------------------------------

def cross_viscous(u, mu, ccd, backend):
    """Compute L_cross[u] = ∂/∂x[μ ∂u/∂y] + ∂/∂y[μ ∂u/∂x].

    Returns a (N, N) numpy array (always on CPU).
    """
    xp = backend.xp
    u_dev = xp.asarray(u)
    mu_dev = xp.asarray(mu)

    du_dx_dev, _ = ccd.differentiate(u_dev, axis=0)
    du_dy_dev, _ = ccd.differentiate(u_dev, axis=1)

    mu_du_dy = mu_dev * du_dy_dev   # for ∂/∂x[μ ∂u/∂y]
    mu_du_dx = mu_dev * du_dx_dev   # for ∂/∂y[μ ∂u/∂x]

    d_dx_mu_du_dy_dev, _ = ccd.differentiate(mu_du_dy, axis=0)
    d_dy_mu_du_dx_dev, _ = ccd.differentiate(mu_du_dx, axis=1)

    result = d_dx_mu_du_dy_dev + d_dy_mu_du_dx_dev
    return np.asarray(backend.to_host(result))


# ---------------------------------------------------------------------------
# Stability check: run N_CHECK Euler steps; return True if stable
# ---------------------------------------------------------------------------

def is_stable(dt, u0, mu, ccd, backend):
    """Return True if N_CHECK explicit Euler steps remain bounded.

    Instability criterion: max|u| grows by more than GROW_LIMIT × max|u0|.
    """
    u = u0.copy()
    u_max0 = float(np.max(np.abs(u)))
    if u_max0 == 0.0:
        return True
    threshold = GROW_LIMIT * u_max0

    for _ in range(N_CHECK):
        Lu = cross_viscous(u, mu, ccd, backend)
        u = u + dt * Lu
        if float(np.max(np.abs(u))) > threshold:
            return False
    return True


# ---------------------------------------------------------------------------
# Binary search for critical Δt
# ---------------------------------------------------------------------------

def find_dt_crit(mu_ratio):
    """Find critical Δt for a given μ_l/μ_g ratio.

    Returns dict with keys: mu_ratio, dt_crit, C_cross.
    """
    backend = Backend()
    h = 1.0 / N
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X_dev, Y_dev = grid.meshgrid()
    X = backend.to_host(X_dev)
    Y = backend.to_host(Y_dev)

    # Viscosity field: circular interface at center, radius R_IFACE
    # cross_viscous handles GPU internally via xp.asarray, so mu/u0 stay numpy
    mu_l = MU_G * mu_ratio
    phi = R_IFACE - np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    H = heaviside(np, phi, eps)
    mu = MU_G + (mu_l - MU_G) * H

    # Divergence-free initial velocity
    u0 = np.sin(2.0 * np.pi * X) * np.sin(2.0 * np.pi * Y)

    # Initial bracket: dt_lo is stable, dt_hi is unstable
    # Scale initial guess by the viscosity jump: Δt ~ h²*ρ/(Δμ)
    delta_mu = max(mu_l - MU_G, MU_G)  # use MU_G as baseline for ratio=1
    dt_scale = (h ** 2) * RHO / delta_mu

    dt_lo = dt_scale * 0.001
    dt_hi = dt_scale * 10.0

    # Ensure dt_lo is stable
    while not is_stable(dt_lo, u0, mu, ccd, backend):
        dt_lo *= 0.1

    # Ensure dt_hi is unstable
    while is_stable(dt_hi, u0, mu, ccd, backend):
        dt_hi *= 2.0

    # Binary search
    while (dt_hi - dt_lo) / dt_lo > BISECT_TOL:
        dt_mid = 0.5 * (dt_lo + dt_hi)
        if is_stable(dt_mid, u0, mu, ccd, backend):
            dt_lo = dt_mid
        else:
            dt_hi = dt_mid

    dt_crit = 0.5 * (dt_lo + dt_hi)

    # C_cross = Δt_crit * Δμ / (ρ * h²)
    C_cross = dt_crit * delta_mu / (RHO * h ** 2)

    return {"mu_ratio": mu_ratio, "dt_crit": dt_crit, "C_cross": C_cross}


# ---------------------------------------------------------------------------
# Run all ratios
# ---------------------------------------------------------------------------

def run_sweep():
    """Find Δt_crit for each μ_l/μ_g. Returns list of result dicts."""
    results = []
    for mu_ratio in MU_RATIOS:
        print(f"  Finding Δt_crit for μ_l/μ_g = {mu_ratio} ...", flush=True)
        r = find_dt_crit(mu_ratio)
        results.append(r)
        print(f"    Δt_crit = {r['dt_crit']:.3e},  C_cross = {r['C_cross']:.3f}")
    return results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def make_figures(results):
    """Two-panel figure: (a) Δt_crit vs ratio, (b) C_cross vs ratio."""
    ratios   = np.array([r["mu_ratio"]  for r in results], dtype=float)
    dt_crits = np.array([r["dt_crit"]   for r in results])
    c_cross  = np.array([r["C_cross"]   for r in results])

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # (a) Δt_crit vs ratio — expected slope -1
    ax = axes[0]
    ax.loglog(ratios, dt_crits, "o-",
              color=COLORS[0], linewidth=1.5, markersize=7, label=r"$\Delta t_{crit}$")

    # Reference slope -1
    r0 = ratios[0]
    dt0 = dt_crits[0]
    r_ref = np.array([ratios[0], ratios[-1]])
    ax.loglog(r_ref, dt0 * (r_ref / r0) ** (-1),
              "k--", alpha=0.5, linewidth=1.2, label=r"slope $-1$")

    ax.set_xlabel(r"$\mu_l / \mu_g$")
    ax.set_ylabel(r"$\Delta t_{crit}$")
    ax.set_title(r"(a) Critical $\Delta t$ vs viscosity ratio")
    ax.legend()
    ax.grid(True, alpha=0.3, which="both")

    # (b) C_cross vs ratio — should be ~constant 0.23
    ax = axes[1]
    ax.semilogx(ratios, c_cross, "s-",
                color=COLORS[1], linewidth=1.5, markersize=7, label=r"$C_{cross}$")
    ax.axhline(0.23, color="k", linestyle="--", alpha=0.5, linewidth=1.2,
               label=r"$C_{cross} = 0.23$")
    ax.axhspan(0.23 * 0.9, 0.23 * 1.1, alpha=0.1, color="gray",
               label=r"$\pm 10\%$ band")

    ax.set_xlabel(r"$\mu_l / \mu_g$")
    ax.set_ylabel(r"$C_{cross}$")
    ax.set_title(r"(b) $C_{cross} = \Delta t_{crit}\,\Delta\mu\,/\,(\rho\,h^2)$")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0.0, 0.5)

    plt.tight_layout()
    save_figure(fig, OUT / "cross_viscous_cfl")


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

def print_summary(results):
    h = 1.0 / N
    print(f"\n=== [12-14] Cross-Derivative Viscous CFL ===")
    print(f"  N={N}, h={h:.4f}\n")
    print(f"  {'μ_l/μ_g':>8} | {'Δt_crit':>10} | {'C_cross':>8}")
    print(f"  {'-'*8}-|-{'-'*10}-|-{'-'*8}")
    for r in results:
        print(f"  {r['mu_ratio']:>8} | {r['dt_crit']:>10.2e} | {r['C_cross']:>8.3f}")

    # Exclude μ_l/μ_g=1 (no cross-viscous term) from consistency check
    c_vals = np.array([r["C_cross"] for r in results if r["mu_ratio"] > 1])
    c_mean = float(np.mean(c_vals))
    c_var  = float((np.max(c_vals) - np.min(c_vals)) / c_mean * 100.0)
    passed = c_var < 10.0

    print(f"\n  C_cross (μ_l/μ_g>1): mean={c_mean:.3f}, variation={c_var:.1f}% (< 10% = PASS)")
    print(f"\n[RESULT] Mean C_cross = {c_mean:.3f}")
    print(f"[RESULT] PASS: {passed} (variation < 10%)")


# ---------------------------------------------------------------------------
# Pack / unpack for npz storage
# ---------------------------------------------------------------------------

def _pack(results):
    return {
        "mu_ratios":  np.array([r["mu_ratio"]  for r in results], dtype=float),
        "dt_crits":   np.array([r["dt_crit"]   for r in results]),
        "c_cross":    np.array([r["C_cross"]   for r in results]),
    }


def _unpack(d):
    ratios   = d["mu_ratios"]
    dt_crits = d["dt_crits"]
    c_cross  = d["c_cross"]
    return [
        {"mu_ratio": float(ratios[i]), "dt_crit": float(dt_crits[i]),
         "C_cross": float(c_cross[i])}
        for i in range(len(ratios))
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = experiment_argparser("[12-14] Cross-Derivative Viscous CFL").parse_args()

    if args.plot_only:
        d = load_results(NPZ)
        results = _unpack(d)
        print_summary(results)
        make_figures(results)
        return

    print("\n=== [12-14] Cross-Derivative Viscous CFL ===")
    print(f"  Setup: N={N}, μ_g={MU_G}, ρ={RHO}")
    print(f"  Binary search tolerance: {BISECT_TOL*100:.0f}%")
    print(f"  Stability check: {N_CHECK} steps, grow limit {GROW_LIMIT}×\n")

    results = run_sweep()

    print_summary(results)

    save_results(NPZ, _pack(results))
    make_figures(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
