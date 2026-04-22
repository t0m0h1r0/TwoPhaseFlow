#!/usr/bin/env python3
"""[12-6] DCCD non-invasiveness on double shear layer.

Paper ref: §12.3.3

Verifies that the DCCD dissipative filter does not degrade physical accuracy
on a double shear layer problem.  Compares kinetic energy evolution for
CCD (ε_d=0) vs DCCD (ε_d=0.05).

Setup:
  Domain : [0, 2π]², periodic, Re=1000 (ν=1e-3), T=0.5
  IC     : double shear layer (δ=π/15, ε₀=0.05)
  Grid   : N ∈ {64, 128}
  Time   : AB2 + FFT PPE, CFL-based dt (CFL=0.4)

Expected: DCCD kinetic energy closely matches CCD (small relative difference).
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
NPZ = OUT / "data.npz"

# --------------------------------------------------------------------------- #
# Physical parameters
# --------------------------------------------------------------------------- #
NU = 1e-3
T_FINAL = 0.5
L_DOM = 2.0 * np.pi
CFL = 0.4
DELTA = np.pi / 15.0
EPS0 = 0.05
N_LIST = [64, 128]
EPS_D_LIST = [0.0, 0.05]  # CCD vs DCCD


def fft_poisson(rhs, h, xp=np):
    """Solve ∇²p = rhs on periodic (N+1)-point grid via FFT."""
    rhs_int = rhs[:-1, :-1]
    N = rhs_int.shape[0]
    kx = xp.fft.fftfreq(N, d=h) * 2 * np.pi
    ky = xp.fft.fftfreq(N, d=h) * 2 * np.pi
    KX, KY = xp.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2
    K2[0, 0] = 1.0
    p_hat = xp.fft.fft2(rhs_int) / (-K2)
    p_hat[0, 0] = 0.0
    p_int = xp.real(xp.fft.ifft2(p_hat))
    p = xp.zeros_like(rhs)
    p[:-1, :-1] = p_int
    p[-1, :] = p[0, :]
    p[:, -1] = p[:, 0]
    return p


def dccd_filter(df, eps_d, axis):
    """Apply DCCD dissipative filter to derivative field (periodic)."""
    if eps_d == 0.0:
        return df
    filtered = df.copy()
    if axis == 0:
        filtered[1:-1, :] = df[1:-1, :] + eps_d * (df[2:, :] - 2 * df[1:-1, :] + df[:-2, :])
        filtered[0, :] = df[0, :] + eps_d * (df[1, :] - 2 * df[0, :] + df[-1, :])
        filtered[-1, :] = df[-1, :] + eps_d * (df[0, :] - 2 * df[-1, :] + df[-2, :])
    elif axis == 1:
        filtered[:, 1:-1] = df[:, 1:-1] + eps_d * (df[:, 2:] - 2 * df[:, 1:-1] + df[:, :-2])
        filtered[:, 0] = df[:, 0] + eps_d * (df[:, 1] - 2 * df[:, 0] + df[:, -1])
        filtered[:, -1] = df[:, -1] + eps_d * (df[:, 0] - 2 * df[:, -1] + df[:, -2])
    return filtered


def initial_condition(X, Y, xp=np):
    """Double shear layer IC."""
    u = xp.where(Y <= np.pi,
                 xp.tanh((Y - np.pi / 2) / DELTA),
                 xp.tanh((3 * np.pi / 2 - Y) / DELTA))
    v = EPS0 * xp.sin(X)
    return u, v


def kinetic_energy(u, v, h):
    """E_k on periodic grid — delegates to library."""
    from twophase.tools.diagnostics import kinetic_energy_periodic
    return kinetic_energy_periodic([u, v], h)


def run_simulation(N, eps_d):
    """Run AB2+projection double shear layer to T_FINAL."""
    backend = Backend()
    xp = backend.xp
    gc = GridConfig(ndim=2, N=(N, N), L=(L_DOM, L_DOM))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X, Y = grid.meshgrid()
    h = L_DOM / N

    u, v = initial_condition(X, Y, xp)
    p = xp.zeros_like(X)  # IPC: initial pressure = 0 (no analytical p for shear layer)
    rhs_u_prev, rhs_v_prev = None, None
    t = 0.0
    step = 0
    ek_history = [(t, kinetic_energy(u, v, h))]

    while t < T_FINAL - 1e-14:
        # CFL-based dt
        u_max = max(float(xp.max(xp.abs(u))), float(xp.max(xp.abs(v))), 1e-10)
        dt = CFL * h / u_max
        dt = min(dt, T_FINAL - t)

        # CCD derivatives for convection (with optional DCCD filter)
        du_dx, d2u_dx2 = ccd.differentiate(u, 0)
        du_dy, d2u_dy2 = ccd.differentiate(u, 1)
        dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
        dv_dy, d2v_dy2 = ccd.differentiate(v, 1)

        # DCCD filter on convective derivatives
        du_dx_f = dccd_filter(du_dx, eps_d, 0)
        du_dy_f = dccd_filter(du_dy, eps_d, 1)
        dv_dx_f = dccd_filter(dv_dx, eps_d, 0)
        dv_dy_f = dccd_filter(dv_dy, eps_d, 1)

        conv_u = u * du_dx_f + v * du_dy_f
        conv_v = u * dv_dx_f + v * dv_dy_f
        visc_u = NU * (d2u_dx2 + d2u_dy2)
        visc_v = NU * (d2v_dx2 + d2v_dy2)

        rhs_u = -conv_u + visc_u
        rhs_v = -conv_v + visc_v

        # IPC: include -∇p^n in predictor
        dp_dx_n, _ = ccd.differentiate(p, 0)
        dp_dy_n, _ = ccd.differentiate(p, 1)

        if step == 0:
            u_star = u + dt * rhs_u - dt * dp_dx_n
            v_star = v + dt * rhs_v - dt * dp_dy_n
        else:
            u_star = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev) - dt * dp_dx_n
            v_star = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev) - dt * dp_dy_n

        rhs_u_prev = rhs_u
        rhs_v_prev = rhs_v

        # PPE for pressure correction
        du_star_dx, _ = ccd.differentiate(u_star, 0)
        dv_star_dy, _ = ccd.differentiate(v_star, 1)
        div_star = du_star_dx + dv_star_dy
        phi = fft_poisson(div_star / dt, h, xp)

        dphi_dx, _ = ccd.differentiate(phi, 0)
        dphi_dy, _ = ccd.differentiate(phi, 1)
        u = u_star - dt * dphi_dx
        v = v_star - dt * dphi_dy
        p = p + phi

        t += dt
        step += 1
        ek_history.append((t, kinetic_energy(u, v, h)))

    ek_final = kinetic_energy(u, v, h)
    print(f"  N={N:>4}, eps_d={eps_d:.2f}: steps={step}, E_k(T)={ek_final:.6e}")
    return {"N": N, "eps_d": eps_d, "steps": step, "ek_final": ek_final,
            "ek_t": [e[0] for e in ek_history],
            "ek_v": [e[1] for e in ek_history]}


def run_all():
    """Run all (N, eps_d) combinations."""
    results = []
    for N in N_LIST:
        for eps_d in EPS_D_LIST:
            r = run_simulation(N, eps_d)
            results.append(r)
    return results


def plot_results(results):
    """Generate E_k comparison figure."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(N_LIST), figsize=(FIGSIZE_2COL[0] * 1.2, FIGSIZE_2COL[1]))
    if len(N_LIST) == 1:
        axes = [axes]

    for ax_idx, N in enumerate(N_LIST):
        ax = axes[ax_idx]
        for r in results:
            if r["N"] != N:
                continue
            label = f"CCD" if r["eps_d"] == 0.0 else rf"DCCD ($\varepsilon_d$={r['eps_d']})"
            cidx = 0 if r["eps_d"] == 0.0 else 1
            ax.plot(r["ek_t"], r["ek_v"], color=COLORS[cidx], label=label)

        ax.set_xlabel(r"$t$")
        ax.set_ylabel(r"$E_k$")
        ax.set_title(f"$N = {N}$")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Double shear layer: CCD vs DCCD kinetic energy")
    fig.tight_layout()
    save_figure(fig, OUT / "dccd_shear")


def main():
    args = experiment_argparser("[12-6] DCCD shear layer non-invasiveness").parse_args()
    if args.plot_only:
        d = load_results(NPZ)
        plot_results(d["results"])
        return

    print("\n=== [12-6] DCCD non-invasiveness on double shear layer ===")
    results = run_all()

    # Print comparison table
    print(f"\n{'N':>6} {'eps_d':>8} {'steps':>8} {'E_k(T)':>14}")
    print("-" * 40)
    for r in results:
        print(f"{r['N']:>6} {r['eps_d']:>8.2f} {r['steps']:>8} {r['ek_final']:>14.6e}")

    # Relative difference for each N
    print("\nRelative E_k difference (DCCD vs CCD):")
    for N in N_LIST:
        ccd_r = [r for r in results if r["N"] == N and r["eps_d"] == 0.0][0]
        dccd_r = [r for r in results if r["N"] == N and r["eps_d"] != 0.0][0]
        rel = abs(dccd_r["ek_final"] - ccd_r["ek_final"]) / abs(ccd_r["ek_final"])
        print(f"  N={N}: |ΔE_k|/E_k = {rel:.4e}")

    save_results(NPZ, {"results": results})
    plot_results(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
