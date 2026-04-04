#!/usr/bin/env python3
"""【11-11】Two-phase temporal accuracy: Δt refinement study.

Paper ref: §11.4c (sec:twophase_temporal_accuracy)

Measures the time convergence order of the full two-phase pipeline:
  CLS advection → property update → variable-density PPE → Corrector

Setup: static droplet with small velocity perturbation δu.
The perturbation decays due to viscosity. We measure the decay
at T_end with successively halved Δt to extract the convergence slope.

Uses non-incremental projection (O(Δt) splitting error expected).
Fixed N=128 to suppress spatial error.

ρ_l/ρ_g = 2, We=10, Re=100.
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
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "twophase_temporal"
OUT.mkdir(parents=True, exist_ok=True)


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE via FVM direct LU."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run_temporal_refinement(N, n_steps_list, rho_l=2.0, rho_g=1.0,
                            We=10.0, Re=100.0):
    """Run Δt refinement study for two-phase time integration.

    Fixed T_end, vary n_steps → vary Δt.
    Measure ||u||_∞ at T_end for each Δt.
    """
    backend = Backend(use_gpu=False)
    L = 1.0
    h = L / N
    eps = 1.5 * h
    sigma = 1.0
    nu = 1.0 / Re
    R = 0.25
    T_end = 0.1  # short integration to avoid nonlinear effects

    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    ls_advection = DissipativeCCDAdvection(backend, grid, ccd)

    X, Y = grid.meshgrid()

    results = []

    for n_steps in n_steps_list:
        dt = T_end / n_steps

        # Reset initial conditions
        phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
        psi = np.asarray(heaviside(np, phi, eps))
        rho = rho_g + (rho_l - rho_g) * psi

        # Small velocity perturbation (solenoidal, smooth)
        amp = 1e-3
        u = amp * np.sin(2 * np.pi * X) * np.cos(2 * np.pi * Y)
        v = -amp * np.cos(2 * np.pi * X) * np.sin(2 * np.pi * Y)

        # Apply wall BC
        u[0, :] = 0.0; u[-1, :] = 0.0; u[:, 0] = 0.0; u[:, -1] = 0.0
        v[0, :] = 0.0; v[-1, :] = 0.0; v[:, 0] = 0.0; v[:, -1] = 0.0

        blowup = False
        for step in range(n_steps):
            # CLS advection (conservative form for ψ)
            psi = ls_advection.advance(psi, [u, v], dt)
            psi = np.asarray(psi)
            rho = rho_g + (rho_l - rho_g) * psi

            # Curvature + CSF
            kappa = curv_calc.compute(psi)
            dpsi_dx, _ = ccd.differentiate(psi, 0)
            dpsi_dy, _ = ccd.differentiate(psi, 1)
            f_csf_x = (sigma / We) * kappa * np.asarray(dpsi_dx)
            f_csf_y = (sigma / We) * kappa * np.asarray(dpsi_dy)

            # Viscous (explicit for simplicity in Δt refinement)
            _, d2u_dx2 = ccd.differentiate(u, 0)
            _, d2u_dy2 = ccd.differentiate(u, 1)
            _, d2v_dx2 = ccd.differentiate(v, 0)
            _, d2v_dy2 = ccd.differentiate(v, 1)
            visc_u = nu * (np.asarray(d2u_dx2) + np.asarray(d2u_dy2))
            visc_v = nu * (np.asarray(d2v_dx2) + np.asarray(d2v_dy2))

            # Predictor (non-incremental + explicit viscous)
            u_star = u + dt * (f_csf_x / rho + visc_u)
            v_star = v + dt * (f_csf_y / rho + visc_v)
            u_star[0, :] = 0.0; u_star[-1, :] = 0.0
            u_star[:, 0] = 0.0; u_star[:, -1] = 0.0
            v_star[0, :] = 0.0; v_star[-1, :] = 0.0
            v_star[:, 0] = 0.0; v_star[:, -1] = 0.0

            # PPE
            du_dx, _ = ccd.differentiate(u_star, 0)
            dv_dy, _ = ccd.differentiate(v_star, 1)
            rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
            p = _solve_ppe(rhs, rho, ppe_builder)

            # Corrector
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)
            u = u_star - dt / rho * np.asarray(dp_dx)
            v = v_star - dt / rho * np.asarray(dp_dy)
            u[0, :] = 0.0; u[-1, :] = 0.0; u[:, 0] = 0.0; u[:, -1] = 0.0
            v[0, :] = 0.0; v[-1, :] = 0.0; v[:, 0] = 0.0; v[:, -1] = 0.0

            if np.any(np.isnan(u)) or np.max(np.abs(u)) > 1e6:
                blowup = True
                break

        u_inf = float(np.max(np.sqrt(u**2 + v**2)))
        results.append({
            "n_steps": n_steps, "dt": dt,
            "u_inf": u_inf if not blowup else float('inf'),
            "blowup": blowup,
        })
        status = "BLOWUP" if blowup else f"u_inf={u_inf:.4e}"
        print(f"  n={n_steps:>5}, dt={dt:.5e} → {status}")

    return results


def main():
    print("\n" + "=" * 80)
    print("  【11-11】Two-Phase Temporal Accuracy: Δt Refinement (§11.4c)")
    print("=" * 80 + "\n")

    N = 128
    n_steps_list = [25, 50, 100, 200, 400]
    print(f"  N={N}, ρ_l/ρ_g=2, We=10, Re=100, T=0.1\n")

    results = run_temporal_refinement(N, n_steps_list)

    # Compute convergence orders
    print(f"\n  {'n_steps':>8} {'Δt':>12} {'||u||∞':>12} {'order':>8}")
    print("  " + "-" * 50)
    for i, r in enumerate(results):
        order = "---"
        if i > 0 and not results[i-1]["blowup"] and not r["blowup"]:
            if results[i-1]["u_inf"] > 1e-16 and r["u_inf"] > 1e-16:
                o = np.log(results[i-1]["u_inf"] / r["u_inf"]) / np.log(
                    results[i-1]["dt"] / r["dt"])
                order = f"{o:.2f}"
        print(f"  {r['n_steps']:>8} {r['dt']:>12.5e} {r['u_inf']:>12.4e} {order:>8}")

    # Save LaTeX table
    with open(OUT / "table_twophase_temporal.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_11_twophase_temporal.py\n")
        fp.write("\\begin{tabular}{rrrc}\n\\toprule\n")
        fp.write("ステップ数 & $\\Delta t$ & $L^\\infty(\\bu)$ & 次数 \\\\\n")
        fp.write("\\midrule\n")
        prev = None
        for r in results:
            order_str = "---"
            if prev is not None and not prev["blowup"] and not r["blowup"]:
                if prev["u_inf"] > 1e-16 and r["u_inf"] > 1e-16:
                    o = np.log(prev["u_inf"] / r["u_inf"]) / np.log(prev["dt"] / r["dt"])
                    order_str = f"${o:.2f}$"
            u_str = f"${r['u_inf']:.2e}$" if not r["blowup"] else "発散"
            fp.write(f"{r['n_steps']} & ${r['dt']:.4e}$ & {u_str} & {order_str} \\\\\n")
            prev = r
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_twophase_temporal.tex'}")

    np.savez(OUT / "twophase_temporal_data.npz", results=results)
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    main()
