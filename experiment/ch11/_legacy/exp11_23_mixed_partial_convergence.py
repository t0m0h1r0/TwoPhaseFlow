#!/usr/bin/env python3
"""[11-23] Sequential CCD mixed partial derivative ∂²f/∂x∂y convergence test.

Validates: §6b -- sequential CCD application achieves O(h^6) for mixed partials.

Tests:
  (a) f = sin(2πx)cos(2πy), periodic BC -> full O(h^6)
  (b) f = sin(2πx)cos(2πy), wall BC -> boundary-limited (interior slice)

Both operator orderings (∂x→∂y and ∂y→∂x) are verified to give identical results.

Expected: O(h^6) for periodic; O(h^4–h^6) for wall (interior slice s=2:-2).
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


# -- Test function -------------------------------------------------------------

def _test_func(x, y, xp=np):
    """f = sin(2πx) cos(2πy) and exact mixed partial."""
    k = 2 * np.pi
    f = xp.sin(k * x) * xp.cos(k * y)
    fxy = -(k**2) * xp.cos(k * x) * xp.sin(k * y)
    return f, fxy


# -- Convergence study ---------------------------------------------------------

def run_convergence(bc_type, Ns):
    backend = Backend()
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=1.0)
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type=bc_type)

        X, Y = grid.meshgrid()
        f, fxy_exact = _test_func(X, Y, xp)

        # Order 1: ∂x then ∂y
        d1x, _ = ccd.differentiate(f, axis=0)
        d1xy, _ = ccd.differentiate(d1x, axis=1)

        # Order 2: ∂y then ∂x
        d1y, _ = ccd.differentiate(f, axis=1)
        d1yx, _ = ccd.differentiate(d1y, axis=0)

        s = slice(2, -2) if bc_type == "wall" else slice(None)

        h = 1.0 / N
        err_xy = float(xp.max(xp.abs(d1xy[s, s] - fxy_exact[s, s])))
        err_yx = float(xp.max(xp.abs(d1yx[s, s] - fxy_exact[s, s])))
        err_comm = float(xp.max(xp.abs(d1xy[s, s] - d1yx[s, s])))

        results.append({
            "N": N, "h": h,
            "xy_Li": err_xy,
            "yx_Li": err_yx,
            "comm_Li": err_comm,
        })

    return results


def compute_slopes(results, keys):
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for k in keys:
            if r0[k] > 0 and r1[k] > 0:
                r1[f"{k}_slope"] = np.log(r1[k] / r0[k]) / log_h
            else:
                r1[f"{k}_slope"] = float("nan")


def print_table(results, keys, title):
    print(f"\n{'='*78}\n  {title}\n{'='*78}")
    header = f"{'N':>6} {'h':>10}"
    for k in keys:
        header += f" {k:>12} {'slope':>6}"
    print(header)
    print("-" * len(header))
    for r in results:
        line = f"{r['N']:>6} {r['h']:>10.2e}"
        for k in keys:
            line += f" {r.get(k, 0.0):>12.3e} {r.get(f'{k}_slope', float('nan')):>6.2f}"
        print(line)


# -- Plot ----------------------------------------------------------------------

def plot_all(res_per, res_wall):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # (a) Periodic BC
    ax = axes[0]
    hs = [r["h"] for r in res_per]
    ax.loglog(hs, [r["xy_Li"] for r in res_per],
              marker=MARKERS[0], color=COLORS[0], ls="-",
              label=r"$\partial_y(\partial_x f)$")
    ax.loglog(hs, [r["yx_Li"] for r in res_per],
              marker=MARKERS[1], color=COLORS[1], ls="--",
              label=r"$\partial_x(\partial_y f)$")

    h_ref = np.array([hs[0], hs[-1]])
    for order, ls in [(4, ":"), (6, "-.")]:
        ax.loglog(h_ref,
                  res_per[0]["xy_Li"] * (h_ref / h_ref[0])**order,
                  ls=ls, color="gray", alpha=0.5,
                  label=f"$O(h^{order})$")

    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title(r"(a) Periodic BC — $\partial^2 f/\partial x \partial y$")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # (b) Wall BC
    ax = axes[1]
    hs = [r["h"] for r in res_wall]
    ax.loglog(hs, [r["xy_Li"] for r in res_wall],
              marker=MARKERS[0], color=COLORS[0], ls="-",
              label=r"$\partial_y(\partial_x f)$")
    ax.loglog(hs, [r["yx_Li"] for r in res_wall],
              marker=MARKERS[1], color=COLORS[1], ls="--",
              label=r"$\partial_x(\partial_y f)$")

    h_ref = np.array([hs[0], hs[-1]])
    for order, ls in [(4, ":"), (6, "-.")]:
        ax.loglog(h_ref,
                  res_wall[0]["xy_Li"] * (h_ref / h_ref[0])**order,
                  ls=ls, color="gray", alpha=0.5,
                  label=f"$O(h^{order})$")

    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title(r"(b) Wall BC — $\partial^2 f/\partial x \partial y$")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "mixed_partial_convergence")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser(
        "[11-23] Mixed Partial Convergence"
    ).parse_args()
    Ns = [16, 32, 64, 128, 256]

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        plot_all(data["periodic"], data["wall"])
        return

    err_keys = ["xy_Li", "yx_Li", "comm_Li"]

    res_per = run_convergence("periodic", Ns)
    compute_slopes(res_per, err_keys)
    print_table(res_per, err_keys,
                "Periodic BC: sin(2pi x)cos(2pi y) -- mixed partial")

    res_wall = run_convergence("wall", Ns)
    compute_slopes(res_wall, err_keys)
    print_table(res_wall, err_keys,
                "Wall BC: sin(2pi x)cos(2pi y) -- mixed partial (interior)")

    save_results(OUT / "data.npz", {
        "periodic": res_per, "wall": res_wall,
    })
    plot_all(res_per, res_wall)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
