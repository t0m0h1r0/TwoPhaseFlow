#!/usr/bin/env python3
"""[11-30] Cross-derivative viscous term temporal accuracy.

Validates: Ch5 -- explicit cross-viscous term O(Δt) at high mu_l/mu_g.

Tests:
  (a) Uniform viscosity (mu_ratio=1): explicit cross-viscous gives O(Δt^2)
      because the overall AB2+CN scheme is O(Δt^2) and there is no
      O(mu_ratio * Δt) penalty at uniform viscosity.
  (b) High viscosity ratio (mu_ratio=100): O(Δt^1) degradation due to
      explicit treatment of cross-derivative terms.  When mu jumps by
      O(mu_ratio) across the interface, the truncation error of the
      explicit cross-term ∂/∂x[μ ∂u/∂y] is O(mu_ratio * Δt), which
      dominates and degrades the overall scheme to first-order in time.

Physical setup:
  PDE: u_t = ∂/∂x[μ(x) ∂u/∂y] + ∂/∂y[μ(x) ∂u/∂x]   (cross terms only)

  μ(x) = μ_base * (1 + (mu_ratio - 1) * H_ε(x - 0.5))
       where H_ε is a smoothed Heaviside with ε = 2h.

  MMS exact solution: u_exact(x,y,t) = exp(-λ(t)) * sin(2π x) * sin(2π y)
  with λ chosen to absorb the MMS forcing; instead we drive the equation
  with a computed source f(x,y,t) = u_t - L_cross[u_exact] and integrate
  forward, comparing with the reference at t = T_final.

Numerical method:
  Forward Euler (explicit) for the cross-viscous operator:
      u^{n+1} = u^n + Δt * (L_cross[u^n] + f^n)
  This isolates the temporal truncation error of the explicit treatment.

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
T_FINAL  = 0.05        # short enough that exact solution stays O(1)
MU_BASE  = 0.01        # base viscosity
DECAY    = 1.0         # temporal decay rate λ; u_exact = exp(-λ t)*sin*sin

MU_RATIOS = [1, 10, 100]
K_LIST    = [10, 20, 40, 80, 160, 320]

# reference is computed with a much finer dt
K_REF     = 3200


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
# MMS source term
# ---------------------------------------------------------------------------

def mms_source(X, Y, t, mu):
    """f(x,y,t) = u_t - L_cross[u_exact].

    u_t = -λ * exp(-λ t) * sin(2π x) * sin(2π y)

    For the exact cross-viscous term we differentiate analytically:
      u = E(t) * sin(kx) * sin(ky),  k = 2π, E(t) = exp(-λ t)
      ∂u/∂y  = E(t) * k * sin(kx) * cos(ky)
      ∂u/∂x  = E(t) * k * cos(kx) * sin(ky)

      ∂/∂x[μ ∂u/∂y] = E(t) * k * [∂μ/∂x * sin(kx) * cos(ky)
                                    + μ * k * cos(kx) * cos(ky)]
      ∂/∂y[μ ∂u/∂x] = E(t) * k * [μ * k * cos(kx) * (-sin(ky))
                                    ... wait, mu = mu(x) only, so ∂μ/∂y = 0]
      ∂/∂y[μ ∂u/∂x] = μ * E(t) * k * cos(kx) * k * cos(ky)
                     = μ * E(t) * k^2 * cos(kx) * cos(ky)

    So L_cross = E(t) * k * [dμ/dx * sin(kx)*cos(ky)
                              + μ * k * cos(kx)*cos(ky)
                              + μ * k * cos(kx)*cos(ky)]
               = E(t) * k * [dmu_dx * sin(kx)*cos(ky)
                              + 2 * μ * k * cos(kx)*cos(ky)]

    Source = u_t - L_cross
    """
    k = 2.0 * np.pi
    E = np.exp(-DECAY * t)
    ut = -DECAY * E * np.sin(k * X) * np.sin(k * Y)

    # ∂μ/∂x via finite central difference (same grid, no CCD needed for source)
    h = X[0, 1] - X[0, 0] if X.ndim == 2 else X[1] - X[0]
    dmu_dx = np.gradient(mu, h, axis=1) if mu.ndim == 2 else np.gradient(mu, h)

    L_cross = E * k * (dmu_dx * np.sin(k * X) * np.cos(k * Y)
                       + 2.0 * mu * k * np.cos(k * X) * np.cos(k * Y))

    return ut - L_cross


# ---------------------------------------------------------------------------
# Time integration (Forward Euler with MMS source)
# ---------------------------------------------------------------------------

def integrate_forward_euler(u0, mu, X, Y, ccd, backend, dt, K):
    """Advance u from t=0 to t=K*dt with Forward Euler + MMS source."""
    u = u0.copy()
    for step in range(K):
        t_n = step * dt
        Lc = cross_viscous(u, mu, ccd, backend)
        f_n = mms_source(X, Y, t_n, mu)
        u = u + dt * (Lc + f_n)
    return u


# ---------------------------------------------------------------------------
# Reference solution (very fine dt, same integrator)
# ---------------------------------------------------------------------------

def reference_solution(mu, X, Y, ccd, backend):
    """Compute reference by Forward Euler with K_REF steps."""
    u0 = u_exact(X, Y, 0.0)
    dt_ref = T_FINAL / K_REF
    return integrate_forward_euler(u0, mu, X, Y, ccd, backend, dt_ref, K_REF)


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

    u0 = u_exact(X, Y, 0.0)

    print(f"\n  mu_ratio={mu_ratio:>4}  computing reference (K={K_REF}) ...")
    u_ref = reference_solution(mu, X, Y, ccd, backend)

    results = []
    for K in K_LIST:
        dt = T_FINAL / K
        u_num = integrate_forward_euler(u0, mu, X, Y, ccd, backend, dt, K)
        err = float(np.sqrt(np.mean((u_num - u_ref) ** 2)))
        results.append({"K": K, "dt": dt, "L2": err})
        print(f"    K={K:>4}, dt={dt:.4e}: L2={err:.4e}")

    # compute slopes between consecutive refinements
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0["L2"] > 1e-15 and r1["L2"] > 1e-15:
            r1["slope"] = np.log(r1["L2"] / r0["L2"]) / np.log(r1["dt"] / r0["dt"])
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
    """Log-log plot: Δt vs L2 error for each mu_ratio with reference slopes."""
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
    ax.set_ylabel(r"$L_2$ error (vs fine-dt reference)")
    ax.set_title(r"Explicit cross-viscous: $\partial_x[\mu\,\partial_y u]$ temporal accuracy")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "cross_viscous_temporal")


# ---------------------------------------------------------------------------
# Print summary table
# ---------------------------------------------------------------------------

def print_summary(all_results):
    """Print final slopes for each mu_ratio."""
    print("\n=== Summary: observed temporal convergence slopes ===")
    print(f"  {'mu_ratio':>10}  {'K_fine':>6}  {'slope (avg last 3)':>20}")
    for mu_ratio in MU_RATIOS:
        results = all_results[mu_ratio]
        slopes = [r.get("slope", float("nan")) for r in results[1:]]
        # average of last three reliable slopes
        valid = [s for s in slopes[-3:] if not np.isnan(s)]
        avg_slope = float(np.mean(valid)) if valid else float("nan")
        print(f"  {mu_ratio:>10}  {K_LIST[-1]:>6}  {avg_slope:>20.3f}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = experiment_argparser("[11-30] Cross-Viscous Temporal").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["results"])
        return

    print("\n=== [11-30] Cross-derivative viscous term temporal accuracy ===")
    print(f"  Grid: {N_GRID}x{N_GRID}, T_final={T_FINAL}, K_ref={K_REF}")
    print(f"  mu_ratios: {MU_RATIOS}")

    all_results = run_convergence()

    print_summary(all_results)

    save_results(OUT / "data.npz", {"results": all_results})
    plot_all(all_results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
