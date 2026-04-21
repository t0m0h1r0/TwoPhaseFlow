#!/usr/bin/env python3
"""[11-32] FVM PPE solver benchmark: direct CSR vs matrix-free GMRES.

Compares the legacy ``PPESolverFVMSpsolve`` against
``PPESolverFVMMatrixFree`` on the same variable-density wall PPE:

    ∇·[(1/ρ) ∇p] = rhs

Metrics:
    - wall-clock solve time
    - relative solution mismatch vs direct solve
    - operator residual under the matrix-free operator

The benchmark is GPU-aware through ``Backend()`` and is intended to be run via
``make run`` / ``make cycle`` so the remote GPU path is used when available.
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np

from twophase.backend import Backend
from twophase.config import (
    FluidConfig,
    GridConfig,
    NumericsConfig,
    SimulationConfig,
    SolverConfig,
)
from twophase.core.grid import Grid
from twophase.ppe.fvm_matrixfree import PPESolverFVMMatrixFree
from twophase.ppe.fvm_spsolve import PPESolverFVMSpsolve
from twophase.tools.experiment import (
    COLORS,
    FIGSIZE_2COL,
    MARKERS,
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()
OUT = experiment_dir(__file__)


def density_field(N: int, h: float, rho_l: float, rho_g: float) -> np.ndarray:
    """Smoothed circular density interface on node points."""
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    phi = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - 0.25
    eps = 1.5 * h
    H = 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))
    return rho_l * (1.0 - H) + rho_g * H


def rhs_field(N: int) -> np.ndarray:
    """Smooth zero-mean RHS with non-trivial multiaxial content."""
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    rhs = (
        np.sin(2.0 * np.pi * X) * np.sin(2.0 * np.pi * Y)
        + 0.15 * np.cos(4.0 * np.pi * X) * np.sin(2.0 * np.pi * Y)
    )
    return rhs - rhs.mean()


def synchronize(backend: Backend) -> None:
    if backend.is_gpu():
        backend.xp.cuda.Stream.null.synchronize()


def l2_rel_error(backend: Backend, ref, trial) -> float:
    xp = backend.xp
    ref_dev = xp.asarray(ref)
    trial_dev = xp.asarray(trial)
    denom = xp.sqrt(xp.sum(ref_dev.ravel() ** 2))
    if float(np.asarray(backend.to_host(denom))) == 0.0:
        return 0.0
    num = xp.sqrt(xp.sum((trial_dev.ravel() - ref_dev.ravel()) ** 2))
    return float(np.asarray(backend.to_host(num / denom)))


def residual_norm(solver: PPESolverFVMMatrixFree, rhs, p) -> float:
    xp = solver.xp
    rhs_dev = xp.asarray(rhs).copy()
    rhs_dev.ravel()[solver._pin_dof] = 0.0
    res = solver.apply(xp.asarray(p)) - rhs_dev
    num = xp.sqrt(xp.sum(res.ravel() ** 2))
    den = xp.sqrt(xp.sum(rhs_dev.ravel() ** 2))
    return float(np.asarray(solver.backend.to_host(num / den)))


def make_matrixfree_config(N: int) -> SimulationConfig:
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(),
        numerics=NumericsConfig(bc_type="wall"),
        solver=SolverConfig(
            ppe_solver_type="fvm_matrixfree",
            pseudo_tol=1e-10,
            pseudo_maxiter=300,
            pseudo_c_tau=2.0,
        ),
    )


def time_solver(backend: Backend, solver, rhs_dev, rho_dev, repeat: int = 3):
    times_ms = []
    last_sol = None
    for _ in range(repeat):
        synchronize(backend)
        t0 = time.perf_counter()
        last_sol = solver.solve(rhs_dev, rho_dev, dt=0.0)
        synchronize(backend)
        times_ms.append((time.perf_counter() - t0) * 1000.0)
    return np.array(times_ms, dtype=np.float64), last_sol


def run_benchmark():
    backend = Backend()
    device = backend.device
    Ns = [64, 128, 256]
    rho_ratio = 1000.0
    rho_l, rho_g = rho_ratio, 1.0
    repeat = 3

    results = {
        "N": np.array(Ns, dtype=np.int64),
        "t_direct_ms": np.zeros(len(Ns), dtype=np.float64),
        "t_matrixfree_ms": np.zeros(len(Ns), dtype=np.float64),
        "speedup": np.zeros(len(Ns), dtype=np.float64),
        "rel_l2_error": np.zeros(len(Ns), dtype=np.float64),
        "res_direct": np.zeros(len(Ns), dtype=np.float64),
        "res_matrixfree": np.zeros(len(Ns), dtype=np.float64),
        "fallback_used": np.zeros(len(Ns), dtype=np.int64),
        "device": np.array(device),
        "rho_ratio": np.array(rho_ratio),
    }

    print(f"\n{'=' * 86}")
    print(f"  FVM PPE Benchmark: direct CSR vs matrix-free GMRES ({device.upper()})")
    print(f"{'=' * 86}")
    print(
        "  "
        f"{'N':>5} {'direct [ms]':>14} {'matrixfree [ms]':>17} "
        f"{'speedup':>10} {'rel-L2 err':>12} {'res dir':>11} {'res mf':>11}"
    )
    print("  " + "-" * 82)

    for idx, N in enumerate(Ns):
        h = 1.0 / N
        grid = Grid(GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)), backend)
        rho = density_field(N, h, rho_l=rho_l, rho_g=rho_g)
        rhs = rhs_field(N)

        rho_dev = backend.to_device(rho)
        rhs_dev = backend.to_device(rhs)

        solver_direct = PPESolverFVMSpsolve(backend, grid, bc_type="wall")
        solver_mf = PPESolverFVMMatrixFree(
            backend, make_matrixfree_config(N), grid, bc_type="wall"
        )

        _ = solver_direct.solve(rhs_dev, rho_dev, dt=0.0)
        _ = solver_mf.solve(rhs_dev, rho_dev, dt=0.0)

        t_direct, p_direct = time_solver(backend, solver_direct, rhs_dev, rho_dev, repeat=repeat)
        t_mf, p_mf = time_solver(backend, solver_mf, rhs_dev, rho_dev, repeat=repeat)

        if solver_mf._operator_coeffs is None:
            solver_mf._operator_coeffs = [
                solver_mf.build_line_coeffs(backend.xp.asarray(rho_dev), ax)
                for ax in range(grid.ndim)
            ]

        direct_ms = float(np.median(t_direct))
        matrixfree_ms = float(np.median(t_mf))
        rel_err = l2_rel_error(backend, p_direct, p_mf)
        res_dir = residual_norm(solver_mf, rhs_dev, p_direct)
        res_mf = residual_norm(solver_mf, rhs_dev, p_mf)
        fallback_used = int(rel_err == 0.0 and matrixfree_ms >= 0.98 * direct_ms)

        results["t_direct_ms"][idx] = direct_ms
        results["t_matrixfree_ms"][idx] = matrixfree_ms
        results["speedup"][idx] = direct_ms / matrixfree_ms if matrixfree_ms > 0.0 else np.nan
        results["rel_l2_error"][idx] = rel_err
        results["res_direct"][idx] = res_dir
        results["res_matrixfree"][idx] = res_mf
        results["fallback_used"][idx] = fallback_used

        print(
            "  "
            f"{N:5d} {direct_ms:14.3f} {matrixfree_ms:17.3f} "
            f"{results['speedup'][idx]:10.3f} {rel_err:12.3e} "
            f"{res_dir:11.3e} {res_mf:11.3e}"
        )

    return results


def plot_all(results):
    import matplotlib.pyplot as plt

    N = np.asarray(results["N"])
    t_direct = np.asarray(results["t_direct_ms"])
    t_mf = np.asarray(results["t_matrixfree_ms"])
    speedup = np.asarray(results["speedup"])
    rel_err = np.asarray(results["rel_l2_error"])
    res_dir = np.asarray(results["res_direct"])
    res_mf = np.asarray(results["res_matrixfree"])

    fig, axes = plt.subplots(1, 3, figsize=(FIGSIZE_2COL[0] * 1.45, FIGSIZE_2COL[1]))

    ax = axes[0]
    ax.loglog(N, t_direct, f"{MARKERS[0]}-", color=COLORS[0], label="FVM spsolve")
    ax.loglog(N, t_mf, f"{MARKERS[1]}-", color=COLORS[1], label="FVM matrix-free")
    ax.set_xlabel("$N$")
    ax.set_ylabel("solve time [ms]")
    ax.set_title("(a) PPE solve time")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

    ax = axes[1]
    ax.semilogx(N, speedup, f"{MARKERS[2]}-", color=COLORS[2])
    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1.0)
    ax.set_xlabel("$N$")
    ax.set_ylabel("direct / matrix-free")
    ax.set_title("(b) Speedup")
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    ax.loglog(N, rel_err, f"{MARKERS[3]}-", color=COLORS[3], label="rel-L2(p)")
    ax.loglog(N, res_dir, f"{MARKERS[4]}-", color=COLORS[4], label="residual direct")
    ax.loglog(N, res_mf, f"{MARKERS[5]}-", color=COLORS[5], label="residual matrix-free")
    ax.set_xlabel("$N$")
    ax.set_ylabel("relative error / residual")
    ax.set_title("(c) Parity")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

    fig.tight_layout()
    save_figure(fig, OUT / "fvm_ppe_solver_benchmark")


def main():
    args = experiment_argparser("[11-32] FVM PPE solver benchmark").parse_args()

    if args.plot_only:
        plot_all(load_results(OUT / "data.npz"))
        return

    results = run_benchmark()
    save_results(OUT / "data.npz", results)
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
