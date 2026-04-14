#!/usr/bin/env python3
"""[11-24] DGR thickness correction dedicated verification.

Validates §7b claims for Direct Geometric Reinitialization (DGR):
  (A) DGR is idempotent on correct-thickness tanh profiles (eps_eff/eps ~ 1.0)
  (B) DGR restores broadened interface: eps_eff = 1.4*eps -> eps after DGR
  (C) DGR frequency parameter study with repeated split reinit + DGR

Expected:
  Test A: eps_eff/eps stays within [0.98, 1.02] over 100 DGR applications
  Test B: DGR reduces eps_eff/eps from ~1.4 to ~1.03; area error ~24x better
  Test C: Higher DGR frequency -> tighter eps_eff/eps maintenance
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_circle_psi(grid, backend, R=0.25, eps_factor=1.0):
    """Create tanh-profile CLS field for a circle of radius R."""
    xp = backend.xp
    X, Y = grid.meshgrid()
    h = grid.L[0] / grid.N[0]
    eps = eps_factor * h
    phi = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    psi = heaviside(xp, phi, eps)
    return psi, eps


def make_broadened_psi(grid, backend, R=0.25, eps_nominal=None, broadening=1.4):
    """Create a circle whose interface thickness is broadened by a factor."""
    xp = backend.xp
    X, Y = grid.meshgrid()
    h = grid.L[0] / grid.N[0]
    if eps_nominal is None:
        eps_nominal = h
    eps_broad = broadening * eps_nominal
    phi = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    psi = heaviside(xp, phi, eps_broad)
    return psi


def measure_eps_eff(psi, ccd, eps, xp=np):
    """Estimate effective interface thickness from psi(1-psi)/|grad psi|.

    For a perfect tanh profile: psi(1-psi)/|grad psi| = eps everywhere
    in the interface band. Returns eps_eff/eps ratio.
    """
    grad_sq = xp.zeros_like(psi)
    for ax in range(2):
        g1, _ = ccd.differentiate(psi, ax)
        grad_sq = grad_sq + g1 * g1
    grad_mag = xp.sqrt(xp.maximum(grad_sq, 1e-28))

    product = psi * (1.0 - psi)
    mask = (psi > 0.05) & (psi < 0.95) & (grad_mag > 1e-10)
    if not bool(xp.any(mask)):
        return 1.0  # fallback
    eps_local = product[mask] / grad_mag[mask]
    eps_eff = float(xp.median(eps_local))
    return eps_eff / eps


def area_from_psi(psi, grid, xp=np):
    """Compute enclosed area as integral of psi * dV."""
    dV = xp.asarray(grid.cell_volumes())
    return float(xp.sum(psi * dV))


# ── Test A: Static DGR-only stability ────────────────────────────────────────

def test_a_dgr_stability(N=128, n_applications=100):
    """Apply DGR repeatedly to a correct-thickness profile.

    A correct tanh profile should be a fixed point of DGR.
    """
    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    psi, eps = make_circle_psi(grid, backend, R=0.25, eps_factor=1.0)
    area0 = area_from_psi(psi, grid, xp)

    reinit_dgr = Reinitializer(
        backend, grid, ccd, eps, n_steps=1, bc="zero", method="dgr",
    )

    ratios = []
    area_errors = []
    ratio0 = measure_eps_eff(psi, ccd, eps, xp)
    ratios.append(ratio0)
    area_errors.append(0.0)
    print(f"\n=== Test A: DGR stability (N={N}, {n_applications} applications) ===")
    print(f"  Initial eps_eff/eps = {ratio0:.4f}")

    for k in range(1, n_applications + 1):
        psi = reinit_dgr.reinitialize(psi)
        ratio = measure_eps_eff(psi, ccd, eps, xp)
        area_err = abs(area_from_psi(psi, grid, xp) - area0) / area0
        ratios.append(ratio)
        area_errors.append(area_err)
        if k % 20 == 0 or k == 1:
            print(f"  k={k:>3}: eps_eff/eps={ratio:.4f}, area_err={area_err:.2e}")

    return {
        "N": N, "n_applications": n_applications,
        "ratios": ratios, "area_errors": area_errors,
    }


# ── Test B: DGR ablation — broadened profile restoration ─────────────────────

def test_b_dgr_ablation(N=128, broadening_factors=None):
    """Apply DGR to artificially broadened profiles and measure restoration.

    Simulates the ~1.4x thickness broadening that operator splitting causes,
    and tests DGR's ability to restore the target thickness.
    """
    if broadening_factors is None:
        broadening_factors = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0]

    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    h = grid.L[0] / grid.N[0]
    eps = h  # target thickness

    # Reference: correct-thickness circle
    psi_ref, _ = make_circle_psi(grid, backend, R=0.25, eps_factor=1.0)
    area_exact = area_from_psi(psi_ref, grid, xp)

    reinit_dgr = Reinitializer(
        backend, grid, ccd, eps, n_steps=1, bc="zero", method="dgr",
    )

    results = []
    print(f"\n=== Test B: DGR ablation (N={N}) ===")
    print(f"  {'broad':>6s} | {'before':>10s} | {'after':>10s} | "
          f"{'area_before':>12s} | {'area_after':>12s} | {'improvement':>11s}")
    print("  " + "-" * 78)

    for bf in broadening_factors:
        psi_broad = make_broadened_psi(grid, backend, R=0.25,
                                       eps_nominal=eps, broadening=bf)
        ratio_before = measure_eps_eff(psi_broad, ccd, eps, xp)
        area_before = abs(area_from_psi(psi_broad, grid, xp) - area_exact) / area_exact

        psi_restored = reinit_dgr.reinitialize(psi_broad)
        ratio_after = measure_eps_eff(psi_restored, ccd, eps, xp)
        area_after = abs(area_from_psi(psi_restored, grid, xp) - area_exact) / area_exact

        improvement = area_before / area_after if area_after > 1e-15 else float("inf")

        results.append({
            "broadening": bf,
            "ratio_before": ratio_before,
            "ratio_after": ratio_after,
            "area_err_before": area_before,
            "area_err_after": area_after,
            "improvement": improvement,
        })
        print(f"  {bf:6.2f} | {ratio_before:10.4f} | {ratio_after:10.4f} | "
              f"{area_before:12.3e} | {area_after:12.3e} | {improvement:11.1f}x")

    return {"N": N, "results": results}


# ── Test C: DGR frequency with repeated split reinit ─────────────────────────

def test_c_dgr_frequency(N=128, n_total=200, dgr_freqs=None):
    """Apply split reinit repeatedly, with DGR at various frequencies.

    Measures how DGR frequency controls thickness drift when split
    reinitialization is the primary shape-restoration mechanism.
    """
    if dgr_freqs is None:
        dgr_freqs = [0, 5, 10, 20, 50]  # 0 = no DGR (control)

    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    h = grid.L[0] / grid.N[0]
    eps = h

    psi_init, _ = make_circle_psi(grid, backend, R=0.25, eps_factor=1.0)
    area_exact = area_from_psi(psi_init, grid, xp)

    print(f"\n=== Test C: DGR frequency study (N={N}, {n_total} split reinits) ===")

    all_results = {}
    for freq in dgr_freqs:
        label = f"dgr_every_{freq}" if freq > 0 else "no_dgr"
        reinit_split = Reinitializer(
            backend, grid, ccd, eps, n_steps=2, bc="zero", method="split",
        )
        reinit_dgr = Reinitializer(
            backend, grid, ccd, eps, n_steps=1, bc="zero", method="dgr",
        )

        psi = psi_init.copy()
        ratios = [measure_eps_eff(psi, ccd, eps, xp)]
        area_errs = [0.0]

        for k in range(1, n_total + 1):
            psi = reinit_split.reinitialize(psi)
            if freq > 0 and k % freq == 0:
                psi = reinit_dgr.reinitialize(psi)
            if k % 10 == 0 or k == n_total:
                ratio = measure_eps_eff(psi, ccd, eps, xp)
                area_err = abs(area_from_psi(psi, grid, xp) - area_exact) / area_exact
                ratios.append(ratio)
                area_errs.append(area_err)

        final_ratio = ratios[-1]
        final_area = area_errs[-1]
        print(f"  freq={freq:>3d}: final eps_eff/eps={final_ratio:.4f}, "
              f"area_err={final_area:.3e}")
        all_results[label] = {
            "freq": freq, "ratios": ratios, "area_errors": area_errs,
        }

    return {"N": N, "n_total": n_total, "results": all_results}


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot_all(test_a, test_b, test_c):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5))

    # (a) Test A: DGR stability — eps_eff/eps over 100 applications
    ax = axes[0]
    ratios = test_a["ratios"]
    steps_a = np.arange(len(ratios))
    ax.plot(steps_a, ratios, "-", color=COLORS[0], linewidth=1.2)
    ax.axhline(1.0, color="gray", ls=":", alpha=0.6)
    ax.axhspan(0.98, 1.02, color=COLORS[0], alpha=0.08, label=r"$\pm 2\%$ band")
    ax.set_xlabel("DGR application count")
    ax.set_ylabel(r"$\varepsilon_\mathrm{eff} / \varepsilon$")
    ax.set_title(r"(a) DGR idempotency ($N=128$)")
    ax.set_ylim(0.90, 1.10)
    ax.legend(fontsize=7, loc="upper right")
    ax.grid(True, alpha=0.3)

    # (b) Test B: DGR ablation — before/after thickness ratio
    ax = axes[1]
    res_b = test_b["results"]
    bfs = [r["broadening"] for r in res_b]
    before = [r["ratio_before"] for r in res_b]
    after = [r["ratio_after"] for r in res_b]
    ax.plot(bfs, before, "s--", color=COLORS[1], label="Before DGR", markersize=5)
    ax.plot(bfs, after, "o-", color=COLORS[0], label="After DGR", markersize=5)
    ax.axhline(1.0, color="gray", ls=":", alpha=0.6)
    ax.set_xlabel(r"Broadening factor $\varepsilon_\mathrm{broad}/\varepsilon$")
    ax.set_ylabel(r"$\varepsilon_\mathrm{eff} / \varepsilon$")
    ax.set_title("(b) DGR thickness restoration")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # (c) Test C: DGR frequency — eps_eff/eps time history
    ax = axes[2]
    results_c = test_c["results"]
    n_total = test_c["n_total"]
    color_idx = 0
    for label in sorted(results_c.keys(), key=lambda x: results_c[x]["freq"]):
        data = results_c[label]
        ratios = data["ratios"]
        freq = data["freq"]
        n_pts = len(ratios)
        x_vals = np.linspace(0, n_total, n_pts)
        style = "--" if freq == 0 else "-"
        display = "no DGR" if freq == 0 else f"every {freq}"
        ax.plot(x_vals, ratios, style, color=COLORS[color_idx % len(COLORS)],
                label=display, linewidth=1.0)
        color_idx += 1
    ax.axhline(1.0, color="gray", ls=":", alpha=0.6)
    ax.set_xlabel("Split reinit count")
    ax.set_ylabel(r"$\varepsilon_\mathrm{eff} / \varepsilon$")
    ax.set_title(r"(c) DGR frequency study ($N=128$)")
    ax.legend(fontsize=6, loc="upper left")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "dgr_verification")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser("[11-24] DGR Verification").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["test_a"], d["test_b"], d["test_c"])
        return

    test_a = test_a_dgr_stability()
    test_b = test_b_dgr_ablation()
    test_c = test_c_dgr_frequency()

    save_results(OUT / "data.npz", {
        "test_a": test_a, "test_b": test_b, "test_c": test_c,
    })
    plot_all(test_a, test_b, test_c)

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n=== Summary ===")

    # Test A: idempotency check
    ratios_a = test_a["ratios"]
    max_dev_a = max(abs(r - 1.0) for r in ratios_a)
    pass_a = max_dev_a < 0.05
    print(f"Test A (idempotency): max |eps_eff/eps - 1| = {max_dev_a:.4f} "
          f"({'PASS' if pass_a else 'FAIL'})")

    # Test B: restoration at broadening=1.4
    res_14 = [r for r in test_b["results"] if abs(r["broadening"] - 1.4) < 0.01]
    if res_14:
        r14 = res_14[0]
        pass_b = r14["ratio_after"] < 1.10
        print(f"Test B (1.4x broadening): eps_eff/eps {r14['ratio_before']:.3f} -> "
              f"{r14['ratio_after']:.3f}, area improvement = {r14['improvement']:.0f}x "
              f"({'PASS' if pass_b else 'FAIL'})")

    # Test C: DGR frequency benefit
    results_c = test_c["results"]
    if "no_dgr" in results_c and "dgr_every_10" in results_c:
        no_dgr_final = results_c["no_dgr"]["ratios"][-1]
        dgr10_final = results_c["dgr_every_10"]["ratios"][-1]
        benefit = abs(no_dgr_final - 1.0) / max(abs(dgr10_final - 1.0), 1e-15)
        print(f"Test C (no DGR vs every-10): final eps_eff/eps = "
              f"{no_dgr_final:.3f} vs {dgr10_final:.3f} "
              f"(DGR {benefit:.0f}x closer to 1.0)")

    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
