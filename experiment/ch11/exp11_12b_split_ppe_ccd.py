#!/usr/bin/env python3
"""exp11_12b  Split-PPE + CCD DC k=3: density-ratio-independent high-order PPE.

Paper ref: §11.3 (sec:verify_split_ppe_dc)

Three-way comparison on manufactured solution p* = sin(pi*x)*sin(pi*y)
with a circular interface (R=0.25, smoothed Heaviside, eps=1.5*h):

  (a) Monolithic DC k=3 (variable-density CCD L_H + FD L_L):
      RHS via CCD product rule: (1/rho)*Lap(p*) - (1/rho^2)*(grad rho . grad p*)
      Expected: diverges at rho_l/rho_g >= 10

  (b) Split-PPE + FD direct (constant-density Laplacian, spsolve):
      RHS: Lap(p*) = -2*pi^2 * sin(pi*x)*sin(pi*y)
      Expected: O(h^2) for all density ratios

  (c) Split-PPE + CCD DC k=3 (constant-density CCD L_H + FD L_L):
      RHS: Lap(p*) = -2*pi^2 * sin(pi*x)*sin(pi*y)
      Expected: O(h^7) Dirichlet for all density ratios

Key insight: Split-PPE eliminates variable-density stencils entirely.
Each phase solves a constant-density Poisson, so DC k=3 recovers full
CCD accuracy regardless of density ratio.

Sweep
-----
  Density ratios: 1, 2, 5, 10, 100, 1000  (N = 64)
  Grid convergence: N = 8, 16, 32, 64, 128  at rho_l/rho_g = 10 and 1000
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__, "12b_split_ppe_ccd")
R = 0.25


def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


# ── CCD operators ─────────────────────────────────────────────────────────

def eval_LH_const(p, ccd, backend):
    """Constant-density Laplacian via CCD O(h^6): Lap(p) = sum_ax d2p/dx_ax^2."""
    xp = backend.xp
    p_dev = xp.asarray(p)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        _, d2p = ccd.differentiate(p_dev, ax)
        Lp += d2p
    return np.asarray(backend.to_host(Lp))


def eval_LH_varrho(p, rho, ccd, backend):
    """Variable-density Laplacian via CCD O(h^6): (1/rho)*Lap(p) - (1/rho^2)*(grad rho . grad p)."""
    xp = backend.xp
    p_dev = xp.asarray(p); rho_dev = xp.asarray(rho)
    Lp = xp.zeros_like(p_dev)
    for ax in range(2):
        dp, d2p = ccd.differentiate(p_dev, ax)
        drho, _ = ccd.differentiate(rho_dev, ax)
        Lp += d2p / rho_dev - (drho / rho_dev**2) * dp
    return np.asarray(backend.to_host(Lp))


# ── FD matrices ───────────────────────────────────────────────────────────

def build_fd_laplacian_dirichlet(N, h, backend):
    """FD 5-point for Lap(p), Dirichlet BC (constant-density)."""
    import scipy.sparse as sp_cpu
    nx = ny = N + 1; n = nx * ny
    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    rows.append(k); cols.append((i + di) * ny + (j + dj))
                    vals.append(1.0 / h**2)
                rows.append(k); cols.append(k); vals.append(-4.0 / h**2)
    A_cpu = sp_cpu.csr_matrix(
        (np.array(vals), (np.array(rows), np.array(cols))), shape=(n, n))
    return backend.sparse.csr_matrix(A_cpu)


def build_fd_varrho_dirichlet(N, h, rho, backend):
    """FD for (1/rho)*Lap(p) - (1/rho^2)*(grad rho . grad p), Dirichlet BC."""
    rho = backend.to_host(rho)  # sparse assembly on CPU
    nx = ny = N + 1; n = nx * ny
    drho_dx = np.zeros_like(rho); drho_dy = np.zeros_like(rho)
    for i in range(1, N):
        drho_dx[i, :] = (rho[i + 1, :] - rho[i - 1, :]) / (2 * h)
    for j in range(1, N):
        drho_dy[:, j] = (rho[:, j + 1] - rho[:, j - 1]) / (2 * h)

    rows, cols, vals = [], [], []
    for i in range(nx):
        for j in range(ny):
            k = i * ny + j
            if i == 0 or i == N or j == 0 or j == N:
                rows.append(k); cols.append(k); vals.append(1.0)
            else:
                inv_rho = 1.0 / rho[i, j]
                cx = drho_dx[i, j] / rho[i, j]**2
                cy = drho_dy[i, j] / rho[i, j]**2
                rows.append(k); cols.append((i + 1) * ny + j)
                vals.append(inv_rho / h**2 - cx / (2 * h))
                rows.append(k); cols.append((i - 1) * ny + j)
                vals.append(inv_rho / h**2 + cx / (2 * h))
                rows.append(k); cols.append(i * ny + (j + 1))
                vals.append(inv_rho / h**2 - cy / (2 * h))
                rows.append(k); cols.append(i * ny + (j - 1))
                vals.append(inv_rho / h**2 + cy / (2 * h))
                center = -4.0 * inv_rho / h**2
                rows.append(k); cols.append(k); vals.append(center)
    import scipy.sparse as sp_cpu
    A_cpu = sp_cpu.csr_matrix(
        (np.array(vals, dtype=np.float64),
         (np.array(rows, dtype=np.int32), np.array(cols, dtype=np.int32))),
        shape=(n, n))
    return backend.sparse.csr_matrix(A_cpu)


# ── DC iteration ──────────────────────────────────────────────────────────

def defect_correction_const(rhs, ccd, backend, L_L, k_max):
    """DC k iterations on constant-density Laplacian (Dirichlet BC)."""
    spsolve = backend.sparse_linalg.spsolve
    p = np.zeros_like(rhs)
    for _ in range(k_max):
        Lp = eval_LH_const(p, ccd, backend)
        d = rhs - Lp
        d[0, :] = 0; d[-1, :] = 0; d[:, 0] = 0; d[:, -1] = 0
        dp = np.asarray(backend.to_host(spsolve(L_L, backend.xp.asarray(d.ravel())))).reshape(rhs.shape)
        p = p + dp
        p[0, :] = 0; p[-1, :] = 0; p[:, 0] = 0; p[:, -1] = 0
    return p


def defect_correction_varrho(rhs, rho, ccd, backend, L_L, k_max):
    """DC k iterations on variable-density operator (Dirichlet BC)."""
    spsolve = backend.sparse_linalg.spsolve
    p = np.zeros_like(rhs)
    for _ in range(k_max):
        Lp = eval_LH_varrho(p, rho, ccd, backend)
        d = rhs - Lp
        d[0, :] = 0; d[-1, :] = 0; d[:, 0] = 0; d[:, -1] = 0
        dp = np.asarray(backend.to_host(spsolve(L_L, backend.xp.asarray(d.ravel())))).reshape(rhs.shape)
        p = p + dp
        p[0, :] = 0; p[-1, :] = 0; p[:, 0] = 0; p[:, -1] = 0
    return p


# ── Experiment core ───────────────────────────────────────────────────────

def run_comparison(N, rho_ratio, k_dc=3):
    """Run three-way comparison at given N and density ratio."""
    backend = Backend()
    h = 1.0 / N; eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    X_dev, Y_dev = grid.meshgrid()
    X = np.asarray(backend.to_host(X_dev))
    Y = np.asarray(backend.to_host(Y_dev))

    # Manufactured solution (Dirichlet: p*=0 on boundary)
    p_star = np.sin(np.pi * X) * np.sin(np.pi * Y)

    # Level-set and density
    phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)  # phi>0 = liquid
    rho_g = 1.0 / rho_ratio
    H = smoothed_heaviside(phi, eps)
    rho = 1.0 + (rho_g - 1.0) * (1.0 - H)  # rho_l=1 inside, rho_g outside

    # Liquid interior mask (well inside interface)
    liquid_mask = phi > 3 * h

    # ── (a) Monolithic DC k=3 (variable-density) ──
    rhs_var = eval_LH_varrho(p_star, rho, ccd, backend)
    rhs_var[0, :] = 0; rhs_var[-1, :] = 0; rhs_var[:, 0] = 0; rhs_var[:, -1] = 0
    A_var = build_fd_varrho_dirichlet(N, h, rho, backend)
    try:
        p_mono = defect_correction_varrho(rhs_var, rho, ccd, backend, A_var, k_dc)
        err_mono = float(np.max(np.abs(p_mono - p_star)))
        err_mono_liq = float(np.max(np.abs((p_mono - p_star)[liquid_mask]))) \
            if np.any(liquid_mask) else err_mono
    except Exception:
        err_mono = float("inf"); err_mono_liq = float("inf")

    # ── (b) Split-PPE + FD direct (constant-density) ──
    rhs_lap = -2.0 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
    rhs_lap_flat = rhs_lap.ravel().copy()
    for i in range(N + 1):
        for j in range(N + 1):
            if i == 0 or i == N or j == 0 or j == N:
                rhs_lap_flat[i * (N + 1) + j] = 0.0
    A_lap = build_fd_laplacian_dirichlet(N, h, backend)
    p_fd = np.asarray(backend.to_host(
        backend.sparse_linalg.spsolve(A_lap, backend.xp.asarray(rhs_lap_flat))
    )).reshape(p_star.shape)
    err_fd = float(np.max(np.abs(p_fd - p_star)))
    err_fd_liq = float(np.max(np.abs((p_fd - p_star)[liquid_mask]))) \
        if np.any(liquid_mask) else err_fd

    # ── (c) Split-PPE + CCD DC k=3 (constant-density) ──
    rhs_dc = rhs_lap.copy()
    rhs_dc[0, :] = 0; rhs_dc[-1, :] = 0; rhs_dc[:, 0] = 0; rhs_dc[:, -1] = 0
    p_dc = defect_correction_const(rhs_dc, ccd, backend, A_lap, k_dc)
    err_dc = float(np.max(np.abs(p_dc - p_star)))
    err_dc_liq = float(np.max(np.abs((p_dc - p_star)[liquid_mask]))) \
        if np.any(liquid_mask) else err_dc

    return {
        "N": N, "h": h, "rho_ratio": float(rho_ratio),
        "err_mono": err_mono, "err_mono_liq": err_mono_liq,
        "err_fd": err_fd, "err_fd_liq": err_fd_liq,
        "err_dc": err_dc, "err_dc_liq": err_dc_liq,
    }


def compute_rates(results, key):
    rates = []
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0[key] > 0 and r1[key] > 0 and np.isfinite(r0[key]) and np.isfinite(r1[key]):
            rates.append(np.log(r0[key] / r1[key]) / np.log(r0["h"] / r1["h"]))
        else:
            rates.append(float("nan"))
    return rates


# ── Sweep routines ────────────────────────────────────────────────────────

def run_sweep():
    """Density ratio sweep at N=64."""
    ratios = [1, 2, 5, 10, 100, 1000]
    results = []
    for dr in ratios:
        r = run_comparison(64, dr)
        results.append(r)
        mono_s = f"{r['err_mono_liq']:.2e}" if np.isfinite(r['err_mono_liq']) else "diverged"
        print(f"  rho={dr:>5}: mono={mono_s}"
              f"  fd={r['err_fd_liq']:.2e}  dc={r['err_dc_liq']:.2e}")
    return results


def run_convergence(rho_ratio):
    """Grid convergence at given density ratio."""
    Ns = [8, 16, 32, 64, 128]
    results = []
    for N in Ns:
        r = run_comparison(N, rho_ratio)
        results.append(r)
    return results


# ── Plotting ──────────────────────────────────────────────────────────────

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def make_figures(sweep, conv_10, conv_1000):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # ── Left: Error vs density ratio (N=64) ──
    ax = axes[0]
    ratios = [r["rho_ratio"] for r in sweep]
    err_m = [r["err_mono_liq"] for r in sweep]
    err_f = [r["err_fd_liq"] for r in sweep]
    err_d = [r["err_dc_liq"] for r in sweep]

    # Clip inf for plotting
    err_m_plot = [e if np.isfinite(e) else None for e in err_m]

    ax.semilogy(ratios, err_m_plot, f"{MARKERS[0]}-", color=COLORS[0],
                linewidth=1.5, markersize=7, label="Monolithic DC $k{=}3$")
    ax.semilogy(ratios, err_f, f"{MARKERS[1]}--", color=COLORS[1],
                linewidth=1.5, markersize=7, label=r"Split-PPE + FD")
    ax.semilogy(ratios, err_d, f"{MARKERS[2]}:", color=COLORS[2],
                linewidth=1.5, markersize=7, label=r"Split-PPE + DC $k{=}3$")
    ax.set_xlabel(r"$\rho_l/\rho_g$")
    ax.set_ylabel(r"$L^\infty$ error (liquid interior)")
    ax.set_title(r"PPE accuracy ($N=64$)")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_xscale("log")

    # ── Middle: Grid convergence at rho=10 ──
    _plot_convergence(axes[1], conv_10, r"$\rho_l/\rho_g = 10$")

    # ── Right: Grid convergence at rho=1000 ──
    _plot_convergence(axes[2], conv_1000, r"$\rho_l/\rho_g = 1000$")

    fig.tight_layout()
    save_figure(fig, OUT / "split_ppe_dc_comparison")


def _plot_convergence(ax, conv, title):
    hs = [r["h"] for r in conv]
    err_m = [r["err_mono_liq"] for r in conv]
    err_f = [r["err_fd_liq"] for r in conv]
    err_d = [r["err_dc_liq"] for r in conv]

    err_m_plot = [e if np.isfinite(e) else None for e in err_m]

    ax.loglog(hs, err_m_plot, f"{MARKERS[0]}-", color=COLORS[0],
              linewidth=1.5, markersize=7, label="Monolithic DC $k{=}3$")
    ax.loglog(hs, err_f, f"{MARKERS[1]}--", color=COLORS[1],
              linewidth=1.5, markersize=7, label="Split-PPE + FD")
    ax.loglog(hs, err_d, f"{MARKERS[2]}:", color=COLORS[2],
              linewidth=1.5, markersize=7, label=r"Split-PPE + DC $k{=}3$")

    # Reference slopes
    h_ref = np.array([hs[0], hs[-1]])
    ax.loglog(h_ref, err_f[0] * (h_ref / h_ref[0])**2,
              "k:", alpha=0.3, label=r"$O(h^2)$")
    ax.loglog(h_ref, err_d[0] * (h_ref / h_ref[0])**7,
              "k-.", alpha=0.3, label=r"$O(h^7)$")

    ax.set_xlabel("$h$"); ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title(f"Grid convergence ({title})")
    ax.legend(fontsize=6); ax.grid(True, alpha=0.3, which="both")
    ax.invert_xaxis()


# ── Serialization helpers ─────────────────────────────────────────────────

def _flatten_list(results, prefix):
    flat = {}
    keys = ["N", "h", "rho_ratio", "err_mono", "err_mono_liq",
            "err_fd", "err_fd_liq", "err_dc", "err_dc_liq"]
    for i, r in enumerate(results):
        for k in keys:
            flat[f"{prefix}__r{i}_{k}"] = r[k]
    flat[f"n_{prefix}"] = len(results)
    return flat


def _rebuild_list(data, prefix, n):
    keys = ["N", "h", "rho_ratio", "err_mono", "err_mono_liq",
            "err_fd", "err_fd_liq", "err_dc", "err_dc_liq"]
    results = []
    for i in range(n):
        r = {}
        for k in keys:
            full = f"{prefix}__r{i}_{k}"
            if full in data:
                r[k] = float(data[full])
        results.append(r)
    return results


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser("Split-PPE + DC k=3 recovery test").parse_args()
    if args.plot_only:
        d = load_results(OUT / "split_ppe_ccd.npz")
        n_sweep = int(d["n_sweep"])
        n_conv_10 = int(d["n_conv_10"])
        n_conv_1000 = int(d["n_conv_1000"])
        sweep = _rebuild_list(d, "sweep", n_sweep)
        conv_10 = _rebuild_list(d, "conv_10", n_conv_10)
        conv_1000 = _rebuild_list(d, "conv_1000", n_conv_1000)
        make_figures(sweep, conv_10, conv_1000)
        return

    print("\n" + "=" * 70)
    print("  exp11_12b  Split-PPE + CCD DC k=3 (density-ratio-independent)")
    print("=" * 70)

    # ── Density sweep ──
    print("\n  Density sweep (N=64):")
    sweep = run_sweep()

    # ── Grid convergence ──
    for rho_ratio in [10, 1000]:
        print(f"\n  Grid convergence (rho_l/rho_g = {rho_ratio}):")
        conv = run_convergence(rho_ratio)
        for r in conv:
            mono_s = f"{r['err_mono_liq']:.4e}" if np.isfinite(r['err_mono_liq']) else "diverged"
            print(f"    N={r['N']:>3}: mono={mono_s}"
                  f"  fd={r['err_fd_liq']:.4e}  dc={r['err_dc_liq']:.4e}")
        rates_f = compute_rates(conv, "err_fd_liq")
        rates_d = compute_rates(conv, "err_dc_liq")
        for i, (rf, rd) in enumerate(zip(rates_f, rates_d)):
            print(f"      N={conv[i]['N']}→{conv[i+1]['N']}:"
                  f" fd={rf:.2f}  dc={rd:.2f}")

    conv_10 = run_convergence(10)
    conv_1000 = run_convergence(1000)

    # ── Save ──
    flat = {}
    flat.update(_flatten_list(sweep, "sweep"))
    flat.update(_flatten_list(conv_10, "conv_10"))
    flat.update(_flatten_list(conv_1000, "conv_1000"))
    save_results(OUT / "split_ppe_ccd.npz", flat)

    make_figures(sweep, conv_10, conv_1000)
    print(f"\n  Results saved to {OUT}")


if __name__ == "__main__":
    main()
