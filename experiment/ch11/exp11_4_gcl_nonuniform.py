#!/usr/bin/env python3
"""[11-4] Non-uniform grid derivatives and Geometric Conservation Law (GCL).

Validates: Ch5 -- Interface-fitted non-uniform grids preserve CCD accuracy.

Tests:
  (a) Convergence: f=sin(pi*x), alpha=1 (uniform) vs alpha=2 (non-uniform)
  (b) GCL: f=1 (constant), measure spurious derivative |df/dx|_inf

Expected:
  (a) O(h^6) on both uniform and non-uniform grids
  (b) GCL residual <= 10^3 * eps_mach ~ 2.2e-13
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


def convergence_test(Ns, alpha):
    """Convergence of CCD on non-uniform grid with given alpha."""
    backend = Backend()
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha)
        grid = Grid(gc, backend)

        if alpha > 1.0:
            # Build CCD on uniform grid first → use for O(h⁶) metric computation
            ccd_uniform = CCDSolver(grid, backend, bc_type="wall")
            # phi_init built on host; update_from_levelset internally to_host()s it.
            X0, Y0 = np.meshgrid(
                np.linspace(0, 1, N + 1), np.linspace(0, 1, N + 1), indexing="ij")
            phi_init = np.sqrt((X0 - 0.5)**2 + (Y0 - 0.5)**2) - 0.25
            grid.update_from_levelset(phi_init, eps=0.05, ccd=ccd_uniform)

        # Rebuild CCD on (now possibly non-uniform) grid
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        f = xp.sin(np.pi * X) * xp.ones_like(Y)
        fx_exact = np.pi * xp.cos(np.pi * X) * xp.ones_like(Y)
        fxx_exact = -(np.pi**2) * xp.sin(np.pi * X) * xp.ones_like(Y)

        d1, d2 = ccd.differentiate(f, axis=0)
        s = slice(2, -2)
        h_eff = float(np.mean(grid.h[0])) if hasattr(grid, 'h') else 1.0 / N

        results.append({
            "N": N, "h": h_eff, "alpha": alpha,
            "d1_Li": float(xp.max(xp.abs(d1[s, s] - fx_exact[s, s]))),
            "d2_Li": float(xp.max(xp.abs(d2[s, s] - fxx_exact[s, s]))),
        })

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for k in ["d1_Li", "d2_Li"]:
            if r0[k] > 0 and r1[k] > 0:
                r1[f"{k}_slope"] = np.log(r1[k] / r0[k]) / log_h
    return results


def gcl_test(Ns, alpha=2.0):
    """GCL: differentiate f=1 on non-uniform grid, measure spurious derivative."""
    backend = Backend()
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha)
        grid = Grid(gc, backend)

        ccd_uniform = CCDSolver(grid, backend, bc_type="wall")
        # phi_init built on host; update_from_levelset internally to_host()s it.
        X0, Y0 = np.meshgrid(
            np.linspace(0, 1, N + 1), np.linspace(0, 1, N + 1), indexing="ij")
        phi_init = np.sqrt((X0 - 0.5)**2 + (Y0 - 0.5)**2) - 0.25
        grid.update_from_levelset(phi_init, eps=0.05, ccd=ccd_uniform)

        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        f_const = xp.ones_like(X)
        d1x, _ = ccd.differentiate(f_const, axis=0)
        d1y, _ = ccd.differentiate(f_const, axis=1)

        gcl_x = float(xp.max(xp.abs(d1x)))
        gcl_y = float(xp.max(xp.abs(d1y)))
        eps_mach = np.finfo(float).eps
        threshold = 1e3 * eps_mach

        results.append({
            "N": N, "gcl_x": gcl_x, "gcl_y": gcl_y,
            "threshold": threshold,
            "pass": gcl_x < threshold and gcl_y < threshold,
        })
        status = "PASS" if results[-1]["pass"] else "FAIL"
        print(f"  N={N:>4}: |d(1)/dx|_inf={gcl_x:.2e}, |d(1)/dy|_inf={gcl_y:.2e}, "
              f"threshold={threshold:.2e} [{status}]")

    return results


def print_convergence(res_uni, res_nu):
    print(f"\n{'='*60}\n  Convergence: uniform vs non-uniform\n{'='*60}")
    print(f"  {'N':>6} | {'uniform d1':>10} {'slope':>6} | {'non-uni d1':>10} {'slope':>6}")
    for ru, rn in zip(res_uni, res_nu):
        su = ru.get("d1_Li_slope", float("nan"))
        sn = rn.get("d1_Li_slope", float("nan"))
        print(f"  {ru['N']:>6} | {ru['d1_Li']:>10.3e} {su:>6.2f} | {rn['d1_Li']:>10.3e} {sn:>6.2f}")


def plot_all(res_uni, res_nu, res_gcl):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    ax = axes[0]
    h_u = [r["h"] for r in res_uni]; h_n = [r["h"] for r in res_nu]
    ax.loglog(h_u, [r["d1_Li"] for r in res_uni], "o-", label=r"Uniform ($\alpha=1$)")
    ax.loglog(h_n, [r["d1_Li"] for r in res_nu], "s--", label=r"Non-uniform ($\alpha=2$)")
    h_ref = np.array([h_u[0], h_u[-1]])
    for order in [5, 6]:
        ax.loglog(h_ref, res_uni[0]["d1_Li"]*(h_ref/h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title(r"(a) $\partial f/\partial x$, $f=\sin(\pi x)$")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    ax = axes[1]
    Ns_gcl = [r["N"] for r in res_gcl]
    gcl_x = [r["gcl_x"] for r in res_gcl]
    gcl_y = [r["gcl_y"] for r in res_gcl]
    x_pos = np.arange(len(Ns_gcl))
    w = 0.35
    ax.bar(x_pos - w/2, gcl_x, w, label=r"$|\partial(1)/\partial x|_\infty$", color=COLORS[0])
    ax.bar(x_pos + w/2, gcl_y, w, label=r"$|\partial(1)/\partial y|_\infty$", color=COLORS[1])
    ax.axhline(res_gcl[0]["threshold"], ls="--", color="red", lw=1, label=r"$10^3 \varepsilon_{\rm mach}$")
    ax.set_xticks(x_pos); ax.set_xticklabels([str(n) for n in Ns_gcl])
    ax.set_xlabel("$N$"); ax.set_ylabel("GCL residual")
    ax.set_yscale("log"); ax.set_title("(b) GCL verification")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    save_figure(fig, OUT / "gcl_nonuniform")


def main():
    args = experiment_argparser("[11-4] GCL Non-uniform").parse_args()
    Ns = [16, 32, 64, 128]

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["uniform"], d["nonuniform"], d["gcl"])
        return

    print("\n--- (a) Convergence ---")
    res_uni = convergence_test(Ns, alpha=1.0)
    res_nu = convergence_test(Ns, alpha=2.0)
    print_convergence(res_uni, res_nu)

    print("\n--- (b) GCL test ---")
    res_gcl = gcl_test(Ns, alpha=2.0)

    save_results(OUT / "data.npz", {
        "uniform": res_uni, "nonuniform": res_nu, "gcl": res_gcl})
    plot_all(res_uni, res_nu, res_gcl)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
