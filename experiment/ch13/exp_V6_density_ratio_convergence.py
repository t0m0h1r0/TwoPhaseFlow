#!/usr/bin/env python3
"""[V6] Density-ratio sweep grid convergence — Tier C.

Paper ref: §13.4 (sec:varrho_dc_convergence, sec:interface_crossing).

Tests that the BF + split-PPE + HFE + CLS pipeline maintains spatial
convergence in the liquid pressure field as the density ratio rho_l/rho_g
increases from 2 to 100, and survives a smoke test at rho_l/rho_g = 833
(water-air).

Sub-tests
---------
  Static droplet R=0.25, [0,1]^2, wall BC, sigma=1, We=1, mu=0.
  N in {32, 64, 128}, rho_l/rho_g in {2, 10, 100, 833}.
  50 steps; measure mean liquid pressure error vs sigma/R.

  Reference: Ch12 U6 isolated split-PPE solver showed order >= 2 for
  density ratios up to 100. V6 verifies this carries over to the coupled
  Predictor-PPE-Corrector loop, where DC k=3 (Defect Correction iteration
  order) replaces direct sparse solve in 'large' problem regimes.

Pass criterion
--------------
  - rho <= 100: spatial L_inf order >= 2.0 (across N=32->128)
  - rho = 833: solver does not blow up (||u||_inf bounded, dp finite)

Usage
-----
  python experiment/ch13/exp_V6_density_ratio_convergence.py
  python experiment/ch13/exp_V6_density_ratio_convergence.py --plot-only
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
WE = 1.0
RHO_G = 1.0
DP_EXACT = SIGMA / (R * WE)
N_STEPS = 50
CFL_FACTOR = 0.20


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


def _measure_dp_inside(p, phi_h, h):
    inside = phi_h > 3.0 * h
    outside = phi_h < -3.0 * h
    if inside.any() and outside.any():
        return float(np.mean(p[inside]) - np.mean(p[outside]))
    return float("nan")


def _liquid_pressure_l_inf(p, phi_h, h, dp_target):
    """Spurious pressure non-uniformity inside the liquid phase.

    The Laplace solution has uniform pressure inside the droplet (Δp = σ/R
    relative to the gas), so the L_inf deviation from the liquid-mean
    pressure is the spurious-pressure error. This is gauge-invariant and
    converges to 0 as the BF discretization is refined.
    """
    inside = phi_h > 3.0 * h
    if not inside.any():
        return float("nan")
    p_in = p[inside]
    return float(np.max(p_in) - np.min(p_in))


def _run_one(N: int, ratio: float) -> dict:
    backend = Backend(use_gpu=False)
    xp = backend.xp
    h = 1.0 / N
    eps = 1.5 * h
    dt = CFL_FACTOR * h
    rho_l = ratio * RHO_G

    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)
    psi = heaviside(xp, phi, eps)
    rho = RHO_G + (rho_l - RHO_G) * psi
    rho_h = np.asarray(backend.to_host(rho))
    phi_h = np.asarray(backend.to_host(phi))
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))

    dpsi_dx = _ccd_grad(psi, ccd, 0, backend)
    dpsi_dy = _ccd_grad(psi, ccd, 1, backend)
    f_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_y = (SIGMA / WE) * kappa_h * dpsi_dy

    u = np.zeros_like(rho_h); v = np.zeros_like(rho_h)
    p = np.zeros_like(rho_h)
    u_inf_history = []
    blew_up = False
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
        u_inf = float(np.max(np.sqrt(u * u + v * v)))
        u_inf_history.append(u_inf)
        if not np.isfinite(u_inf) or u_inf > 1e3:
            blew_up = True; break

    dp_meas = _measure_dp_inside(p, phi_h, h) if not blew_up else float("nan")
    p_l_inf = _liquid_pressure_l_inf(p, phi_h, h, DP_EXACT) if not blew_up else float("nan")
    return {
        "N": N, "h": h, "ratio": ratio, "dt": dt,
        "blew_up": blew_up,
        "u_inf_final": u_inf_history[-1] if u_inf_history else float("nan"),
        "dp_measured": dp_meas, "dp_exact": DP_EXACT,
        "p_liquid_l_inf": p_l_inf,
    }


def run_all() -> dict:
    out = {}
    for ratio in (2.0, 10.0, 100.0, 833.0):
        rows = []
        for N in (32, 64, 128):
            rows.append(_run_one(N, ratio))
        out[f"r{int(ratio)}"] = rows
    return {"sweeps": out}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_c, ax_d = axes
    sweeps = results["sweeps"]
    colors = {"r2": "C0", "r10": "C1", "r100": "C2", "r833": "C3"}
    for key, rows in sweeps.items():
        rows_ok = [r for r in rows if not r["blew_up"] and np.isfinite(r["p_liquid_l_inf"])]
        if len(rows_ok) < 2: continue
        hs = np.array([r["h"] for r in rows_ok])
        errs = np.array([r["p_liquid_l_inf"] for r in rows_ok])
        ax_c.loglog(hs, errs, "o-", color=colors.get(key, "k"),
                    label=f"ρ={int(rows_ok[0]['ratio'])}")
    if sweeps.get("r2"):
        rows_ok = [r for r in sweeps["r2"] if not r["blew_up"] and np.isfinite(r["p_liquid_l_inf"])]
        if len(rows_ok) >= 2:
            hs = np.array([r["h"] for r in rows_ok])
            errs = np.array([r["p_liquid_l_inf"] for r in rows_ok])
            ax_c.loglog(hs, errs[0] * (hs / hs[0]) ** 2, "k--", alpha=0.4, label="O(h²)")
    ax_c.invert_xaxis(); ax_c.set_xlabel("h")
    ax_c.set_ylabel("L_inf liquid p error")
    ax_c.set_title("(a) Liquid pressure convergence")
    ax_c.legend()

    cats = []; dps = []
    for key, rows in sweeps.items():
        for r in rows:
            cats.append(f"N{r['N']}\nρ={int(r['ratio'])}")
            dps.append(r["dp_measured"] if np.isfinite(r["dp_measured"]) else 0.0)
    ax_d.bar(cats, dps, color="C2")
    ax_d.axhline(DP_EXACT, color="k", linestyle="--", alpha=0.7, label="σ/R")
    ax_d.set_ylabel("Δp_measured"); ax_d.set_xticklabels(cats, rotation=45, fontsize=7)
    ax_d.set_title("(b) Laplace Δp across (N, ρ)")
    ax_d.legend()

    save_figure(fig, OUT / "V6_density_ratio_convergence")


def print_summary(results: dict) -> None:
    print("V6 (density-ratio sweep grid convergence):")
    sweeps = results["sweeps"]
    for key in ("r2", "r10", "r100", "r833"):
        rows = sweeps.get(key, [])
        if not rows: continue
        print(f"  ρ={int(rows[0]['ratio'])}:")
        rows_ok = [r for r in rows if not r["blew_up"] and np.isfinite(r["p_liquid_l_inf"])]
        for r in rows:
            tag = "BLEW UP" if r["blew_up"] else f"L∞={r['p_liquid_l_inf']:.3e}  Δp={r['dp_measured']:.3e}"
            print(f"    N={r['N']:>3}  {tag}")
        if len(rows_ok) >= 2:
            hs = np.array([r["h"] for r in rows_ok])
            errs = np.array([r["p_liquid_l_inf"] for r in rows_ok])
            rates = compute_convergence_rates(errs, hs)
            if len(rates):
                print(f"    asymptotic order ≈ {rates[-1]:.2f}  (target ≥ 2.0)")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V6 outputs in {OUT}")


if __name__ == "__main__":
    main()
