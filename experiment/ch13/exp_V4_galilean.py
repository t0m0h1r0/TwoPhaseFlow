#!/usr/bin/env python3
"""[V4] Galilean offset residual under fixed-wall + reference-pinned PPE.

Paper ref: §13.3 (sec:galilean_offset).

A static droplet (R=0.25, sigma>0) is run twice on the same fixed Eulerian
wall grid: baseline U=(0,0) and offset U=(0.1,0). This is a reduced
residual-scale check for the BF + split-PPE + CSF/PPE loop under wall BC and
pinned pressure gauge, not an exact periodic Galilean-invariance proof.

Setup
-----
  [0,1]^2 wall BC, N=64, R=0.25, ρ_l/ρ_g=10, σ=1, We=10,
  U_offset=(0.1, 0.0), dt=0.20h, 50 steps.

Note: interface advection is disabled because the droplet is static.
The Rayleigh-Taylor linear-growth diagnostic that previously sat next to
this test has been removed; pure RT linear/non-linear behavior is the
remit of §14 (sec:val_rayleigh_taylor) which uses the production stack.

Usage
-----
  python experiment/ch13/exp_V4_galilean.py
  python experiment/ch13/exp_V4_galilean.py --plot-only
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)
from twophase.tools.experiment.gpu import sparse_solve_2d

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"


def _solve_ppe(rhs, rho, ppe_builder, backend):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=A_shape)
    xp = backend.xp
    rhs_flat = xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return sparse_solve_2d(backend, A, rhs_flat).reshape(rho.shape)


def _ccd_grad(field, ccd, axis, backend):
    d1, _ = ccd.differentiate(field, axis)
    return np.asarray(backend.to_host(d1))


def _wall_bc(arr) -> None:
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def run_V4() -> dict:
    """Translation-stability test: static droplet with uniform offset velocity
    U_frame on wall BC. The interior velocity perturbation about U_frame
    should remain small (Galilean invariance of the BF/CSF/PPE pipeline)."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    N = 64
    h = 1.0 / N
    eps = 1.5 * h
    n_steps = 50

    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    R = 0.25; SIGMA = 1.0; WE = 10.0
    rho_l, rho_g = 10.0, 1.0
    dt = 0.20 * h

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = heaviside(xp, phi, eps)
    rho_h = np.asarray(backend.to_host(rho_g + (rho_l - rho_g) * psi))
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))
    dpsi_dx = _ccd_grad(psi, ccd, 0, backend)
    dpsi_dy = _ccd_grad(psi, ccd, 1, backend)
    f_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_y = (SIGMA / WE) * kappa_h * dpsi_dy

    def _trajectory(U):
        u = U[0] * np.ones_like(rho_h); v = U[1] * np.ones_like(rho_h)
        _wall_bc(u); _wall_bc(v)
        hist = []
        for _ in range(n_steps):
            u_s = u + dt / rho_h * f_x; v_s = v + dt / rho_h * f_y
            _wall_bc(u_s); _wall_bc(v_s)
            rhs = (_ccd_grad(u_s, ccd, 0, backend) + _ccd_grad(v_s, ccd, 1, backend)) / dt
            p = np.asarray(_solve_ppe(rhs, rho_h, ppe_builder, backend))
            u = u_s - dt / rho_h * _ccd_grad(p, ccd, 0, backend)
            v = v_s - dt / rho_h * _ccd_grad(p, ccd, 1, backend)
            _wall_bc(u); _wall_bc(v)
            hist.append((u - U[0], v - U[1]))
        return hist

    static_h = _trajectory(np.array([0.0, 0.0]))
    offset_h = _trajectory(np.array([0.1, 0.0]))
    diff = []
    for (du_s, dv_s), (du_o, dv_o) in zip(static_h, offset_h):
        diff.append(float(np.max(np.sqrt((du_o - du_s) ** 2 + (dv_o - dv_s) ** 2))))

    return {
        "N": N, "n_steps": n_steps, "dt": dt, "U_offset": [0.1, 0.0],
        "galilean_diff_history": np.asarray(diff),
        "galilean_diff_final": diff[-1],
        "galilean_diff_max": float(max(diff)),
    }


def run_all() -> dict:
    return {"V4": run_V4()}


def make_figures(results: dict) -> None:
    fig, ax = plt.subplots(1, 1, figsize=(6.5, 4.4))
    a = results["V4"]
    steps = np.arange(1, len(a["galilean_diff_history"]) + 1)
    ax.semilogy(steps, a["galilean_diff_history"], "o-", color="C0",
                label=f"||(u-U)_offset - u_static||_inf (N={a['N']})")
    ax.axhline(1e-8, color="C3", linestyle="--", alpha=0.6, label="reference: 1e-8")
    ax.set_xlabel("step"); ax.set_ylabel("Galilean residual")
    ax.set_title("V4: Galilean offset residual (fixed wall, pinned PPE)")
    ax.legend()
    save_figure(fig, OUT / "V4_galilean_offset")


def print_summary(results: dict) -> None:
    a = results["V4"]
    print("V4 (Galilean offset residual, wall BC):")
    print(f"  N={a['N']}  n={a['n_steps']}  dt={a['dt']:.3e}  "
          f"diff_final={a['galilean_diff_final']:.3e}  "
          f"diff_max={a['galilean_diff_max']:.3e}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V4 outputs in {OUT}")


if __name__ == "__main__":
    main()
