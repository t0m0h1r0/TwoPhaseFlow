"""
CCD Curvature Convergence Experiment
=====================================
Verifies that the CCD-based curvature estimator achieves O(h^5–6)
asymptotic convergence for a 2-D circular interface.

Problem
-------
Circle of radius R = 0.5 centred at (0.5, 0.5) in the unit square.
Paper setup: h = 2R/N = 1/N, κ_exact = −1/R = −2.

Method
------
- Build φ = sqrt((x−0.5)² + (y−0.5)²) − R on an N×N grid.
- Compute κ via the explicit 2-D formula (§2.6 Eq. 30) using CCDSolver:
    κ = −(φ_y² φ_xx − 2φ_x φ_y φ_xy + φ_x² φ_yy) / (φ_x² + φ_y²)^{3/2}
- Compare to point-wise analytic κ(x,y) = −1/r (r = dist. from centre)
  on the thin interface zone |φ| < h (half grid-spacing either side).
- Grid sizes: N = 16, 32, 64, 128, 256.

Note on convergence
-------------------
For N ≥ 64 (≥8 cells per radius) the nonlinear curvature formula enters
the asymptotic O(h^5–6) regime.  Coarser grids show pre-asymptotic
behaviour due to the product structure of the curvature formula.
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

R       = 0.5       # circle radius  (paper setup: h = 2R/N = 1/N)
CENTER  = (0.5, 0.5)
KAPPA_EXACT = -1.0 / R    # = −2.0
N_VALUES = [16, 32, 64, 128, 256]

# ── Core computation ──────────────────────────────────────────────────────────

def curvature_error(N: int) -> float:
    """Return L∞ curvature error on interface zone for an N×N grid."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    X, Y = grid.meshgrid()
    cx, cy = CENTER
    phi = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - R   # shape (N+1, N+1)

    # CCD derivatives along each axis
    phi_x, phi_xx = ccd.differentiate(phi, axis=0)
    phi_y, phi_yy = ccd.differentiate(phi, axis=1)
    # Cross derivative: d²φ/dxdy via differentiate(φ_x, axis=1)
    phi_xy, _ = ccd.differentiate(np.asarray(phi_x), axis=1)

    phi_x  = np.asarray(phi_x)
    phi_y  = np.asarray(phi_y)
    phi_xx = np.asarray(phi_xx)
    phi_yy = np.asarray(phi_yy)
    phi_xy = np.asarray(phi_xy)

    # 2-D curvature formula  §2.6 Eq. 30
    num = phi_y ** 2 * phi_xx - 2.0 * phi_x * phi_y * phi_xy + phi_x ** 2 * phi_yy
    denom = (phi_x ** 2 + phi_y ** 2) ** 1.5
    eps_reg = 1e-8  # regularisation against division by zero far from interface
    kappa = -num / np.where(denom > eps_reg, denom, eps_reg)

    # Point-wise analytic curvature: κ(x,y) = −1/r  (signed-dist sphere formula)
    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    kappa_analytic = -1.0 / np.where(r > 1e-12, r, 1e-12)

    # Thin zone: |φ| < h (one cell width either side of the circle).
    # Points here have the smallest geometric offset, giving the cleanest
    # comparison to the point-wise analytic κ = −1/r.
    h = 1.0 / N
    mask = (np.abs(phi) < h) & (r > 0.05)
    if mask.sum() == 0:
        return float("nan")
    return float(np.max(np.abs(kappa[mask] - kappa_analytic[mask])))


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("CCD Curvature Convergence Test")
    print(f"  Circle: R={R}, κ_exact={KAPPA_EXACT:.4f}")
    print(f"  Error zone: |φ| < h (one cell width), compare to κ=-1/r")
    print("=" * 60)
    print(f"  {'N':>5}  {'E_κ (L∞)':>14}  {'order p':>10}  {'n_pts':>7}")

    results = []
    prev_E = None
    for N in N_VALUES:
        E = curvature_error(N)
        p = np.log2(prev_E / E) if (prev_E and not np.isnan(E)) else float("nan")
        results.append((N, E, p))
        p_str = f"{p:.2f}" if not np.isnan(p) else "   ---"
        print(f"  {N:>5}  {E:>14.4e}  {p_str:>10}")
        prev_E = E

    return results


def make_figure(results: list, out_path: str):
    Ns = [r[0] for r in results if not np.isnan(r[1])]
    Es = [r[1] for r in results if not np.isnan(r[1])]
    if not Ns:
        return

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.loglog(Ns, Es, "o-", label=r"CCD $\kappa$ error")
    # Reference slope O(h^6)
    Ns_ref = np.array([Ns[0], Ns[-1]], dtype=float)
    ax.loglog(Ns_ref, Es[0] * (Ns_ref / Ns[0]) ** (-6),
              "k--", lw=0.9, label=r"$O(h^6)$")
    ax.set_xlabel("$N$")
    ax.set_ylabel(r"$\|\kappa - \kappa_{\rm exact}\|_\infty$")
    ax.set_title(r"Curvature Convergence: CCD on Circle ($R=0.25$)")
    ax.legend()
    ax.grid(True, which="both", ls=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure saved: {out_path}")
    plt.close(fig)


if __name__ == "__main__":
    results = run()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "paper", "figures")
    os.makedirs(out_dir, exist_ok=True)
    make_figure(results, os.path.join(out_dir, "ccd_curvature_convergence.pdf"))
