#!/usr/bin/env python3
"""[11-26] WENO5 vs DCCD CLS advection comparison.

Validates: §7 — WENO5 over-diffuses smooth CLS profiles compared to DCCD.

Test:
  1D linear advection u_t + c*u_x = 0, c=1, periodic BC, T=1 (one period).
  CLS tanh profile: psi(x) = 0.5*(tanh((x-0.25)/(2*eps)) - tanh((x-0.75)/(2*eps)))
  with eps = 0.02, 0.04.
  N = 128, 256, CFL = 0.4, RK4.
  Schemes: WENO5, CCD (no filter), DCCD (eps_d=0.05).

Expected:
  WENO5 — over-diffusion, interface width grows, L2 error higher for smooth CLS.
  CCD   — lowest error but may show oscillations for sharp profiles.
  DCCD  — slightly more error than CCD but stable, interface width well-preserved.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy.optimize import curve_fit
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import LevelSetAdvection
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__)


# ── Initial condition ────────────────────────────────────────────────────────

def cls_profile(x, eps):
    """CLS tanh profile: two back-to-back interfaces at x=0.25 and x=0.75."""
    return 0.5 * (np.tanh((x - 0.25) / (2 * eps))
                  - np.tanh((x - 0.75) / (2 * eps)))


# ── Advection routines ──────────────────────────────────────────────────────

def advect_ccd(q0, ccd, dt, n_steps, eps_d=0.0):
    """Advect with CCD (or DCCD if eps_d > 0) using RK4."""
    q = q0.copy()

    def rhs(q_in):
        d1, _ = ccd.differentiate(q_in, axis=0)
        flux = -1.0 * d1  # c = 1
        if eps_d > 0:
            f = flux.copy()
            f[1:-1, :] = flux[1:-1, :] + eps_d * (
                flux[2:, :] - 2 * flux[1:-1, :] + flux[:-2, :])
            f[0, :] = flux[0, :] + eps_d * (
                flux[1, :] - 2 * flux[0, :] + flux[-1, :])
            f[-1, :] = f[0, :]
            return f
        return flux

    for _ in range(n_steps):
        k1 = rhs(q)
        k2 = rhs(q + 0.5 * dt * k1)
        k3 = rhs(q + 0.5 * dt * k2)
        k4 = rhs(q + dt * k3)
        q = q + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

    return q


def advect_weno5(q0, grid, backend, dt, n_steps):
    """Advect with WENO5 (LevelSetAdvection._rhs) + RK4."""
    weno = LevelSetAdvection(backend, grid, bc="periodic")
    q = q0.copy()
    c = 1.0
    vel = [c * np.ones_like(q), np.zeros_like(q)]

    for _ in range(n_steps):
        def rhs(q_in):
            return weno._rhs(q_in, vel)
        k1 = rhs(q)
        k2 = rhs(q + 0.5 * dt * k1)
        k3 = rhs(q + 0.5 * dt * k2)
        k4 = rhs(q + dt * k3)
        q = q + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

    return q


# ── Interface width measurement ─────────────────────────────────────────────

def measure_interface_width(x, profile, eps0):
    """Fit the profile to a CLS tanh template and return the effective eps.

    Uses nonlinear least-squares to fit:
        psi(x) = 0.5*(tanh((x - x1)/(2*eps_eff)) - tanh((x - x2)/(2*eps_eff)))
    and returns eps_eff.
    """
    def model(x_in, eps_eff, x1, x2):
        return 0.5 * (np.tanh((x_in - x1) / (2 * eps_eff))
                      - np.tanh((x_in - x2) / (2 * eps_eff)))

    try:
        popt, _ = curve_fit(
            model, x, profile,
            p0=[eps0, 0.25, 0.75],
            bounds=([1e-4, 0.1, 0.5], [0.2, 0.4, 0.9]),
            maxfev=5000,
        )
        return popt[0]  # eps_eff
    except RuntimeError:
        return np.nan


# ── Benchmark runner ─────────────────────────────────────────────────────────

def run_benchmark():
    eps_values = [0.02, 0.04]
    N_values = [128, 256]
    cfl = 0.4
    T = 1.0

    results = {}

    for N in N_values:
        h = 1.0 / N
        dt = cfl * h
        n_steps = int(T / dt)
        dt = T / n_steps  # adjust for exact periodicity

        backend = Backend(use_gpu=False)
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()
        x = X[:, 0]

        for eps in eps_values:
            key = f"N{N}_eps{eps}"
            q0_1d = cls_profile(x, eps)
            q0 = np.tile(q0_1d[:, None], (1, N + 1))
            q_exact = q0.copy()

            print(f"\n  Running N={N}, eps={eps} ...")

            # WENO5
            q_weno = advect_weno5(q0.copy(), grid, backend, dt, n_steps)
            # CCD (no filter)
            q_ccd = advect_ccd(q0.copy(), ccd, dt, n_steps, eps_d=0.0)
            # DCCD (eps_d = 0.05)
            q_dccd = advect_ccd(q0.copy(), ccd, dt, n_steps, eps_d=0.05)

            mid = N // 2
            exact_1d = q_exact[:, mid]
            weno_1d = q_weno[:, mid]
            ccd_1d = q_ccd[:, mid]
            dccd_1d = q_dccd[:, mid]

            # L2 errors
            L2_weno = float(np.sqrt(np.mean((weno_1d - exact_1d) ** 2)))
            L2_ccd = float(np.sqrt(np.mean((ccd_1d - exact_1d) ** 2)))
            L2_dccd = float(np.sqrt(np.mean((dccd_1d - exact_1d) ** 2)))

            # Interface widths
            eps_weno = measure_interface_width(x, weno_1d, eps)
            eps_ccd = measure_interface_width(x, ccd_1d, eps)
            eps_dccd = measure_interface_width(x, dccd_1d, eps)

            results[key] = {
                "x": x,
                "exact": exact_1d,
                "weno5": weno_1d,
                "ccd": ccd_1d,
                "dccd": dccd_1d,
                "L2_weno5": L2_weno,
                "L2_ccd": L2_ccd,
                "L2_dccd": L2_dccd,
                "eps0": eps,
                "eps_weno5": float(eps_weno),
                "eps_ccd": float(eps_ccd),
                "eps_dccd": float(eps_dccd),
                "N": N,
            }

            r = results[key]
            print(f"    L2:  WENO5={L2_weno:.3e}, CCD={L2_ccd:.3e}, "
                  f"DCCD={L2_dccd:.3e}")
            print(f"    eps: initial={eps:.4f}, "
                  f"WENO5={eps_weno:.4f}, CCD={eps_ccd:.4f}, "
                  f"DCCD={eps_dccd:.4f}")

    return results


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot_all(results):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_WIDE)

    # ── Panel (a): Profile comparison (eps=0.02, N=256) ──────────────────
    ax = axes[0]
    key = "N256_eps0.02"
    r = results[key]
    x = r["x"]

    ax.plot(x, r["exact"], "k--", lw=1.2, label="Exact")
    ax.plot(x, r["weno5"], color=COLORS[0], lw=0.9, label="WENO5")
    ax.plot(x, r["ccd"], color=COLORS[1], lw=0.9, label="CCD")
    ax.plot(x, r["dccd"], color=COLORS[2], lw=0.9, label="DCCD")
    ax.set_xlabel("$x$")
    ax.set_ylabel(r"$\psi$")
    ax.set_title(r"(a) Profile after $T=1$, $\varepsilon=0.02$, $N=256$")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # ── Panel (b): Interface width comparison ────────────────────────────
    ax = axes[1]

    eps_values = [0.02, 0.04]
    N_plot = 256

    eps0_list = []
    eps_weno_list = []
    eps_ccd_list = []
    eps_dccd_list = []

    for eps in eps_values:
        key = f"N{N_plot}_eps{eps}"
        r = results[key]
        eps0_list.append(r["eps0"])
        eps_weno_list.append(r["eps_weno5"])
        eps_ccd_list.append(r["eps_ccd"])
        eps_dccd_list.append(r["eps_dccd"])

    x_pos = np.arange(len(eps_values))
    width = 0.2

    ax.bar(x_pos - width, eps0_list, width, color="gray",
           label=r"Initial $\varepsilon$", alpha=0.6)
    ax.bar(x_pos, eps_weno_list, width, color=COLORS[0],
           label="WENO5")
    ax.bar(x_pos + width, eps_ccd_list, width, color=COLORS[1],
           label="CCD")
    ax.bar(x_pos + 2 * width, eps_dccd_list, width, color=COLORS[2],
           label="DCCD")

    ax.set_xticks(x_pos + width / 2)
    ax.set_xticklabels([rf"$\varepsilon_0={e}$" for e in eps_values])
    ax.set_ylabel(r"Effective $\varepsilon$")
    ax.set_title(r"(b) Interface width after $T=1$, $N=256$")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    save_figure(fig, OUT / "weno5_vs_dccd")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser("[11-26] WENO5 vs DCCD CLS advection").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d)
        return

    results = run_benchmark()
    save_results(OUT / "data.npz", results)
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
