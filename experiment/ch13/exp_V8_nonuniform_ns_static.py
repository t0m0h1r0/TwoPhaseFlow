#!/usr/bin/env python3
"""[V8] Static droplet on non-uniform grid (alpha=2) — Tier D.

Paper ref: §13.5 (sec:nonuniform_grid_ns).

V3 verifies the static droplet over 200 steps on a uniform grid (alpha=1).
V8 repeats the same reduced CCD-gradient + CSF + FVM-PPE coupling test with
the project's interface-fitted non-uniform grid (alpha_grid=2.0). It is a
non-uniform static-droplet diagnostic, not a §14 FCCD/HFE/Ridge-Eikonal stack
validation.

Setup
-----
  R = 0.25, [0,1]^2, wall BC, sigma = 1, We = 10, mu = 0,
  rho_l/rho_g = 10, CFL = 0.20 * h_min, 200 steps.
  N in {48, 64, 96}; alpha_grid = 2.0 (refined near interface).

Comparison: each (N, alpha=2) run is matched against a reference
(N, alpha=1) run for the same N, to quantify the non-uniform-vs-uniform
spurious-current penalty (or, ideally, improvement near the interface).

Pass criterion
--------------
  - all N stable (no blow up over 200 steps)
  - spurious peak ||u||_inf < 1e-2 at N=64, alpha=2
  - alpha=2 not worse than alpha=1 by more than 2x

Usage
-----
  python experiment/ch13/exp_V8_nonuniform_ns_static.py
  python experiment/ch13/exp_V8_nonuniform_ns_static.py --plot-only
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

R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 1.0
WE = 10.0
RHO_L = 10.0
RHO_G = 1.0
N_STEPS = 200
CFL_FACTOR = 0.20
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


def _run(N: int, alpha: float, n_steps: int = N_STEPS) -> dict:
    backend = Backend(use_gpu=False)
    xp = backend.xp
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0),
                                            alpha_grid=alpha))
    grid = Grid(cfg.grid, backend)
    h_uniform = 1.0 / N
    eps = 1.5 * h_uniform

    ccd = CCDSolver(grid, backend, bc_type="wall")

    # Initial level set on uniform grid → inflate non-uniform grid via Heaviside
    X0, Y0 = grid.meshgrid()
    phi0 = R - xp.sqrt((X0 - CENTER[0]) ** 2 + (Y0 - CENTER[1]) ** 2)
    psi0 = heaviside(xp, phi0, eps)
    if alpha > 1.0:
        grid.update_from_levelset(psi0, eps, ccd=ccd)
    h_min = float(min(np.min(grid.h[ax]) for ax in range(2)))
    dt = CFL_FACTOR * h_min

    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)
    psi = heaviside(xp, phi, eps)
    rho = RHO_G + (RHO_L - RHO_G) * psi
    rho_h = np.asarray(backend.to_host(rho))
    phi_h = np.asarray(backend.to_host(phi))
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))

    dpsi_dx = _ccd_grad(psi, ccd, 0, backend)
    dpsi_dy = _ccd_grad(psi, ccd, 1, backend)
    f_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_y = (SIGMA / WE) * kappa_h * dpsi_dy

    u = np.zeros_like(rho_h); v = np.zeros_like(rho_h)
    u_inf_hist = []; dp_hist = []
    blew_up = False
    for _ in range(n_steps):
        u_star = u + dt / rho_h * f_x
        v_star = v + dt / rho_h * f_y
        _wall_bc(u_star); _wall_bc(v_star)
        rhs = (_ccd_grad(u_star, ccd, 0, backend) +
               _ccd_grad(v_star, ccd, 1, backend)) / dt
        try:
            p = np.asarray(_solve_ppe(rhs, rho_h, ppe_builder, backend))
        except Exception:
            blew_up = True; break
        u = u_star - dt / rho_h * _ccd_grad(p, ccd, 0, backend)
        v = v_star - dt / rho_h * _ccd_grad(p, ccd, 1, backend)
        _wall_bc(u); _wall_bc(v)
        ui = float(np.max(np.sqrt(u * u + v * v)))
        u_inf_hist.append(ui)
        dp_hist.append(_measure_dp(p, phi_h, h_min))
        if not np.isfinite(ui) or ui > 1e2:
            blew_up = True; break

    arr = np.asarray(u_inf_hist)
    return {
        "N": N, "alpha": alpha, "h_min": h_min, "dt": dt,
        "blew_up": blew_up,
        "u_inf_history": arr,
        "dp_history": np.asarray(dp_hist),
        "u_inf_final": float(arr[-1]) if len(arr) else float("nan"),
        "u_inf_max": float(arr.max()) if len(arr) else float("nan"),
        "dp_final": float(np.asarray(dp_hist)[-1]) if dp_hist else float("nan"),
    }


def run_all() -> dict:
    out = {}
    for N in (48, 64, 96):
        for a in (1.0, 2.0):
            out[f"N{N}_a{a:.0f}"] = _run(N, a)
    return {"runs": out}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_u, ax_d = axes
    runs = results["runs"]

    for N, color in zip((48, 64, 96), ("C0", "C1", "C2")):
        for a, ls in zip((1.0, 2.0), ("-", "--")):
            r = runs.get(f"N{N}_a{a:.0f}")
            if r is None or r["blew_up"]: continue
            arr = r["u_inf_history"]
            ax_u.semilogy(np.arange(1, len(arr) + 1), arr, ls, color=color,
                          label=f"N={N}, α={a:.0f}")
    ax_u.axhline(1e-2, color="C3", linestyle=":", alpha=0.6, label="pass: 1e-2 @ N=64")
    ax_u.set_xlabel("step"); ax_u.set_ylabel("||u||_inf")
    ax_u.set_title("V8: spurious current — α=1 vs α=2"); ax_u.legend(fontsize=7)

    cats = []; dps = []
    for N in (48, 64, 96):
        for a in (1.0, 2.0):
            r = runs.get(f"N{N}_a{a:.0f}")
            cats.append(f"N{N}\nα={a:.0f}")
            dps.append(r["dp_final"] if r and not r["blew_up"] else 0.0)
    ax_d.bar(cats, dps, color="C2")
    ax_d.axhline(DP_EXACT, color="k", linestyle="--", alpha=0.7, label="σ/R")
    ax_d.set_ylabel("Δp_final"); ax_d.set_title("V8: Laplace Δp")
    ax_d.legend()

    save_figure(fig, OUT / "V8_nonuniform_ns_static")


def print_summary(results: dict) -> None:
    print(f"V8 (static droplet, α=1 vs α=2, ρ_l/ρ_g={RHO_L:.0f}):")
    runs = results["runs"]
    for N in (48, 64, 96):
        for a in (1.0, 2.0):
            r = runs.get(f"N{N}_a{a:.0f}")
            if r is None: continue
            tag = "BLEW UP" if r["blew_up"] else (
                f"|u|_max={r['u_inf_max']:.2e}  |u|_final={r['u_inf_final']:.2e}"
                f"  Δp={r['dp_final']:.4f}"
            )
            print(f"  N={N:>3}  α={a:.0f}  {tag}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V8 outputs in {OUT}")


if __name__ == "__main__":
    main()
