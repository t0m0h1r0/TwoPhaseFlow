#!/usr/bin/env python3
"""【10-8】Defect correction iteration count vs spatial accuracy.

Paper ref: §8.3 (sec:defect_correction_main), §11.3.7 (sec:dc_iteration_accuracy)

Tests:
  2D Poisson ∇²p = f on [0,1]², Dirichlet BC, p* = sin(πx)sin(πy).
  Run EXACT defect correction with FIXED iteration counts k = 1, 2, 3, 5, 10.
  L_H = CCD operator (O(h⁶)), L_L = FD 5-point Laplacian (O(h²)).
  L_L is solved exactly via sparse direct solve (not factored sweep).

Expected:
  k=1 → O(h²) (L_L dominates)
  k=2 → O(h⁴) (intermediate)
  k≥3 → O(h⁶) (L_H accuracy fully expressed)
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

OUT = pathlib.Path(__file__).resolve().parent.parent.parent / "results" / "ch10_dc_iteration"
OUT.mkdir(parents=True, exist_ok=True)

# ── Analytical solution ──────────────────────────────────────────────────────

def analytical_solution(X, Y):
    """p* = sin(πx)sin(πy), f = -2π² sin(πx)sin(πy). Dirichlet BC."""
    p = np.sin(np.pi * X) * np.sin(np.pi * Y)
    lap_p = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
    return p, lap_p


# ── L_H: CCD Laplacian evaluation (O(h⁶)) ──────────────────────────────────

def eval_LH(p, ccd, backend):
    """Evaluate L_H p = ∇²p using CCD (O(h⁶)), constant density ρ=1."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        _, d2p = ccd.differentiate(p_dev, ax)
        Lp += d2p
    return np.asarray(backend.to_host(Lp))


# ── L_L: FD 5-point Laplacian matrix (O(h²)) ───────────────────────────────

def build_fd_laplacian_dirichlet(Nx, Ny, hx, hy):
    """Build 2D 5-point FD Laplacian with Dirichlet BC.

    Grid: (Nx+1) x (Ny+1) nodes, indices (0..Nx, 0..Ny).
    Boundary nodes: fixed to 0 (identity rows).
    Interior nodes: standard 5-point stencil.
    """
    nx, ny = Nx + 1, Ny + 1
    n = nx * ny

    def idx(i, j):
        return i * ny + j

    rows, cols, vals = [], [], []

    for i in range(nx):
        for j in range(ny):
            k = idx(i, j)
            if i == 0 or i == Nx or j == 0 or j == Ny:
                # Dirichlet BC: identity row
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                # Interior: (p[i-1,j] + p[i+1,j] - 2p[i,j]) / hx²
                #         + (p[i,j-1] + p[i,j+1] - 2p[i,j]) / hy²
                rows.append(k); cols.append(idx(i-1, j)); vals.append(1.0 / hx**2)
                rows.append(k); cols.append(idx(i+1, j)); vals.append(1.0 / hx**2)
                rows.append(k); cols.append(idx(i, j-1)); vals.append(1.0 / hy**2)
                rows.append(k); cols.append(idx(i, j+1)); vals.append(1.0 / hy**2)
                rows.append(k); cols.append(k);            vals.append(-2.0/hx**2 - 2.0/hy**2)

    return sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))


def solve_LL(rhs_2d, L_L_mat):
    """Solve L_L δp = rhs exactly via sparse direct solve."""
    shape = rhs_2d.shape
    rhs_flat = rhs_2d.ravel()
    dp_flat = spsolve(L_L_mat, rhs_flat)
    return dp_flat.reshape(shape)


# ── Defect Correction (exact L_L solve) ──────────────────────────────────────

def defect_correction_fixed_k(rhs, ccd, backend, L_L_mat, k_max):
    """Run exact defect correction for k_max iterations.

    Algorithm (eq:dc_three_step):
      d^(k) = b - L_H p^(k)          [CCD residual]
      L_L δp^(k+1) = d^(k)           [exact FD solve]
      p^(k+1) = p^(k) + δp^(k+1)    [update, ω=1]
    """
    p = np.zeros_like(rhs)
    residuals = []

    for k in range(k_max):
        # Step 1: defect d = b - L_H p
        Lp = eval_LH(p, ccd, backend)
        d = rhs - Lp
        # Zero out boundary (Dirichlet: rhs on boundary is 0)
        d[0, :] = 0.0; d[-1, :] = 0.0
        d[:, 0] = 0.0; d[:, -1] = 0.0
        residuals.append(float(np.sqrt(np.mean(d**2))))

        # Step 2: solve L_L δp = d
        dp = solve_LL(d, L_L_mat)

        # Step 3: update p = p + δp
        p = p + dp
        # Enforce Dirichlet BC
        p[0, :] = 0.0; p[-1, :] = 0.0
        p[:, 0] = 0.0; p[:, -1] = 0.0

    return p, residuals


