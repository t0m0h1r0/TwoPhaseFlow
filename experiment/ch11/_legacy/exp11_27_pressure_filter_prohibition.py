#!/usr/bin/env python3
"""[11-27] Pressure filter prohibition: DCCD on pressure destroys div-free.

Validates: Ch8c -- applying dissipative filter to pressure field is forbidden.

Test: Manufactured pressure field + velocity correction step.
  Given exact PPE solution p, compute velocity correction u^{n+1} = u* - dt*grad(p).
  (a) Unfiltered pressure: div(u^{n+1}) approx 0 (CCD discretisation error only)
  (b) DCCD-filtered pressure: div(u^{n+1}) >> 0 (O(eps_d * h^2) error)

Expected: Filtered pressure introduces O(eps_d * h^2) divergence error,
  confirming the §8c prohibition.
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


# ── Manufactured fields ─────────────────────────────────────────────────────

def manufactured_pressure(xp, X, Y):
    """p(x,y) = sin(2*pi*x) * sin(2*pi*y)."""
    return xp.sin(2 * np.pi * X) * xp.sin(2 * np.pi * Y)


def exact_laplacian_p(xp, X, Y):
    """Exact: nabla^2 p = -8*pi^2 * sin(2*pi*x) * sin(2*pi*y)."""
    return -8.0 * np.pi**2 * xp.sin(2 * np.pi * X) * xp.sin(2 * np.pi * Y)


# ── DCCD 3-point filter ────────────────────────────────────────────────────

def dccd_filter_1d(f, eps_d, axis):
    """Apply 3-point dissipative filter along *axis* (periodic BC)."""
    result = f.copy()
    if axis == 0:
        result[1:-1, :] = ((1 - 2 * eps_d) * f[1:-1, :]
                           + eps_d * (f[2:, :] + f[:-2, :]))
        result[0, :] = ((1 - 2 * eps_d) * f[0, :]
                        + eps_d * (f[1, :] + f[-2, :]))
        result[-1, :] = result[0, :]
    else:
        result[:, 1:-1] = ((1 - 2 * eps_d) * f[:, 1:-1]
                           + eps_d * (f[:, 2:] + f[:, :-2]))
        result[:, 0] = ((1 - 2 * eps_d) * f[:, 0]
                        + eps_d * (f[:, 1] + f[:, -2]))
        result[:, -1] = result[:, 0]
    return result


def dccd_filter_2d(f, eps_d):
    """Sequential 3-point filter in x then y (periodic)."""
    return dccd_filter_1d(dccd_filter_1d(f, eps_d, axis=0), eps_d, axis=1)


# ── Core benchmark ──────────────────────────────────────────────────────────

def run_benchmark():
    """Compute Laplacian error due to filtering across grid sizes and eps_d."""
    N_values = [32, 64, 128, 256]
    eps_d_values = [0.05, 0.25]
    dt = 1.0  # dt cancels in the ratio, arbitrary

    results = {"N": N_values, "eps_d": eps_d_values}
    backend = Backend()
    xp = backend.xp

    for eps_d in eps_d_values:
        linf_list = []
        l2_list = []

        for N in N_values:
            gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
            grid = Grid(gc, backend)
            ccd = CCDSolver(grid, backend, bc_type="periodic")
            X, Y = grid.meshgrid()

            # Manufactured pressure
            p = manufactured_pressure(xp, X, Y)

            # DCCD-filtered pressure (pure slice+broadcast ops, xp-native)
            p_filt = dccd_filter_2d(p, eps_d)

            # CCD Laplacians: nabla^2 p and nabla^2 p_filt
            _, d2px = ccd.differentiate(p, axis=0)
            _, d2py = ccd.differentiate(p, axis=1)
            lap_p = d2px + d2py

            _, d2pfx = ccd.differentiate(p_filt, axis=0)
            _, d2pfy = ccd.differentiate(p_filt, axis=1)
            lap_pf = d2pfx + d2pfy

            # Divergence error = (1/dt)(lap_p - lap_pf) in corrected velocity
            # Since dt=1, divergence error = lap_p - lap_pf
            div_err = xp.abs(lap_p - lap_pf)

            # Exclude periodic-image boundary row/col for clean interior norms
            interior = div_err[1:-1, 1:-1]
            linf = float(xp.max(interior))
            l2 = float(xp.sqrt(xp.mean(interior**2)))

            linf_list.append(linf)
            l2_list.append(l2)

            print(f"  eps_d={eps_d:.2f}, N={N:>4}: "
                  f"||div_err||_inf={linf:.4e}, ||div_err||_2={l2:.4e}")

            # Store 2D error field for contour plot (N=64, eps_d=0.25).
            # Host-convert so load_results/plot don't need a GPU to render.
            if N == 64 and eps_d == 0.25:
                results["contour_X"] = backend.to_host(X)
                results["contour_Y"] = backend.to_host(Y)
                results["contour_div_err"] = backend.to_host(div_err)

        results[f"linf_eps{eps_d}"] = linf_list
        results[f"l2_eps{eps_d}"] = l2_list

    # Also measure unfiltered CCD Laplacian accuracy vs exact
    print("\n  Unfiltered CCD Laplacian accuracy (vs exact):")
    linf_ccd = []
    for N in N_values:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()
        p = manufactured_pressure(xp, X, Y)
        lap_exact = exact_laplacian_p(xp, X, Y)

        _, d2px = ccd.differentiate(p, axis=0)
        _, d2py = ccd.differentiate(p, axis=1)
        lap_ccd = d2px + d2py

        err = float(xp.max(xp.abs(lap_ccd[1:-1, 1:-1] - lap_exact[1:-1, 1:-1])))
        linf_ccd.append(err)
        print(f"    N={N:>4}: ||lap_ccd - lap_exact||_inf = {err:.4e}")

    results["linf_ccd_exact"] = linf_ccd

    return results


# ── Plotting ────────────────────────────────────────────────────────────────

def plot_all(results):
    import matplotlib.pyplot as plt

    N_arr = np.array(results["N"])
    h_arr = 1.0 / N_arr

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # ── Panel (a): Convergence of divergence error ──────────────────────
    ax = axes[0]

    # Unfiltered CCD Laplacian error (reference)
    linf_ccd = np.array(results["linf_ccd_exact"])
    ax.loglog(h_arr, linf_ccd, "k--", marker="s", ms=5, lw=1.0,
              label=r"CCD $\nabla^2 p$ error (no filter)")

    # Filtered divergence error
    for ci, eps_d in enumerate(results["eps_d"]):
        linf = np.array(results[f"linf_eps{eps_d}"])
        ax.loglog(h_arr, linf, color=COLORS[ci], marker=MARKERS[ci],
                  ms=5, lw=1.2,
                  label=rf"$\varepsilon_d = {eps_d}$")

    # Reference slopes
    h_ref = np.array([h_arr[0], h_arr[-1]])
    scale2 = results[f"linf_eps0.25"][0] / h_arr[0]**2
    ax.loglog(h_ref, scale2 * h_ref**2, ":", color="gray", lw=0.8,
              label=r"$O(h^2)$")
    scale6 = linf_ccd[0] / h_arr[0]**6
    ax.loglog(h_ref, scale6 * h_ref**6, "-.", color="gray", lw=0.8,
              label=r"$O(h^6)$")

    ax.set_xlabel(r"$h$")
    ax.set_ylabel(r"$\| \nabla^2 p - \nabla^2 \tilde{p} \|_\infty$")
    ax.set_title(r"(a) Divergence error from pressure filtering")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which="both")

    # ── Panel (b): 2D contour of error at N=64, eps_d=0.25 ─────────────
    ax = axes[1]
    X = results["contour_X"]
    Y = results["contour_Y"]
    err2d = results["contour_div_err"]

    levels = np.linspace(0, float(np.max(err2d)), 20)
    cs = ax.contourf(X, Y, err2d, levels=levels, cmap="hot_r")
    fig.colorbar(cs, ax=ax, shrink=0.85,
                 label=r"$|\nabla^2 p - \nabla^2 \tilde{p}|$")
    ax.set_xlabel("$x$")
    ax.set_ylabel("$y$")
    ax.set_title(r"(b) Error structure, $N=64$, $\varepsilon_d=0.25$")
    ax.set_aspect("equal")

    fig.tight_layout()
    save_figure(fig, OUT / "pressure_filter_prohibition")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser(
        "[11-27] Pressure filter prohibition"
    ).parse_args()

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        plot_all(data)
        return

    print("\n=== [11-27] Pressure filter prohibition ===")
    print("Demonstrating that DCCD filter on pressure destroys div-free.\n")

    results = run_benchmark()
    save_results(OUT / "data.npz", results)
    plot_all(results)

    # ── Summary ─────────────────────────────────────────────────────────
    N_arr = np.array(results["N"])
    h_arr = 1.0 / N_arr
    print("\n--- Convergence rates ---")
    for eps_d in results["eps_d"]:
        linf = np.array(results[f"linf_eps{eps_d}"])
        rates = np.log(linf[:-1] / linf[1:]) / np.log(h_arr[:-1] / h_arr[1:])
        print(f"  eps_d={eps_d:.2f}: rates = {[f'{r:.2f}' for r in rates]}")

    linf_ccd = np.array(results["linf_ccd_exact"])
    rates_ccd = (np.log(linf_ccd[:-1] / linf_ccd[1:])
                 / np.log(h_arr[:-1] / h_arr[1:]))
    print(f"  CCD exact:  rates = {[f'{r:.2f}' for r in rates_ccd]}")

    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
