#!/usr/bin/env python3
"""[U2] CCD-Poisson + current PPE BC — Tier I (uniform grid).

Paper ref: Chapter 12 U2 (sec:U2_ccd_poisson_ppe_bc; paper/sections/12u2_ccd_poisson_ppe_bc.tex).

Sub-tests
---------
  (a) Poisson Dirichlet reference, DC k = 1, 2, 3, 5, 10
      reference  p* = sin(pi x) sin(pi y)
      expected   k=1 -> O(h^2), k=2 -> O(h^4), k>=3 -> O(h^7) (super-conv.)
      NOTE: production `PPESolverDefectCorrection` is Neumann-only; this
      Dirichlet variant keeps a hand-rolled FD+DC pair as a CCD-elliptic
      operator + DC concept reference (paper §12.U2-a clarifies scope).
  (b) Current FVM/spsolve PPE operator under Neumann BC + gauge pin
      reference  p* = cos(pi x) cos(pi y)
      expected   O(h^2) (FVM/FDM projection baseline per PR-2)
      observed   N=8..128 slope ≈ 2.00
      Drives `twophase.ppe.PPEBuilder`, the sparse FVM matrix used by the
      current fvm_spsolve/fvm_direct pressure path. The historical
      PPESolverCCDLU Kronecker path is intentionally not used here; it is
      restricted to explicit smooth component/reference tests.

Usage
-----
  python experiment/ch12/exp_U2_ccd_poisson_ppe_bc.py
  python experiment/ch12/exp_U2_ccd_poisson_ppe_bc.py --plot-only
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
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    convergence_loglog, compute_convergence_rates,
)
from twophase.tools.experiment.gpu import (
    fd_laplacian_dirichlet_2d, sparse_solve_2d,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u2_ccd_poisson_ppe_bc"

DIRICHLET_GRID_SIZES = [8, 16, 32, 64, 128]
FVM_GRID_SIZES = [8, 16, 32, 64, 128]
DC_K_LIST = [1, 2, 3, 5, 10]


# ── Operator helpers ─────────────────────────────────────────────────────────

def _grid_2d(N: int, backend) -> Grid:
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    return Grid(cfg.grid, backend)


def _ccd_laplacian(ccd: CCDSolver, p: np.ndarray) -> np.ndarray:
    """CCD Laplacian = d2_x + d2_y via CCDSolver.differentiate."""
    _, d2x = ccd.differentiate(p, axis=0)
    _, d2y = ccd.differentiate(p, axis=1)
    return np.asarray(d2x) + np.asarray(d2y)


# ── U2-a: CCD-Poisson Dirichlet, DC k sweep ─────────────────────────────────

def _u2a_solve(N: int, k_dc: int, backend) -> dict:
    grid = _grid_2d(N, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)
    rhs = -2.0 * np.pi ** 2 * p_exact

    A = fd_laplacian_dirichlet_2d(N, h, backend)
    rhs_flat = rhs.ravel().copy()
    rhs_flat[_boundary_mask(N).ravel()] = 0.0

    p = np.asarray(sparse_solve_2d(backend, A, rhs_flat, shape=p_exact.shape))
    p = _zero_dirichlet(p)

    for _ in range(k_dc - 1):
        residual = rhs - _ccd_laplacian(ccd, p)
        residual = _zero_dirichlet(residual)
        delta = np.asarray(sparse_solve_2d(backend, A, residual.ravel(), shape=p.shape))
        delta = _zero_dirichlet(delta)
        p = p + delta

    err = np.abs(p - p_exact)
    return {
        "Linf": float(np.max(err)),
        "L2": float(np.sqrt(np.mean(err ** 2))),
    }


def _boundary_mask(N: int) -> np.ndarray:
    mask = np.zeros((N + 1, N + 1), dtype=bool)
    mask[0, :] = mask[-1, :] = True
    mask[:, 0] = mask[:, -1] = True
    return mask


def _zero_dirichlet(arr: np.ndarray) -> np.ndarray:
    out = arr.copy()
    out[0, :] = 0.0; out[-1, :] = 0.0
    out[:, 0] = 0.0; out[:, -1] = 0.0
    return out


def run_U2a():
    backend = Backend(use_gpu=False)
    rows = []
    for N in DIRICHLET_GRID_SIZES:
        entry = {"N": N, "h": 1.0 / N}
        for k in DC_K_LIST:
            res = _u2a_solve(N, k, backend)
            entry[f"Linf_k{k}"] = res["Linf"]
            entry[f"L2_k{k}"] = res["L2"]
        rows.append(entry)
    return {"dirichlet": rows}


# ── U2-b: Current FVM/spsolve PPE operator + Neumann gauge ──────────────────

def _u2b_solve(N: int, backend) -> dict:
    """Validate the current FVM PPE builder under Neumann BC + gauge pin."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    )
    grid = Grid(cfg.grid, backend)
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")

    X, Y = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
    f_rhs = -2.0 * np.pi ** 2 * p_exact

    rho = np.ones(grid.shape)
    triplet, shape = ppe_builder.build(rho)
    data, rows, cols = [np.asarray(a) for a in triplet]
    L = sp.csr_matrix((data, (rows, cols)), shape=shape)
    rhs = f_rhs.ravel().copy()
    rhs[ppe_builder._pin_dof] = 0.0

    p_flat = spla.spsolve(L, rhs)
    p = p_flat.reshape(grid.shape)
    gauge_shift = p.ravel()[ppe_builder._pin_dof] - p_exact.ravel()[ppe_builder._pin_dof]
    p = p - gauge_shift

    err = np.abs(p - p_exact)
    return {
        "Linf": float(np.max(err)),
        "L2": float(np.sqrt(np.mean(err ** 2))),
    }


