#!/usr/bin/env python3
"""[11-21] Zalesak ε/h study: can hybrid reinit work with narrower transitions?

Tests ε/h = {1.0, 0.75, 0.5} × method = {split, hybrid} on Zalesak N=128.
Goal: find if reducing ε makes DGR safe for the narrow slot (width=0.05).
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside, invert_heaviside
from twophase.initial_conditions.velocity_fields import RigidRotation
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    """Zalesak slotted disk SDF — delegates to library."""
    from twophase.initial_conditions.shapes import ZalesakDisk
    return ZalesakDisk(center=center, radius=R, slot_width=slot_w, slot_depth=slot_h).sdf(X, Y)


_REINIT_THRESHOLD = 1.10


def _adaptive_reinit_needed(xp, psi, M_ref, h, threshold=_REINIT_THRESHOLD):
    M_cur = float(xp.sum(psi * (1.0 - psi))) * (h ** 2)
    return M_ref > 1e-15 and M_cur / M_ref > threshold


def run_zalesak_case(N, eps_ratio, method, reinit_freq=20):
    """Run single Zalesak case. Returns dict with metrics."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h
    X, Y = grid.meshgrid()

    phi0 = zalesak_sdf(X, Y)
    psi0 = heaviside(np, phi0, eps)

    T = 2 * np.pi
    vf = RigidRotation(center=(0.5, 0.5), period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05,
                                  mass_correction=True)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                           method=method)

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    mass0 = float(np.sum(psi))
    reinit_count = 0

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=0)
        psi = adv.advance(psi, [u, v], dt)
        if (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)
            reinit_count += 1

    mass_err = abs(float(np.sum(psi)) - mass0) / mass0
    err_L2 = float(np.sqrt(np.mean((psi - psi0)**2)))
    phi_final = invert_heaviside(np, psi, eps)
    band = np.abs(phi0) < 6 * eps
    err_L2_phi = float(np.sqrt(np.mean((phi_final[band] - phi0[band])**2)))
    area0 = float(np.sum(psi0 >= 0.5))
    area_err = abs(float(np.sum(psi >= 0.5)) - area0) / max(area0, 1.0)

    # Check slot integrity: sample ψ at slot center
    cx, cy = N // 2, int(0.65 * N)  # approx slot center
    slot_psi = float(psi[cy, cx]) if cy < N and cx < N else -1.0

    return {
        "N": N, "eps_ratio": eps_ratio, "method": method,
        "L2_psi": err_L2, "L2_phi": err_L2_phi,
        "area_err": area_err, "mass_err": mass_err,
        "reinits": reinit_count, "slot_psi": slot_psi,
        "psi_final": psi, "psi_init": psi0, "X": X, "Y": Y,
    }


def main():
    args = experiment_argparser("[11-21] Zalesak ε/h study").parse_args()

    N = 128
    eps_ratios = [1.0, 0.75, 0.5]
    methods = ["split", "hybrid"]

    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_comparison(d["results"])
        return

    all_results = []
    all_fields = {}

    for eps_r in eps_ratios:
        for method in methods:
            label = f"ε/h={eps_r}, {method}"
            print(f"\n--- {label} ---")
            r = run_zalesak_case(N, eps_r, method)
            print(f"  L2ψ={r['L2_psi']:.3e}, L2φ={r['L2_phi']:.3e}, "
                  f"area={r['area_err']:.2e}, mass={r['mass_err']:.2e}, "
                  f"slot_ψ={r['slot_psi']:.4f}")
            all_results.append({
                "eps_ratio": eps_r, "method": method,
                "L2_psi": r["L2_psi"], "L2_phi": r["L2_phi"],
                "area_err": r["area_err"], "mass_err": r["mass_err"],
                "slot_psi": r["slot_psi"],
            })
            key = f"psi_{eps_r}_{method}"
            all_fields[key] = r["psi_final"]
            all_fields[f"init_{eps_r}_{method}"] = r["psi_init"]

    all_fields["X"] = r["X"]
    all_fields["Y"] = r["Y"]

    save_results(OUT / "data.npz", {"results": all_results, **all_fields})
    plot_comparison(all_results, all_fields)
    print(f"\nResults saved to {OUT}")


def plot_comparison(results, fields=None):
    import matplotlib.pyplot as plt

    # Print table
    print("\n" + "=" * 80)
    print(f"{'ε/h':>6} {'method':>8} {'L2(ψ)':>10} {'L2(φ)':>10} "
          f"{'area_err':>10} {'mass_err':>10} {'slot_ψ':>8}")
    print("-" * 80)
    for r in results:
        print(f"{r['eps_ratio']:>6.2f} {r['method']:>8} {r['L2_psi']:>10.3e} "
              f"{r['L2_phi']:>10.3e} {r['area_err']:>10.2e} "
              f"{r['mass_err']:>10.2e} {r['slot_psi']:>8.4f}")
    print("=" * 80)

    if fields is None:
        return

    # 2D contour comparison: 3 rows (ε/h) × 2 cols (split, hybrid)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list(
        "phase", ["#4393c3", "#d1e5f0", "#fddbc7", "#d6604d"], N=256
    )

    eps_ratios = [1.0, 0.75, 0.5]
    methods = ["split", "hybrid"]
    fig, axes = plt.subplots(3, 2, figsize=(5.0, 7.5))

    X, Y = fields["X"], fields["Y"]
    for i, eps_r in enumerate(eps_ratios):
        for j, method in enumerate(methods):
            ax = axes[i, j]
            key = f"psi_{eps_r}_{method}"
            init_key = f"init_{eps_r}_{method}"
            if key not in fields:
                ax.set_visible(False)
                continue
            psi = fields[key]
            psi_init = fields[init_key]
            ax.pcolormesh(X, Y, psi, cmap=cmap, vmin=0, vmax=1,
                          shading="gouraud", rasterized=True)
            ax.contour(X, Y, psi, levels=[0.5], colors="k", linewidths=0.8)
            ax.contour(X, Y, psi_init, levels=[0.5],
                       colors="k", linewidths=0.5, linestyles="dashed")
            ax.set_aspect("equal")
            ax.set_xlim(0.2, 0.8); ax.set_ylim(0.45, 1.0)
            ax.tick_params(labelsize=6)
            if i == 0:
                ax.set_title(method, fontsize=9)
            if j == 0:
                ax.set_ylabel(f"ε/h={eps_r}", fontsize=9)

    fig.tight_layout()
    save_figure(fig, OUT / "zalesak_eps_study")


if __name__ == "__main__":
    main()
