#!/usr/bin/env python3
"""【10-3】Curvature κ computation accuracy.

Tests:
(a) Circle: κ_exact = 1/R, grid convergence for R=0.25
(b) Sinusoidal interface: κ varies along interface, max error evaluation
(c) Comparison: CCD 6th-order vs standard 2nd-order central difference

Paper ref: §2c, §10 curvature verification
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

OUT = pathlib.Path(__file__).resolve().parent / "results" / "curvature"
OUT.mkdir(parents=True, exist_ok=True)


def curvature_cd2(phi, grid):
    """Standard 2nd-order central difference curvature (baseline)."""
    xp = np
    ndim = grid.ndim
    h = [float(grid.L[ax]) / grid.N[ax] for ax in range(ndim)]

    # First derivatives (central diff)
    phi_x = np.zeros_like(phi)
    phi_y = np.zeros_like(phi)
    phi_x[1:-1, :] = (phi[2:, :] - phi[:-2, :]) / (2 * h[0])
    phi_y[:, 1:-1] = (phi[:, 2:] - phi[:, :-2]) / (2 * h[1])

    # Second derivatives
    phi_xx = np.zeros_like(phi)
    phi_yy = np.zeros_like(phi)
    phi_xy = np.zeros_like(phi)
    phi_xx[1:-1, :] = (phi[2:, :] - 2*phi[1:-1, :] + phi[:-2, :]) / h[0]**2
    phi_yy[:, 1:-1] = (phi[:, 2:] - 2*phi[:, 1:-1] + phi[:, :-2]) / h[1]**2
    phi_xy[1:-1, 1:-1] = (phi[2:, 2:] - phi[2:, :-2] - phi[:-2, 2:] + phi[:-2, :-2]) / (4*h[0]*h[1])

    # Curvature
    grad_mag = np.sqrt(phi_x**2 + phi_y**2 + 1e-12)
    kappa = -(phi_y**2 * phi_xx - 2*phi_x*phi_y*phi_xy + phi_x**2 * phi_yy) / grad_mag**3

    return kappa


def circle_convergence(R=0.25, center=(0.5, 0.5)):
    """Grid convergence of curvature for a circle."""
    backend = Backend(use_gpu=False)
    Ns = [16, 32, 64, 128, 256]
    kappa_exact = 1.0 / R

    results_ccd = []
    results_cd2 = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N

        X, Y = grid.meshgrid()
        phi = R - np.sqrt((X - center[0])**2 + (Y - center[1])**2)  # positive inside
        psi = heaviside(np, phi, eps)

        # CCD curvature
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa_ccd = curv_calc.compute(psi)

        # CD2 curvature (from phi directly)
        kappa_cd2 = curvature_cd2(phi, grid)

        # Measure error near interface (|phi| < 3h)
        h = 1.0 / N
        near_interface = np.abs(phi) < 3 * h

        if np.any(near_interface):
            err_ccd_Li = float(np.max(np.abs(kappa_ccd[near_interface] - kappa_exact)))
            err_ccd_L2 = float(np.sqrt(np.mean((kappa_ccd[near_interface] - kappa_exact)**2)))
            err_cd2_Li = float(np.max(np.abs(kappa_cd2[near_interface] - kappa_exact)))
            err_cd2_L2 = float(np.sqrt(np.mean((kappa_cd2[near_interface] - kappa_exact)**2)))
        else:
            err_ccd_Li = err_ccd_L2 = err_cd2_Li = err_cd2_L2 = float("nan")

        results_ccd.append({"N": N, "h": h, "Li": err_ccd_Li, "L2": err_ccd_L2})
        results_cd2.append({"N": N, "h": h, "Li": err_cd2_Li, "L2": err_cd2_L2})

    # Compute slopes
    for res_list in [results_ccd, results_cd2]:
        for i in range(1, len(res_list)):
            r0, r1 = res_list[i-1], res_list[i]
            log_h = np.log(r1["h"] / r0["h"])
            for key in ["Li", "L2"]:
                if r0[key] > 0 and r1[key] > 0:
                    r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results_ccd, results_cd2


def sinusoidal_interface_test():
    """Curvature accuracy for sinusoidal interface y = 0.5 + A·sin(2πx)."""
    backend = Backend(use_gpu=False)
    A = 0.05  # amplitude
    Ns = [32, 64, 128, 256]
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N

        X, Y = grid.meshgrid()
        # SDF for sinusoidal interface (positive below = "liquid" side)
        y_interface = 0.5 + A * np.sin(2 * np.pi * X)
        phi = y_interface - Y  # positive below interface
        psi = heaviside(np, phi, eps)

        # CCD curvature
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa_ccd = curv_calc.compute(psi)

        # Exact curvature for y = f(x): κ = -f''/(1+f'^2)^{3/2}
        f_prime = A * 2 * np.pi * np.cos(2 * np.pi * X)
        f_double = -A * (2 * np.pi)**2 * np.sin(2 * np.pi * X)
        kappa_exact = -f_double / (1 + f_prime**2)**1.5

        # Error near interface
        h = 1.0 / N
        near = np.abs(phi) < 3 * h
        if np.any(near):
            err_Li = float(np.max(np.abs(kappa_ccd[near] - kappa_exact[near])))
            err_L2 = float(np.sqrt(np.mean((kappa_ccd[near] - kappa_exact[near])**2)))
        else:
            err_Li = err_L2 = float("nan")

        results.append({"N": N, "h": h, "Li": err_Li, "L2": err_L2})

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for key in ["Li", "L2"]:
            if r0[key] > 0 and r1[key] > 0:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results


def plot_results(res_ccd, res_cd2, res_sin):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # (a) Circle: CCD vs CD2
    ax = axes[0]
    h_ccd = [r["h"] for r in res_ccd]
    h_cd2 = [r["h"] for r in res_cd2]
    ax.loglog(h_ccd, [r["Li"] for r in res_ccd], "o-", label=r"CCD $L_\infty$")
    ax.loglog(h_ccd, [r["L2"] for r in res_ccd], "s--", label=r"CCD $L_2$")
    ax.loglog(h_cd2, [r["Li"] for r in res_cd2], "^-", label=r"CD2 $L_\infty$")
    ax.loglog(h_cd2, [r["L2"] for r in res_cd2], "v--", label=r"CD2 $L_2$")

    # Reference slopes
    h_ref = np.array([h_ccd[0], h_ccd[-1]])
    for order, ls, c in [(2, ":", "gray"), (4, "-.", "gray"), (6, "--", "gray")]:
        e0 = res_ccd[0]["Li"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, ls, color=c, alpha=0.4,
                  label=f"$O(h^{order})$")

    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$|\kappa - \kappa_{\mathrm{exact}}|$")
    ax.set_title(r"(a) Circle $R=0.25$, $\kappa_{\mathrm{exact}}=4$")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", alpha=0.3)

    # (b) Sinusoidal interface
    ax = axes[1]
    h_sin = [r["h"] for r in res_sin]
    ax.loglog(h_sin, [r["Li"] for r in res_sin], "o-", label=r"$L_\infty$")
    ax.loglog(h_sin, [r["L2"] for r in res_sin], "s--", label=r"$L_2$")
    h_ref = np.array([h_sin[0], h_sin[-1]])
    for order, ls in [(2, ":"), (4, "-.")]:
        e0 = res_sin[0]["Li"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, ls, color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")
    ax.set_xlabel("$h$")
    ax.set_ylabel(r"$|\kappa - \kappa_{\mathrm{exact}}|$")
    ax.set_title(r"(b) Sinusoidal $y=0.5+0.05\sin(2\pi x)$")
    ax.legend(fontsize=7)
    ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT / "curvature_accuracy.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'curvature_accuracy.png'}")


def print_and_save(res_ccd, res_cd2, res_sin):
    print(f"\n{'='*70}")
    print("  Circle curvature convergence (R=0.25, κ_exact=4.0)")
    print(f"{'='*70}")
    print(f"  {'N':>6} | {'CCD Li':>10} {'slope':>6} | {'CD2 Li':>10} {'slope':>6}")
    for i, (rc, r2) in enumerate(zip(res_ccd, res_cd2)):
        sc = rc.get("Li_slope", float("nan"))
        s2 = r2.get("Li_slope", float("nan"))
        print(f"  {rc['N']:>6} | {rc['Li']:>10.3e} {sc:>6.2f} | {r2['Li']:>10.3e} {s2:>6.2f}")

    print(f"\n  Sinusoidal interface curvature convergence:")
    print(f"  {'N':>6} | {'Li':>10} {'slope':>6} | {'L2':>10} {'slope':>6}")
    for r in res_sin:
        sl = r.get("Li_slope", float("nan"))
        s2 = r.get("L2_slope", float("nan"))
        print(f"  {r['N']:>6} | {r['Li']:>10.3e} {sl:>6.2f} | {r['L2']:>10.3e} {s2:>6.2f}")

    # LaTeX tables
    with open(OUT / "table_circle.tex", "w") as fp:
        fp.write("% Circle curvature convergence\n")
        fp.write("\\begin{tabular}{rrrrr}\n\\toprule\n")
        fp.write("$N$ & CCD $L_\\infty$ & slope & CD2 $L_\\infty$ & slope \\\\\n\\midrule\n")
        for rc, r2 in zip(res_ccd, res_cd2):
            sc = rc.get("Li_slope", float("nan"))
            s2 = r2.get("Li_slope", float("nan"))
            sc_s = f"{sc:.2f}" if not np.isnan(sc) else "---"
            s2_s = f"{s2:.2f}" if not np.isnan(s2) else "---"
            fp.write(f"{rc['N']} & {rc['Li']:.2e} & {sc_s} & {r2['Li']:.2e} & {s2_s} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")


def main():
    print("\n" + "="*80)
    print("  【10-3】Curvature κ Computation Accuracy")
    print("="*80)

    print("\n--- (a) Circle R=0.25 convergence ---")
    res_ccd, res_cd2 = circle_convergence()

    print("\n--- (b) Sinusoidal interface ---")
    res_sin = sinusoidal_interface_test()

    print_and_save(res_ccd, res_cd2, res_sin)
    plot_results(res_ccd, res_cd2, res_sin)

    np.savez(OUT / "curvature_data.npz",
             circle_ccd=res_ccd, circle_cd2=res_cd2, sinusoidal=res_sin)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "curvature_data.npz", allow_pickle=True)
        plot_results(list(_d["circle_ccd"]), list(_d["circle_cd2"]), list(_d["sinusoidal"]))
    else:
        main()
