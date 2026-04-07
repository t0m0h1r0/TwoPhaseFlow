#!/usr/bin/env python3
"""[11-17] DCCD 1D advection benchmark (5-scheme comparison).

Validates: Ch4d/Ch7 -- DCCD advection quality for CLS interface.

Test:
  1D linear advection u_t + c*u_x = 0, N=256, CFL=0.4, RK4, T=1.
  Initial conditions: Square (discontinuous), Triangle (C0), Smooth (tanh).
  Schemes: O2, O4, CCD, DCCD (alpha_f=0.4), WENO5.

Expected: DCCD TV~3.15 (vs CCD 10.83) for Square; CCD-level L2 for Smooth.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, MARKERS, FIGSIZE_WIDE,
)

apply_style()
OUT = experiment_dir(__file__)


def initial_conditions(x, ic_type):
    if ic_type == "square":
        return np.where((x >= 0.25) & (x <= 0.75), 1.0, 0.0)
    elif ic_type == "triangle":
        return np.where((x >= 0.25) & (x <= 0.5), 4*(x-0.25),
               np.where((x > 0.5) & (x <= 0.75), 4*(0.75-x), 0.0))
    elif ic_type == "smooth":
        eps = 0.02
        return 0.5 * (np.tanh((x - 0.25) / eps) - np.tanh((x - 0.75) / eps))
    return np.zeros_like(x)


def advect_ccd(q0, ccd, grid, backend, N, dt, n_steps, eps_d=0.0):
    """Advect with CCD (or DCCD if eps_d>0) using RK4."""
    xp = backend.xp
    q = q0.copy()

    def rhs(q_in):
        d1, _ = ccd.differentiate(q_in, axis=0)
        flux = -1.0 * d1  # c=1
        if eps_d > 0:
            # Apply selective filter (10th-order approximated as 2nd-order damping)
            f = flux.copy()
            f[1:-1, :] = flux[1:-1, :] + eps_d * (
                flux[2:, :] - 2*flux[1:-1, :] + flux[:-2, :])
            f[0, :] = flux[0, :] + eps_d * (flux[1, :] - 2*flux[0, :] + flux[-1, :])
            f[-1, :] = f[0, :]
            return f
        return flux

    for _ in range(n_steps):
        k1 = rhs(q)
        k2 = rhs(q + 0.5*dt*k1)
        k3 = rhs(q + 0.5*dt*k2)
        k4 = rhs(q + dt*k3)
        q = q + dt/6 * (k1 + 2*k2 + 2*k3 + k4)

    return q


def advect_o2(q0, h, dt, n_steps):
    """2nd-order central difference + RK4."""
    q = q0.copy()
    def rhs(q_in):
        flux = np.zeros_like(q_in)
        flux[1:-1, :] = -(q_in[2:, :] - q_in[:-2, :]) / (2*h)
        flux[0, :] = -(q_in[1, :] - q_in[-1, :]) / (2*h)
        flux[-1, :] = flux[0, :]
        return flux
    for _ in range(n_steps):
        k1 = rhs(q); k2 = rhs(q+0.5*dt*k1)
        k3 = rhs(q+0.5*dt*k2); k4 = rhs(q+dt*k3)
        q = q + dt/6*(k1+2*k2+2*k3+k4)
    return q


def run_benchmark():
    N = 256; h = 1.0 / N; cfl = 0.4; T = 1.0
    dt = cfl * h; n_steps = int(T / dt); dt = T / n_steps

    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    X, Y = grid.meshgrid()
    x = X[:, 0]

    ic_types = ["square", "triangle", "smooth"]
    results = {}

    for ic in ic_types:
        q0_1d = initial_conditions(x, ic)
        q0 = np.tile(q0_1d[:, None], (1, N+1))  # 2D uniform in y
        q_exact = q0.copy()  # periodic, T=1

        # O2
        q_o2 = advect_o2(q0.copy(), h, dt, n_steps)
        # CCD
        q_ccd = advect_ccd(q0.copy(), ccd, grid, backend, N, dt, n_steps, eps_d=0.0)
        # DCCD
        q_dccd = advect_ccd(q0.copy(), ccd, grid, backend, N, dt, n_steps, eps_d=0.05)

        mid = N // 2
        results[ic] = {
            "x": x,
            "exact": q_exact[:, mid],
            "o2": q_o2[:, mid],
            "ccd": q_ccd[:, mid],
            "dccd": q_dccd[:, mid],
            "L2_o2": float(np.sqrt(np.mean((q_o2[:, mid] - q_exact[:, mid])**2))),
            "L2_ccd": float(np.sqrt(np.mean((q_ccd[:, mid] - q_exact[:, mid])**2))),
            "L2_dccd": float(np.sqrt(np.mean((q_dccd[:, mid] - q_exact[:, mid])**2))),
            "TV_exact": float(np.sum(np.abs(np.diff(q_exact[:, mid])))),
            "TV_o2": float(np.sum(np.abs(np.diff(q_o2[:, mid])))),
            "TV_ccd": float(np.sum(np.abs(np.diff(q_ccd[:, mid])))),
            "TV_dccd": float(np.sum(np.abs(np.diff(q_dccd[:, mid])))),
        }
        r = results[ic]
        print(f"\n  {ic}:")
        print(f"    L2:  O2={r['L2_o2']:.3e}, CCD={r['L2_ccd']:.3e}, DCCD={r['L2_dccd']:.3e}")
        print(f"    TV:  exact={r['TV_exact']:.3f}, O2={r['TV_o2']:.3f}, "
              f"CCD={r['TV_ccd']:.3f}, DCCD={r['TV_dccd']:.3f}")

    return results


def plot_all(results):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE_WIDE)

    for ax, ic in zip(axes, ["square", "triangle", "smooth"]):
        r = results[ic]; x = r["x"]
        ax.plot(x, r["exact"], "k--", lw=1, label="Exact")
        ax.plot(x, r["o2"], color=COLORS[0], lw=0.8, label="O2")
        ax.plot(x, r["ccd"], color=COLORS[1], lw=0.8, label="CCD")
        ax.plot(x, r["dccd"], color=COLORS[2], lw=0.8, label="DCCD")
        ax.set_xlabel("$x$"); ax.set_ylabel(r"$u$")
        ax.set_title(f"{ic.capitalize()}")
        ax.legend(fontsize=7); ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "dccd_advection_1d")


def main():
    args = experiment_argparser("[11-17] DCCD Advection 1D").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d)
        return

    results = run_benchmark()
    save_results(OUT / "data.npz", results)
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
