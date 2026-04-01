#!/usr/bin/env python3
"""【11-1b】Static droplet balanced-force verification.

Paper ref: §11.1.2 — Surface tension equilibrium + parasitic currents

Static droplet: R=0.25, ρ_l/ρ_g=1000, We=1, no gravity.
Verifies: Laplace pressure Δp = σ/R = 4.0
Measures: parasitic current convergence with grid refinement.

NOTE: This is a PPE-level test. Full two-phase simulation is suspended (CHK-059).
We verify the pressure jump using the GFM PPE correction on a frozen interface.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import splu
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset import heaviside as hs_mod

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch11_bf_droplet"
OUT.mkdir(parents=True, exist_ok=True)


def static_droplet_ppe_test(N, R=0.25, rho_l=1000.0, rho_g=1.0, sigma=1.0, We=1.0):
    """PPE-only test: solve for pressure with CSF body force on static droplet.

    The pressure field should satisfy Δp ≈ σ/R across the interface.
    Deviation from exact Laplace balance produces residual velocity (parasitic current).
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="dirichlet")

    X, Y = grid.meshgrid()
    xc, yc = 0.5, 0.5

    # Signed distance function
    phi = np.sqrt((X - xc)**2 + (Y - yc)**2) - R

    # Smoothed Heaviside and density
    eps = 1.5 * h
    xp = backend.xp
    H = np.asarray(backend.to_host(hs_mod.heaviside(xp, xp.asarray(phi), eps)))
    rho = rho_g + (rho_l - rho_g) * H

    # Curvature via CCD
    curv_calc = CurvatureCalculator(backend, ccd, eps=eps)
    kappa = np.asarray(backend.to_host(curv_calc.compute(xp.asarray(phi))))

    # CSF body force: f_σ = (σ/We) κ ∇H
    delta_fn = np.asarray(backend.to_host(hs_mod.delta(xp, xp.asarray(phi), eps)))
    dphi_dx, _ = ccd.differentiate(xp.asarray(phi), axis=0)
    dphi_dy, _ = ccd.differentiate(xp.asarray(phi), axis=1)
    dphi_dx = np.asarray(backend.to_host(dphi_dx))
    dphi_dy = np.asarray(backend.to_host(dphi_dy))

    grad_H_x = delta_fn * dphi_dx
    grad_H_y = delta_fn * dphi_dy

    f_sigma_x = (sigma / We) * kappa * grad_H_x
    f_sigma_y = (sigma / We) * kappa * grad_H_y

    # For a balanced static droplet, the PPE should solve:
    # ∇·((1/ρ)∇p) = ∇·((1/ρ) f_σ)
    # which gives p = p_in inside, p_out outside, Δp = σκ/We

    # Simplified approach: measure pressure from a single-step projection
    # u* = dt * f_σ/ρ (predictor from zero velocity with surface tension only)
    dt = 1.0  # arbitrary, cancels out
    u_star = dt * f_sigma_x / rho
    v_star = dt * f_sigma_y / rho

    # Divergence of u*
    du_dx, _ = ccd.differentiate(xp.asarray(u_star), axis=0)
    dv_dy, _ = ccd.differentiate(xp.asarray(v_star), axis=1)
    div_star = np.asarray(backend.to_host(du_dx)) + np.asarray(backend.to_host(dv_dy))

    # Solve PPE: ∇²p = (ρ/dt)∇·u* using FD Poisson with Neumann-like BC
    n_inner = (N - 1)**2
    def idx(i, j): return (i-1)*(N-1) + (j-1)

    A = lil_matrix((n_inner, n_inner))
    b = np.zeros(n_inner)
    for i in range(1, N):
        for j in range(1, N):
            k = idx(i, j)
            A[k, k] = -4.0/h**2
            if i > 1: A[k, idx(i-1, j)] = 1.0/h**2
            if i < N-1: A[k, idx(i+1, j)] = 1.0/h**2
            if j > 1: A[k, idx(i, j-1)] = 1.0/h**2
            if j < N-1: A[k, idx(i, j+1)] = 1.0/h**2
            b[k] = rho[i, j] * div_star[i, j] / dt

    lu = splu(A.tocsc())
    p_inner = lu.solve(b)
    p = np.zeros((N+1, N+1))
    p[1:N, 1:N] = p_inner.reshape((N-1, N-1))

    # Measure Laplace pressure jump
    # Interior pressure: average p where phi < -2h (well inside droplet)
    mask_in = phi[1:N, 1:N] < -2*h
    mask_out = phi[1:N, 1:N] > 2*h
    p_inner_vals = p[1:N, 1:N]

    if np.any(mask_in) and np.any(mask_out):
        p_in = np.mean(p_inner_vals[mask_in])
        p_out = np.mean(p_inner_vals[mask_out])
        delta_p = p_in - p_out
    else:
        delta_p = np.nan

    laplace_exact = sigma / (R * We)  # = 4.0
    laplace_err = abs(delta_p - laplace_exact) / laplace_exact if not np.isnan(delta_p) else np.nan

    # Parasitic velocity (corrected velocity after projection)
    dp_dx, _ = ccd.differentiate(xp.asarray(p), axis=0)
    dp_dy, _ = ccd.differentiate(xp.asarray(p), axis=1)
    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))

    u_corr = u_star - dt / rho * dp_dx
    v_corr = v_star - dt / rho * dp_dy
    u_para = np.max(np.sqrt(u_corr**2 + v_corr**2))

    return delta_p, laplace_err, u_para, kappa


