#!/usr/bin/env python3
"""【10-13】PPE Neumann BC + gauge fixing verification.

Paper ref: §10.3.3 (sec:verify_ppe_neumann)

Tests:
  2D Poisson ∇²p = f on [0,1]², all-Neumann BC, gauge pin p_{0,0}=p*(0,0).
  Manufactured solution p* = cos(πx)cos(πy) (satisfies ∂p*/∂n = 0 naturally).
  Defect correction k=3: L_H = CCD (O(h⁶)), L_L = FD 5-point Neumann.

Expected:
  O(h⁶) or O(h⁵) convergence (boundary scheme O(h⁵) may become visible
  unlike the Dirichlet test where p*|∂Ω=0 suppresses boundary error).
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch10_ppe_neumann"
OUT.mkdir(parents=True, exist_ok=True)


# ── Analytical solution ──────────────────────────────────────────────────────

def analytical_solution(X, Y):
    """p* = cos(πx)cos(πy), f = -2π² cos(πx)cos(πy). Neumann BC natural."""
    p = np.cos(np.pi * X) * np.cos(np.pi * Y)
    lap_p = -2.0 * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y)
    return p, lap_p


# ── L_H: CCD Laplacian evaluation (O(h⁶)) ──────────────────────────────────

def eval_LH(p, ccd, backend):
    """Evaluate L_H p = ∇²p using CCD (O(h⁶)), wall (Neumann) BC."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        _, d2p = ccd.differentiate(p_dev, ax)
        Lp += d2p
    return np.asarray(backend.to_host(Lp))


# ── L_L: FD 5-point Laplacian with Neumann BC ───────────────────────────────

def build_fd_laplacian_neumann(Nx, Ny, hx, hy):
    """Build 2D 5-point FD Laplacian with Neumann BC (ghost-node elimination).

    Grid: (Nx+1) x (Ny+1) nodes, indices (0..Nx, 0..Ny).
    Neumann ∂p/∂n = 0 at all boundaries: ghost-node approach gives
    modified stencil at boundary nodes.
    """
    nx, ny = Nx + 1, Ny + 1
    n = nx * ny

    def idx(i, j):
        return i * ny + j

    rows, cols, vals = [], [], []

    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)

            # Standard 5-point stencil center coefficient
            center = 0.0

            # x-direction
            if i > 0:
                rows.append(k); cols.append(idx(i-1, j)); vals.append(1.0 / hx**2)
                center -= 1.0 / hx**2
            if i < Nx:
                rows.append(k); cols.append(idx(i+1, j)); vals.append(1.0 / hx**2)
                center -= 1.0 / hx**2

            # Neumann BC: ∂p/∂n = 0 → ghost node = interior neighbor
            if i == 0:
                # ghost at i=-1: p[-1,j] = p[1,j] → adds 1/hx² to p[1,j]
                rows.append(k); cols.append(idx(1, j)); vals.append(1.0 / hx**2)
                center -= 1.0 / hx**2
            if i == Nx:
                # ghost at i=Nx+1: p[Nx+1,j] = p[Nx-1,j]
                rows.append(k); cols.append(idx(Nx-1, j)); vals.append(1.0 / hx**2)
                center -= 1.0 / hx**2

            # y-direction
            if j > 0:
                rows.append(k); cols.append(idx(i, j-1)); vals.append(1.0 / hy**2)
                center -= 1.0 / hy**2
            if j < Ny:
                rows.append(k); cols.append(idx(i, j+1)); vals.append(1.0 / hy**2)
                center -= 1.0 / hy**2

            if j == 0:
                rows.append(k); cols.append(idx(i, 1)); vals.append(1.0 / hy**2)
                center -= 1.0 / hy**2
            if j == Ny:
                rows.append(k); cols.append(idx(i, Ny-1)); vals.append(1.0 / hy**2)
                center -= 1.0 / hy**2

            rows.append(k); cols.append(k); vals.append(center)

    L = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
    return L


