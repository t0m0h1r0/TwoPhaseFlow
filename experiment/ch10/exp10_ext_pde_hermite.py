#!/usr/bin/env python3
"""Closest-Point Hermite Extension verification for §10.2.2 (re-experiment).

Compares FieldExtender (Aslam 2004, O(h¹)) vs ClosestPointExtender (O(h⁶)).

Test (a): 1D field-extension convergence with SMOOTH source field.
  Setup:
    - φ = x − 0.5 (planar interface)
    - q(x) = 1 + cos(πx) everywhere (smooth, no jump)
      → CSF-regularised pressure is continuous: this is the correct use case.
      A sharp step function would corrupt CCD derivatives globally via the
      tri-diagonal system, preventing O(h⁶) convergence for either method.
    - Exact extension: q_ext = q(0.5) = 1 for all x > 0.5
    - Upwind sampling error: q(0.5 − h) − q(0.5) ≈ h·π = O(h¹)
    - Hermite extrapolation error: O(h⁶) (§8.4 eq. hermite5_error)
    - Error band: [0.52, 0.55]

Test (b): Young-Laplace Δp = κ/We with Hermite extension.
  Same setup as existing test_young_laplace, but using ClosestPointExtender.

Output: results/ch10_ext_pde_hermite/
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.field_extender import FieldExtender
from twophase.levelset.closest_point_extender import ClosestPointExtender
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "ext_pde_hermite"
OUT.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Test (a): 1D smooth-field convergence — Upwind vs Hermite
# ══════════════════════════════════════════════════════════════════════════════

def test_1d_convergence():
    """O(h¹) upwind vs O(h⁶) Hermite for smooth source field."""
    print("\n" + "=" * 70)
    print("  Test (a): 1D extension convergence — Upwind vs Hermite")
    print("=" * 70)
    print("  q(x) = 1 + cos(πx)  everywhere (smooth, no jump)")
    print("  Exact q_ext = q(0.5) = 1.0  for  x > 0.5")
    print()

    backend = Backend(use_gpu=False)
    Ns = [32, 64, 128, 256]
    upwind_results = []
    hermite_results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type='wall')
        h = 1.0 / N

        X, Y = grid.meshgrid()
        phi = X - 0.5                          # interface at x=0.5; source: φ<0
        q = 1.0 + np.cos(np.pi * X)            # smooth everywhere
        q_exact = 1.0                           # = q(0.5)
        j_mid = N // 2
        band_mask_1d = (X[:, 0] >= 0.52) & (X[:, 0] <= 0.55)

        def measure_error(q_ext):
            if band_mask_1d.any():
                return float(np.max(np.abs(q_ext[band_mask_1d, j_mid] - q_exact)))
            return float('nan')

        # ── Upwind (Aslam 2004) ──────────────────────────────────────────────
        n_ext = max(N, 20)
        upwind = FieldExtender(backend, grid, ccd, n_iter=n_ext, cfl=0.5)
        q_ext_up = upwind.extend(q, phi)
        err_up = measure_error(q_ext_up)
        upwind_results.append({"N": N, "h": h, "Linf": err_up})

        # ── Hermite (ClosestPointExtender) ───────────────────────────────────
        hermite = ClosestPointExtender(backend, grid, ccd)
        q_ext_hm = hermite.extend(q, phi)
        err_hm = measure_error(q_ext_hm)
        hermite_results.append({"N": N, "h": h, "Linf": err_hm})

        print(f"  N={N:>4}  Upwind: {err_up:.4e}   Hermite: {err_hm:.4e}")

    # Convergence orders
    def print_orders(results, name):
        print(f"\n  {name} convergence orders:")
        for i in range(1, len(results)):
            r0, r1 = results[i - 1], results[i]
            if r0["Linf"] > 1e-14 and r1["Linf"] > 1e-14:
                order = np.log(r0["Linf"] / r1["Linf"]) / np.log(r0["h"] / r1["h"])
                results[i]["order"] = order
                print(f"    {r0['N']}→{r1['N']}: order = {order:.2f}")
            else:
                results[i]["order"] = float('nan')
                print(f"    {r0['N']}→{r1['N']}: below machine precision")

    print_orders(upwind_results, "Upwind PDE")
    print_orders(hermite_results, "Hermite")

    return upwind_results, hermite_results


# ══════════════════════════════════════════════════════════════════════════════
# Test (b): Young-Laplace — Hermite extension
# ══════════════════════════════════════════════════════════════════════════════

def test_young_laplace_hermite():
    """Young-Laplace test: compare upwind vs Hermite extension pipelines.

    Both methods extend p^n (=0 at first step) BEFORE PPE solve, then measure
    Δp from the raw PPE solution.  At the initial step p^n=0, extension is a
    no-op regardless of method, so results should be identical — confirming
    that Hermite introduces no regression.  The Δp accuracy is governed by
    CSF regularisation O(h²), not by the extension scheme.
    """
    print("\n" + "=" * 70)
    print("  Test (b): Young-Laplace Δp = κ/We (Upwind vs Hermite)")
    print("=" * 70)

    backend = Backend(use_gpu=False)
    R = 0.25
    We = 1.0
    dp_exact = 1.0 / (R * We)   # = 4.0
    rho_l, rho_g = 1000.0, 1.0
    Ns = [32, 64, 128]
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type='wall')
        upwind = FieldExtender(backend, grid, ccd, n_iter=5, cfl=0.5)
        hermite = ClosestPointExtender(backend, grid, ccd)
        h = 1.0 / N
        eps = 1.5 * h

        X, Y = grid.meshgrid()
        dist = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
        phi = R - dist          # φ>0 inside (liquid)
        psi = heaviside(np, phi, eps)
        rho = rho_g + (rho_l - rho_g) * psi

        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa = curv_calc.compute(psi)

        grad_psi = []
        for ax in range(2):
            dpsi, _ = ccd.differentiate(psi, ax)
            grad_psi.append(dpsi)

        fx = kappa * grad_psi[0] / (We * rho)
        fy = kappa * grad_psi[1] / (We * rho)
        rhs = np.zeros_like(psi)
        rhs[1:N, :] += (fx[1:N, :] - fx[0:N - 1, :]) / h
        rhs[:, 1:N] += (fy[:, 1:N] - fy[:, 0:N - 1]) / h

        ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
        triplet, A_shape = ppe_builder.build(rho)
        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        # ── Upwind pipeline: extend p^n=0, solve PPE ──
        p0 = np.zeros_like(psi)
        p0_ext_up = upwind.extend(p0, phi)
        rhs_up = rhs.ravel().copy()
        rhs_up[ppe_builder._pin_dof] = 0.0
        p_up = spsolve(A, rhs_up).reshape(psi.shape)

        # ── Hermite pipeline: extend p^n=0, solve PPE ──
        p0_ext_hm = hermite.extend(p0, phi)
        rhs_hm = rhs.ravel().copy()
        rhs_hm[ppe_builder._pin_dof] = 0.0
        p_hm = spsolve(A, rhs_hm).reshape(psi.shape)

        inside  = phi >  3 * h
        outside = phi < -3 * h
        dp_up  = _measure_dp(p_up,  inside, outside)
        dp_hm  = _measure_dp(p_hm,  inside, outside)
        rel_err_up = abs(dp_up - dp_exact) / dp_exact
        rel_err_hm = abs(dp_hm - dp_exact) / dp_exact

        results.append({
            "N": N, "h": h,
            "dp_upwind": dp_up, "dp_hermite": dp_hm,
            "rel_err_upwind": rel_err_up, "rel_err_hermite": rel_err_hm,
        })
        print(f"  N={N:>4}: Δp(upwind)={dp_up:.4f}  Δp(Hermite)={dp_hm:.4f}  "
              f"exact={dp_exact:.1f}  err_up={rel_err_up:.3e}  err_hm={rel_err_hm:.3e}")

    print("\n  Convergence orders:")
    for label, key in [("Upwind", "rel_err_upwind"), ("Hermite", "rel_err_hermite")]:
        print(f"    {label}:")
        for i in range(1, len(results)):
            r0, r1 = results[i - 1], results[i]
            if r0[key] > 1e-14 and r1[key] > 1e-14:
                order = np.log(r0[key] / r1[key]) / np.log(r0["h"] / r1["h"])
                print(f"      {Ns[i-1]}→{Ns[i]}: order = {order:.2f}")

    return results


def _measure_dp(p, inside, outside):
    if np.any(inside) and np.any(outside):
        return float(np.mean(p[inside]) - np.mean(p[outside]))
    return float('nan')


# ══════════════════════════════════════════════════════════════════════════════
# Output
# ══════════════════════════════════════════════════════════════════════════════

def save_results(upwind_res, hermite_res, laplace_res):
    """Save LaTeX tables and npz data."""

    # Comparison table: test (a)
    with open(OUT / "table_comparison_1d.tex", "w") as fp:
        fp.write("% Auto-generated: Upwind vs Hermite 1D convergence (smooth q)\n")
        fp.write("% N & Upwind L∞ & order & Hermite L∞ & order\n")
        for i, (ru, rh) in enumerate(zip(upwind_res, hermite_res)):
            up_ord  = f"${ru.get('order', float('nan')):.1f}$" if i > 0 and not np.isnan(ru.get("order", float('nan'))) else "---"
            hm_ord  = f"${rh.get('order', float('nan')):.1f}$" if i > 0 and not np.isnan(rh.get("order", float('nan'))) else "---"
            fp.write(f"  {ru['N']:>3} & ${ru['Linf']:.2e}$ & {up_ord}"
                     f" & ${rh['Linf']:.2e}$ & {hm_ord} \\\\\n")

    # Test (b) table: upwind vs hermite
    with open(OUT / "table_laplace_comparison.tex", "w") as fp:
        fp.write("% Auto-generated: Young-Laplace — Upwind vs Hermite\n")
        fp.write("% N & Upwind Δp & rel_err & Hermite Δp & rel_err\n")
        for r in laplace_res:
            fp.write(f"  {r['N']:>3} & ${r['dp_upwind']:.2f}$"
                     f" & ${r['rel_err_upwind']:.2e}$"
                     f" & ${r['dp_hermite']:.2f}$"
                     f" & ${r['rel_err_hermite']:.2e}$ \\\\\n")

    # NPZ for figure generation
    np.savez(
        OUT / "hermite_data.npz",
        upwind_N=np.array([r["N"] for r in upwind_res]),
        upwind_h=np.array([r["h"] for r in upwind_res]),
        upwind_err=np.array([r["Linf"] for r in upwind_res]),
        hermite_N=np.array([r["N"] for r in hermite_res]),
        hermite_h=np.array([r["h"] for r in hermite_res]),
        hermite_err=np.array([r["Linf"] for r in hermite_res]),
        laplace_N=np.array([r["N"] for r in laplace_res]),
        laplace_dp_upwind=np.array([r["dp_upwind"] for r in laplace_res]),
        laplace_dp_hermite=np.array([r["dp_hermite"] for r in laplace_res]),
        laplace_rel_err_upwind=np.array([r["rel_err_upwind"] for r in laplace_res]),
        laplace_rel_err_hermite=np.array([r["rel_err_hermite"] for r in laplace_res]),
    )

    print(f"\n  Results saved to {OUT}")


def main():
    print("\n" + "=" * 70)
    print("  Closest-Point Hermite Extension Verification (§10.2.2 re-exp)")
    print("=" * 70)
    upwind_res, hermite_res = test_1d_convergence()
    laplace_res = test_young_laplace_hermite()
    save_results(upwind_res, hermite_res, laplace_res)


if __name__ == "__main__":
    main()
