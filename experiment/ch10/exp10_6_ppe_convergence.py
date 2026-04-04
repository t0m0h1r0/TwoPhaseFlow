#!/usr/bin/env python3
"""【10-6】PPE solver convergence characteristics.

Tests:
(a) CCD-PPE grid convergence (manufactured solution)
(b) Iterative solver comparison: LGMRES vs BiCGSTAB
(c) Condition number estimation vs grid size

Paper ref: §8, §8b, §8d
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import time
from twophase.backend import Backend
from twophase.config import GridConfig, FluidConfig, NumericsConfig, SolverConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver

OUT = pathlib.Path(__file__).resolve().parent / "results" / "ppe"
OUT.mkdir(parents=True, exist_ok=True)


def manufactured_solution(X, Y):
    """Manufactured pressure: p = cos(2πx)cos(2πy).

    Satisfies Neumann BC ∂p/∂n = 0 at all walls of [0,1]².
    Laplacian: ∇²p = -8π² cos(2πx)cos(2πy).
    """
    k = 2 * np.pi
    p = np.cos(k * X) * np.cos(k * Y)
    lap_p = -2 * k**2 * np.cos(k * X) * np.cos(k * Y)
    return p, lap_p


def grid_convergence(Ns=[16, 32, 64, 128]):
    """PPE grid convergence with manufactured solution (constant density).

    Compares CCD+LGMRES (pseudotime, O(h^6)) vs FVM-LU (O(h^2)).
    Note: CCD-LU direct solver diverges with Neumann BC due to null space;
    use pseudotime (LGMRES) as the CCD solver pathway.
    """
    backend = Backend(use_gpu=False)
    results = {"ccd_lgmres": [], "lu": []}

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N

        X, Y = grid.meshgrid()
        p_exact, lap_exact = manufactured_solution(X, Y)

        rho = np.ones_like(p_exact)  # uniform density
        rhs = lap_exact  # RHS = (1/ρ)∇²p = ∇²p (for ρ=1)
        p_ref = p_exact - np.mean(p_exact)

        # CCD+LGMRES solver (pseudotime, O(h^6) expected)
        sc_ccd = SolverConfig(ppe_solver_type="pseudotime",
                              pseudo_tol=1e-12, pseudo_maxiter=2000)
        config_ccd = SimulationConfig(
            grid=gc, fluid=FluidConfig(), numerics=NumericsConfig(bc_type="wall"),
            solver=sc_ccd)
        from twophase.pressure.ppe_solver_pseudotime import PPESolverPseudoTime
        ppe_ccd = PPESolverPseudoTime(backend, config_ccd, grid, ccd)
        p_ccd = ppe_ccd.solve(rhs, rho, dt=1.0)
        p_ccd -= np.mean(p_ccd)

        err_ccd_L2 = float(np.sqrt(np.mean((p_ccd - p_ref)**2)))
        err_ccd_Li = float(np.max(np.abs(p_ccd - p_ref)))

        results["ccd_lgmres"].append({"N": N, "h": h, "L2": err_ccd_L2, "Li": err_ccd_Li})

        # FVM-LU solver (O(h^2) expected)
        sc_lu = SolverConfig(ppe_solver_type="pseudotime")
        config_lu = SimulationConfig(
            grid=gc, fluid=FluidConfig(), numerics=NumericsConfig(bc_type="wall"),
            solver=sc_lu)
        from twophase.pressure.ppe_solver_lu import PPESolverLU
        ppe_lu = PPESolverLU(backend, config_lu, grid)
        p_lu = ppe_lu.solve(rhs, rho, dt=1.0)
        p_lu -= np.mean(p_lu)

        err_lu_L2 = float(np.sqrt(np.mean((p_lu - p_ref)**2)))
        err_lu_Li = float(np.max(np.abs(p_lu - p_ref)))

        results["lu"].append({"N": N, "h": h, "L2": err_lu_L2, "Li": err_lu_Li})

        print(f"  N={N:>4}: CCD+LGMRES L2={err_ccd_L2:.3e} Li={err_ccd_Li:.3e}  |  "
              f"FVM-LU L2={err_lu_L2:.3e} Li={err_lu_Li:.3e}")

    # Slopes
    for solver_name in results:
        for i in range(1, len(results[solver_name])):
            r0, r1 = results[solver_name][i-1], results[solver_name][i]
            log_h = np.log(r1["h"] / r0["h"])
            for key in ["L2", "Li"]:
                if r0[key] > 0 and r1[key] > 0:
                    r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results




def variable_density_test(Ns=[32, 64, 128]):
    """PPE convergence with variable density (ρ_l/ρ_g = 1000)."""
    backend = Backend(use_gpu=False)
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        eps = 1.5 * h

        X, Y = grid.meshgrid()

        # Variable density: circle interface
        R = 0.25
        phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
        from twophase.levelset.heaviside import heaviside
        psi = heaviside(np, phi, eps)
        rho_l, rho_g = 1.0, 0.001
        rho = rho_g + (rho_l - rho_g) * psi

        # Manufactured: p = sin(2πx)sin(2πy)
        p_exact, _ = manufactured_solution(X, Y)

        # For variable-density PPE: ∇·((1/ρ)∇p) = rhs
        # Compute rhs numerically from p_exact using CCD
        d1x_p, d2x_p = ccd.differentiate(p_exact, axis=0)
        d1y_p, d2y_p = ccd.differentiate(p_exact, axis=1)

        # (1/ρ) ∇²p - (∇ρ/ρ²)·∇p
        d1x_rho, _ = ccd.differentiate(rho, axis=0)
        d1y_rho, _ = ccd.differentiate(rho, axis=1)

        rhs = (d2x_p + d2y_p) / rho - (d1x_rho * d1x_p + d1y_rho * d1y_p) / rho**2

        # Solve with CCD+LGMRES (pseudotime)
        sc = SolverConfig(ppe_solver_type="pseudotime",
                          pseudo_tol=1e-12, pseudo_maxiter=2000)
        config = SimulationConfig(
            grid=gc, fluid=FluidConfig(),
            numerics=NumericsConfig(bc_type="wall"), solver=sc)
        from twophase.pressure.ppe_solver_pseudotime import PPESolverPseudoTime
        ppe = PPESolverPseudoTime(backend, config, grid, ccd)
        p_sol = ppe.solve(rhs, rho, dt=1.0)

        p_sol -= np.mean(p_sol)
        p_ref = p_exact - np.mean(p_exact)

        err_L2 = float(np.sqrt(np.mean((p_sol - p_ref)**2)))
        err_Li = float(np.max(np.abs(p_sol - p_ref)))

        results.append({"N": N, "h": h, "L2": err_L2, "Li": err_Li})
        print(f"  N={N:>4}: L2={err_L2:.3e}, Li={err_Li:.3e}")

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for key in ["L2", "Li"]:
            if r0[key] > 0 and r1[key] > 0:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results


def plot_results(conv_results, var_rho_res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # (a) Grid convergence: CCD vs FVM
    ax = axes[0]
    for name, marker, ls in [("ccd_lgmres", "o", "-"), ("lu", "s", "--")]:
        h = [r["h"] for r in conv_results[name]]
        ax.loglog(h, [r["Li"] for r in conv_results[name]], f"{marker}{ls}",
                  label=f"{name.upper()} $L_\\infty$")
    h_ref = np.array([h[0], h[-1]])
    for order, lstyle in [(2, ":"), (4, "-."), (6, "--")]:
        e0 = conv_results["ccd_lgmres"][0]["Li"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, lstyle, color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("(a) PPE grid convergence (uniform $\\rho$)")
    ax.legend(fontsize=7); ax.grid(True, which="both", alpha=0.3)

    # (b) Variable density
    ax = axes[1]
    h = [r["h"] for r in var_rho_res]
    ax.loglog(h, [r["Li"] for r in var_rho_res], "o-", label=r"$L_\infty$")
    ax.loglog(h, [r["L2"] for r in var_rho_res], "s--", label=r"$L_2$")
    h_ref = np.array([h[0], h[-1]])
    for order in [2, 4]:
        e0 = var_rho_res[0]["Li"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, ":", color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel("Error")
    ax.set_title(r"(b) Variable density PPE ($\rho_l/\rho_g=1000$)")
    ax.legend(fontsize=7); ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT / "ppe_convergence.pdf", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'ppe_convergence.pdf'}")


def save_tables(conv_results, var_rho_res):
    with open(OUT / "table_ppe_convergence.tex", "w") as fp:
        fp.write("% PPE grid convergence\n")
        fp.write("\\begin{tabular}{rrrrrrr}\n\\toprule\n")
        fp.write("$N$ & CCD $L_\\infty$ & slope & FVM $L_\\infty$ & slope \\\\\n\\midrule\n")
        for rc, rl in zip(conv_results["ccd_lgmres"], conv_results["lu"]):
            sc = rc.get("Li_slope", float("nan"))
            sl = rl.get("Li_slope", float("nan"))
            sc_s = f"{sc:.2f}" if not np.isnan(sc) else "---"
            sl_s = f"{sl:.2f}" if not np.isnan(sl) else "---"
            fp.write(f"{rc['N']} & {rc['Li']:.2e} & {sc_s} & {rl['Li']:.2e} & {sl_s} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")

    with open(OUT / "table_variable_density.tex", "w") as fp:
        fp.write("% Variable density PPE convergence\n")
        fp.write("\\begin{tabular}{rrrr}\n\\toprule\n")
        fp.write("$N$ & $L_\\infty$ & slope \\\\\n\\midrule\n")
        for r in var_rho_res:
            s = r.get("Li_slope", float("nan"))
            s_s = f"{s:.2f}" if not np.isnan(s) else "---"
            fp.write(f"{r['N']} & {r['Li']:.2e} & {s_s} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")


def main():
    print("\n" + "="*80)
    print("  【10-6】PPE Solver Convergence")
    print("="*80)

    print("\n--- (a) Grid convergence: CCD+LGMRES vs FVM-LU ---")
    conv_results = grid_convergence()

    print("\n--- (b) Variable density (ρ_l/ρ_g=1000) ---")
    var_rho_res = variable_density_test()

    save_tables(conv_results, var_rho_res)
    plot_results(conv_results, var_rho_res)

    np.savez(OUT / "ppe_data.npz",
             convergence=conv_results,
             variable_density=var_rho_res)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "ppe_data.npz", allow_pickle=True)
        plot_results(list(_d["convergence"]), list(_d["variable_density"]))
    else:
        main()
