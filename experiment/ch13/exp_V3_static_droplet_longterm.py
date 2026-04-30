#!/usr/bin/env python3
"""[V3] Static droplet 200-step coupling — default pass (paper §13b).

Paper ref: §13.2 (sec:twophase_static_longterm; extension of §12 U7).

Verifies that a reduced BF (balanced-force) + CSF + CCD-gradient + FVM-PPE
pipeline maintains a static circular droplet over 200 time steps without
secular growth of spurious currents and that the Laplace pressure jump
sigma/R is preserved within 1% at the finest grid.

Sub-tests
---------
  Static droplet: R=0.25, center (0.5, 0.5), wall BC, [0,1]^2,
  rho_l/rho_g = 10, We = 1, sigma = 1, mu = 0 (inviscid limit isolates the
  pressure-velocity coupling), CFL = 0.25 * h, 200 steps.
  N in {64, 96, 128}.

  At each step, run Predictor-PPE-Corrector with phi held static
  (interface advection disabled). Track:
    - max parasitic velocity |u|_inf,
    - Delta p (mean liquid p - mean gas p) vs sigma/R,
    - L2 velocity norm.

  Final-step diagnostics:
    - peak |u|_inf   (expected: bounded, no secular growth)
    - Delta p relative error to sigma/R
    - max |u|_inf observed during 200-step trajectory.

Reported diagnostics: |u|_inf trajectory, |Delta p - sigma/R|, and peak
spurious current over 200 steps.

Pass criteria
-------------
  - |Delta p_meas - sigma/R| / (sigma/R) <= 1.3% across all N (FORMAL).
  - u_inf^max bounded below sigma/Re_c spurious-current scale (~1e-2)
    and not monotonically growing across 200 steps (qualitative;
    no formal numeric threshold).

Usage
-----
  python experiment/ch13/exp_V3_static_droplet_longterm.py
  python experiment/ch13/exp_V3_static_droplet_longterm.py --plot-only
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
PAPER_FIGURES = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 1.0
WE = 1.0
RHO_L = 10.0
RHO_G = 1.0
N_STEPS = 200
CFL_FACTOR = 0.25
DP_EXACT = SIGMA / (R * WE)


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


def _measure_dp(p, phi_h, h):
    inside = phi_h > 3.0 * h
    outside = phi_h < -3.0 * h
    if inside.any() and outside.any():
        return float(np.mean(p[inside]) - np.mean(p[outside]))
    return float("nan")


def _run_single(N: int, n_steps: int = N_STEPS) -> dict:
    backend = Backend(use_gpu=False)
    xp = backend.xp
    h = 1.0 / N
    eps = 1.5 * h
    dt = CFL_FACTOR * h

    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)
    psi = heaviside(xp, phi, eps)
    rho = RHO_G + (RHO_L - RHO_G) * psi
    rho_h = np.asarray(backend.to_host(rho))
    phi_h = np.asarray(backend.to_host(phi))
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))

    # Pre-compute static CSF force: F = (sigma/We) * kappa * grad(psi)
    dpsi_dx = _ccd_grad(psi, ccd, 0, backend)
    dpsi_dy = _ccd_grad(psi, ccd, 1, backend)
    f_csf_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_csf_y = (SIGMA / WE) * kappa_h * dpsi_dy

    u = np.zeros_like(rho_h)
    v = np.zeros_like(rho_h)

    u_inf_history = []
    dp_history = []

    for _ in range(n_steps):
        # Predictor: only CSF (mu = 0, advection skipped — phi static)
        u_star = u + dt / rho_h * f_csf_x
        v_star = v + dt / rho_h * f_csf_y
        _wall_bc(u_star); _wall_bc(v_star)

        du_dx = _ccd_grad(u_star, ccd, 0, backend)
        dv_dy = _ccd_grad(v_star, ccd, 1, backend)
        rhs = (du_dx + dv_dy) / dt
        p = np.asarray(_solve_ppe(rhs, rho_h, ppe_builder, backend))

        dp_dx = _ccd_grad(p, ccd, 0, backend)
        dp_dy = _ccd_grad(p, ccd, 1, backend)
        u = u_star - dt / rho_h * dp_dx
        v = v_star - dt / rho_h * dp_dy
        _wall_bc(u); _wall_bc(v)

        u_inf_history.append(float(np.max(np.sqrt(u**2 + v**2))))
        dp_history.append(_measure_dp(p, phi_h, h))

    u_inf_final = u_inf_history[-1]
    u_inf_max = float(max(u_inf_history))
    dp_final = dp_history[-1]
    dp_rel_err = abs(dp_final - DP_EXACT) / DP_EXACT
    return {
        "N": N, "h": h, "dt": dt, "n_steps": n_steps,
        "u_inf_final": u_inf_final, "u_inf_max": u_inf_max,
        "dp_final": dp_final, "dp_exact": DP_EXACT, "dp_rel_err": dp_rel_err,
        "u_inf_history": np.asarray(u_inf_history),
        "dp_history": np.asarray(dp_history),
        "X": np.asarray(backend.to_host(X)),
        "Y": np.asarray(backend.to_host(Y)),
        "psi": np.asarray(backend.to_host(psi)),
        "pressure": p,
        "speed": np.sqrt(u * u + v * v),
    }


def run_all() -> dict:
    runs = {f"N{N}": _run_single(N) for N in (64, 96, 128)}
    return {"runs": runs}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_u, ax_p = axes
    runs = results["runs"]
    Ns = sorted(int(k.replace("N", "")) for k in runs)
    colors = ["C0", "C1", "C2", "C3"]
    for color, N in zip(colors, Ns):
        r = runs[f"N{N}"]
        steps = np.arange(1, len(r["u_inf_history"]) + 1)
        ax_u.semilogy(steps, r["u_inf_history"], color=color, label=f"N={N}")
        ax_p.plot(steps, r["dp_history"], color=color, label=f"N={N}")
    ax_u.set_xlabel("step"); ax_u.set_ylabel("$\\|u\\|_\\infty$")
    ax_u.set_title("Spurious current trajectory (200 step)")
    ax_u.axhline(1e-2, color="C3", linestyle=":", alpha=0.5,
                 label="scale ref: $\\sigma/\\mathrm{Re}_c$ ($\\sim 10^{-2}$)")
    ax_u.legend()
    ax_p.axhline(DP_EXACT, color="k", linestyle="--", alpha=0.7, label="$\\sigma/R$")
    ax_p.set_xlabel("step"); ax_p.set_ylabel("$\\Delta p$")
    ax_p.set_title("Laplace pressure (200 step)"); ax_p.legend()
    save_figure(fig, OUT / "V3_static_droplet_longterm",
                also_to=PAPER_FIGURES / "ch13_v3_static_droplet")

    snap = runs["N128"]
    fig_snap, axes_snap = plt.subplots(1, 2, figsize=(10.5, 4.4))
    ax_p, ax_u = axes_snap
    im_p = ax_p.pcolormesh(snap["X"], snap["Y"], snap["pressure"], cmap="coolwarm",
                           shading="auto")
    ax_p.contour(snap["X"], snap["Y"], snap["psi"], levels=[0.5],
                 colors="black", linewidths=1.0)
    ax_p.set_aspect("equal"); ax_p.set_xlabel("x"); ax_p.set_ylabel("y")
    ax_p.set_title("pressure field + interface")
    fig_snap.colorbar(im_p, ax=ax_p, shrink=0.82, label="$p$")

    im_u = ax_u.pcolormesh(snap["X"], snap["Y"], snap["speed"], cmap="magma",
                           shading="auto")
    ax_u.contour(snap["X"], snap["Y"], snap["psi"], levels=[0.5],
                 colors="white", linewidths=1.0)
    ax_u.set_aspect("equal"); ax_u.set_xlabel("x"); ax_u.set_ylabel("y")
    ax_u.set_title("$|u|$ after 200 steps")
    fig_snap.colorbar(im_u, ax=ax_u, shrink=0.82, label="$|u|$")
    fig_snap.suptitle("V3: static droplet 2D fields (N=128)")
    save_figure(fig_snap, OUT / "V3_static_droplet_snapshot",
                also_to=PAPER_FIGURES / "ch13_v3_static_droplet_snapshot")


def print_summary(results: dict) -> None:
    runs = results["runs"]
    print(f"V3 (static droplet 200-step, rho_l/rho_g={int(RHO_L/RHO_G)}, We={WE:.0f}):")
    for key in sorted(runs):
        r = runs[key]
        print(f"  N={r['N']:>3}  |u|_inf_final={r['u_inf_final']:.3e}"
              f"  |u|_inf_max={r['u_inf_max']:.3e}"
              f"  Delta_p={r['dp_final']:.4f}"
              f"  rel_err={r['dp_rel_err']:.2%}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V3 outputs in {OUT}")


if __name__ == "__main__":
    main()
