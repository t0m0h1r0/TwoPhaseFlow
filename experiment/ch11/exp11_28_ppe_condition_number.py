#!/usr/bin/env python3
"""[11-28] PPE condition number scaling measurement.

Validates: Ch9c -- empirical condition number growth for interface-density PPE.

Test: Assemble FVM Poisson matrix with variable density (interface-type),
      compute condition number for various N and rho_l/rho_g.

Expected: condition number worsens with grid refinement and density contrast.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


# -- Density field -------------------------------------------------------------

def density_field(N, h, rho_l, rho_g):
    """Smoothed circular density interface: rho_l inside, rho_g outside."""
    x = np.linspace(0, 1, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    eps = 1.5 * h
    H = 0.5 * (1 + np.tanh(phi / (2 * eps)))
    rho = rho_l * (1 - H) + rho_g * H
    return rho


# -- FVM Laplacian assembly ----------------------------------------------------

def assemble_fvm_laplacian(N, rho, h, backend):
    """Assemble 2D variable-density FVM Laplacian with Neumann BC + center gauge.

    Operator: nabla . (1/rho nabla p), discretised with harmonic-mean face coeff.
    Matrix is assembled on host (Python lists) then converted to backend sparse.
    """
    n_total = (N + 1) ** 2
    rows, cols, vals = [], [], []

    def idx(i, j):
        return i * (N + 1) + j

    for i in range(N + 1):
        for j in range(N + 1):
            node = idx(i, j)
            diag = 0.0

            # East face (i+1/2, j)
            if i < N:
                coeff = 2.0 / (rho[i, j] + rho[i + 1, j]) / h**2
                rows.append(node); cols.append(idx(i + 1, j)); vals.append(coeff)
                diag -= coeff

            # West face (i-1/2, j)
            if i > 0:
                coeff = 2.0 / (rho[i, j] + rho[i - 1, j]) / h**2
                rows.append(node); cols.append(idx(i - 1, j)); vals.append(coeff)
                diag -= coeff

            # North face (i, j+1/2)
            if j < N:
                coeff = 2.0 / (rho[i, j] + rho[i, j + 1]) / h**2
                rows.append(node); cols.append(idx(i, j + 1)); vals.append(coeff)
                diag -= coeff

            # South face (i, j-1/2)
            if j > 0:
                coeff = 2.0 / (rho[i, j] + rho[i, j - 1]) / h**2
                rows.append(node); cols.append(idx(i, j - 1)); vals.append(coeff)
                diag -= coeff

            rows.append(node); cols.append(node); vals.append(diag)

    import scipy.sparse as _sp_sparse  # always CPU for assembly
    L_cpu = _sp_sparse.csr_matrix((vals, (rows, cols)), shape=(n_total, n_total))

    # Gauge fix: pin center node (on CPU lil for indexed assignment)
    center = idx(N // 2, N // 2)
    L_lil = L_cpu.tolil()
    L_lil[center, :] = 0
    L_lil[center, center] = 1.0
    L_cpu = L_lil.tocsr()

    # Convert to backend sparse (no-op on CPU; moves to device on GPU)
    return backend.sparse.csr_matrix(L_cpu)


# -- Benchmark -----------------------------------------------------------------

def run_benchmark():
    backend = Backend()
    Ns = [8, 16, 32, 64]
    rho_ratios = [1, 10, 100, 1000]
    results = []

    print(f"\n{'='*72}")
    print(f"  PPE Condition Number: kappa vs (N, rho_l/rho_g)")
    print(f"{'='*72}")
    header = f"  {'N':>4}"
    for rr in rho_ratios:
        header += f" {'rho=' + str(rr):>14}"
    print(header)
    print("  " + "-" * (4 + 15 * len(rho_ratios)))

    for N in Ns:
        h = 1.0 / N
        row_data = {"N": N, "h": h}
        line = f"  {N:>4}"

        for rr in rho_ratios:
            rho_l, rho_g = float(rr), 1.0
            rho = density_field(N, h, rho_l, rho_g)
            L = assemble_fvm_laplacian(N, rho, h, backend)

            # Condition number (dense for small matrices); always on host
            L_dense = np.asarray(backend.to_host(L.toarray()))
            cond = float(np.linalg.cond(L_dense))
            row_data[f"cond_{rr}"] = cond
            line += f"  {cond:>12.2e}"

        results.append(row_data)
        print(line)

    # Compute slopes (kappa vs N at fixed rho)
    print(f"\n  Slopes (log(kappa)/log(N/N_prev)):")
    for rr in rho_ratios:
        slopes = []
        for i in range(1, len(results)):
            k0 = results[i - 1][f"cond_{rr}"]
            k1 = results[i][f"cond_{rr}"]
            N0, N1 = results[i - 1]["N"], results[i]["N"]
            if k0 > 0 and k1 > 0:
                slope = np.log(k1 / k0) / np.log(N1 / N0)
                slopes.append(slope)
        print(f"    rho={rr}: {slopes}")

    return results


# -- Plot ----------------------------------------------------------------------

def plot_all(results):
    import matplotlib.pyplot as plt

    rho_ratios = [1, 10, 100, 1000]
    Ns = [r["N"] for r in results]
    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # (a) kappa vs N for each rho_ratio
    ax = axes[0]
    for idx, rr in enumerate(rho_ratios):
        conds = [r[f"cond_{rr}"] for r in results]
        ax.loglog(Ns, conds, f"{MARKERS[idx]}-", color=COLORS[idx],
                  label=rf"$\rho_l/\rho_g = {rr}$")
    # N^2 reference
    N_ref = np.array([Ns[0], Ns[-1]], dtype=float)
    c_ref = results[0][f"cond_1"]
    ax.loglog(N_ref, c_ref * (N_ref / N_ref[0])**2,
              ":", color="gray", alpha=0.5, label=r"$O(N^2)$")
    ax.set_xlabel("$N$"); ax.set_ylabel(r"$\kappa$")
    ax.set_title(r"(a) $\kappa$ vs $N$")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    # (b) kappa vs rho_ratio for each N
    ax = axes[1]
    rr_arr = np.array(rho_ratios, dtype=float)
    for idx, r in enumerate(results):
        conds = [r[f"cond_{rr}"] for rr in rho_ratios]
        ax.loglog(rr_arr, conds, f"{MARKERS[idx]}-", color=COLORS[idx],
                  label=f"$N = {r['N']}$")
    # Linear reference
    ax.loglog(rr_arr, results[-1][f"cond_1"] * rr_arr / rr_arr[0],
              ":", color="gray", alpha=0.5, label=r"$O(\rho_l/\rho_g)$")
    ax.set_xlabel(r"$\rho_l / \rho_g$"); ax.set_ylabel(r"$\kappa$")
    ax.set_title(r"(b) $\kappa$ vs density ratio")
    ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "ppe_condition_number")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser("[11-28] PPE Condition Number").parse_args()

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        plot_all(data["results"])
        return

    results = run_benchmark()
    save_results(OUT / "data.npz", {"results": results})
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
