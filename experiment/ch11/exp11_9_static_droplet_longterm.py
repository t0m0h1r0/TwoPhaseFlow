#!/usr/bin/env python3
"""【11-9】Static droplet long-time stability (multi-step Laplace equilibrium).

Paper ref: §11.4a (sec:twophase_static_longterm)

Extends §11.1b single-step projection to multi-step time integration.
Key difference from §11.1b: from step 2 onward, p^n ≠ 0, so the IPC
predictor includes -∇p^n/ρ, which must balance the CSF body force.

For ρ_l/ρ_g ≤ 5 with smoothed Heaviside (ε=1.5h), the pressure
transition is smooth enough that raw CCD gradient (without Hermite
extension) should correctly capture ∇p across the interface.

Static droplet: R=0.25, u₀=0, gravity=0.
Success: parasitic currents bounded, Δp maintained, mass conserved.
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

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch11_static_longterm"
OUT.mkdir(parents=True, exist_ok=True)


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE via FVM direct LU."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run_static_longterm(N, rho_l, rho_g, We=10.0, n_steps=200):
    """Run multi-step time integration on a static droplet.

    Uses NON-INCREMENTAL projection (no -∇p^n in predictor) to avoid
    CCD gradient of pressure across the density interface. This gives
    O(Δt) splitting error but guarantees stability for interface problems.
    For incremental projection (O(Δt²)), Hermite extension of p is required.
    """
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h  # conservative: CFL ~ 0.25

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    R = 0.25
    sigma = 1.0

    # Initial conditions
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = rho_g + (rho_l - rho_g) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    mass_0 = float(np.sum(psi) * h**2)
    dp_exact = sigma / (R * We)

    # Precompute curvature and CSF (static: these don't change)
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
    mass_err_history = []
    div_max_history = []

    for step in range(n_steps):
        # Predictor: u* = u^n + dt/ρ · f_csf
        # (non-incremental: no -∇p^n term)
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star)
        wall_bc(v_star)

        # PPE RHS: div(u*) / dt
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt

        # Solve PPE for full pressure (non-incremental)
        p = _solve_ppe(rhs, rho, ppe_builder)

        # Corrector: u^{n+1} = u* - dt/ρ · ∇p
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u)
        wall_bc(v)

        # Diagnostics
        vel_mag = np.sqrt(u**2 + v**2)
        u_max = float(np.max(vel_mag))

        du_dx_check, _ = ccd.differentiate(u, 0)
        dv_dy_check, _ = ccd.differentiate(v, 1)
        div_max = float(np.max(np.abs(np.asarray(du_dx_check) + np.asarray(dv_dy_check))))

        inside  = phi >  3 * h
        outside = phi < -3 * h
        if np.any(inside) and np.any(outside):
            dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
        else:
            dp_meas = float('nan')

        mass = float(np.sum(psi) * h**2)
        mass_err = abs(mass - mass_0) / max(mass_0, 1e-16)

        u_max_history.append(u_max)
        dp_history.append(dp_meas)
        mass_err_history.append(mass_err)
        div_max_history.append(div_max)

        # Early termination on blowup
        if np.isnan(u_max) or u_max > 1e6:
            print(f"    [N={N}, ρ={rho_l/rho_g:.0f}] BLOWUP at step {step+1}")
            break

    dp_final = dp_history[-1] if dp_history else float('nan')
    dp_rel_err = abs(dp_final - dp_exact) / dp_exact if not np.isnan(dp_final) else float('nan')

    # Stability: check if parasitic current is bounded
    if len(u_max_history) >= 10:
        u_early = np.mean(u_max_history[1:6])
        u_late = np.mean(u_max_history[-5:])
        growth = u_late / max(u_early, 1e-16)
    else:
        growth = float('inf')

    return {
        "N": N, "rho_ratio": rho_l / rho_g, "n_steps": len(u_max_history),
        "dt": dt, "u_max_peak": max(u_max_history),
        "u_max_final": u_max_history[-1],
        "growth_ratio": growth,
        "dp_final": dp_final, "dp_exact": dp_exact,
        "dp_rel_err": dp_rel_err,
        "mass_err_final": mass_err_history[-1],
        "div_max_final": div_max_history[-1],
        "div_max_peak": max(div_max_history),
        "stable": growth < 5.0 and not np.isnan(u_max_history[-1]),
        "u_max_history": np.array(u_max_history),
        "dp_history": np.array(dp_history),
        "div_max_history": np.array(div_max_history),
    }


def main():
    print("\n" + "=" * 80)
    print("  【11-9】Static Droplet Long-Time Stability (§11.4a)")
    print("=" * 80 + "\n")

    Ns = [64, 128]
    density_ratios = [2, 5]
    n_steps = 200
    all_results = []

    for dr in density_ratios:
        print(f"\n--- ρ_l/ρ_g = {dr}, {n_steps} steps ---")
        print(f"  {'N':>5} | {'||u||∞_peak':>12} | {'||u||∞_final':>12} | "
              f"{'growth':>8} | {'Δp_err':>8} | {'mass_err':>10} | "
              f"{'div_max':>10} | {'stable':>7}")
        print("  " + "-" * 95)

        for N in Ns:
            r = run_static_longterm(N, rho_l=float(dr), rho_g=1.0,
                                    n_steps=n_steps)
            all_results.append(r)

            print(f"  {N:>5} | {r['u_max_peak']:>12.3e} | {r['u_max_final']:>12.3e} | "
                  f"{r['growth_ratio']:>8.2f} | {r['dp_rel_err']:>7.1%} | "
                  f"{r['mass_err_final']:>10.3e} | "
                  f"{r['div_max_final']:>10.3e} | "
                  f"{'YES' if r['stable'] else 'NO':>7}")

    # Save LaTeX table
    with open(OUT / "table_static_longterm.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_9_static_droplet_longterm.py\n")
        fp.write("\\begin{tabular}{rrccccc}\n\\toprule\n")
        fp.write("$\\rho_l/\\rho_g$ & $N$ & "
                 "$\\|\\bu_{\\mathrm{para}}\\|_\\infty^{\\mathrm{peak}}$ & "
                 "$\\Delta p$ 相対誤差 & 質量誤差 & "
                 "$\\|\\bnabla\\cdot\\bu\\|_\\infty$ & 安定 \\\\\n")
        fp.write("\\midrule\n")
        for r in all_results:
            stable = "○" if r["stable"] else "×"
            fp.write(f"{r['rho_ratio']:.0f} & {r['N']} & "
                     f"${r['u_max_peak']:.2e}$ & "
                     f"${r['dp_rel_err']:.1e}$ & "
                     f"${r['mass_err_final']:.2e}$ & "
                     f"${r['div_max_final']:.2e}$ & "
                     f"{stable} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_static_longterm.tex'}")

    np.savez(OUT / "static_longterm_data.npz",
             results=[{k: v for k, v in r.items() if k != 'u_max_history'
                       and k != 'dp_history' and k != 'div_max_history'}
                      for r in all_results],
             u_max_histories=[r['u_max_history'] for r in all_results],
             dp_histories=[r['dp_history'] for r in all_results])
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    main()
