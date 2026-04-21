#!/usr/bin/env python3
"""[11-33] FVM matrix-free GMRES diagnostics.

Diagnoses why ``PPESolverFVMMatrixFree`` underperforms the direct CSR solve by
measuring, on the remote GPU path:

    - total GMRES solve time
    - matrix-free operator application cost
    - line-preconditioner application cost
    - GMRES matvec / preconditioner call counts
    - parity vs the direct ``PPESolverFVMSpsolve`` reference

The sweep is intentionally small and targeted to ``N = 128, 256`` where the
first benchmark already showed the matrix-free solver nearing parity in wall
time but losing residual quality at the finest grid.
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


VARIANTS = [
    {"name": "prec_t1e10_ct2_r40", "tol": 1e-10, "c_tau": 2.0, "restart": 40, "use_prec": True},
    {"name": "prec_t1e8_ct2_r40", "tol": 1e-8, "c_tau": 2.0, "restart": 40, "use_prec": True},
    {"name": "prec_t1e8_ct1_r40", "tol": 1e-8, "c_tau": 1.0, "restart": 40, "use_prec": True},
    {"name": "prec_t1e8_ct4_r40", "tol": 1e-8, "c_tau": 4.0, "restart": 40, "use_prec": True},
    {"name": "prec_t1e8_ct4_r20", "tol": 1e-8, "c_tau": 4.0, "restart": 20, "use_prec": True},
    {"name": "prec_t1e8_ct4_r80", "tol": 1e-8, "c_tau": 4.0, "restart": 80, "use_prec": True},
    {"name": "noprec_t1e8_r40", "tol": 1e-8, "c_tau": 2.0, "restart": 40, "use_prec": False},
]


def density_field(N: int, h: float, rho_l: float, rho_g: float) -> np.ndarray:
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    phi = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - 0.25
    eps = 1.5 * h
    H = 0.5 * (1.0 + np.tanh(phi / (2.0 * eps)))
    return rho_l * (1.0 - H) + rho_g * H


def rhs_field(N: int) -> np.ndarray:
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


def make_matrixfree_config(N: int, tol: float, c_tau: float, maxiter: int = 300):
    return SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(),
        numerics=NumericsConfig(bc_type="wall"),
        solver=SolverConfig(
            ppe_solver_type="fvm_matrixfree",
            pseudo_tol=tol,
            pseudo_maxiter=maxiter,
            pseudo_c_tau=c_tau,
        ),
    )


def prepare_solver(backend: Backend, N: int, rho_dev, tol: float, c_tau: float, restart: int):
    grid = Grid(GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)), backend)
    solver = PPESolverFVMMatrixFree(
        backend,
        make_matrixfree_config(N, tol=tol, c_tau=c_tau),
        grid,
        bc_type="wall",
    )
    solver.restart = restart
    rho_xp = backend.xp.asarray(rho_dev)
    solver._operator_coeffs = [
        solver.build_line_coeffs(rho_xp, ax) for ax in range(grid.ndim)
    ]
    shift = 2.0 / (solver.c_tau * rho_xp * (solver._h_min ** 2))
    solver._precond_coeffs = []
    for lower, main, upper in solver._operator_coeffs:
        solver._precond_coeffs.append((-lower, shift - main, -upper))
    return grid, solver


def median_time_ms(backend: Backend, fn, repeat: int = 5) -> float:
    times = []
    for _ in range(repeat):
        synchronize(backend)
        t0 = time.perf_counter()
        _ = fn()
        synchronize(backend)
        times.append((time.perf_counter() - t0) * 1000.0)
    return float(np.median(np.asarray(times, dtype=np.float64)))


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


def run_gmres_variant(solver: PPESolverFVMMatrixFree, rhs_dev, *, use_prec: bool):
    xp = solver.xp
    la = solver.backend.sparse_linalg
    rhs_flat = xp.asarray(rhs_dev).ravel().copy()
    rhs_flat[solver._pin_dof] = 0.0
    n_dof = int(np.prod(solver.grid.shape))

    counts = {"matvec": 0, "prec": 0}

    def _matvec(p_flat):
        counts["matvec"] += 1
        p_field = xp.asarray(p_flat).reshape(solver.grid.shape)
        return solver.apply(p_field).ravel()

    A = la.LinearOperator((n_dof, n_dof), matvec=_matvec, dtype=rhs_flat.dtype)

    M = None
    if use_prec:
        def _precond(r_flat):
            counts["prec"] += 1
            r_field = xp.asarray(r_flat).reshape(solver.grid.shape)
            return solver.apply_line_preconditioner(r_field).ravel()

        M = la.LinearOperator((n_dof, n_dof), matvec=_precond, dtype=rhs_flat.dtype)

    synchronize(solver.backend)
    t0 = time.perf_counter()
    try:
        sol_flat, info = la.gmres(
            A,
            rhs_flat,
            M=M,
            restart=solver.restart,
            maxiter=solver.maxiter,
            atol=0.0,
            rtol=solver.tol,
        )
    except TypeError:
        sol_flat, info = la.gmres(
            A,
            rhs_flat,
            M=M,
            restart=solver.restart,
            maxiter=solver.maxiter,
            tol=solver.tol,
        )
    synchronize(solver.backend)

    sol = xp.asarray(sol_flat).reshape(solver.grid.shape)
    sol.ravel()[solver._pin_dof] = 0.0
    return sol, int(info), counts, (time.perf_counter() - t0) * 1000.0


def run_benchmark():
    backend = Backend()
    Ns = [128, 256]
    rho_ratio = 1000.0
    rho_l, rho_g = rho_ratio, 1.0
    results = {
        "_meta": {
            "device": backend.device,
            "rho_ratio": rho_ratio,
            "N": np.asarray(Ns, dtype=np.int64),
        },
        "direct": {
            "t_solve_ms": np.zeros(len(Ns), dtype=np.float64),
            "residual": np.zeros(len(Ns), dtype=np.float64),
        },
    }

    for variant in VARIANTS:
        results[variant["name"]] = {
            "t_solve_ms": np.zeros(len(Ns), dtype=np.float64),
            "t_apply_ms": np.zeros(len(Ns), dtype=np.float64),
            "t_prec_ms": np.full(len(Ns), np.nan, dtype=np.float64),
            "matvec_calls": np.zeros(len(Ns), dtype=np.float64),
            "prec_calls": np.zeros(len(Ns), dtype=np.float64),
            "gmres_info": np.zeros(len(Ns), dtype=np.float64),
            "rel_l2_error": np.zeros(len(Ns), dtype=np.float64),
            "residual": np.zeros(len(Ns), dtype=np.float64),
            "est_apply_share": np.zeros(len(Ns), dtype=np.float64),
            "est_prec_share": np.zeros(len(Ns), dtype=np.float64),
        }

    print(f"\n{'=' * 112}")
    print(f"  FVM Matrix-Free GMRES Diagnostics ({backend.device.upper()})")
    print(f"{'=' * 112}")
    print(
        "  "
        f"{'variant':<21} {'N':>5} {'solve [ms]':>12} {'apply [ms]':>12} "
        f"{'prec [ms]':>11} {'mv':>6} {'pc':>6} {'rel-L2':>11} {'res':>11}"
    )
    print("  " + "-" * 108)

    for idx, N in enumerate(Ns):
        h = 1.0 / N
        rho = density_field(N, h, rho_l=rho_l, rho_g=rho_g)
        rhs = rhs_field(N)
        rho_dev = backend.to_device(rho)
        rhs_dev = backend.to_device(rhs)

        grid_direct = Grid(GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)), backend)
        solver_direct = PPESolverFVMSpsolve(backend, grid_direct, bc_type="wall")
        _ = solver_direct.solve(rhs_dev, rho_dev, dt=0.0)
        direct_t = median_time_ms(
            backend, lambda: solver_direct.solve(rhs_dev, rho_dev, dt=0.0), repeat=3
        )
        p_direct = solver_direct.solve(rhs_dev, rho_dev, dt=0.0)

        _, solver_res = prepare_solver(backend, N, rho_dev, tol=1e-10, c_tau=2.0, restart=40)
        results["direct"]["t_solve_ms"][idx] = direct_t
        results["direct"]["residual"][idx] = residual_norm(solver_res, rhs_dev, p_direct)

        for variant in VARIANTS:
            _, solver = prepare_solver(
                backend, N, rho_dev,
                tol=variant["tol"],
                c_tau=variant["c_tau"],
                restart=variant["restart"],
            )

            probe_p = backend.xp.sin(backend.xp.asarray(rhs_dev))
            apply_ms = median_time_ms(backend, lambda: solver.apply(probe_p), repeat=5)
            prec_ms = np.nan
            if variant["use_prec"]:
                prec_ms = median_time_ms(
                    backend, lambda: solver.apply_line_preconditioner(probe_p), repeat=5
                )

            p_mf, info, counts, solve_ms = run_gmres_variant(
                solver, rhs_dev, use_prec=variant["use_prec"]
            )
            rel_err = l2_rel_error(backend, p_direct, p_mf)
            res_mf = residual_norm(solver, rhs_dev, p_mf)

            total_est = counts["matvec"] * apply_ms
            if variant["use_prec"] and not np.isnan(prec_ms):
                total_est += counts["prec"] * prec_ms
            apply_share = (counts["matvec"] * apply_ms / total_est) if total_est > 0.0 else np.nan
            prec_share = (
                counts["prec"] * prec_ms / total_est
                if variant["use_prec"] and total_est > 0.0 and not np.isnan(prec_ms)
                else 0.0
            )

            dst = results[variant["name"]]
            dst["t_solve_ms"][idx] = solve_ms
            dst["t_apply_ms"][idx] = apply_ms
            dst["t_prec_ms"][idx] = prec_ms
            dst["matvec_calls"][idx] = counts["matvec"]
            dst["prec_calls"][idx] = counts["prec"]
            dst["gmres_info"][idx] = info
            dst["rel_l2_error"][idx] = rel_err
            dst["residual"][idx] = res_mf
            dst["est_apply_share"][idx] = apply_share
            dst["est_prec_share"][idx] = prec_share

            print(
                "  "
                f"{variant['name']:<21} {N:5d} {solve_ms:12.3f} {apply_ms:12.3f} "
                f"{prec_ms:11.3f} {counts['matvec']:6d} {counts['prec']:6d} "
                f"{rel_err:11.3e} {res_mf:11.3e}"
            )

        print(
            "  "
            f"{'direct_ref':<21} {N:5d} {direct_t:12.3f} {'-':>12} {'-':>11} "
            f"{'-':>6} {'-':>6} {0.0:11.3e} {results['direct']['residual'][idx]:11.3e}"
        )
        print("  " + "-" * 108)

    return results


def plot_all(results):
    import matplotlib.pyplot as plt

    Ns = np.asarray(results["_meta"]["N"])
    variant_names = [v["name"] for v in VARIANTS]

    fig, axes = plt.subplots(1, 3, figsize=(FIGSIZE_2COL[0] * 1.7, FIGSIZE_2COL[1]))

    ax = axes[0]
    direct = np.asarray(results["direct"]["t_solve_ms"])
    for idx, name in enumerate(variant_names):
        vals = np.asarray(results[name]["t_solve_ms"])
        ax.loglog(Ns, vals, f"{MARKERS[idx]}-", color=COLORS[idx], label=name)
    ax.loglog(Ns, direct, "k--", label="direct_ref")
    ax.set_xlabel("$N$")
    ax.set_ylabel("solve time [ms]")
    ax.set_title("(a) GMRES solve time")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6)

    ax = axes[1]
    for idx, name in enumerate(variant_names):
        vals = np.asarray(results[name]["matvec_calls"])
        ax.semilogx(Ns, vals, f"{MARKERS[idx]}-", color=COLORS[idx], label=name)
    ax.set_xlabel("$N$")
    ax.set_ylabel("matvec calls")
    ax.set_title("(b) Krylov work")
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    for idx, name in enumerate(variant_names):
        vals = np.asarray(results[name]["rel_l2_error"])
        ax.loglog(Ns, vals, f"{MARKERS[idx]}-", color=COLORS[idx], label=name)
    ax.set_xlabel("$N$")
    ax.set_ylabel("rel-L2 error vs direct")
    ax.set_title("(c) Parity")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    save_figure(fig, OUT / "fvm_matrixfree_gmres_diag")


def main():
    args = experiment_argparser("[11-33] FVM matrix-free GMRES diagnostics").parse_args()
    if args.plot_only:
        plot_all(load_results(OUT / "data.npz"))
        return

    results = run_benchmark()
    save_results(OUT / "data.npz", results)
    plot_all(results)
    print(f"\nResults saved to {OUT}")


if __name__ == "__main__":
    main()
