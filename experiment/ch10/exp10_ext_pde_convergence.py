#!/usr/bin/env python3
"""Extension PDE verification for §10.2.2.

Test (a): 1D Extension PDE field extension convergence (tab:extension_pde_convergence).
  Setup:
    - 2D grid (y-uniform → effectively 1D along x)
    - φ = x − 0.5 (interface at x = 0.5)
    - Source field q(x) = 1 + cos(πx) for x < 0.5, q = 0 for x ≥ 0.5
      → q(0.5⁻) = 1, q'(0.5⁻) = −π sin(π/2) = −π ≠ 0
    - Exact extension: q_ext = q(0.5) = 1 for all x > 0.5
    - Upwind 1st-order: interface sampling error = q(0.5 − h) − q(0.5) = O(h)
    - n_ext = N (converge pseudo-time in the measurement band)
    - Error band: [0.52, 0.55] (fixed physical)
  Expected: O(h¹) convergence from interface sampling error.

Test (b): Young-Laplace Δp via Extension PDE + CSF + CCD-PPE (tab:extension_pde_laplace).
  - 2D circular droplet, R=0.25, We=1, ρ_l/ρ_g=1000
  - Exact Δp = κ/We = 1/R = 4.0
  - N = 32, 64, 128
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
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "ext_pde"
OUT.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Test (a): 1D Extension PDE convergence
# ══════════════════════════════════════════════════════════════════════════════

def test_1d_convergence():
    """O(h¹) convergence of Extension PDE for smooth source field."""
    print("\n" + "=" * 70)
    print("  Test (a): Extension PDE 1D convergence")
    print("=" * 70)

    backend = Backend(use_gpu=False)
    Ns = [32, 64, 128, 256]
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type='wall')
        h = 1.0 / N

        # Use enough iterations for convergence in measurement band
        # CFL=0.5 → each iter covers 0.5h → need N iters to cover 0.5 (physical)
        n_ext = max(N, 20)
        extender = FieldExtender(backend, grid, ccd, n_iter=n_ext, cfl=0.5)

        X, Y = grid.meshgrid()
        phi = X - 0.5  # interface at x=0.5

        # Source: smooth field with q'(0.5) ≠ 0
        # q(x) = 1 + cos(πx) → q(0.5) = 1, q'(0.5) = -π
        q_source = 1.0 + np.cos(np.pi * X)
        q = np.where(X < 0.5, q_source, 0.0)

        # Exact extension: q_ext = q(0.5) = 1.0 for all x > 0.5
        q_exact_ext = 1.0

        # Extend: FieldExtender.extend() extends from φ<0 → φ≥0
        q_ext = extender.extend(q, phi)

        # Measure L∞ error at fixed physical band [0.52, 0.55]
        x1d = X[:, 0]
        band = (x1d >= 0.52) & (x1d <= 0.55)
        j_mid = N // 2

        if band.any():
            err = np.max(np.abs(q_ext[band, j_mid] - q_exact_ext))
        else:
            err = float('nan')

        results.append({"N": N, "h": h, "Linf": err})
        print(f"  N={N:>4}, h=1/{N:>3}: L∞ error = {err:.4e}")

    # Convergence orders
    print("\n  Convergence orders:")
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0["Linf"] > 1e-15 and r1["Linf"] > 1e-15:
            order = np.log(r0["Linf"] / r1["Linf"]) / np.log(r0["h"] / r1["h"])
            results[i]["order"] = order
            print(f"    {r0['N']}→{r1['N']}: order = {order:.2f}")
        else:
            results[i]["order"] = float('nan')

    return results


# ══════════════════════════════════════════════════════════════════════════════
# Test (b): Young-Laplace static droplet
# ══════════════════════════════════════════════════════════════════════════════

def test_young_laplace():
    """Extension PDE + CSF + PPE: Laplace pressure jump for static droplet."""
    print("\n" + "=" * 70)
    print("  Test (b): Young-Laplace Δp = κ/We (Extension PDE + CSF)")
    print("=" * 70)

    backend = Backend(use_gpu=False)
    R = 0.25
    We = 1.0
    dp_exact = 1.0 / (R * We)  # = 4.0
    rho_l, rho_g = 1000.0, 1.0
    Ns = [32, 64, 128]
    n_ext = 5

    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type='wall')
        extender = FieldExtender(backend, grid, ccd, n_iter=n_ext, cfl=0.5)
        h = 1.0 / N
        eps = 1.5 * h

        X, Y = grid.meshgrid()
        dist = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
        phi = R - dist  # φ>0 inside (liquid)
        psi = heaviside(np, phi, eps)

        rho = rho_g + (rho_l - rho_g) * psi

        # Curvature via CCD (from psi → phi inversion)
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa = curv_calc.compute(psi)

        # CSF body force f_σ = (κ/We) ∇ψ
        grad_psi = []
        for ax in range(2):
            dpsi, _ = ccd.differentiate(psi, ax)
            grad_psi.append(dpsi)

        # PPE RHS = ∇·((1/ρ)(κ/We)∇ψ) via FD divergence
        fx = kappa * grad_psi[0] / (We * rho)
        fy = kappa * grad_psi[1] / (We * rho)
        rhs = np.zeros_like(psi)
        rhs[1:N, :] += (fx[1:N, :] - fx[0:N - 1, :]) / h
        rhs[:, 1:N] += (fy[:, 1:N] - fy[:, 0:N - 1]) / h

        # Build and solve PPE
        ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
        triplet, A_shape = ppe_builder.build(rho)
        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        rhs_flat = rhs.ravel().copy()
        rhs_flat[ppe_builder._pin_dof] = 0.0
        p_sol = spsolve(A, rhs_flat).reshape(psi.shape)

        # Apply Extension PDE: extend liquid pressure outward
        # Flip φ: FieldExtender.extend() extends φ<0→φ≥0; we want inside→outside
        p_ext = extender.extend(p_sol, -phi)

        # Measure Δp
        inside = phi > 3 * h
        outside = phi < -3 * h
        dp_raw = _measure_dp(p_sol, inside, outside)
        dp_with_ext = _measure_dp(p_ext, inside, outside)
        rel_err = abs(dp_with_ext - dp_exact) / dp_exact

        results.append({
            "N": N, "h": h,
            "dp_raw": dp_raw, "dp_ext": dp_with_ext,
            "rel_err_raw": abs(dp_raw - dp_exact) / dp_exact,
            "rel_err": rel_err,
        })
        print(f"  N={N:>4}: Δp(CSF)={dp_raw:.4f}  Δp(+ExtPDE)={dp_with_ext:.4f}  "
              f"exact={dp_exact:.4f}  rel_err={rel_err:.3e}")

    # Convergence orders
    print("\n  Convergence orders (CSF + ExtPDE):")
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0["rel_err"] > 1e-15 and r1["rel_err"] > 1e-15:
            order = np.log(r0["rel_err"] / r1["rel_err"]) / np.log(r0["h"] / r1["h"])
            results[i]["order"] = order
            print(f"    {Ns[i-1]}→{Ns[i]}: order = {order:.2f}")
        else:
            results[i]["order"] = float('nan')

    return results


def _measure_dp(p, inside, outside):
    if np.any(inside) and np.any(outside):
        return float(np.mean(p[inside]) - np.mean(p[outside]))
    return float('nan')


# ══════════════════════════════════════════════════════════════════════════════
# Output
# ══════════════════════════════════════════════════════════════════════════════

def save_results(conv_results, laplace_results):
    with open(OUT / "table_ext_pde_convergence.tex", "w") as fp:
        fp.write("% Auto-generated: Extension PDE 1D convergence\n")
        for r in conv_results:
            order_str = "---"
            if "order" in r and not np.isnan(r["order"]):
                order_str = f"$\\approx {r['order']:.1f}$"
            fp.write(f"  {r['N']:>3} & $1/{r['N']}$ & "
                     f"${r['Linf']:.2e}$ & {order_str} \\\\\n")

    with open(OUT / "table_ext_pde_laplace.tex", "w") as fp:
        fp.write("% Auto-generated: Extension PDE + CSF Young-Laplace\n")
        for r in laplace_results:
            order_str = "---"
            if "order" in r and not np.isnan(r.get("order", float("nan"))):
                order_str = f"$\\approx {r['order']:.1f}$"
            fp.write(f"  {r['N']:>3} & ${r['dp_ext']:.2f}$ & "
                     f"${r['rel_err']:.2e}$ & {order_str} \\\\\n")

    np.savez(OUT / "ext_pde_data.npz",
             convergence=conv_results, laplace=laplace_results)
    print(f"\n  Results saved to {OUT}")


def main():
    print("\n" + "=" * 70)
    print("  Extension PDE Verification (§10.2.2)")
    print("=" * 70)
    conv_results = test_1d_convergence()
    laplace_results = test_young_laplace()
    save_results(conv_results, laplace_results)


if __name__ == "__main__":
    main()
