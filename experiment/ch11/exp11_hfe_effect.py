#!/usr/bin/env python3
"""【11-HFE】HFE effect verification on static droplet (§11.4 supplement).

Compares HFE ON vs OFF on the same static droplet as exp11_9.
Uses NON-INCREMENTAL projection (same as §11.4a) with IPC modification:
  - HFE ON:  p^n extended via Hermite before CCD gradient
  - HFE OFF: p^n used directly (raw CCD gradient across interface)

Key difference from exp11_9: adds HFE/no-HFE comparison column.
For non-incremental projection, the predictor is u* = u^n + dt/ρ · f_csf
(no -∇p^n term), so HFE affects only the corrector's ∇p evaluation
when computing diagnostics and through the next-step pressure feedback.

Actually, in non-incremental projection the pressure is recomputed from
scratch each step, so the HFE effect manifests in the CORRECTOR step:
  u^{n+1} = u* - dt/ρ · ∇p
where ∇p is computed by CCD on the PPE solution p, which has a jump
at the interface due to σκ. Extending p before taking ∇p smooths this.
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
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.hfe.field_extension import HermiteFieldExtension

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch11_hfe_effect"
OUT.mkdir(parents=True, exist_ok=True)


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE via FVM direct LU."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run(N, rho_l, rho_g, We, n_steps, use_hfe):
    """Run multi-step static droplet with or without HFE.

    HFE is applied to the pressure field p BEFORE computing ∇p
    in the corrector step. This smooths the Young-Laplace jump
    and improves the velocity correction accuracy.
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h
    sigma = 1.0

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    hfe = HermiteFieldExtension(grid, ccd, backend, band_cells=6) if use_hfe else None

    X, Y = grid.meshgrid()
    R = 0.25

    # Initial conditions
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)  # phi > 0 inside
    psi = np.asarray(heaviside(np, phi, eps))
    rho = rho_g + (rho_l - rho_g) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    mass_0 = float(np.sum(psi) * h**2)
    dp_exact = sigma / (R * We)

    # Precompute curvature and CSF (static droplet: constant)
    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (sigma / We) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (sigma / We) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_history = []
    dp_history = []

    for step in range(n_steps):
        # Predictor (non-incremental: no -∇p^n)
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
        p = _solve_ppe(rhs, rho, ppe_builder)

        # HFE: extend p before computing gradient
        if hfe is not None:
            # source_sign = +1: source is inside droplet (phi > 0)
            p_for_grad = hfe.extend(p, phi, source_sign=+1.0)
        else:
            p_for_grad = p

        # Corrector
        dp_dx, _ = ccd.differentiate(p_for_grad, 0)
        dp_dy, _ = ccd.differentiate(p_for_grad, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        # Diagnostics
        vel_mag = np.sqrt(u**2 + v**2)
        u_max = float(np.max(vel_mag))

        inside = phi > 3 * h
        outside = phi < -3 * h
        if np.any(inside) and np.any(outside):
            dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
        else:
            dp_meas = float('nan')

        u_max_history.append(u_max)
        dp_history.append(dp_meas)

        if np.isnan(u_max) or u_max > 1e6:
            print(f"    BLOWUP at step {step+1}")
            break

    dp_final = dp_history[-1] if dp_history else float('nan')
    dp_rel_err = abs(dp_final - dp_exact) / dp_exact if not np.isnan(dp_final) else float('nan')

    return {
        "N": N, "rho_ratio": rho_l / rho_g, "use_hfe": use_hfe,
        "n_steps": len(u_max_history),
        "u_max_peak": max(u_max_history),
        "dp_rel_err": dp_rel_err,
        "dp_final": dp_final, "dp_exact": dp_exact,
        "u_max_history": np.array(u_max_history),
        "dp_history": np.array(dp_history),
    }


def main():
    print("\n" + "=" * 70)
    print("  【11-HFE】HFE Effect Verification (§11.4 supplement)")
    print("=" * 70)

    Ns = [64, 128]
    rho_ratios = [2, 5]
    n_steps = 200
    We = 10.0
    all_results = []

    for dr in rho_ratios:
        print(f"\n--- ρ_l/ρ_g = {dr} ---")
        print(f"  {'N':>5} | {'HFE':>5} | {'||u||∞_peak':>12} | {'Δp_err':>8}")
        print("  " + "-" * 50)

        for N in Ns:
            for use_hfe in [False, True]:
                r = run(N, rho_l=float(dr), rho_g=1.0, We=We,
                        n_steps=n_steps, use_hfe=use_hfe)
                all_results.append(r)
                label = "ON" if use_hfe else "OFF"
                print(f"  {N:>5} | {label:>5} | {r['u_max_peak']:>12.3e} | "
                      f"{r['dp_rel_err']:>7.1%}")

    # Save results
    np.savez(OUT / "hfe_effect_data.npz",
             results=[{k: v for k, v in r.items()
                       if k not in ('u_max_history', 'dp_history')}
                      for r in all_results])

    # Print summary table for paper
    print("\n\n  LaTeX table data (tab:hfe_ns_effect):")
    print("  " + "-" * 60)
    for r in all_results:
        hfe_str = "HFE" if r["use_hfe"] else "---"
        print(f"  ρ={r['rho_ratio']:.0f}  N={r['N']}  {hfe_str:>4}  "
              f"u_peak={r['u_max_peak']:.2e}  Δp_err={r['dp_rel_err']:.2%}")

    print(f"\n  Results saved to {OUT}")


if __name__ == "__main__":
    main()
