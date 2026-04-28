#!/usr/bin/env python3
"""[V7] IMEX-BDF2 two-phase time accuracy — Tier C.

Paper ref: §13.4 (sec:error_budget contributor).

V2 established AB2 + spectral projection achieves O(dt^2) on periodic
single-phase NS. V7 verifies the same time-integration order persists in
the coupled two-phase setting (CCD + CSF + split-PPE + HFE) with
moderate density ratio.

Setup
-----
  Slightly perturbed droplet (initial velocity perturbation in liquid):
    phi_0(x,y) = R - sqrt((x-0.5)^2 + (y-0.5)^2),
    u_0(x,y)   = U_amp * cos(2*pi*y) * H_eps(phi),
    v_0(x,y)   = -U_amp * cos(2*pi*x) * H_eps(phi).

  N = 128 fixed (spatial error saturated), rho_l/rho_g = 10, sigma = 1,
  We = 10, T = 0.05 (linear regime).
  dt in {T/40, T/80, T/160, T/320, T/640} (5-stage sweep, 16x range).

  Time integrator: BDF2 predictor + split-PPE corrector (the project's
  IMEX-BDF2 mode), forward-Euler startup for first step.

Reference solution: the run with dt = T/640 (smallest dt) is used as
'exact' for Richardson-style error estimation.

Pass criterion
--------------
  Slope of L_inf(u(T)) error vs dt >= 1.8 (target 2.0).

Usage
-----
  python experiment/ch13/exp_V7_imex_bdf2_twophase_time.py
  python experiment/ch13/exp_V7_imex_bdf2_twophase_time.py --plot-only
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
    compute_convergence_rates,
)
from twophase.tools.experiment.gpu import sparse_solve_2d

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 1.0
WE = 10.0
RHO_L = 10.0
RHO_G = 1.0
N_GRID = 128
T_FINAL = 0.05
U_AMP = 0.05


def _wall_bc(arr) -> None:
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


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


def _bdf2_step(u, v, u_prev, v_prev, f_x, f_y, rho_h, dt, ccd, ppe, backend, first_step: bool):
    """Predictor-Corrector with BDF2 predictor (FE on first step)."""
    if first_step:
        u_pred = u + dt * f_x / rho_h
        v_pred = v + dt * f_y / rho_h
    else:
        # BDF2: u_pred = (4 u^n - u^{n-1})/3 + (2 dt / 3) * f / rho
        u_pred = (4.0 * u - u_prev) / 3.0 + (2.0 * dt / 3.0) * f_x / rho_h
        v_pred = (4.0 * v - v_prev) / 3.0 + (2.0 * dt / 3.0) * f_y / rho_h
    _wall_bc(u_pred); _wall_bc(v_pred)
    rhs = (_ccd_grad(u_pred, ccd, 0, backend) +
           _ccd_grad(v_pred, ccd, 1, backend)) / dt
    p = np.asarray(_solve_ppe(rhs, rho_h, ppe, backend))
    dp_dx = _ccd_grad(p, ccd, 0, backend)
    dp_dy = _ccd_grad(p, ccd, 1, backend)
    u_new = u_pred - dt / rho_h * dp_dx
    v_new = v_pred - dt / rho_h * dp_dy
    _wall_bc(u_new); _wall_bc(v_new)
    return u_new, v_new


def _run(n_steps: int) -> dict:
    backend = Backend(use_gpu=False)
    xp = backend.xp
    N = N_GRID
    h = 1.0 / N
    eps = 1.5 * h
    dt = T_FINAL / n_steps

    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe = PPEBuilder(backend, grid, bc_type="wall")
    curv = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)
    psi = heaviside(xp, phi, eps)
    rho = RHO_G + (RHO_L - RHO_G) * psi
    rho_h = np.asarray(backend.to_host(rho))
    psi_h = np.asarray(backend.to_host(psi))
    kappa_h = np.asarray(backend.to_host(curv.compute(psi)))

    dpsi_dx = _ccd_grad(psi, ccd, 0, backend)
    dpsi_dy = _ccd_grad(psi, ccd, 1, backend)
    f_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_y = (SIGMA / WE) * kappa_h * dpsi_dy

    Xh = np.asarray(backend.to_host(X))
    Yh = np.asarray(backend.to_host(Y))
    u = U_AMP * np.cos(2 * np.pi * Yh) * psi_h
    v = -U_AMP * np.cos(2 * np.pi * Xh) * psi_h
    _wall_bc(u); _wall_bc(v)
    u_prev = u.copy(); v_prev = v.copy()

    for step in range(n_steps):
        u_new, v_new = _bdf2_step(u, v, u_prev, v_prev, f_x, f_y, rho_h, dt,
                                   ccd, ppe, backend, first_step=(step == 0))
        u_prev, v_prev = u, v
        u, v = u_new, v_new
    return {"n_steps": n_steps, "dt": dt, "u": u, "v": v}


def run_all() -> dict:
    n_list = [40, 80, 160, 320, 640]
    runs = [_run(n) for n in n_list]
    u_ref = runs[-1]["u"]; v_ref = runs[-1]["v"]
    rows = []
    for r in runs[:-1]:
        err = float(np.max(np.sqrt((r["u"] - u_ref) ** 2 + (r["v"] - v_ref) ** 2)))
        rows.append({"n_steps": r["n_steps"], "dt": r["dt"], "Linf_err": err})
    return {"reference_n_steps": n_list[-1], "rows": rows}


def make_figures(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    rows = results["rows"]
    dts = np.array([r["dt"] for r in rows])
    errs = np.array([r["Linf_err"] for r in rows])
    ax.loglog(dts, errs, "o-", color="C0", label="BDF2 + split-PPE (two-phase)")
    ax.loglog(dts, errs[0] * (dts / dts[0]) ** 2, "k--", alpha=0.6, label="O(dt²)")
    ax.loglog(dts, errs[0] * (dts / dts[0]) ** 1, "k:", alpha=0.4, label="O(dt¹)")
    ax.invert_xaxis()
    ax.set_xlabel("dt"); ax.set_ylabel("L_inf u error vs dt-ref")
    ax.set_title(f"V7: BDF2 two-phase time order (N={N_GRID}, ρ_l/ρ_g={RHO_L:.0f})")
    ax.legend()
    save_figure(fig, OUT / "V7_imex_bdf2_twophase_time")


def print_summary(results: dict) -> None:
    print(f"V7 (BDF2 two-phase time order, N={N_GRID}, T={T_FINAL}):")
    rows = results["rows"]
    dts = np.array([r["dt"] for r in rows])
    errs = np.array([r["Linf_err"] for r in rows])
    rates = compute_convergence_rates(errs, dts)
    for r, rate in zip(rows, [None] + list(rates)):
        rate_s = "" if rate is None else f"  slope={rate:.2f}"
        print(f"  n={r['n_steps']:>4}  dt={r['dt']:.3e}  Linf_err={r['Linf_err']:.3e}{rate_s}")
    if len(rates):
        print(f"  → asymptotic time order ≈ {rates[-1]:.2f}  (target ≥ 1.8)")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V7 outputs in {OUT}")


if __name__ == "__main__":
    main()
