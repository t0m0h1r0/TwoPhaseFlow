#!/usr/bin/env python3
"""[12-5] Kovasznay spatial convergence (CCD-NS residual).

Paper ref: §12.3.2

Evaluates the CCD spatial discretization residual on the exact Kovasznay (1948)
solution.  No time stepping — purely spatial accuracy test.

Setup:
  Re = 40, ν = 1/Re = 0.025
  λ  = Re/2 - sqrt(Re²/4 + 4π²)
  u  = 1 - exp(λx)cos(2πy)
  v  = λ/(2π) exp(λx)sin(2πy)
  p  = -½ exp(2λx)
  Domain: [0,1] × [-0.5, 0.5], wall BC (Dirichlet)
  N ∈ {16, 32, 64, 128}

Residual measured on interior points [1:-1, 1:-1] only.

Expected: momentum residual O(h⁴), divergence residual O(h⁶).
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
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# --------------------------------------------------------------------------- #
# Physical parameters
# --------------------------------------------------------------------------- #
RE = 40.0
NU = 1.0 / RE
LAMBDA = RE / 2.0 - np.sqrt(RE**2 / 4.0 + 4.0 * np.pi**2)
N_LIST = [16, 32, 64, 128]


def exact_fields(X, Y):
    """Evaluate exact Kovasznay u, v, p on meshgrid arrays."""
    u = 1.0 - np.exp(LAMBDA * X) * np.cos(2.0 * np.pi * Y)
    v = LAMBDA / (2.0 * np.pi) * np.exp(LAMBDA * X) * np.sin(2.0 * np.pi * Y)
    p = -0.5 * np.exp(2.0 * LAMBDA * X)
    return u, v, p


def compute_residual(N):
    """Compute NS residual for given grid resolution."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    # Shift y-coordinates to [-0.5, 0.5]
    grid.coords[1] = grid.coords[1] - 0.5
    ccd = CCDSolver(grid, backend, bc_type="wall")

    X, Y = grid.meshgrid()
    u, v, p = exact_fields(X, Y)

    # CCD derivatives of u
    du_dx, d2u_dx2 = ccd.differentiate(u, 0)
    du_dy, d2u_dy2 = ccd.differentiate(u, 1)
    du_dx = np.asarray(du_dx); d2u_dx2 = np.asarray(d2u_dx2)
    du_dy = np.asarray(du_dy); d2u_dy2 = np.asarray(d2u_dy2)

    # CCD derivatives of v
    dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
    dv_dy, d2v_dy2 = ccd.differentiate(v, 1)
    dv_dx = np.asarray(dv_dx); d2v_dx2 = np.asarray(d2v_dx2)
    dv_dy = np.asarray(dv_dy); d2v_dy2 = np.asarray(d2v_dy2)

    # CCD derivatives of p
    dp_dx, _ = ccd.differentiate(p, 0)
    dp_dy, _ = ccd.differentiate(p, 1)
    dp_dx = np.asarray(dp_dx); dp_dy = np.asarray(dp_dy)

    # NS residuals (steady): R = -convection + viscous - pressure gradient
    R_u = -(u * du_dx + v * du_dy) + NU * (d2u_dx2 + d2u_dy2) - dp_dx
    R_v = -(u * dv_dx + v * dv_dy) + NU * (d2v_dx2 + d2v_dy2) - dp_dy
    R_div = du_dx + dv_dy

    # Measure on interior only (exclude boundary stencil error)
    interior = (slice(1, -1), slice(1, -1))
    err_mom = max(np.max(np.abs(R_u[interior])), np.max(np.abs(R_v[interior])))
    err_div = np.max(np.abs(R_div[interior]))
    h = 1.0 / N

    return h, err_mom, err_div


def run_convergence():
    """Run all resolutions and compute convergence rates."""
    results = []
    for N in N_LIST:
        h, err_mom, err_div = compute_residual(N)
        results.append({"N": N, "h": h, "err_mom": err_mom, "err_div": err_div})
        print(f"  N={N:>4}, h={h:.4e}, ||R_mom||∞={err_mom:.4e}, ||R_div||∞={err_div:.4e}")

    # Compute convergence orders
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0["err_mom"] > 1e-15 and r1["err_mom"] > 1e-15:
            r1["order_mom"] = np.log(r0["err_mom"] / r1["err_mom"]) / np.log(r0["h"] / r1["h"])
        if r0["err_div"] > 1e-15 and r1["err_div"] > 1e-15:
            r1["order_div"] = np.log(r0["err_div"] / r1["err_div"]) / np.log(r0["h"] / r1["h"])
    return results


def plot_convergence(results):
    """Generate convergence plot."""
    import matplotlib.pyplot as plt

    h_arr = np.array([r["h"] for r in results])
    err_mom = np.array([r["err_mom"] for r in results])
    err_div = np.array([r["err_div"] for r in results])

    fig, ax = plt.subplots(figsize=FIGSIZE_2COL)
    ax.loglog(h_arr, err_mom, "o-", color=COLORS[0], marker=MARKERS[0],
              label=r"$\|R_{\mathrm{mom}}\|_\infty$")
    ax.loglog(h_arr, err_div, "s-", color=COLORS[1], marker=MARKERS[1],
              label=r"$\|R_{\mathrm{div}}\|_\infty$")

    # Reference slopes
    ref4 = err_mom[-1] * (h_arr / h_arr[-1])**4
    ref6 = err_div[-1] * (h_arr / h_arr[-1])**6
    ax.loglog(h_arr, ref4, "--", color="gray", label=r"$O(h^4)$")
    ax.loglog(h_arr, ref6, ":", color="gray", label=r"$O(h^6)$")

    ax.set_xlabel(r"$h$")
    ax.set_ylabel(r"$L^\infty$ residual")
    ax.set_title("Kovasznay spatial convergence (CCD residual)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, OUT / "kovasznay")


def main():
    args = experiment_argparser("[12-5] Kovasznay spatial convergence").parse_args()
    if args.plot_only:
        d = load_results(NPZ)
        plot_convergence(d["results"])
        return

    print("\n=== [12-5] Kovasznay spatial convergence ===")
    results = run_convergence()

    # Print table
    print(f"\n{'N':>6} {'h':>12} {'||R_mom||∞':>12} {'order_mom':>10} {'||R_div||∞':>12} {'order_div':>10}")
    print("-" * 66)
    for r in results:
        om = r.get("order_mom", float("nan"))
        od = r.get("order_div", float("nan"))
        print(f"{r['N']:>6} {r['h']:>12.4e} {r['err_mom']:>12.4e} {om:>10.2f} {r['err_div']:>12.4e} {od:>10.2f}")

    save_results(NPZ, {"results": results})
    plot_convergence(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
