#!/usr/bin/env python3
"""[12-14] Cross-derivative viscous CFL constraint verification.

Validates: Ch5 eq.218-219 -- stability limit for explicit cross-viscous term.

Test: 2D viscous flow with sharp viscosity jump (mu_l/mu_g >> 1).
  Increase dt until instability to measure critical CFL.

Expected: dt_crit ~ C * h^2 / (Delta_mu / rho).
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
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)

# -- Physical parameters ------------------------------------------------------
N_GRID = 64
RHO = 1.0           # constant density
MU_G = 1.0           # gas-side viscosity (reference)
R_INTERFACE = 0.25   # circle radius for interface
N_STEPS = 200        # explicit steps per trial
N_BISECT = 40        # binary-search iterations


# -- Explicit viscous step ----------------------------------------------------

def explicit_viscous_step(u, mu_eff, ccd, dt):
    """One forward-Euler step for u_t = d/dy(mu * du/dy).

    Isolates the cross-derivative-like explicit viscous term:
    d/dy(mu * du/dy) = mu * d2u/dy2 + (dmu/dy) * (du/dy).

    Parameters
    ----------
    u      : 2-D field
    mu_eff : mu / rho field (kinematic-viscosity-like)
    ccd    : CCDSolver
    dt     : time step
    """
    d1y, d2y = ccd.differentiate(u, axis=1)
    d1mu_y, _ = ccd.differentiate(mu_eff, axis=1)
    rhs = mu_eff * d2y + d1mu_y * d1y
    return u + dt * rhs


# -- Critical dt finder -------------------------------------------------------

def find_critical_dt(N, mu_l, mu_g, rho, n_steps=N_STEPS):
    """Binary-search for the largest stable dt of explicit cross-viscous term.

    Returns
    -------
    dt_crit : float
        Largest dt for which N_STEPS explicit steps remain bounded.
    """
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X, Y = grid.meshgrid()
    h = 1.0 / N
    eps = 1.5 * h

    # Interface: circle at centre, radius R_INTERFACE
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R_INTERFACE
    H = np.asarray(heaviside(np, phi, eps))
    mu = mu_l * H + mu_g * (1.0 - H)
    mu_eff = mu / rho

    # Initial condition: smooth periodic field
    u0 = np.sin(2.0 * np.pi * X) * np.sin(2.0 * np.pi * Y)

    # Upper bound: for uniform mu, explicit diffusion CFL is dt < h^2/(2*nu).
    # With variable mu, use the maximum kinematic viscosity.
    nu_max = float(np.max(mu_eff))
    dt_high = 0.5 * h**2 / max(nu_max, 1e-14)
    dt_low = 0.0

    def _is_stable(dt):
        u = u0.copy()
        for _ in range(n_steps):
            u = explicit_viscous_step(u, mu_eff, ccd, dt)
            if np.any(np.isnan(u)) or np.max(np.abs(u)) > 1e6:
                return False
        return True

    for _ in range(N_BISECT):
        dt_mid = 0.5 * (dt_low + dt_high)
        if _is_stable(dt_mid):
            dt_low = dt_mid
        else:
            dt_high = dt_mid

    return dt_low


# -- Sweep over viscosity ratios -----------------------------------------------

def run_sweep(N=N_GRID):
    """Measure critical dt for several mu_l/mu_g ratios."""
    ratios = [1.0, 10.0, 100.0, 1000.0]
    h = 1.0 / N
    results = []

    for ratio in ratios:
        mu_l = MU_G * ratio
        delta_mu = mu_l - MU_G
        dt_crit = find_critical_dt(N, mu_l, MU_G, RHO)

        # Normalised CFL constant: C_cross = dt_crit * delta_mu / (rho * h^2)
        if delta_mu > 0:
            C_cross = dt_crit * delta_mu / (RHO * h**2)
        else:
            C_cross = dt_crit * mu_l / (RHO * h**2)  # uniform case

        results.append({
            "ratio": ratio,
            "mu_l": mu_l,
            "mu_g": MU_G,
            "delta_mu": delta_mu if delta_mu > 0 else mu_l,
            "dt_crit": dt_crit,
            "C_cross": C_cross,
            "h": h,
        })
        print(f"  mu_l/mu_g={ratio:>7.0f}  dt_crit={dt_crit:.4e}  "
              f"C_cross={C_cross:.4f}")

    return results


# -- Plotting ------------------------------------------------------------------

def plot_results(results):
    """Two-panel figure: (a) dt_crit vs Delta_mu, (b) C_cross vs ratio."""
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    ratios = np.array([r["ratio"] for r in results])
    dt_crits = np.array([r["dt_crit"] for r in results])
    delta_mus = np.array([r["delta_mu"] for r in results])
    C_crosses = np.array([r["C_cross"] for r in results])
    h = results[0]["h"]

    # -- (a) Log-log: dt_crit vs Delta_mu/rho ------------------------------------
    ax = axes[0]
    nu_eff = delta_mus / RHO
    ax.loglog(nu_eff, dt_crits, "o-", color=COLORS[0], markersize=7,
              label=r"$\Delta t_{\mathrm{crit}}$ (measured)")

    # Reference line: h^2 / (2 * Delta_mu / rho)
    nu_ref = np.logspace(np.log10(nu_eff.min() * 0.5),
                         np.log10(nu_eff.max() * 2.0), 50)
    ax.loglog(nu_ref, 0.5 * h**2 / nu_ref, "--", color="gray", alpha=0.6,
              label=r"$h^2 / (2\,\Delta\mu/\rho)$")

    ax.set_xlabel(r"$\Delta\mu / \rho$")
    ax.set_ylabel(r"$\Delta t_{\mathrm{crit}}$")
    ax.set_title(r"(a) Critical $\Delta t$ vs $\Delta\mu/\rho$")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, which="both")

    # -- (b) C_cross vs mu ratio (should be flat) --------------------------------
    ax = axes[1]
    ax.semilogx(ratios, C_crosses, "s-", color=COLORS[1], markersize=7,
                label=r"$C_{\mathrm{cross}}$")

    # Horizontal reference at the mean (excluding ratio=1 if it differs much)
    mask_high = ratios >= 10
    if np.any(mask_high):
        C_mean = float(np.mean(C_crosses[mask_high]))
    else:
        C_mean = float(np.mean(C_crosses))
    ax.axhline(C_mean, color="gray", ls="--", alpha=0.5,
               label=f"mean $= {C_mean:.3f}$")

    ax.set_xlabel(r"$\mu_l / \mu_g$")
    ax.set_ylabel(r"$C_{\mathrm{cross}} = \Delta t_{\mathrm{crit}}"
                  r"\,\Delta\mu / (\rho\, h^2)$")
    ax.set_title(r"(b) Normalised CFL constant")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "cross_viscous_cfl.pdf")


# -- Main ----------------------------------------------------------------------

def main():
    print("\n" + "=" * 70)
    print("  [12-14] Cross-derivative viscous CFL constraint")
    print("=" * 70)
    print(f"\n  N={N_GRID}, rho={RHO}, mu_g={MU_G}, "
          f"n_steps={N_STEPS}, n_bisect={N_BISECT}\n")

    print("  Viscosity ratio sweep:")
    print(f"  {'mu_l/mu_g':>10} | {'dt_crit':>12} | {'C_cross':>10}")
    print("  " + "-" * 40)

    results = run_sweep()

    for r in results:
        print(f"  {r['ratio']:>10.0f} | {r['dt_crit']:>12.4e} | "
              f"{r['C_cross']:>10.4f}")

    # Verify near-constant C_cross for high ratios
    high_ratio = [r for r in results if r["ratio"] >= 10]
    if len(high_ratio) >= 2:
        Cs = [r["C_cross"] for r in high_ratio]
        spread = (max(Cs) - min(Cs)) / np.mean(Cs)
        print(f"\n  C_cross spread (ratio>=10): {spread:.2%}")
        if spread < 0.3:
            print("  PASS: C_cross is approximately constant")
        else:
            print("  WARN: C_cross varies more than 30%")

    # Save
    save_results(OUT / "data.npz", {
        "ratio": np.array([r["ratio"] for r in results]),
        "mu_l": np.array([r["mu_l"] for r in results]),
        "delta_mu": np.array([r["delta_mu"] for r in results]),
        "dt_crit": np.array([r["dt_crit"] for r in results]),
        "C_cross": np.array([r["C_cross"] for r in results]),
        "h": results[0]["h"],
        "N": N_GRID,
        "rho": RHO,
    })

    plot_results(results)
    print(f"\n  Results saved to {OUT}")


if __name__ == "__main__":
    args = experiment_argparser("[12-14] Cross-viscous CFL").parse_args()

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        results = []
        for i in range(len(d["ratio"])):
            results.append({
                "ratio": float(d["ratio"][i]),
                "mu_l": float(d["mu_l"][i]),
                "mu_g": MU_G,
                "delta_mu": float(d["delta_mu"][i]),
                "dt_crit": float(d["dt_crit"][i]),
                "C_cross": float(d["C_cross"][i]),
                "h": float(d["h"]),
            })
        plot_results(results)
    else:
        main()
