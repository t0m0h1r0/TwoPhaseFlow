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
from twophase.levelset.heaviside import heaviside
from twophase.initial_conditions.velocity_fields import RigidRotation
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    phi_circle = np.sqrt((X - center[0])**2 + (Y - center[1])**2) - R
    slot_x_min, slot_x_max = center[0] - slot_w / 2, center[0] + slot_w / 2
    slot_y_max = center[1] - R + slot_h
    dx = np.maximum(slot_x_min - X, X - slot_x_max)
    dy = np.maximum(-1e10 - Y, Y - slot_y_max)
    phi_slot = np.maximum(dx, dy)
    return np.maximum(phi_circle, -phi_slot)


_REINIT_THRESHOLD = 1.10   # adaptive reinit trigger: M(τ)/M_ref > θ (§7b)


def _adaptive_reinit_needed(xp, psi, M_ref, h, threshold=_REINIT_THRESHOLD):
    """Check if reinitialization is needed based on volume monitor M(τ)."""
    M_cur = float(xp.sum(psi * (1.0 - psi))) * (h ** 2)
    return M_ref > 1e-15 and M_cur / M_ref > threshold


def run_zalesak(Ns=[64, 128, 256], save_fields_N=128):
    backend = Backend(use_gpu=False)
    results = []
    fields = {}
    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N
        h = 1.0 / N
        X, Y = grid.meshgrid()

        phi0 = zalesak_sdf(X, Y)
        psi0 = heaviside(np, phi0, eps)

        T = 2 * np.pi
        vf = RigidRotation(center=(0.5, 0.5), period=T)
        adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05, mass_correction=True)
        reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero")

        dt = 0.45 / N
        n_steps = int(T / dt); dt = T / n_steps
        psi = psi0.copy()
        mass0 = float(np.sum(psi))
        M_ref = float(np.sum(psi * (1.0 - psi))) * (h ** 2)
        reinit_count = 0

        # Save fields for 2D visualization at selected resolution
        save_2d = (N == save_fields_N)
        if save_2d:
            fields["zalesak_init"] = psi0.copy()
            fields["zalesak_X"] = X.copy()
            fields["zalesak_Y"] = Y.copy()

        for step in range(n_steps):
            u, v = vf.compute(X, Y, t=0)
            psi = adv.advance(psi, [u, v], dt)
            # Fixed-frequency reinit for Zalesak (sharp slot geometry
            # requires regular profile maintenance; adaptive trigger
            # M(τ)/M_ref cannot detect local corner degradation)
            if (step + 1) % 20 == 0:
                psi = reinit.reinitialize(psi)
                reinit_count += 1
            # Save at quarter and half revolution
            if save_2d and step + 1 == n_steps // 4:
                fields["zalesak_quarter"] = psi.copy()
            if save_2d and step + 1 == n_steps // 2:
                fields["zalesak_half"] = psi.copy()

        if save_2d:
            fields["zalesak_final"] = psi.copy()

        mass_err = abs(float(np.sum(psi)) - mass0) / mass0
        err_L2 = float(np.sqrt(np.mean((psi - psi0)**2)))
        results.append({"N": N, "h": 1.0/N, "L2": err_L2, "mass_err": mass_err})
        print(f"  N={N:>4}: L2={err_L2:.3e}, mass_err={mass_err:.3e}, reinits={reinit_count}")
    return results, fields


def single_vortex_field(X, Y, t, T):
    c = np.cos(np.pi * t / T)
    u = -2 * np.sin(np.pi * X)**2 * np.sin(np.pi * Y) * np.cos(np.pi * Y) * c
    v =  2 * np.sin(np.pi * Y)**2 * np.sin(np.pi * X) * np.cos(np.pi * X) * c
    return u, v


def run_single_vortex(Ns=[64, 128, 256], save_fields_N=128):
    backend = Backend(use_gpu=False)
    results = []
    fields = {}
    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N
        h = 1.0 / N
        X, Y = grid.meshgrid()

        phi0 = np.sqrt((X - 0.5)**2 + (Y - 0.75)**2) - 0.15
        psi0 = heaviside(np, phi0, eps)
        adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05, mass_correction=True)
        reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero")

        T = 8.0; dt = 0.45 / N; n_steps = int(T / dt); dt = T / n_steps
        psi = psi0.copy(); mass0 = float(np.sum(psi))
        M_ref = float(np.sum(psi * (1.0 - psi))) * (h ** 2)
        reinit_count = 0

        save_2d = (N == save_fields_N)
        if save_2d:
            fields["vortex_init"] = psi0.copy()
            fields["vortex_X"] = X.copy()
            fields["vortex_Y"] = Y.copy()

        for step in range(n_steps):
            u, v = single_vortex_field(X, Y, step * dt, T)
            psi = adv.advance(psi, [u, v], dt)
            # Adaptive reinit trigger (§7b eq:adaptive_reinit_trigger)
            if _adaptive_reinit_needed(np, psi, M_ref, h):
                psi = reinit.reinitialize(psi)
                M_ref = float(np.sum(psi * (1.0 - psi))) * (h ** 2)
                reinit_count += 1
            # Save at max deformation (t = T/2)
            if save_2d and step + 1 == n_steps // 2:
                fields["vortex_mid"] = psi.copy()

        if save_2d:
            fields["vortex_final"] = psi.copy()

        mass_err = abs(float(np.sum(psi)) - mass0) / mass0
        err_L2 = float(np.sqrt(np.mean((psi - psi0)**2)))
        results.append({"N": N, "h": 1.0/N, "L2": err_L2, "mass_err": mass_err})
        print(f"  N={N:>4}: L2={err_L2:.3e}, mass_err={mass_err:.3e}, reinits={reinit_count}")
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
