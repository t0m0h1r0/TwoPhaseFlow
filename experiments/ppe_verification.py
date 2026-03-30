"""
PPE Verification: Tests C-1, C-2, C-3
=======================================
Three tests verifying the CCD-Poisson solver (§11b3).

Manufactured solution: p*(x,y) = cos(πx)cos(πy)
  Satisfies Neumann BC ∂p/∂n = 0 on all walls (∂p/∂x|_{x=0,1} = -π sin(πx)cos(πy)|_{x=0,1} = 0,
  similarly for y). Gauge: p*(0.5,0.5) = cos(π/2)cos(π/2) = 0, matches center-node pin.
  RHS: f = -2π²cos(πx)cos(πy).
  Compatibility: ∫f dΩ = 0 (∫cos(πx)dx = 0).

Test C-1: Grid convergence (N=8..256, uniform density ρ=1).
  Expected: O(h^6) for CCD, O(h^2) for FD2.

Test C-2: LGMRES residual history (N=32,64,128; record convergence count).

Test C-3: Variable-density (ρ_l/ρ_g=10^3).
  p*(x,y) = ρ(x,y)·cos(πx)cos(πy); Neumann BC satisfied since
  ∂ρ/∂x=0 at x=0,1 and sin(0)=sin(π)=0.

Output
------
  results/ppe_verification/
    figures/  C1_convergence.png  C2_residual.png  C3_convergence.png
    data/     C1.csv  C2.csv  C3.csv
    latex/    tab_C1.tex  tab_C2.tex  tab_C3.tex
"""
from __future__ import annotations

import os, sys, csv, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from twophase.backend import Backend
from twophase.config import GridConfig, SimulationConfig, SolverConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.pressure.ppe_solver_ccd_lu import PPESolverCCDLU
from twophase.pressure.ppe_solver_pseudotime import PPESolverPseudoTime

_ROOT = os.path.join(os.path.dirname(__file__), "..")
_OUT  = os.path.join(_ROOT, "results", "ppe_verification")
_FIG  = os.path.join(_OUT, "figures")
_DAT  = os.path.join(_OUT, "data")
_TEX  = os.path.join(_OUT, "latex")
for _d in (_FIG, _DAT, _TEX):
    os.makedirs(_d, exist_ok=True)


# ─── helpers ─────────────────────────────────────────────────────────────────

def make_backend_grid_solver(N: int, solver_cls=PPESolverCCDLU, pseudo_tol=1e-12):
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    sc = SolverConfig(pseudo_tol=pseudo_tol, pseudo_maxiter=2000)
    cfg = SimulationConfig(solver=sc)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    solver = solver_cls(backend, cfg, grid, ccd=ccd)
    return backend, grid, solver


def nodes(N):
    pts = np.linspace(0.0, 1.0, N + 1)
    return np.meshgrid(pts, pts, indexing="ij")


# ─── C-1: grid convergence (uniform density) ─────────────────────────────────

