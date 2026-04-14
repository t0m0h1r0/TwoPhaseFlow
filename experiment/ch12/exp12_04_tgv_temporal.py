#!/usr/bin/env python3
"""[12-4] TGV temporal convergence (AB2 + projection).

Paper ref: §12.3.1

Verifies that the Adams-Bashforth 2nd-order + projection time integrator
achieves O(Δt²) temporal accuracy on the Taylor-Green vortex.

Setup:
  Domain : [0, 2π]², periodic, ρ=1, ν=0.01 (Re=100)
  IC     : u = sin(x)cos(y), v = -cos(x)sin(y)
  Exact  : u(t) = sin(x)cos(y)exp(-2νt), v(t) = -cos(x)sin(y)exp(-2νt)
  Grid   : N=64 fixed
  Vary   : nsteps ∈ {5, 10, 20, 40, 80, 160}, all to T=0.5

Expected: O(Δt²) in L∞(u - u_exact).
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
NU = 0.01
T_FINAL = 0.5
N_GRID = 64
L_DOM = 2.0 * np.pi
NSTEPS_LIST = [5, 10, 20, 40, 80, 160]


def fft_poisson(rhs, h):
    """Solve ∇²p = rhs on periodic (N+1)-point grid via FFT."""
    rhs_int = rhs[:-1, :-1]
    N = rhs_int.shape[0]
    kx = np.fft.fftfreq(N, d=h) * 2 * np.pi
    ky = np.fft.fftfreq(N, d=h) * 2 * np.pi
    KX, KY = np.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2
    K2[0, 0] = 1.0
    p_hat = np.fft.fft2(rhs_int) / (-K2)
    p_hat[0, 0] = 0.0
    p_int = np.real(np.fft.ifft2(p_hat))
    p = np.zeros_like(rhs)
    p[:-1, :-1] = p_int
    p[-1, :] = p[0, :]
    p[:, -1] = p[:, 0]
    return p
    return p


def exact_solution(X, Y, t):
    """TGV exact solution at time t — delegates to library."""
    from twophase.tools.benchmarks.analytical_solutions import tgv_velocity
    return tgv_velocity(X, Y, t, NU)


def compute_rhs(u, v, ccd):
    """Compute RHS = -convection + viscous diffusion using CCD."""
    du_dx, d2u_dx2 = ccd.differentiate(u, 0)
    du_dy, d2u_dy2 = ccd.differentiate(u, 1)
    dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
    dv_dy, d2v_dy2 = ccd.differentiate(v, 1)

    du_dx = np.asarray(du_dx); d2u_dx2 = np.asarray(d2u_dx2)
    du_dy = np.asarray(du_dy); d2u_dy2 = np.asarray(d2u_dy2)
    dv_dx = np.asarray(dv_dx); d2v_dx2 = np.asarray(d2v_dx2)
    dv_dy = np.asarray(dv_dy); d2v_dy2 = np.asarray(d2v_dy2)

    conv_u = u * du_dx + v * du_dy
    conv_v = u * dv_dx + v * dv_dy
    visc_u = NU * (d2u_dx2 + d2u_dy2)
    visc_v = NU * (d2v_dx2 + d2v_dy2)

    rhs_u = -conv_u + visc_u
    rhs_v = -conv_v + visc_v
    return rhs_u, rhs_v


def run_simulation(nsteps):
    """Run AB2+IPC TGV to T_FINAL with given number of steps."""
    backend = Backend(use_gpu=False)
    N = N_GRID
    gc = GridConfig(ndim=2, N=(N, N), L=(L_DOM, L_DOM))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X, Y = grid.meshgrid()
    h = L_DOM / N
    dt = T_FINAL / nsteps

    # Initial condition
    u, v = exact_solution(X, Y, 0.0)
    # IPC: initialize pressure to exact TGV pressure
    p = -0.25 * (np.cos(2 * X) + np.cos(2 * Y))
    rhs_u_prev, rhs_v_prev = None, None

    for step in range(nsteps):
        rhs_u, rhs_v = compute_rhs(u, v, ccd)

        # IPC: include -∇p^n in predictor
        dp_dx_n, _ = ccd.differentiate(p, 0)
        dp_dy_n, _ = ccd.differentiate(p, 1)

        if step == 0:
            u_star = u + dt * rhs_u - dt * np.asarray(dp_dx_n)
            v_star = v + dt * rhs_v - dt * np.asarray(dp_dy_n)
        else:
            u_star = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev) - dt * np.asarray(dp_dx_n)
            v_star = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev) - dt * np.asarray(dp_dy_n)

        rhs_u_prev = rhs_u
        rhs_v_prev = rhs_v

        # PPE for pressure correction
        du_star_dx, _ = ccd.differentiate(u_star, 0)
        dv_star_dy, _ = ccd.differentiate(v_star, 1)
        div_star = np.asarray(du_star_dx) + np.asarray(dv_star_dy)
        phi = fft_poisson(div_star / dt, h)

        dphi_dx, _ = ccd.differentiate(phi, 0)
        dphi_dy, _ = ccd.differentiate(phi, 1)
        u = u_star - dt * np.asarray(dphi_dx)
        v = v_star - dt * np.asarray(dphi_dy)
        p = p + phi

    u_ex, v_ex = exact_solution(X, Y, T_FINAL)
    err = max(np.max(np.abs(u - u_ex)), np.max(np.abs(v - v_ex)))
    return dt, err


def run_convergence():
    """Run all resolutions and compute convergence rates."""
    results = []
    for nsteps in NSTEPS_LIST:
        dt, err = run_simulation(nsteps)
        results.append({"nsteps": nsteps, "dt": dt, "error": err})
        print(f"  nsteps={nsteps:>4}, dt={dt:.4e}, L∞={err:.4e}")

    # Compute convergence orders
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        if r0["error"] > 1e-15 and r1["error"] > 1e-15:
            r1["order"] = np.log(r0["error"] / r1["error"]) / np.log(r0["dt"] / r1["dt"])
    return results


def plot_convergence(results):
    """Generate convergence plot."""
    import matplotlib.pyplot as plt

    dt_arr = np.array([r["dt"] for r in results])
    err_arr = np.array([r["error"] for r in results])

    fig, ax = plt.subplots(figsize=FIGSIZE_2COL)
    ax.loglog(dt_arr, err_arr, "o-", color=COLORS[0], marker=MARKERS[0],
              label="AB2 + projection")

    # Reference O(dt^2) line
    ref = err_arr[-1] * (dt_arr / dt_arr[-1])**2
    ax.loglog(dt_arr, ref, "--", color="gray", label=r"$O(\Delta t^2)$")

    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("TGV temporal convergence (AB2 + projection)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, OUT / "tgv_temporal")


def main():
    args = experiment_argparser("[12-4] TGV temporal convergence").parse_args()
    if args.plot_only:
        d = load_results(NPZ)
        plot_convergence(d["results"])
        return

    print("\n=== [12-4] TGV temporal convergence ===")
    results = run_convergence()

    # Print table
    print(f"\n{'nsteps':>8} {'dt':>12} {'L∞ error':>12} {'order':>8}")
    print("-" * 44)
    for r in results:
        order = r.get("order", float("nan"))
        print(f"{r['nsteps']:>8} {r['dt']:>12.4e} {r['error']:>12.4e} {order:>8.2f}")

    save_results(NPZ, {"results": results})
    plot_convergence(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
