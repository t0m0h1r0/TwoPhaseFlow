#!/usr/bin/env python3
"""【10-14】Variable-density PPE convergence verification.

Paper ref: §10.3.4 (sec:verify_ppe_varrho)

Tests:
  2D variable-density Poisson ∇·(1/ρ ∇p) = q on [0,1]², Dirichlet BC.
  Manufactured solution p* = sin(πx)sin(πy).
  Density field ρ(x,y) = ρ_g + (ρ_l - ρ_g) H_ε(φ_0),
  φ_0 = sqrt((x-0.5)²+(y-0.5)²) - 0.25 (circular interface).

  Solver: Defect correction (DC) with k=3 iterations.
    L_H = CCD variable-density product-rule (matrix-free, O(h⁶)).
    L_L = FD variable-density product-rule 5-point (sparse direct LU, O(h²)).
  NOTE: LGMRES is NOT used — it fails for interface-type density fields.

Expected:
  ρ_l/ρ_g = 1: matches Dirichlet test (O(h⁶+))
  Higher density ratios: convergence limited by DC with interface density.
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

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch10_ppe_varrho"
OUT.mkdir(parents=True, exist_ok=True)


# ── Smoothed Heaviside / Delta ───────────────────────────────────────────────

def smoothed_heaviside(phi, eps):
    return np.where(
        phi < -eps, 0.0,
        np.where(phi > eps, 1.0,
                 0.5 * (1.0 + phi / eps + np.sin(np.pi * phi / eps) / np.pi)))


def smoothed_delta(phi, eps):
    mask = np.abs(phi) <= eps
    delta = np.zeros_like(phi)
    delta[mask] = 0.5 / eps * (1.0 + np.cos(np.pi * phi[mask] / eps))
    return delta


# ── Density field and analytical RHS ─────────────────────────────────────────

def build_density_field(X, Y, rho_l, rho_g, eps):
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    H = smoothed_heaviside(phi, eps)
    rho = rho_g + (rho_l - rho_g) * H
    return rho, phi


def analytical_rhs(X, Y, rho, rho_l, rho_g, phi, eps):
    """q = ∇·(1/ρ ∇p*) for p* = sin(πx)sin(πy)."""
    pi = np.pi
    sinx, siny = np.sin(pi * X), np.sin(pi * Y)
    cosx, cosy = np.cos(pi * X), np.cos(pi * Y)

    lap_p = -2.0 * pi**2 * sinx * siny
    dp_dx = pi * cosx * siny
    dp_dy = pi * sinx * cosy

    delta = smoothed_delta(phi, eps)
    r = np.maximum(np.sqrt((X - 0.5)**2 + (Y - 0.5)**2), 1e-14)
    drho_dx = (rho_l - rho_g) * delta * (X - 0.5) / r
    drho_dy = (rho_l - rho_g) * delta * (Y - 0.5) / r

    q = lap_p / rho - (drho_dx * dp_dx + drho_dy * dp_dy) / rho**2
    return q


# ── L_H: CCD variable-density operator (matrix-free, O(h⁶)) ────────────────

def eval_LH_varrho(p, rho, ccd, backend):
    """L_H p = (1/ρ)(D²ₓp + D²ᵧp) − (Dₓρ/ρ²)(Dₓp) − (Dᵧρ/ρ²)(Dᵧp)."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    rho_dev = xp.asarray(rho)

    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        dp, d2p = ccd.differentiate(p_dev, ax)
        drho, _ = ccd.differentiate(rho_dev, ax)
        Lp += d2p / rho_dev - (drho / rho_dev**2) * dp

    return np.asarray(backend.to_host(Lp))


# ── L_L: FD variable-density product-rule Laplacian (O(h²)) ─────────────────

def build_fd_varrho_product_rule_dirichlet(Nx, Ny, hx, hy, rho):
    """Build FD product-rule ∇·(1/ρ ∇p) with Dirichlet BC."""
    nx, ny = Nx + 1, Ny + 1
    n = nx * ny

    def idx(i, j):
        return i * ny + j

    drho_dx = np.zeros_like(rho)
    drho_dy = np.zeros_like(rho)
    for i in range(1, Nx):
        for j in range(ny):
            drho_dx[i, j] = (rho[i+1, j] - rho[i-1, j]) / (2.0 * hx)
    for i in range(nx):
        for j in range(1, Ny):
            drho_dy[i, j] = (rho[i, j+1] - rho[i, j-1]) / (2.0 * hy)

    rows, cols, vals = [], [], []

    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)
            if i == 0 or i == Nx or j == 0 or j == Ny:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                inv_rho = 1.0 / rho[i, j]
                cx = drho_dx[i, j] / rho[i, j]**2
                cy = drho_dy[i, j] / rho[i, j]**2

                rows.append(k); cols.append(idx(i+1, j)); vals.append(inv_rho / hx**2)
                rows.append(k); cols.append(idx(i-1, j)); vals.append(inv_rho / hx**2)
                rows.append(k); cols.append(idx(i, j+1)); vals.append(inv_rho / hy**2)
                rows.append(k); cols.append(idx(i, j-1)); vals.append(inv_rho / hy**2)

                center = -2.0 * inv_rho / hx**2 - 2.0 * inv_rho / hy**2

                rows.append(k); cols.append(idx(i+1, j)); vals.append(-cx / (2.0 * hx))
                rows.append(k); cols.append(idx(i-1, j)); vals.append( cx / (2.0 * hx))
                rows.append(k); cols.append(idx(i, j+1)); vals.append(-cy / (2.0 * hy))
                rows.append(k); cols.append(idx(i, j-1)); vals.append( cy / (2.0 * hy))

                rows.append(k); cols.append(k); vals.append(center)

    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


