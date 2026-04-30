#!/usr/bin/env python3
"""[V5] Spurious-current multi-step CCD vs FD — Type-A (revised criterion).

Paper ref: §13.3 (sec:bf_static_droplet companion / sec:error_budget contributor).

V3 establishes that a reduced CCD-gradient BF + CSF + FVM-PPE static-droplet
loop remains bounded over 200 steps at moderate density ratio. V5 adds two
controls:

  (i)  Compare against a 2nd-order central-difference (FD) baseline operator
       (same pipeline, same BCs, same eps; only spatial gradient operator
       differs). The ratio is reported, not used as a hard pass threshold.

  (ii) Track spurious current peak over 200 steps for several density
       ratios in {1, 10, 100} (ρ=1 is single-phase sanity), confirming
       that the peak does NOT grow secularly. ρ=100 stresses the
       BF discretization to its design limit.

Setup
-----
  R=0.25, [0,1]^2, wall BC, σ=1, We=10, μ=0, CFL=0.25h, 200 steps.
  N in {32, 64, 128}, ρ_l/ρ_g in {1, 10, 100}.

Reported diagnostics
--------------------
  - final-time FD/CCD ratio over the (N, ρ) sweep
  - peak and final CCD spurious-current histories

Usage
-----
  python experiment/ch13/exp_V5_spurious_current_multistep.py
  python experiment/ch13/exp_V5_spurious_current_multistep.py --plot-only
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
WE = 10.0
RHO_G = 1.0
N_STEPS = 200
CFL_FACTOR = 0.25


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


def _fd_grad(field, axis, h):
    """2nd-order central difference (Dirichlet zero outside)."""
    out = np.zeros_like(field)
    if axis == 0:
        out[1:-1, :] = (field[2:, :] - field[:-2, :]) / (2.0 * h)
    else:
        out[:, 1:-1] = (field[:, 2:] - field[:, :-2]) / (2.0 * h)
    return out


def _run_one(N: int, ratio: float, op_kind: str) -> dict:
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
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))

    if op_kind == "ccd":
        gx = lambda f: _ccd_grad(f, ccd, 0, backend)
        gy = lambda f: _ccd_grad(f, ccd, 1, backend)
    else:
        gx = lambda f: _fd_grad(f, 0, h)
        gy = lambda f: _fd_grad(f, 1, h)

    dpsi_dx = gx(np.asarray(backend.to_host(psi)))
    dpsi_dy = gy(np.asarray(backend.to_host(psi)))
    f_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_y = (SIGMA / WE) * kappa_h * dpsi_dy

    u = np.zeros_like(rho_h); v = np.zeros_like(rho_h)
    u_inf_hist = []
    for _ in range(N_STEPS):
        u_star = u + dt / rho_h * f_x
        v_star = v + dt / rho_h * f_y
        _wall_bc(u_star); _wall_bc(v_star)
        rhs = (gx(u_star) + gy(v_star)) / dt
        p = np.asarray(_solve_ppe(rhs, rho_h, ppe_builder, backend))
        u = u_star - dt / rho_h * gx(p)
        v = v_star - dt / rho_h * gy(p)
        _wall_bc(u); _wall_bc(v)
        u_inf_hist.append(float(np.max(np.sqrt(u * u + v * v))))

    arr = np.asarray(u_inf_hist)
    return {
        "N": N, "ratio": ratio, "op": op_kind, "h": h, "dt": dt,
        "u_inf_history": arr,
        "u_inf_final": float(arr[-1]),
        "u_inf_peak50": float(arr[:50].max()),
        "u_inf_peak_all": float(arr.max()),
    }


def run_all() -> dict:
    out = {}
    for N in (32, 64, 128):
        for r in (1.0, 10.0, 100.0):
            for op in ("ccd", "fd"):
                key = f"N{N}_r{int(r):d}_{op}"
                out[key] = _run_one(N, r, op)
    return {"runs": out}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_t, ax_b = axes
    runs = results["runs"]

    # Trajectories at N=128, ρ=10 — CCD vs FD
    for op, color in (("ccd", "C0"), ("fd", "C3")):
        key = f"N128_r10_{op}"
        if key in runs:
            arr = runs[key]["u_inf_history"]
            ax_t.semilogy(np.arange(1, len(arr) + 1), arr, color=color, label=op.upper())
    ax_t.set_xlabel("step"); ax_t.set_ylabel("||u||_inf")
    ax_t.set_title("Spurious current trajectory (N=128, ρ=10)")
    ax_t.legend()

    # CCD u_inf^end absolute (primary) with FD as a lighter side-reference.
    cats = []
    ccd_vals = []
    fd_vals = []
    for N in (32, 64, 128):
        for r in (1, 10, 100):
            ccd = runs.get(f"N{N}_r{r}_ccd")
            fd = runs.get(f"N{N}_r{r}_fd")
            if ccd and fd:
                cats.append(f"N{N}\nρ={r}")
                ccd_vals.append(ccd["u_inf_final"])
                fd_vals.append(fd["u_inf_final"])
    x = np.arange(len(cats))
    width = 0.4
    ax_b.bar(x - width / 2, ccd_vals, width, color="C0", label="CCD (primary)")
    ax_b.bar(x + width / 2, fd_vals, width, color="C3", alpha=0.35,
             label="FD (side ref.)")
    ax_b.set_xticks(x); ax_b.set_xticklabels(cats)
    ax_b.set_ylabel(r"$\|u\|_\infty^{\mathrm{end}}$")
    ax_b.set_title("CCD spurious-current absolute (FD side reference)")
    ax_b.set_yscale("log")
    ax_b.legend(fontsize=8)

    save_figure(fig, OUT / "V5_spurious_multistep_ccd_vs_fd",
                also_to=PAPER_FIGURES / "ch13_v5_spurious_multistep")


def print_summary(results: dict) -> None:
    print("V5 (spurious-current multi-step, CCD vs FD):")
    runs = results["runs"]
    for N in (32, 64, 128):
        for r in (1, 10, 100):
            ccd = runs.get(f"N{N}_r{r}_ccd")
            fd = runs.get(f"N{N}_r{r}_fd")
            if ccd and fd:
                ratio = fd["u_inf_final"] / max(ccd["u_inf_final"], 1e-30)
                print(f"  N={N:>3}  ρ={r:>3}  CCD_final={ccd['u_inf_final']:.2e}  "
                      f"FD_final={fd['u_inf_final']:.2e}  FD/CCD={ratio:.1f}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V5 outputs in {OUT}")


if __name__ == "__main__":
    main()
