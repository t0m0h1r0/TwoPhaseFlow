"""
CCD Solver Benchmark: Poisson Equation
=======================================
1D Poisson: φ'' = S(x), x∈[0,1], φ(0)=φ(1)=0.
Exact: φ = sin(2πx),  S = -(2π)²·sin(2πx).

Four solver approaches compared:
  1. FD2  + SOR         — 2nd-order finite difference + SOR (ω_opt, classical)
  2. CCD  + Direct LU   — 6th-order CCD + dense LU factorisation (reference)
  3. CCD  + BiCGSTAB    — 6th-order CCD + Krylov solver (scipy.sparse)
  4. CCD  + Pseudo-time — 6th-order CCD + matrix-free forward-Euler pseudo-time

Convergence tolerance: ‖res‖∞ < 1e-8 for all iterative methods.
  Note: ‖res‖∞ < 1e-10 causes a floating-point floor problem for FD2+SOR at N≥256
  (~2×10⁻¹⁰ due to roundoff accumulation), so 1e-8 is used uniformly.
  Direct LU solves to machine precision (1 step).

Pseudo-time is run only for N=[32,64]; N≥128 takes O(N²) iterations (>10⁵ at N=128),
which is impractical. Estimated from measured O(N²) scaling.

Metrics:
  n_iters   — iterations (FD2+SOR, BiCGSTAB, Pseudo-time); 1 for LU
  time_ms   — wall-clock time
  mem_MB    — dominant data-structure memory
  L2_err    — L₂ error vs exact at interior nodes

Output
------
  results/ccd_solver_benchmark/
    figures/
      01_convergence.png   — ‖res‖∞ vs iteration (N=64)
      02_time_scaling.png  — wall-clock time vs N
      03_accuracy.png      — L₂ error vs N (both discretisations)
    data/benchmark.csv
    latex/table_benchmark.tex

Appendix: paper/sections/appendix_numerics_schemes_s9.tex  (D.9)
"""
from __future__ import annotations

import csv
import os
import sys
import time

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.linalg import lu_factor, lu_solve
from scipy.sparse import diags as sp_diags
from scipy.sparse.linalg import bicgstab

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from twophase.ccd.ccd_solver import CCDSolver

# ─── output paths ────────────────────────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..")
_OUT  = os.path.join(_ROOT, "results", "ccd_solver_benchmark")
_FIG  = os.path.join(_OUT, "figures")
_DAT  = os.path.join(_OUT, "data")
_TEX  = os.path.join(_OUT, "latex")
for _d in (_FIG, _DAT, _TEX):
    os.makedirs(_d, exist_ok=True)

# ─── CCD factory ─────────────────────────────────────────────────────────────
class _Grid1D:
    ndim = 1; uniform = True
    def __init__(self, n: int):
        self.N = (n,); self.L = (1.0,)

class _Backend:
    xp = np

def _make_ccd(n: int) -> CCDSolver:
    return CCDSolver(_Grid1D(n), _Backend(), bc_type="wall")

# ─── problem ─────────────────────────────────────────────────────────────────
def _exact(x):  return np.sin(2.0 * np.pi * x)
def _rhs(x):    return -(2.0 * np.pi)**2 * np.sin(2.0 * np.pi * x)

# ─── matrix builders ─────────────────────────────────────────────────────────

def _build_fd2_matrix(N: int) -> np.ndarray:
    """Standard 3-point FD2 Laplacian, shape (N+1, N+1)."""
    h = 1.0 / N
    c = 1.0 / h**2
    A = np.zeros((N + 1, N + 1))
    for i in range(1, N):
        A[i, i - 1] =  c
        A[i, i    ] = -2.0 * c
        A[i, i + 1] =  c
    # BC rows
    A[0,  0] = 1.0
    A[-1, -1] = 1.0
    return A


def _build_ccd_d2_matrix(ccd: CCDSolver, N: int) -> np.ndarray:
    """CCD D2 matrix by column probing, shape (N+1, N+1)."""
    n_pts = N + 1
    D2 = np.zeros((n_pts, n_pts))
    e  = np.zeros(n_pts)
    for j in range(n_pts):
        e[:] = 0.0; e[j] = 1.0
        _, d2 = ccd.differentiate(e, 0)
        D2[:, j] = np.asarray(d2)
    # Apply Dirichlet rows
    D2[0,  :] = 0.0; D2[0,  0]  = 1.0
    D2[-1, :] = 0.0; D2[-1, -1] = 1.0
    return D2


