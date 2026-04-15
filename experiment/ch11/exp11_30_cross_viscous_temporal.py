#!/usr/bin/env python3
"""[11-30] Cross-derivative viscous term temporal accuracy.

Validates: Ch5 -- explicit cross-viscous term O(Δt) at high mu_l/mu_g.

Tests:
  (a) Uniform viscosity (mu_ratio=1): explicit cross-viscous gives O(Δt^2)
      since the local truncation error is e_LTE = (Δt²/2)u_tt + O(Δt³)
      and all terms are smooth → classic Forward Euler behaviour.
  (b) High viscosity ratio (mu_ratio=100): O(Δt^1) degradation due to
      explicit treatment of cross-derivative terms.  When mu jumps by
      O(mu_ratio) across the interface, the spatial discretisation error
      from CCD differentiating μ·∂u/∂x across the interface produces an
      O(h^1-2) spatial residual that couples into the local temporal error.

Method: Single-step Forward Euler local truncation error (LTE) measurement.
  For each Δt:
    u_num = u(0) + Δt * (L_cross_CCD[u(0)] + f(0))
    u_ref = u_exact(Δt)
    err = ‖u_num − u_ref‖₂

  This avoids multi-step instability at large μ while directly measuring
  the truncation error order.

Physical setup:
  PDE: u_t = ∂/∂x[μ(x) ∂u/∂y] + ∂/∂y[μ(x) ∂u/∂x] + f(x,y,t)

  μ(x) = μ_base * (1 + (mu_ratio - 1) * H_ε(x - 0.5))

  MMS exact solution: u_exact(x,y,t) = exp(-λt) * sin(2πx) * sin(2πy)
  Source f chosen so that the PDE is satisfied exactly.

Expected: slope ≈ 2 at mu_ratio=1; slope ≈ 1 at mu_ratio=100.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)

# ---------------------------------------------------------------------------
# Physical / numerical parameters
# ---------------------------------------------------------------------------
N_GRID   = 64          # fixed spatial resolution (periodic BC)
MU_BASE  = 0.01        # base viscosity
DECAY    = 1.0         # temporal decay rate λ

MU_RATIOS = [1, 10, 100]
DT_LIST   = [1e-2, 5e-3, 2e-3, 1e-3, 5e-4, 2e-4, 1e-4]


# ---------------------------------------------------------------------------
# Exact solution (MMS)
# ---------------------------------------------------------------------------

def u_exact(X, Y, t):
    """u(x,y,t) = exp(-λ t) * sin(2π x) * sin(2π y)."""
    k = 2.0 * np.pi
    return np.exp(-DECAY * t) * np.sin(k * X) * np.sin(k * Y)


def smoothed_mu(X, mu_ratio, eps):
    """μ(x) = MU_BASE * (1 + (mu_ratio - 1) * H_ε(x - 0.5)).

    H_ε is the smooth Heaviside: H_ε(s) = 0.5 * (1 + tanh(s / ε)).
    eps = 2 * grid spacing so the interface occupies ~2 cells.
    """
    H = 0.5 * (1.0 + np.tanh((X - 0.5) / eps))
    return MU_BASE * (1.0 + (mu_ratio - 1.0) * H)


# ---------------------------------------------------------------------------
# Cross-viscous operator via CCD
# ---------------------------------------------------------------------------

def cross_viscous(u, mu, ccd, backend):
    """Compute L_cross[u] = ∂/∂x[μ ∂u/∂y] + ∂/∂y[μ ∂u/∂x].

    Uses CCD to obtain ∂u/∂x and ∂u/∂y, then multiplies by μ,
    and differentiates the result with CCD again.

    Returns a (N,N) numpy array (always on CPU).
    """
    xp = backend.xp
    u_dev = xp.asarray(u)
    mu_dev = xp.asarray(mu)

    # first derivatives of u
    du_dx_dev, _ = ccd.differentiate(u_dev, axis=0)
    du_dy_dev, _ = ccd.differentiate(u_dev, axis=1)

    # weight by mu
    mu_du_dy = mu_dev * du_dy_dev   # for ∂/∂x[μ ∂u/∂y]
    mu_du_dx = mu_dev * du_dx_dev   # for ∂/∂y[μ ∂u/∂x]

    # outer differentiation
    d_dx_mu_du_dy_dev, _ = ccd.differentiate(mu_du_dy, axis=0)
    d_dy_mu_du_dx_dev, _ = ccd.differentiate(mu_du_dx, axis=1)

    result = d_dx_mu_du_dy_dev + d_dy_mu_du_dx_dev
    return np.asarray(backend.to_host(result))


# ---------------------------------------------------------------------------
# MMS source term (analytical)
# ---------------------------------------------------------------------------

def mms_source(X, Y, t, mu, dmu_dx):
    """f(x,y,t) = u_t - L_cross[u_exact].

    Analytical cross-viscous:
      u = E(t) sin(kx) sin(ky), E(t) = exp(-λt), k = 2π
      L_cross = E k [dμ/dx sin(kx) cos(ky) + 2μk cos(kx) cos(ky)]

    Source = u_t - L_cross  (so that u_t = L_cross + f)
    """
    k = 2.0 * np.pi
    E = np.exp(-DECAY * t)
    ut = -DECAY * E * np.sin(k * X) * np.sin(k * Y)

    L_cross = E * k * (dmu_dx * np.sin(k * X) * np.cos(k * Y)
                       + 2.0 * mu * k * np.cos(k * X) * np.cos(k * Y))

    return ut - L_cross


# ---------------------------------------------------------------------------
# Single-step LTE measurement
# ---------------------------------------------------------------------------

def single_step_lte(dt, u0, mu, dmu_dx, X, Y, ccd, backend):
    """One Forward Euler step → local truncation error vs exact."""
    Lc0 = cross_viscous(u0, mu, ccd, backend)
    f0 = mms_source(X, Y, 0.0, mu, dmu_dx)
    u_num = u0 + dt * (Lc0 + f0)
    u_ref = u_exact(X, Y, dt)
    return float(np.sqrt(np.mean((u_num - u_ref) ** 2)))


# ---------------------------------------------------------------------------
# Convergence sweep for one mu_ratio
# ---------------------------------------------------------------------------

def convergence_sweep(mu_ratio):
    """Run dt-convergence for a given mu_ratio. Returns list of dicts."""
    backend = Backend()
    gc = GridConfig(ndim=2, N=(N_GRID, N_GRID), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X_dev, Y_dev = grid.meshgrid()
    X = np.asarray(backend.to_host(X_dev))
    Y = np.asarray(backend.to_host(Y_dev))

    h = 1.0 / N_GRID
    eps = 2.0 * h
    mu = smoothed_mu(X, mu_ratio, eps)

    # pre-compute analytical dmu/dx (axis=0 for ij-indexed meshgrid)
    dmu_dx = np.gradient(mu, h, axis=0)

    u0 = u_exact(X, Y, 0.0)

    print(f"\n  mu_ratio={mu_ratio:>4}")

    results = []
    for dt in DT_LIST:
        err = single_step_lte(dt, u0, mu, dmu_dx, X, Y, ccd, backend)
        results.append({"dt": dt, "L2": err})
        print(f"    dt={dt:.4e}: L2={err:.4e}")

    # compute slopes between consecutive refinements
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0["L2"] > 1e-15 and r1["L2"] > 1e-15:
            r1["slope"] = np.log(r0["L2"] / r1["L2"]) / np.log(r0["dt"] / r1["dt"])
        else:
            r1["slope"] = float("nan")

    return results


# ---------------------------------------------------------------------------
# Full convergence study
# ---------------------------------------------------------------------------

def run_convergence():
    """Run sweep for all mu_ratios. Returns dict keyed by mu_ratio."""
    all_results = {}
    for mu_ratio in MU_RATIOS:
        all_results[mu_ratio] = convergence_sweep(mu_ratio)
    return all_results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_all(all_results):
    """Log-log plot: Δt vs LTE for each mu_ratio with reference slopes."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=FIGSIZE_2COL)

    for idx, mu_ratio in enumerate(MU_RATIOS):
        results = all_results[mu_ratio]
        dt_arr  = [r["dt"]  for r in results]
        err_arr = [r["L2"]  for r in results]
        label = fr"$\mu_l/\mu_g = {mu_ratio}$"
        ax.loglog(dt_arr, err_arr,
                  marker=MARKERS[idx % len(MARKERS)],
                  color=COLORS[idx % len(COLORS)],
                  markersize=7, linewidth=1.5,
                  label=label)

    # reference lines anchored at the coarsest (largest Δt) point of mu_ratio=1
    base = all_results[MU_RATIOS[0]]
    dt0  = base[0]["dt"]
    err0 = base[0]["L2"] if base[0]["L2"] > 1e-15 else 1e-3
    dt_range = np.array([dt0, base[-1]["dt"]])

    for order, ls, label_order in [(1, ":", r"$O(\Delta t)$"),
                                   (2, "--", r"$O(\Delta t^2)$")]:
        ax.loglog(dt_range,
                  err0 * (dt_range / dt0) ** order,
                  ls, color="gray", alpha=0.6, linewidth=1.2,
                  label=label_order)

    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel(r"$L_2$ local truncation error")
    ax.set_title(r"[11-30] Explicit cross-viscous LTE: $\partial_x[\mu\,\partial_y u]$")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "cross_viscous_temporal")


