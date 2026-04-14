#!/usr/bin/env python3
"""[11-18] CLS-DCCD conservation theory verification (WIKI-T-028).

Validates three theoretical claims from CHK-101:
  (A) DCCD spatial operator preserves sum(f') = 0 for periodic BC
  (B) Unified DCCD reinit improves mass conservation vs operator-split
  (C) Unified scheme is less sensitive to reinit frequency

Expected:
  Test A: |sum(RHS)| < 1e-12 for periodic BC
  Test B: unified mass_err < split mass_err at all N
  Test C: unified mass_err nearly flat across reinit frequencies
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
from twophase.simulation.initial_conditions.velocity_fields import SingleVortex
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


# ── Shared velocity field ─────────────────────────────────────────────────

def single_vortex_field(X, Y, t, T):
    """LeVeque (1996) single vortex — delegates to library."""
    return SingleVortex(period=T).compute(X, Y, t=t)


# ── Test A: DCCD sum property ─────────────────────────────────────────────

def test_dccd_sum_property(Ns=[64, 128, 256]):
    """Verify |sum(D_DCCD(psi*u))| for periodic and wall BC."""
    backend = Backend()
    xp = backend.xp
    results = []
    print("\n=== Test A: DCCD Sum Property ===")

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)

        # Smooth periodic field: sum of sines
        X, Y = grid.meshgrid()
        psi = 0.5 + 0.3 * xp.sin(2 * np.pi * X) * xp.sin(4 * np.pi * Y)
        u = xp.sin(2 * np.pi * X) * xp.cos(2 * np.pi * Y)
        v = -xp.cos(2 * np.pi * X) * xp.sin(2 * np.pi * Y)

        # Periodic BC
        ccd_p = CCDSolver(grid, backend, bc_type="periodic")
        adv_p = DissipativeCCDAdvection(backend, grid, ccd_p, bc="periodic")
        rhs_p = adv_p._rhs(psi, [u, v])
        sum_periodic = abs(float(xp.sum(rhs_p)))

        # Wall BC
        ccd_w = CCDSolver(grid, backend, bc_type="wall")
        adv_w = DissipativeCCDAdvection(backend, grid, ccd_w, bc="zero")
        rhs_w = adv_w._rhs(psi, [u, v])
        sum_wall = abs(float(xp.sum(rhs_w)))

        results.append({
            "N": N, "h": 1.0/N,
            "sum_periodic": sum_periodic,
            "sum_wall": sum_wall,
        })
        print(f"  N={N:>4}: |sum_periodic|={sum_periodic:.2e}, |sum_wall|={sum_wall:.2e}")

    return results


# ── Test B: Single vortex — split vs unified ──────────────────────────────

def run_single_vortex(N, reinit_freq, unified_dccd, mass_correction,
                      backend, label=""):
    """Run single vortex test and return metrics."""
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    eps = 1.5 / N
    X, Y = grid.meshgrid()

    phi0 = xp.sqrt((X - 0.5)**2 + (Y - 0.75)**2) - 0.15
    psi0 = heaviside(xp, phi0, eps)
    adv = DissipativeCCDAdvection(
        backend, grid, ccd, bc="zero", eps_d=0.05, mass_correction=True,
    )
    reinit = Reinitializer(
        backend, grid, ccd, eps, n_steps=4, bc="zero",
        unified_dccd=unified_dccd, mass_correction=mass_correction,
    )

    T = 8.0; dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    mass0 = float(xp.sum(psi))

    for step in range(n_steps):
        u, v = single_vortex_field(X, Y, step * dt, T)
        psi = adv.advance(psi, [u, v], dt)
        if reinit_freq > 0 and (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)

    mass_err = abs(float(xp.sum(psi)) - mass0) / max(mass0, 1e-15)
    err_L2 = float(xp.sqrt(xp.mean((psi - psi0)**2)))
    err_Linf = float(xp.max(xp.abs(psi - psi0)))
    return {"L2": err_L2, "Linf": err_Linf, "mass_err": mass_err}


def test_convergence(Ns=[64, 128, 256], reinit_freq=10):
    """Test B: grid convergence for 4 configurations."""
    backend = Backend()
    configs = [
        ("split",      False, False),
        ("split+mc",   False, True),
        ("unified",    True,  False),
        ("unified+mc", True,  True),
    ]
    results = {name: [] for name, _, _ in configs}
    print(f"\n=== Test B: Convergence (reinit every {reinit_freq} steps) ===")

    for N in Ns:
        print(f"  N={N}:")
        for name, unified, mc in configs:
            r = run_single_vortex(N, reinit_freq, unified, mc, backend, name)
            r["N"] = N; r["h"] = 1.0 / N
            results[name].append(r)
            print(f"    {name:>12}: L2={r['L2']:.3e}, mass={r['mass_err']:.3e}")

    return results


# ── Test C: Reinit frequency sensitivity ──────────────────────────────────

def test_reinit_sensitivity(N=64, freqs=[1, 2, 5, 10, 20]):
    """Test C: mass error vs reinit frequency."""
    backend = Backend()
    configs = [
        ("split+mc",   False, True),
        ("unified+mc", True,  True),
    ]
    results = {name: [] for name, _, _ in configs}
    print(f"\n=== Test C: Reinit Sensitivity (N={N}) ===")

    for freq in freqs:
        print(f"  freq={freq}:")
        for name, unified, mc in configs:
            r = run_single_vortex(N, freq, unified, mc, backend, name)
            r["freq"] = freq
            results[name].append(r)
            print(f"    {name:>12}: L2={r['L2']:.3e}, mass={r['mass_err']:.3e}")

    return results


# ── Plotting ──────────────────────────────────────────────────────────────

def plot_all(test_a, test_b, test_c):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5))

    # (a) Test A: DCCD sum property
    ax = axes[0]
    h = [r["h"] for r in test_a]
    ax.semilogy(h, [r["sum_periodic"] for r in test_a], "o-",
                color=COLORS[0], label="Periodic")
    ax.semilogy(h, [r["sum_wall"] for r in test_a], "s--",
                color=COLORS[1], label="Wall")
    ax.axhline(1e-13, color="gray", ls=":", alpha=0.5, label=r"$10^{-13}$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$|\sum \tilde{f}'_i|$")
    ax.set_title("(a) DCCD sum property")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # (b) Test B: convergence — mass error
    ax = axes[1]
    markers = ["o", "s", "^", "D"]
    styles = ["-", "-", "--", "--"]
    colors_b = [COLORS[0], COLORS[1], COLORS[2], COLORS[3]]
    for i, name in enumerate(test_b):
        res = test_b[name]
        h = [r["h"] for r in res]
        mass = [r["mass_err"] for r in res]
        ax.loglog(h, mass, markers[i] + styles[i], color=colors_b[i],
                  label=name, markersize=5)
    ax.set_xlabel("$h$"); ax.set_ylabel("Mass error (relative)")
    ax.set_title("(b) Grid convergence")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # (c) Test C: reinit sensitivity
    ax = axes[2]
    for i, name in enumerate(test_c):
        res = test_c[name]
        freqs = [r["freq"] for r in res]
        mass = [r["mass_err"] for r in res]
        color = COLORS[1] if "split" in name else COLORS[2]
        style = "s-" if "split" in name else "^--"
        ax.semilogy(freqs, mass, style, color=color, label=name, markersize=5)
    ax.set_xlabel("Reinit frequency (steps)")
    ax.set_ylabel("Mass error (relative)")
    ax.set_title("(c) Reinit sensitivity ($N=64$)")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)
    ax.invert_xaxis()

    fig.tight_layout()
    save_figure(fig, OUT / "cls_dccd_conservation")


def main():
    args = experiment_argparser("[11-18] CLS-DCCD Conservation").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["test_a"], d["test_b"], d["test_c"])
        return

    test_a = test_dccd_sum_property()
    test_b = test_convergence()
    test_c = test_reinit_sensitivity()

    save_results(OUT / "data.npz", {
        "test_a": test_a, "test_b": test_b, "test_c": test_c,
    })
    plot_all(test_a, test_b, test_c)

    # Summary
    print("\n=== Summary ===")
    periodic_pass = all(r["sum_periodic"] < 1e-10 for r in test_a)
    print(f"Test A (periodic sum): {'PASS' if periodic_pass else 'FAIL'}")

    # Check if unified is better than split at each N
    for name_u, name_s in [("unified+mc", "split+mc"), ("unified", "split")]:
        if name_u in test_b and name_s in test_b:
            wins = sum(1 for u, s in zip(test_b[name_u], test_b[name_s])
                       if u["mass_err"] <= s["mass_err"])
            total = len(test_b[name_u])
            print(f"Test B ({name_u} vs {name_s}): {wins}/{total} wins")

    # Reinit sensitivity ratio
    for name in test_c:
        masses = [r["mass_err"] for r in test_c[name]]
        ratio = max(masses) / max(min(masses), 1e-15)
        print(f"Test C ({name}): max/min mass_err ratio = {ratio:.1f}x")

    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