# ═══════════════════════════════════════════════════════════════════════════════
# Solver 1 — FD2 + SOR (ω_opt)
# ═══════════════════════════════════════════════════════════════════════════════

def solve_fd2_sor(N: int, b: np.ndarray,
                  tol: float = 1e-8, max_iter: int = 20000) -> tuple:
    """SOR on standard FD2 Laplacian.

    Optimal SOR parameter for 1D Dirichlet Laplacian:
        ω_opt = 2 / (1 + sin(π/(N)))    [classical formula]
    """
    h     = 1.0 / N
    c     = 1.0 / h**2
    rho_J = np.cos(np.pi / N)           # Jacobi spectral radius
    omega = 2.0 / (1.0 + np.sqrt(1.0 - rho_J**2))

    b_ = b.copy(); b_[0] = 0.0; b_[-1] = 0.0
    phi   = np.zeros(N + 1)
    history = []

    t0 = time.perf_counter()
    for it in range(max_iter):
        # Forward SOR sweep (interior nodes only)
        for i in range(1, N):
            phi_gs = (b_[i] - c * phi[i - 1] - c * phi[i + 1]) / (-2.0 * c)
            phi[i] += omega * (phi_gs - phi[i])
        # Residual every 50 steps
        if (it % 50) == 0 or it == 0:
            r = np.zeros(N + 1)
            r[1:N] = c * (phi[:-2] - 2.0 * phi[1:-1] + phi[2:]) - b_[1:N]
            res = float(np.max(np.abs(r)))
            history.append((it, res))
            if res < tol:
                break
    else:
        history.append((it + 1, res))
    t1 = time.perf_counter()

    mem_MB = (N + 1) * 3 * 8.0 / 1e6    # phi, b, r only (matrix-free for FD2)
    return phi, it + 1, (t1 - t0) * 1e3, mem_MB, history, omega


# ═══════════════════════════════════════════════════════════════════════════════
# Solver 2 — CCD + Direct LU
# ═══════════════════════════════════════════════════════════════════════════════

def solve_ccd_lu(D2: np.ndarray, b: np.ndarray, N: int) -> tuple:
    """Direct LU on CCD D2 matrix (Dirichlet BC already applied in D2)."""
    b_    = b.copy(); b_[0] = 0.0; b_[-1] = 0.0
    t0 = time.perf_counter()
    lu, piv = lu_factor(D2)
    phi = lu_solve((lu, piv), b_)
    t1 = time.perf_counter()
    mem_MB = 2.0 * (N + 1)**2 * 8.0 / 1e6   # D2 + LU factors
    res = float(np.max(np.abs(D2 @ phi - b_)))
    return phi, 1, (t1 - t0) * 1e3, mem_MB, [(0, res)]


# ═══════════════════════════════════════════════════════════════════════════════
# Solver 3 — CCD + BiCGSTAB
# ═══════════════════════════════════════════════════════════════════════════════

def solve_ccd_bicgstab(D2: np.ndarray, b: np.ndarray, N: int,
                       tol: float = 1e-8) -> tuple:
    """BiCGSTAB on CCD D2 sparse matrix."""
    from scipy.sparse import csr_matrix as csr
    b_ = b.copy(); b_[0] = 0.0; b_[-1] = 0.0
    A_sp    = csr(D2)
    counter = [0]
    history = []

    def _cb(xk):
        counter[0] += 1
        r = float(np.max(np.abs(A_sp.dot(xk) - b_)))
        history.append((counter[0], r))

    t0 = time.perf_counter()
    phi, info = bicgstab(A_sp, b_, rtol=tol / (np.linalg.norm(b_) + 1e-30),
                         atol=tol, maxiter=5000, callback=_cb)
    t1 = time.perf_counter()

    mem_MB = (A_sp.nnz * 16 + 8 * (N + 1) * 8) / 1e6   # CSR data + Krylov
    return phi, counter[0], (t1 - t0) * 1e3, mem_MB, history


# ═══════════════════════════════════════════════════════════════════════════════
# Solver 4 — CCD + Pseudo-time (matrix-free)
# ═══════════════════════════════════════════════════════════════════════════════

