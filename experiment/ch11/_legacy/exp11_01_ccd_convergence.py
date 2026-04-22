#!/usr/bin/env python3
"""[11-1] CCD/DCCD spatial differentiation convergence test.

Validates: Ch4 -- CCD scheme, O(h^6) spatial accuracy.

Tests:
  (a) f = sin(2*pi*x)*sin(2*pi*y), periodic BC -> full O(h^6)
  (b) f = exp(sin(pi*x))*exp(cos(pi*y)), wall BC -> O(h^5) boundary-limited
  (c) Non-uniform grid (alpha=2.0) -> preserves O(h^6)

Expected: O(h^6) interior; O(h^5) boundary; N=256 reaches machine precision.
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
    convergence_loglog, latex_convergence_table,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


# -- Test functions ----------------------------------------------------------

def _sin_test(x, y, xp):
    k = 2 * np.pi
    f = xp.sin(k * x) * xp.sin(k * y)
    fx = k * xp.cos(k * x) * xp.sin(k * y)
    fy = k * xp.sin(k * x) * xp.cos(k * y)
    fxx = -(k**2) * xp.sin(k * x) * xp.sin(k * y)
    fyy = -(k**2) * xp.sin(k * x) * xp.sin(k * y)
    return f, (fx, fy), (fxx, fyy)


def _exp_test(x, y, xp):
    sx, cx = xp.sin(np.pi * x), xp.cos(np.pi * x)
    sy, cy = xp.sin(np.pi * y), xp.cos(np.pi * y)
    ef = xp.exp(sx) * xp.exp(cy)
    f = ef
    fx = np.pi * cx * ef
    fxx = ef * np.pi**2 * (-sx + cx**2)
    fy = -np.pi * sy * ef
    fyy = ef * np.pi**2 * (-cy + sy**2)
    return f, (fx, fy), (fxx, fyy)


# -- Convergence study -------------------------------------------------------

def run_convergence(test_func, bc_type, Ns):
    backend = Backend()
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=1.0)
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type=bc_type)

        X, Y = grid.meshgrid()
        f_exact, (fx_ex, fy_ex), (fxx_ex, fyy_ex) = test_func(X, Y, xp)

        d1x, d2x = ccd.differentiate(f_exact, axis=0)
        d1y, d2y = ccd.differentiate(f_exact, axis=1)

        s = slice(2, -2) if bc_type == "wall" else slice(None)

        h = 1.0 / N
        results.append({
            "N": N, "h": h,
            "d1x_Li": float(xp.max(xp.abs(d1x[s, s] - fx_ex[s, s]))),
            "d2x_Li": float(xp.max(xp.abs(d2x[s, s] - fxx_ex[s, s]))),
            "d1y_Li": float(xp.max(xp.abs(d1y[s, s] - fy_ex[s, s]))),
            "d2y_Li": float(xp.max(xp.abs(d2y[s, s] - fyy_ex[s, s]))),
        })

    return results


def run_nonuniform(test_func, Ns, alpha=2.0):
    backend = Backend()
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha)
        grid = Grid(gc, backend)

        # Build CCD on uniform grid first → use for O(h⁶) metric computation
        ccd_uniform = CCDSolver(grid, backend, bc_type="wall")
        X0, Y0 = np.meshgrid(
            np.linspace(0, 1, N + 1), np.linspace(0, 1, N + 1), indexing="ij")
        phi_init = np.sqrt((X0 - 0.5)**2 + (Y0 - 0.5)**2) - 0.25
        grid.update_from_levelset(phi_init, eps=0.05, ccd=ccd_uniform)

        # Rebuild CCD on non-uniform grid
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        f_exact, (fx_ex, _), (fxx_ex, _) = test_func(X, Y, xp)

        d1x, d2x = ccd.differentiate(f_exact, axis=0)
        s = slice(2, -2)
        h_eff = float(
            sum(float(backend.to_host(grid.h[ax]).mean()) for ax in range(2)) / 2
        )

        results.append({
            "N": N, "h": h_eff,
            "d1_Li": float(xp.max(xp.abs(d1x[s, s] - fx_ex[s, s]))),
            "d2_Li": float(xp.max(xp.abs(d2x[s, s] - fxx_ex[s, s]))),
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
    print(f"\n{'='*72}\n  {title}\n{'='*72}")
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


# -- Plot --------------------------------------------------------------------

def plot_all(res_per, res_wall, res_nu):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    # (a) Periodic
    ax = axes[0]
    hs = [r["h"] for r in res_per]
    ax.loglog(hs, [r["d1x_Li"] for r in res_per], "o-", label=r"$\partial_x f$")
    ax.loglog(hs, [r["d2x_Li"] for r in res_per], "s--", label=r"$\partial_{xx} f$")
    h_ref = np.array([hs[0], hs[-1]])
    for order in [4, 6]:
        ax.loglog(h_ref, res_per[0]["d1x_Li"] * (h_ref / h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("(a) Periodic BC"); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # (b) Wall BC
    ax = axes[1]
    hs = [r["h"] for r in res_wall]
    ax.loglog(hs, [r["d1x_Li"] for r in res_wall], "o-", label=r"$\partial_x f$")
    ax.loglog(hs, [r["d2x_Li"] for r in res_wall], "s--", label=r"$\partial_{xx} f$")
    h_ref = np.array([hs[0], hs[-1]])
    for order in [4, 5, 6]:
        ax.loglog(h_ref, res_wall[0]["d1x_Li"] * (h_ref / h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("(b) Wall BC"); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # (c) Non-uniform
    ax = axes[2]
    hs = [r["h"] for r in res_nu]
    ax.loglog(hs, [r["d1_Li"] for r in res_nu], "o-", label=r"$\partial_x f$")
    ax.loglog(hs, [r["d2_Li"] for r in res_nu], "s--", label=r"$\partial_{xx} f$")
    h_ref = np.array([hs[0], hs[-1]])
    for order in [5, 6]:
        ax.loglog(h_ref, res_nu[0]["d1_Li"] * (h_ref / h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title(r"(c) Non-uniform ($\alpha=2$)"); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "ccd_convergence")


# -- Main --------------------------------------------------------------------

def main():
    args = experiment_argparser("[11-1] CCD Convergence").parse_args()
    Ns = [16, 32, 64, 128, 256]

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        plot_all(data["periodic"], data["wall"], data["nonuniform"])
        return

    res_per = run_convergence(_sin_test, "periodic", Ns)
    compute_slopes(res_per, ["d1x_Li", "d2x_Li", "d1y_Li", "d2y_Li"])
    print_table(res_per, ["d1x_Li", "d2x_Li"], "Case A: sin -- periodic BC")

    res_wall = run_convergence(_exp_test, "wall", Ns)
    compute_slopes(res_wall, ["d1x_Li", "d2x_Li", "d1y_Li", "d2y_Li"])
    print_table(res_wall, ["d1x_Li", "d2x_Li"], "Case B: exp -- wall BC")

    res_nu = run_nonuniform(_exp_test, Ns, alpha=2.0)
    compute_slopes(res_nu, ["d1_Li", "d2_Li"])
    print_table(res_nu, ["d1_Li", "d2_Li"], "Case C: non-uniform grid")

    save_results(OUT / "data.npz", {
        "periodic": res_per, "wall": res_wall, "nonuniform": res_nu,
    })
    plot_all(res_per, res_wall, res_nu)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
