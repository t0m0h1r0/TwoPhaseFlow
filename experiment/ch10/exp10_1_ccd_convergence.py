#!/usr/bin/env python3
"""【10-1】CCD/DCCD spatial differentiation convergence test.

Test CCD 1st/2nd derivatives on smooth functions (sin, exp) for both
uniform and non-uniform grids. Measures L2/Linf errors and log-log slopes.

Expected: O(h^6) interior, O(h^5) boundary-limited on wall BC.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver

# ── Output ──────────────────────────────────────────────
OUT = pathlib.Path(__file__).resolve().parent / "results" / "ccd_convergence"
OUT.mkdir(parents=True, exist_ok=True)

# ── Test functions ──────────────────────────────────────
def _sin_test(x, y):
    """f = sin(2πx)sin(2πy), periodic-compatible."""
    k = 2 * np.pi
    f = np.sin(k * x) * np.sin(k * y)
    fx = k * np.cos(k * x) * np.sin(k * y)
    fy = k * np.sin(k * x) * np.cos(k * y)
    fxx = -(k**2) * np.sin(k * x) * np.sin(k * y)
    fyy = -(k**2) * np.sin(k * x) * np.cos(k * y) * 0 + fxx  # same by symmetry
    fyy = -(k**2) * np.sin(k * x) * np.sin(k * y)
    return f, (fx, fy), (fxx, fyy)

def _exp_test(x, y):
    """f = exp(sin(πx))·exp(cos(πy)), non-periodic."""
    f = np.exp(np.sin(np.pi * x)) * np.exp(np.cos(np.pi * y))
    fx = np.pi * np.cos(np.pi * x) * f
    fy = -np.pi * np.sin(np.pi * y) * f
    fxx = (np.pi**2) * (-np.sin(np.pi * x) + np.pi * np.cos(np.pi * x)**2) * \
          np.exp(np.sin(np.pi * x)) * np.exp(np.cos(np.pi * y))
    # Correct fxx
    fxx = np.exp(np.sin(np.pi * x)) * np.exp(np.cos(np.pi * y)) * \
          (np.pi**2) * (-np.sin(np.pi * x) + np.cos(np.pi * x)**2 * np.pi)
    # Recalculate cleanly
    sx = np.sin(np.pi * x); cx = np.cos(np.pi * x)
    sy = np.sin(np.pi * y); cy = np.cos(np.pi * y)
    ef = np.exp(sx) * np.exp(cy)
    fx = np.pi * cx * ef
    fxx = ef * np.pi**2 * (-sx + cx**2)
    fy = -np.pi * sy * ef
    fyy = ef * np.pi**2 * (-cy + sy**2)
    return f, (fx, fy), (fxx, fyy)


def run_convergence(test_func, bc_type, Ns, label):
    """Run grid convergence study for a test function."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=1.0)
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type=bc_type)

        X, Y = grid.meshgrid()
        f_exact, (fx_ex, fy_ex), (fxx_ex, fyy_ex) = test_func(X, Y)

        # Differentiate along x (axis=0) and y (axis=1)
        d1x, d2x = ccd.differentiate(f_exact, axis=0)
        d1y, d2y = ccd.differentiate(f_exact, axis=1)

        # Errors (interior only for wall BC to avoid boundary effects)
        if bc_type == "wall":
            s = slice(2, -2)
        else:
            s = slice(None)

        err_d1x_L2 = float(xp.sqrt(xp.mean((d1x[s, s] - fx_ex[s, s])**2)))
        err_d1x_Li = float(xp.max(xp.abs(d1x[s, s] - fx_ex[s, s])))
        err_d2x_L2 = float(xp.sqrt(xp.mean((d2x[s, s] - fxx_ex[s, s])**2)))
        err_d2x_Li = float(xp.max(xp.abs(d2x[s, s] - fxx_ex[s, s])))
        err_d1y_L2 = float(xp.sqrt(xp.mean((d1y[s, s] - fy_ex[s, s])**2)))
        err_d1y_Li = float(xp.max(xp.abs(d1y[s, s] - fy_ex[s, s])))
        err_d2y_L2 = float(xp.sqrt(xp.mean((d2y[s, s] - fyy_ex[s, s])**2)))
        err_d2y_Li = float(xp.max(xp.abs(d2y[s, s] - fyy_ex[s, s])))

        h = 1.0 / N
        results.append({
            "N": N, "h": h,
            "d1x_L2": err_d1x_L2, "d1x_Li": err_d1x_Li,
            "d2x_L2": err_d2x_L2, "d2x_Li": err_d2x_Li,
            "d1y_L2": err_d1y_L2, "d1y_Li": err_d1y_Li,
            "d2y_L2": err_d2y_L2, "d2y_Li": err_d2y_Li,
        })

    # Compute slopes
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for key in ["d1x_L2", "d1x_Li", "d2x_L2", "d2x_Li",
                     "d1y_L2", "d1y_Li", "d2y_L2", "d2y_Li"]:
            if r0[key] > 0 and r1[key] > 0:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h
            else:
                r1[f"{key}_slope"] = float("nan")

    return results


