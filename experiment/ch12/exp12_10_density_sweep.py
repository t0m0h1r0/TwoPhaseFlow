#!/usr/bin/env python3
"""exp12_10  Density ratio limit of smoothed Heaviside PPE.

Paper ref: SS12.5.1-2

MMS test: manufactured solution p* = sin(pi*x)*sin(pi*y) on [0,1]^2 with
circular interface R=0.25.  Density field uses smoothed Heaviside
(eps = 1.5*h).  The variable-coefficient PPE matrix A is built via
PPEBuilder, and the round-trip error ||spsolve(A, A @ p*) - p*||_inf
is measured as a function of density ratio rho_l/rho_g.

Sweep
-----
  Density ratios: 2, 5, 10, 20, 50, 100  (N = 64)
  Grid convergence: N = 16, 32, 64, 128  at rho = 2 and rho = 5

Usage
-----
  python experiment/ch12/exp12_10_density_sweep.py
  python experiment/ch12/exp12_10_density_sweep.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.levelset.heaviside import heaviside
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure, COLORS, MARKERS,
)

OUT = experiment_dir(__file__, "10_density_sweep")

R = 0.25  # interface radius


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE: nabla . [(1/rho) nabla p] = rhs."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run_mms(N, rho_l, rho_g=1.0):
    """MMS round-trip test at given N and density ratio.

    Returns L-inf error of the PPE round-trip.
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ppe_builder = PPEBuilder(backend, grid, bc_type='dirichlet')

    X, Y = grid.meshgrid()

    # Manufactured solution
    p_star = np.sin(np.pi * X) * np.sin(np.pi * Y)

    # Density field via smoothed Heaviside
    phi = R - np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = rho_g + (rho_l - rho_g) * psi

    # Build PPE matrix
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

    # Forward: rhs = A @ p_star
    p_star_vec = p_star.ravel().copy()
    rhs_vec = A @ p_star_vec

    # Pin DOF
    rhs_vec[ppe_builder._pin_dof] = 0.0
    p_star_vec[ppe_builder._pin_dof] = 0.0

    # Solve
    p_computed = spsolve(A, rhs_vec).reshape(p_star.shape)

    # Error (interior only, skip boundary)
    err = float(np.max(np.abs(p_computed - p_star)))

    cond_est = float(np.max(np.abs(rho)) / np.min(np.abs(rho)))

    return {
        "N": N,
        "h": h,
        "rho_ratio": rho_l / rho_g,
        "linf_err": err,
        "cond_est": cond_est,
    }


def run_density_sweep():
    """Sweep density ratio at fixed N=64."""
    ratios = [2, 5, 10, 20, 50, 100]
    results = []
    for dr in ratios:
        r = run_mms(64, rho_l=float(dr), rho_g=1.0)
        results.append(r)
    return results


def run_grid_convergence(rho_l):
    """Grid convergence at fixed density ratio."""
    Ns = [16, 32, 64, 128]
    results = []
    for N in Ns:
        r = run_mms(N, rho_l=rho_l, rho_g=1.0)
        results.append(r)
    return results