def main():
    print("\n" + "=" * 80)
    print("  【11-1b】Static Droplet: Balanced-Force + Parasitic Currents")
    print("=" * 80 + "\n")

    Ns = [32, 64, 128]
    results = []

    print(f"  {'N':>5} {'Δp':>10} {'Δp_exact':>10} {'rel_err':>10} {'||u_para||':>12} {'order':>8}")
    print("  " + "-" * 65)

    for N in Ns:
        delta_p, laplace_err, u_para, kappa = static_droplet_ppe_test(N)
        results.append({"N": N, "delta_p": delta_p, "err": laplace_err, "u_para": u_para})

        order_str = "---"
        if len(results) > 1:
            r0, r1 = results[-2], results[-1]
            if r0["u_para"] > 0 and r1["u_para"] > 0:
                s = np.log(r1["u_para"]/r0["u_para"]) / np.log((1.0/r1["N"])/(1.0/r0["N"]))
                order_str = f"{s:.2f}"

        print(f"  {N:>5} {delta_p:>10.4f} {'4.0000':>10} {laplace_err:>10.3e} "
              f"{u_para:>12.3e} {order_str:>8}")

    # Save LaTeX table
    with open(OUT / "table_bf_droplet.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_2_bf_droplet.py\n")
        fp.write("\\begin{tabular}{rrrrc}\n\\toprule\n")
        fp.write("$N$ & $\\Delta p$ & 相対誤差 & $\\|\\bu_{\\mathrm{para}}\\|_\\infty$ & 収束次数 \\\\\n")
        fp.write("\\midrule\n")
        for i, r in enumerate(results):
            order = "---"
            if i > 0:
                r0 = results[i-1]
                if r0["u_para"] > 0 and r["u_para"] > 0:
                    s = np.log(r["u_para"]/r0["u_para"]) / np.log((1.0/r["N"])/(1.0/r0["N"]))
                    order = f"${s:.2f}$"
            fp.write(f"{r['N']} & ${r['delta_p']:.3f}$ & ${r['err']:.2e}$ "
                     f"& ${r['u_para']:.2e}$ & {order} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_bf_droplet.tex'}")

    np.savez(OUT / "bf_droplet_data.npz", results=results)
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    main()
