#!/usr/bin/env python3
"""[11-22] Zalesak on non-uniform (interface-fitted) grid.

N=128, ε/h=0.5, alpha_grid=2.0 vs uniform baseline.
Grid rebuilt every advection step from φ = invert_heaviside(ψ).
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside, invert_heaviside
from twophase.initial_conditions.velocity_fields import RigidRotation
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, save_figure,
)

apply_style()
OUT = experiment_dir(__file__)


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    phi_circle = np.sqrt((X - center[0])**2 + (Y - center[1])**2) - R
    slot_x_min, slot_x_max = center[0] - slot_w / 2, center[0] + slot_w / 2
    slot_y_max = center[1] - R + slot_h
    dx = np.maximum(slot_x_min - X, X - slot_x_max)
    dy = np.maximum(-1e10 - Y, Y - slot_y_max)
    phi_slot = np.maximum(dx, dy)
    return np.maximum(phi_circle, -phi_slot)


def run_case(N, eps_ratio, alpha_grid, method="split", reinit_freq=20):
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha_grid)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h
    X, Y = grid.meshgrid()

    phi0 = zalesak_sdf(X, Y)
    psi0 = heaviside(np, phi0, eps)

    # For non-uniform: initial grid fitting
    if alpha_grid > 1.0:
        grid.update_from_levelset(phi0, eps, ccd=ccd)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        phi0 = zalesak_sdf(X, Y)
        psi0 = heaviside(np, phi0, eps)

    T = 2 * np.pi
    vf = RigidRotation(center=(0.5, 0.5), period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05,
                                  mass_correction=True)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                           method=method)

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    dV = grid.cell_volumes()
    mass0 = float(np.sum(psi * dV))
    reinit_count = 0

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=0)
        psi = adv.advance(psi, [u, v], dt)

        # Rebuild non-uniform grid from current interface
        if alpha_grid > 1.0 and (step + 1) % reinit_freq == 0:
            # 1. ψ → φ on OLD grid
            phi_cur = invert_heaviside(np, psi, eps)
            old_coords = [c.copy() for c in grid.coords]

            # 2. Rebuild grid from φ (coordinates change, array shape unchanged)
            grid.update_from_levelset(phi_cur, eps, ccd=ccd)
            new_coords = grid.coords

            # 3. Interpolate φ from old grid → new grid
            interp = RegularGridInterpolator(
                old_coords, phi_cur, method="cubic",
                bounds_error=False, fill_value=None,
            )
            X_new, Y_new = grid.meshgrid()
            pts = np.stack([X_new.ravel(), Y_new.ravel()], axis=-1)
            phi_new = interp(pts).reshape(X_new.shape)

            # 4. φ → ψ on new grid
            psi = heaviside(np, phi_new, eps)

            # 5. Rebuild solvers on new grid
            ccd = CCDSolver(grid, backend, bc_type="wall")
            adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                          eps_d=0.05, mass_correction=True)
            reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4,
                                   bc="zero", method=method)
            X, Y = X_new, Y_new

        if (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)
            reinit_count += 1

    # Final metrics on current grid
    X, Y = grid.meshgrid()
    phi0_final_grid = zalesak_sdf(X, Y)
    psi0_final_grid = heaviside(np, phi0_final_grid, eps)

    dV_final = grid.cell_volumes()
    mass_err = abs(float(np.sum(psi * dV_final)) - mass0) / mass0
    err_L2 = float(np.sqrt(np.mean((psi - psi0_final_grid)**2)))
    phi_final = invert_heaviside(np, psi, eps)
    band = np.abs(phi0_final_grid) < 6 * eps
    if np.any(band):
        err_L2_phi = float(np.sqrt(np.mean((phi_final[band] - phi0_final_grid[band])**2)))
    else:
        err_L2_phi = float('nan')
    area0 = float(np.sum(psi0_final_grid >= 0.5))
    area_err = abs(float(np.sum(psi >= 0.5)) - area0) / max(area0, 1.0)

    return {
        "N": N, "eps_ratio": eps_ratio, "alpha": alpha_grid, "method": method,
        "L2_psi": err_L2, "L2_phi": err_L2_phi,
        "area_err": area_err, "mass_err": mass_err,
        "reinits": reinit_count,
        "psi_final": psi, "psi_init": psi0_final_grid, "X": X, "Y": Y,
    }


def main():
    args = experiment_argparser("[11-22] Zalesak non-uniform grid").parse_args()
    N = 128
    eps_ratio = 0.5

    cases = [
        ("uniform", 1.0, "split"),
        ("non-uniform α=2", 2.0, "split"),
        ("non-uniform α=3", 3.0, "split"),
    ]

    all_results = []
    for label, alpha, method in cases:
        print(f"\n--- {label} ---")
        r = run_case(N, eps_ratio, alpha, method)
        print(f"  L2ψ={r['L2_psi']:.3e}, L2φ={r['L2_phi']:.3e}, "
              f"area={r['area_err']:.2e}, mass={r['mass_err']:.2e}")
        all_results.append({
            "label": label, "alpha": alpha,
            "L2_psi": r["L2_psi"], "L2_phi": r["L2_phi"],
            "area_err": r["area_err"], "mass_err": r["mass_err"],
        })

    print("\n" + "=" * 70)
    print(f"{'case':>20} {'L2(φ)':>10} {'area_err':>10} {'mass_err':>10}")
    print("-" * 70)
    for r in all_results:
        print(f"{r['label']:>20} {r['L2_phi']:>10.3e} {r['area_err']:>10.2e} {r['mass_err']:>10.2e}")
    print("=" * 70)


if __name__ == "__main__":
    main()