def _fd2_neumann_poisson(N: int) -> np.ndarray:
    """FD2 Laplacian with Neumann BC on [0,1]² + center-pin gauge.
    Exact solution p* = cos(πx)cos(πy), f = -2π²cos(πx)cos(πy).
    """
    h = 1.0 / N
    n_tot = (N + 1) ** 2
    idx = lambda i, j: i * (N + 1) + j

    rows, cols, vals = [], [], []
    rhs_list = np.zeros(n_tot)

    X, Y = nodes(N)
    f_field = -2.0 * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y)

    for i in range(N + 1):
        for j in range(N + 1):
            r = idx(i, j)
            # Reflect at boundaries (Neumann: one-sided stencil mirrors)
            im = max(i - 1, 0) if i > 0 else 1   # ghost = node 1
            ip = min(i + 1, N) if i < N else N - 1
            jm = max(j - 1, 0) if j > 0 else 1
            jp = min(j + 1, N) if j < N else N - 1

            stencil = {r: 0.0}
            def _add(ni, nj, v):
                k = idx(ni, nj)
                stencil[k] = stencil.get(k, 0.0) + v

            # d²p/dx²
            _add(ip, j,  1.0 / h**2)
            stencil[r] -= 2.0 / h**2
            _add(im, j,  1.0 / h**2)
            # d²p/dy²
            _add(i, jp,  1.0 / h**2)
            stencil[r] -= 2.0 / h**2
            _add(i, jm,  1.0 / h**2)

            for c, v in stencil.items():
                rows.append(r); cols.append(c); vals.append(v)
            rhs_list[r] = f_field[i, j]

    A = sp.csr_matrix((vals, (rows, cols)), shape=(n_tot, n_tot))
    # Pin center node
    pin = (N // 2) * (N + 1) + (N // 2)
    A_lil = A.tolil()
    A_lil[pin, :] = 0.0
    A_lil[pin, pin] = 1.0
    A = A_lil.tocsr()
    rhs_list[pin] = 0.0  # p*(0.5,0.5) = 0

    p_flat = spla.spsolve(A, rhs_list)
    return p_flat.reshape(N + 1, N + 1)


def run_C1():
    print("\n[C-1] Grid convergence: uniform-density Poisson O(h^6)")
    N_list = [8, 16, 32, 64, 128, 256]
    results = []

    for N in N_list:
        backend, grid, solver = make_backend_grid_solver(N)
        X, Y = nodes(N)
        p_exact  = np.cos(np.pi * X) * np.cos(np.pi * Y)
        rhs_field = -2.0 * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y)
        rho = np.ones_like(rhs_field)

        p_ccd = np.asarray(solver.solve(
            backend.to_device(rhs_field.astype(float)),
            backend.to_device(rho.astype(float)),
            dt=1.0,
        ))
        # p_exact(0.5,0.5) = 0 = gauge pin → no shift needed
        mask_int = np.zeros_like(p_exact, dtype=bool)
        mask_int[1:N, 1:N] = True
        err_ccd = float(np.max(np.abs((p_ccd - p_exact)[mask_int])))

        p_fd2 = _fd2_neumann_poisson(N)
        err_fd2 = float(np.max(np.abs((p_fd2 - p_exact)[mask_int])))

        results.append((N, err_ccd, err_fd2))
        print(f"  N={N:4d}: CCD E={err_ccd:.3e}  FD2 E={err_fd2:.3e}")

    rows = []
    for k, (N, e_ccd, e_fd2) in enumerate(results):
        if k == 0:
            ord_ccd = ord_fd2 = float("nan")
        else:
            e_ccd_p, e_fd2_p = results[k - 1][1], results[k - 1][2]
            ord_ccd = np.log2(e_ccd_p / e_ccd) if e_ccd > 0 else float("nan")
            ord_fd2 = np.log2(e_fd2_p / e_fd2) if e_fd2 > 0 else float("nan")
        rows.append((N, e_ccd, ord_ccd, e_fd2, ord_fd2))

    with open(os.path.join(_DAT, "C1.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["N", "CCD_Linf", "CCD_order", "FD2_Linf", "FD2_order"])
        for r in rows:
            w.writerow([r[0], f"{r[1]:.3e}", "" if np.isnan(r[2]) else f"{r[2]:.2f}",
                        f"{r[3]:.3e}", "" if np.isnan(r[4]) else f"{r[4]:.2f}"])

    with open(os.path.join(_TEX, "tab_C1.tex"), "w") as f:
        f.write(
r"""\begin{table}[htbp]
\centering
\caption{テスト C-1：CCD-Poisson ソルバーの格子収束テスト（実測値）．
  解析解 $p^*(x,y)=\cos(\pi x)\cos(\pi y)$，ノイマン BC，均一密度 $\rho=1$．
  スクリプト: \texttt{experiments/ppe\_verification.py}.}
\label{tab:ccd_poisson_conv}
\begin{tabular}{ccccc}
\toprule
$N$ & CCD $L^\infty$ & 収束次数 & FD2 $L^\infty$ & 収束次数 \\
\midrule
""")
        for r in rows:
            oc = "---" if np.isnan(r[2]) else f"{r[2]:.1f}"
            of = "---" if np.isnan(r[4]) else f"{r[4]:.1f}"
            f.write(f"${r[0]}$ & ${r[1]:.3e}$ & ${oc}$ & ${r[3]:.3e}$ & ${of}$ \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")

    hs = [1.0 / r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.loglog(hs, [r[1] for r in rows], "o-", label="CCD", color="C0")
    ax.loglog(hs, [r[3] for r in rows], "s--", label="FD2", color="C1")
    href = np.array(hs)
    ax.loglog(href, rows[-2][1] * (href / hs[-2])**6, ":", color="C0", label="$h^6$")
    ax.loglog(href, rows[-2][3] * (href / hs[-2])**2, ":", color="C1", label="$h^2$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("Test C-1: CCD-Poisson grid convergence")
    ax.legend(fontsize=9); ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(_FIG, "C1_convergence.png"), dpi=150); plt.close(fig)
    print("  [fig] C1_convergence.png")
    return rows


# ─── C-2: LGMRES convergence behavior ────────────────────────────────────────

def run_C2():
    print("\n[C-2] LGMRES convergence (residual history, N sweep)")
    N_list = [32, 64, 128]
    results = []

    for N in N_list:
        backend, grid, _ = make_backend_grid_solver(N)
        X, Y = nodes(N)
        rhs_field = -2.0 * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y)
        rho = np.ones_like(rhs_field)

        # Build pinned operator via the base class
        from twophase.pressure.ppe_solver_ccd_lu import PPESolverCCDLU as _LU
        sc = SolverConfig(pseudo_tol=1e-12, pseudo_maxiter=5000)
        cfg = SimulationConfig(solver=sc)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        solver_lu = _LU(backend, cfg, grid, ccd=ccd)
        L_pinned, rhs_np = solver_lu._assemble_pinned_system(
            backend.to_device(rhs_field.astype(float)),
            backend.to_device(rho.astype(float)),
        )

        iters = []
        def _cb(residual):
            iters.append(float(np.linalg.norm(residual)))

        p_flat, info = spla.lgmres(
            L_pinned, rhs_np, x0=np.zeros(rhs_np.shape[0]),
            rtol=1e-10, atol=1e-14, maxiter=3000,
            callback=_cb,
        )
        n_iters = len(iters)
        final_res = iters[-1] if iters else float("nan")
        print(f"  N={N:4d}: LGMRES iters={n_iters:5d}  final_res={final_res:.3e}  info={info}")
        results.append((N, n_iters, final_res, iters))

    # Save CSV (iter count table)
    with open(os.path.join(_DAT, "C2.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["N", "lgmres_iters", "final_res"])
        for N, n_iters, final_res, _ in results:
            w.writerow([N, n_iters, f"{final_res:.3e}"])

    # LaTeX table
    with open(os.path.join(_TEX, "tab_C2.tex"), "w") as f:
        f.write(r"""\begin{table}[htbp]
\centering
\caption{テスト C-2：LGMRES 収束挙動（均一密度，ノイマン BC）．
  残差 $\|\mathcal{L}p - q\|_2 < 10^{-10}$ を達成するまでの反復回数と最終残差．
  スクリプト: \texttt{experiments/ppe\_verification.py}.}
\label{tab:ccd_pseudotime_conv}
\begin{tabular}{ccc}
\toprule
$N$ & LGMRES 反復回数 & 最終残差 $\|\mathcal{L}p-q\|_2$ \\
\midrule
""")
        for N, n_iters, final_res, _ in results:
            f.write(f"${N}$ & ${n_iters}$ & ${final_res:.3e}$ \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")

    # Figure: residual vs iteration
    fig, ax = plt.subplots(figsize=(7, 4))
    for N, n_iters, final_res, iters in results:
        ax.semilogy(range(len(iters)), iters, label=f"$N={N}$")
    ax.set_xlabel("LGMRES iteration"); ax.set_ylabel(r"$\|\mathcal{L}p - q\|_2$")
    ax.set_title("Test C-2: LGMRES convergence (uniform density)")
    ax.legend(fontsize=9); ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(_FIG, "C2_residual.png"), dpi=150); plt.close(fig)
    print("  [fig] C2_residual.png")
    return results


# ─── C-3: variable-density ───────────────────────────────────────────────────

def _piecewise_linear_H(s, eps):
    return np.where(s < -eps, 0.0, np.where(s > eps, 1.0, 0.5 * (1.0 + s / eps)))

def _build_rho_drho(X, eps, rho_l=1000.0, rho_g=1.0):
    s = X - 0.5
    H = _piecewise_linear_H(s, eps)
    rho = rho_g + (rho_l - rho_g) * H
    drho_dx = np.where(np.abs(s) <= eps, (rho_l - rho_g) / (2.0 * eps), 0.0)
    return rho, drho_dx

def _fd2_var_neumann(N, eps):
    """FD2 5-point ∇·(1/ρ ∇p) = f with Neumann BC, center-pin gauge.
    p* = ρ(x,y)·cos(πx)cos(πy).
    """
    h = 1.0 / N
    x = np.linspace(0, 1, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    rho, drho_dx = _build_rho_drho(X, eps)

    p_exact = rho * np.cos(np.pi * X) * np.cos(np.pi * Y)

    # Compute RHS = ∇·(1/ρ ∇p*) analytically
    dp_dx = (drho_dx * np.cos(np.pi * X) * np.cos(np.pi * Y)
             - rho * np.pi * np.sin(np.pi * X) * np.cos(np.pi * Y))
    dp_dy = -rho * np.pi * np.cos(np.pi * X) * np.sin(np.pi * Y)
    d2p_dx2 = (0.0  # ∂²ρ/∂x² = 0 for piecewise-linear (approx)
               - 2.0 * drho_dx * np.pi * np.sin(np.pi * X) * np.cos(np.pi * Y)
               - rho * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y))
    d2p_dy2 = -rho * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y)
    f_field = (d2p_dx2 + d2p_dy2) / rho - (drho_dx / rho**2) * dp_dx

    n_tot = (N + 1)**2
    idx = lambda i, j: i * (N + 1) + j

    rows_, cols_, vals_ = [], [], []
    rhs_arr = np.zeros(n_tot)

    for i in range(N + 1):
        for j in range(N + 1):
            r = idx(i, j)
            rho_c = rho[i, j]
            im = i - 1 if i > 0 else 1; ip = i + 1 if i < N else N - 1
            jm = j - 1 if j > 0 else 1; jp = j + 1 if j < N else N - 1

            stencil = {r: 0.0}
            def _add(ni, nj, v):
                k = idx(ni, nj)
                stencil[k] = stencil.get(k, 0.0) + v
            _add(ip, j,  1.0 / (rho_c * h**2)); stencil[r] -= 2.0 / (rho_c * h**2)
            _add(im, j,  1.0 / (rho_c * h**2))
            _add(i, jp,  1.0 / (rho_c * h**2)); stencil[r] -= 2.0 / (rho_c * h**2)
            _add(i, jm,  1.0 / (rho_c * h**2))

            for c_, v_ in stencil.items():
                rows_.append(r); cols_.append(c_); vals_.append(v_)
            rhs_arr[r] = f_field[i, j]

    A = sp.csr_matrix((vals_, (rows_, cols_)), shape=(n_tot, n_tot))
    pin_dof = (N // 2) * (N + 1) + (N // 2)
    A_lil = A.tolil(); A_lil[pin_dof, :] = 0.0; A_lil[pin_dof, pin_dof] = 1.0
    A = A_lil.tocsr(); rhs_arr[pin_dof] = 0.0  # p*(0.5,0.5)=0
    p_flat = spla.spsolve(A, rhs_arr)
    return p_flat.reshape(N + 1, N + 1), p_exact, f_field


def run_C3():
    print("\n[C-3] Variable-density Poisson (density ratio 1000)")
    N_list = [32, 64, 128]
    results = []

    for N in N_list:
        h = 1.0 / N
        eps = 3.0 * h
        backend, grid, solver = make_backend_grid_solver(N)
        X, Y = nodes(N)
        rho, drho_dx = _build_rho_drho(X, eps)

        p_exact = rho * np.cos(np.pi * X) * np.cos(np.pi * Y)
        dp_dx = (drho_dx * np.cos(np.pi * X) * np.cos(np.pi * Y)
                 - rho * np.pi * np.sin(np.pi * X) * np.cos(np.pi * Y))
        d2p_dx2 = (- 2.0 * drho_dx * np.pi * np.sin(np.pi * X) * np.cos(np.pi * Y)
                   - rho * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y))
        d2p_dy2 = -rho * np.pi**2 * np.cos(np.pi * X) * np.cos(np.pi * Y)
        f_field = (d2p_dx2 + d2p_dy2) / rho - (drho_dx / rho**2) * dp_dx

        p_ccd = np.asarray(solver.solve(
            backend.to_device(f_field.astype(float)),
            backend.to_device(rho.astype(float)),
            dt=1.0,
        ))
        # p*(0.5,0.5) = ρ(0.5)·cos(π/2)·cos(π/2) = 0 → no shift
        mask_int = np.zeros_like(p_exact, dtype=bool); mask_int[1:N, 1:N] = True
        err_ccd = float(np.max(np.abs((p_ccd - p_exact)[mask_int])))

        p_fd2, _, _ = _fd2_var_neumann(N, eps)
        err_fd2 = float(np.max(np.abs((p_fd2 - p_exact)[mask_int])))

        results.append((N, err_ccd, err_fd2))
        print(f"  N={N:4d}: CCD E={err_ccd:.3e}  FD2 E={err_fd2:.3e}  ratio={err_fd2/max(err_ccd,1e-30):.1f}x")

    rows = []
    for k, (N, e_ccd, e_fd2) in enumerate(results):
        if k == 0:
            ord_ccd = ord_fd2 = float("nan")
        else:
            e_c0, e_f0 = results[k - 1][1], results[k - 1][2]
            ord_ccd = np.log2(e_c0 / e_ccd) if e_ccd > 0 else float("nan")
            ord_fd2 = np.log2(e_f0 / e_fd2) if e_fd2 > 0 else float("nan")
        rows.append((N, e_ccd, ord_ccd, e_fd2, ord_fd2))

    with open(os.path.join(_DAT, "C3.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["N","CCD_Linf","CCD_order","FD2_Linf","FD2_order"])
        for r in rows:
            w.writerow([r[0], f"{r[1]:.3e}", "" if np.isnan(r[2]) else f"{r[2]:.2f}",
                        f"{r[3]:.3e}", "" if np.isnan(r[4]) else f"{r[4]:.2f}"])

    with open(os.path.join(_TEX, "tab_C3.tex"), "w") as f:
        f.write(r"""\begin{table}[htbp]
\centering
\caption{テスト C-3：変密度 Poisson（$\rho_l/\rho_g = 10^3$）格子収束（実測値）．
  $\varepsilon = 3h$，解析解 $p^*(x,y)=\rho(x,y)\cos(\pi x)\cos(\pi y)$（ノイマン BC）．
  スクリプト: \texttt{experiments/ppe\_verification.py}.}
\label{tab:c3_var_density}
\begin{tabular}{ccccc}
\toprule
$N$ & CCD $L^\infty$ & 収束次数 & FD2 $L^\infty$ & 収束次数 \\
\midrule
""")
        for r in rows:
            oc = "---" if np.isnan(r[2]) else f"{r[2]:.1f}"
            of = "---" if np.isnan(r[4]) else f"{r[4]:.1f}"
            f.write(f"${r[0]}$ & ${r[1]:.3e}$ & ${oc}$ & ${r[3]:.3e}$ & ${of}$ \\\\\n")
        f.write(r"""\bottomrule
\end{tabular}
\end{table}
""")

    hs = [1.0 / r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.loglog(hs, [r[1] for r in rows], "o-", label="CCD", color="C0")
    ax.loglog(hs, [r[3] for r in rows], "s--", label="FD2", color="C1")
    href = np.array(hs)
    ax.loglog(href, rows[0][1] * (href / hs[0])**4, ":", color="C0", label="$h^4$")
    ax.loglog(href, rows[0][3] * (href / hs[0])**2, ":", color="C1", label="$h^2$")
    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("Test C-3: Variable-density Poisson ($\\rho_l/\\rho_g=10^3$)")
    ax.legend(fontsize=9); ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(_FIG, "C3_convergence.png"), dpi=150); plt.close(fig)
    print("  [fig] C3_convergence.png")
    return rows


# ─── main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[PPE Verification] Running Tests C-1, C-2, C-3 …")
    c1 = run_C1()
    c2 = run_C2()
    c3 = run_C3()
    print("\n[PPE Verification] Done. Outputs in results/ppe_verification/")