# ── Defect Correction solver ────────────────────────────────────────────────

def solve_varrho_dc(rhs, rho, ccd, backend, L_L_mat, k_max=3):
    """Defect correction: d^(k) = b − L_H p^(k); L_L δp = d^(k); p^(k+1) = p^(k) + δp."""
    shape = rhs.shape
    p = np.zeros_like(rhs)

    for k in range(k_max):
        Lp = eval_LH_varrho(p, rho, ccd, backend)
        d = rhs - Lp
        # Enforce Dirichlet BC on defect
        d[0, :] = 0.0; d[-1, :] = 0.0
        d[:, 0] = 0.0; d[:, -1] = 0.0

        dp = spsolve(L_L_mat, d.ravel()).reshape(shape)
        p = p + dp
        # Enforce Dirichlet BC on solution
        p[0, :] = 0.0; p[-1, :] = 0.0
        p[:, 0] = 0.0; p[:, -1] = 0.0

    return p


# ── Main experiment ──────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend(use_gpu=False)

    Ns = [16, 32, 64, 128]
    density_ratios = [1, 10, 100, 1000]
    k_dc = 3

    all_results = {dr: [] for dr in density_ratios}

    for dr in density_ratios:
        rho_l = float(dr)
        rho_g = 1.0

        print(f"\n--- ρ_l/ρ_g = {dr} (DC k={k_dc}) ---")
        print(f"  {'N':>5} | {'h':>8} | {'L∞ error':>12} | {'order':>6}")
        print("  " + "-" * 43)

        for N in Ns:
            gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
            grid = Grid(gc, backend)
            ccd = CCDSolver(grid, backend, bc_type="wall")
            h = 1.0 / N

            X, Y = grid.meshgrid()
            p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)

            eps = 1.5 * h
            rho, phi = build_density_field(X, Y, rho_l, rho_g, eps)
            rhs = analytical_rhs(X, Y, rho, rho_l, rho_g, phi, eps)

            # Enforce Dirichlet BC on rhs (p* = 0 on boundary for sin·sin)
            rhs[0, :] = 0.0; rhs[-1, :] = 0.0
            rhs[:, 0] = 0.0; rhs[:, -1] = 0.0

            # Build FD variable-density Laplacian
            L_L = build_fd_varrho_product_rule_dirichlet(N, N, h, h, rho)

            # Defect correction with k iterations
            p_dc = solve_varrho_dc(rhs, rho, ccd, backend, L_L, k_max=k_dc)

            err_Li = float(np.max(np.abs(p_dc - p_exact)))
            all_results[dr].append({"N": N, "h": h, "Li": err_Li})

            order_str = "---"
            if len(all_results[dr]) > 1:
                r0, r1 = all_results[dr][-2], all_results[dr][-1]
                if r0["Li"] > 1e-15 and r1["Li"] > 1e-15:
                    order = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])
                    order_str = f"{order:.2f}"

            print(f"  {N:>5} | {h:>8.4f} | {err_Li:>12.3e} | {order_str:>6}")

    return all_results


def save_latex_table(all_results, density_ratios, Ns):
    with open(OUT / "table_ppe_varrho.tex", "w") as fp:
        fp.write("% Auto-generated by exp10_14_ppe_variable_density.py\n")
        fp.write("\\begin{tabular}{r" + "c" * len(density_ratios) + "}\n\\toprule\n")
        fp.write("$N$")
        for dr in density_ratios:
            fp.write(f" & $\\rho_l/\\rho_g = {dr}$")
        fp.write(" \\\\\n\\midrule\n")

        for i, N in enumerate(Ns):
            fp.write(f"${N}$")
            for dr in density_ratios:
                e = all_results[dr][i]["Li"]
                fp.write(f" & ${e:.2e}$")
            fp.write(" \\\\\n")

        fp.write("\\midrule\n次数")
        for dr in density_ratios:
            res = all_results[dr]
            orders = []
            for j in range(1, len(res)):
                if res[j-1]["Li"] > 1e-15 and res[j]["Li"] > 1e-15:
                    orders.append(np.log(res[j]["Li"] / res[j-1]["Li"])
                                  / np.log(res[j]["h"] / res[j-1]["h"]))
            if orders:
                avg = np.mean(orders[-2:]) if len(orders) >= 2 else orders[-1]
                fp.write(f" & $\\approx {avg:.1f}$")
            else:
                fp.write(" & ---")
        fp.write(" \\\\\n\\bottomrule\n\\end{tabular}\n")

    print(f"\n  Saved: {OUT / 'table_ppe_varrho.tex'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-14】Variable-Density PPE Convergence (Defect Correction k=3)")
    print("=" * 80)

    density_ratios = [1, 10, 100, 1000]
    Ns = [16, 32, 64, 128]

    all_results = run_experiment()
    save_latex_table(all_results, density_ratios, Ns)

    np.savez(OUT / "ppe_varrho_data.npz", results=dict(all_results))
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
