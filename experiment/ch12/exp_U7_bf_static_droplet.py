#!/usr/bin/env python3
"""[U7] BF static droplet 1-step (Laplace pressure error) — Tier VII.

Paper ref: Chapter 11 U7 (sec:U7_bf_static_droplet; paper/sections/12u7_bf_static_droplet.tex).

Sub-tests
---------
  (a) Circular interface at rest, Δp = σκ vs computed Δp_num
      (BF operator consistency: Match vs Mismatch ∇p / ∇ψ pairing)
      R = 0.25, center (0.5, 0.5), σ = 1, We = 1, ρ_l/ρ_g = 1000
      N = 32, 64, 128; 1 NS step (non-incremental projection)
      Match    : ∇p = CCD,  ∇ψ = CCD     (BF consistent)
      Mismatch : ∇p = CCD,  ∇ψ = FD2     (BF inconsistent)
  (b) ρ/μ face interpolation (arithmetic / harmonic / VOF), 1D plane interface

Usage
-----
  python experiment/ch12/exp_U7_bf_static_droplet.py
  python experiment/ch12/exp_U7_bf_static_droplet.py --plot-only
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
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u7_bf_static_droplet"

# ── Physical parameters (U7-a) ───────────────────────────────────────────────
R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 1.0
WE = 1.0
RHO_L = 1000.0
RHO_G = 1.0
GRID_SIZES_A = [32, 64, 128]
DP_EXACT = SIGMA / (R * WE)


# ── PPE solver helper ────────────────────────────────────────────────────────

def _solve_ppe(rhs, rho, ppe_builder, backend):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=A_shape)
    xp = backend.xp
    rhs_flat = xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return sparse_solve_2d(backend, A, rhs_flat).reshape(rho.shape)


def _wall_bc(arr) -> None:
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


def _grad_psi_fd2(psi, h):
    """2nd-order centred FD gradient (Mismatch case)."""
    dpsi_dx = np.zeros_like(psi)
    dpsi_dy = np.zeros_like(psi)
    dpsi_dx[1:-1, :] = (psi[2:, :] - psi[:-2, :]) / (2 * h)
    dpsi_dy[:, 1:-1] = (psi[:, 2:] - psi[:, :-2]) / (2 * h)
    return dpsi_dx, dpsi_dy


# ── U7-a: 1-step NS solve, Match vs Mismatch ────────────────────────────────

def _u7a_run(N: int, mode: str, backend) -> dict:
    """One NS step on circular droplet, return Δp and parasitic current."""
    xp = backend.xp
    h = 1.0 / N
    eps = 1.5 * h
    dt = 0.25 * h

    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)
    psi = heaviside(xp, phi, eps)
    rho = RHO_G + (RHO_L - RHO_G) * psi

    psi_h = np.asarray(backend.to_host(psi))
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))

    if mode == "match":
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        dpsi_dx = np.asarray(backend.to_host(dpsi_dx))
        dpsi_dy = np.asarray(backend.to_host(dpsi_dy))
    elif mode == "mismatch":
        dpsi_dx, dpsi_dy = _grad_psi_fd2(psi_h, h)
    else:
        raise ValueError(mode)

    f_csf_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_csf_y = (SIGMA / WE) * kappa_h * dpsi_dy

    rho_h = np.asarray(backend.to_host(rho))
    u = np.zeros_like(rho_h)
    v = np.zeros_like(rho_h)

    u_star = u + dt / rho_h * f_csf_x
    v_star = v + dt / rho_h * f_csf_y
    _wall_bc(u_star); _wall_bc(v_star)

    du_dx, _ = ccd.differentiate(u_star, 0)
    dv_dy, _ = ccd.differentiate(v_star, 1)
    rhs = (np.asarray(backend.to_host(du_dx)) + np.asarray(backend.to_host(dv_dy))) / dt
    p = np.asarray(_solve_ppe(rhs, rho_h, ppe_builder, backend))

    dp_dx, _ = ccd.differentiate(p, 0)
    dp_dy, _ = ccd.differentiate(p, 1)
    dp_dx = np.asarray(backend.to_host(dp_dx))
    dp_dy = np.asarray(backend.to_host(dp_dy))
    u_new = u_star - dt / rho_h * dp_dx
    v_new = v_star - dt / rho_h * dp_dy
    _wall_bc(u_new); _wall_bc(v_new)

    phi_h = np.asarray(backend.to_host(phi))
    inside = phi_h > 3 * h
    outside = phi_h < -3 * h
    if inside.any() and outside.any():
        dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
    else:
        dp_meas = float("nan")
    dp_rel_err = abs(dp_meas - DP_EXACT) / DP_EXACT
    u_max = float(np.max(np.sqrt(u_new ** 2 + v_new ** 2)))
    return {
        "N": N, "h": h, "mode": mode,
        "dp_meas": dp_meas,
        "dp_exact": DP_EXACT,
        "dp_rel_err": dp_rel_err,
        "u_max": u_max,
    }


def run_U7a():
    backend = Backend(use_gpu=False)
    rows = []
    for N in GRID_SIZES_A:
        for mode in ("match", "mismatch"):
            rows.append(_u7a_run(N, mode, backend))
    return {"oneshot": rows}


# ── U7-b: ρ/μ face interpolation (1D plane interface) ───────────────────────

def _rho_field_1d(N: int, eps_phys: float = 0.02):
    """Smoothed Heaviside-based ρ on [0,1] with interface at x=0.5.

    eps_phys is a fixed physical smoothing scale (independent of h) so
    that face errors converge as the grid resolves the interface band.
    """
    h = 1.0 / N
    x = np.linspace(0.0, 1.0, N + 1)
    phi = 0.5 - x  # liquid for x < 0.5
    psi = 0.5 * (1.0 + np.tanh(phi / eps_phys))
    return x, h, RHO_G + (RHO_L - RHO_G) * psi, eps_phys


def _face_interp(rho, scheme: str):
    """Cell-centre rho (length N+1) -> face values (length N) at x_{i+1/2}."""
    if scheme == "arithmetic":
        return 0.5 * (rho[:-1] + rho[1:])
    if scheme == "harmonic":
        return 2.0 / (1.0 / rho[:-1] + 1.0 / rho[1:])
    if scheme == "vof":
        psi = (rho - RHO_G) / (RHO_L - RHO_G)
        psi = np.clip(psi, 0.0, 1.0)
        psi_face = 0.5 * (psi[:-1] + psi[1:])
        return RHO_G + (RHO_L - RHO_G) * psi_face
    raise ValueError(scheme)


def _u7b_errors(N: int, eps_phys: float = 0.02):
    x, h, rho_cell, eps = _rho_field_1d(N, eps_phys=eps_phys)
    x_face = x[:-1] + 0.5 * h
    psi_face_exact = 0.5 * (1.0 + np.tanh((0.5 - x_face) / eps))
    rho_face_exact = RHO_G + (RHO_L - RHO_G) * psi_face_exact
    return {
        "N": N, "h": h,
        "Linf_arith": float(np.max(np.abs(_face_interp(rho_cell, "arithmetic") - rho_face_exact))),
        "Linf_harm": float(np.max(np.abs(_face_interp(rho_cell, "harmonic") - rho_face_exact))),
        "Linf_vof": float(np.max(np.abs(_face_interp(rho_cell, "vof") - rho_face_exact))),
    }


def run_U7b():
    rows = [_u7b_errors(N) for N in [32, 64, 128, 256, 512]]
    return {"face_interp": rows}


# ── Aggregator + plotting ────────────────────────────────────────────────────

def run_all() -> dict:
    return {
        "U7a": run_U7a(),
        "U7b": run_U7b(),
    }


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    ax_dp, ax_u, ax_face = axes

    rows = results["U7a"]["oneshot"]
    Ns = sorted({r["N"] for r in rows})
    for mode, marker, color in (("match", "o", "C0"), ("mismatch", "s", "C3")):
        dp_errs = [next(r["dp_rel_err"] for r in rows if r["N"] == N and r["mode"] == mode) for N in Ns]
        u_max = [next(r["u_max"] for r in rows if r["N"] == N and r["mode"] == mode) for N in Ns]
        hs = [1.0 / N for N in Ns]
        ax_dp.loglog(hs, dp_errs, marker=marker, color=color, label=mode)
        ax_u.loglog(hs, u_max, marker=marker, color=color, label=mode)
    ax_dp.set_xlabel("$h$"); ax_dp.set_ylabel("$|\\Delta p_\\mathrm{num} - \\sigma\\kappa|/\\sigma\\kappa$")
    ax_dp.set_title("(a-1) Laplace Δp relative error"); ax_dp.legend(); ax_dp.invert_xaxis()
    ax_u.set_xlabel("$h$"); ax_u.set_ylabel("$\\max|\\mathbf{u}^1|$")
    ax_u.set_title("(a-2) Parasitic current"); ax_u.legend(); ax_u.invert_xaxis()

    rows_b = results["U7b"]["face_interp"]
    hs_b = [r["h"] for r in rows_b]
    for key, label, marker in (
        ("Linf_arith", "arithmetic", "o"),
        ("Linf_harm", "harmonic", "s"),
        ("Linf_vof", "VOF", "^"),
    ):
        ax_face.loglog(hs_b, [r[key] for r in rows_b], marker=marker, label=label)
    h_ref = np.array(hs_b)
    ax_face.loglog(h_ref, h_ref / h_ref[0] * rows_b[0]["Linf_arith"], "k--", alpha=0.4, label="$O(h)$")
    ax_face.set_xlabel("$h$"); ax_face.set_ylabel("$L_\\infty$ ρ-face error")
    ax_face.set_title("(b) ρ face interpolation"); ax_face.legend(); ax_face.invert_xaxis()

    save_figure(fig, OUT / "U7_bf_static_droplet", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    print("U7-a (BF Laplace pressure, 1-step):")
    for r in results["U7a"]["oneshot"]:
        print(f"  N={r['N']:>3}  mode={r['mode']:<8}  Δp={r['dp_meas']:.4f}"
              f"  rel_err={r['dp_rel_err']:.2%}  max|u|={r['u_max']:.2e}")
    print("U7-b (ρ face interp, finest grid):")
    finest = results["U7b"]["face_interp"][-1]
    print(f"  N={finest['N']:>3}  arith={finest['Linf_arith']:.3e}"
          f"  harm={finest['Linf_harm']:.3e}  vof={finest['Linf_vof']:.3e}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> U7 outputs in {OUT}")


if __name__ == "__main__":
    main()
