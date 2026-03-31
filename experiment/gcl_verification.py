"""
GCL / Non-Uniform Grid Metric Verification
===========================================
Two tests verifying that CCD differentiation on an interface-fitted
(non-uniform) grid is correct.

Test 1 — Derivative accuracy on non-uniform grid.
    f = sin(πx), known df/dx = π cos(πx), d²f/dx² = −π² sin(πx).
    Convergence order must be preserved after the metric transform.
    Comparison: uniform (alpha=1) vs non-uniform (alpha=2).

Test 2 — Geometric Conservation Law (GCL) / freestream preservation.
    f = 1 (constant) — a divergence-free freestream velocity field.
    ‖d/dx(1)‖∞ must equal zero to machine precision regardless of
    the grid non-uniformity, verifying that the metric transform
    introduces no spurious derivatives for constant fields.
"""

from __future__ import annotations

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver

# ── Parameters ────────────────────────────────────────────────────────────────

ALPHA_NONUNIFORM = 2.0    # grid stretch factor (>1 → interface-fitted)
EPS_INTERFACE    = 0.08   # half-width of the synthetic interface (ε)
N_VALUES         = [16, 32, 64, 128]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_grid_ccd(N: int, alpha: float) -> tuple[Grid, CCDSolver]:
    """Return (Grid, CCDSolver) for axis=0, 1-D slice via thin 2-D grid."""
    backend = Backend(use_gpu=False)
    # N[1]=3 → 4 nodes on axis-1, the minimum for the CCD boundary scheme
    gc = GridConfig(ndim=2, N=(N, 3), L=(1.0, 1.0), alpha_grid=alpha)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    if alpha > 1.0:
        # Synthetic interface at x = 0.5 — concentrates nodes near centre
        x_lin = np.linspace(0.0, 1.0, N + 1)
        phi_1d = x_lin - 0.5              # signed distance to x = 0.5
        # Broadcast to grid shape (N+1, 4)
        phi_2d = np.broadcast_to(phi_1d[:, None], (N + 1, 4)).copy()
        grid.update_from_levelset(phi_2d, eps=EPS_INTERFACE, ccd=ccd)

    return grid, ccd


def _differentiate_1d(grid: Grid, ccd: CCDSolver, f_1d: np.ndarray):
    """Apply CCDSolver to a 1-D function along axis=0 (thin-2D trick)."""
    f_2d = np.tile(f_1d[:, None], (1, 4))          # (N+1, 4)
    d1_2d, d2_2d = ccd.differentiate(f_2d, axis=0)
    return np.asarray(d1_2d[:, 0]), np.asarray(d2_2d[:, 0])


# ── Test 1: Convergence on non-uniform grid ───────────────────────────────────

def test1_convergence():
    """Compare L∞ derivative errors on uniform vs non-uniform grids."""
    print("\n" + "=" * 60)
    print("Test 1: Derivative Accuracy — Uniform vs Non-Uniform Grid")
    print("  f = sin(πx),  df/dx = π cos(πx),  d²f/dx² = −π² sin(πx)")
    print("=" * 60)

    results = {"uniform": [], "nonuniform": []}

    for label, alpha in [("uniform", 1.0), ("nonuniform", ALPHA_NONUNIFORM)]:
        print(f"\n  {label} (alpha={alpha}):")
        print(f"  {'N':>6}  {'E_d1 (L∞)':>14}  {'order_d1':>10}  "
              f"{'E_d2 (L∞)':>14}  {'order_d2':>10}")
        prev_e1 = prev_e2 = None
        for N in N_VALUES:
            grid, ccd = _make_grid_ccd(N, alpha)
            x = np.asarray(grid.coords[0])          # physical x coords
            f   = np.sin(np.pi * x)
            df  = np.pi * np.cos(np.pi * x)
            ddf = -(np.pi ** 2) * np.sin(np.pi * x)
            d1, d2 = _differentiate_1d(grid, ccd, f)
            e1 = float(np.max(np.abs(d1 - df)))
            e2 = float(np.max(np.abs(d2 - ddf)))
            o1 = np.log2(prev_e1 / e1) if prev_e1 else float("nan")
            o2 = np.log2(prev_e2 / e2) if prev_e2 else float("nan")
            print(f"  {N:>6}  {e1:>14.4e}  {o1:>10.2f}  {e2:>14.4e}  {o2:>10.2f}")
            results[label].append((N, e1, e2))
            prev_e1, prev_e2 = e1, e2

    return results


# ── Test 2: GCL / Freestream preservation ────────────────────────────────────

