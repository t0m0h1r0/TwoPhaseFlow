#!/usr/bin/env python3
"""【11-13】IPC + Hermite extension: Galilean invariance recovery.

Paper ref: §11.4d (sec:hermite_galilean_recovery)

Demonstrates that applying ClosestPointExtender to p^n before computing
∇p^n in the IPC predictor resolves the 2-step blowup observed in §11.4b
(exp11_10, Test B: moving droplet with surface tension).

Key difference from exp11_10 Test B:
  Before:  ∇p^n computed directly (CCD across interface jump → O(1) error → blowup)
  After:   p^n_ext = Hermite5(p^n, φ) → ∇p^n_ext (smooth within each phase → O(h⁶))

Setup: circular droplet R=0.25, u₀=(U,0), periodic BC, ρ_l/ρ_g=2, We=10.
T = L/U (one full period).

Also generates a figure comparing with/without Hermite extension.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.closest_point_extender import ClosestPointExtender
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "hermite_galilean"
OUT.mkdir(parents=True, exist_ok=True)


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE via FVM direct LU."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def run_hermite_galilean(N, rho_l, rho_g, U=1.0, We=10.0,
                         use_hermite=True, n_periods=1):
    """Run Galilean invariance test with/without Hermite extension of p^n."""
    backend = Backend(use_gpu=False)
    L = 1.0
    h = L / N
    eps = 1.5 * h
    dt = 0.2 * h / max(U, 1e-10)
    T = n_periods * L / U
    n_steps = int(np.ceil(T / dt))
    dt = T / n_steps

    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='periodic')
    ppe_builder = PPEBuilder(backend, grid, bc_type='periodic')
    curv_calc = CurvatureCalculator(backend, ccd, eps)
    ls_advection = DissipativeCCDAdvection(backend, grid, ccd)
    extender = ClosestPointExtender(backend, grid, ccd) if use_hermite else None

    X, Y = grid.meshgrid()
    R = 0.25
    sigma = 1.0
    xc, yc = 0.5, 0.5

    # Initial conditions
    phi = R - np.sqrt((X - xc)**2 + (Y - yc)**2)  # φ > 0 inside liquid
    psi = np.asarray(heaviside(np, phi, eps))
    psi_0 = psi.copy()
    rho = rho_g + (rho_l - rho_g) * psi

    u = np.full_like(X, U)
    v = np.zeros_like(X)

    mass_0 = float(np.sum(psi) * h**2)
    dp_exact = sigma / (R * We)

    # Warm-start pressure via single-step projection
    kappa = curv_calc.compute(psi)
    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_x = (sigma / We) * kappa * np.asarray(dpsi_dx)
    f_y = (sigma / We) * kappa * np.asarray(dpsi_dy)
    u_tmp = u + dt / rho * f_x
    v_tmp = v + dt / rho * f_y
    du, _ = ccd.differentiate(u_tmp, 0)
    dv, _ = ccd.differentiate(v_tmp, 1)
    rhs = (np.asarray(du) + np.asarray(dv)) / dt
    p = _solve_ppe(rhs, rho, ppe_builder)

    u_para_history = []
    dp_history = []
    mass_history = []

    for step in range(n_steps):
        # 1. Advect ψ
        psi = ls_advection.advance(psi, [u, v], dt)
        psi = np.asarray(psi)
        rho = rho_g + (rho_l - rho_g) * psi

        # Recompute φ from ψ for Hermite extension
        # ψ ∈ [0,1] → approximate φ via inverse Heaviside
        # Simple approximation: φ ≈ eps * (2ψ - 1) / max(|2ψ-1|, δ)
        # More robust: use the advected ψ contour ψ=0.5 to estimate SDF
        phi_approx = eps * (2 * psi - 1)

        # 2. CSF body force
        kappa = curv_calc.compute(psi)
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
        f_csf_x = (sigma / We) * kappa * np.asarray(dpsi_dx)
        f_csf_y = (sigma / We) * kappa * np.asarray(dpsi_dy)

        # 3. IPC Predictor with Hermite-extended pressure gradient
        p_for_grad = p
        if extender is not None:
            try:
                # Extend p from liquid (φ > 0 = inside) into gas (φ < 0)
                # Note: ClosestPointExtender extends from φ<0 to φ≥0,
                # so we need to pass -phi_approx to extend from liquid outward
                p_ext = extender.extend(p, -phi_approx)
                p_for_grad = np.asarray(p_ext)
            except Exception as e:
                print(f"    Hermite extension failed at step {step}: {e}")
                pass

        dp_dx, _ = ccd.differentiate(p_for_grad, 0)
        dp_dy, _ = ccd.differentiate(p_for_grad, 1)
        u_star = u + dt / rho * (f_csf_x - np.asarray(dp_dx))
        v_star = v + dt / rho * (f_csf_y - np.asarray(dp_dy))

        # 4. PPE
        du_dx, _ = ccd.differentiate(u_star, 0)
        dv_dy, _ = ccd.differentiate(v_star, 1)
        rhs = (np.asarray(du_dx) + np.asarray(dv_dy)) / dt
        delta_p = _solve_ppe(rhs, rho, ppe_builder)

        # 5. Corrector
        ddp_dx, _ = ccd.differentiate(delta_p, 0)
        ddp_dy, _ = ccd.differentiate(delta_p, 1)
        u = u_star - dt / rho * np.asarray(ddp_dx)
        v = v_star - dt / rho * np.asarray(ddp_dy)
        p = p + delta_p

        # Diagnostics
        u_para = np.sqrt((u - U)**2 + v**2)
        u_para_max = float(np.max(u_para))

        inside  = psi > 0.9
        outside = psi < 0.1
        if np.any(inside) and np.any(outside):
            dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
        else:
            dp_meas = float('nan')

        mass = float(np.sum(psi) * h**2)
        mass_err = abs(mass - mass_0) / max(mass_0, 1e-16)

        u_para_history.append(u_para_max)
        dp_history.append(dp_meas)
        mass_history.append(mass_err)

        if np.isnan(u_para_max) or u_para_max > 1e3:
            print(f"    [N={N}, hermite={use_hermite}] BLOWUP at step {step+1}/{n_steps}")
            break

    dp_final = dp_history[-1] if dp_history else float('nan')
    dp_rel_err = abs(dp_final - dp_exact) / dp_exact if not np.isnan(dp_final) else float('nan')
    shape_err = float(np.max(np.abs(psi - psi_0)))
    stable = not np.isnan(u_para_history[-1]) and u_para_history[-1] < 1e1

    return {
        "N": N, "rho_ratio": rho_l / rho_g, "U": U,
        "use_hermite": use_hermite,
        "n_steps_completed": len(u_para_history),
        "n_steps_target": n_steps,
        "u_para_peak": max(u_para_history),
        "u_para_final": u_para_history[-1],
        "dp_rel_err": dp_rel_err,
        "mass_err_final": mass_history[-1],
        "shape_err": shape_err,
        "stable": stable,
        "u_para_history": np.array(u_para_history),
    }


def _plot_hermite_galilean(all_results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 1, figsize=(8, 5))

        for r in all_results:
            if r["N"] == 64:
                label = f"{'Hermite IPC' if r['use_hermite'] else 'Raw IPC'} (N={r['N']})"
                style = '-' if r['use_hermite'] else '--'
                color = 'steelblue' if r['use_hermite'] else 'salmon'
                t_arr = np.arange(1, len(r['u_para_history']) + 1) * (1.0 / r['n_steps_target'])
                ax.semilogy(t_arr, r['u_para_history'], style, color=color,
                           label=label, linewidth=2)

        ax.set_xlabel('$t / T$')
        ax.set_ylabel('$\\|\\mathbf{u}_{\\mathrm{para}}\\|_\\infty$')
        ax.set_title('Galilean invariance: Raw IPC vs Hermite IPC ($\\rho_l/\\rho_g=2$, $We=10$, $N=64$)')
        ax.legend()
        ax.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig(OUT / "hermite_galilean_comparison.pdf", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved: {OUT / 'hermite_galilean_comparison.pdf'}")
    except ImportError:
        pass


def main():
    print("\n" + "=" * 80)
    print("  【11-13】IPC + Hermite Extension: Galilean Recovery (§11.4d)")
    print("=" * 80 + "\n")

    Ns = [64, 128]
    rho_l, rho_g = 2.0, 1.0
    all_results = []

    for use_hermite in [False, True]:
        label = "WITH Hermite" if use_hermite else "WITHOUT Hermite (baseline)"
        print(f"\n  === {label} ===")
        print(f"  {'N':>5} | {'steps':>6} | {'||u_para||∞':>12} | {'Δp_err':>8} | "
              f"{'mass_err':>10} | {'stable':>7}")
        print("  " + "-" * 65)

        for N in Ns:
            r = run_hermite_galilean(N, rho_l, rho_g, use_hermite=use_hermite)
            all_results.append(r)
            dp_str = f"{r['dp_rel_err']:.1%}" if not np.isnan(r['dp_rel_err']) else "nan"
            print(f"  {N:>5} | {r['n_steps_completed']:>6} | "
                  f"{r['u_para_final']:>12.3e} | {dp_str:>8} | "
                  f"{r['mass_err_final']:>10.3e} | "
                  f"{'YES' if r['stable'] else 'NO':>7}")

    # ── Save LaTeX table ──
    with open(OUT / "table_hermite_galilean.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_13_hermite_galilean.py\n")
        fp.write("\\begin{tabular}{llrcccl}\n\\toprule\n")
        fp.write("手法 & $N$ & ステップ & "
                 "$\\|\\bu_{\\mathrm{para}}\\|_\\infty$ & "
                 "$\\Delta p$ 相対誤差 & 質量誤差 & 安定 \\\\\n")
        fp.write("\\midrule\n")
        for r in all_results:
            method = "Hermite IPC" if r["use_hermite"] else "Raw IPC"
            dp_str = f"${r['dp_rel_err']:.1e}$" if not np.isnan(r['dp_rel_err']) else "---"
            stable = "○" if r["stable"] else "×（発散）"
            fp.write(f"{method} & {r['N']} & {r['n_steps_completed']} & "
                     f"${r['u_para_final']:.2e}$ & {dp_str} & "
                     f"${r['mass_err_final']:.2e}$ & {stable} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_hermite_galilean.tex'}")

    # ── Plot ──
    _plot_hermite_galilean(all_results)

    np.savez(OUT / "hermite_galilean_data.npz",
             results=[{k: v for k, v in r.items() if k != 'u_para_history'} for r in all_results],
             **{f"u_para_hist_{i}": np.array(r['u_para_history']) for i, r in enumerate(all_results)})
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "hermite_galilean_data.npz", allow_pickle=True)
        _results = list(_d["results"])
        for _i, _r in enumerate(_results):
            _r = dict(_r.item()) if hasattr(_r, 'item') else dict(_r)
            _r['u_para_history'] = list(_d[f"u_para_hist_{_i}"])
            _results[_i] = _r
        _plot_hermite_galilean(_results)
    else:
        main()