# ---------------------------------------------------------------------------
# Print summary table
# ---------------------------------------------------------------------------

def print_summary(all_results):
    """Print final slopes for each mu_ratio."""
    print("\n=== Summary: observed temporal convergence slopes (LTE) ===")
    print(f"  {'mu_ratio':>10}  {'slope (avg last 3)':>20}")
    for mu_ratio in MU_RATIOS:
        results = all_results[mu_ratio]
        slopes = [r.get("slope", float("nan")) for r in results[1:]]
        valid = [s for s in slopes[-3:] if not np.isnan(s)]
        avg_slope = float(np.mean(valid)) if valid else float("nan")
        print(f"  {mu_ratio:>10}  {avg_slope:>20.3f}")

    # PASS/FAIL
    for mu_ratio in MU_RATIOS:
        results = all_results[mu_ratio]
        slopes = [r.get("slope", float("nan")) for r in results[1:]]
        valid = [s for s in slopes[-3:] if not np.isnan(s)]
        avg = float(np.mean(valid)) if valid else float("nan")
        if mu_ratio == 1:
            ok = avg >= 1.5
            print(f"\n[RESULT] mu_ratio={mu_ratio}: slope={avg:.2f}  PASS={ok} (expect ≈2)")
        else:
            ok = 0.5 < avg < 2.5
            print(f"[RESULT] mu_ratio={mu_ratio}: slope={avg:.2f}  PASS={ok} (expect ≈1-2)")
    print()


