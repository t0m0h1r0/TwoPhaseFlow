#!/usr/bin/env python3
"""[12-13] Interface temporal accuracy degradation.

Validates: CN achieves O(Δt²) in the bulk but degrades to O(Δt^~1.7) near a
viscosity discontinuity when μ_l/μ_g = 100.

Setup
-----
  PDE:  u_t = ∂/∂y[μ(x) · ∂u/∂y]  (1-D heat equation, x-varying viscosity)
  μ(x) = MU_BASE * (1 + (mu_ratio - 1) * H_ε(x - 0.5)),  ε = 2h,  mu_ratio = 100
  Domain [0,1]²,  periodic BC,  N = 64,  T = 0.1

MMS exact solution
------------------
  u(x,y,t) = exp(-λt) · sin(2πx) · sin(2πy),   λ = DECAY
  Source:  f = u · (-λ + μ(x) · k²),  k = 2π

Pass criteria
-------------
  Bulk convergence rate   ≥ 1.9  (target O(Δt²))
  Interface convergence rate ≥ 1.7  (degraded near discontinuity)

Output
------
  experiment/ch12/results/13_interface_temporal_accuracy/data.npz
  experiment/ch12/results/13_interface_temporal_accuracy/interface_temporal_accuracy.pdf
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy.sparse.linalg import gmres, LinearOperator
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
NPZ = OUT / "data.npz"

# -- Physical parameters -------------------------------------------------------
MU_BASE   = 0.01       # gas-phase viscosity
MU_RATIO  = 100        # μ_l / μ_g
DECAY     = 1.0        # λ: exponential decay rate of exact solution
N_GRID    = 64         # spatial resolution (fixed)
T_FINAL   = 0.1        # integration horizon
K_LIST    = [10, 20, 40, 80, 160, 320]

# Pass thresholds
BULK_PASS  = 1.9
INTF_PASS  = 1.7


# -- Viscosity field -----------------------------------------------------------

def smooth_heaviside(s, eps):
    """H_ε(s) = 0.5 * (1 + tanh(s / ε)), element-wise."""
    return 0.5 * (1.0 + np.tanh(s / eps))


def build_mu(X, h):
    """μ(x) = MU_BASE * (1 + (MU_RATIO - 1) * H_ε(x - 0.5)), ε = 2h."""
    eps = 2.0 * h
    return MU_BASE * (1.0 + (MU_RATIO - 1.0) * smooth_heaviside(X - 0.5, eps))


# -- MMS exact solution --------------------------------------------------------

def exact_u(X, Y, t):
    """u(x,y,t) = exp(-λt) · sin(2πx) · sin(2πy)."""
    k = 2.0 * np.pi
    return np.exp(-DECAY * t) * np.sin(k * X) * np.sin(k * Y)


def mms_source(X, Y, t, mu):
    """f = u · (-λ + μ(x) · k²).

    Derivation:
      u_t            = -λ · u
      ∂/∂y[μ ∂u/∂y] = -μ(x) · k² · u    (second y-derivative of sin(ky) gives -k²)
      f = u_t - A[u] = -λu + μk²u = u(-λ + μk²)
    """
    k = 2.0 * np.pi
    u = exact_u(X, Y, t)
    return u * (-DECAY + mu * k**2)


# -- Viscous operator (CCD-based) ----------------------------------------------

def viscous_operator(u, mu, ccd, backend):
    """Compute ∂/∂y[μ(x) · ∂u/∂y] using CCD.

    Steps:
      1. du_dy = CCD differentiate u along y (axis=1)
      2. mu_du_dy = μ(x) · du_dy
      3. result = CCD differentiate mu_du_dy along y (axis=1)
    """
    xp = backend.xp
    u_dev = xp.asarray(u)
    mu_dev = xp.asarray(mu)
    du_dy_dev, _ = ccd.differentiate(u_dev, axis=1)
    mu_du_dy = mu_dev * du_dy_dev
    result_dev, _ = ccd.differentiate(mu_du_dy, axis=1)
    return np.asarray(backend.to_host(result_dev))


# -- CN time step via GMRES ----------------------------------------------------

def cn_step(u, mu, ccd, backend, dt, X, Y, t_n):
    """One Crank-Nicolson step for u_t = A[u] + f, where A[u] = ∂/∂y[μ ∂u/∂y].

    Scheme:
      rhs = u^n + 0.5*dt*(A[u^n] + f(t_n + dt/2))
      Solve: (I - 0.5*dt*A) u^{n+1} = rhs   via GMRES
    """
    shape = u.shape
    n = u.size

    # Explicit part of RHS
    Au_n = viscous_operator(u, mu, ccd, backend)
    f_mid = mms_source(X, Y, t_n + 0.5 * dt, mu)
    rhs_2d = u + 0.5 * dt * (Au_n + f_mid)

    def matvec(v_flat):
        v = v_flat.reshape(shape)
        Av = viscous_operator(v, mu, ccd, backend)
        return (v - 0.5 * dt * Av).flatten()

    A_op = LinearOperator((n, n), matvec=matvec)
    u_new_flat, info = gmres(
        A_op, rhs_2d.flatten(), x0=u.flatten(),
        atol=1e-14, restart=100, maxiter=500,
    )
    return u_new_flat.reshape(shape)


# -- Temporal convergence sweep ------------------------------------------------

def temporal_convergence(X, Y, mu, h):
    """Sweep over K_LIST, return list of dicts with bulk/interface L2 errors."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N_GRID, N_GRID), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    eps = 2.0 * h
    # Region masks
    dist = np.abs(X - 0.5)
    bulk_mask  = dist > 6.0 * eps   # far from interface
    intf_mask  = dist < 3.0 * eps   # near interface

    results = []
    for K in K_LIST:
        dt = T_FINAL / K
        u = exact_u(X, Y, 0.0).copy()
        t = 0.0
        for _ in range(K):
            u = cn_step(u, mu, ccd, backend, dt, X, Y, t)
            t += dt

        u_ref = exact_u(X, Y, T_FINAL)
        err = u - u_ref

        bulk_l2 = float(np.sqrt(np.mean(err[bulk_mask]**2))) if np.any(bulk_mask) else float("nan")
        intf_l2 = float(np.sqrt(np.mean(err[intf_mask]**2))) if np.any(intf_mask) else float("nan")

        results.append({
            "K": K,
            "dt": dt,
            "bulk_l2": bulk_l2,
            "intf_l2": intf_l2,
        })
        print(f"  K={K:>4}, dt={dt:.2e}: bulk L2={bulk_l2:.3e}, intf L2={intf_l2:.3e}")

    return results