def pin_gauge(L, rhs_flat, pin_dof, pin_val):
    """Pin one node to fix the Neumann null space.

    Replace row pin_dof with identity, set rhs to pin_val.
    """
    L_lil = L.tolil()
    L_lil[pin_dof, :] = 0.0
    L_lil[pin_dof, pin_dof] = 1.0
    rhs_flat[pin_dof] = pin_val
    return L_lil.tocsr(), rhs_flat


# ── Defect Correction with Neumann BC ────────────────────────────────────────

def defect_correction_neumann(rhs_2d, ccd, backend, L_L_pinned, pin_dof, pin_val, k_max=3):
    """Defect correction for Neumann PPE with gauge fixing.

    Algorithm (eq:dc_three_step):
      d^(k) = b - L_H p^(k)
      L_L δp^(k+1) = d^(k)    (pinned system)
      p^(k+1) = p^(k) + δp^(k+1)
    """
    shape = rhs_2d.shape
    p = np.zeros_like(rhs_2d)

    for k in range(k_max):
        # Step 1: CCD residual
        Lp = eval_LH(p, ccd, backend)
        d = rhs_2d - Lp

        # Pin gauge in residual
        d_flat = d.ravel().copy()
        d_flat[pin_dof] = pin_val - p.ravel()[pin_dof]

        # Step 2: solve L_L δp = d
        dp_flat = spsolve(L_L_pinned, d_flat)
        dp = dp_flat.reshape(shape)

        # Step 3: update
        p = p + dp

    return p


# ── Main experiment ──────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend(use_gpu=False)

    Ns = [8, 16, 32, 64, 128]
    k_dc = 3

    results = []

    print(f"\n{'N':>5} | {'h':>8} | {'L∞ error':>12} | {'order':>6}")
    print("-" * 45)

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N

        X, Y = grid.meshgrid()
        p_exact, rhs = analytical_solution(X, Y)

        # Build Neumann FD Laplacian
        L_L = build_fd_laplacian_neumann(N, N, h, h)

        # Pin gauge at (0,0): p_{0,0} = p*(0,0) = cos(0)cos(0) = 1.0
        pin_dof = 0
        pin_val = float(p_exact.ravel()[pin_dof])

        rhs_flat = rhs.ravel().copy()
        L_L_pinned, rhs_flat = pin_gauge(L_L.copy(), rhs_flat, pin_dof, pin_val)

        # Run defect correction
        p_dc = defect_correction_neumann(
            rhs, ccd, backend, L_L_pinned,
            pin_dof, pin_val, k_max=k_dc
        )

        err_Li = float(np.max(np.abs(p_dc - p_exact)))
        results.append({"N": N, "h": h, "Li": err_Li})

        # Convergence order
        order_str = "---"
        if len(results) > 1:
            r0, r1 = results[-2], results[-1]
            if r0["Li"] > 0 and r1["Li"] > 0:
                order = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])
                order_str = f"{order:.2f}"

        print(f"{N:>5} | {h:>8.4f} | {err_Li:>12.3e} | {order_str:>6}")

    return results


def save_latex_table(results):
    with open(OUT / "table_ppe_neumann.tex", "w") as fp:
        fp.write("% Auto-generated by exp10_13_ppe_neumann.py\n")
        fp.write("\\begin{tabular}{rrrr}\n\\toprule\n")
        fp.write("$N$ & $h$ & $L^\\infty$ 誤差 & 次数 \\\\\n\\midrule\n")

        for i, r in enumerate(results):
            order_str = "---"
            if i > 0:
                r0 = results[i-1]
                if r0["Li"] > 0 and r["Li"] > 0:
                    order = np.log(r["Li"] / r0["Li"]) / np.log(r["h"] / r0["h"])
                    order_str = f"{order:.1f}"

            fp.write(f"${r['N']}$ & $1/{r['N']}$ & ${r['Li']:.2e}$ & {order_str} \\\\\n")

        fp.write("\\bottomrule\n\\end{tabular}\n")

    print(f"\n  Saved: {OUT / 'table_ppe_neumann.tex'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-13】PPE Neumann BC + Gauge Fixing Verification")
    print("=" * 80)

    results = run_experiment()
    save_latex_table(results)

    np.savez(OUT / "ppe_neumann_data.npz", results=results)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
