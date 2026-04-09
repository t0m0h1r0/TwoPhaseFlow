#!/usr/bin/env python3
"""[12-13] Interface vs bulk temporal accuracy degradation.

Validates: Ch5 -- O(dt^2) in bulk, O(dt) near interface due to variable mu.

Test: 2D diffusion with variable viscosity (step-like mu profile).
  Measure temporal convergence separately in interface and bulk regions.

Expected: Bulk: O(dt^2); Interface region (|phi|<3*eps): O(dt^1).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# -- Physical parameters -------------------------------------------------------
MU_L = 1.0          # liquid viscosity
MU_G = 0.01         # gas viscosity (ratio 100)
N_GRID = 64          # fixed spatial resolution
T_FINAL = 0.1
K_LIST = [20, 40, 80, 160, 320]   # number of time steps


# -- Variable viscosity field ---------------------------------------------------

def build_mu(X, eps):
    """Smoothed viscosity: mu(x) = mu_l*H_eps(phi) + mu_g*(1-H_eps(phi)).

    phi = x - 0.5  =>  vertical interface at x = 0.5.
    """
    phi = X - 0.5
    # Smoothed Heaviside
    H = np.where(
        phi < -eps, 0.0,
        np.where(phi > eps, 1.0,
                 0.5 * (1.0 + phi / eps + np.sin(np.pi * phi / eps) / np.pi))
    )
    return MU_L * H + MU_G * (1.0 - H)


# -- Exact solution -------------------------------------------------------------

def exact_solution(X, Y, t, mu):
    """u(x,y,t) = exp(-4*pi^2*mu(x)*t) * sin(2*pi*y).

    Since mu depends only on x and IC varies only in y, each x-line
    diffuses independently: u_t = mu(x) * u_yy.
    """
    return np.exp(-4.0 * np.pi**2 * mu * t) * np.sin(2.0 * np.pi * Y)


# -- CN time stepper with variable viscosity ------------------------------------

def cn_variable_mu_step(u, mu, ccd, dt, n_iter=30):
    """One Crank-Nicolson step for u_t = mu(x) * u_yy via fixed-point iteration."""
    _, d2y_n = ccd.differentiate(u, axis=1)
    d2y_n = np.asarray(d2y_n)
    rhs_n = mu * d2y_n
    rhs_half = u + 0.5 * dt * rhs_n

    u_new = u.copy()
    for _ in range(n_iter):
        _, d2y_new = ccd.differentiate(u_new, axis=1)
        d2y_new = np.asarray(d2y_new)
        rhs_new = mu * d2y_new
        u_new = rhs_half + 0.5 * dt * rhs_new
    return u_new


# -- Test A: temporal convergence -----------------------------------------------

def temporal_convergence():
    """Run CN time stepping for various K, measure error in bulk and interface."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N_GRID, N_GRID), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    X, Y = grid.meshgrid()

    h = 1.0 / N_GRID
    eps = 3.0 * h
    mu = build_mu(X, eps)

    # Masks for bulk and interface regions
    phi = X - 0.5
    mask_interface = np.abs(phi) < 3.0 * eps
    mask_bulk = np.abs(phi) > 6.0 * eps

    u0 = exact_solution(X, Y, 0.0, mu)
    u_ref = exact_solution(X, Y, T_FINAL, mu)

    results = []
    error_fields = {}

    for K in K_LIST:
        dt = T_FINAL / K
        u = u0.copy()
        for _ in range(K):
            u = cn_variable_mu_step(u, mu, ccd, dt)

        err = np.abs(u - u_ref)
        err_bulk = float(np.max(err[mask_bulk])) if np.any(mask_bulk) else 0.0
        err_intf = float(np.max(err[mask_interface])) if np.any(mask_interface) else 0.0

        results.append({
            "K": K, "dt": dt,
            "Linf_bulk": err_bulk,
            "Linf_interface": err_intf,
        })
        # Save error field for the middle resolution (K=80) for panel (b)
        if K == 80:
            error_fields["err_K80"] = err

        print(f"  K={K:>4}, dt={dt:.4e}: "
              f"bulk={err_bulk:.4e}, interface={err_intf:.4e}")

    # Compute convergence slopes
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        log_dt = np.log(r1["dt"] / r0["dt"])
        if r0["Linf_bulk"] > 1e-15 and r1["Linf_bulk"] > 1e-15:
            r1["slope_bulk"] = np.log(r1["Linf_bulk"] / r0["Linf_bulk"]) / log_dt
        if r0["Linf_interface"] > 1e-15 and r1["Linf_interface"] > 1e-15:
            r1["slope_intf"] = np.log(r1["Linf_interface"] / r0["Linf_interface"]) / log_dt

    return results, error_fields, X, Y


