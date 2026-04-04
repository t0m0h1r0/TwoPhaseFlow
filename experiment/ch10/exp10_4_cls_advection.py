#!/usr/bin/env python3
"""【10-4】CLS advection and reinitialization accuracy.

Tests:
(a) Zalesak slotted disk — shape preservation under rigid rotation
(b) Single vortex (LeVeque 1996) — interface sharpness and mass conservation

Paper ref: §3, §5, §10
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import LevelSetAdvection, DissipativeCCDAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside
from twophase.initial_conditions.shapes import Circle
from twophase.initial_conditions.velocity_fields import RigidRotation
from twophase.initial_conditions.builder import InitialConditionBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "cls_advection"
OUT.mkdir(parents=True, exist_ok=True)


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    """Signed distance for Zalesak slotted disk."""
    # Circle SDF
    phi_circle = np.sqrt((X - center[0])**2 + (Y - center[1])**2) - R
    # Slot: rectangular cut from bottom of circle
    # Slot extends from center[1]-R to center[1]-R+slot_h
    slot_x_min = center[0] - slot_w / 2
    slot_x_max = center[0] + slot_w / 2
    slot_y_max = center[1] - R + slot_h

    # Rectangle SDF (inside = negative)
    dx = np.maximum(slot_x_min - X, X - slot_x_max)
    dy = np.maximum(-1e10 - Y, Y - slot_y_max)  # open at bottom
    phi_slot = np.maximum(dx, dy)

    # Slotted disk = circle AND NOT slot
    phi = np.maximum(phi_circle, -phi_slot)
    return phi


def run_zalesak(Ns=[64, 128, 256]):
    """Zalesak disk rotation test."""
    backend = Backend(use_gpu=False)
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N

        X, Y = grid.meshgrid()

        # Initial SDF → CLS
        phi0 = zalesak_sdf(X, Y)
        psi0 = heaviside(np, phi0, eps)

        # Rigid rotation: one full revolution with period T
        T = 2 * np.pi  # period
        vf = RigidRotation(center=(0.5, 0.5), period=T)

        # DCCD advection + reinitializer
        adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05)
        reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero")

        dt = 0.45 / N  # CFL ~ 0.45 * max(|u|) ~ 0.45 * 2π * 0.5 / T ... ≈ 0.45
        # Actually max |u| ≈ 2π * R_max / T where R_max ~ 0.5
        # max|u| ≈ 2π * 0.5 / (2π) = 0.5, so CFL = u*dt/h = 0.5 * 0.45/N * N = 0.225
        n_steps = int(T / dt)
        dt = T / n_steps  # exact period

        psi = psi0.copy()
        mass0 = float(np.sum(psi))

        for step in range(n_steps):
            u, v = vf.compute(X, Y, t=0)  # steady rotation
            psi = adv.advance(psi, [u, v], dt)
            if (step + 1) % 20 == 0:
                psi = reinit.reinitialize(psi)

        mass_final = float(np.sum(psi))
        mass_err = abs(mass_final - mass0) / mass0

        # Shape error (L2 of psi difference)
        err_L2 = float(np.sqrt(np.mean((psi - psi0)**2)))
        err_Li = float(np.max(np.abs(psi - psi0)))

        # Area error
        area0 = float(np.sum(psi0)) / N**2
        area_f = float(np.sum(psi)) / N**2
        area_err = abs(area_f - area0) / area0

        results.append({
            "N": N, "h": 1.0/N, "n_steps": n_steps,
            "L2": err_L2, "Li": err_Li,
            "mass_err": mass_err, "area_err": area_err,
        })

        print(f"  N={N:>4}: L2={err_L2:.3e}, Li={err_Li:.3e}, "
              f"mass_err={mass_err:.3e}, area_err={area_err:.3e}")

    # Slopes
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for key in ["L2", "Li"]:
            if r0[key] > 0 and r1[key] > 0:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results


def single_vortex_field(X, Y, t, T):
    """Time-reversing single vortex velocity field (LeVeque 1996)."""
    cos_factor = np.cos(np.pi * t / T)
    u = -2 * np.sin(np.pi * X)**2 * np.sin(np.pi * Y) * np.cos(np.pi * Y) * cos_factor
    v =  2 * np.sin(np.pi * Y)**2 * np.sin(np.pi * X) * np.cos(np.pi * X) * cos_factor
    return u, v


def run_single_vortex(Ns=[64, 128, 256]):
    """Single vortex test: deform and reverse."""
    backend = Backend(use_gpu=False)
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N

        X, Y = grid.meshgrid()

        # Initial: circle at (0.5, 0.75), R=0.15
        phi0 = np.sqrt((X - 0.5)**2 + (Y - 0.75)**2) - 0.15
        psi0 = heaviside(np, phi0, eps)

        adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05)
        reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero")

        T = 8.0  # full period (deform + reverse)
        cfl = 0.45
        # max|u| ~ 1 (from the vortex field)
        dt = cfl / N
        n_steps = int(T / dt)
        dt = T / n_steps

        psi = psi0.copy()
        mass0 = float(np.sum(psi))

        for step in range(n_steps):
            t = step * dt
            u, v = single_vortex_field(X, Y, t, T)
            psi = adv.advance(psi, [u, v], dt)
            if (step + 1) % 10 == 0:
                psi = reinit.reinitialize(psi)

        mass_final = float(np.sum(psi))
        mass_err = abs(mass_final - mass0) / mass0

        err_L2 = float(np.sqrt(np.mean((psi - psi0)**2)))
        err_Li = float(np.max(np.abs(psi - psi0)))

        results.append({
            "N": N, "h": 1.0/N, "n_steps": n_steps,
            "L2": err_L2, "Li": err_Li, "mass_err": mass_err,
        })
        print(f"  N={N:>4}: L2={err_L2:.3e}, Li={err_Li:.3e}, mass_err={mass_err:.3e}")

    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        log_h = np.log(r1["h"] / r0["h"])
        for key in ["L2", "Li"]:
            if r0[key] > 0 and r1[key] > 0:
                r1[f"{key}_slope"] = np.log(r1[key] / r0[key]) / log_h

    return results


def plot_results(zalesak_res, vortex_res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # (a) Zalesak
    ax = axes[0]
    h = [r["h"] for r in zalesak_res]
    ax.loglog(h, [r["L2"] for r in zalesak_res], "o-", label=r"$L_2$")
    ax.loglog(h, [r["Li"] for r in zalesak_res], "s--", label=r"$L_\infty$")
    ax.loglog(h, [r["mass_err"] for r in zalesak_res], "^:", label="Mass error")
    h_ref = np.array([h[0], h[-1]])
    for order in [1, 2]:
        e0 = zalesak_res[0]["L2"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, "--", color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel("Error")
    ax.set_title("(a) Zalesak slotted disk (1 revolution)")
    ax.legend(fontsize=7); ax.grid(True, which="both", alpha=0.3)

    # (b) Single vortex
    ax = axes[1]
    h = [r["h"] for r in vortex_res]
    ax.loglog(h, [r["L2"] for r in vortex_res], "o-", label=r"$L_2$")
    ax.loglog(h, [r["Li"] for r in vortex_res], "s--", label=r"$L_\infty$")
    ax.loglog(h, [r["mass_err"] for r in vortex_res], "^:", label="Mass error")
    h_ref = np.array([h[0], h[-1]])
    for order in [1, 2]:
        e0 = vortex_res[0]["L2"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, "--", color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel("Error")
    ax.set_title("(b) Single vortex (deform + reverse)")
    ax.legend(fontsize=7); ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT / "cls_advection.pdf", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'cls_advection.pdf'}")


def save_tables(zalesak_res, vortex_res):
    for name, res in [("zalesak", zalesak_res), ("vortex", vortex_res)]:
        with open(OUT / f"table_{name}.tex", "w") as fp:
            fp.write(f"% {name} convergence\n")
            fp.write("\\begin{tabular}{rrrrrr}\n\\toprule\n")
            fp.write("$N$ & $L_2$ & slope & $L_\\infty$ & slope & mass err \\\\\n\\midrule\n")
            for r in res:
                sl2 = r.get("L2_slope", float("nan"))
                sli = r.get("Li_slope", float("nan"))
                sl2_s = f"{sl2:.2f}" if not np.isnan(sl2) else "---"
                sli_s = f"{sli:.2f}" if not np.isnan(sli) else "---"
                fp.write(f"{r['N']} & {r['L2']:.2e} & {sl2_s} & "
                         f"{r['Li']:.2e} & {sli_s} & {r['mass_err']:.2e} \\\\\n")
            fp.write("\\bottomrule\n\\end{tabular}\n")


def main():
    print("\n" + "="*80)
    print("  【10-4】CLS Advection & Reinitialization Accuracy")
    print("="*80)

    print("\n--- (a) Zalesak slotted disk ---")
    zalesak_res = run_zalesak()

    print("\n--- (b) Single vortex (LeVeque 1996) ---")
    vortex_res = run_single_vortex()

    save_tables(zalesak_res, vortex_res)
    plot_results(zalesak_res, vortex_res)

    np.savez(OUT / "cls_advection_data.npz",
             zalesak=zalesak_res, vortex=vortex_res)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "cls_advection_data.npz", allow_pickle=True)
        plot_results(list(_d["zalesak"]), list(_d["vortex"]))
    else:
        main()
