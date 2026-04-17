#!/usr/bin/env python3
"""[11-36] Single vortex (LeVeque 1996) — ξ-space eps comparison.

Tests eps_g_cells and eps_xi_cells against the legacy eps_g_factor path.
N=128, T=8.0, eps/h=1.5, alpha_grid in {1, 2, 3}.

Cases:
  (a) uniform baseline
  (b) legacy alpha=2 (eps_g_factor=2)
  (c) xi-space: alpha=2, eps_g_cells=4
  (d) xi-space full: alpha=2, eps_g_cells=4, eps_xi_cells=1.5
  (e) xi-space full, alpha=3: alpha=3, eps_g_cells=4, eps_xi_cells=1.5

Velocity reverses at T/2 -> shape should recover at T.
Metrics: L2(psi), L2(phi in band), area_err, mass_err.
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
from twophase.simulation.initial_conditions.velocity_fields import SingleVortex
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)

apply_style()
OUT = experiment_dir(__file__)


def _make_eps_field(xp, grid, eps_xi_cells, eps_scalar):
    """eps(x) = eps_xi_cells * max(hx, hy) or scalar fallback."""
    if eps_xi_cells is None:
        return eps_scalar
    hx = xp.asarray(grid.h[0])[:, None]
    hy = xp.asarray(grid.h[1])[None, :]
    return eps_xi_cells * xp.maximum(hx, hy)


def run_case(N, eps_ratio, alpha_grid, reinit_freq=20,
             eps_g_cells=None, eps_xi_cells=None):
    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0),
                    alpha_grid=alpha_grid, eps_g_cells=eps_g_cells)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h
    eps_field = _make_eps_field(xp, grid, eps_xi_cells, eps)

    X, Y = grid.meshgrid()
    phi0_dev = xp.sqrt((X - 0.5) ** 2 + (Y - 0.75) ** 2) - 0.15
    psi0 = heaviside(xp, phi0_dev, eps_field)

    # Initial grid fitting for non-uniform case
    if alpha_grid > 1.0:
        grid.update_from_levelset(psi0, eps, ccd=ccd)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        eps_field = _make_eps_field(xp, grid, eps_xi_cells, eps)
        phi0_dev = xp.sqrt((X - 0.5) ** 2 + (Y - 0.75) ** 2) - 0.15
        psi0 = heaviside(xp, phi0_dev, eps_field)

    T = 8.0
    vf = SingleVortex(period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05,
                                  mass_correction=True)
    eps_reinit = float(xp.min(xp.asarray(eps_field))) if eps_xi_cells is not None else eps
    reinit = Reinitializer(backend, grid, ccd, eps_reinit, n_steps=4,
                           bc="zero", method="split")

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    half_step = n_steps // 2

    psi = psi0.copy()
    dV = grid.cell_volumes()
    mass0 = float(xp.sum(psi * dV))
    psi_half = None

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=step * dt)
        psi = adv.advance(psi, [u, v], dt)

        # Rebuild non-uniform grid
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
            eps_field = _make_eps_field(xp, grid, eps_xi_cells, eps)
            eps_reinit = float(xp.min(xp.asarray(eps_field))) if eps_xi_cells is not None else eps
            reinit = Reinitializer(backend, grid, ccd, eps_reinit, n_steps=4,
                                   bc="zero", method="split")
            X, Y = grid.meshgrid()

        if (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)

        if step + 1 == half_step:
            psi_half = backend.to_host(psi).copy()

    # Final metrics
    X_f, Y_f = grid.meshgrid()
    phi0_final = xp.sqrt((X_f - 0.5) ** 2 + (Y_f - 0.75) ** 2) - 0.15
    psi0_final = heaviside(xp, phi0_final, eps_field)

    dV_final = grid.cell_volumes()
    mass_err = abs(float(xp.sum(psi * dV_final)) - mass0) / mass0
    err_L2_psi = float(xp.sqrt(xp.mean((psi - psi0_final) ** 2)))

    phi_final = invert_heaviside(xp, psi, eps_field)
    band = xp.abs(phi0_final) < 6 * eps_field
    err_L2_phi = float(xp.sqrt(xp.mean((phi_final[band] - phi0_final[band]) ** 2))) \
        if bool(xp.any(band)) else float("nan")

    area0 = float(xp.sum(psi0_final >= 0.5))
    area_err = abs(float(xp.sum(psi >= 0.5)) - area0) / max(area0, 1.0)

    return {
        "N": N, "eps_ratio": eps_ratio, "alpha": alpha_grid,
        "eps_g_cells": eps_g_cells if eps_g_cells is not None else 0.0,
        "eps_xi_cells": eps_xi_cells if eps_xi_cells is not None else 0.0,
        "L2_psi": err_L2_psi, "L2_phi": err_L2_phi,
        "area_err": area_err, "mass_err": mass_err,
        "psi_init": backend.to_host(psi0_final),
        "psi_half": psi_half,
        "psi_final": backend.to_host(psi),
        "X": backend.to_host(X_f), "Y": backend.to_host(Y_f),
    }


# ── Case definitions ──────────────────────────────────────────────────────
CASES = [
    # (label,              alpha, eps_g_cells, eps_xi_cells)
    ("uniform",             1.0,  None,  None),
    ("legacy a=2",          2.0,  None,  None),
    ("xi-gc4 a=2",          2.0,  4.0,   None),
    ("xi-gc4+xc1.5 a=2",   2.0,  4.0,   1.5),
    ("xi-gc4+xc1.5 a=3",   3.0,  4.0,   1.5),
]
KEY_MAP = {
    "uniform":            "uniform",
    "legacy a=2":         "legacy_a2",
    "xi-gc4 a=2":         "xi_gc4_a2",
    "xi-gc4+xc1.5 a=2":  "xi_gc4_xc15_a2",
    "xi-gc4+xc1.5 a=3":  "xi_gc4_xc15_a3",
}


def plot_results(all_results):
    """2 rows x N cols: (top) T/2 max deformation, (bottom) T recovered."""
    n = len(all_results)
    fig, axes = plt.subplots(2, n, figsize=(4.0 * n, 8))

    for j, r in enumerate(all_results):
        X, Y = r["X"], r["Y"]
        for row, (field, ttl) in enumerate([
            (r["psi_half"],  "T/2 (max deform)"),
            (r["psi_final"], "T (recovered)"),
        ]):
            ax = axes[row, j]
            if field is not None:
                ax.pcolormesh(X, Y, field, cmap="RdBu_r", vmin=0, vmax=1,
                              shading="auto")
                ax.contour(X, Y, field, levels=[0.5], colors="k",
                           linewidths=1.0)
            ax.contour(X, Y, r["psi_init"], levels=[0.5],
                       colors="gray", linewidths=0.8, linestyles="--")
            ax.set_aspect("equal")
            ax.set_title(f"{r['label']}\n{ttl}", fontsize=8)
            ax.set_xlabel("x"); ax.set_ylabel("y")

    fig.suptitle(
        r"Single vortex (LeVeque 1996) — $\xi$-space eps comparison"
        "\n$N=128,\\ T=8$",
        fontsize=10,
    )
    fig.tight_layout()
    return fig


def main():
    args = experiment_argparser("[11-36] Single vortex xi-space eps").parse_args()
    N = 128
    eps_ratio = 1.5

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        print("\n" + "=" * 80)
        print(f"{'case':>22} {'L2(psi)':>10} {'L2(phi)':>10} {'area_err':>10} {'mass_err':>10}")
        print("-" * 80)
        for label, *_ in CASES:
            k = KEY_MAP[label]
            r = data[k]
            print(f"{label:>22} {float(r['L2_psi']):>10.3e} {float(r['L2_phi']):>10.3e} "
                  f"{float(r['area_err']):>10.2e} {float(r['mass_err']):>10.2e}")
        print("=" * 80)
        return

    all_results = []
    for label, alpha, gc, xc in CASES:
        print(f"\n--- {label} ---")
        r = run_case(N, eps_ratio, alpha, eps_g_cells=gc, eps_xi_cells=xc)
        r["label"] = label
        print(f"  L2psi={r['L2_psi']:.3e}  L2phi={r['L2_phi']:.3e}  "
              f"area={r['area_err']:.2e}  mass={r['mass_err']:.2e}")
        all_results.append(r)

    print("\n" + "=" * 80)
    print(f"{'case':>22} {'L2(psi)':>10} {'L2(phi)':>10} {'area_err':>10} {'mass_err':>10}")
    print("-" * 80)
    for r in all_results:
        print(f"{r['label']:>22} {r['L2_psi']:>10.3e} {r['L2_phi']:>10.3e} "
              f"{r['area_err']:>10.2e} {r['mass_err']:>10.2e}")
    print("=" * 80)

    save_results(OUT / "data.npz", {
        KEY_MAP[r["label"]]: {
            f: r[f] for f in (
                "alpha", "eps_g_cells", "eps_xi_cells",
                "L2_psi", "L2_phi", "area_err", "mass_err",
                "psi_init", "psi_half", "psi_final", "X", "Y",
            )
        }
        for r in all_results
    })

    fig = plot_results(all_results)
    save_figure(fig, OUT / "single_vortex_xi_eps")
    print(f"Saved figure -> {OUT / 'single_vortex_xi_eps.pdf'}")


if __name__ == "__main__":
    main()