def run_nonuniform_convergence(test_func, Ns, alpha, label):
    """Run convergence on non-uniform (interface-fitted) grids."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha)
        grid = Grid(gc, backend)

        # Create a level-set field to drive grid adaptation
        X0, Y0 = np.meshgrid(
            np.linspace(0, 1, N+1), np.linspace(0, 1, N+1), indexing="ij"
        )
        phi_init = np.sqrt((X0 - 0.5)**2 + (Y0 - 0.5)**2) - 0.25
        grid.update_from_levelset(phi_init, eps=0.05)

        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        f_exact, (fx_ex, fy_ex), (fxx_ex, fyy_ex) = test_func(X, Y)

        d1x, d2x = ccd.differentiate(f_exact, axis=0)
        d1y, d2y = ccd.differentiate(f_exact, axis=1)

        s = slice(2, -2)
        h_eff = float(np.mean([np.mean(grid.h[ax]) for ax in range(2)]))

        err_d1_L2 = float(xp.sqrt(xp.mean((d1x[s, s] - fx_ex[s, s])**2)))
        err_d1_Li = float(xp.max(xp.abs(d1x[s, s] - fx_ex[s, s])))
        err_d2_L2 = float(xp.sqrt(xp.mean((d2x[s, s] - fxx_ex[s, s])**2)))
        err_d2_Li = float(xp.max(xp.abs(d2x[s, s] - fxx_ex[s, s])))

        results.append({
            "N": N, "h": h_eff,
            "d1_L2": err_d1_L2, "d1_Li": err_d1_Li,
            "d2_L2": err_d2_L2, "d2_Li": err_d2_Li,
        })

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for key in ["d1_L2", "d1_Li", "d2_L2", "d2_Li"]:
            if r0[key] > 0 and r1[key] > 0:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results


def print_table(results, keys, title):
    """Print convergence table."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")
    header = f"{'N':>6} {'h':>10}"
    for k in keys:
        header += f" {k:>12} {'slope':>6}"
    print(header)
    print("-" * len(header))
    for r in results:
        line = f"{r['N']:>6} {r['h']:>10.2e}"
        for k in keys:
            val = r.get(k, 0.0)
            slope = r.get(f"{k}_slope", float("nan"))
            line += f" {val:>12.3e} {slope:>6.2f}"
        print(line)


def save_latex_table(results, keys, title, filename):
    """Save LaTeX-formatted convergence table."""
    with open(OUT / filename, "w") as fp:
        fp.write(f"% {title}\n")
        # Header
        cols = "r" + "".join(["rr"] * len(keys))
        fp.write(f"\\begin{{tabular}}{{{cols}}}\n\\toprule\n")
        header = "$N$"
        for k in keys:
            short = k.replace("_L2", " $L_2$").replace("_Li", " $L_\\infty$")
            header += f" & {short} & slope"
        fp.write(header + " \\\\\n\\midrule\n")
        for r in results:
            line = f"{r['N']}"
            for k in keys:
                val = r.get(k, 0.0)
                slope = r.get(f"{k}_slope", float("nan"))
                if np.isnan(slope):
                    line += f" & {val:.2e} & ---"
                else:
                    line += f" & {val:.2e} & {slope:.2f}"
            fp.write(line + " \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")


