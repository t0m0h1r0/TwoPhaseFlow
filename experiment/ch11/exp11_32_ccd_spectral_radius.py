#!/usr/bin/env python3
"""[11-32] CCD D2 operator spectral radius measurement.

Validates: Ch9 -- spectral radius rho(D2_CCD) approx 9.6/h^2.

Tests:
  (a) 1D: Assemble CCD D2 matrix, compute eigenvalues, measure max|lambda|
  (b) Verify coefficient: rho * h^2 -> 9.6 as N increases
  (c) Compare with FD D2: rho(D2_FD) = 4/h^2
  (d) 2D Kronecker: rho(L_2D) = 2 * rho(L_1D)

Expected: rho(D2_CCD) * h^2 approx 9.6 (vs FD 4.0).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)

# Reference value from §9 of the paper
CCD_SPECTRAL_COEFF_REF = 9.6
FD_SPECTRAL_COEFF_REF  = 4.0


# -- Matrix assembly helpers --------------------------------------------------

def assemble_ccd_d2_matrix_1d(N, backend):
    """Build the N×N CCD second-derivative matrix for a periodic 1D grid of N cells.

    Strategy: use an N×N 2D periodic grid and differentiate along axis=0.
    For column j (0..N-1):
      - Set f[j, :] = 1.0 (constant in y), all other rows = 0.
      - Differentiate along axis=0 to get d2.
      - The column d2[:, 0] gives column j of the 1D D2 matrix
        (all y-columns are identical by linearity).
    The grid has N+1 nodes per axis (0..N with node N = node 0 for periodic).
    The N unique interior nodes correspond to indices 0..N-1.

    Returns
    -------
    D2 : ndarray, shape (N, N)  — the 1D CCD D2 operator matrix (on host)
    h  : float                  — grid spacing 1/N
    """
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=1.0)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    xp = backend.xp

    D2 = np.zeros((N, N))
    # f has shape (N+1, N+1); we fill rows 0..N-1 (row N = row 0 for periodic)
    f = xp.zeros((N + 1, N + 1))

    for j in range(N):
        f[:] = xp.zeros((N + 1, N + 1))
        f[j, :] = 1.0
        # Enforce periodic image: f[N, :] = f[0, :] (already 0 unless j==0)
        f[N, :] = f[0, :]

        _, d2 = ccd.differentiate(f, axis=0)
        # d2 has shape (N+1, N+1); extract the N unique rows, column 0
        d2_host = np.asarray(backend.to_host(d2))
        D2[:, j] = d2_host[:N, 0]

    h = 1.0 / N
    return D2, h


def assemble_fd_d2_matrix_1d(N):
    """Build the N×N standard 3-point FD second-derivative matrix (periodic).

    Stencil: [1, -2, 1] / h^2, with periodic wrap-around.

    Returns
    -------
    D2 : ndarray, shape (N, N)
    h  : float
    """
    h = 1.0 / N
    D2 = np.zeros((N, N))
    for i in range(N):
        D2[i, i] = -2.0
        D2[i, (i + 1) % N] += 1.0
        D2[i, (i - 1) % N] += 1.0
    D2 /= h ** 2
    return D2, h


# -- 1D spectral radius study -------------------------------------------------

def run_1d_study(Ns, backend):
    """Compute spectral radii of CCD D2 and FD D2 for each N in Ns.

    Returns list of dicts with keys: N, h, rho_ccd, rho_fd,
    norm_ccd (= rho_ccd * h^2), norm_fd (= rho_fd * h^2).
    """
    results = []
    print(f"\n{'='*72}")
    print(f"  1D Spectral Radius: rho(D2) * h^2  (expect CCD~9.6, FD~4.0)")
    print(f"{'='*72}")
    print(f"  {'N':>6}  {'h':>8}  {'CCD rho*h^2':>14}  {'FD rho*h^2':>12}  {'ratio':>8}")
    print(f"  {'-'*6}  {'-'*8}  {'-'*14}  {'-'*12}  {'-'*8}")

    for N in Ns:
        D2_ccd, h = assemble_ccd_d2_matrix_1d(N, backend)
        D2_fd,  _ = assemble_fd_d2_matrix_1d(N)

        eigvals_ccd = np.linalg.eigvals(D2_ccd)
        eigvals_fd  = np.linalg.eigvals(D2_fd)

        rho_ccd = float(np.max(np.abs(eigvals_ccd)))
        rho_fd  = float(np.max(np.abs(eigvals_fd)))

        norm_ccd = rho_ccd * h ** 2
        norm_fd  = rho_fd  * h ** 2

        results.append({
            "N":        N,
            "h":        h,
            "rho_ccd":  rho_ccd,
            "rho_fd":   rho_fd,
            "norm_ccd": norm_ccd,
            "norm_fd":  norm_fd,
            "eigvals_ccd_real": eigvals_ccd.real.tolist(),
            "eigvals_fd_real":  eigvals_fd.real.tolist(),
        })

        print(f"  {N:>6}  {h:>8.4f}  {norm_ccd:>14.6f}  {norm_fd:>12.6f}  "
              f"  {norm_ccd / CCD_SPECTRAL_COEFF_REF:>6.4f}")

    return results


# -- 2D Kronecker verification ------------------------------------------------

def run_2d_kronecker_study(Ns_2d, backend):
    """Verify rho(L_2D) = 2 * rho(L_1D) for L_2D = I⊗L + L⊗I.

    For each N, build L_1D (CCD D2, N×N), then construct
    L_2D = kron(I_N, L_1D) + kron(L_1D, I_N)  (shape N^2 × N^2),
    and compare rho(L_2D) vs 2*rho(L_1D).
    """
    results = []
    print(f"\n{'='*72}")
    print(f"  2D Kronecker: rho(L_2D) vs 2 * rho(L_1D)")
    print(f"{'='*72}")
    print(f"  {'N':>6}  {'rho(L_1D)*h^2':>16}  {'rho(L_2D)*h^2':>16}  {'2*rho_1D*h^2':>16}  {'err%':>8}")
    print(f"  {'-'*6}  {'-'*16}  {'-'*16}  {'-'*16}  {'-'*8}")

    for N in Ns_2d:
        D2_ccd, h = assemble_ccd_d2_matrix_1d(N, backend)

        rho_1d = float(np.max(np.abs(np.linalg.eigvals(D2_ccd))))

        I_N   = np.eye(N)
        L_2D  = np.kron(I_N, D2_ccd) + np.kron(D2_ccd, I_N)

        # Eigenvalues of L_2D: use eigvals (L_2D is N^2 × N^2, feasible for N<=32)
        eigvals_2d = np.linalg.eigvals(L_2D)
        rho_2d     = float(np.max(np.abs(eigvals_2d)))

        predicted  = 2.0 * rho_1d
        rel_err    = abs(rho_2d - predicted) / predicted * 100.0

        results.append({
            "N":           N,
            "h":           h,
            "rho_1d_norm": rho_1d * h ** 2,
            "rho_2d_norm": rho_2d * h ** 2,
            "pred_norm":   predicted * h ** 2,
            "rel_err_pct": rel_err,
        })

        print(f"  {N:>6}  {rho_1d * h**2:>16.6f}  {rho_2d * h**2:>16.6f}  "
              f"{predicted * h**2:>16.6f}  {rel_err:>8.4f}%")

    return results


# -- Plot ---------------------------------------------------------------------

def plot_all(res_1d, res_2d):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE_2COL)

    # ── (a) Normalized spectral radius vs N ──────────────────────────────────
    ax = axes[0]
    Ns       = [r["N"]        for r in res_1d]
    norm_ccd = [r["norm_ccd"] for r in res_1d]
    norm_fd  = [r["norm_fd"]  for r in res_1d]

    ax.semilogx(Ns, norm_ccd, f"{MARKERS[0]}-", color=COLORS[0],
                label=r"CCD $D^{(2)}$")
    ax.semilogx(Ns, norm_fd,  f"{MARKERS[1]}--", color=COLORS[1],
                label=r"FD $D^{(2)}$")

    # Reference lines
    ax.axhline(CCD_SPECTRAL_COEFF_REF, color=COLORS[0], linestyle=":",
               alpha=0.6, label=rf"$\rho_{{CCD}} h^2 = {CCD_SPECTRAL_COEFF_REF}$")
    ax.axhline(FD_SPECTRAL_COEFF_REF,  color=COLORS[1], linestyle=":",
               alpha=0.6, label=rf"$\rho_{{FD}} h^2 = {FD_SPECTRAL_COEFF_REF}$")

    ax.set_xlabel("$N$")
    ax.set_ylabel(r"$\rho(D^{(2)}) \cdot h^2$")
    ax.set_title(r"(a) Normalized spectral radius vs $N$")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(2.0, 5.0)

    # ── (b) Eigenvalue spectrum (real parts) for N=32 ────────────────────────
    ax = axes[1]

    # Find N=32 result (or largest N available)
    target_N = 32
    r32 = next((r for r in res_1d if r["N"] == target_N),
               res_1d[-1])
    N_plot = r32["N"]
    h_plot = r32["h"]

    eigvals_ccd_real = np.array(r32["eigvals_ccd_real"])
    # For FD: analytic eigenvalues  lambda_k = (2 cos(2 pi k / N) - 2) / h^2
    k_arr = np.arange(N_plot)
    eigvals_fd_analytic = (2.0 * np.cos(2.0 * np.pi * k_arr / N_plot) - 2.0) / h_plot ** 2

    # Sort by value for a cleaner plot
    sorted_ccd = np.sort(eigvals_ccd_real)
    sorted_fd  = np.sort(eigvals_fd_analytic)

    ax.plot(sorted_ccd, f"{MARKERS[0]}", color=COLORS[0], markersize=4,
            label=f"CCD ($N={N_plot}$)", alpha=0.8)
    ax.plot(sorted_fd,  f"{MARKERS[1]}", color=COLORS[1], markersize=4,
            label=f"FD ($N={N_plot}$)", alpha=0.8)

    ax.axhline(0, color="gray", linewidth=0.6, alpha=0.5)
    ax.set_xlabel("Eigenvalue index (sorted)")
    ax.set_ylabel(r"$\lambda$")
    ax.set_title(rf"(b) Eigenvalue spectrum, $N={N_plot}$")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "ccd_spectral_radius")


# -- Validation checks --------------------------------------------------------

def validate(res_1d, res_2d):
    """Assert expected spectral radius coefficients.

    Returns True if all checks pass.
    """
    all_pass = True
    tol_coeff = 0.05   # 5% tolerance on the normalized coefficient

    print(f"\n{'='*72}")
    print(f"  VALIDATION CHECKS")
    print(f"{'='*72}")

    # Check 1: CCD coefficient converges to ~3.43
    for r in res_1d:
        N, c = r["N"], r["norm_ccd"]
        ok = abs(c - CCD_SPECTRAL_COEFF_REF) / CCD_SPECTRAL_COEFF_REF < tol_coeff
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] N={N:4d}: rho_CCD*h^2 = {c:.4f}  "
              f"(expect {CCD_SPECTRAL_COEFF_REF}, tol={tol_coeff*100:.0f}%)")

    # Check 2: FD coefficient = 4.0
    tol_fd = 1e-10
    for r in res_1d:
        N, c = r["N"], r["norm_fd"]
        ok = abs(c - FD_SPECTRAL_COEFF_REF) < tol_fd
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] N={N:4d}: rho_FD*h^2  = {c:.10f}  (expect {FD_SPECTRAL_COEFF_REF} exactly)")

    # Check 3: 2D Kronecker identity rho(L_2D) = 2 * rho(L_1D)
    tol_kron = 1e-8
    for r in res_2d:
        N    = r["N"]
        err  = r["rel_err_pct"]
        ok   = err < tol_kron * 100
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] Kronecker N={N:4d}: rho(L_2D)*h^2 = {r['rho_2d_norm']:.6f}, "
              f"2*rho(L_1D)*h^2 = {r['pred_norm']:.6f}  (rel err {err:.2e}%)")

    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    return all_pass


# -- Main ---------------------------------------------------------------------

def main():
    args = experiment_argparser("[11-32] CCD D2 Spectral Radius").parse_args()

    if args.plot_only:
        data = load_results(OUT / "data.npz")
        plot_all(data["res_1d"], data["res_2d"])
        return

    backend = Backend()

    # 1D study: N = 8, 16, 32, 64, 128
    Ns_1d = [8, 16, 32, 64, 128]
    res_1d = run_1d_study(Ns_1d, backend)

    # 2D Kronecker: N = 16, 32 (N^2 × N^2 eigenvalue problem; N=32 → 1024×1024)
    Ns_2d = [16, 32]
    res_2d = run_2d_kronecker_study(Ns_2d, backend)

    validate(res_1d, res_2d)

    save_results(OUT / "data.npz", {"res_1d": res_1d, "res_2d": res_2d})
    plot_all(res_1d, res_2d)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