# -- Plotting -------------------------------------------------------------------

def plot_all(results, error_fields, X, Y):
    """2-panel figure: (a) convergence, (b) spatial error map."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # (a) Log-log temporal convergence
    ax = axes[0]
    dt_arr = np.array([r["dt"] for r in results])
    err_bulk = np.array([r["Linf_bulk"] for r in results])
    err_intf = np.array([r["Linf_interface"] for r in results])

    ax.loglog(dt_arr, err_bulk, "o-", color=COLORS[0], markersize=6,
              label=r"Bulk ($|x-0.5|>6\varepsilon$)")
    ax.loglog(dt_arr, err_intf, "s-", color=COLORS[1], markersize=6,
              label=r"Interface ($|x-0.5|<3\varepsilon$)")

    # Reference slopes
    d_ref = np.array([dt_arr[0], dt_arr[-1]])
    ax.loglog(d_ref, err_bulk[0] * (d_ref / d_ref[0])**2,
              "--", color="gray", alpha=0.5, label=r"$O(\Delta t^2)$")
    ax.loglog(d_ref, err_intf[0] * (d_ref / d_ref[0])**1,
              ":", color="gray", alpha=0.5, label=r"$O(\Delta t)$")

    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("(a) Temporal convergence by region")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # (b) Spatial error map at K=80
    ax = axes[1]
    err_field = error_fields.get("err_K80")
    if err_field is not None:
        vmax = float(np.max(err_field))
        if vmax < 1e-20:
            vmax = 1.0
        im = ax.pcolormesh(np.asarray(X), np.asarray(Y), err_field,
                           shading="auto", cmap="hot_r", vmin=0, vmax=vmax)
        cb = fig.colorbar(im, ax=ax, shrink=0.85)
        cb.set_label(r"$|u - u_{\mathrm{exact}}|$")
        # Mark interface region
        h = 1.0 / N_GRID
        eps = 3.0 * h
        ax.axvline(0.5 - 3.0 * eps, color="cyan", ls="--", lw=0.8, alpha=0.7)
        ax.axvline(0.5 + 3.0 * eps, color="cyan", ls="--", lw=0.8, alpha=0.7,
                   label=r"$|x-0.5|=3\varepsilon$")
        ax.axvline(0.5 - 6.0 * eps, color="lime", ls=":", lw=0.8, alpha=0.7)
        ax.axvline(0.5 + 6.0 * eps, color="lime", ls=":", lw=0.8, alpha=0.7,
                   label=r"$|x-0.5|=6\varepsilon$")
        ax.legend(fontsize=7, loc="lower right")
    else:
        ax.text(0.5, 0.5, "No data for K=80", ha="center", va="center",
                transform=ax.transAxes)

    ax.set_xlabel("$x$")
    ax.set_ylabel("$y$")
    ax.set_title(r"(b) Error field ($K=80$, $N=64$)")
    ax.set_aspect("equal")

    fig.tight_layout()
    save_figure(fig, OUT / "interface_temporal_accuracy")


# -- Main -----------------------------------------------------------------------

def main():
    args = experiment_argparser(
        "[12-13] Interface vs bulk temporal accuracy"
    ).parse_args()

    if args.plot_only:
        d = load_results(NPZ)
        plot_all(d["results"], d, d.get("X"), d.get("Y"))
        return

    print("\n=== [12-13] Interface vs bulk temporal accuracy ===")
    results, error_fields, X, Y = temporal_convergence()

    # Print convergence table
    print(f"\n{'K':>6} {'dt':>12} {'Linf_bulk':>12} {'slope_b':>8} "
          f"{'Linf_intf':>12} {'slope_i':>8}")
    print("-" * 66)
    for r in results:
        sb = r.get("slope_bulk", float("nan"))
        si = r.get("slope_intf", float("nan"))
        print(f"{r['K']:>6} {r['dt']:>12.4e} {r['Linf_bulk']:>12.4e} {sb:>8.2f} "
              f"{r['Linf_interface']:>12.4e} {si:>8.2f}")

    # Save
    save_data = {"results": results, "X": np.asarray(X), "Y": np.asarray(Y)}
    for k, v in error_fields.items():
        save_data[k] = v
    save_results(NPZ, save_data)

    plot_all(results, error_fields, X, Y)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
