#!/usr/bin/env python3
"""[11-3] Curvature kappa computation -- three-path comparison.

Validates: Ch2c -- Curvature formula kappa = -div(grad(phi)/|grad(phi)|).

Tests:
  (a) Circle R=0.25, kappa_exact=4: CCD vs CD2 convergence
  (b) Sinusoidal interface y=0.5+0.05*sin(2*pi*x): variable curvature

Expected: CCD path O(h^4-5) near interface; CD2 O(h^2).
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.heaviside import heaviside
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def curvature_cd2(phi, grid, xp):
    h = [float(grid.L[ax]) / grid.N[ax] for ax in range(grid.ndim)]
    phi_x = xp.zeros_like(phi); phi_y = xp.zeros_like(phi)
    phi_x[1:-1, :] = (phi[2:, :] - phi[:-2, :]) / (2 * h[0])
    phi_y[:, 1:-1] = (phi[:, 2:] - phi[:, :-2]) / (2 * h[1])
    phi_xx = xp.zeros_like(phi); phi_yy = xp.zeros_like(phi); phi_xy = xp.zeros_like(phi)
    phi_xx[1:-1, :] = (phi[2:, :] - 2*phi[1:-1, :] + phi[:-2, :]) / h[0]**2
    phi_yy[:, 1:-1] = (phi[:, 2:] - 2*phi[:, 1:-1] + phi[:, :-2]) / h[1]**2
    phi_xy[1:-1, 1:-1] = (phi[2:, 2:] - phi[2:, :-2] - phi[:-2, 2:] + phi[:-2, :-2]) / (4*h[0]*h[1])
    grad_mag = xp.sqrt(phi_x**2 + phi_y**2 + 1e-12)
    kappa = -(phi_y**2 * phi_xx - 2*phi_x*phi_y*phi_xy + phi_x**2 * phi_yy) / grad_mag**3
    return kappa


def circle_convergence(R=0.25, center=(0.5, 0.5)):
    backend = Backend()
    xp = backend.xp
    Ns = [16, 32, 64, 128, 256]
    kappa_exact = 1.0 / R
    res_ccd, res_cd2 = [], []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N
        X, Y = grid.meshgrid()
        phi = R - xp.sqrt((X - center[0])**2 + (Y - center[1])**2)
        psi = heaviside(xp, phi, eps)

        kappa_ccd = CurvatureCalculator(backend, ccd, eps).compute(psi)
        kappa_cd2_val = curvature_cd2(phi, grid, xp)

        h = 1.0 / N
        near = xp.abs(phi) < 3 * h
        if bool(xp.any(near)):
            res_ccd.append({"N": N, "h": h,
                "Li": float(xp.max(xp.abs(kappa_ccd[near] - kappa_exact))),
                "L2": float(xp.sqrt(xp.mean((kappa_ccd[near] - kappa_exact)**2)))})
            res_cd2.append({"N": N, "h": h,
                "Li": float(xp.max(xp.abs(kappa_cd2_val[near] - kappa_exact))),
                "L2": float(xp.sqrt(xp.mean((kappa_cd2_val[near] - kappa_exact)**2)))})

    for res in [res_ccd, res_cd2]:
        for i in range(1, len(res)):
            r0, r1 = res[i-1], res[i]
            log_h = np.log(r1["h"] / r0["h"])
            for k in ["Li", "L2"]:
                if r0[k] > 0 and r1[k] > 0:
                    r1[f"{k}_slope"] = np.log(r1[k] / r0[k]) / log_h
    return res_ccd, res_cd2


def sinusoidal_test(A=0.05):
    backend = Backend()
    xp = backend.xp
    Ns = [32, 64, 128, 256]
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N
        X, Y = grid.meshgrid()
        y_if = 0.5 + A * xp.sin(2 * np.pi * X)
        phi = y_if - Y
        psi = heaviside(xp, phi, eps)
        kappa_ccd = CurvatureCalculator(backend, ccd, eps).compute(psi)

        f_p = A * 2 * np.pi * xp.cos(2 * np.pi * X)
        f_pp = -A * (2 * np.pi)**2 * xp.sin(2 * np.pi * X)
        kappa_exact = -f_pp / (1 + f_p**2)**1.5

        h = 1.0 / N
        near = xp.abs(phi) < 3 * h
        if bool(xp.any(near)):
            results.append({"N": N, "h": h,
                "Li": float(xp.max(xp.abs(kappa_ccd[near] - kappa_exact[near]))),
                "L2": float(xp.sqrt(xp.mean((kappa_ccd[near] - kappa_exact[near])**2)))})

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for k in ["Li", "L2"]:
            if r0[k] > 0 and r1[k] > 0:
                r1[f"{k}_slope"] = np.log(r1[k] / r0[k]) / log_h
    return results


def print_results(res_ccd, res_cd2, res_sin):
    print(f"\n{'='*60}\n  Circle R=0.25, kappa_exact=4.0\n{'='*60}")
    print(f"  {'N':>6} | {'CCD Li':>10} {'slope':>6} | {'CD2 Li':>10} {'slope':>6}")
    for rc, r2 in zip(res_ccd, res_cd2):
        sc = rc.get("Li_slope", float("nan"))
        s2 = r2.get("Li_slope", float("nan"))
        print(f"  {rc['N']:>6} | {rc['Li']:>10.3e} {sc:>6.2f} | {r2['Li']:>10.3e} {s2:>6.2f}")

    print(f"\n  Sinusoidal interface:")
    print(f"  {'N':>6} | {'Li':>10} {'slope':>6}")
    for r in res_sin:
        print(f"  {r['N']:>6} | {r['Li']:>10.3e} {r.get('Li_slope', float('nan')):>6.2f}")


def plot_all(res_ccd, res_cd2, res_sin):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    ax = axes[0]
    h_ccd = [r["h"] for r in res_ccd]
    ax.loglog(h_ccd, [r["Li"] for r in res_ccd], "o-", label=r"CCD $L_\infty$")
    ax.loglog(h_ccd, [r["L2"] for r in res_ccd], "s--", label=r"CCD $L_2$")
    h_cd2 = [r["h"] for r in res_cd2]
    ax.loglog(h_cd2, [r["Li"] for r in res_cd2], "^-", label=r"CD2 $L_\infty$")
    h_ref = np.array([h_ccd[0], h_ccd[-1]])
    for order in [2, 4]:
        ax.loglog(h_ref, res_ccd[0]["Li"]*(h_ref/h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$|\kappa - \kappa_{\rm exact}|$")
    ax.set_title(r"(a) Circle $R=0.25$"); ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    ax = axes[1]
    h_s = [r["h"] for r in res_sin]
    ax.loglog(h_s, [r["Li"] for r in res_sin], "o-", label=r"$L_\infty$")
    ax.loglog(h_s, [r["L2"] for r in res_sin], "s--", label=r"$L_2$")
    h_ref = np.array([h_s[0], h_s[-1]])
    for order in [2, 4]:
        ax.loglog(h_ref, res_sin[0]["Li"]*(h_ref/h_ref[0])**order,
                  ":", color="gray", alpha=0.5, label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$|\kappa - \kappa_{\rm exact}|$")
    ax.set_title(r"(b) Sinusoidal $y=0.5+0.05\sin(2\pi x)$")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "curvature_3path")


def main():
    args = experiment_argparser("[11-3] Curvature 3-path").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["circle_ccd"], d["circle_cd2"], d["sinusoidal"])
        return

    print("\n--- (a) Circle R=0.25 ---")
    res_ccd, res_cd2 = circle_convergence()
    print("\n--- (b) Sinusoidal interface ---")
    res_sin = sinusoidal_test()
    print_results(res_ccd, res_cd2, res_sin)

    save_results(OUT / "data.npz", {
        "circle_ccd": res_ccd, "circle_cd2": res_cd2, "sinusoidal": res_sin})
    plot_all(res_ccd, res_cd2, res_sin)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
