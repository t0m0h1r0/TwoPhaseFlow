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

try:
    from twophase.levelset.curvature import CurvatureCalculator
    from twophase.levelset.curvature_filter import InterfaceLimitedFilter
    _HAS_CURVATURE = True
except ImportError:
    _HAS_CURVATURE = False

try:
    from twophase.simulation.visualization.plot_fields import (
        field_with_contour, symmetric_range,
    )
    _HAS_PLOT_FIELDS = True
except ImportError:
    _HAS_PLOT_FIELDS = False

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


def _run_droplet_snapshot(rho_l, rho_g=1.0, N=64, n_steps=50):
    """Run a short static droplet simulation and return field data."""
    if not _HAS_CURVATURE:
        raise RuntimeError("CurvatureCalculator not available; cannot run droplet snapshot")

    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = 0.25 - np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = rho_g + (rho_l - rho_g) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    # CSF surface tension force
    kappa = curv_calc.compute(psi)
    kappa = np.asarray(kappa)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    SIGMA, WE = 1.0, 10.0
    f_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0; arr[-1, :] = 0
        arr[:, 0] = 0; arr[:, -1] = 0

    p = np.zeros_like(X)
    for _ in range(n_steps):
        u_star = u + dt / rho * f_x
        v_star = v + dt / rho * f_y
        wall_bc(u_star); wall_bc(v_star)

        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt

        triplet, A_shape = ppe_builder.build(rho)
        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
        rhs_vec = rhs.ravel().copy()
        rhs_vec[ppe_builder._pin_dof] = 0.0
        p = spsolve(A, rhs_vec).reshape(rho.shape)

        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

    x1d = np.linspace(0, 1, N)
    y1d = np.linspace(0, 1, N)
    return {
        "rho_ratio": rho_l / rho_g,
        "p": p, "u": u, "v": v, "psi": psi,
        "x1d": x1d, "y1d": y1d,
    }


def run_field_snapshots():
    """Run short static droplet simulations for density ratios {2,3,5,10}."""
    ratios = [2, 3, 5, 10]
    snapshots = []
    for dr in ratios:
        print(f"  Field snapshot: rho_l/rho_g = {dr} ...", flush=True)
        snap = _run_droplet_snapshot(rho_l=float(dr), rho_g=1.0, N=64, n_steps=50)
        snapshots.append(snap)
    return snapshots


def make_field_figure(snapshots):
    """2×4 panel figure: pressure (top) and velocity magnitude (bottom)."""
    if not _HAS_PLOT_FIELDS:
        print("  WARNING: plot_fields not available; skipping field figure")
        return

    apply_style()

    ratios = [s["rho_ratio"] for s in snapshots]
    n = len(snapshots)

    fig, axes = plt.subplots(2, n, figsize=(3.5 * n, 7))

    # Compute shared color ranges per row
    p_vmax = max(symmetric_range(s["p"]) for s in snapshots)
    speed_vmax = max(float(np.max(np.sqrt(s["u"] ** 2 + s["v"] ** 2)))
                     for s in snapshots)

    im_p = None
    im_v = None

    for col, snap in enumerate(snapshots):
        dr = snap["rho_ratio"]
        x1d, y1d = snap["x1d"], snap["y1d"]
        speed = np.sqrt(snap["u"] ** 2 + snap["v"] ** 2)

        # Top row: pressure
        ax_p = axes[0, col]
        im_p = field_with_contour(
            ax_p, x1d, y1d, snap["p"],
            cmap="RdBu_r",
            vmin=-p_vmax, vmax=p_vmax,
            contour_field=snap["psi"],
            contour_level=0.5,
            title=rf"$\rho_l/\rho_g = {int(dr)}$",
            xlabel="$x$",
            ylabel="$y$" if col == 0 else "",
        )
        ax_p.set_aspect("equal")

        # Bottom row: velocity magnitude (parasitic currents)
        ax_v = axes[1, col]
        im_v = field_with_contour(
            ax_v, x1d, y1d, speed,
            cmap="viridis",
            vmin=0.0, vmax=speed_vmax,
            contour_field=snap["psi"],
            contour_level=0.5,
            title="",
            xlabel="$x$",
            ylabel="$y$" if col == 0 else "",
        )
        ax_v.set_aspect("equal")

    # Row labels on leftmost column
    axes[0, 0].set_ylabel("Pressure $p$\n$y$", fontsize=10)
    axes[1, 0].set_ylabel("Speed $|\\mathbf{u}|$\n$y$", fontsize=10)

    # Shared colorbars
    if im_p is not None:
        fig.colorbar(im_p, ax=axes[0, :].tolist(), shrink=0.8, label="$p$")
    if im_v is not None:
        fig.colorbar(im_v, ax=axes[1, :].tolist(), shrink=0.8,
                     label=r"$|\mathbf{u}|$")

    plt.tight_layout()
    save_figure(fig, OUT / "density_fields",
                also_to="paper/figures/ch12_density_fields.pdf")


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

    # -- Field snapshots for density ratio visualization --
    print("\n  Field snapshots (static droplet, 50 steps each):")
    snapshots = run_field_snapshots()

    # Flatten snapshot arrays for npz storage
    snap_save = {}
    for i, snap in enumerate(snapshots):
        for k, v in snap.items():
            snap_save[f"snap_{i}_{k}"] = v
    snap_save["n_snap"] = len(snapshots)

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
        **snap_save,
    })

    make_figures(sweep, conv_2, conv_5)
    make_field_figure(snapshots)
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
        # Rebuild snapshots if present
        n_snap = int(d.get("n_snap", 0))
        if n_snap > 0:
            snap_keys = ["rho_ratio", "p", "u", "v", "psi", "x1d", "y1d"]
            snapshots = []
            for i in range(n_snap):
                snap = {}
                for k in snap_keys:
                    key = f"snap_{i}_{k}"
                    if key in d:
                        snap[k] = d[key]
                snapshots.append(snap)
            make_field_figure(snapshots)
    else:
        main()
