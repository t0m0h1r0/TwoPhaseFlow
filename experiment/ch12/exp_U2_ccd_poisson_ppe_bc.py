#!/usr/bin/env python3
"""[U2] CCD-Poisson + PPE BC — Tier I (uniform grid).

Paper ref: Chapter 12 U2 (sec:U2_ccd_poisson_ppe_bc; paper/sections/12u2_ccd_poisson_ppe_bc.tex).

Sub-tests
---------
  (a) Poisson Dirichlet reference, DC k = 1, 2, 3, 5, 10
      reference  p* = sin(pi x) sin(pi y)
      expected   k=1 -> O(h^2), k=2 -> O(h^4), k>=3 -> O(h^7) (super-conv.)
      NOTE: production `PPESolverDefectCorrection` is Neumann-only; this
      Dirichlet variant keeps a hand-rolled FD+DC pair as a CCD-elliptic
      operator + DC concept reference (paper §12.U2-a clarifies scope).
  (b) Production CCD-PPE Kronecker operator under Dirichlet BC patch
      reference  p* = cos(pi x) cos(pi y)
      expected   O(h^5)~O(h^6) (boundary scheme limited)
      observed   N=8..128 slopes 5.17 / 5.78 / 5.94 / 5.98 (overall 5.72)
      Drives `twophase.ppe.PPESolverCCDLU._build_sparse_operator`
      (production operator factory). Boundary rows are replaced with
      Dirichlet identity rows because the constant-rho CCD Kronecker
      Laplacian has a ~12-dim nullspace that the standard solve()
      interface's single-pin gauge cannot fix (documented in
      test_pressure.py:200-207).

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
from twophase.config import GridConfig, SimulationConfig, SolverConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ppe import PPESolverCCDLU
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
PROD_CCD_GRID_SIZES = [8, 16, 32, 64, 128]
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


# ── U2-b: Production CCD Kronecker operator + Dirichlet BC patch ────────────

def _u2b_solve(N: int, backend) -> dict:
    """Validate the production CCD-PPE Kronecker operator under Dirichlet BC.

    Drives `PPESolverCCDLU._build_sparse_operator` (production CCD operator
    factory). The standard `PPESolverCCDLU.solve()` Neumann + single-pin
    interface cannot be exercised directly here because the constant-ρ CCD
    Kronecker Laplacian has a ~12-dim nullspace that the single-pin gauge
    cannot fully fix (documented in `test_pressure.py:200-207`). The
    production-team-sanctioned workaround for smooth-MMS verification is to
    replace boundary rows of the assembled operator with Dirichlet identity
    rows, yielding a full-rank linear system that exposes the interior
    O(h⁶) accuracy bounded by the boundary scheme order.
    """
    import scipy.sparse.linalg as spla

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(
            ppe_solver_type="ccd_lu",
            allow_kronecker_lu=True,
        ),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe = PPESolverCCDLU(backend, cfg, grid, ccd=ccd)

    X, Y = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    p_exact = np.cos(np.pi * X) * np.cos(np.pi * Y)
    f_rhs = -2.0 * np.pi ** 2 * p_exact

    # Production CCD-PPE operator (constant ρ, ∇ρ = 0 ⇒ pure Kronecker Laplacian)
    rho = np.ones(grid.shape)
    drho_np = [np.zeros_like(rho), np.zeros_like(rho)]
    L = ppe._build_sparse_operator(rho, drho_np)

    # Replace boundary rows with Dirichlet identity (test_pressure.py pattern)
    L_lil = L.tolil()
    rhs = f_rhs.ravel().copy()
    for i in range(N + 1):
        for j in range(N + 1):
            if i == 0 or i == N or j == 0 or j == N:
                dof = i * (N + 1) + j
                L_lil[dof, :] = 0.0
                L_lil[dof, dof] = 1.0
                rhs[dof] = p_exact[i, j]

    p_flat = spla.spsolve(L_lil.tocsr(), rhs)
    p = p_flat.reshape(grid.shape)

    err = np.abs(p - p_exact)
    return {
        "Linf": float(np.max(err)),
        "L2": float(np.sqrt(np.mean(err ** 2))),
    }


def run_U2b():
    backend = Backend(use_gpu=False)
    rows = [
        {"N": N, "h": 1.0 / N, **_u2b_solve(N, backend)}
        for N in PROD_CCD_GRID_SIZES
    ]
    return {"prod_ccd": rows}


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

    rows_b = results["U2b"]["prod_ccd"]
    hs_b = [r["h"] for r in rows_b]
    convergence_loglog(
        ax_b, hs_b,
        {"$L_\\infty$ (prod CCD + Dirichlet patch)": [r["Linf"] for r in rows_b]},
        ref_orders=[5, 6], xlabel="$h$", ylabel="$L_\\infty$ error",
        title="(b) Production CCD-PPE op + Dirichlet patch")

    save_figure(fig, OUT / "U2_ccd_poisson_ppe_bc", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    rows_a = results["U2a"]["dirichlet"]
    for k in DC_K_LIST:
        print(f"U2-a Dirichlet k={k:>2} slope:", _slope_summary(rows_a, f"Linf_k{k}"))
    print("U2-b prod CCD + patch slope:", _slope_summary(results["U2b"]["prod_ccd"], "Linf"))


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
