#!/usr/bin/env python3
"""【11-4】High-Re double shear layer: DCCD stabilization test.

Paper ref: §11.4 — Advection-pressure coupling robustness

Double shear layer at Re=1000, periodic BC.
Compare CCD (ε_d=0, no filter) vs DCCD (ε_d=0.05, stabilized).
CCD should develop checkerboard oscillations; DCCD should remain stable.

Initial condition:
  u = tanh((y-π/2)/δ) for y≤π, tanh((3π/2-y)/δ) for y>π
  v = ε₀ sin(x)
  δ = π/15, ε₀ = 0.05
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "ch10"))
from exp10_10_ipc_time_accuracy import (
    SpectralPPE, SpectralHelmholtz,
    ccd_divergence, ccd_gradient, ccd_laplacian, ccd_convection,
)

OUT = pathlib.Path(__file__).resolve().parent / "results" / "highre_dccd"
OUT.mkdir(parents=True, exist_ok=True)

# D10 filter kernel (10th-order selective dissipation, same as dccd_comparison.py)
_D10_KERNEL = np.array([1, -10, 45, -120, 210, -252, 210, -120, 45, -10, 1],
                       dtype=np.float64) / 1024.0


def d10_filter_2d(f, alpha_f=0.4):
    """Apply 10th-order selective filter in both x and y (periodic)."""
    N = f.shape[0]
    result = f.copy()
    # Filter in x-direction
    for j, c in enumerate(_D10_KERNEL):
        result += alpha_f * c * np.roll(f, 5 - j, axis=0)
    # Filter in y-direction
    f2 = result.copy()
    for j, c in enumerate(_D10_KERNEL):
        result += alpha_f * c * np.roll(f2, 5 - j, axis=1)
    return result


def double_shear_ic(X, Y, delta=np.pi/15, eps0=0.05):
    """Double shear layer initial condition."""
    u = np.where(Y <= np.pi,
                 np.tanh((Y - np.pi/2) / delta),
                 np.tanh((3*np.pi/2 - Y) / delta))
    v = eps0 * np.sin(X)
    p = np.zeros_like(X)
    return u, v, p


def run_shear_layer(N, Re, T_end, dt, eps_d=0.0, label="CCD"):
    """Run double shear layer with AB2+IPC."""
    backend = Backend(use_gpu=False)
    nu = 1.0 / Re
    L = 2.0 * np.pi
    n_steps = int(T_end / dt)

    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    ppe_solver = SpectralPPE(N, L)
    helmholtz = SpectralHelmholtz(N, L)
    alpha_cn = dt * nu / 2.0

    X, Y = grid.meshgrid()
    u, v, p = double_shear_ic(X, Y)

    conv_u_prev = None
    conv_v_prev = None

    Ek_history = []
    vort_max_history = []
    blowup = False

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

        # Viscous + pressure
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

        # Apply DCCD filter if eps_d > 0
        if eps_d > 0:
            u = d10_filter_2d(u, alpha_f=eps_d * 4)  # scale: eps_d=0.05 → alpha_f=0.2
            v = d10_filter_2d(v, alpha_f=eps_d * 4)

        # Diagnostics
        h = L / N
        Ek = 0.5 * np.sum((u[:N, :N]**2 + v[:N, :N]**2)) * h**2
        Ek_history.append(Ek)

        # Check for blowup
        if np.isnan(Ek) or Ek > 1e10:
            print(f"    [{label}] BLOWUP at step {step+1}, t={t:.4f}")
            blowup = True
            break

    return {
        "label": label, "eps_d": eps_d, "N": N, "Re": Re,
        "T_end": T_end, "dt": dt, "n_steps": len(Ek_history),
        "Ek_final": Ek_history[-1] if Ek_history else np.nan,
        "Ek_history": np.array(Ek_history),
        "blowup": blowup,
        "u_final": u, "v_final": v,
    }


def _plot_highre_dccd(results, N, dt, T_end):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        r_ccd, r_dccd = results[0], results[1]
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # Energy history
        ax = axes[0]
        for r, c in [(r_ccd, 'r'), (r_dccd, 'b')]:
            t_arr = np.arange(1, len(r["Ek_history"])+1) * dt
            ax.plot(t_arr, r["Ek_history"], c, label=f'{r["label"]} (ε_d={r["eps_d"]})')
        ax.set_xlabel('$t$')
        ax.set_ylabel('$E_k$')
        ax.set_title('Kinetic Energy')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Vorticity snapshots
        for idx, r in enumerate([r_ccd, r_dccd]):
            ax = axes[idx + 1]
            if not r["blowup"] and "u_final" in r and r["u_final"] is not None:
                u_f, v_f = r["u_final"], r["v_final"]
                h = 2*np.pi / N
                dvdx = (np.roll(v_f, -1, axis=0) - np.roll(v_f, 1, axis=0)) / (2*h)
                dudy = (np.roll(u_f, -1, axis=1) - np.roll(u_f, 1, axis=1)) / (2*h)
                omega = dvdx - dudy
                ax.contourf(omega[:N, :N].T, levels=50, cmap='RdBu_r')
                ax.set_title(f'{r["label"]} (ε_d={r["eps_d"]}): ω at t={T_end}')
            else:
                ax.text(0.5, 0.5, 'BLOWUP', ha='center', va='center',
                        fontsize=20, color='red', transform=ax.transAxes)
                ax.set_title(f'{r["label"]} (ε_d={r["eps_d"]}): BLOWUP')
            ax.set_aspect('equal')

        fig.tight_layout()
        fig.savefig(OUT / "highre_dccd_comparison.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"\n  Saved: {OUT / 'highre_dccd_comparison.png'}")
    except ImportError:
        pass


def main():
    print("\n" + "=" * 80)
    print("  【11-4】High-Re Double Shear Layer: CCD vs DCCD")
    print("=" * 80 + "\n")

    N = 64
    Re = 1000.0
    T_end = 0.5
    dt = 0.002

    print(f"  N={N}, Re={Re}, T_end={T_end}, dt={dt}\n")

    # CCD (no filter)
    print("  Running CCD (ε_d=0)...")
    r_ccd = run_shear_layer(N, Re, T_end, dt, eps_d=0.0, label="CCD")

    # DCCD (with filter)
    print("  Running DCCD (ε_d=0.05)...")
    r_dccd = run_shear_layer(N, Re, T_end, dt, eps_d=0.05, label="DCCD")

    # Summary
    print(f"\n  {'Scheme':>8} {'ε_d':>6} {'Steps':>8} {'E_k(final)':>14} {'Status':>10}")
    print("  " + "-" * 55)
    for r in [r_ccd, r_dccd]:
        status = "BLOWUP" if r["blowup"] else "STABLE"
        print(f"  {r['label']:>8} {r['eps_d']:>6.2f} {r['n_steps']:>8} "
              f"{r['Ek_final']:>14.6e} {status:>10}")

    # Save plot
    _plot_highre_dccd([r_ccd, r_dccd], N, dt, T_end)

    # Save LaTeX table
    with open(OUT / "table_highre_dccd.tex", "w") as fp:
        fp.write("% Auto-generated by exp11_6_highre_dccd.py\n")
        fp.write("\\begin{tabular}{lcrrc}\n\\toprule\n")
        fp.write("スキーム & $\\varepsilon_d$ & ステップ数 & $E_k(T)$ & 状態 \\\\\n")
        fp.write("\\midrule\n")
        for r in [r_ccd, r_dccd]:
            status = "発散" if r["blowup"] else "安定"
            fp.write(f"{r['label']} & ${r['eps_d']:.2f}$ & {r['n_steps']} "
                     f"& ${r['Ek_final']:.4e}$ & {status} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {OUT / 'table_highre_dccd.tex'}")

    # Save data for --plot-only
    np.savez(OUT / "highre_dccd_data.npz",
             r_ccd={k: v for k, v in r_ccd.items() if k != "u_final" and k != "v_final"},
             r_dccd={k: v for k, v in r_dccd.items() if k != "u_final" and k != "v_final"},
             r_ccd_u_final=r_ccd.get("u_final"),
             r_ccd_v_final=r_ccd.get("v_final"),
             r_dccd_u_final=r_dccd.get("u_final"),
             r_dccd_v_final=r_dccd.get("v_final"),
             N=N, dt=dt, T_end=T_end)
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "highre_dccd_data.npz", allow_pickle=True)
        _r_ccd = _d["r_ccd"].item()
        _r_dccd = _d["r_dccd"].item()
        _u_ccd = _d["r_ccd_u_final"]
        if _u_ccd is not None and _u_ccd.ndim > 0:
            _r_ccd["u_final"] = _u_ccd
            _r_ccd["v_final"] = _d["r_ccd_v_final"]
        _u_dccd = _d["r_dccd_u_final"]
        if _u_dccd is not None and _u_dccd.ndim > 0:
            _r_dccd["u_final"] = _u_dccd
            _r_dccd["v_final"] = _d["r_dccd_v_final"]
        _plot_highre_dccd([_r_ccd, _r_dccd], int(_d["N"]), float(_d["dt"]), float(_d["T_end"]))
    else:
        main()