def plot_convergence(results_list, labels, keys, title, filename):
    """Plot convergence curves."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(keys), figsize=(5 * len(keys), 4))
    if len(keys) == 1:
        axes = [axes]

    for ax, key in zip(axes, keys):
        for results, label in zip(results_list, labels):
            hs = [r["h"] for r in results]
            errs = [r[key] for r in results if key in r]
            if len(errs) == len(hs):
                ax.loglog(hs, errs, "o-", label=label)

        # Reference slopes
        h_ref = np.array([results_list[0][0]["h"], results_list[0][-1]["h"]])
        for order, ls in [(4, ":"), (5, "--"), (6, "-.")]:
            e_ref = errs[0] * (h_ref / h_ref[0])**order
            ax.loglog(h_ref, e_ref, ls, color="gray", alpha=0.5,
                      label=f"$O(h^{order})$")

        ax.set_xlabel("$h$")
        short = key.replace("_L2", " $L_2$").replace("_Li", " $L_\\infty$")
        ax.set_ylabel(f"Error ({short})")
        ax.legend(fontsize=7)
        ax.grid(True, which="both", alpha=0.3)

    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / filename}")


# ── Main ────────────────────────────────────────────────
def main():
    Ns = [16, 32, 64, 128, 256]

    # Case A: sin on periodic grid (should give full O(h^6))
    print("\n" + "="*80)
    print("  Case A: sin(2πx)sin(2πy) — periodic BC")
    res_sin_per = run_convergence(_sin_test, "periodic", Ns, "sin_periodic")
    print_table(res_sin_per, ["d1x_L2", "d1x_Li", "d2x_L2", "d2x_Li"],
                "Case A: sin — periodic BC")
    save_latex_table(res_sin_per, ["d1x_L2", "d1x_Li", "d2x_L2", "d2x_Li"],
                     "CCD periodic sin", "table_sin_periodic.tex")

    # Case B: exp on wall grid (boundary-limited ~O(h^4-5))
    print("\n" + "="*80)
    print("  Case B: exp(sin(πx))exp(cos(πy)) — wall BC")
    res_exp_wall = run_convergence(_exp_test, "wall", Ns, "exp_wall")
    print_table(res_exp_wall, ["d1x_L2", "d1x_Li", "d2x_L2", "d2x_Li"],
                "Case B: exp — wall BC")
    save_latex_table(res_exp_wall, ["d1x_L2", "d1x_Li", "d2x_L2", "d2x_Li"],
                     "CCD wall exp", "table_exp_wall.tex")

    # Case C: Non-uniform grid
    print("\n" + "="*80)
    print("  Case C: exp test — non-uniform grid (alpha=2.0)")
    res_nonunif = run_nonuniform_convergence(_exp_test, Ns, alpha=2.0, label="nonuniform")
    print_table(res_nonunif, ["d1_L2", "d1_Li", "d2_L2", "d2_Li"],
                "Case C: exp — non-uniform grid")
    save_latex_table(res_nonunif, ["d1_L2", "d1_Li", "d2_L2", "d2_Li"],
                     "CCD non-uniform exp", "table_nonuniform.tex")

    # Plot
    plot_convergence(
        [res_sin_per, res_exp_wall],
        ["sin (periodic)", "exp (wall)"],
        ["d1x_Li", "d2x_Li"],
        "CCD Differentiation Convergence",
        "ccd_convergence.png",
    )

    # Save raw data
    np.savez(OUT / "convergence_data.npz",
             sin_periodic=res_sin_per,
             exp_wall=res_exp_wall,
             nonuniform=res_nonunif)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import sys as _sys
    if "--plot-only" in _sys.argv:
        import matplotlib; matplotlib.use("Agg")
        d = np.load(OUT / "convergence_data.npz", allow_pickle=True)
        res_sin_per = list(d["sin_periodic"])
        res_exp_wall = list(d["exp_wall"])
        plot_convergence(
            [res_sin_per, res_exp_wall],
            ["sin (periodic)", "exp (wall)"],
            ["d1x_Li", "d2x_Li"],
            "CCD Differentiation Convergence",
            "ccd_convergence.png",
        )
        print("  --plot-only done.")
    else:
        main()
