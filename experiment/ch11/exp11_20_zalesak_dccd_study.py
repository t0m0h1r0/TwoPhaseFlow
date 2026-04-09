#!/usr/bin/env python3
"""[11-20] Zalesak slotted disk — DCCD damping parametric study.

Investigates whether DCCD filtering (εd=0.05) is too strong for the sharp
slot corners of Zalesak's disk.  The "DCCD ≈ 2 %" finding from exp11_19
was measured on a smooth circle; Zalesak's corners have high-frequency
content that experiences stronger damping.

Sweeps (all at N=128):
  S1: advection εd   ∈ {0.0, 0.01, 0.025, 0.05}
  S2: reinit comp εd  ∈ {0.0, 0.01, 0.025, 0.05}
  S3: reinit frequency ∈ every {10, 20, 40, 80} steps
  S4: combined best from S1–S3 + ε/h ∈ {1.0, 1.5}
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

N = 128   # fixed resolution for all sweeps


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    """Zalesak slotted disk SDF — delegates to library."""
    from twophase.initial_conditions.shapes import ZalesakDisk
    return ZalesakDisk(center=center, radius=R, slot_width=slot_w, slot_depth=slot_h).sdf(X, Y)


def run_zalesak(eps_d_adv=0.05, eps_d_reinit=0.05, reinit_every=20,
                n_reinit_steps=4, eps_over_h=1.5):
    """Run Zalesak 1-revolution test with specified parameters.

    Returns dict: {L2, mass_err, reinit_count, params}
    """
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_over_h * h
    X, Y = grid.meshgrid()

    phi0 = zalesak_sdf(X, Y)
    psi0 = heaviside(np, phi0, eps)

    T = 2 * np.pi
    vf = RigidRotation(center=(0.5, 0.5), period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                  eps_d=eps_d_adv, mass_correction=True)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=n_reinit_steps,
                           bc="zero", eps_d_comp=eps_d_reinit)

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    mass0 = float(np.sum(psi))
    reinit_count = 0

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=0)
        psi = adv.advance(psi, [u, v], dt)
        if reinit_every > 0 and (step + 1) % reinit_every == 0:
            psi = reinit.reinitialize(psi)
            reinit_count += 1

    mass_err = abs(float(np.sum(psi)) - mass0) / mass0
    err_L2_psi = float(np.sqrt(np.mean((psi - psi0)**2)))

    # φ-space L₂ (interface band |φ₀| < 6ε) — ε-independent metric
    phi_final = invert_heaviside(np, psi, eps)
    band = np.abs(phi0) < 6 * eps
    err_L2_phi = float(np.sqrt(np.mean((phi_final[band] - phi0[band])**2)))

    # Area error: symmetric difference of {ψ ≥ 0.5}
    area0 = float(np.sum(psi0 >= 0.5))
    area_final = float(np.sum(psi >= 0.5))
    area_err = abs(area_final - area0) / max(area0, 1.0)

    return {
        "L2": err_L2_psi, "L2_phi": err_L2_phi, "area_err": area_err,
        "mass_err": mass_err, "reinit_count": reinit_count,
        "eps_d_adv": eps_d_adv, "eps_d_reinit": eps_d_reinit,
        "reinit_every": reinit_every, "eps_over_h": eps_over_h,
    }


def sweep_adv_epsd():
    """S1: advection εd sweep."""
    print("\n=== Sweep 1: advection εd ===")
    values = [0.0, 0.01, 0.025, 0.05]
    results = []
    for ed in values:
        r = run_zalesak(eps_d_adv=ed)
        results.append(r)
        print(f"  εd_adv={ed:.3f}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, area={r['area_err']:.2e}")
    return results


def sweep_reinit_epsd():
    """S2: reinit compression εd sweep."""
    print("\n=== Sweep 2: reinit compression εd ===")
    values = [0.0, 0.01, 0.025, 0.05]
    results = []
    for ed in values:
        r = run_zalesak(eps_d_reinit=ed)
        results.append(r)
        print(f"  εd_reinit={ed:.3f}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, area={r['area_err']:.2e}")
    return results


def sweep_reinit_freq():
    """S3: reinit frequency sweep."""
    print("\n=== Sweep 3: reinit frequency ===")
    values = [10, 20, 40, 80]
    results = []
    for freq in values:
        r = run_zalesak(reinit_every=freq)
        results.append(r)
        print(f"  every {freq:>3}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, area={r['area_err']:.2e}, reinits={r['reinit_count']}")
    return results


def sweep_combined(best_adv, best_reinit, best_freq):
    """S4: combined best + ε/h variation."""
    print("\n=== Sweep 4: combined best ===")
    results = []
    for eps_over_h in [1.0, 1.5]:
        r = run_zalesak(eps_d_adv=best_adv, eps_d_reinit=best_reinit,
                        reinit_every=best_freq, eps_over_h=eps_over_h)
        results.append(r)
        print(f"  εd_adv={best_adv:.3f}, εd_reinit={best_reinit:.3f}, "
              f"every={best_freq}, ε/h={eps_over_h:.1f}: "
              f"L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, area={r['area_err']:.2e}")

    # Also run baseline for comparison
    baseline = run_zalesak()
    results.append(baseline)
    print(f"  BASELINE (default):  L2ψ={baseline['L2']:.4e}, L2φ={baseline['L2_phi']:.4e}")
    return results


def plot_all(s1, s2, s3, s4):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE_2COL)

    # S1: advection εd
    ax = axes[0, 0]
    eds = [r["eps_d_adv"] for r in s1]
    l2_phi = [r["L2_phi"] for r in s1]
    ax.bar(range(len(eds)), l2_phi, color=COLORS[0], alpha=0.8)
    ax.set_xticks(range(len(eds)))
    ax.set_xticklabels([f"{e:.3f}" for e in eds], fontsize=7)
    ax.set_xlabel(r"$\varepsilon_{d,\mathrm{adv}}$")
    ax.set_ylabel(r"$L_2(\phi)$")
    ax.set_title("S1: advection $\\varepsilon_d$", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    # S2: reinit compression εd
    ax = axes[0, 1]
    eds = [r["eps_d_reinit"] for r in s2]
    l2_phi = [r["L2_phi"] for r in s2]
    ax.bar(range(len(eds)), l2_phi, color=COLORS[1], alpha=0.8)
    ax.set_xticks(range(len(eds)))
    ax.set_xticklabels([f"{e:.3f}" for e in eds], fontsize=7)
    ax.set_xlabel(r"$\varepsilon_{d,\mathrm{reinit}}$")
    ax.set_ylabel(r"$L_2(\phi)$")
    ax.set_title("S2: reinit compression $\\varepsilon_d$", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    # S3: reinit frequency
    ax = axes[1, 0]
    freqs = [r["reinit_every"] for r in s3]
    l2_phi = [r["L2_phi"] for r in s3]
    ax.bar(range(len(freqs)), l2_phi, color=COLORS[2], alpha=0.8)
    ax.set_xticks(range(len(freqs)))
    ax.set_xticklabels([str(f) for f in freqs], fontsize=7)
    ax.set_xlabel("Reinit interval (steps)")
    ax.set_ylabel(r"$L_2(\phi)$")
    ax.set_title("S3: reinit frequency", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    # S4: combined (φ-space enables fair cross-ε comparison)
    ax = axes[1, 1]
    labels = [f"ε/h={r['eps_over_h']:.1f}" for r in s4[:-1]] + ["baseline"]
    l2_phi = [r["L2_phi"] for r in s4]
    colors_s4 = [COLORS[3]] * (len(s4) - 1) + ["gray"]
    ax.bar(range(len(l2_phi)), l2_phi, color=colors_s4, alpha=0.8)
    ax.set_xticks(range(len(l2_phi)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel(r"$L_2(\phi)$")
    ax.set_title("S4: combined best", fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "zalesak_dccd_study")


def main():
    args = experiment_argparser("[11-20] Zalesak DCCD Study").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["s1"], d["s2"], d["s3"], d["s4"])
        return

    s1 = sweep_adv_epsd()
    s2 = sweep_reinit_epsd()
    s3 = sweep_reinit_freq()

    # Pick best from each sweep (lowest L2)
    best_adv = min(s1, key=lambda r: r["L2"])["eps_d_adv"]
    best_reinit = min(s2, key=lambda r: r["L2"])["eps_d_reinit"]
    best_freq = min(s3, key=lambda r: r["L2"])["reinit_every"]
    print(f"\nBest: εd_adv={best_adv}, εd_reinit={best_reinit}, freq={best_freq}")

    s4 = sweep_combined(best_adv, best_reinit, best_freq)

    save_results(OUT / "data.npz", {"s1": s1, "s2": s2, "s3": s3, "s4": s4})
    plot_all(s1, s2, s3, s4)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
