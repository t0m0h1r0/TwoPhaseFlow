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
    save_results, load_results, save_figure,
)

apply_style()
OUT = experiment_dir(__file__)


def zalesak_sdf(X, Y, center=(0.5, 0.75), R=0.15, slot_w=0.05, slot_h=0.25):
    """Zalesak slotted disk SDF — delegates to library."""
    from twophase.initial_conditions.shapes import ZalesakDisk
    return ZalesakDisk(center=center, radius=R, slot_width=slot_w, slot_depth=slot_h).sdf(X, Y)


def run_case(N, eps_ratio, alpha_grid, method="split", reinit_freq=20):
    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha_grid)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h
    X, Y = grid.meshgrid()

    # ZalesakDisk.sdf uses np.maximum (CPU-only) → build on host, promote to device
    X_h, Y_h = backend.to_host(X), backend.to_host(Y)
    phi0 = xp.asarray(zalesak_sdf(X_h, Y_h))
    psi0 = heaviside(xp, phi0, eps)

    # For non-uniform: initial grid fitting
    if alpha_grid > 1.0:
        grid.update_from_levelset(phi0, eps, ccd=ccd)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        X_h, Y_h = backend.to_host(X), backend.to_host(Y)
        phi0 = xp.asarray(zalesak_sdf(X_h, Y_h))
        psi0 = heaviside(xp, phi0, eps)

    T = 2 * np.pi
    vf = RigidRotation(center=(0.5, 0.5), period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05,
                                  mass_correction=True)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                           method=method)

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    dV = xp.asarray(grid.cell_volumes())   # grid.cell_volumes() always numpy
    mass0 = float(xp.sum(psi * dV))
    reinit_count = 0

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=0)
        psi = adv.advance(psi, [u, v], dt)

        # Rebuild non-uniform grid from current interface
        if alpha_grid > 1.0 and (step + 1) % reinit_freq == 0:
            # 1. ψ → φ on OLD grid; old_coords always numpy (grid.coords is host)
            phi_cur = invert_heaviside(xp, psi, eps)
            old_coords = [c.copy() for c in grid.coords]

            # 2. Compute M_before BEFORE host-converting psi
            M_before = float(xp.sum(psi * dV))

            # 3. Rebuild grid from φ (coordinates change, array shape unchanged)
            grid.update_from_levelset(phi_cur, eps, ccd=ccd)

            # 4. RegularGridInterpolator: scipy is CPU-only — must host-convert
            X_new_dev, Y_new_dev = grid.meshgrid()
            X_new = np.asarray(backend.to_host(X_new_dev))
            Y_new = np.asarray(backend.to_host(Y_new_dev))
            pts = np.stack([X_new.ravel(), Y_new.ravel()], axis=-1)
            psi_host = np.asarray(backend.to_host(psi))
            interp = RegularGridInterpolator(
                old_coords, psi_host, method="linear",
                bounds_error=False, fill_value=None,
            )
            psi_host_new = np.clip(interp(pts).reshape(X_new.shape), 0.0, 1.0)

            # 5. Mass correction on host
            dV_np = np.asarray(grid.cell_volumes())
            M_after = float(np.sum(psi_host_new * dV_np))
            w = 4.0 * psi_host_new * (1.0 - psi_host_new)
            W = float(np.sum(w * dV_np))
            if W > 1e-12:
                psi_host_new = np.clip(
                    psi_host_new + ((M_before - M_after) / W) * w, 0.0, 1.0)

            # 6. Push back to device
            psi = xp.asarray(psi_host_new)
            dV = xp.asarray(grid.cell_volumes())

            # 7. Rebuild solvers on new grid
            ccd = CCDSolver(grid, backend, bc_type="wall")
            adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                          eps_d=0.05, mass_correction=True)
            reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4,
                                   bc="zero", method=method)
            X, Y = X_new_dev, Y_new_dev

        if (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)
            reinit_count += 1

    # Final metrics on current grid
    X, Y = grid.meshgrid()
    X_h, Y_h = backend.to_host(X), backend.to_host(Y)
    phi0_final_grid = xp.asarray(zalesak_sdf(X_h, Y_h))
    psi0_final_grid = heaviside(xp, phi0_final_grid, eps)

    dV_final = xp.asarray(grid.cell_volumes())
    mass_err = abs(float(xp.sum(psi * dV_final)) - mass0) / mass0
    err_L2 = float(xp.sqrt(xp.mean((psi - psi0_final_grid)**2)))
    phi_final = invert_heaviside(xp, psi, eps)
    band = xp.abs(phi0_final_grid) < 6 * eps
    if bool(xp.any(band)):
        err_L2_phi = float(xp.sqrt(xp.mean((phi_final[band] - phi0_final_grid[band])**2)))
    else:
        err_L2_phi = float('nan')
    area0 = float(xp.sum(psi0_final_grid >= 0.5))
    area_err = abs(float(xp.sum(psi >= 0.5)) - area0) / max(area0, 1.0)

    return {
        "N": N, "eps_ratio": eps_ratio, "alpha": alpha_grid, "method": method,
        "L2_psi": err_L2, "L2_phi": err_L2_phi,
        "area_err": area_err, "mass_err": mass_err,
        "reinits": reinit_count,
        "psi_final": backend.to_host(psi),
        "psi_init": backend.to_host(psi0_final_grid),
        "X": backend.to_host(X), "Y": backend.to_host(Y),
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
    key_map = {
        "uniform": "uniform",
        "non-uniform α=2": "nonunif_a2",
        "non-uniform α=3": "nonunif_a3",
    }

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        print("\n" + "=" * 70)
        print(f"{'case':>20} {'L2(φ)':>10} {'area_err':>10} {'mass_err':>10}")
        print("-" * 70)
        for label, _, _ in cases:
            k = key_map[label]
            r = data[k]
            print(f"{label:>20} {float(r['L2_phi']):>10.3e} "
                  f"{float(r['area_err']):>10.2e} {float(r['mass_err']):>10.2e}")
        print("=" * 70)
        return

    from twophase.backend import Backend as _B
    _probe = _B()
    _gpu_run = _probe.is_gpu()

    all_results = []
    for label, alpha, method in cases:
        print(f"\n--- {label} ---")
        r = run_case(N, eps_ratio, alpha, method)
        print(f"  L2ψ={r['L2_psi']:.3e}, L2φ={r['L2_phi']:.3e}, "
              f"area={r['area_err']:.2e}, mass={r['mass_err']:.2e}")
        if _gpu_run and alpha > 1.0:
            print(f"  NOTE [{label}]: ASM-122-A FUNDAMENTAL drift expected in L2_psi "
                  f"(CHK-124) — non-uniform split reinit over ~900 steps")
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

    save_results(OUT / "data.npz", {
        key_map[r["label"]]: {
            f: r[f] for f in ("alpha", "L2_psi", "L2_phi", "area_err", "mass_err")
        }
        for r in all_results
    })


if __name__ == "__main__":
    main()
