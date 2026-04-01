"""
CCD-Poisson Iterative Solver Verification (§10.3.3)
====================================================
2D CCD-Poisson operator verification using LGMRES (no LU).

Test cases:
  C-1: Grid convergence of 2D Poisson (Dirichlet BC) — O(h^6+) verification
  C-2: LGMRES convergence behaviour (Dirichlet BC) — residual history
  C-3: Variable-density self-consistency (Dirichlet BC, rho_l/rho_g = 10)

All tests use Dirichlet BC enforced by replacing boundary rows of the CCD
Kronecker operator with identity rows.  This eliminates the Neumann null
space (ASM-002) and isolates the CCD operator's spatial accuracy.

Note on sweep solver:
  PPESolverSweep (matrix-free defect correction) is unstable for standalone
  Poisson tests — ADI splitting amplifies Neumann null-space components.
  Sweep convergence requires production simulation context; its verification
  is delegated to multiphase benchmarks (§11).

Experiment policy (§1 01_PROJECT_MAP.md): reuse src/ libraries.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import scipy.sparse.linalg as spla
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig, SolverConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.pressure.ppe_solver_pseudotime import PPESolverPseudoTime

RESULTS_DIR = "results/ccd_ppe_iterative"
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_solver(N: int):
    """Create Grid, Backend, CCDSolver, PPESolverPseudoTime for N×N grid."""
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    sc = SolverConfig(ppe_solver_type="pseudotime", pseudo_tol=1e-12,
                      pseudo_maxiter=5000)
    config = SimulationConfig(solver=sc)
    solver = PPESolverPseudoTime(backend, config, grid, ccd=ccd)
    return grid, backend, ccd, solver


def _build_dirichlet_system(solver, rho, rhs, p_bc, N):
    """Build CCD Kronecker operator with Dirichlet BC on boundary rows.

    Returns (A, b) where A is csr_matrix and b is ndarray.
    """
    rho_np = np.asarray(rho, dtype=float)
    xp = solver.xp
    rho_dev = xp.asarray(rho_np)
    drho_np = []
    for ax in range(solver.ndim):
        dr, _ = solver.ccd.differentiate(rho_dev, ax)
        drho_np.append(np.asarray(solver.backend.to_host(dr), dtype=float))

    L = solver._build_sparse_operator(rho_np, drho_np)
    L_lil = L.tolil()
    b = rhs.ravel().copy()
    n_pts = N + 1

    for i in range(n_pts):
        for j in range(n_pts):
            if i == 0 or i == N or j == 0 or j == N:
                dof = i * n_pts + j
                L_lil[dof, :] = 0.0
                L_lil[dof, dof] = 1.0
                b[dof] = p_bc.ravel()[dof]

    return L_lil.tocsr(), b


def _lgmres_solve(A, b, tol=1e-12, maxiter=5000, track_residuals=False):
    """LGMRES solve. Returns (x, info, n_iters, [residuals])."""
    residuals = []
    counter = [0]

    def callback(xk):
        counter[0] += 1
        if track_residuals:
            residuals.append(float(np.linalg.norm(b - A @ xk)))

    atol = max(1e-14, tol * float(np.linalg.norm(b)))
    x, info = spla.lgmres(A, b, rtol=tol, maxiter=maxiter, atol=atol,
                          callback=callback)
    if track_residuals:
        return x, info, counter[0], np.array(residuals)
    return x, info, counter[0]


# ---------------------------------------------------------------------------
# Test C-1: Grid Convergence
# ---------------------------------------------------------------------------

def test_c1():
    """2D Poisson, Dirichlet BC, uniform rho=1.
    p* = sin(pi x) sin(pi y), f = -2 pi^2 sin(pi x) sin(pi y).
    """
    print("\n" + "=" * 70)
    print("Test C-1: Grid Convergence (Dirichlet BC, LGMRES)")
    print("=" * 70)

    Ns = [8, 16, 32, 64, 128]
    errors, iters_list = [], []

    for N in Ns:
        grid, backend, ccd, solver = _make_solver(N)
        x = np.linspace(0, 1, N + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")

        p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)
        rhs = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
        rho = np.ones_like(X)

        A, b = _build_dirichlet_system(solver, rho, rhs, p_exact, N)
        p_flat, info, n_iters = _lgmres_solve(A, b)
        p_sol = p_flat.reshape(grid.shape)

        err = np.max(np.abs(p_sol - p_exact))
        errors.append(err)
        iters_list.append(n_iters)
        print(f"  N={N:4d}  E_inf={err:.3e}  iters={n_iters}")

    errors = np.array(errors)
    hs = np.array([1.0 / N for N in Ns])
    orders = np.log(errors[:-1] / errors[1:]) / np.log(2.0)
    for k, o in enumerate(orders):
        print(f"  order N={Ns[k]}→{Ns[k+1]}: p={o:.2f}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    np.savez(os.path.join(RESULTS_DIR, "c1.npz"),
             Ns=Ns, hs=hs, errors=errors, orders=orders,
             iters=np.array(iters_list))
    return Ns, hs, errors, orders, iters_list


# ---------------------------------------------------------------------------
# Test C-2: LGMRES Convergence Behaviour
# ---------------------------------------------------------------------------

def test_c2():
    """Track LGMRES residual history at N=16, 32, 64 (Dirichlet BC)."""
    print("\n" + "=" * 70)
    print("Test C-2: LGMRES Convergence History")
    print("=" * 70)

    Ns = [16, 32, 64]
    results = {}

    for N in Ns:
        grid, backend, ccd, solver = _make_solver(N)
        x = np.linspace(0, 1, N + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")

        p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)
        rhs = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
        rho = np.ones_like(X)

        A, b = _build_dirichlet_system(solver, rho, rhs, p_exact, N)
        p_flat, info, n_iters, res_hist = _lgmres_solve(
            A, b, track_residuals=True)

        err = np.max(np.abs(p_flat.reshape(grid.shape) - p_exact))
        results[N] = {"error": err, "n_iters": n_iters, "residuals": res_hist}
        res_str = " → ".join(f"{r:.2e}" for r in res_hist)
        print(f"  N={N:3d}  iters={n_iters}  E_inf={err:.3e}")
        print(f"         residuals: {res_str}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    save_dict = {"Ns": Ns}
    for N in Ns:
        save_dict[f"N{N}_error"] = results[N]["error"]
        save_dict[f"N{N}_residuals"] = results[N]["residuals"]
    np.savez(os.path.join(RESULTS_DIR, "c2.npz"), **save_dict)
    return Ns, results


# ---------------------------------------------------------------------------
# Test C-3: Variable Density
# ---------------------------------------------------------------------------

def test_c3():
    """Variable-density Poisson, Dirichlet BC, rho_l/rho_g=10.
    CCD-consistent RHS (rhs = L_CCD^rho p*).
    """
    print("\n" + "=" * 70)
    print("Test C-3: Variable Density (rho_l/rho_g=10, Dirichlet, LGMRES)")
    print("=" * 70)

    rho_l, rho_g = 10.0, 1.0
    Ns = [16, 32, 64]
    errors, iters_list = [], []

    for N in Ns:
        grid, backend, ccd, solver = _make_solver(N)
        h = 1.0 / N
        eps = 3.0 * h
        x = np.linspace(0, 1, N + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")

        s = X - 0.5
        H = np.where(s < -eps, 0.0,
            np.where(s > eps, 1.0, 0.5 * (1.0 + s / eps)))
        rho = rho_g + (rho_l - rho_g) * H
        p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)

        # CCD-consistent RHS
        xp = backend.xp
        p_dev = xp.asarray(p_exact)
        rho_dev = xp.asarray(rho)
        dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
        dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
        drho_x, _ = ccd.differentiate(rho_dev, 0)
        drho_y, _ = ccd.differentiate(rho_dev, 1)

        rhs = (np.asarray(d2p_dx2 + d2p_dy2) / rho
               - np.asarray(drho_x) / rho**2 * np.asarray(dp_dx)
               - np.asarray(drho_y) / rho**2 * np.asarray(dp_dy))

        A, b = _build_dirichlet_system(solver, rho, rhs, p_exact, N)
        p_flat, info, n_iters = _lgmres_solve(A, b)

        err = np.max(np.abs(p_flat.reshape(grid.shape) - p_exact))
        errors.append(err)
        iters_list.append(n_iters)
        print(f"  N={N:3d}  E_inf={err:.3e}  iters={n_iters}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    np.savez(os.path.join(RESULTS_DIR, "c3.npz"),
             Ns=Ns, errors=np.array(errors), iters=np.array(iters_list),
             rho_l=rho_l, rho_g=rho_g)
    return Ns, errors, iters_list


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_c1(Ns, hs, errors, orders, _):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.loglog(hs, errors, "b-o", lw=1.8, ms=7, label="LGMRES (CCD Kronecker)")
    ref6 = errors[0] * (hs / hs[0])**6
    ref4 = errors[0] * (hs / hs[0])**4
    ax.loglog(hs, ref6, "k:", lw=0.8, label=r"$O(h^6)$")
    ax.loglog(hs, ref4, "k-.", lw=0.8, label=r"$O(h^4)$")
    for k in range(len(orders)):
        hmid = np.sqrt(hs[k] * hs[k+1])
        emid = np.sqrt(errors[k] * errors[k+1])
        ax.annotate(f"p={orders[k]:.1f}", xy=(hmid, emid),
                    fontsize=9, color="blue", ha="center",
                    xytext=(0, -14), textcoords="offset points")
    ax.set_xlabel("Grid spacing $h$", fontsize=12)
    ax.set_ylabel(r"$L^\infty$ error", fontsize=12)
    ax.set_title("Test C-1: CCD-Poisson Grid Convergence (2D, Dirichlet BC)", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, which="both", ls="--", alpha=0.4)
    fig.tight_layout()
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = os.path.join(FIGURES_DIR, "c1_convergence.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved: {path}")


def fig_c2(Ns, results):
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = ["#2166ac", "#d62728", "#2ca02c"]
    for N, col in zip(Ns, colors):
        r = results[N]["residuals"]
        if len(r) > 0:
            ax.semilogy(range(1, len(r)+1), r, f"{col}", lw=1.5, marker="o",
                        ms=5, label=f"N={N} ({results[N]['n_iters']} iters)")
    ax.set_xlabel("Outer iteration", fontsize=12)
    ax.set_ylabel(r"Residual $\|Ap - b\|_2$", fontsize=12)
    ax.set_title("Test C-2: LGMRES Convergence History (Dirichlet BC)", fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, which="both", ls="--", alpha=0.4)
    fig.tight_layout()
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = os.path.join(FIGURES_DIR, "c2_convergence.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import shutil

    c1 = test_c1()
    c2_Ns, c2_results = test_c2()
    c3 = test_c3()

    print("\n--- Generating figures ---")
    fig_c1(*c1)
    fig_c2(c2_Ns, c2_results)

    dst_dir = "paper/figures"
    os.makedirs(dst_dir, exist_ok=True)
    for fname in ["c1_convergence.png", "c2_convergence.png"]:
        src = os.path.join(FIGURES_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst_dir, fname))
            print(f"Copied {src} -> {dst_dir}/{fname}")

    print("\nAll tests complete.")
