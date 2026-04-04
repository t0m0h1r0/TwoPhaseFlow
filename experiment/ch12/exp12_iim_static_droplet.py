#!/usr/bin/env python3
"""IIM-CCD vs standard CCD-LU: static droplet Laplace pressure accuracy.

Compares two PPE solvers on the static droplet benchmark:
  1. CCD-LU  — standard CCD Kronecker + direct LU (no interface correction)
  2. IIM-CCD — same operator + zeroth-order IIM correction Δq = σκ⊙[m⁻(Lm⁺)−m⁺(Lm⁻)]

Setup
-----
  Domain : [0,1]², wall BC, no gravity, u* = 0
  Droplet: R = 0.25, centre (0.5, 0.5)
  ρ_l = 2.0, ρ_g = 1.0, σ = 1.0, We = 10.0
  Analytical Laplace pressure: Δp_exact = 2σ/R = 8.0

Output
------
  results/ch12_iim/laplace_error_table.txt  — error table per grid
  results/ch12_iim/iim_convergence.png      — log-log convergence plot
  results/ch12_iim/pressure_fields_N64.png  — side-by-side pressure fields
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.ppe_solver_ccd_lu import PPESolverCCDLU
from twophase.pressure.ppe_solver_iim import PPESolverIIM

OUT = pathlib.Path(__file__).resolve().parents[2] / "results" / "ch12_iim"
OUT.mkdir(parents=True, exist_ok=True)

# Physical parameters
RHO_L   = 2.0
RHO_G   = 1.0
SIGMA   = 1.0
WE      = 10.0
R       = 0.25
DT      = 1e-3    # dummy dt (u* = 0, RHS = 0 exactly from div u*)
DP_EXACT = 2 * SIGMA / R   # = 8.0


def _make_config(N):
    """Minimal SimulationConfig-like object for solver construction."""
    class _Solver:
        pseudo_tol     = 1e-10
        pseudo_maxiter = 500
        ppe_solver_type = "ccd_lu"
    class _Cfg:
        solver = _Solver()
    return _Cfg()


def run_one(N):
    """Solve static droplet PPE on N×N grid. Returns (e_ccdlu, e_iim)."""
    backend  = Backend(use_gpu=False)
    h        = 1.0 / N
    eps      = 1.5 * h

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")
    cfg  = _make_config(N)

    X, Y = grid.meshgrid()

    # Level-set: φ > 0 inside droplet (gas)
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R   # φ < 0 inside → flip for our convention
    phi = -phi                                           # φ > 0 inside (gas), φ < 0 outside (liquid)

    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * (1.0 - psi)      # inside=RHO_G, outside=RHO_L

    # Curvature — CurvatureCalculator.compute() expects ψ (CLS var ∈ [0,1]),
    # not the raw signed-distance φ.
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa     = np.asarray(curv_calc.compute(psi))

    # PPE builder (for RHS assembly: we use zero u* → RHS = 0)
    # We solve L p = 0 + CSF_balance_force contribution via IIM correction
    # In balanced-force projection the PPE RHS is ∇·u*/dt and the surface
    # tension enters only through the jump condition [p] = σκ.
    # For the static case u* = 0, so RHS = 0 everywhere.
    rhs = np.zeros_like(phi)

    # ── Solver 1: standard CCD-LU ────────────────────────────────────
    solver_ccd = PPESolverCCDLU(backend, cfg, grid, ccd=ccd)
    p_ccd = np.asarray(solver_ccd.solve(rhs, rho, DT))

    # ── Solver 2: IIM-CCD ────────────────────────────────────────────
    solver_iim = PPESolverIIM(backend, cfg, grid, ccd=ccd)
    # sigma/We is the dimensional surface tension used in the GFM jump
    p_iim = np.asarray(solver_iim.solve(
        rhs, rho, DT,
        phi=phi, kappa=kappa, sigma=SIGMA / WE
    ))

    def laplace_error(p):
        """Mean pressure inside minus outside vs. analytical Δp."""
        mask_in  = phi > 0
        mask_out = phi < 0
        dp = p[mask_in].mean() - p[mask_out].mean()
        return abs(dp - DP_EXACT / WE)   # scaled by We (dimensionless)

    return laplace_error(p_ccd), laplace_error(p_iim), p_ccd, p_iim, phi, X, Y


def main():
    grids = [32, 48, 64, 96, 128]
    err_ccd = []
    err_iim = []

    p_ccd_64 = p_iim_64 = phi_64 = X_64 = Y_64 = None

    for N in grids:
        ec, ei, pc, pi, phi, X, Y = run_one(N)
        err_ccd.append(ec)
        err_iim.append(ei)
        print(f"N={N:4d}  CCD-LU: {ec:.4e}   IIM-CCD: {ei:.4e}   ratio: {ec/max(ei,1e-16):.2f}×")
        if N == 64:
            p_ccd_64, p_iim_64, phi_64, X_64, Y_64 = pc, pi, phi, X, Y

    # ── Error table ──────────────────────────────────────────────────
    table_path = OUT / "laplace_error_table.txt"
    with open(table_path, "w") as f:
        f.write("N      CCD-LU          IIM-CCD         ratio\n")
        for N, ec, ei in zip(grids, err_ccd, err_iim):
            f.write(f"{N:6d}  {ec:.4e}  {ei:.4e}  {ec/max(ei,1e-16):.2f}x\n")
    print(f"\nTable saved: {table_path}")

    # ── Convergence plot ─────────────────────────────────────────────
    h_vals = [1.0 / N for N in grids]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.loglog(h_vals, err_ccd, "o--", color="steelblue", label="CCD-LU (no correction)")
    ax.loglog(h_vals, err_iim, "s-",  color="darkorange", label="IIM-CCD (this work)")

    # Reference slopes
    h_ref = np.array([h_vals[0], h_vals[-1]])
    for slope, ls, label in [(2, ":", "O(h²)"), (4, "-.", "O(h⁴)"), (6, "--", "O(h⁶)")]:
        scale = err_ccd[0] / h_vals[0]**slope
        ax.loglog(h_ref, scale * h_ref**slope, ls, color="gray", alpha=0.5, label=label)

    ax.set_xlabel("h = 1/N")
    ax.set_ylabel("|Δp − Δp_exact| / We")
    ax.set_title("Static droplet: Laplace pressure error")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    conv_path = OUT / "iim_convergence.png"
    plt.savefig(conv_path, dpi=150)
    plt.close()
    print(f"Convergence plot: {conv_path}")

    # ── Pressure field comparison (N=64) ─────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    vmax = max(np.abs(p_ccd_64).max(), np.abs(p_iim_64).max())

    for ax_, p_, title_ in zip(
        axes[:2],
        [p_ccd_64, p_iim_64],
        ["CCD-LU", "IIM-CCD"],
    ):
        im = ax_.pcolormesh(X_64, Y_64, p_, cmap="RdBu_r",
                            vmin=-vmax, vmax=vmax, shading="auto")
        plt.colorbar(im, ax=ax_)
        ax_.contour(X_64, Y_64, phi_64, levels=[0], colors="k", linewidths=1)
        ax_.set_title(title_)
        ax_.set_aspect("equal")

    diff = p_iim_64 - p_ccd_64
    im3  = axes[2].pcolormesh(X_64, Y_64, diff, cmap="RdBu_r",
                               vmin=-np.abs(diff).max(), vmax=np.abs(diff).max(),
                               shading="auto")
    plt.colorbar(im3, ax=axes[2])
    axes[2].contour(X_64, Y_64, phi_64, levels=[0], colors="k", linewidths=1)
    axes[2].set_title("IIM − CCD-LU")
    axes[2].set_aspect("equal")

    plt.suptitle(f"Static droplet pressure (N=64, R=0.25, Δp_exact={DP_EXACT/WE:.3f})")
    plt.tight_layout()
    field_path = OUT / "pressure_fields_N64.png"
    plt.savefig(field_path, dpi=150)
    plt.close()
    print(f"Field plot:        {field_path}")


if __name__ == "__main__":
    main()
