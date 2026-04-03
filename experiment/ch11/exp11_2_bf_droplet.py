#!/usr/bin/env python3
"""【11-1b】Static droplet balanced-force verification.

Paper ref: §11.1.2 — Surface tension equilibrium + parasitic currents

Static droplet: R=0.25, ρ_l/ρ_g=1000, We=1, no gravity.
Verifies: Laplace pressure Δp = σ/R = 4.0
Measures: parasitic current magnitude and grid convergence.

Uses variable-coefficient PPE (PPEBuilder) and CCD-CSF body force,
consistent with §10.2 Young-Laplace infrastructure.
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
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.heaviside import heaviside
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch11_bf_droplet"
OUT.mkdir(parents=True, exist_ok=True)


def static_droplet_ppe_test(N, R=0.25, rho_l=1000.0, rho_g=1.0, sigma=1.0, We=1.0):
    """Single-step projection test on a static droplet.

    Pipeline:
      1. Compute CSF body force f_σ = (σ/We) κ ∇ψ / ρ
      2. Predictor: u* = dt · f_σ (from zero velocity)
      3. PPE: ∇·((1/ρ)∇δp) = ∇·u*/dt  (variable-coefficient)
      4. Corrector: u = u* − (dt/ρ)∇δp
      5. Measure Δp and parasitic current ||u||_∞
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')

    X, Y = grid.meshgrid()
    xc, yc = 0.5, 0.5

    # Signed distance: φ > 0 inside (liquid)
    dist = np.sqrt((X - xc)**2 + (Y - yc)**2)
    phi = R - dist

    # Smoothed Heaviside and density
    psi = heaviside(np, phi, eps)
    rho = rho_g + (rho_l - rho_g) * psi

    # Curvature via CCD
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa = curv_calc.compute(psi)

    # CSF body force: f_σ = (σ/We) κ ∇ψ
    grad_psi = []
    for ax in range(2):
        dpsi, _ = ccd.differentiate(psi, ax)
        grad_psi.append(dpsi)

    # Predictor: u* = dt · f_σ / ρ  (dt=1 arbitrary, cancels in projection)
    dt = 1.0
    u_star = dt * (sigma / We) * kappa * grad_psi[0] / rho
    v_star = dt * (sigma / We) * kappa * grad_psi[1] / rho

    # PPE RHS: divergence of (f_σ/ρ) via FD (balanced-force consistent)
    rhs = np.zeros_like(psi)
    rhs[1:N, :] += (u_star[1:N, :] - u_star[0:N-1, :]) / h
    rhs[:, 1:N] += (v_star[:, 1:N] - v_star[:, 0:N-1]) / h
    rhs /= dt

    # Variable-coefficient PPE: ∇·((1/ρ)∇p) = RHS
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    p = spsolve(A, rhs_vec).reshape(psi.shape)

    # Measure Laplace pressure jump
    inside  = phi >  3 * h
    outside = phi < -3 * h
    if np.any(inside) and np.any(outside):
        dp = float(np.mean(p[inside]) - np.mean(p[outside]))
    else:
        dp = float('nan')

    dp_exact = sigma / (R * We)   # = 4.0
    rel_err = abs(dp - dp_exact) / dp_exact if not np.isnan(dp) else float('nan')

    # Corrector: u = u* − (dt/ρ)∇p  → parasitic current
    dp_dx, _ = ccd.differentiate(p, 0)
    dp_dy, _ = ccd.differentiate(p, 1)
    u_corr = u_star - dt / rho * dp_dx
    v_corr = v_star - dt / rho * dp_dy
    u_para = float(np.max(np.sqrt(u_corr**2 + v_corr**2)))

    return dp, rel_err, u_para


def main():
    print("\n" + "=" * 80)
    print("  【11-1b】Static Droplet: Balanced-Force + Parasitic Currents")
    print("=" * 80 + "\n")

    Ns = [32, 64, 128]
    dp_exact = 4.0
    results = []

    print(f"  {'N':>5} {'Δp':>10} {'Δp_exact':>10} {'rel_err':>10} "
          f"{'||u_para||':>12} {'寄生流れ次数':>14}")
    print("  " + "-" * 75)

    for N in Ns:
        dp, rel_err, u_para = static_droplet_ppe_test(N)
        results.append({"N": N, "dp": dp, "rel_err": rel_err, "u_para": u_para})

        order_str = "---"
        if len(results) > 1:
            r0, r1 = results[-2], results[-1]
            if r0["u_para"] > 0 and r1["u_para"] > 0:
                s = np.log(r0["u_para"] / r1["u_para"]) / np.log(
                    float(r1["N"]) / r0["N"])
                order_str = f"{s:.2f}"

        print(f"  {N:>5} {dp:>10.4f} {dp_exact:>10.1f} {rel_err:>10.3e} "
              f"{u_para:>12.3e} {order_str:>14}")

    # Pressure error convergence
    print("\n  Δp 相対誤差 収束次数:")
    for i in range(1, len(results)):
        r0, r1 = results[i-1], results[i]
        if r0["rel_err"] > 1e-14 and r1["rel_err"] > 1e-14:
            order = np.log(r0["rel_err"] / r1["rel_err"]) / np.log(
                float(r1["N"]) / r0["N"])
            print(f"    {r0['N']}→{r1['N']}: order = {order:.2f}")

    # Save LaTeX table
    with open(OUT / "table_bf_droplet.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_2_bf_droplet.py\n")
        fp.write("\\begin{tabular}{rrrrc}\n\\toprule\n")
        fp.write("$N$ & $\\Delta p$ & 相対誤差 & "
                 "$\\|\\bu_{\\mathrm{para}}\\|_\\infty$ & 寄生流れ次数 \\\\\n")
        fp.write("\\midrule\n")
        for i, r in enumerate(results):
            order = "---"
            if i > 0:
                r0 = results[i-1]
                if r0["u_para"] > 0 and r["u_para"] > 0:
                    s = np.log(r0["u_para"] / r["u_para"]) / np.log(
                        float(r["N"]) / r0["N"])
                    order = f"${s:.2f}$"
            fp.write(f"{r['N']} & ${r['dp']:.2f}$ & ${r['rel_err']:.1e}$ "
                     f"& ${r['u_para']:.2e}$ & {order} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_bf_droplet.tex'}")

    np.savez(OUT / "bf_droplet_data.npz", results=results)
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    main()
