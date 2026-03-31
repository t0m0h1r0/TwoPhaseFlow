"""
ψ-Direct Curvature Verification Experiment
============================================
Compares three curvature computation paths:

  Path A (φ-exact): CCD on exact SDF φ → κ  (ideal baseline, §10 existing)
  Path B (φ-via-inversion): ψ→φ logit→ CCD → κ  (legacy, §10 existing)
  Path C (ψ-direct, §3b eq:curvature_psi_2d): CCD on ψ → κ  (new recommended)

Tests:
  1. Circle (R=0.25): κ_exact = -1/R = -4.0
  2. Sinusoidal interface y = 0.5 + A sin(2πx), A=0.05
  3. ε_eff diagnostic (eq:epsilon_eff)

Grid sizes: N = 16, 32, 64, 128, 256
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
from twophase.levelset.heaviside import heaviside, invert_heaviside

# ── Parameters ────────────────────────────────────────────────────────────────

N_VALUES = [16, 32, 64, 128, 256]
PSI_MIN  = 0.01      # hybrid threshold (§3b)
EPS_NORM = 1e-3      # regularisation floor for φ-based path


# ── Shared helpers ────────────────────────────────────────────────────────────

def _ccd_curvature_2d(ccd, field):
    """Compute 2D curvature from any scalar field using CCD.

    κ = -[f_y² f_xx - 2 f_x f_y f_xy + f_x² f_yy] / (f_x² + f_y²)^{3/2}
    """
    f_x, f_xx = ccd.differentiate(field, axis=0)
    f_y, f_yy = ccd.differentiate(field, axis=1)
    f_xy, _ = ccd.differentiate(np.asarray(f_x), axis=1)

    f_x  = np.asarray(f_x)
    f_y  = np.asarray(f_y)
    f_xx = np.asarray(f_xx)
    f_yy = np.asarray(f_yy)
    f_xy = np.asarray(f_xy)

    num = f_y**2 * f_xx - 2.0 * f_x * f_y * f_xy + f_x**2 * f_yy
    grad_sq = f_x**2 + f_y**2

    return num, grad_sq, f_x, f_y


def _make_grid_and_ccd(N):
    """Create uniform N×N grid and CCD solver."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    X, Y = grid.meshgrid()
    return ccd, X, Y, grid


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: Circular interface
# ═══════════════════════════════════════════════════════════════════════════════

R_CIRCLE = 0.25
CENTER   = (0.5, 0.5)


