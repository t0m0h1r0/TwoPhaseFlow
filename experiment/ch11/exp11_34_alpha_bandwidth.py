#!/usr/bin/env python3
"""[11-34] Alpha bandwidth constraint: eps_g_factor sweep for non-uniform grid.

Hypothesis: the fine-grid bandwidth W_fine ~ eps_g_factor * eps must exceed
the interface displacement delta_x = |u_max| * reinit_freq * dt between
grid rebuilds.  Current eps_g_factor=2.0 gives W_fine << delta_x.

Sweeps eps_g_factor = [1.0, 2.0, 4.0, 6.0, 8.0] with alpha=2, N=128,
eps_ratio=0.5, reinit_freq=20 to find the threshold.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt
from twophase.core.grid_remap import build_grid_remapper
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside, invert_heaviside
from twophase.simulation.initial_conditions.velocity_fields import RigidRotation
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS,
)

apply_style()
OUT = experiment_dir(__file__)


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    from twophase.simulation.initial_conditions.shapes import ZalesakDisk
    return ZalesakDisk(center=center, radius=R, slot_width=slot_w, slot_depth=slot_h).sdf(X, Y)


def run_case(N, eps_ratio, alpha_grid, eps_g_factor, reinit_freq=20):
    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0),
                    alpha_grid=alpha_grid, eps_g_factor=eps_g_factor)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h
    X, Y = grid.meshgrid()

    X_h, Y_h = backend.to_host(X), backend.to_host(Y)
    phi0 = xp.asarray(zalesak_sdf(X_h, Y_h))
    psi0 = heaviside(xp, phi0, eps)

    # Initial grid fitting
    if alpha_grid > 1.0:
        grid.update_from_levelset(psi0, eps, ccd=ccd)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        X_h, Y_h = backend.to_host(X), backend.to_host(Y)
        phi0 = xp.asarray(zalesak_sdf(X_h, Y_h))
        psi0 = heaviside(xp, phi0, eps)

    # Measure fine-grid bandwidth after initial fitting
    eps_g = eps_g_factor * eps
    phi_host = np.asarray(backend.to_host(invert_heaviside(xp, psi0, eps)))
    W_fine_cells = []  # per-axis fine-region width in uniform-cell units
    for ax in range(2):
        axes_other = tuple(a for a in range(2) if a != ax)
        phi_1d = np.min(np.abs(phi_host), axis=axes_other)
        # Fine region: where indicator > 1/e (half-max of Gaussian)
        n_fine = np.sum(phi_1d < eps_g)
        W_fine_cells.append(n_fine)

    T = 2 * np.pi
    vf = RigidRotation(center=(0.5, 0.5), period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05,
                                  mass_correction=True)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                           method="split")

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    dV = grid.cell_volumes()
    mass0 = float(xp.sum(psi * dV))

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=0)
        psi = adv.advance(psi, [u, v], dt)

        if alpha_grid > 1.0 and (step + 1) % reinit_freq == 0:
            old_coords = [c.copy() for c in grid.coords]
            M_before = float(xp.sum(psi * dV))
            grid.update_from_levelset(psi, eps, ccd=ccd)

            remapper = build_grid_remapper(backend, old_coords, grid.coords)
            psi = xp.clip(remapper.remap(psi), 0.0, 1.0)

            dV = grid.cell_volumes()
            M_after = float(xp.sum(psi * dV))
            w = 4.0 * psi * (1.0 - psi)
            W = float(xp.sum(w * dV))
            if W > 1e-12:
                psi = xp.clip(psi + ((M_before - M_after) / W) * w, 0.0, 1.0)

            ccd = CCDSolver(grid, backend, bc_type="wall")
            adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                          eps_d=0.05, mass_correction=True)
            reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4,
                                   bc="zero", method="split")
            X, Y = grid.meshgrid()

        if (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)

    # Final metrics
    X, Y = grid.meshgrid()
    X_h, Y_h = backend.to_host(X), backend.to_host(Y)
    phi0_final = xp.asarray(zalesak_sdf(X_h, Y_h))
    psi0_final = heaviside(xp, phi0_final, eps)

    dV_final = grid.cell_volumes()
    mass_err = abs(float(xp.sum(psi * dV_final)) - mass0) / mass0
    err_L2 = float(xp.sqrt(xp.mean((psi - psi0_final)**2)))
    phi_final = invert_heaviside(xp, psi, eps)
    band = xp.abs(phi0_final) < 6 * eps
    err_L2_phi = float(xp.sqrt(xp.mean((phi_final[band] - phi0_final[band])**2))) \
        if bool(xp.any(band)) else float('nan')
    area0 = float(xp.sum(psi0_final >= 0.5))
    area_err = abs(float(xp.sum(psi >= 0.5)) - area0) / max(area0, 1.0)

    # Interface displacement estimate
    u_max = 0.5  # max velocity for rigid rotation at r=0.5 from center
    delta_x = u_max * reinit_freq * dt
    W_fine_phys = 2.0 * eps_g  # physical half-width (Gaussian 1/e width)

    return {
        "N": N, "eps_ratio": eps_ratio, "alpha": alpha_grid,
        "eps_g_factor": eps_g_factor,
        "L2_psi": err_L2, "L2_phi": err_L2_phi,
        "area_err": area_err, "mass_err": mass_err,
        "W_fine_phys": W_fine_phys,
        "W_fine_cells": W_fine_cells,
        "delta_x": delta_x,
        "bandwidth_ratio": W_fine_phys / max(delta_x, 1e-30),
        "psi_final": backend.to_host(psi),
        "psi_init": backend.to_host(psi0_final),
        "X": backend.to_host(X), "Y": backend.to_host(Y),
    }


def run_uniform_baseline(N, eps_ratio):
    """Run uniform case for reference."""
    return run_case(N, eps_ratio, alpha_grid=1.0, eps_g_factor=2.0)


def main():
    args = experiment_argparser("[11-34] Alpha bandwidth sweep").parse_args()
    N = 128
    eps_ratio = 0.5
    alpha = 2.0

    eps_g_factors = [1.0, 2.0, 4.0, 6.0, 8.0]

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        print("\n" + "=" * 80)
        print(f"{'eps_g_factor':>12} {'W_fine/δx':>10} {'area_err':>10} "
              f"{'mass_err':>10} {'L2(φ)':>10}")
        print("-" * 80)
        for egf in eps_g_factors:
            k = f"egf_{egf:.1f}"
            if k in data:
                r = data[k]
                print(f"{egf:>12.1f} {float(r['bandwidth_ratio']):>10.2f} "
                      f"{float(r['area_err']):>10.3e} "
                      f"{float(r['mass_err']):>10.2e} "
                      f"{float(r['L2_phi']):>10.3e}")
        if "uniform" in data:
            u = data["uniform"]
            print(f"{'uniform':>12} {'---':>10} {float(u['area_err']):>10.3e} "
                  f"{float(u['mass_err']):>10.2e} {float(u['L2_phi']):>10.3e}")
        print("=" * 80)
        return

    all_results = []

    # Uniform baseline
    print("\n--- uniform baseline ---")
    r_uni = run_uniform_baseline(N, eps_ratio)
    print(f"  area_err={r_uni['area_err']:.3e}  mass_err={r_uni['mass_err']:.2e}")
    all_results.append({"label": "uniform", **r_uni})

    # eps_g_factor sweep
    for egf in eps_g_factors:
        print(f"\n--- alpha={alpha}, eps_g_factor={egf:.1f} ---")
        r = run_case(N, eps_ratio, alpha, egf)
        print(f"  W_fine/delta_x={r['bandwidth_ratio']:.2f}  "
              f"area_err={r['area_err']:.3e}  mass_err={r['mass_err']:.2e}  "
              f"L2phi={r['L2_phi']:.3e}")
        all_results.append({"label": f"egf={egf:.1f}", **r})

    # Summary table
    print("\n" + "=" * 80)
    print(f"{'case':>20} {'W_fine/δx':>10} {'area_err':>10} {'mass_err':>10} {'L2(φ)':>10}")
    print("-" * 80)
    for r in all_results:
        bw = f"{r['bandwidth_ratio']:.2f}" if r['alpha'] > 1.0 else "---"
        print(f"{r['label']:>20} {bw:>10} {r['area_err']:>10.3e} "
              f"{r['mass_err']:>10.2e} {r['L2_phi']:>10.3e}")
    print("=" * 80)

    # Save results
    save_dict = {"uniform": {
        f: r_uni[f] for f in ("alpha", "L2_psi", "L2_phi", "area_err", "mass_err",
                               "bandwidth_ratio", "W_fine_phys", "delta_x",
                               "psi_final", "psi_init", "X", "Y")
    }}
    for r in all_results[1:]:  # skip uniform
        k = f"egf_{r['eps_g_factor']:.1f}"
        save_dict[k] = {
            f: r[f] for f in ("alpha", "eps_g_factor", "L2_psi", "L2_phi",
                               "area_err", "mass_err", "bandwidth_ratio",
                               "W_fine_phys", "delta_x",
                               "psi_final", "psi_init", "X", "Y")
        }
    save_results(OUT / "data.npz", save_dict)

    # --- Visualization ---
    nonunif = [r for r in all_results if r["alpha"] > 1.0]
    egf_vals = [r["eps_g_factor"] for r in nonunif]
    area_errs = [r["area_err"] for r in nonunif]
    bw_ratios = [r["bandwidth_ratio"] for r in nonunif]

    fig, ax1 = plt.subplots(figsize=(7, 5))

    # Left axis: area_err
    c1 = COLORS[0]
    ax1.semilogy(egf_vals, area_errs, "o-", color=c1, label="area_err (non-uniform)")
    ax1.axhline(r_uni["area_err"], color="gray", ls="--", lw=0.8,
                label=f"uniform baseline ({r_uni['area_err']:.2e})")
    ax1.set_xlabel(r"$\varepsilon_g$ factor")
    ax1.set_ylabel("area_err", color=c1)
    ax1.tick_params(axis="y", labelcolor=c1)

    # Right axis: bandwidth ratio
    ax2 = ax1.twinx()
    c2 = COLORS[1]
    ax2.plot(egf_vals, bw_ratios, "s--", color=c2, label=r"$W_\mathrm{fine}/\delta x$")
    ax2.axhline(1.0, color=c2, ls=":", lw=0.8, alpha=0.5)
    ax2.set_ylabel(r"$W_\mathrm{fine} / \delta x$", color=c2)
    ax2.tick_params(axis="y", labelcolor=c2)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="center right")

    ax1.set_title(
        r"Non-uniform grid: $\varepsilon_g$ factor sweep"
        f"\n(N={N}, eps/h={eps_ratio}, alpha={alpha}, reinit_freq=20)",
        fontsize=10,
    )
    fig.tight_layout()
    save_figure(fig, OUT / "alpha_bandwidth")
    print(f"\nSaved figure -> {OUT / 'alpha_bandwidth.pdf'}")

    # Contour comparison for selected cases
    sel = [r for r in all_results if r["label"] in ("uniform", "egf=2.0", "egf=6.0", "egf=8.0")]
    if len(sel) >= 2:
        n_sel = len(sel)
        fig2, axes = plt.subplots(1, n_sel, figsize=(4.5 * n_sel, 4.5))
        if n_sel == 1:
            axes = [axes]
        for ax, r in zip(axes, sel):
            X, Y = r["X"], r["Y"]
            ax.pcolormesh(X, Y, r["psi_final"], cmap="RdBu_r", vmin=0, vmax=1,
                          shading="auto")
            ax.contour(X, Y, r["psi_init"], levels=[0.5], colors="gray",
                       linewidths=0.8, linestyles="--")
            ax.contour(X, Y, r["psi_final"], levels=[0.5], colors="k",
                       linewidths=1.2)
            ax.set_aspect("equal")
            bw = f"W/dx={r['bandwidth_ratio']:.1f}" if r['alpha'] > 1.0 else "uniform"
            ax.set_title(f"{r['label']}\narea={r['area_err']:.2e}  {bw}", fontsize=9)
        fig2.suptitle("Zalesak 1-rev contour comparison", fontsize=10)
        fig2.tight_layout()
        save_figure(fig2, OUT / "alpha_bandwidth_contours")
        print(f"Saved figure -> {OUT / 'alpha_bandwidth_contours.pdf'}")


if __name__ == "__main__":
    main()
