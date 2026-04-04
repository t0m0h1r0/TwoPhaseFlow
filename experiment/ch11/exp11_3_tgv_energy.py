#!/usr/bin/env python3
"""【11-2】Taylor-Green vortex energy conservation and divergence-free test.

Paper ref: §11.2 — Conservation properties

Verifies:
  1. Kinetic energy decay E_k(t) = E_k(0) * exp(-4νt) (viscous dissipation)
  2. Divergence-free constraint ||∇·u||_inf < 10^{-10} at all times

Uses the same AB2+IPC+spectral-PPE infrastructure as exp10_10.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver

# Reuse TGV infrastructure from ch10
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "ch10"))
from exp10_10_ipc_time_accuracy import (
    tgv_exact, SpectralPPE, SpectralHelmholtz,
    ccd_divergence, ccd_gradient, ccd_laplacian, ccd_convection,
)

OUT = pathlib.Path(__file__).resolve().parent / "results" / "tgv_energy"
OUT.mkdir(parents=True, exist_ok=True)


def run_tgv_energy(N=64, T_end=2.0, Re=100.0, dt=0.01):
    """Run TGV and record energy + divergence at each step."""
    backend = Backend(use_gpu=False)
    nu = 1.0 / Re
    L = 2.0 * np.pi
    h = L / N
    n_steps = int(T_end / dt)

    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    ppe_solver = SpectralPPE(N, L)
    helmholtz = SpectralHelmholtz(N, L)
    alpha_cn = dt * nu / 2.0

    X, Y = grid.meshgrid()
    u, v, p = tgv_exact(X, Y, 0.0, nu)

    # Cell area for energy integration
    cell_area = h * h

    conv_u_prev = None
    conv_v_prev = None

    times = [0.0]
    Ek_numerical = [0.5 * np.sum((u**2 + v**2)[:N, :N]) * cell_area]
    Ek_exact = [Ek_numerical[0]]
    div_inf = [np.max(np.abs(ccd_divergence(u, v, ccd, backend)))]

    for step in range(n_steps):
        t = (step + 1) * dt

        # Convection
        conv_u, conv_v = ccd_convection(u, v, ccd, backend)
        if conv_u_prev is not None:
            ab2_u = 1.5 * conv_u - 0.5 * conv_u_prev
            ab2_v = 1.5 * conv_v - 0.5 * conv_v_prev
        else:
            ab2_u = conv_u
            ab2_v = conv_v
        conv_u_prev = conv_u.copy()
        conv_v_prev = conv_v.copy()

        # Viscous (explicit half) + pressure gradient
        visc_u = nu * ccd_laplacian(u, ccd, backend)
        visc_v = nu * ccd_laplacian(v, ccd, backend)
        dp_dx, dp_dy = ccd_gradient(p, ccd, backend)

        rhs_u = u + dt * (-ab2_u + 0.5 * visc_u - dp_dx)
        rhs_v = v + dt * (-ab2_v + 0.5 * visc_v - dp_dy)

        u_star = helmholtz.solve(rhs_u, alpha_cn)
        v_star = helmholtz.solve(rhs_v, alpha_cn)

        # PPE + corrector
        div_star = ccd_divergence(u_star, v_star, ccd, backend)
        delta_p = ppe_solver.solve(div_star / dt)
        ddp_dx, ddp_dy = ccd_gradient(delta_p, ccd, backend)
        u = u_star - dt * ddp_dx
        v = v_star - dt * ddp_dy
        p = p + delta_p

        # Record diagnostics
        Ek_num = 0.5 * np.sum((u**2 + v**2)[:N, :N]) * cell_area
        Ek_ex = Ek_numerical[0] * np.exp(-4.0 * nu * t)
        div_max = np.max(np.abs(ccd_divergence(u, v, ccd, backend)))

        times.append(t)
        Ek_numerical.append(Ek_num)
        Ek_exact.append(Ek_ex)
        div_inf.append(div_max)

    return np.array(times), np.array(Ek_numerical), np.array(Ek_exact), np.array(div_inf)


def _plot_tgv_energy(times, Ek_num, Ek_ex, div_inf, N, Re):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))

        ax1.plot(times, Ek_num, 'b-', label='Numerical $E_k$', linewidth=1.5)
        ax1.plot(times, Ek_ex, 'r--', label='Exact $E_k(0) e^{-4\\nu t}$', linewidth=1.5)
        ax1.set_xlabel('$t$')
        ax1.set_ylabel('$E_k$')
        ax1.set_title(f'Taylor-Green Energy Decay (N={N}, Re={Re})')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.semilogy(times, div_inf, 'g-', linewidth=1)
        ax2.axhline(1e-10, color='r', linestyle='--', alpha=0.5, label='Tolerance $10^{-10}$')
        ax2.set_xlabel('$t$')
        ax2.set_ylabel('$\\|\\nabla \\cdot \\mathbf{u}\\|_\\infty$')
        ax2.set_title('Divergence-Free Constraint')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig(OUT / "tgv_energy_conservation.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"\n  Saved: {OUT / 'tgv_energy_conservation.png'}")
    except ImportError:
        print("  (matplotlib not available, skipping plot)")


def main():
    print("\n" + "=" * 80)
    print("  【11-2】Taylor-Green Vortex: Energy Conservation + Div-Free")
    print("=" * 80 + "\n")

    N = 64
    Re = 100.0
    T_end = 2.0
    dt = 0.01

    times, Ek_num, Ek_ex, div_inf = run_tgv_energy(N=N, T_end=T_end, Re=Re, dt=dt)

    # Report at selected times
    report_times = [0.5, 1.0, 1.5, 2.0]
    print(f"  {'t':>6} {'E_k(num)':>12} {'E_k(exact)':>12} {'rel_err':>12} {'||div u||_inf':>14}")
    print("  " + "-" * 65)
    for t_target in report_times:
        idx = np.argmin(np.abs(times - t_target))
        rel_err = abs(Ek_num[idx] - Ek_ex[idx]) / Ek_ex[idx] if Ek_ex[idx] > 0 else 0
        print(f"  {times[idx]:>6.2f} {Ek_num[idx]:>12.6e} {Ek_ex[idx]:>12.6e} "
              f"{rel_err:>12.3e} {div_inf[idx]:>14.3e}")

    # Overall metrics
    max_rel_err = np.max(np.abs(Ek_num - Ek_ex) / np.maximum(Ek_ex, 1e-30))
    max_div = np.max(div_inf)
    energy_pass = max_rel_err < 1e-4
    div_pass = max_div < 1e-10

    print(f"\n  Max relative energy error: {max_rel_err:.3e} {'PASS' if energy_pass else 'FAIL'}")
    print(f"  Max ||div u||_inf:         {max_div:.3e} {'PASS' if div_pass else 'FAIL'}")

    # Save plot
    _plot_tgv_energy(times, Ek_num, Ek_ex, div_inf, N, Re)

    # Save LaTeX table
    with open(OUT / "table_tgv_energy.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_3_tgv_energy.py\n")
        fp.write("\\begin{tabular}{rcccc}\n\\toprule\n")
        fp.write("$t$ & $E_k$（数値） & $E_k$（解析） & 相対誤差 & $\\|\\bnabla\\cdot\\bu\\|_\\infty$ \\\\\n")
        fp.write("\\midrule\n")
        for t_target in report_times:
            idx = np.argmin(np.abs(times - t_target))
            rel_err = abs(Ek_num[idx] - Ek_ex[idx]) / Ek_ex[idx]
            fp.write(f"${times[idx]:.1f}$ & ${Ek_num[idx]:.6e}$ & ${Ek_ex[idx]:.6e}$ "
                     f"& ${rel_err:.2e}$ & ${div_inf[idx]:.2e}$ \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {OUT / 'table_tgv_energy.tex'}")

    np.savez(OUT / "tgv_energy_data.npz",
             times=times, Ek_numerical=Ek_num, Ek_exact=Ek_ex, div_inf=div_inf,
             N=N, Re=Re)


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "tgv_energy_data.npz", allow_pickle=True)
        _plot_tgv_energy(
            _d["times"], _d["Ek_numerical"], _d["Ek_exact"], _d["div_inf"],
            int(_d["N"]), float(_d["Re"]),
        )
    else:
        main()
