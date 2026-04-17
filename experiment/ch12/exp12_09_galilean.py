#!/usr/bin/env python3
"""【12-9】Galilean invariance test for CLS advection (sigma=0).

Paper ref: §12.9 (sec:val_galilean)

Test A: Advect a circular interface through a uniform velocity field.
        After one full traversal the interface should return to its
        initial position with minimal deformation.

Test B: Same physical problem in a co-moving frame (u_bg = 0).
        The interface is stationary; any velocity that develops is
        purely numerical.

The difference between Test A and Test B quantifies Galilean invariance
violation in the CLS advection + projection pipeline.

Setup
-----
  Domain : [0, 1] x [0, 1],  periodic BC
  Droplet: R = 0.25, center (0.5, 0.5)
  sigma = 0  (no surface tension)
  rho_l / rho_g = 2
  Background velocity (Test A): (u_bg, v_bg) = (1, 0)
  Grid: N = 64

Metrics
-------
  - L2 shape error:  || psi(T) - psi(0) ||_2 / || psi(0) ||_2
  - Mass error:      | sum(psi(T)) - sum(psi(0)) | / sum(psi(0))
  - Max velocity perturbation (deviation from uniform field)

Output
------
  experiment/ch12/results/galilean/
    galilean.pdf         — psi snapshots + error time history
    galilean_data.npz    — raw data

Usage
-----
  python experiment/ch12/exp12_09_galilean.py
  python experiment/ch12/exp12_09_galilean.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)

try:
    from twophase.levelset.advection import DissipativeCCDAdvection
    _HAS_ADVECTION = True
except ImportError:
    _HAS_ADVECTION = False
    print("[WARN] DissipativeCCDAdvection not available")

OUT = experiment_dir(__file__)
NPZ_PATH = OUT / "galilean_data.npz"
FIG_PATH = OUT / "galilean.pdf"

# ── Parameters ───────────────────────────────────────────────────────────────
R      = 0.25
RHO_L  = 2.0
RHO_G  = 1.0
N      = 64
U_BG   = 1.0   # background velocity for Test A
V_BG   = 0.0
CFL    = 0.25
N_TRAVERSALS = 1  # number of full domain traversals


# ── Helpers ──────────────────────────────────────────────────────────────────

def _init_psi(X, Y, eps, xp=np):
    """Initialize circular interface psi via smoothed Heaviside."""
    phi = R - xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    return heaviside(xp, phi, eps)


# ── Test A: advection with uniform background flow ──────────────────────────

def run_test_a(N):
    """Advect circular psi through uniform (U_BG, V_BG) for one traversal."""
    if not _HAS_ADVECTION:
        print("  [Test A] SKIPPED — DissipativeCCDAdvection unavailable")
        return None

    backend = Backend()
    xp  = backend.xp
    h   = 1.0 / N
    eps = 1.5 * h
    dt  = CFL * h / max(abs(U_BG), abs(V_BG), 1e-14)

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type='periodic')
    advect = DissipativeCCDAdvection(backend, grid, ccd, bc='periodic')

    X, Y = grid.meshgrid()
    psi_0 = _init_psi(X, Y, eps, xp)
    psi   = psi_0.copy()

    # Uniform velocity field (constant, no projection needed for sigma=0)
    u = xp.full_like(X, U_BG)
    v = xp.full_like(X, V_BG)

    # Time for one full traversal: T = L / U_BG
    speed = np.sqrt(U_BG**2 + V_BG**2)
    T_total = N_TRAVERSALS * 1.0 / speed if speed > 0 else 0.0
    n_steps = max(1, int(np.ceil(T_total / dt)))
    dt_actual = T_total / n_steps  # adjust for exact traversal

    print(f"  [Test A] N={N}, dt={dt_actual:.5f}, n_steps={n_steps}, "
          f"T={T_total:.3f}")

    mass_0 = float(xp.sum(psi_0))
    shape_errors = []
    mass_errors  = []

    for step in range(n_steps):
        psi = advect.advance(psi, [u, v], dt_actual)

        # Track errors every 10 steps
        if (step + 1) % 10 == 0 or step == n_steps - 1:
            shape_err = float(xp.linalg.norm(psi - psi_0) /
                              max(float(xp.linalg.norm(psi_0)), 1e-14))
            mass_err  = float(abs(float(xp.sum(psi)) - mass_0) / max(mass_0, 1e-14))
            shape_errors.append((step + 1, shape_err))
            mass_errors.append((step + 1, mass_err))

    # Final metrics
    shape_err_final = float(xp.linalg.norm(psi - psi_0) /
                            max(float(xp.linalg.norm(psi_0)), 1e-14))
    mass_err_final  = float(abs(float(xp.sum(psi)) - mass_0) / max(mass_0, 1e-14))

    print(f"    shape L2 error = {shape_err_final:.4e}")
    print(f"    mass error     = {mass_err_final:.4e}")

    return {
        "psi_0":       backend.to_host(psi_0),
        "psi_final":   backend.to_host(psi),
        "shape_err":   shape_err_final,
        "mass_err":    mass_err_final,
        "shape_hist":  np.array(shape_errors),
        "mass_hist":   np.array(mass_errors),
        "n_steps":     n_steps,
        "dt":          dt_actual,
        "T_total":     T_total,
        "N":           N,
    }


# ── Test B: stationary interface (co-moving frame) ──────────────────────────

def run_test_b(N):
    """Stationary circular psi, no flow (u=v=0). Measure numerical drift."""
    if not _HAS_ADVECTION:
        print("  [Test B] SKIPPED — DissipativeCCDAdvection unavailable")
        return None

    backend = Backend()
    xp  = backend.xp
    h   = 1.0 / N
    eps = 1.5 * h
    dt  = CFL * h  # arbitrary (u=0, but we still step)

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type='periodic')
    advect = DissipativeCCDAdvection(backend, grid, ccd, bc='periodic')

    X, Y = grid.meshgrid()
    psi_0 = _init_psi(X, Y, eps, xp)
    psi   = psi_0.copy()

    u = xp.zeros_like(X)
    v = xp.zeros_like(X)

    # Same physical time as Test A
    speed_a = np.sqrt(U_BG**2 + V_BG**2)
    T_total = N_TRAVERSALS * 1.0 / speed_a if speed_a > 0 else 1.0
    n_steps = max(1, int(np.ceil(T_total / dt)))
    dt_actual = T_total / n_steps

    print(f"  [Test B] N={N}, dt={dt_actual:.5f}, n_steps={n_steps}, "
          f"T={T_total:.3f}")

    mass_0 = float(xp.sum(psi_0))
    shape_errors = []
    mass_errors  = []

    for step in range(n_steps):
        psi = advect.advance(psi, [u, v], dt_actual)

        if (step + 1) % 10 == 0 or step == n_steps - 1:
            shape_err = float(xp.linalg.norm(psi - psi_0) /
                              max(float(xp.linalg.norm(psi_0)), 1e-14))
            mass_err  = float(abs(float(xp.sum(psi)) - mass_0) / max(mass_0, 1e-14))
            shape_errors.append((step + 1, shape_err))
            mass_errors.append((step + 1, mass_err))

    shape_err_final = float(xp.linalg.norm(psi - psi_0) /
                            max(float(xp.linalg.norm(psi_0)), 1e-14))
    mass_err_final  = float(abs(float(xp.sum(psi)) - mass_0) / max(mass_0, 1e-14))

    print(f"    shape L2 error = {shape_err_final:.4e}")
    print(f"    mass error     = {mass_err_final:.4e}")

    return {
        "psi_0":       backend.to_host(psi_0),
        "psi_final":   backend.to_host(psi),
        "shape_err":   shape_err_final,
        "mass_err":    mass_err_final,
        "shape_hist":  np.array(shape_errors),
        "mass_hist":   np.array(mass_errors),
        "n_steps":     n_steps,
        "dt":          dt_actual,
        "T_total":     T_total,
        "N":           N,
    }


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot(results):
    apply_style()
    import matplotlib.pyplot as plt

    test_a = results.get("test_a")
    test_b = results.get("test_b")

    n_tests = sum(1 for t in [test_a, test_b] if t is not None)
    if n_tests == 0:
        print("  [WARN] No results to plot")
        return

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

    x1d = np.linspace(0, 1, N + 1)

    # ── Row 0: psi snapshots ──
    # Test A: initial
    if test_a is not None:
        ax = fig.add_subplot(gs[0, 0])
        ax.pcolormesh(x1d, x1d, test_a["psi_0"].T, cmap="Blues",
                      vmin=0, vmax=1, shading="auto")
        ax.contour(x1d, x1d, test_a["psi_0"].T, levels=[0.5],
                   colors="k", linewidths=1)
        ax.set_aspect("equal"); ax.set_title("Test A: initial $\\psi$")
        ax.tick_params(labelsize=7)

        # Test A: final
        ax = fig.add_subplot(gs[0, 1])
        ax.pcolormesh(x1d, x1d, test_a["psi_final"].T, cmap="Blues",
                      vmin=0, vmax=1, shading="auto")
        ax.contour(x1d, x1d, test_a["psi_final"].T, levels=[0.5],
                   colors="r", linewidths=1)
        ax.contour(x1d, x1d, test_a["psi_0"].T, levels=[0.5],
                   colors="k", linewidths=0.5, linestyles="--")
        ax.set_aspect("equal")
        ax.set_title(f"Test A: final $\\psi$ (shape err={test_a['shape_err']:.2e})")
        ax.tick_params(labelsize=7)

    # Test B: final
    if test_b is not None:
        ax = fig.add_subplot(gs[0, 2])
        ax.pcolormesh(x1d, x1d, test_b["psi_final"].T, cmap="Blues",
                      vmin=0, vmax=1, shading="auto")
        ax.contour(x1d, x1d, test_b["psi_final"].T, levels=[0.5],
                   colors="r", linewidths=1)
        ax.contour(x1d, x1d, test_b["psi_0"].T, levels=[0.5],
                   colors="k", linewidths=0.5, linestyles="--")
        ax.set_aspect("equal")
        ax.set_title(f"Test B: final $\\psi$ (shape err={test_b['shape_err']:.2e})")
        ax.tick_params(labelsize=7)

    # ── Row 1: error history ──
    ax_shape = fig.add_subplot(gs[1, 0])
    ax_mass  = fig.add_subplot(gs[1, 1])
    ax_table = fig.add_subplot(gs[1, 2])

    if test_a is not None and len(test_a["shape_hist"]) > 0:
        steps_a = test_a["shape_hist"][:, 0]
        ax_shape.semilogy(steps_a, test_a["shape_hist"][:, 1],
                          'b-o', ms=3, lw=1.2, label="Test A (moving)")
        ax_mass.semilogy(steps_a, test_a["mass_hist"][:, 1],
                         'b-o', ms=3, lw=1.2, label="Test A (moving)")

    if test_b is not None and len(test_b["shape_hist"]) > 0:
        steps_b = test_b["shape_hist"][:, 0]
        ax_shape.semilogy(steps_b, test_b["shape_hist"][:, 1],
                          'r-s', ms=3, lw=1.2, label="Test B (stationary)")
        ax_mass.semilogy(steps_b, test_b["mass_hist"][:, 1],
                         'r-s', ms=3, lw=1.2, label="Test B (stationary)")

    ax_shape.set_xlabel("Time step")
    ax_shape.set_ylabel("Shape L2 error (relative)")
    ax_shape.set_title("Shape Error History")
    ax_shape.legend(fontsize=8); ax_shape.grid(True, alpha=0.3)

    ax_mass.set_xlabel("Time step")
    ax_mass.set_ylabel("Mass error (relative)")
    ax_mass.set_title("Mass Conservation")
    ax_mass.legend(fontsize=8); ax_mass.grid(True, alpha=0.3)

    # Summary table
    ax_table.axis("off")
    rows_txt = ["Galilean Invariance Summary", "=" * 40]
    for name, t in [("Test A (moving)", test_a), ("Test B (stationary)", test_b)]:
        if t is not None:
            rows_txt.append(f"{name}:")
            rows_txt.append(f"  shape L2 err = {t['shape_err']:.4e}")
            rows_txt.append(f"  mass err     = {t['mass_err']:.4e}")
            rows_txt.append(f"  n_steps      = {t['n_steps']}")
            rows_txt.append(f"  dt           = {t['dt']:.5f}")
        else:
            rows_txt.append(f"{name}: SKIPPED")
        rows_txt.append("")

    if test_a is not None and test_b is not None:
        ratio = test_a["shape_err"] / max(test_b["shape_err"], 1e-30)
        rows_txt.append(f"Shape err ratio (A/B) = {ratio:.2f}")
        rows_txt.append("Galilean invariant if ratio ~ 1")

    ax_table.text(0.05, 0.95, "\n".join(rows_txt), transform=ax_table.transAxes,
                  fontsize=9, family="monospace", va="top",
                  bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    fig.suptitle(
        f"Galilean Invariance Test ($\\sigma=0$, CLS advection)\n"
        f"$N={N}$, $R={R}$, $\\rho_l/\\rho_g={int(RHO_L)}$, "
        f"$u_{{bg}}={U_BG}$, {N_TRAVERSALS} traversal(s)",
        fontsize=11,
    )

    save_figure(fig, FIG_PATH)


# ── I/O ──────────────────────────────────────────────────────────────────────

def save_npz(results):
    # Filter out None entries before saving
    filtered = {k: v for k, v in results.items() if v is not None}
    save_results(NPZ_PATH, filtered)


def load_npz():
    results = load_results(NPZ_PATH)
    for r in results.values():
        if not isinstance(r, dict):
            continue
        for k in ("shape_err", "mass_err", "dt", "T_total"):
            if k in r:
                r[k] = float(r[k])
        for k in ("n_steps", "N"):
            if k in r:
                r[k] = int(r[k])
    return results


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  [12-9] Galilean Invariance Test (sigma=0, CLS advection)")
    print("=" * 80 + "\n")

    results = {}
    results["test_a"] = run_test_a(N)
    results["test_b"] = run_test_b(N)

    save_npz(results)
    plot(results)

    print("\n  Done.")


if __name__ == "__main__":
    args = experiment_argparser("Galilean invariance test").parse_args()

    if args.plot_only:
        results = load_npz()
        plot(results)
    else:
        main()
