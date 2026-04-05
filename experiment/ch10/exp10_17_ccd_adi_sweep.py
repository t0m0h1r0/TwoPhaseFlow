#!/usr/bin/env python3
"""【10-17】CCD-ADI sweep: 修正三重対角前処理の収束検証.

Paper ref: §8d (defect correction + 前処理改善案)
Motivation: exp10_16 で FD 前処理 DC が全条件発散を確認。
            → CCD Eq-II の β₂ 結合を pseudo-time 前処理に取り込む。

Problem:
  ∇·(1/ρ ∇p) = q on [0,1]², Neumann BC + pin gauge.
  p* = cos(πx)cos(πy)
  ρ(x,y): circular interface (R=0.25), smoothed Heaviside.

前処理の変更点（FD Thomas → CCD-ADI）:
  FD:     (1/Δτ − L_FD_ax) δp = R
  CCD-ADI: (1/Δτ)(I + β₂T) δp − (A₂/h²)(1/ρ)δ²δp = (I + β₂T)R
  β₂ = −1/8, A₂ = 3  (CCD Eq-II 係数)

Nyquist での前処理-演算子スペクトル比:
  FD 前処理:      λ_H/λ_FD = 2.4 > 2 → 発散
  CCD-ADI 前処理: λ_H/λ_prec ≈ 1.0 → 高速収束

Sweep:
  ρ_l/ρ_g = 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000
  N = 32, 64
  c_tau = 2.0

Goal: CCD-ADI sweep が収束することを示し，FD sweep との比較で
      前処理スペクトル整合性の効果を定量化する。
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_2COL, FIGSIZE_WIDE,
)

apply_style()

OUT = experiment_dir(__file__)

# CCD Eq-II 係数 (Chu & Fan 1998, Table 1)
_BETA2 = -1.0 / 8.0
_A2    =  3.0


# ── Smoothed Heaviside ───────────────────────────────────────────────────────

def smoothed_heaviside(phi, eps):
    return 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))


# ── CCD variable-density Laplacian (O(h⁶)) ─────────────────────────────────

def eval_LH(p, rho, drho_x, drho_y, ccd, backend):
    xp = backend.xp
    p_dev = xp.asarray(p)
    dp_dx, d2p_dx2 = ccd.differentiate(p_dev, 0)
    dp_dy, d2p_dy2 = ccd.differentiate(p_dev, 1)
    dp_dx   = np.asarray(backend.to_host(dp_dx))
    dp_dy   = np.asarray(backend.to_host(dp_dy))
    d2p_dx2 = np.asarray(backend.to_host(d2p_dx2))
    d2p_dy2 = np.asarray(backend.to_host(d2p_dy2))
    return (d2p_dx2 + d2p_dy2) / rho - (drho_x * dp_dx + drho_y * dp_dy) / rho**2


# ── FD Thomas sweep (baseline — known to diverge) ───────────────────────────

def fd_thomas_sweep(rhs, rho, drho_ax, dtau, h, axis):
    """(1/Δτ − L_FD_axis) q = rhs, Neumann BC (FD 前処理, 発散確認用)."""
    f     = np.moveaxis(rhs,     axis, 0)
    rho_f = np.moveaxis(rho,     axis, 0)
    drho_f = np.moveaxis(drho_ax, axis, 0)
    dtau_f = np.moveaxis(dtau,   axis, 0)
    n = f.shape[0]
    h2 = h * h

    inv_dtau   = 1.0 / dtau_f
    inv_rho_h2 = 1.0 / (rho_f * h2)
    drho_h     = drho_f / (rho_f**2 * 2.0 * h)

    a = np.zeros_like(f); b = np.ones_like(f); c = np.zeros_like(f)
    rhs_m = f.copy()

    a[1:-1] = -inv_rho_h2[1:-1] + drho_h[1:-1]
    b[1:-1] =  inv_dtau[1:-1] + 2.0 * inv_rho_h2[1:-1]
    c[1:-1] = -inv_rho_h2[1:-1] - drho_h[1:-1]

    a[0]  = 0.0;                    b[0]  = inv_dtau[0]  + 2.0 * inv_rho_h2[0];  c[0]  = -2.0 * inv_rho_h2[0]
    a[-1] = -2.0 * inv_rho_h2[-1]; b[-1] = inv_dtau[-1] + 2.0 * inv_rho_h2[-1]; c[-1] = 0.0

    return np.moveaxis(_thomas_solve(a, b, c, rhs_m), 0, axis)


# ── CCD-ADI 修正三重対角スイープ（新提案） ──────────────────────────────────

def ccd_adi_sweep(rhs, rho, dtau, h, axis):
    """CCD-ADI 修正三重対角スイープ: (1/Δτ)(I+β₂T) − (A₂/h²)(1/ρ)δ² ] δp = (I+β₂T) R.

    CCD Eq-II の暗陽結合 β₂ を pseudo-time 前処理に取り込む。
    変形波数 λ_prec(k) ≈ λ_H(k) で前処理-演算子スペクトル比 ≈ 1 (Nyquist 含め)。

    Neumann BC: ゴーストセル反射 δp[-1]=δp[1], δp[N+1]=δp[N-1]
    対角優位性: b_i - (|a_i|+|c_i|) = 0.75/Δτ_i > 0 (全条件で安定)

    密度勾配項 (ρ'δp'/ρ²) は省略 (第一近似; 滑らかなρに対して有効)。
    """
    f      = np.moveaxis(rhs,  axis, 0)
    rho_f  = np.moveaxis(rho,  axis, 0)
    dtau_f = np.moveaxis(dtau, axis, 0)
    h2 = h * h

    inv_dtau   = 1.0 / dtau_f
    inv_rho_h2 = 1.0 / (rho_f * h2)

    a = np.zeros_like(f); b = np.zeros_like(f); c = np.zeros_like(f)
    rhs_m = np.zeros_like(f)

    # Interior (1 ≤ i ≤ N-1)
    a[1:-1] = _BETA2 * inv_dtau[1:-1] - _A2 * inv_rho_h2[1:-1]
    b[1:-1] =          inv_dtau[1:-1] + 2.0 * _A2 * inv_rho_h2[1:-1]
    c[1:-1] = _BETA2 * inv_dtau[1:-1] - _A2 * inv_rho_h2[1:-1]
    rhs_m[1:-1] = f[1:-1] + _BETA2 * (f[:-2] + f[2:])

    # Boundary i=0: Neumann, ghost δp[-1]=δp[1] → c doubled, RHS uses 2β₂R[1]
    a[0]  = 0.0
    b[0]  = inv_dtau[0]  + 2.0 * _A2 * inv_rho_h2[0]
    c[0]  = 2.0 * (_BETA2 * inv_dtau[0]  - _A2 * inv_rho_h2[0])
    rhs_m[0]  = f[0]  + 2.0 * _BETA2 * f[1]

    # Boundary i=N: Neumann, ghost δp[N+1]=δp[N-1] → a doubled, RHS uses 2β₂R[N-1]
    a[-1] = 2.0 * (_BETA2 * inv_dtau[-1] - _A2 * inv_rho_h2[-1])
    b[-1] = inv_dtau[-1] + 2.0 * _A2 * inv_rho_h2[-1]
    c[-1] = 0.0
    rhs_m[-1] = f[-1] + 2.0 * _BETA2 * f[-2]

    return np.moveaxis(_thomas_solve(a, b, c, rhs_m), 0, axis)


# ── Thomas algorithm (shared) ────────────────────────────────────────────────

def _thomas_solve(a, b, c, rhs):
    """Thomas forward-elimination + back-substitution for vectorized tridiagonal."""
    n = rhs.shape[0]
    c_p = np.zeros_like(rhs); r_p = np.zeros_like(rhs)
    c_p[0] = c[0] / b[0]
    r_p[0] = rhs[0] / b[0]
    for i in range(1, n):
        denom = b[i] - a[i] * c_p[i - 1]
        c_p[i] = c[i] / denom
        r_p[i] = (rhs[i] - a[i] * r_p[i - 1]) / denom
    q = np.empty_like(rhs)
    q[-1] = r_p[-1]
    for i in range(n - 2, -1, -1):
        q[i] = r_p[i] - c_p[i] * q[i + 1]
    return q


# ── Solvers ──────────────────────────────────────────────────────────────────

def dc_solve(rhs, rho, drho_x, drho_y, ccd, backend,
             h, c_tau, tol, maxiter, pin_dof, sweep_fn, label):
    """DC 反復: CCD 残差 + 1D sweep 前処理 (ADI).

    p ← p − δp  (pseudo-time sign: Thomas/CCD-ADI sweep は R を入力し δp を出力)
    """
    shape = rhs.shape
    p = np.zeros(shape, dtype=float)
    residuals = []
    dtau = c_tau * rho * h**2 / 2.0

    for k in range(maxiter):
        Lp = eval_LH(p, rho, drho_x, drho_y, ccd, backend)
        R  = rhs - Lp
        R.ravel()[pin_dof] = 0.0

        R_flat = R.ravel().copy()
        res = float(np.sqrt(np.dot(R_flat, R_flat)))
        residuals.append(res)

        if res < tol:
            return p, residuals, k + 1, True
        if res > 1e20 or np.isnan(res):
            return p, residuals, k + 1, False

        # x-sweep then y-sweep
        q  = sweep_fn(R,  rho, dtau, h, axis=0)
        q.ravel()[pin_dof] = 0.0
        dp = sweep_fn(q,  rho, dtau, h, axis=1)
        dp.ravel()[pin_dof] = 0.0

        p = p - dp
        p.ravel()[pin_dof] = 0.0

    return p, residuals, maxiter, False


def make_fd_sweep(drho_x, drho_y):
    """FD Thomas sweep を dc_solve の sweep_fn シグネチャに合わせるアダプタ."""
    def sweep(rhs, rho, dtau, h, axis):
        drho_ax = drho_x if axis == 0 else drho_y
        return fd_thomas_sweep(rhs, rho, drho_ax, dtau, h, axis)
    return sweep


# ── Experiment ──────────────────────────────────────────────────────────────

def run_experiment():
    backend = Backend(use_gpu=False)

    density_ratios = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    grid_sizes = [32, 64]
    c_tau  = 2.0
    tol    = 1e-10
    maxiter = 500

    all_results = {}

    for N in grid_sizes:
        h  = 1.0 / N
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd  = CCDSolver(grid, backend, bc_type="wall")
        xp   = backend.xp

        X, Y = grid.meshgrid()
        p_exact  = np.cos(np.pi * X) * np.cos(np.pi * Y)
        pin_dof  = (N // 2) * (N + 1) + (N // 2)

        phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
        eps = 1.5 * h

        print(f"\n{'='*88}")
        print(f"  N={N}, h={h:.4f}, c_tau={c_tau}, tol={tol}, maxiter={maxiter}")
        print(f"{'='*88}")
        print(f"  {'ρ_l/ρ_g':>8} | {'FD iters':>9} | {'FD res':>12} | {'FD':>6} "
              f"| {'CCD-ADI iters':>14} | {'CCD-ADI res':>13} | {'CCD-ADI':>8}")
        print("  " + "-" * 90)

        for rho_ratio in density_ratios:
            rho_g = 1.0 / rho_ratio
            H     = smoothed_heaviside(phi, eps)
            rho   = 1.0 + (rho_g - 1.0) * H

            drho_x_dev, _ = ccd.differentiate(xp.asarray(rho), 0)
            drho_y_dev, _ = ccd.differentiate(xp.asarray(rho), 1)
            drho_x = np.asarray(backend.to_host(drho_x_dev))
            drho_y = np.asarray(backend.to_host(drho_y_dev))

            rhs = eval_LH(p_exact, rho, drho_x, drho_y, ccd, backend)
            rhs.ravel()[pin_dof] = 0.0

            # FD Thomas sweep (baseline)
            fd_sweep = make_fd_sweep(drho_x, drho_y)
            p_fd, res_fd, n_fd, conv_fd = dc_solve(
                rhs, rho, drho_x, drho_y, ccd, backend,
                h, c_tau, tol, maxiter, pin_dof, fd_sweep, "FD")

            # CCD-ADI sweep (new)
            p_ca, res_ca, n_ca, conv_ca = dc_solve(
                rhs, rho, drho_x, drho_y, ccd, backend,
                h, c_tau, tol, maxiter, pin_dof, ccd_adi_sweep, "CCD-ADI")

            key = f"N{N}_r{rho_ratio}"
            all_results[key] = {
                "N": N, "h": h, "rho_ratio": rho_ratio,
                "fd_iters":    n_fd,  "fd_converged":    int(conv_fd),
                "fd_final_res":    res_fd[-1] if res_fd else np.nan,
                "fd_residuals":    np.array(res_fd),
                "ccd_adi_iters":   n_ca,  "ccd_adi_converged":   int(conv_ca),
                "ccd_adi_final_res":   res_ca[-1] if res_ca else np.nan,
                "ccd_adi_residuals":   np.array(res_ca),
            }

            fd_tag  = "OK" if conv_fd  else "FAIL"
            ca_tag  = "OK" if conv_ca  else "FAIL"
            print(f"  {rho_ratio:>8} | {n_fd:>9} | {res_fd[-1]:>12.3e} | {fd_tag:>6} "
                  f"| {n_ca:>14} | {res_ca[-1]:>13.3e} | {ca_tag:>8}")

    return all_results


# ── Plot ─────────────────────────────────────────────────────────────────────

def plot_results(all_results):
    import matplotlib.pyplot as plt

    grid_sizes = sorted(set(v["N"] for v in all_results.values()))

    # (a) Iteration count vs density ratio
    fig, axes = plt.subplots(1, len(grid_sizes), figsize=FIGSIZE_WIDE)
    if len(grid_sizes) == 1:
        axes = [axes]

    for idx, N in enumerate(grid_sizes):
        ax = axes[idx]
        ratios, fd_iters, ca_iters = [], [], []
        fd_conv, ca_conv = [], []

        for key, v in sorted(all_results.items()):
            if v["N"] != N:
                continue
            ratios.append(v["rho_ratio"])
            fd_iters.append(v["fd_iters"])
            ca_iters.append(v["ccd_adi_iters"])
            fd_conv.append(v["fd_converged"])
            ca_conv.append(v["ccd_adi_converged"])

        ratios   = np.array(ratios)
        fd_iters = np.array(fd_iters)
        ca_iters = np.array(ca_iters)
        fd_conv  = np.array(fd_conv)
        ca_conv  = np.array(ca_conv)

        for iters, conv, color, marker, label in [
            (fd_iters, fd_conv,  COLORS[0], "o", "DC + FD sweep (baseline)"),
            (ca_iters, ca_conv,  COLORS[1], "s", "DC + CCD-ADI sweep (proposed)"),
        ]:
            mask_ok   = conv == 1
            mask_fail = conv == 0
            if mask_ok.any():
                ax.semilogx(ratios[mask_ok], iters[mask_ok],
                            f"{marker}-", color=color, label=label, markersize=7)
            if mask_fail.any():
                ax.semilogx(ratios[mask_fail], iters[mask_fail],
                            marker, color=color, markerfacecolor="white",
                            markersize=9, markeredgewidth=2)

        ax.set_xlabel(r"$\rho_l / \rho_g$")
        ax.set_ylabel("Iterations to convergence")
        ax.set_title(f"$N = {N}$ (hollow = not converged)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("CCD-ADI vs FD sweep: iteration count")
    fig.tight_layout()
    save_figure(fig, OUT / "ccd_adi_iters_vs_ratio")

    # (b) Residual history
    fig2, axes2 = plt.subplots(2, len(grid_sizes), figsize=FIGSIZE_WIDE)
    if len(grid_sizes) == 1:
        axes2 = axes2.reshape(-1, 1)

    selected_ratios = [1, 10, 100, 1000]

    for col, N in enumerate(grid_sizes):
        for row, (key_res, title) in enumerate([
            ("fd_residuals",      "FD sweep (baseline)"),
            ("ccd_adi_residuals", "CCD-ADI sweep"),
        ]):
            ax = axes2[row, col]
            for ci, rr in enumerate(selected_ratios):
                key = f"N{N}_r{rr}"
                if key not in all_results:
                    continue
                v   = all_results[key]
                res = v[key_res]
                if len(res) == 0:
                    continue
                conv_key = key_res.replace("_residuals", "_converged")
                style = "-" if v[conv_key] else "--"
                ax.semilogy(range(1, len(res) + 1), res,
                            style, color=COLORS[ci % len(COLORS)],
                            label=rf"$\rho_l/\rho_g={rr}$")
            ax.set_xlabel("Iteration")
            ax.set_ylabel("Residual (RMS)")
            ax.set_title(f"{title} ($N={N}$)")
            ax.legend(fontsize=7)
            ax.grid(True, which="both", alpha=0.3)

    fig2.tight_layout()
    save_figure(fig2, OUT / "ccd_adi_residual_history")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = experiment_argparser("CCD-ADI sweep convergence vs FD sweep").parse_args()

    if args.plot_only:
        results = load_results(OUT / "data.npz")
        plot_results(results)
        return

    print("\n" + "=" * 88)
    print("  【10-17】CCD-ADI Sweep: 修正三重対角前処理の収束検証")
    print("=" * 88)

    all_results = run_experiment()
    save_results(OUT / "data.npz", all_results)
    plot_results(all_results)

    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