# -- Convergence rate helper ---------------------------------------------------

def log_rate(e1, e0, dt1, dt0):
    """Slope in log-log space."""
    if e1 <= 0.0 or e0 <= 0.0:
        return float("nan")
    return np.log(e1 / e0) / np.log(dt1 / dt0)


# -- Plotting ------------------------------------------------------------------

def plot_all(results, h):
    import matplotlib.pyplot as plt

    dts       = [r["dt"]      for r in results]
    bulk_errs = [r["bulk_l2"] for r in results]
    intf_errs = [r["intf_l2"] for r in results]

    # Compute rates between consecutive points
    bulk_rates = [float("nan")] + [
        log_rate(bulk_errs[i], bulk_errs[i - 1], dts[i], dts[i - 1])
        for i in range(1, len(results))
    ]
    intf_rates = [float("nan")] + [
        log_rate(intf_errs[i], intf_errs[i - 1], dts[i], dts[i - 1])
        for i in range(1, len(results))
    ]

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # (a) L2 error vs Δt
    ax = axes[0]
    dt_arr = np.array(dts)
    ax.loglog(dt_arr, bulk_errs, "o-", color=COLORS[0], markersize=7,
              label="Bulk")
    ax.loglog(dt_arr, intf_errs, "s--", color=COLORS[1], markersize=7,
              label="Interface")

    # Reference slopes anchored at largest dt
    d_ref = np.array([dt_arr[0], dt_arr[-1]])
    ax.loglog(d_ref, np.array(bulk_errs)[0] * (d_ref / dt_arr[0])**1,
              ":", color="gray", alpha=0.5, label=r"$O(\Delta t)$")
    ax.loglog(d_ref, np.array(bulk_errs)[0] * (d_ref / dt_arr[0])**2,
              "--", color="gray", alpha=0.5, label=r"$O(\Delta t^2)$")

    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel(r"$L_2$ error")
    ax.set_title("(a) Temporal convergence")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # (b) Convergence rate vs Δt
    ax = axes[1]
    dt_mid = [0.5 * (dts[i] + dts[i - 1]) for i in range(1, len(results))]
    ax.semilogx(dt_mid, bulk_rates[1:], "o-", color=COLORS[0], markersize=7,
                label="Bulk")
    ax.semilogx(dt_mid, intf_rates[1:], "s--", color=COLORS[1], markersize=7,
                label="Interface")
    ax.axhline(2.0, color="gray", linestyle=":", alpha=0.5, label=r"$p=2$")
    ax.axhline(1.7, color="gray", linestyle="--", alpha=0.5, label=r"$p=1.7$")
    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel("Convergence rate")
    ax.set_title("(b) Local convergence rate")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "interface_temporal_accuracy")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser("[12-13] Interface Temporal Accuracy").parse_args()

    if args.plot_only:
        data = load_results(NPZ)
        results = data["results"]
        h = float(data["h"])
        plot_all(results, h)
        return

    print("\n=== [12-13] Interface Temporal Accuracy Degradation ===")
    print(f"  μ_l/μ_g = {MU_RATIO}, N={N_GRID}, T={T_FINAL}\n")

    # Build grid quantities (CPU-only; backend not needed here)
    h = 1.0 / N_GRID
    x1d = np.linspace(0.0, 1.0 - h, N_GRID)   # cell centres, periodic
    y1d = np.linspace(0.0, 1.0 - h, N_GRID)
    X, Y = np.meshgrid(x1d, y1d, indexing="ij")   # shape (N, N), x varies along axis 0
    mu = build_mu(X, h)

    results = temporal_convergence(X, Y, mu, h)

    # Print convergence rates using the K=20->40 pair (index 1->2)
    r0, r1 = results[1], results[2]
    bulk_rate = log_rate(r1["bulk_l2"], r0["bulk_l2"], r1["dt"], r0["dt"])
    intf_rate = log_rate(r1["intf_l2"], r0["intf_l2"], r1["dt"], r0["dt"])

    print(f"\n  Convergence rates (K={r0['K']}\u2192{r1['K']}):")
    print(f"    Bulk:      O(\u0394t^{bulk_rate:.2f})")
    print(f"    Interface: O(\u0394t^{intf_rate:.2f})")

    passed = bulk_rate >= BULK_PASS and intf_rate >= INTF_PASS
    print(f"\n[RESULT] Bulk rate = {bulk_rate:.2f}, Interface rate = {intf_rate:.2f}")
    print(f"[RESULT] PASS: {passed}")

    save_results(NPZ, {"results": results, "h": h})
    plot_all(results, h)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
