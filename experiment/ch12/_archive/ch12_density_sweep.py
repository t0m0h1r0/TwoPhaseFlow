#!/usr/bin/env python3
"""【12-4】Density ratio sweep — §12.4

Tests CSF + smoothed Heaviside monolithic solver at increasing density ratios
to identify the dynamic breakdown threshold in the full NS pipeline.

Setup: Static droplet R=0.25, We=10, N=64, 200 steps (or until blowup)
Density ratios: rho_l/rho_g = 2, 3, 5, 10

Usage:
    python experiment/ch12/ch12_density_sweep.py
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

OUT = pathlib.Path(__file__).resolve().parent / "results" / "density_sweep"
OUT.mkdir(parents=True, exist_ok=True)

N = 64
WE = 10.0
R = 0.25
SIGMA = 1.0
N_STEPS = 200


def _solve_ppe(rhs, rho, ppe_builder):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run(rho_l, rho_g):
    """Run static droplet at given density ratio."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h
    dp_exact = SIGMA / (R * WE)

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi = np.asarray(heaviside(np, phi, eps))
    rho = rho_g + (rho_l - rho_g) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    mass_0 = float(np.sum(psi) * h**2)

    # Precompute CSF
    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u_max_history = []
    stable = True
    breakdown_step = None

    for step in range(N_STEPS):
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
        p = _solve_ppe(rhs, rho, ppe_builder)

        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u); wall_bc(v)

        vel_mag = np.sqrt(u**2 + v**2)
        u_max = float(np.max(vel_mag))
        u_max_history.append(u_max)

        if np.isnan(u_max) or u_max > 1e6:
            stable = False
            breakdown_step = step + 1
            break

    # Diagnostics
    mass_final = float(np.sum(psi) * h**2)
    mass_err = abs(mass_final - mass_0) / mass_0

    inside = phi > 3 * h
    outside = phi < -3 * h
    if np.any(inside) and np.any(outside) and stable:
        dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
        dp_err = abs(dp_meas - dp_exact) / dp_exact
    else:
        dp_meas = float('nan')
        dp_err = float('nan')

    # Divergence
    if stable:
        du_dx_f, _ = ccd.differentiate(u, 0)
        dv_dy_f, _ = ccd.differentiate(v, 1)
        div = np.asarray(du_dx_f) + np.asarray(dv_dy_f)
        div_linf = float(np.max(np.abs(div)))
    else:
        div_linf = float('nan')

    return {
        "rho_ratio": rho_l / rho_g,
        "u_max_peak": max(u_max_history) if u_max_history else float('nan'),
        "dp_rel_err": dp_err,
        "mass_err": mass_err,
        "div_linf": div_linf,
        "stable": stable,
        "breakdown_step": breakdown_step,
        "n_steps": len(u_max_history),
    }


def main():
    print("\n" + "=" * 70)
    print("  【12-4】Density Ratio Sweep (§12.4)")
    print("=" * 70)

    rho_ratios = [2, 3, 5, 10]
    results = []

    print(f"\n  {'ρ_l/ρ_g':>8} | {'||u||∞_peak':>12} | {'Δp_err':>8} | "
          f"{'mass_err':>10} | {'div_linf':>10} | {'status':>10}")
    print("  " + "-" * 75)

    for dr in rho_ratios:
        r = run(rho_l=float(dr), rho_g=1.0)
        results.append(r)
        status = "STABLE" if r["stable"] else f"BLOWUP@{r['breakdown_step']}"
        print(f"  {dr:>8} | {r['u_max_peak']:>12.3e} | "
              f"{r['dp_rel_err']:>7.2%} | "
              f"{r['mass_err']:>10.2e} | {r['div_linf']:>10.2e} | {status:>10}")

    np.savez(OUT / "density_sweep_data.npz",
             results=[r for r in results])

    print(f"\n  Results saved to {OUT}")


if __name__ == "__main__":
    main()