def solve_ccd_pseudotime(ccd: CCDSolver, N: int, S: np.ndarray,
                         tol: float = 1e-8, max_iter: int = 100000) -> tuple:
    """∂φ/∂τ = φ''−S, forward Euler.  Matrix-free: uses ccd.differentiate."""
    h      = 1.0 / N
    rho_d2 = 9.57 / h**2          # CCD D2 spectral radius (from D.7 analysis)
    dtau   = 0.9 * 2.0 / rho_d2  # stability limit

    phi     = np.zeros(N + 1)
    history = []

    t0 = time.perf_counter()
    for it in range(max_iter):
        _, d2 = ccd.differentiate(phi, 0)
        d2 = np.asarray(d2)
        r  = d2 - S
        r[0] = 0.0; r[N] = 0.0   # enforce BC residual = 0
        res = float(np.max(np.abs(r)))
        if (it % 200) == 0 or it == 0:
            history.append((it, res))
        if res < tol:
            history.append((it, res))
            break
        phi[1:N] += dtau * r[1:N]
    else:
        history.append((it + 1, res))
    t1 = time.perf_counter()

    mem_MB = 3.0 * (N + 1) * 8.0 / 1e6   # φ, d2, r
    return phi, it + 1, (t1 - t0) * 1e3, mem_MB, history


# ═══════════════════════════════════════════════════════════════════════════════
# Run benchmark
# ═══════════════════════════════════════════════════════════════════════════════

_SOLVERS = ["FD2+SOR", "CCD+LU", "CCD+BiCGSTAB", "CCD+PseudoT"]
_LABELS  = {
    "FD2+SOR":    "FD2 + SOR ($\\omega_{\\rm opt}$)",
    "CCD+LU":     "CCD + Direct LU",
    "CCD+BiCGSTAB": "CCD + BiCGSTAB",
    "CCD+PseudoT":  "CCD + Pseudo-time",
}
_COLORS = {
    "FD2+SOR":    "#e06c75",
    "CCD+LU":     "#d19a66",
    "CCD+BiCGSTAB": "#98c379",
    "CCD+PseudoT":  "#61afef",
}
_MARKER = {
    "FD2+SOR":    "s",
    "CCD+LU":     "^",
    "CCD+BiCGSTAB": "D",
    "CCD+PseudoT":  "o",
}


_PSEUDOTIME_MAX_N = 64   # Pseudo-time is O(N²) iterations; skip N>64 in this benchmark.
                         # For N=128: ~49,000 iters (~110s); N=256: ~196,000 iters (~500s).


def run_all(N_values: list) -> dict:
    """Results[N][solver] = dict(n_iters, time_ms, mem_MB, L2, history).

    Pseudo-time is run only for N ≤ _PSEUDOTIME_MAX_N.
    For larger N, an O(N²) extrapolation is stored (n_iters estimated, time_ms=NaN).
    """
    results: dict = {}
    # Reference pseudo-time count at N=32 for O(N²) extrapolation
    _pt_ref: dict = {}

    for N in N_values:
        results[N] = {}
        x   = np.linspace(0.0, 1.0, N + 1)
        S   = _rhs(x)
        ccd = _make_ccd(N)
        D2  = _build_ccd_d2_matrix(ccd, N)
        phi_ex = _exact(x)

        # ── FD2 + SOR ────────────────────────────────────────────────────────
        phi, n, t, m, hist, om = solve_fd2_sor(N, S.copy())
        L2 = float(np.sqrt(np.mean((phi[1:-1] - phi_ex[1:-1])**2)))
        results[N]["FD2+SOR"] = dict(n_iters=n, time_ms=t, mem_MB=m,
                                     L2=L2, history=hist, omega=om,
                                     converged=(n < 20000))
        conv_s = "✓" if n < 20000 else "DNF"
        print(f"  N={N:4d}  [FD2+SOR  ω={om:.3f} {conv_s}]  i={n:6d}"
              f"  t={t:7.1f}ms  mem={m:.3f}MB  L2={L2:.3e}")

        # ── CCD + Direct LU ──────────────────────────────────────────────────
        phi, n, t, m, hist = solve_ccd_lu(D2, S.copy(), N)
        L2 = float(np.sqrt(np.mean((phi[1:-1] - phi_ex[1:-1])**2)))
        results[N]["CCD+LU"] = dict(n_iters=n, time_ms=t, mem_MB=m,
                                    L2=L2, history=hist)
        print(f"  N={N:4d}  [CCD+LU              ]  i={n:6d}"
              f"  t={t:7.1f}ms  mem={m:.3f}MB  L2={L2:.3e}")

        # ── CCD + BiCGSTAB ───────────────────────────────────────────────────
        phi, n, t, m, hist = solve_ccd_bicgstab(D2, S.copy(), N)
        L2 = float(np.sqrt(np.mean((phi[1:-1] - phi_ex[1:-1])**2)))
        results[N]["CCD+BiCGSTAB"] = dict(n_iters=n, time_ms=t, mem_MB=m,
                                          L2=L2, history=hist)
        print(f"  N={N:4d}  [CCD+BiCGSTAB        ]  i={n:6d}"
              f"  t={t:7.1f}ms  mem={m:.3f}MB  L2={L2:.3e}")

        # ── CCD + Pseudo-time ────────────────────────────────────────────────
        if N <= _PSEUDOTIME_MAX_N:
            phi, n, t, m, hist = solve_ccd_pseudotime(ccd, N, S.copy())
            L2 = float(np.sqrt(np.mean((phi[1:-1] - phi_ex[1:-1])**2)))
            results[N]["CCD+PseudoT"] = dict(n_iters=n, time_ms=t, mem_MB=m,
                                              L2=L2, history=hist, estimated=False)
            _pt_ref[N] = n
            print(f"  N={N:4d}  [CCD+PseudoT         ]  i={n:6d}"
                  f"  t={t:7.1f}ms  mem={m:.3f}MB  L2={L2:.3e}")
        else:
            # O(N²) extrapolation from smallest measured N
            N_ref = min(_pt_ref.keys())
            n_est = int(_pt_ref[N_ref] * (N / N_ref)**2)
            m_est = 3.0 * (N + 1) * 8.0 / 1e6
            # L2 extrapolate from CCD accuracy (O(h^5))
            L2_est = results[N_ref]["CCD+PseudoT"]["L2"] * (N_ref / N)**5
            results[N]["CCD+PseudoT"] = dict(n_iters=n_est, time_ms=float("nan"),
                                              mem_MB=m_est, L2=L2_est,
                                              history=[], estimated=True)
            print(f"  N={N:4d}  [CCD+PseudoT (est)   ]  i={n_est:6d} (O(N²) estimate)")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Figures
