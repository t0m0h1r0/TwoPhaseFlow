#!/usr/bin/env python3
"""[11-33] Single vortex (LeVeque 1996) on non-uniform (interface-fitted) grid.

N=128, T=8.0, eps/h=1.5.  Compares:
  - uniform (alpha=1)
  - non-uniform alpha=2
  - non-uniform alpha=3

Grid rebuilt every ``reinit_freq`` advection steps from phi = invert_heaviside(psi).
Velocity reverses at T/2 -> shape should recover at T.

Metrics: L2(psi), L2(phi in band), area_err, mass_err.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.core.grid_remap import build_grid_remapper

import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside, invert_heaviside
from twophase.simulation.initial_conditions.velocity_fields import SingleVortex
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def run_case(N, eps_ratio, alpha_grid, reinit_freq=20):
    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha_grid)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h

    X, Y = grid.meshgrid()
    phi0_dev = xp.sqrt((X - 0.5) ** 2 + (Y - 0.75) ** 2) - 0.15
    psi0 = heaviside(xp, phi0_dev, eps)

    # Initial grid fitting for non-uniform case
    if alpha_grid > 1.0:
        grid.update_from_levelset(phi0_dev, eps, ccd=ccd)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        phi0_dev = xp.sqrt((X - 0.5) ** 2 + (Y - 0.75) ** 2) - 0.15
        psi0 = heaviside(xp, phi0_dev, eps)

    T = 8.0
    vf = SingleVortex(period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05,
                                  mass_correction=True)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                           method="split")

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    half_step = n_steps // 2

    psi = psi0.copy()
    dV = grid.cell_volumes()
    mass0 = float(xp.sum(psi * dV))

    psi_half = None   # snapshot at T/2 (most deformed)

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=step * dt)
        psi = adv.advance(psi, [u, v], dt)

        # Rebuild non-uniform grid
        if alpha_grid > 1.0 and (step + 1) % reinit_freq == 0:
            phi_cur = invert_heaviside(xp, psi, eps)
            old_coords = [c.copy() for c in grid.coords]

            M_before = float(xp.sum(psi * dV))
            grid.update_from_levelset(phi_cur, eps, ccd=ccd)

            # GPU-native remap: old_coords → new grid coords (no host transfer)
            remapper = build_grid_remapper(backend, old_coords, grid.coords)
            psi = xp.clip(remapper.remap(psi), 0.0, 1.0)

            # Mass correction on device
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

        if step + 1 == half_step:
            psi_half = backend.to_host(psi).copy()

    # Final metrics
    X_f, Y_f = grid.meshgrid()
    phi0_final = xp.sqrt((X_f - 0.5) ** 2 + (Y_f - 0.75) ** 2) - 0.15
    psi0_final = heaviside(xp, phi0_final, eps)

    dV_final = grid.cell_volumes()
    mass_err = abs(float(xp.sum(psi * dV_final)) - mass0) / mass0
    err_L2_psi = float(xp.sqrt(xp.mean((psi - psi0_final) ** 2)))

    phi_final = invert_heaviside(xp, psi, eps)
    band = xp.abs(phi0_final) < 6 * eps
    err_L2_phi = float(xp.sqrt(xp.mean((phi_final[band] - phi0_final[band]) ** 2))) \
        if bool(xp.any(band)) else float("nan")

    area0 = float(xp.sum(psi0_final >= 0.5))
    area_err = abs(float(xp.sum(psi >= 0.5)) - area0) / max(area0, 1.0)

    return {
        "N": N, "eps_ratio": eps_ratio, "alpha": alpha_grid,
        "L2_psi": err_L2_psi, "L2_phi": err_L2_phi,
        "area_err": area_err, "mass_err": mass_err,
        "psi_init": backend.to_host(psi0_final),
        "psi_half": psi_half,
        "psi_final": backend.to_host(psi),
        "X": backend.to_host(X_f), "Y": backend.to_host(Y_f),
    }


def plot_results(all_results):
    """2行×3列: 各ケースの (上) T=T/2 (最大変形), (下) T=T (復元後)."""
    n = len(all_results)
    fig, axes = plt.subplots(2, n, figsize=(4.5 * n, 8))

    titles = [r["label"] for r in all_results]
    levels = np.linspace(0, 1, 11)

    for j, r in enumerate(all_results):
        X, Y = r["X"], r["Y"]

        for row, (field, ttl) in enumerate([
            (r["psi_half"],  "T/2 (max deform)"),
            (r["psi_final"], "T (recovered)"),
        ]):
            ax = axes[row, j]
            if field is not None:
                ax.pcolormesh(X, Y, field, cmap="RdBu_r", vmin=0, vmax=1, shading="auto")
                ax.contour(X, Y, field, levels=[0.5], colors="k", linewidths=1.0)
            ax.contour(X, Y, r["psi_init"], levels=[0.5],
                       colors="gray", linewidths=0.8, linestyles="--")
            ax.set_aspect("equal")
            ax.set_title(f"{titles[j]}\n{ttl}", fontsize=9)
            ax.set_xlabel("x"); ax.set_ylabel("y")

    # Metrics table as text below
    fig.suptitle(
        "Single vortex (LeVeque 1996) — non-uniform grid comparison\n"
        r"$N=128,\ \varepsilon/h=1.5,\ T=8$",
        fontsize=11,
    )
    fig.tight_layout()
    return fig


def main():
    args = experiment_argparser("[11-33] Single vortex non-uniform").parse_args()
    N = 128
    eps_ratio = 1.5

    cases = [
        ("uniform",       1.0),
        ("non-uniform a=2", 2.0),
        ("non-uniform a=3", 3.0),
    ]
    key_map = {
        "uniform":       "uniform",
        "non-uniform a=2": "nonunif_a2",
        "non-uniform a=3": "nonunif_a3",
    }

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        print("\n" + "=" * 72)
        print(f"{'case':>20} {'L2(phi)':>10} {'area_err':>10} {'mass_err':>10}")
        print("-" * 72)
        for label, _ in cases:
            k = key_map[label]
            r = data[k]
            print(f"{label:>20} {float(r['L2_phi']):>10.3e} "
                  f"{float(r['area_err']):>10.2e} {float(r['mass_err']):>10.2e}")
        print("=" * 72)
        return

    all_results = []
    for label, alpha in cases:
        print(f"\n--- {label} ---")
        r = run_case(N, eps_ratio, alpha)
        r["label"] = label
        print(f"  L2psi={r['L2_psi']:.3e}  L2phi={r['L2_phi']:.3e}  "
              f"area={r['area_err']:.2e}  mass={r['mass_err']:.2e}")
        all_results.append(r)

    print("\n" + "=" * 72)
    print(f"{'case':>20} {'L2(phi)':>10} {'area_err':>10} {'mass_err':>10}")
    print("-" * 72)
    for r in all_results:
        print(f"{r['label']:>20} {r['L2_phi']:>10.3e} "
              f"{r['area_err']:>10.2e} {r['mass_err']:>10.2e}")
    print("=" * 72)

    save_results(OUT / "data.npz", {
        key_map[r["label"]]: {
            f: r[f] for f in (
                "alpha", "L2_psi", "L2_phi", "area_err", "mass_err",
                "psi_init", "psi_half", "psi_final", "X", "Y",
            )
        }
        for r in all_results
    })

    fig = plot_results(all_results)
    save_figure(fig, OUT / "single_vortex_nonuniform")
    print(f"Saved figure -> {OUT / 'single_vortex_nonuniform.pdf'}")


if __name__ == "__main__":
    main()