def run_U2b():
    backend = Backend(use_gpu=False)
    rows = [
        {"N": N, "h": 1.0 / N, **_u2b_solve(N, backend)}
        for N in FVM_GRID_SIZES
    ]
    return {"fvm_direct": rows}


# ── Aggregator + plotting ────────────────────────────────────────────────────

def run_all() -> dict:
    return {
        "U2a": run_U2a(),
        "U2b": run_U2b(),
    }


def _slope_summary(rows, err_key: str) -> str:
    hs = [r["h"] for r in rows]
    errs = [r[err_key] for r in rows]
    rates = compute_convergence_rates(errs, hs)
    finite = [r for r in rates if np.isfinite(r)]
    return f"mean={np.mean(finite):.2f}" if finite else "n/a"


def make_figures(results: dict) -> None:
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11, 4.5))

    rows_a = results["U2a"]["dirichlet"]
    hs_a = [r["h"] for r in rows_a]
    series_a = {f"$k={k}$": [r[f"Linf_k{k}"] for r in rows_a] for k in DC_K_LIST}
    convergence_loglog(
        ax_a, hs_a, series_a,
        ref_orders=[2, 4, 7], xlabel="$h$", ylabel="$L_\\infty$ error",
        title="(a) CCD-Poisson Dirichlet, DC sweep")

    rows_b = results["U2b"]["fvm_direct"]
    hs_b = [r["h"] for r in rows_b]
    convergence_loglog(
        ax_b, hs_b,
        {"$L_\\infty$ (FVM PPE + gauge)": [r["Linf"] for r in rows_b]},
        ref_orders=[2], xlabel="$h$", ylabel="$L_\\infty$ error",
        title="(b) Current FVM PPE + Neumann gauge")

    save_figure(fig, OUT / "U2_ccd_poisson_ppe_bc", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    rows_a = results["U2a"]["dirichlet"]
    for k in DC_K_LIST:
        print(f"U2-a Dirichlet k={k:>2} slope:", _slope_summary(rows_a, f"Linf_k{k}"))
    print("U2-b current FVM PPE slope:", _slope_summary(results["U2b"]["fvm_direct"], "Linf"))


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> U2 outputs in {OUT}")


if __name__ == "__main__":
    main()