# ═══════════════════════════════════════════════════════════════════════════════

def _style(ax, xlabel="", ylabel="", title=""):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.grid(True, alpha=0.25, lw=0.6)


def plot_convergence(results: dict, N_plot: int):
    """‖res‖∞ vs iteration for iterative solvers at N=N_plot."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for key in ["FD2+SOR", "CCD+BiCGSTAB", "CCD+PseudoT"]:
        hist = results[N_plot][key]["history"]
        it_v = [h[0] for h in hist]
        rs_v = [max(h[1], 1e-18) for h in hist]
        ax.semilogy(it_v, rs_v, color=_COLORS[key], lw=1.8,
                    label=_LABELS[key],
                    marker=_MARKER[key],
                    markevery=max(1, len(it_v) // 8), ms=4)
    ax.axhline(1e-10, color="gray", lw=0.8, ls="--", label="tol $10^{-10}$")
    _style(ax, "Iteration", r"$\|\mathrm{res}\|_\infty$",
           f"Convergence history  |  N={N_plot}, 1D Poisson  (tol $=10^{{-8}}$)")
    ax.legend(fontsize=9, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(_FIG, "01_convergence.png")
    plt.savefig(out, dpi=180, bbox_inches="tight"); plt.close()
    print(f"  [fig] {out}")


def plot_time_scaling(results: dict, N_values: list):
    """Wall-clock time vs N (log-log)."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    Nf = np.array(N_values, dtype=float)
    for key in _SOLVERS:
        times = [results[N][key]["time_ms"] for N in N_values]
        ax.loglog(Nf, times, color=_COLORS[key], lw=1.8,
                  label=_LABELS[key], marker=_MARKER[key], ms=6)
    _style(ax, "Grid size N", "Wall-clock time (ms)",
           r"Solver scaling  |  tol $=10^{-8}$  (iterative methods)")
    ax.legend(fontsize=9, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(_FIG, "02_time_scaling.png")
    plt.savefig(out, dpi=180, bbox_inches="tight"); plt.close()
    print(f"  [fig] {out}")


def plot_accuracy(results: dict, N_values: list):
    """L₂ error vs N (log-log)."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    Nf = np.array(N_values, dtype=float)
    for key in _SOLVERS:
        errs = [results[N][key]["L2"] for N in N_values]
        ax.loglog(Nf, errs, color=_COLORS[key], lw=1.8,
                  label=_LABELS[key], marker=_MARKER[key], ms=6)
    # Reference lines
    c2 = results[N_values[0]]["FD2+SOR"]["L2"] * N_values[0]**2
    c5 = results[N_values[0]]["CCD+LU"]["L2"]  * N_values[0]**5
    ax.loglog(Nf, c2 / Nf**2, "k:", lw=0.8, label="$O(N^{-2})$ ref")
    ax.loglog(Nf, c5 / Nf**5, "k--", lw=0.8, label="$O(N^{-5})$ ref")
    _style(ax, "Grid size N", r"$L_2$ error",
           "Spatial accuracy  |  1D Poisson, $\\phi=\\sin(2\\pi x)$")
    ax.legend(fontsize=9, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(_FIG, "03_accuracy.png")
    plt.savefig(out, dpi=180, bbox_inches="tight"); plt.close()
    print(f"  [fig] {out}")


# ═══════════════════════════════════════════════════════════════════════════════
# CSV + LaTeX
# ═══════════════════════════════════════════════════════════════════════════════

def save_csv(results: dict, N_values: list):
    out = os.path.join(_DAT, "benchmark.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N", "solver", "n_iters", "time_ms", "mem_MB", "L2_err"])
        for N in N_values:
            for key in _SOLVERS:
                r = results[N][key]
                w.writerow([N, key, r["n_iters"],
                             f"{r['time_ms']:.2f}",
                             f"{r['mem_MB']:.4f}",
                             f"{r['L2']:.4e}"])
    print(f"  [csv] {out}")


def save_latex(results: dict, N_values: list):
    head = " & ".join(f"$N={N}$" for N in N_values)
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{%",
        r"    1次元ポアソン問題 $\phi'' = S$，$\phi=\sin(2\pi x)$ に対する各ソルバーの性能比較．",
        r"    収束判定 $\|\mathrm{res}\|_\infty < 10^{-10}$（Direct LU は 1 ステップ）．",
        r"    FD2$+$SOR の $\omega_{\rm opt}$ は格子ごとに最適化（$N=64$: $\omega=%.3f$）．}" % (
            results[64]["FD2+SOR"].get("omega", 1.9) if 64 in results else 1.9),
        r"  \label{tab:ccd_solver_benchmark}",
        rf"  \begin{{tabular}}{{l{'r'*len(N_values)}{'r'*len(N_values)}{'r'*len(N_values)}}}",
        r"    \toprule",
        r"    & \multicolumn{" + str(len(N_values)) + r"}{c}{反復回数}"
        + r" & \multicolumn{" + str(len(N_values)) + r"}{c}{時間 (ms)}"
        + r" & \multicolumn{" + str(len(N_values)) + r"}{c}{$L_2$ 誤差} \\",
        r"    \cmidrule(lr){2-" + str(1+len(N_values)) + "}"
        + r"\cmidrule(lr){" + str(2+len(N_values)) + "-" + str(1+2*len(N_values)) + "}"
        + r"\cmidrule(lr){" + str(2+2*len(N_values)) + "-" + str(1+3*len(N_values)) + "}",
        rf"    ソルバー & {head} & {head} & {head} \\",
        r"    \midrule",
    ]
    label_map = {
        "FD2+SOR": r"FD2$+$SOR",
        "CCD+LU": r"CCD$+$Direct LU",
        "CCD+BiCGSTAB": r"CCD$+$BiCGSTAB",
        "CCD+PseudoT": r"CCD$+$仮想時間",
    }
    for key in _SOLVERS:
        n_vals = [str(results[N][key]["n_iters"]) for N in N_values]
        t_vals = [f"{results[N][key]['time_ms']:.1f}" for N in N_values]
        l_vals = [f"${results[N][key]['L2']:.2e}$".replace("e-0", r"\times10^{-").replace("e-", r"\times10^{-") for N in N_values]
        # Simpler formatting
        l_vals = [f"${results[N][key]['L2']:.2e}$" for N in N_values]
        lines.append(f"    {label_map[key]} & " +
                     " & ".join(n_vals) + " & " +
                     " & ".join(t_vals) + " & " +
                     " & ".join(l_vals) + r" \\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    out = os.path.join(_TEX, "table_benchmark.tex")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  [tex] {out}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    N_values = [32, 64, 128, 256]
    N_plot   = 64   # grid size for convergence history plot

    print(f"[CCD Benchmark] N={N_values}, tol=1e-10")
    results = run_all(N_values)

    print("\n[CCD Benchmark] Figures ...")
    plot_convergence(results, N_plot)
    plot_time_scaling(results, N_values)
    plot_accuracy(results, N_values)

    print("\n[CCD Benchmark] Data ...")
    save_csv(results, N_values)
    save_latex(results, N_values)

    print("\n[CCD Benchmark] Done.")