# ── Main experiment ──────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend(use_gpu=False)

    Ns = [8, 16, 32, 64, 128]
    Ks = [1, 2, 3, 5, 10]

    errors = {k: [] for k in Ks}

    print(f"\n{'N':>5}", end="")
    for k in Ks:
        print(f" | {'k='+str(k):>12}", end="")
    print("\n" + "-" * (5 + 15 * len(Ks)))

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N

        X, Y = grid.meshgrid()
        p_exact, rhs = analytical_solution(X, Y)

        # Enforce Dirichlet BC on rhs
        rhs[0, :] = 0.0; rhs[-1, :] = 0.0
        rhs[:, 0] = 0.0; rhs[:, -1] = 0.0

        # Build FD Laplacian matrix (L_L) with Dirichlet BC
        L_L_mat = build_fd_laplacian_dirichlet(N, N, h, h)

        print(f"{N:>5}", end="")

        for k in Ks:
            p_dc, res = defect_correction_fixed_k(rhs, ccd, backend, L_L_mat, k)
            err_Li = float(np.max(np.abs(p_dc - p_exact)))
            errors[k].append({"N": N, "h": h, "Li": err_Li})
            print(f" | {err_Li:>12.3e}", end="")

        print()

    # Compute convergence slopes
    slopes = {k: [] for k in Ks}
    for k in Ks:
        slopes[k].append(float("nan"))
        for i in range(1, len(errors[k])):
            r0, r1 = errors[k][i - 1], errors[k][i]
            if r0["Li"] > 0 and r1["Li"] > 0:
                s = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])
                slopes[k].append(s)
            else:
                slopes[k].append(float("nan"))

    print("\nConvergence orders:")
    print(f"{'N':>5}", end="")
    for k in Ks:
        print(f" | {'k='+str(k):>12}", end="")
    print()
    for i, N in enumerate(Ns):
        print(f"{N:>5}", end="")
        for k in Ks:
            s = slopes[k][i]
            print(f" | {s:>12.2f}" if not np.isnan(s) else f" | {'---':>12}", end="")
        print()

    return errors, slopes


def save_latex_table(errors, slopes, Ns, Ks):
    with open(OUT / "table_dc_iteration_accuracy.tex", "w") as fp:
        fp.write("% Auto-generated by exp10_8_dc_iteration_accuracy.py\n")
        fp.write("\\begin{tabular}{cc" + "c" * len(Ks) + "}\n")
        fp.write("\\toprule\n")
        fp.write("$N$ & $h$")
        for k in Ks:
            fp.write(f" & $k={k}$")
        fp.write(" \\\\\n\\midrule\n")

        for i, N in enumerate(Ns):
            fp.write(f"${N}$ & $1/{N}$")
            for k in Ks:
                e = errors[k][i]["Li"]
                fp.write(f" & ${e:.2e}$")
            fp.write(" \\\\\n")

        fp.write("\\midrule\n")
        fp.write("\\multicolumn{2}{c}{収束次数 $p$}")
        for k in Ks:
            valid = [s for s in slopes[k] if not np.isnan(s)]
            if valid:
                avg = np.mean(valid[-2:])
                fp.write(f" & $\\approx {avg:.1f}$")
            else:
                fp.write(" & ---")
        fp.write(" \\\\\n\\bottomrule\n\\end{tabular}\n")

    print(f"\n  Saved: {OUT / 'table_dc_iteration_accuracy.tex'}")


def save_plot(errors, Ns, Ks):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(7, 5))
    markers = ["o", "s", "D", "^", "v"]
    for ki, k in enumerate(Ks):
        hs = [e["h"] for e in errors[k]]
        es = [e["Li"] for e in errors[k]]
        ax.loglog(hs, es, f"{markers[ki]}-", label=f"$k={k}$", markersize=6)

    h_ref = np.array([1.0 / Ns[0], 1.0 / Ns[-1]])
    e_top = errors[1][0]["Li"]
    for order, ls, label in [(2, ":", "$O(h^2)$"), (4, "-.", "$O(h^4)$"),
                              (6, "--", "$O(h^6)$")]:
        ax.loglog(h_ref, e_top * (h_ref / h_ref[0])**order, ls,
                  color="gray", alpha=0.5, label=label)

    ax.set_xlabel("$h$")
    ax.set_ylabel("$L^\\infty$ error")
    ax.set_title("Defect correction: iteration count $k$ vs spatial accuracy")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "dc_iteration_accuracy.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'dc_iteration_accuracy.png'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-8】Defect Correction: Iteration Count vs Spatial Accuracy")
    print("=" * 80)

    Ns = [8, 16, 32, 64, 128]
    Ks = [1, 2, 3, 5, 10]

    errors, slopes = run_experiment()
    save_latex_table(errors, slopes, Ns, Ks)
    save_plot(errors, Ns, Ks)

    np.savez(OUT / "dc_iteration_data.npz",
             errors=errors, slopes=slopes, Ns=Ns, Ks=Ks)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
