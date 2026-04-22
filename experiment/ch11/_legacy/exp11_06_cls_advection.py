#!/usr/bin/env python3
"""[11-6] CLS advection and reinitialization accuracy.

Validates: Ch3, Ch7 -- DCCD advection, reinitialization, mass conservation.

Tests:
  (a) Zalesak slotted disk: rigid rotation 1 full revolution
  (b) Single vortex (LeVeque 1996): deform + time-reverse

Expected: Mass conservation O(10^-5) at N=256; shape recovery improves with N.
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
from twophase.simulation.initial_conditions.velocity_fields import RigidRotation, SingleVortex
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    """Zalesak slotted disk SDF — delegates to library."""
    from twophase.simulation.initial_conditions.shapes import ZalesakDisk
    return ZalesakDisk(center=center, radius=R, slot_width=slot_w, slot_depth=slot_h).sdf(X, Y)


_REINIT_THRESHOLD = 1.10   # adaptive reinit trigger: M(τ)/M_ref > θ (§7b)


def _adaptive_reinit_needed(xp, psi, M_ref, h, threshold=_REINIT_THRESHOLD):
    """Check if reinitialization is needed based on volume monitor M(τ)."""
    M_cur = float(xp.sum(psi * (1.0 - psi))) * (h ** 2)
    return M_ref > 1e-15 and M_cur / M_ref > threshold


def run_zalesak(Ns=[64, 128, 256], save_fields_N=128):
    backend = Backend()
    xp = backend.xp
    results = []
    fields = {}
    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        eps = 1.0 * h
        X, Y = grid.meshgrid()

        phi0 = zalesak_sdf(X, Y)
        psi0 = heaviside(xp, phi0, eps)

        T = 2 * np.pi
        vf = RigidRotation(center=(0.5, 0.5), period=T)
        adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05, mass_correction=True)
        reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                               method='hybrid')

        dt = 0.45 / N
        n_steps = int(T / dt); dt = T / n_steps
        psi = psi0.copy()
        mass0 = float(xp.sum(psi))
        M_ref = float(xp.sum(psi * (1.0 - psi))) * (h ** 2)
        reinit_count = 0

        # Save fields for 2D visualization at selected resolution
        save_2d = (N == save_fields_N)
        if save_2d:
            fields["zalesak_init"] = backend.to_host(psi0).copy()
            fields["zalesak_X"] = backend.to_host(X).copy()
            fields["zalesak_Y"] = backend.to_host(Y).copy()

        for step in range(n_steps):
            u, v = vf.compute(X, Y, t=0)
            psi = adv.advance(psi, [u, v], dt)
            # Fixed-frequency hybrid reinit for Zalesak (sharp slot geometry
            # requires regular profile maintenance; adaptive trigger
            # M(τ)/M_ref cannot detect local corner degradation).
            # Hybrid = comp-diff (shape) + DGR (thickness): ε_eff/ε ≈ 1.02.
            if (step + 1) % 20 == 0:
                psi = reinit.reinitialize(psi)
                reinit_count += 1
            # Save at quarter and half revolution
            if save_2d and step + 1 == n_steps // 4:
                fields["zalesak_quarter"] = backend.to_host(psi).copy()
            if save_2d and step + 1 == n_steps // 2:
                fields["zalesak_half"] = backend.to_host(psi).copy()

        if save_2d:
            fields["zalesak_final"] = backend.to_host(psi).copy()

        mass_err = abs(float(xp.sum(psi)) - mass0) / mass0
        err_L2 = float(xp.sqrt(xp.mean((psi - psi0)**2)))
        phi_final = invert_heaviside(xp, psi, eps)
        band = xp.abs(phi0) < 6 * eps
        err_L2_phi = float(xp.sqrt(xp.mean((phi_final[band] - phi0[band])**2)))
        area0 = float(xp.sum(psi0 >= 0.5))
        area_err = abs(float(xp.sum(psi >= 0.5)) - area0) / max(area0, 1.0)
        results.append({"N": N, "h": 1.0/N, "L2": err_L2, "L2_phi": err_L2_phi,
                         "area_err": area_err, "mass_err": mass_err})
        print(f"  N={N:>4}: L2ψ={err_L2:.3e}, L2φ={err_L2_phi:.3e}, area={area_err:.2e}, reinits={reinit_count}")
    return results, fields


def run_single_vortex(Ns=[64, 128, 256], save_fields_N=128):
    backend = Backend()
    xp = backend.xp
    results = []
    fields = {}
    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        eps = 1.0 * h
        X, Y = grid.meshgrid()

        phi0 = xp.sqrt((X - 0.5)**2 + (Y - 0.75)**2) - 0.15
        psi0 = heaviside(xp, phi0, eps)
        adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05, mass_correction=True)
        reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                               method='hybrid')

        T = 8.0; dt = 0.45 / N; n_steps = int(T / dt); dt = T / n_steps
        psi = psi0.copy(); mass0 = float(xp.sum(psi))
        M_ref = float(xp.sum(psi * (1.0 - psi))) * (h ** 2)
        reinit_count = 0

        save_2d = (N == save_fields_N)
        if save_2d:
            fields["vortex_init"] = backend.to_host(psi0).copy()
            fields["vortex_X"] = backend.to_host(X).copy()
            fields["vortex_Y"] = backend.to_host(Y).copy()

        for step in range(n_steps):
            u, v = SingleVortex(period=T).compute(X, Y, t=step * dt)
            psi = adv.advance(psi, [u, v], dt)
            # Adaptive hybrid reinit trigger (§7b eq:adaptive_reinit_trigger)
            # Hybrid = comp-diff (shape) + DGR (thickness): ε_eff/ε ≈ 1.02.
            if _adaptive_reinit_needed(xp, psi, M_ref, h):
                psi = reinit.reinitialize(psi)
                M_ref = float(xp.sum(psi * (1.0 - psi))) * (h ** 2)
                reinit_count += 1
            # Save at max deformation (t = T/2)
            if save_2d and step + 1 == n_steps // 2:
                fields["vortex_mid"] = backend.to_host(psi).copy()

        if save_2d:
            fields["vortex_final"] = backend.to_host(psi).copy()

        mass_err = abs(float(xp.sum(psi)) - mass0) / mass0
        err_L2 = float(xp.sqrt(xp.mean((psi - psi0)**2)))
        phi_final = invert_heaviside(xp, psi, eps)
        band = xp.abs(phi0) < 6 * eps
        err_L2_phi = float(xp.sqrt(xp.mean((phi_final[band] - phi0[band])**2)))
        area0 = float(xp.sum(psi0 >= 0.5))
        area_err = abs(float(xp.sum(psi >= 0.5)) - area0) / max(area0, 1.0)
        results.append({"N": N, "h": 1.0/N, "L2": err_L2, "L2_phi": err_L2_phi,
                         "area_err": area_err, "mass_err": mass_err})
        print(f"  N={N:>4}: L2ψ={err_L2:.3e}, L2φ={err_L2_phi:.3e}, area={area_err:.2e}, reinits={reinit_count}")
    return results, fields


def plot_all(zalesak, vortex):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    for ax, res, title in [(axes[0], zalesak, "(a) Zalesak"), (axes[1], vortex, "(b) Single vortex")]:
        h = [r["h"] for r in res]
        ax.loglog(h, [r["L2"] for r in res], "o-", label=r"$L_2$")
        ax.loglog(h, [r["mass_err"] for r in res], "^:", label="Mass error")
        h_ref = np.array([h[0], h[-1]])
        for order in [1, 2]:
            ax.loglog(h_ref, res[0]["L2"]*(h_ref/h_ref[0])**order,
                      "--", color="gray", alpha=0.4, label=f"$O(h^{order})$")
        ax.set_xlabel("$h$"); ax.set_ylabel("Error"); ax.set_title(title)
        ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "cls_advection")


def plot_snapshots(fields):
    """Generate 2D contour visualizations of CLS advection tests."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    # Custom colormap: light blue (gas) -> white (interface) -> warm orange (liquid)
    cmap = LinearSegmentedColormap.from_list(
        "phase", ["#4393c3", "#d1e5f0", "#fddbc7", "#d6604d"], N=256
    )

    fig, axes = plt.subplots(2, 3, figsize=(7.0, 5.0))

    # --- Row 1: Zalesak slotted disk ---
    zX, zY = fields["zalesak_X"], fields["zalesak_Y"]
    z_panels = [
        (fields["zalesak_init"], "$t = 0$"),
        (fields["zalesak_half"], "$t = T/2$"),
        (fields["zalesak_final"], "$t = T$"),
    ]
    for ax, (psi, title) in zip(axes[0], z_panels):
        pcm = ax.pcolormesh(zX, zY, psi, cmap=cmap, vmin=0, vmax=1,
                            shading="gouraud", rasterized=True)
        ax.contour(zX, zY, psi, levels=[0.5], colors="k", linewidths=0.8)
        # Show initial interface as dashed reference
        if title != "$t = 0$":
            ax.contour(zX, zY, fields["zalesak_init"], levels=[0.5],
                       colors="k", linewidths=0.5, linestyles="dashed")
        ax.set_aspect("equal")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(title, fontsize=9)
        ax.tick_params(labelsize=7)
    axes[0, 0].set_ylabel("(a) Zalesak", fontsize=9)

    # --- Row 2: Single vortex ---
    vX, vY = fields["vortex_X"], fields["vortex_Y"]
    v_panels = [
        (fields["vortex_init"], "$t = 0$"),
        (fields["vortex_mid"], "$t = T/2$"),
        (fields["vortex_final"], "$t = T$"),
    ]
    for ax, (psi, title) in zip(axes[1], v_panels):
        pcm = ax.pcolormesh(vX, vY, psi, cmap=cmap, vmin=0, vmax=1,
                            shading="gouraud", rasterized=True)
        ax.contour(vX, vY, psi, levels=[0.5], colors="k", linewidths=0.8)
        if title != "$t = 0$":
            ax.contour(vX, vY, fields["vortex_init"], levels=[0.5],
                       colors="k", linewidths=0.5, linestyles="dashed")
        ax.set_aspect("equal")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_title(title, fontsize=9)
        ax.tick_params(labelsize=7)
    axes[1, 0].set_ylabel("(b) Single vortex", fontsize=9)

    fig.tight_layout(h_pad=1.0, w_pad=0.5)
    cbar = fig.colorbar(pcm, ax=axes, shrink=0.6, pad=0.02,
                        label=r"$\psi$", ticks=[0, 0.5, 1])
    cbar.ax.tick_params(labelsize=7)
    save_figure(fig, OUT / "cls_advection_2d")


def main():
    args = experiment_argparser("[11-6] CLS Advection").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["zalesak"], d["vortex"])
        if "zalesak_init" in d:
            plot_snapshots(d)
        return

    print("\n--- (a) Zalesak slotted disk ---")
    zalesak, z_fields = run_zalesak()
    print("\n--- (b) Single vortex ---")
    vortex, v_fields = run_single_vortex()

    all_fields = {**z_fields, **v_fields}
    save_results(OUT / "data.npz", {"zalesak": zalesak, "vortex": vortex, **all_fields})
    plot_all(zalesak, vortex)
    plot_snapshots(all_fields)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