# ---------------------------------------------------------------------------
# Pack/unpack for npz storage
# ---------------------------------------------------------------------------

_KEYS = ("dt", "L2")


def _pack(all_results):
    """Convert {mu_ratio: [dicts]} → flat dict for npz."""
    out = {}
    for mu_ratio, results in all_results.items():
        for k in _KEYS:
            out[f"mu{mu_ratio}_{k}"] = np.array([float(r[k]) for r in results])
        slopes = [float(r.get("slope", np.nan)) for r in results]
        out[f"mu{mu_ratio}_slope"] = np.array(slopes)
    return out


def _unpack(d):
    """Reverse of _pack."""
    all_results = {}
    for mu_ratio in MU_RATIOS:
        dt_arr = d[f"mu{mu_ratio}_dt"]
        l2_arr = d[f"mu{mu_ratio}_L2"]
        sl_arr = d[f"mu{mu_ratio}_slope"]
        results = []
        for i in range(len(dt_arr)):
            r = {"dt": float(dt_arr[i]), "L2": float(l2_arr[i])}
            if not np.isnan(sl_arr[i]):
                r["slope"] = float(sl_arr[i])
            results.append(r)
        all_results[mu_ratio] = results
    return all_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = experiment_argparser("[11-30] Cross-Viscous Temporal").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        all_results = _unpack(d)
        plot_all(all_results)
        return

    print("\n=== [11-30] Cross-derivative viscous term temporal accuracy ===")
    print(f"  Grid: {N_GRID}x{N_GRID}, single-step LTE method")
    print(f"  mu_ratios: {MU_RATIOS}")

    all_results = run_convergence()

    print_summary(all_results)

    save_results(OUT / "data.npz", _pack(all_results))
    plot_all(all_results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
