#!/usr/bin/env python3
"""【11-8】Variable-density PPE breakdown limit: density ratio sweep.

Paper ref: §11.5 (sec:interface_crossing)

Parametric sweep of density ratios ρ_l/ρ_g = 2, 5, 10, 20, 50, 100
with interface-type (smoothed Heaviside) density field.
Manufactured solution: p* = sin(πx)sin(πy), circular interface R=0.25.
Solver: Defect correction (DC k=3) with FD product-rule L_L.

Purpose:
  Quantitatively identify the breakdown threshold of the smoothed
  Heaviside one-fluid PPE approach, providing numerical evidence
  for the necessity of GFM (Ghost Fluid Method).

Expected:
  ρ_l/ρ_g ≤ 5:   DC converges (residual reduction)
  ρ_l/ρ_g = 10:   marginal (slow convergence)
  ρ_l/ρ_g ≥ 20:   DC diverges (spectral radius > 1)

This is a "failure is success" experiment: demonstrating divergence
at high density ratio is the primary scientific result.
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

OUT = pathlib.Path(__file__).resolve().parent / "results" / "varrho_breakdown"
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

def build_interface_density(X, Y, rho_l, rho_g, eps):
    """Build interface-type density field (smoothed Heaviside)."""
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


# ── CCD variable-density operator (matrix-free, O(h⁶)) ──────────────────────

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


# ── FD variable-density product-rule Laplacian (O(h²)) ─────────────────────

def build_fd_varrho_dirichlet(Nx, Ny, hx, hy, rho):
    """Build FD product-rule ∇·(1/ρ ∇p) with Dirichlet BC."""
    nx, ny = Nx + 1, Ny + 1
    n = nx * ny

    def idx(i, j):
        return i * ny + j

    drho_dx = np.zeros_like(rho)
    drho_dy = np.zeros_like(rho)
    for i in range(1, Nx):
        for j in range(ny):
            drho_dx[i, j] = (rho[i + 1, j] - rho[i - 1, j]) / (2.0 * hx)
    for i in range(nx):
        for j in range(1, Ny):
            drho_dy[i, j] = (rho[i, j + 1] - rho[i, j - 1]) / (2.0 * hy)

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

                rows.append(k); cols.append(idx(i + 1, j))
                vals.append(inv_rho / hx**2 - cx / (2.0 * hx))
                rows.append(k); cols.append(idx(i - 1, j))
                vals.append(inv_rho / hx**2 + cx / (2.0 * hx))
                rows.append(k); cols.append(idx(i, j + 1))
                vals.append(inv_rho / hy**2 - cy / (2.0 * hy))
                rows.append(k); cols.append(idx(i, j - 1))
                vals.append(inv_rho / hy**2 + cy / (2.0 * hy))

                center = -2.0 * inv_rho * (1.0 / hx**2 + 1.0 / hy**2)
                rows.append(k); cols.append(k); vals.append(center)

    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


# ── Defect Correction solver with residual tracking ──────────────────────────

def solve_varrho_dc_tracked(rhs, rho, ccd, backend, L_L_mat, k_max=3):
    """DC solver returning residual history per iteration."""
    shape = rhs.shape
    p = np.zeros_like(rhs)
    residuals = []

    for k in range(k_max):
        Lp = eval_LH_varrho(p, rho, ccd, backend)
        d = rhs - Lp
        d[0, :] = 0.0; d[-1, :] = 0.0
        d[:, 0] = 0.0; d[:, -1] = 0.0

        res_norm = float(np.max(np.abs(d)))
        residuals.append(res_norm)

        dp = spsolve(L_L_mat, d.ravel()).reshape(shape)
        p = p + dp
        p[0, :] = 0.0; p[-1, :] = 0.0
        p[:, 0] = 0.0; p[:, -1] = 0.0

    # Final residual
    Lp = eval_LH_varrho(p, rho, ccd, backend)
    d_final = rhs - Lp
    d_final[0, :] = 0.0; d_final[-1, :] = 0.0
    d_final[:, 0] = 0.0; d_final[:, -1] = 0.0
    residuals.append(float(np.max(np.abs(d_final))))

    return p, residuals


# ── Main experiment ──────────────────────────────────────────────────────────

def run_single(N, rho_l, rho_g, k_dc=3):
    """Run single PPE test with interface density."""
    backend = Backend(use_gpu=False)
    h = 1.0 / N
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    X, Y = grid.meshgrid()
    p_exact = np.sin(np.pi * X) * np.sin(np.pi * Y)

    rho, phi = build_interface_density(X, Y, rho_l, rho_g, eps)
    rhs = analytical_rhs(X, Y, rho, rho_l, rho_g, phi, eps)

    # Enforce Dirichlet BC on RHS
    rhs[0, :] = 0.0; rhs[-1, :] = 0.0
    rhs[:, 0] = 0.0; rhs[:, -1] = 0.0

    L_L = build_fd_varrho_dirichlet(N, N, h, h, rho)
    p_num, residuals = solve_varrho_dc_tracked(rhs, rho, ccd, backend, L_L, k_max=k_dc)

    err = float(np.max(np.abs(p_num - p_exact)))
    res_ratio = residuals[-1] / residuals[0] if residuals[0] > 1e-16 else float('inf')

    converged = res_ratio < 1.0

    return {
        "N": N,
        "rho_ratio": rho_l / rho_g,
        "L_inf_error": err,
        "residuals": residuals,
        "res_ratio": res_ratio,
        "converged": converged,
    }


def main():
    print("\n" + "=" * 80)
    print("  【11-8】Variable-Density PPE Breakdown Limit: Density Ratio Sweep")
    print("=" * 80 + "\n")

    N = 64  # Fixed grid
    density_ratios = [2, 5, 10, 20, 50, 100]
    k_dc = 3
    all_results = []

    print(f"  Grid: N={N}, DC iterations: k={k_dc}")
    print(f"  Density field: smoothed Heaviside (interface-type), ε = 1.5h\n")

    print(f"  {'ρ_l/ρ_g':>8} | {'L∞ error':>12} | {'||r_0||':>12} | "
          f"{'||r_final||':>12} | {'ratio':>8} | {'status':>12}")
    print("  " + "-" * 80)

    for dr in density_ratios:
        rho_l = float(dr)
        rho_g = 1.0

        r = run_single(N, rho_l, rho_g, k_dc=k_dc)
        all_results.append(r)

        res = r["residuals"]
        status = "PASS" if r["converged"] else "EXPECTED FAIL"
        if r["converged"] and r["res_ratio"] > 0.1:
            status = "WARN (slow)"

        print(f"  {dr:>8} | {r['L_inf_error']:>12.3e} | {res[0]:>12.3e} | "
              f"{res[-1]:>12.3e} | {r['res_ratio']:>8.3f} | {status:>12}")

    # Also test multiple grid resolutions for low density ratios
    print(f"\n  --- Grid convergence for ρ_l/ρ_g = 2, 5 ---\n")
    Ns_conv = [16, 32, 64, 128]
    conv_results = []

    for dr in [2, 5]:
        print(f"  ρ_l/ρ_g = {dr}:")
        print(f"    {'N':>5} | {'L∞ error':>12} | {'order':>6} | {'converged':>10}")
        print("    " + "-" * 45)
        prev_err = None
        for Nc in Ns_conv:
            r = run_single(Nc, float(dr), 1.0, k_dc=k_dc)
            conv_results.append(r)

            order_str = "---"
            if prev_err is not None and r["L_inf_error"] > 1e-16 and prev_err > 1e-16:
                order = np.log(prev_err / r["L_inf_error"]) / np.log(2.0)
                order_str = f"{order:.2f}"

            print(f"    {Nc:>5} | {r['L_inf_error']:>12.3e} | {order_str:>6} | "
                  f"{'yes' if r['converged'] else 'NO':>10}")
            prev_err = r["L_inf_error"]
        print()

    # Save LaTeX table (density sweep)
    with open(OUT / "table_varrho_breakdown.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_8_varrho_breakdown.py\n")
        fp.write("\\begin{tabular}{rcccc}\n\\toprule\n")
        fp.write("$\\rho_l/\\rho_g$ & $L^\\infty$ 誤差 & "
                 "$\\|r_0\\|$ & $\\|r_{\\mathrm{final}}\\|$ & 判定 \\\\\n")
        fp.write("\\midrule\n")
        for r in all_results:
            res = r["residuals"]
            status = "収束" if r["converged"] else "\\textbf{発散}"
            if r["converged"] and r["res_ratio"] > 0.1:
                status = "遅化"
            fp.write(f"{r['rho_ratio']:.0f} & ${r['L_inf_error']:.2e}$ & "
                     f"${res[0]:.2e}$ & ${res[-1]:.2e}$ & {status} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {OUT / 'table_varrho_breakdown.tex'}")

    # Save LaTeX table (grid convergence)
    with open(OUT / "table_varrho_convergence.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_8_varrho_breakdown.py\n")
        fp.write("\\begin{tabular}{rrccc}\n\\toprule\n")
        fp.write("$\\rho_l/\\rho_g$ & $N$ & $L^\\infty$ 誤差 & 次数 & 収束 \\\\\n")
        fp.write("\\midrule\n")
        for i, r in enumerate(conv_results):
            order_str = "---"
            if i > 0 and conv_results[i - 1]["rho_ratio"] == r["rho_ratio"]:
                prev = conv_results[i - 1]
                if prev["L_inf_error"] > 1e-16 and r["L_inf_error"] > 1e-16:
                    order = np.log(prev["L_inf_error"] / r["L_inf_error"]) / np.log(
                        float(r["N"]) / prev["N"])
                    order_str = f"${order:.2f}$"
            conv = "○" if r["converged"] else "×"
            fp.write(f"{r['rho_ratio']:.0f} & {r['N']} & ${r['L_inf_error']:.2e}$ & "
                     f"{order_str} & {conv} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {OUT / 'table_varrho_convergence.tex'}")

    np.savez(OUT / "varrho_breakdown_data.npz",
             sweep_results=all_results, conv_results=conv_results)
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    main()
