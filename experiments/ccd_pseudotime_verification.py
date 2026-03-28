"""
CCD Pseudo-time Verification Experiment
========================================
Three cases verifying 6th-order CCD spatial accuracy and pseudo-time stability.

CCD computation uses src/twophase/ccd/ccd_solver.CCDSolver directly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import scipy.linalg
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver


# ---------------------------------------------------------------------------
# CCD 1D helpers using CCDSolver
# ---------------------------------------------------------------------------

def _make_ccd_1d(N: int, L: float = 1.0) -> CCDSolver:
    """Return a CCDSolver usable for 1D differentiation along axis=0.

    GridConfig requires ndim≥2, so a thin 2D grid (N[1]=2) is used.
    Only axis=0 is ever called.
    """
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, 2), L=(L, 1.0))
    grid = Grid(gc, backend)
    return CCDSolver(grid, backend, bc_type="wall")


def _ccd_d1d2_1d(solver: CCDSolver, u: np.ndarray):
    """(d1, d2) of 1D array u via CCDSolver (axis=0)."""
    u2d = np.tile(u[:, None], (1, 3))          # (N+1, 3) — batch over 3 columns
    d1_2d, d2_2d = solver.differentiate(u2d, axis=0)
    return np.asarray(d1_2d[:, 0]), np.asarray(d2_2d[:, 0])


def _ccd_d2_1d(solver: CCDSolver, u: np.ndarray) -> np.ndarray:
    """Second derivative of 1D array u via CCDSolver (axis=0)."""
    _, d2 = _ccd_d1d2_1d(solver, u)
    return d2


def _build_ccd_matrices(solver: CCDSolver, N: int):
    """Build (D1, D2) derivative matrices via basis-vector approach.

    Columns are computed by applying CCDSolver to each canonical basis vector.
    """
    n_pts = N + 1
    D1 = np.zeros((n_pts, n_pts))
    D2 = np.zeros((n_pts, n_pts))
    for j in range(n_pts):
        e = np.zeros(n_pts)
        e[j] = 1.0
        d1j, d2j = _ccd_d1d2_1d(solver, e)
        D1[:, j] = d1j
        D2[:, j] = d2j
    return D1, D2


def _ccd_d2_spectral_radius(D2: np.ndarray) -> float:
    """Return max |λ| of the D2 matrix (spectral radius for stability bound)."""
    eigs = np.linalg.eigvals(D2)
    return float(np.max(np.abs(eigs.real)))


def _cds2_d2(u: np.ndarray, h: float) -> np.ndarray:
    """Central difference d2 at interior nodes; boundary set to 0."""
    d2 = np.zeros_like(u)
    d2[1:-1] = (u[:-2] - 2.0 * u[1:-1] + u[2:]) / h**2
    return d2


# ---------------------------------------------------------------------------
# Case 1 — Spatial Convergence
# ---------------------------------------------------------------------------

def case1_convergence():
    print("\n" + "=" * 60)
    print("Case 1: Spatial Convergence  u=sin(2πx)")
    print("=" * 60)

    Ns = [8, 16, 32, 64, 128]
    ccd_errors = []
    cds2_errors = []

    for N in Ns:
        h = 1.0 / N
        x = np.linspace(0.0, 1.0, N + 1)
        u = np.sin(2.0 * np.pi * x)
        d2_exact = -(2.0 * np.pi) ** 2 * np.sin(2.0 * np.pi * x)

        solver = _make_ccd_1d(N)
        d2_ccd = _ccd_d2_1d(solver, u)
        err_ccd = np.max(np.abs(d2_ccd[1:-1] - d2_exact[1:-1]))

        d2_cds = _cds2_d2(u, h)
        err_cds2 = np.max(np.abs(d2_cds[1:-1] - d2_exact[1:-1]))

        ccd_errors.append(err_ccd)
        cds2_errors.append(err_cds2)

    ccd_errors = np.array(ccd_errors)
    cds2_errors = np.array(cds2_errors)
    hs = np.array([1.0 / N for N in Ns])

    ccd_orders = np.log(ccd_errors[:-1] / ccd_errors[1:]) / np.log(hs[:-1] / hs[1:])
    cds2_orders = np.log(cds2_errors[:-1] / cds2_errors[1:]) / np.log(hs[:-1] / hs[1:])

    print("\n% LaTeX table — Case 1")
    print(r"\begin{tabular}{rrcccc}")
    print(r"  $N$ & $h$ & CCD $L^\infty$ & CDS2 $L^\infty$ & CCD order & CDS2 order \\")
    print(r"  \hline")
    for k, N in enumerate(Ns):
        h = 1.0 / N
        o_ccd = f"{ccd_orders[k-1]:.2f}" if k > 0 else "--"
        o_cds2 = f"{cds2_orders[k-1]:.2f}" if k > 0 else "--"
        print(f"  {N:4d} & {h:.4f} & {ccd_errors[k]:.3e} & {cds2_errors[k]:.3e} "
              f"& {o_ccd} & {o_cds2} \\\\")
    print(r"\end{tabular}")

    os.makedirs("results/ccd_pseudotime", exist_ok=True)
    np.savez("results/ccd_pseudotime/case1_convergence.npz",
             Ns=Ns, hs=hs,
             ccd_errors=ccd_errors, cds2_errors=cds2_errors,
             ccd_orders=ccd_orders, cds2_orders=cds2_orders)

    return Ns, hs, ccd_errors, cds2_errors, ccd_orders, cds2_orders


# ---------------------------------------------------------------------------
# Case 2 — Pseudo-time Implicit for Parabolic PDE
# ---------------------------------------------------------------------------

def _pseudo_time_step(solver_or_h, u_guess, rhs, eps, dt_phys, method,
                      rho_d2: float = None,
                      max_iter=500, tol=1e-10, bdf_coeff=1.5):
    """Solve (bdf_coeff/Δt)·u − ε·u_xx = rhs via pseudo-time forward Euler.

    Parameters
    ----------
    solver_or_h : CCDSolver (method="CCD") or float h (method="CDS2")
    rho_d2      : spectral radius of the D2 operator (|max eigenvalue|).
                  Determines stable Δτ.  CDS2 ≈ 4/h², CCD ≈ 9.6/h².
                  If None, uses 4/h² (conservative for both).
    """
    lam = bdf_coeff / dt_phys
    n_pts = len(u_guess)
    h = 1.0 / (n_pts - 1)
    if rho_d2 is None:
        rho_d2 = 4.0 / h ** 2          # safe default (CDS2 spectral radius)
    dt_tau = 0.9 / (lam + eps * rho_d2 / 2.0)   # factor /2 matches CDS2 convention

    u = u_guess.copy()
    u[0] = 0.0
    u[-1] = 0.0

    for it in range(max_iter):
        if method == "CCD":
            d2u = _ccd_d2_1d(solver_or_h, u)
        else:
            d2u = _cds2_d2(u, h)

        residual = rhs - lam * u + eps * d2u
        residual[0] = 0.0
        residual[-1] = 0.0

        if np.max(np.abs(residual)) < tol:
            return u, it + 1

        u = u + dt_tau * residual
        u[0] = 0.0
        u[-1] = 0.0

    return u, max_iter


def case2_parabolic():
    print("\n" + "=" * 60)
    print("Case 2: Parabolic PDE  u_t = ε u_xx")
    print("=" * 60)

    eps = 0.01
    N = 64
    n_pts = N + 1
    h = 1.0 / N
    x = np.linspace(0.0, 1.0, n_pts)
    T_end = 1.0

    dt_cfl = h ** 2 / (2.0 * eps)
    dt_vals = [dt_cfl, 0.01, 0.1]
    dt_labels = [f"CFL={dt_cfl:.4f}", "0.01", "0.1"]

    u_exact_T = np.exp(-eps * np.pi ** 2 * T_end) * np.sin(np.pi * x)

    ccd_solver = _make_ccd_1d(N)

    # Spectral radius of D2_ccd (numerically): determines stable Δτ for CCD.
    # CDS2 uses the standard central-difference value 4/h².
    _, D2_mat = _build_ccd_matrices(ccd_solver, N)
    rho_ccd = _ccd_d2_spectral_radius(D2_mat)
    rho_cds2 = 4.0 / h ** 2
    print(f"  D2 spectral radii:  CCD={rho_ccd:.2f}/h² ({rho_ccd * h**2:.4f}/h²-units), "
          f"CDS2={rho_cds2:.2f} ({rho_cds2 * h**2:.4f}/h²-units)")

    results = {}

    for dt_phys, lbl in zip(dt_vals, dt_labels):
        n_steps = max(1, int(round(T_end / dt_phys)))
        actual_dt = T_end / n_steps

        for method in ["CCD", "CDS2"]:
            solver_arg = ccd_solver if method == "CCD" else h
            rho_d2 = rho_ccd if method == "CCD" else rho_cds2

            u0 = np.sin(np.pi * x)
            # BDF1 bootstrap (step 0 → 1)
            rhs1 = u0 / actual_dt
            u1, _ = _pseudo_time_step(solver_arg, u0.copy(), rhs1, eps,
                                      actual_dt, method, rho_d2=rho_d2,
                                      bdf_coeff=1.0)

            u_curr, u_prev = u1.copy(), u0.copy()
            total_iters = 0

            for _ in range(1, n_steps):
                rhs = (4.0 * u_curr - u_prev) / (2.0 * actual_dt)
                u_new, it = _pseudo_time_step(solver_arg, u_curr.copy(), rhs,
                                              eps, actual_dt, method,
                                              rho_d2=rho_d2, bdf_coeff=1.5)
                u_prev, u_curr = u_curr, u_new
                total_iters += it

            avg_iters = total_iters / max(n_steps - 1, 1)
            err = np.max(np.abs(u_curr - u_exact_T))
            results[(lbl, method)] = {"error": err, "avg_iters": avg_iters,
                                      "n_steps": n_steps, "dt": actual_dt}
            print(f"  dt={lbl:12s}  method={method}  "
                  f"err={err:.3e}  avg_iters={avg_iters:.1f}  n_steps={n_steps}")

    os.makedirs("results/ccd_pseudotime", exist_ok=True)
    keys = list(results.keys())
    np.savez("results/ccd_pseudotime/case2_parabolic.npz",
             dt_labels=dt_labels, dt_vals=dt_vals,
             results_keys=np.array([str(k) for k in keys]),
             results_errors=np.array([results[k]["error"] for k in keys]),
             results_avg_iters=np.array([results[k]["avg_iters"] for k in keys]),
             results_n_steps=np.array([results[k]["n_steps"] for k in keys]))

    return dt_vals, dt_labels, results


# ---------------------------------------------------------------------------
# Case 3 — Steady Advection-Diffusion
# ---------------------------------------------------------------------------

def case3_advdiff():
    print("\n" + "=" * 60)
    print("Case 3: Steady Advection-Diffusion  c·u_x − ε·u_xx = 0  (Pe=10)")
    print("=" * 60)

    c = 1.0
    eps = 0.1
    Pe = c / eps  # = 10
    Ns = [8, 16, 32, 64, 128, 256]

    ccd_errors = []
    cds2_errors = []

    for N in Ns:
        n_pts = N + 1
        h = 1.0 / N
        x = np.linspace(0.0, 1.0, n_pts)
        u_exact = (np.exp(Pe * x) - 1.0) / (np.exp(Pe) - 1.0)

        # CCD: build operator matrices via CCDSolver
        solver = _make_ccd_1d(N)
        D1, D2 = _build_ccd_matrices(solver, N)
        A_ccd = c * D1 - eps * D2
        rhs_ccd = np.zeros(n_pts)
        A_ccd[0, :] = 0.0;  A_ccd[0, 0] = 1.0;  rhs_ccd[0] = 0.0
        A_ccd[N, :] = 0.0;  A_ccd[N, N] = 1.0;  rhs_ccd[N] = 1.0
        u_ccd = scipy.linalg.solve(A_ccd, rhs_ccd)
        err_ccd = np.max(np.abs(u_ccd[1:-1] - u_exact[1:-1]))

        # CDS2: standard central-difference system
        A_cds2 = np.zeros((n_pts, n_pts))
        rhs_cds2 = np.zeros(n_pts)
        A_cds2[0, 0] = 1.0
        A_cds2[N, N] = 1.0;  rhs_cds2[N] = 1.0
        for i in range(1, N):
            A_cds2[i, i - 1] = -c / (2.0 * h) - eps / h ** 2
            A_cds2[i, i]     =  2.0 * eps / h ** 2
            A_cds2[i, i + 1] =  c / (2.0 * h) - eps / h ** 2
        u_cds2 = scipy.linalg.solve(A_cds2, rhs_cds2)
        err_cds2 = np.max(np.abs(u_cds2[1:-1] - u_exact[1:-1]))

        ccd_errors.append(err_ccd)
        cds2_errors.append(err_cds2)

    ccd_errors = np.array(ccd_errors)
    cds2_errors = np.array(cds2_errors)
    hs = np.array([1.0 / N for N in Ns])
    Peh = Pe * hs

    ccd_orders = np.log(ccd_errors[:-1] / ccd_errors[1:]) / np.log(hs[:-1] / hs[1:])
    cds2_orders = np.log(cds2_errors[:-1] / cds2_errors[1:]) / np.log(hs[:-1] / hs[1:])

    print("\n% LaTeX table — Case 3")
    print(r"\begin{tabular}{rrccccc}")
    print(r"  $N$ & $h$ & $Pe\cdot h$ & CCD $L^\infty$ & CDS2 $L^\infty$ & CCD order & CDS2 order \\")
    print(r"  \hline")
    for k, N in enumerate(Ns):
        h = 1.0 / N
        o_ccd = f"{ccd_orders[k-1]:.2f}" if k > 0 else "--"
        o_cds2 = f"{cds2_orders[k-1]:.2f}" if k > 0 else "--"
        print(f"  {N:4d} & {h:.5f} & {Peh[k]:.3f} & {ccd_errors[k]:.3e} "
              f"& {cds2_errors[k]:.3e} & {o_ccd} & {o_cds2} \\\\")
    print(r"\end{tabular}")

    os.makedirs("results/ccd_pseudotime", exist_ok=True)
    np.savez("results/ccd_pseudotime/case3_advdiff.npz",
             Ns=Ns, hs=hs, Peh=Peh,
             ccd_errors=ccd_errors, cds2_errors=cds2_errors,
             ccd_orders=ccd_orders, cds2_orders=cds2_orders)

    return Ns, hs, Peh, ccd_errors, cds2_errors, ccd_orders, cds2_orders


# ---------------------------------------------------------------------------
# Figure generation
# ---------------------------------------------------------------------------

def fig1_convergence(Ns, hs, ccd_errors, cds2_errors, ccd_orders, cds2_orders):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.loglog(hs, ccd_errors,  "b-o",  label="CCD",  linewidth=1.8, markersize=7)
    ax.loglog(hs, cds2_errors, "r--s", label="CDS2", linewidth=1.8, markersize=7)

    ref2 = cds2_errors[0] * (hs / hs[0]) ** 2
    ref6 = ccd_errors[0]  * (hs / hs[0]) ** 6
    ax.loglog(hs, ref2, color="gray", linestyle=":",  linewidth=1.0, label=r"$O(h^2)$")
    ax.loglog(hs, ref6, color="gray", linestyle="-.", linewidth=1.0, label=r"$O(h^6)$")

    for k in range(len(ccd_orders)):
        hmid = np.sqrt(hs[k] * hs[k + 1])
        ax.annotate(f"p={ccd_orders[k]:.1f}",
                    xy=(hmid, np.sqrt(ccd_errors[k] * ccd_errors[k + 1])),
                    fontsize=8, color="blue", ha="center")
    for k in range(len(cds2_orders)):
        hmid = np.sqrt(hs[k] * hs[k + 1])
        ax.annotate(f"p={cds2_orders[k]:.1f}",
                    xy=(hmid, np.sqrt(cds2_errors[k] * cds2_errors[k + 1]) * 1.5),
                    fontsize=8, color="red", ha="center")

    ax.set_xlabel("Grid spacing $h$", fontsize=12)
    ax.set_ylabel(r"$L^\infty$ error in $u''$", fontsize=12)
    ax.set_title(r"Case 1: Spatial Convergence ($u''$ of $\sin(2\pi x)$)", fontsize=13)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, which="both", ls="--", alpha=0.4)
    fig.tight_layout()

    os.makedirs("results/ccd_pseudotime/figures", exist_ok=True)
    fig.savefig("results/ccd_pseudotime/figures/case1_convergence.png", dpi=150)
    plt.close(fig)
    print("Saved: results/ccd_pseudotime/figures/case1_convergence.png")


def fig2_parabolic(dt_vals, dt_labels, results):
    fig, axes = plt.subplots(1, 3, figsize=(10, 5))
    methods = ["CCD", "CDS2"]
    colors = {"CCD": "#2166ac", "CDS2": "#d6604d"}

    for ax, dt_phys, lbl in zip(axes, dt_vals, dt_labels):
        errs = [results[(lbl, m)]["error"] for m in methods]
        bars = ax.bar(methods, errs, color=[colors[m] for m in methods],
                      alpha=0.85, edgecolor="k")
        ax.set_yscale("log")
        ax.set_xlabel("Method", fontsize=10)
        ax.set_ylabel(r"$L^\infty$ error at $T=1$", fontsize=9)
        ax.set_title(f"$\\Delta t = {dt_phys:.4f}$", fontsize=11)
        ax.grid(True, axis="y", ls="--", alpha=0.4)
        for bar, err in zip(bars, errs):
            ax.text(bar.get_x() + bar.get_width() / 2.0, err * 1.5,
                    f"{err:.1e}", ha="center", va="bottom", fontsize=8)

    fig.suptitle(r"Case 2: Parabolic PDE — Large $\Delta t$ Stability", fontsize=13)
    fig.tight_layout()

    os.makedirs("results/ccd_pseudotime/figures", exist_ok=True)
    fig.savefig("results/ccd_pseudotime/figures/case2_parabolic.png", dpi=150)
    plt.close(fig)
    print("Saved: results/ccd_pseudotime/figures/case2_parabolic.png")


def fig3_advdiff(Ns, hs, Peh, ccd_errors, cds2_errors, ccd_orders, cds2_orders):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.loglog(hs, ccd_errors,  "b-o",  label="CCD",  linewidth=1.8, markersize=7)
    ax.loglog(hs, cds2_errors, "r--s", label="CDS2", linewidth=1.8, markersize=7)

    ref2 = cds2_errors[0] * (hs / hs[0]) ** 2
    ref6 = ccd_errors[0]  * (hs / hs[0]) ** 6
    ax.loglog(hs, ref2, color="gray", linestyle=":",  linewidth=1.0, label=r"$O(h^2)$")
    ax.loglog(hs, ref6, color="gray", linestyle="-.", linewidth=1.0, label=r"$O(h^6)$")

    Pe = 10.0
    h_stable = 2.0 / Pe
    ax.axvline(x=h_stable, color="purple", linestyle="--", linewidth=1.4,
               label=f"$Pe\\cdot h=2$ (CDS2 stability limit)")

    for k in range(len(ccd_orders)):
        hmid = np.sqrt(hs[k] * hs[k + 1])
        ax.annotate(f"p={ccd_orders[k]:.1f}",
                    xy=(hmid, np.sqrt(ccd_errors[k] * ccd_errors[k + 1])),
                    fontsize=8, color="blue", ha="center")
    for k in range(len(cds2_orders)):
        hmid = np.sqrt(hs[k] * hs[k + 1])
        ax.annotate(f"p={cds2_orders[k]:.1f}",
                    xy=(hmid, np.sqrt(cds2_errors[k] * cds2_errors[k + 1]) * 1.5),
                    fontsize=8, color="red", ha="center")

    ax.set_xlabel("Grid spacing $h$", fontsize=12)
    ax.set_ylabel(r"$L^\infty$ error in $u$", fontsize=12)
    ax.set_title(r"Case 3: Advection-Diffusion ($Pe=10$)", fontsize=13)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", ls="--", alpha=0.4)
    fig.tight_layout()

    os.makedirs("results/ccd_pseudotime/figures", exist_ok=True)
    fig.savefig("results/ccd_pseudotime/figures/case3_advdiff.png", dpi=150)
    plt.close(fig)
    print("Saved: results/ccd_pseudotime/figures/case3_advdiff.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import shutil

    c1 = case1_convergence()
    c2 = case2_parabolic()
    c3 = case3_advdiff()

    print("\n--- Generating figures ---")
    fig1_convergence(*c1)
    fig2_parabolic(*c2)
    fig3_advdiff(*c3)

    dst_dir = "paper/figures"
    os.makedirs(dst_dir, exist_ok=True)
    for fname in ["case1_convergence.png", "case2_parabolic.png", "case3_advdiff.png"]:
        src = os.path.join("results/ccd_pseudotime/figures", fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dst_dir, fname))
            print(f"Copied {src} -> {dst_dir}/{fname}")

    print("\nDone.")