def make_figures(sweep, conv_2, conv_5):
    """Generate density sweep and convergence plots."""
    apply_style()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # -- Left: L-inf error vs density ratio --
    ax = axes[0]
    ratios = [r["rho_ratio"] for r in sweep]
    errs = [r["linf_err"] for r in sweep]
    ax.semilogy(ratios, errs, "o-", color=COLORS[0], linewidth=1.5,
                markersize=7, label=r"$\|p - p^*\|_\infty$")
    ax.set_xlabel(r"Density ratio $\rho_l / \rho_g$")
    ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("PPE Round-Trip Error vs Density Ratio ($N=64$)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # -- Right: Grid convergence for rho=2 and rho=5 --
    ax = axes[1]
    for label, conv, color, marker in [
        (r"$\rho_l/\rho_g = 2$", conv_2, COLORS[0], MARKERS[0]),
        (r"$\rho_l/\rho_g = 5$", conv_5, COLORS[1], MARKERS[1]),
    ]:
        hs = [r["h"] for r in conv]
        errs = [r["linf_err"] for r in conv]
        ax.loglog(hs, errs, f"{marker}-", color=color, linewidth=1.5,
                  markersize=7, label=label)

    # Reference slope
    h_ref = np.array([conv_2[0]["h"], conv_2[-1]["h"]])
    ax.loglog(h_ref, conv_2[0]["linf_err"] * (h_ref / h_ref[0]) ** 2,
              "k--", alpha=0.4, label=r"$O(h^2)$")
    ax.set_xlabel("Grid spacing $h$")
    ax.set_ylabel(r"$L_\infty$ error")
    ax.set_title("Grid Convergence")
    ax.legend()
    ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()

    plt.tight_layout()
    save_figure(fig, OUT / "density_sweep.pdf")


def main():
    print("\n" + "=" * 70)
    print("  exp12_10  Density Ratio Sweep (MMS round-trip)")
    print("=" * 70 + "\n")

    # -- Density sweep --
    print("  Density sweep (N=64):")
    print(f"  {'rho_l/rho_g':>12} | {'L_inf error':>12}")
    print("  " + "-" * 30)
    sweep = run_density_sweep()
    for r in sweep:
        print(f"  {r['rho_ratio']:>12.0f} | {r['linf_err']:>12.4e}")

    # -- Grid convergence --
    for rho_l in [2, 5]:
        print(f"\n  Grid convergence (rho_l/rho_g = {rho_l}):")
        print(f"  {'N':>5} | {'h':>10} | {'L_inf error':>12}")
        print("  " + "-" * 35)
        conv = run_grid_convergence(float(rho_l))
        for r in conv:
            print(f"  {r['N']:>5} | {r['h']:>10.5f} | {r['linf_err']:>12.4e}")
        # Convergence rates
        for i in range(1, len(conv)):
            r0, r1 = conv[i - 1], conv[i]
            if r1["linf_err"] > 0 and r0["linf_err"] > 0:
                rate = np.log(r0["linf_err"] / r1["linf_err"]) / np.log(
                    r0["h"] / r1["h"]
                )
                print(f"    N={r0['N']}-->{r1['N']}: rate = {rate:.2f}")

    conv_2 = run_grid_convergence(2.0)
    conv_5 = run_grid_convergence(5.0)

    # Save
    save_results(OUT / "density_sweep.npz", {
        "sweep": {f"r{i}_{k}": v for i, r in enumerate(sweep)
                  for k, v in r.items()},
        "conv_2": {f"r{i}_{k}": v for i, r in enumerate(conv_2)
                   for k, v in r.items()},
        "conv_5": {f"r{i}_{k}": v for i, r in enumerate(conv_5)
                   for k, v in r.items()},
        "n_sweep": len(sweep),
        "n_conv": len(conv_2),
    })

    make_figures(sweep, conv_2, conv_5)
    print(f"\n  All results saved to {OUT}")


def _rebuild_list(data, prefix, n):
    """Rebuild list-of-dicts from flattened save_results format."""
    keys = ["N", "h", "rho_ratio", "linf_err", "cond_est"]
    results = []
    for i in range(n):
        r = {}
        for k in keys:
            full = f"{prefix}__r{i}_{k}"
            if full in data:
                r[k] = data[full]
            else:
                r[k] = float(data.get(f"r{i}_{k}", 0))
        results.append(r)
    return results


if __name__ == "__main__":
    args = experiment_argparser("Density ratio sweep (MMS)").parse_args()

    if args.plot_only:
        d = load_results(OUT / "density_sweep.npz")
        n_sweep = int(d["n_sweep"])
        n_conv = int(d["n_conv"])
        sweep = _rebuild_list(d, "sweep", n_sweep)
        conv_2 = _rebuild_list(d, "conv_2", n_conv)
        conv_5 = _rebuild_list(d, "conv_5", n_conv)
        make_figures(sweep, conv_2, conv_5)
    else:
        main()
