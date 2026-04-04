#!/usr/bin/env python3
"""【11-10】Galilean invariance test for two-phase NS solver.

Paper ref: §11.4b (sec:galilean_invariance)

Tests discrete Galilean invariance of the CLS↔variable-density PPE coupling.

Test A: Pure translation (σ=0)
  A density interface advected by uniform flow U.
  No surface tension → no pressure jump → velocity should stay uniform.
  Tests: CLS advection quality + variable-density PPE + divergence-free maintenance.

Test B: Laplace equilibrium in a moving frame (σ > 0)
  Same as Test A but with surface tension. The Laplace pressure Δp = σ/(R·We)
  should be maintained during translation.

Success: parasitic current bounded, mass conserved, shape preserved.
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

OUT = pathlib.Path(__file__).resolve().parent / "results" / "galilean"
OUT.mkdir(parents=True, exist_ok=True)


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE via FVM direct LU."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run_galilean(N, rho_l, rho_g, U=1.0, We=None, sigma=0.0,
                 n_periods=1):
    """Run droplet translation for Galilean invariance.

    Parameters
    ----------
    We : float or None
        Weber number. If None, σ=0 (no surface tension, Test A).
        Otherwise σ = 1.0 and surface tension is active (Test B).
    """
    backend = Backend(use_gpu=False)
    L = 1.0
    h = L / N
    eps = 1.5 * h
    dt = 0.2 * h / max(U, 1e-10)  # CFL ~ 0.2 (conservative)
    T = n_periods * L / U
    n_steps = int(np.ceil(T / dt))
    dt = T / n_steps  # exact period

    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='periodic')
    ppe_builder = PPEBuilder(backend, grid, bc_type='periodic')
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    ls_advection = DissipativeCCDAdvection(backend, grid, ccd)

    X, Y = grid.meshgrid()
    R = 0.25
    xc, yc = 0.5, 0.5

    # Surface tension setup
    if We is not None and We > 0:
        sigma_val = 1.0
        dp_exact = sigma_val / (R * We)
    else:
        sigma_val = 0.0
        dp_exact = 0.0

    # Initial conditions
    phi = R - np.sqrt((X - xc)**2 + (Y - yc)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    psi_0 = psi.copy()
    rho = rho_g + (rho_l - rho_g) * psi

    # Uniform initial velocity
    u = np.full_like(X, U)
    v = np.zeros_like(X)

    mass_0 = float(np.sum(psi) * h**2)

    # For IPC: warm-start pressure from single-step projection
    p = np.zeros_like(X)
    if sigma_val > 0:
        kappa = curv_calc.compute(psi)
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_x = (sigma_val / We) * kappa * np.asarray(dpsi_dx)
        f_y = (sigma_val / We) * kappa * np.asarray(dpsi_dy)
        u_tmp = u + dt / rho * f_x
        v_tmp = v + dt / rho * f_y
        du, _ = ccd.differentiate(u_tmp, 0)
        dv, _ = ccd.differentiate(v_tmp, 1)
        rhs = (np.asarray(du) + np.asarray(dv)) / dt
        p = _solve_ppe(rhs, rho, ppe_builder)

    u_para_history = []
    dp_history = []
    mass_history = []
    div_history = []

    for step in range(n_steps):
        # 1. Advect ψ (CLS: ∂ψ/∂t + ∇·(ψu) = 0)
        psi = ls_advection.advance(psi, [u, v], dt)
        psi = np.asarray(psi)
        rho = rho_g + (rho_l - rho_g) * psi

        # 2. CSF body force (if surface tension active)
        f_csf_x = np.zeros_like(X)
        f_csf_y = np.zeros_like(X)
        if sigma_val > 0:
            kappa = curv_calc.compute(psi)
            dpsi_dx, _ = ccd.differentiate(psi, 0)
            dpsi_dy, _ = ccd.differentiate(psi, 1)
            f_csf_x = (sigma_val / We) * kappa * np.asarray(dpsi_dx)
            f_csf_y = (sigma_val / We) * kappa * np.asarray(dpsi_dy)

        # 3. Predictor (IPC: include -∇p^n)
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u_star = u + dt / rho * (f_csf_x - np.asarray(dp_dx))
        v_star = v + dt / rho * (f_csf_y - np.asarray(dp_dy))

        # 4. PPE
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
        delta_p = _solve_ppe(rhs, rho, ppe_builder)

        # 5. Corrector
        ddp_dx, _ = ccd.differentiate(delta_p, 0)
        ddp_dy, _ = ccd.differentiate(delta_p, 1)
        u = u_star - dt / rho * np.asarray(ddp_dx)
        v = v_star - dt / rho * np.asarray(ddp_dy)
        p = p + delta_p

        # Diagnostics
        u_para = np.sqrt((u - U)**2 + v**2)
        u_para_max = float(np.max(u_para))

        du_check, _ = ccd.differentiate(u, 0)
        dv_check, _ = ccd.differentiate(v, 1)
        div_max = float(np.max(np.abs(np.asarray(du_check) + np.asarray(dv_check))))

        inside  = psi > 0.9
        outside = psi < 0.1
        if np.any(inside) and np.any(outside):
            dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
        else:
            dp_meas = float('nan')

        mass = float(np.sum(psi) * h**2)
        mass_err = abs(mass - mass_0) / max(mass_0, 1e-16)

        u_para_history.append(u_para_max)
        dp_history.append(dp_meas)
        mass_history.append(mass_err)
        div_history.append(div_max)

        if np.isnan(u_para_max) or u_para_max > 1e3:
            print(f"    [N={N}, ρ={rho_l/rho_g:.0f}] BLOWUP at step {step+1}/{n_steps}")
            break

    mass_err_final = mass_history[-1] if mass_history else float('nan')
    dp_final = dp_history[-1] if dp_history else float('nan')
    dp_rel_err = abs(dp_final - dp_exact) / max(dp_exact, 1e-16) if not np.isnan(dp_final) else float('nan')

    # Shape error: compare final ψ with initial ψ
    shape_err = float(np.max(np.abs(psi - psi_0)))

    stable = not np.isnan(u_para_history[-1]) and u_para_history[-1] < 1e1

    return {
        "N": N, "rho_ratio": rho_l / rho_g, "U": U,
        "We": We if We else 0,
        "n_steps": len(u_para_history),
        "n_steps_target": n_steps,
        "dt": dt,
        "u_para_peak": max(u_para_history),
        "u_para_final": u_para_history[-1],
        "dp_final": dp_final, "dp_exact": dp_exact,
        "dp_rel_err": dp_rel_err,
        "mass_err_final": mass_err_final,
        "div_max_final": div_history[-1],
        "shape_err": shape_err,
        "stable": stable,
    }


def main():
    print("\n" + "=" * 80)
    print("  【11-10】Galilean Invariance Test (§11.4b)")
    print("=" * 80 + "\n")

    Ns = [64, 128]
    rho_l, rho_g = 2.0, 1.0
    U = 1.0

    # ── Test A: Pure translation (σ=0) ──
    print("  Test A: Pure translation (σ=0)")
    print(f"  {'N':>5} | {'||u_para||∞':>12} | {'mass_err':>10} | "
          f"{'shape_err':>10} | {'div_max':>10} | {'stable':>7}")
    print("  " + "-" * 70)
    results_A = []
    for N in Ns:
        r = run_galilean(N, rho_l, rho_g, U=U, We=None)
        results_A.append(r)
        print(f"  {N:>5} | {r['u_para_final']:>12.3e} | "
              f"{r['mass_err_final']:>10.3e} | {r['shape_err']:>10.3e} | "
              f"{r['div_max_final']:>10.3e} | {'YES' if r['stable'] else 'NO':>7}")

    # ── Test B: Moving Laplace equilibrium (σ>0) ──
    print(f"\n  Test B: Moving droplet with surface tension (We=10)")
    print(f"  {'N':>5} | {'||u_para||∞':>12} | {'Δp_err':>8} | "
          f"{'mass_err':>10} | {'shape_err':>10} | {'stable':>7}")
    print("  " + "-" * 70)
    results_B = []
    for N in Ns:
        r = run_galilean(N, rho_l, rho_g, U=U, We=10.0)
        results_B.append(r)
        dp_str = f"{r['dp_rel_err']:.1%}" if not np.isnan(r['dp_rel_err']) else "nan"
        print(f"  {N:>5} | {r['u_para_final']:>12.3e} | {dp_str:>8} | "
              f"{r['mass_err_final']:>10.3e} | {r['shape_err']:>10.3e} | "
              f"{'YES' if r['stable'] else 'NO':>7}")

    all_results = results_A + results_B

    # Save LaTeX table
    with open(OUT / "table_galilean.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_10_galilean.py\n")
        fp.write("\\begin{tabular}{llrccccc}\n\\toprule\n")
        fp.write("テスト & $N$ & $\\mathit{We}$ & "
                 "$\\|\\bu_{\\mathrm{para}}\\|_\\infty$ & "
                 "$\\Delta p$ 相対誤差 & 質量誤差 & 形状誤差 & 安定 \\\\\n")
        fp.write("\\midrule\n")
        for r in all_results:
            test = "A（$\\sigma{=}0$）" if r["We"] == 0 else "B（$\\mathit{We}{=}10$）"
            dp_str = f"${r['dp_rel_err']:.1e}$" if r["dp_exact"] > 0 and not np.isnan(r['dp_rel_err']) else "---"
            stable = "○" if r["stable"] else "×"
            fp.write(f"{test} & {r['N']} & {r['We']:.0f} & "
                     f"${r['u_para_final']:.2e}$ & {dp_str} & "
                     f"${r['mass_err_final']:.2e}$ & "
                     f"${r['shape_err']:.2e}$ & {stable} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_galilean.tex'}")

    np.savez(OUT / "galilean_data.npz", results=all_results)
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    main()
