#!/usr/bin/env python3
"""[V9] Local-epsilon validation on non-uniform grid — Tier D.

Paper ref: §13.5 (sec:local_eps_validation).

For non-uniform interface-fitted grids (alpha_grid > 1), the smoothed
Heaviside thickness eps must scale with local spacing h(x) to keep
H_eps a true 1.5-cell smoothing. A globally-fixed eps under-resolves the
interface (too smeared) where h is small near the interface.

V9 compares three configurations on the V8 static-droplet setup:

  A:  alpha = 1.0  + fixed eps = 1.5 * h  (uniform reference; baseline)
  B:  alpha = 2.0  + fixed eps = 1.5 * h_avg  (naive non-uniform)
  C:  alpha = 2.0  + local eps_ij = 1.5 * h_local_ij  (corrected non-uniform)

Goal: confirm that C improves over B (smaller spurious current,
smaller Δp error). The expected outcome is decisive — either C beats B
(validates local-eps recipe) or it does not (paper-reportable null result).

Setup
-----
  R = 0.25, [0,1]^2, wall BC, sigma = 1, We = 10, mu = 0,
  rho_l/rho_g = 10, CFL = 0.20 * h_min, 100 steps, N in {48, 64}.

Pass criterion
--------------
  Decisive presentation: any monotone trend (A < C < B or otherwise) is
  reportable; result drives §13.5 narrative regardless of sign.

Usage
-----
  python experiment/ch13/exp_V9_local_eps_nonuniform.py
  python experiment/ch13/exp_V9_local_eps_nonuniform.py --plot-only
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
N_STEPS = 100
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


def _measure_dp(p, phi_h, h_ref):
    inside = phi_h > 3.0 * h_ref
    outside = phi_h < -3.0 * h_ref
    if inside.any() and outside.any():
        return float(np.mean(p[inside]) - np.mean(p[outside]))
    return float("nan")


def _local_h_field(grid, N: int) -> np.ndarray:
    """Return per-node local spacing field h_ij = sqrt(h_x_i * h_y_j) on (N+1)x(N+1).

    Uses grid.h[ax] which is per-node spacing of length N+1, then takes the
    geometric mean of x and y spacings to form a 2D field matching meshgrid().
    """
    try:
        hx = np.asarray(grid.h[0]).flatten()  # length N+1
        hy = np.asarray(grid.h[1]).flatten()
        return np.sqrt(np.outer(hx, hy))
    except Exception:
        return np.full((N + 1, N + 1), 1.0 / N)


def _run_config(N: int, alpha: float, eps_kind: str) -> dict:
    backend = Backend(use_gpu=False)
    xp = backend.xp
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0),
                                            alpha_grid=alpha))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    h_uniform = 1.0 / N
    eps_init = 1.5 * h_uniform
    X0, Y0 = grid.meshgrid()
    phi0 = R - xp.sqrt((X0 - CENTER[0]) ** 2 + (Y0 - CENTER[1]) ** 2)
    psi0 = heaviside(xp, phi0, eps_init)
    if alpha > 1.0:
        grid.update_from_levelset(psi0, eps_init, ccd=ccd)

    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")

    h_local = _local_h_field(grid, N)
    h_avg = float(np.mean(h_local))
    h_min = float(np.min(h_local))

    if eps_kind == "fixed":
        eps_field = np.full((N + 1, N + 1), 1.5 * h_avg)
    elif eps_kind == "local":
        eps_field = 1.5 * h_local
    else:
        raise ValueError(eps_kind)

    eps_for_curv = float(np.mean(eps_field))
    curv_calc = CurvatureCalculator(backend, ccd, eps_for_curv)
    dt = CFL_FACTOR * h_min

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)
    psi = heaviside(xp, phi, xp.asarray(eps_field))
    rho = RHO_G + (RHO_L - RHO_G) * psi
    rho_h = np.asarray(backend.to_host(rho))
    phi_h = np.asarray(backend.to_host(phi))
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))

    dpsi_dx = _ccd_grad(psi, ccd, 0, backend)
    dpsi_dy = _ccd_grad(psi, ccd, 1, backend)
    f_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_y = (SIGMA / WE) * kappa_h * dpsi_dy

    u = np.zeros_like(rho_h); v = np.zeros_like(rho_h)
    u_inf_hist = []; dp_hist = []; blew_up = False
    for _ in range(N_STEPS):
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
        "N": N, "alpha": alpha, "eps_kind": eps_kind, "h_min": h_min,
        "h_avg": h_avg, "dt": dt, "blew_up": blew_up,
        "u_inf_history": arr,
        "u_inf_max": float(arr.max()) if len(arr) else float("nan"),
        "u_inf_final": float(arr[-1]) if len(arr) else float("nan"),
        "dp_final": dp_hist[-1] if dp_hist else float("nan"),
        "dp_rel_err": (abs(dp_hist[-1] - DP_EXACT) / DP_EXACT) if dp_hist else float("nan"),
    }


def run_all() -> dict:
    out = {}
    for N in (48, 64):
        out[f"N{N}_A"] = _run_config(N, alpha=1.0, eps_kind="fixed")
        out[f"N{N}_B"] = _run_config(N, alpha=2.0, eps_kind="fixed")
        out[f"N{N}_C"] = _run_config(N, alpha=2.0, eps_kind="local")
    return {"runs": out}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_u, ax_d = axes
    runs = results["runs"]
    cmap = {"A": "C0", "B": "C1", "C": "C2"}
    label = {"A": "α=1, fixed eps", "B": "α=2, fixed eps", "C": "α=2, local eps"}
    for N in (48, 64):
        for cfg_id in ("A", "B", "C"):
            r = runs.get(f"N{N}_{cfg_id}")
            if r is None or r["blew_up"]: continue
            arr = r["u_inf_history"]
            ax_u.semilogy(np.arange(1, len(arr) + 1), arr,
                          color=cmap[cfg_id],
                          linestyle=("-" if N == 48 else "--"),
                          label=f"N={N}, {label[cfg_id]}")
    ax_u.set_xlabel("step"); ax_u.set_ylabel("||u||_inf")
    ax_u.set_title("V9: spurious current — A vs B vs C")
    ax_u.legend(fontsize=7)

    cats = []; vals = []; bar_colors = []
    for N in (48, 64):
        for cfg_id, color in zip(("A", "B", "C"), ("C0", "C1", "C2")):
            r = runs.get(f"N{N}_{cfg_id}")
            cats.append(f"N{N}\n{cfg_id}")
            vals.append(r["dp_rel_err"] if r and not r["blew_up"] else 0.0)
            bar_colors.append(color)
    ax_d.bar(cats, vals, color=bar_colors)
    ax_d.set_ylabel("|Δp - σ/R| / (σ/R)"); ax_d.set_yscale("log")
    ax_d.set_title("V9: Δp relative error (final step)")
    save_figure(fig, OUT / "V9_local_eps_nonuniform")


def print_summary(results: dict) -> None:
    print("V9 (local-ε validation, A=α1+fixed, B=α2+fixed, C=α2+local):")
    runs = results["runs"]
    for N in (48, 64):
        for cfg_id, name in (("A", "α=1, fixed"), ("B", "α=2, fixed"),
                              ("C", "α=2, local")):
            r = runs.get(f"N{N}_{cfg_id}")
            if r is None: continue
            tag = "BLEW UP" if r["blew_up"] else (
                f"|u|_max={r['u_inf_max']:.2e}  Δp={r['dp_final']:.4f}  "
                f"rel_err={r['dp_rel_err']:.2%}"
            )
            print(f"  N={N}  ({cfg_id}) {name:>14s}: {tag}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V9 outputs in {OUT}")


if __name__ == "__main__":
    main()
