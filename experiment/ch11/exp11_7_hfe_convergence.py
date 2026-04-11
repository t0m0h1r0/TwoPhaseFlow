#!/usr/bin/env python3
"""[11-7] Hermite Field Extension (HFE) convergence.

Validates: Ch9d -- Closest-point Hermite extension O(h^6).

Tests:
  (a) 1D: phi=x-0.5, q=1+cos(pi*x), upwind O(h^1) vs Hermite O(h^6+)
  (b) 2D: circular interface R=0.25, q=cos(pi*x)*cos(pi*y), tensor-product HFE

Expected: (a) Upwind O(h^1), Hermite O(h^6+); (b) 2D HFE O(h^3).
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
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def run_1d_hfe_test(Ns=[32, 64, 128, 256]):
    """1D HFE: upwind vs Hermite on phi=x-0.5, q=1+cos(pi*x)."""
    backend = Backend()
    xp = backend.xp
    res_upwind, res_hermite = [], []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        X, Y = grid.meshgrid()

        # SDF: interface at x=0.5, positive on right
        phi = X - 0.5

        # Source field (smooth)
        q = 1.0 + xp.cos(np.pi * X)

        # Exact extension: q_ext = q(x_Gamma) = q(0.5) = 1 + cos(pi*0.5) = 1
        q_ext_exact = xp.ones_like(X)

        # Measurement band: 0.52 <= x <= 0.55
        band = (X >= 0.52) & (X <= 0.55)

        # -- Upwind extension (O(h)) --
        try:
            from twophase.levelset.field_extender import FieldExtender
            ext_up = FieldExtender(backend, grid, ccd, n_ext=5, method="upwind")
            q_ext_up = ext_up.extend(q.copy(), phi)
            err_up = float(xp.max(xp.abs(q_ext_up[band] - q_ext_exact[band])))
        except Exception:
            err_up = float("nan")

        # -- Hermite extension (O(h^6)) --
        try:
            from twophase.levelset.closest_point_extender import ClosestPointExtender
            ext_h = ClosestPointExtender(backend, grid, ccd)
            q_ext_h = ext_h.extend(q.copy(), phi)
            err_h = float(xp.max(xp.abs(q_ext_h[band] - q_ext_exact[band])))
        except Exception:
            err_h = float("nan")

        res_upwind.append({"N": N, "h": h, "Li": err_up})
        res_hermite.append({"N": N, "h": h, "Li": err_h})
        print(f"  N={N:>4}: Upwind={err_up:.3e}, Hermite={err_h:.3e}")

    for res in [res_upwind, res_hermite]:
        for i in range(1, len(res)):
            r0, r1 = res[i-1], res[i]
            if r0["Li"] > 1e-15 and r1["Li"] > 1e-15:
                r1["Li_slope"] = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])

    return res_upwind, res_hermite


def run_2d_hfe_test(Ns=[32, 64, 128, 256]):
    """2D HFE: circular interface, q=cos(pi*x)*cos(pi*y)."""
    backend = Backend()
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        X, Y = grid.meshgrid()

        phi = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
        q = xp.cos(np.pi * X) * xp.cos(np.pi * Y)

        # Exact: q_ext(x) = q(x_Gamma) where x_Gamma = x - phi * n_hat
        r = xp.maximum(xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2), 1e-14)
        nx = (X - 0.5) / r; ny = (Y - 0.5) / r
        xg = X - phi * nx; yg = Y - phi * ny
        q_ext_exact = xp.cos(np.pi * xg) * xp.cos(np.pi * yg)

        # Target band: 0 < phi <= 3h
        band = (phi > 0) & (phi <= 3 * h)

        try:
            from twophase.levelset.closest_point_extender import ClosestPointExtender
            ext = ClosestPointExtender(backend, grid, ccd)
            q_ext = ext.extend(q.copy(), phi)
            err = float(xp.max(xp.abs(q_ext[band] - q_ext_exact[band])))
        except Exception:
            err = float("nan")

        results.append({"N": N, "h": h, "Li": err})
        print(f"  N={N:>4}: Li={err:.3e}")

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r0["Li"] > 1e-15 and r1["Li"] > 1e-15:
            r1["Li_slope"] = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])

    return results


def plot_all(res_up, res_h, res_2d):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    ax = axes[0]
    hs = [r["h"] for r in res_up]
    ax.loglog(hs, [r["Li"] for r in res_up], "s--", label="Upwind", markersize=7)
    ax.loglog(hs, [r["Li"] for r in res_h], "o-", label="Hermite", markersize=7)
    h_ref = np.array([hs[0], hs[-1]])
    for order in [1, 6]:
        ax.loglog(h_ref, res_up[0]["Li"]*(h_ref/h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("(a) 1D HFE"); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    ax = axes[1]
    hs = [r["h"] for r in res_2d]
    ax.loglog(hs, [r["Li"] for r in res_2d], "o-", label=r"2D Hermite $L_\infty$", markersize=7)
    h_ref = np.array([hs[0], hs[-1]])
    for order in [1, 3]:
        ax.loglog(h_ref, res_2d[0]["Li"]*(h_ref/h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("(b) 2D HFE"); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "hfe_convergence")


def main():
    args = experiment_argparser("[11-7] HFE Convergence").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["upwind_1d"], d["hermite_1d"], d["hermite_2d"])
        return

    print("\n--- (a) 1D HFE: upwind vs Hermite ---")
    res_up, res_h = run_1d_hfe_test()
    print("\n--- (b) 2D HFE: circular interface ---")
    res_2d = run_2d_hfe_test()

    save_results(OUT / "data.npz", {
        "upwind_1d": res_up, "hermite_1d": res_h, "hermite_2d": res_2d})
    plot_all(res_up, res_h, res_2d)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