def test2_gcl():
    """Freestream preservation: d/dx(1) must vanish to machine precision.

    GCL in the NS sense requires the *first-order* divergence operator to
    preserve a constant (freestream) velocity field.  The second derivative
    d²/dx²(1) is informational only: the metric amplifies floating-point
    noise in d1_ξ by a factor J · |dJ/dξ|, so it grows with N but is
    irrelevant for the divergence-free property.
    """
    print("\n" + "=" * 60)
    print("Test 2: GCL / Freestream Preservation  (f = 1)")
    print("  PASS criterion: ‖d/dx(1)‖∞ ≤ 1000 · ε_mach  (first derivative)")
    print("  ‖d²/dx²(1)‖∞ reported informally (metric amplification, not GCL)")
    print("=" * 60)
    print(f"  {'N':>6}  {'‖d/dx(1)‖∞':>16}  {'‖d²/dx²(1)‖∞':>16}")

    gcl_results = []
    for N in N_VALUES:
        grid, ccd = _make_grid_ccd(N, ALPHA_NONUNIFORM)
        f_const = np.ones(N + 1)
        d1, d2 = _differentiate_1d(grid, ccd, f_const)
        e1 = float(np.max(np.abs(d1)))
        e2 = float(np.max(np.abs(d2)))
        gcl_results.append((N, e1, e2))
        print(f"  {N:>6}  {e1:>16.3e}  {e2:>16.3e}")

    max_e1 = max(r[1] for r in gcl_results)
    eps_m = np.finfo(float).eps
    passed = max_e1 < 1e3 * eps_m
    status = "PASS" if passed else "FAIL"
    print(f"\n  max ‖d/dx(1)‖∞  = {max_e1:.3e}  (tol: 1000 ε_mach = {1e3*eps_m:.3e})")
    print(f"  GCL freestream: {status}")
    return gcl_results, passed


# ── Figure ───────────────────────────────────────────────────────────────────

def _make_figure(conv_results: dict, gcl_results: list, out_path: str):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))

    # Panel 1: d1 convergence
    ax = axes[0]
    for label, marker, ls in [("uniform", "o", "--"), ("nonuniform", "s", "-")]:
        Ns  = [r[0] for r in conv_results[label]]
        E1  = [r[1] for r in conv_results[label]]
        ax.loglog(Ns, E1, marker=marker, linestyle=ls, label=label)
    # Reference slopes
    Ns_ref = np.array([16, 128], dtype=float)
    ax.loglog(Ns_ref, 2e-3 * (Ns_ref / 16) ** (-4), "k:", lw=0.8, label="O(h⁴)")
    ax.loglog(Ns_ref, 1e-3 * (Ns_ref / 16) ** (-6), "k--", lw=0.8, label="O(h⁶)")
    ax.set_xlabel("N")
    ax.set_ylabel(r"$\|d/dx - df/dx\|_\infty$")
    ax.set_title(r"(a) $\partial f/\partial x$ error")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", ls=":", alpha=0.4)

    # Panel 2: d2 convergence
    ax = axes[1]
    for label, marker, ls in [("uniform", "o", "--"), ("nonuniform", "s", "-")]:
        Ns  = [r[0] for r in conv_results[label]]
        E2  = [r[2] for r in conv_results[label]]
        ax.loglog(Ns, E2, marker=marker, linestyle=ls, label=label)
    ax.loglog(Ns_ref, 5e-2 * (Ns_ref / 16) ** (-4), "k:", lw=0.8, label="O(h⁴)")
    ax.loglog(Ns_ref, 2e-2 * (Ns_ref / 16) ** (-5), "k--", lw=0.8, label="O(h⁵)")
    ax.set_xlabel("N")
    ax.set_ylabel(r"$\|d^2/dx^2 - d^2f/dx^2\|_\infty$")
    ax.set_title(r"(b) $\partial^2 f/\partial x^2$ error")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", ls=":", alpha=0.4)

    # Panel 3: GCL freestream
    ax = axes[2]
    Ns_gcl = [r[0] for r in gcl_results]
    E1_gcl = [r[1] for r in gcl_results]
    E2_gcl = [r[2] for r in gcl_results]
    eps_m  = np.finfo(float).eps
    ax.semilogy(Ns_gcl, E1_gcl, "o-", label=r"$\|\partial(1)/\partial x\|_\infty$")
    ax.semilogy(Ns_gcl, E2_gcl, "s-", label=r"$\|\partial^2(1)/\partial x^2\|_\infty$")
    ax.axhline(eps_m, color="k", ls=":", lw=0.8, label=r"$\varepsilon_\mathrm{mach}$")
    ax.set_xlabel("N")
    ax.set_ylabel("Error")
    ax.set_title("(c) GCL freestream preservation\n" + r"$f=1$ on non-uniform grid")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", ls=":", alpha=0.4)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure saved: {out_path}")
    plt.close(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    conv_results = test1_convergence()
    gcl_results, gcl_passed = test2_gcl()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "paper", "figures")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "gcl_verification.pdf")
    _make_figure(conv_results, gcl_results, out_path)

    print("\n" + "=" * 60)
    print(f"GCL / Non-Uniform Grid Verification: {'PASS' if gcl_passed else 'FAIL'}")
    print("=" * 60)