def circle_convergence():
    """Run circle curvature convergence for three paths."""
    print("=" * 80)
    print("Test 1: Circular Interface (R=0.25, κ_exact = -1/r pointwise)")
    print("  Path A: φ-exact (CCD on true SDF)")
    print("  Path B: ψ→φ logit→κ (legacy)")
    print("  Path C: ψ-direct→κ (§3b recommended)")
    print("=" * 80)

    header = (f"  {'N':>5}  {'A:φ-exact':>12} {'ord':>5}  "
              f"{'B:φ-logit':>12} {'ord':>5}  "
              f"{'C:ψ-direct':>12} {'ord':>5}")
    print(header)

    results = []
    prev = [None, None, None]

    for N in N_VALUES:
        h = 1.0 / N
        eps = 1.5 * h

        ccd, X, Y, grid = _make_grid_and_ccd(N)

        # Exact SDF
        r = np.sqrt((X - CENTER[0])**2 + (Y - CENTER[1])**2)
        phi_exact = r - R_CIRCLE
        psi = heaviside(np, phi_exact, eps)

        # Analytic curvature: κ = -1/r (for concentric circle level sets)
        kappa_exact = -1.0 / np.where(r > 1e-12, r, 1e-12)

        # Error mask: narrow band |φ| < 2h (well-resolved zone)
        band = np.abs(phi_exact) < 2.0 * h
        if band.sum() < 5:
            results.append((N, h, np.nan, np.nan, np.nan))
            print(f"  {N:>5}  (insufficient band points)")
            continue

        # Path A: φ-exact → CCD → κ
        num_a, gs_a, _, _ = _ccd_curvature_2d(ccd, phi_exact)
        denom_a = np.sqrt(np.maximum(gs_a, EPS_NORM**2))**3
        kappa_a = -num_a / denom_a
        err_a = float(np.max(np.abs(kappa_a[band] - kappa_exact[band])))

        # Path B: ψ → φ logit → CCD → κ
        phi_inv = invert_heaviside(np, psi, eps)
        num_b, gs_b, _, _ = _ccd_curvature_2d(ccd, phi_inv)
        denom_b = np.sqrt(np.maximum(gs_b, EPS_NORM**2))**3
        kappa_b = -num_b / denom_b
        err_b = float(np.max(np.abs(kappa_b[band] - kappa_exact[band])))

        # Path C: ψ → CCD → κ (direct, §3b)
        num_c, gs_c, _, _ = _ccd_curvature_2d(ccd, psi)
        denom_c = (gs_c + 1e-30)**1.5
        kappa_c = -num_c / denom_c
        # Hybrid masking
        far = (psi <= PSI_MIN) | (psi >= 1.0 - PSI_MIN)
        kappa_c[far] = 0.0
        # Only compare within ψ-valid zone AND narrow band
        mask_c = band & ~far
        err_c = float(np.max(np.abs(kappa_c[mask_c] - kappa_exact[mask_c]))) if mask_c.sum() > 0 else np.nan

        results.append((N, h, err_a, err_b, err_c))

        # Compute orders
        orders = []
        for i, (err, p) in enumerate(zip([err_a, err_b, err_c], prev)):
            if p is not None and not np.isnan(err) and err > 0:
                orders.append(np.log2(p / err))
            else:
                orders.append(np.nan)
            prev[i] = err

        def _fmt(e, o):
            e_s = f"{e:>12.4e}" if not np.isnan(e) else "         nan"
            o_s = f"{o:>5.2f}" if not np.isnan(o) else "  ---"
            return f"{e_s} {o_s}"

        print(f"  {N:>5}  {_fmt(err_a, orders[0])}  {_fmt(err_b, orders[1])}  {_fmt(err_c, orders[2])}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Sinusoidal interface
# ═══════════════════════════════════════════════════════════════════════════════

A_SIN = 0.05


def _sinusoidal_exact_curvature(x):
    """Level-set curvature for φ = y - f(x), f(x) = A sin(2πx).

    κ = -(φ_y² φ_xx - ... ) / |∇φ|³ = f''/(1+f'^2)^{3/2}
    """
    f_pp = -A_SIN * (2.0 * np.pi)**2 * np.sin(2.0 * np.pi * x)
    f_p  =  A_SIN * 2.0 * np.pi * np.cos(2.0 * np.pi * x)
    return f_pp / (1.0 + f_p**2)**1.5


def sinusoidal_convergence():
    """Run sinusoidal interface curvature convergence for three paths."""
    print("\n" + "=" * 80)
    print(f"Test 2: Sinusoidal Interface y = 0.5 + {A_SIN}*sin(2πx)")
    print("=" * 80)

    header = (f"  {'N':>5}  {'A:φ-exact':>12} {'ord':>5}  "
              f"{'B:φ-logit':>12} {'ord':>5}  "
              f"{'C:ψ-direct':>12} {'ord':>5}")
    print(header)

    results = []
    prev = [None, None, None]

    for N in N_VALUES:
        h = 1.0 / N
        eps = 1.5 * h

        ccd, X, Y, grid = _make_grid_and_ccd(N)

        # φ = y - f(x) (not exact SDF, but level sets are correct)
        y_intf = 0.5 + A_SIN * np.sin(2.0 * np.pi * X)
        phi = Y - y_intf
        psi = heaviside(np, phi, eps)

        # Analytic curvature (function of x only, constant along y for φ = y-f(x))
        kappa_exact_1d = _sinusoidal_exact_curvature(X[:, 0])
        kappa_exact_2d = np.broadcast_to(kappa_exact_1d[:, np.newaxis], X.shape).copy()

        # Narrow band: |φ| < h
        band = np.abs(phi) < h

        if band.sum() < 5:
            results.append((N, h, np.nan, np.nan, np.nan))
            print(f"  {N:>5}  (insufficient band points)")
            continue

        # Path A: φ (vertical distance) → CCD → κ
        num_a, gs_a, _, _ = _ccd_curvature_2d(ccd, phi)
        denom_a = np.sqrt(np.maximum(gs_a, EPS_NORM**2))**3
        kappa_a = -num_a / denom_a
        err_a = float(np.max(np.abs(kappa_a[band] - kappa_exact_2d[band])))

        # Path B: ψ → φ logit → CCD → κ
        phi_inv = invert_heaviside(np, psi, eps)
        num_b, gs_b, _, _ = _ccd_curvature_2d(ccd, phi_inv)
        denom_b = np.sqrt(np.maximum(gs_b, EPS_NORM**2))**3
        kappa_b = -num_b / denom_b
        err_b = float(np.max(np.abs(kappa_b[band] - kappa_exact_2d[band])))

        # Path C: ψ-direct → κ
        num_c, gs_c, _, _ = _ccd_curvature_2d(ccd, psi)
        denom_c = (gs_c + 1e-30)**1.5
        kappa_c = -num_c / denom_c
        far = (psi <= PSI_MIN) | (psi >= 1.0 - PSI_MIN)
        kappa_c[far] = 0.0
        mask_c = band & ~far
        err_c = float(np.max(np.abs(kappa_c[mask_c] - kappa_exact_2d[mask_c]))) if mask_c.sum() > 0 else np.nan

        results.append((N, h, err_a, err_b, err_c))

        orders = []
        for i, (err, p) in enumerate(zip([err_a, err_b, err_c], prev)):
            if p is not None and not np.isnan(err) and err > 0:
                orders.append(np.log2(p / err))
            else:
                orders.append(np.nan)
            prev[i] = err

        def _fmt(e, o):
            e_s = f"{e:>12.4e}" if not np.isnan(e) else "         nan"
            o_s = f"{o:>5.2f}" if not np.isnan(o) else "  ---"
            return f"{e_s} {o_s}"

        print(f"  {N:>5}  {_fmt(err_a, orders[0])}  {_fmt(err_b, orders[1])}  {_fmt(err_c, orders[2])}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: ε_eff diagnostic
# ═══════════════════════════════════════════════════════════════════════════════

def epsilon_eff_diagnostic():
    """Evaluate ε_eff = ψ(1-ψ)/|∇ψ| at interface zone."""
    print("\n" + "=" * 80)
    print("Test 3: ε_eff Profile Quality Diagnostic (eq:epsilon_eff)")
    print("=" * 80)

    for N in [64, 128, 256]:
        h = 1.0 / N
        eps = 1.5 * h

        ccd, X, Y, grid = _make_grid_and_ccd(N)
        r = np.sqrt((X - CENTER[0])**2 + (Y - CENTER[1])**2)
        phi_exact = r - R_CIRCLE
        psi = heaviside(np, phi_exact, eps)

        psi_x, _ = ccd.differentiate(psi, axis=0)
        psi_y, _ = ccd.differentiate(psi, axis=1)
        psi_x = np.asarray(psi_x)
        psi_y = np.asarray(psi_y)
        grad_psi = np.sqrt(psi_x**2 + psi_y**2)

        mask = (psi > PSI_MIN) & (psi < 1.0 - PSI_MIN) & (grad_psi > 1e-12)
        eps_eff = psi[mask] * (1.0 - psi[mask]) / grad_psi[mask]
        ratio = eps_eff / eps

        print(f"\n  N = {N}, ε = {eps:.6f} (= 1.5h), interface pts = {mask.sum()}")
        print(f"    ε_eff/ε:  mean={np.mean(ratio):.6f}  std={np.std(ratio):.6f}"
              f"  min={np.min(ratio):.6f}  max={np.max(ratio):.6f}")


# ═══════════════════════════════════════════════════════════════════════════════
# Figures
# ═══════════════════════════════════════════════════════════════════════════════

def make_circle_figure(results, out_path):
    Ns   = [r[0] for r in results if not np.isnan(r[2])]
    err_a = [r[2] for r in results if not np.isnan(r[2])]
    err_b = [r[3] for r in results if not np.isnan(r[2])]
    err_c = [r[4] for r in results if not np.isnan(r[2])]
    if len(Ns) < 2:
        return

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.loglog(Ns, err_a, "^-",  color="C2", label=r"A: $\phi$-exact")
    ax.loglog(Ns, err_b, "o--", color="C1", label=r"B: $\psi \to \phi$ logit")
    ax.loglog(Ns, err_c, "s-",  color="C0", label=r"C: $\psi$-direct (§3b)")

    Ns_ref = np.array([Ns[0], Ns[-1]], dtype=float)
    ax.loglog(Ns_ref, err_a[0] * (Ns_ref / Ns[0])**(-6),
              "k:", lw=0.8, label=r"$O(h^6)$")

    ax.set_xlabel("$N$")
    ax.set_ylabel(r"$\|\kappa - \kappa_{\rm exact}\|_\infty$")
    ax.set_title(r"Circle Curvature: $\phi$-exact vs logit vs $\psi$-direct")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure saved: {out_path}")
    plt.close(fig)


def make_sinusoidal_figure(results, out_path):
    Ns   = [r[0] for r in results if not np.isnan(r[2])]
    err_a = [r[2] for r in results if not np.isnan(r[2])]
    err_b = [r[3] for r in results if not np.isnan(r[2])]
    err_c = [r[4] for r in results if not np.isnan(r[2])]
    if len(Ns) < 2:
        return

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.loglog(Ns, err_a, "^-",  color="C2", label=r"A: $\phi$-exact")
    ax.loglog(Ns, err_b, "o--", color="C1", label=r"B: $\psi \to \phi$ logit")
    ax.loglog(Ns, err_c, "s-",  color="C0", label=r"C: $\psi$-direct (§3b)")

    Ns_ref = np.array([Ns[0], Ns[-1]], dtype=float)
    ax.loglog(Ns_ref, err_a[0] * (Ns_ref / Ns[0])**(-5),
              "k:", lw=0.8, label=r"$O(h^5)$")

    ax.set_xlabel("$N$")
    ax.set_ylabel(r"$\|\kappa - \kappa_{\rm exact}\|_\infty$")
    ax.set_title(r"Sinusoidal Curvature: $\phi$-exact vs logit vs $\psi$-direct")
    ax.legend(fontsize=9)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure saved: {out_path}")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    circle_results = circle_convergence()
    sin_results = sinusoidal_convergence()
    epsilon_eff_diagnostic()

    out_dir = os.path.join(os.path.dirname(__file__), "..", "paper", "figures")
    os.makedirs(out_dir, exist_ok=True)
    make_circle_figure(circle_results, os.path.join(out_dir, "curvature_psi_vs_phi_circle.pdf"))
    make_sinusoidal_figure(sin_results, os.path.join(out_dir, "curvature_psi_vs_phi_sinusoidal.pdf"))

    print("\n" + "=" * 80)
    print("DONE — All tests completed.")
    print("=" * 80)
