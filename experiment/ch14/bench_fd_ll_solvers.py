#!/usr/bin/env python3
"""Benchmark FD direct and FD-CG low-order L_L solvers for defect correction."""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.backend import Backend  # noqa: E402
from twophase.config import GridConfig, SimulationConfig, SolverConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.ppe.fd_direct import PPESolverFDDirect  # noqa: E402
from twophase.ppe.fd_matrixfree import PPESolverFDMatrixFree  # noqa: E402


@dataclass
class TimedResult:
    payload: dict
    elapsed_s: float
    proc_peak_mib: float | None


class GpuProcessSampler:
    """Poll nvidia-smi for current-process GPU memory while a block runs."""

    def __init__(self, interval_s: float = 0.05):
        self.interval_s = interval_s
        self.pid = os.getpid()
        self.peak_mib: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        if not _nvidia_smi_available():
            return self
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _poll(self) -> None:
        while not self._stop.is_set():
            try:
                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-compute-apps=pid,used_memory",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=1.0,
                )
                for line in out.splitlines():
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) >= 2 and int(parts[0]) == self.pid:
                        value = float(parts[1])
                        self.peak_mib = (
                            value if self.peak_mib is None else max(self.peak_mib, value)
                        )
            except Exception:
                pass
            self._stop.wait(self.interval_s)


def _nvidia_smi_available() -> bool:
    try:
        subprocess.run(
            ["nvidia-smi", "-L"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.0,
            check=False,
        )
        return True
    except Exception:
        return False


def _sync(backend: Backend) -> None:
    if backend.is_gpu():
        backend.xp.cuda.Device().synchronize()


def _time_block(backend: Backend, func) -> TimedResult:
    _sync(backend)
    with GpuProcessSampler() as sampler:
        start = time.perf_counter()
        payload = func()
        _sync(backend)
        elapsed = time.perf_counter() - start
    return TimedResult(payload=payload, elapsed_s=elapsed, proc_peak_mib=sampler.peak_mib)


def _pool_stats(backend: Backend) -> dict:
    if not backend.is_gpu():
        return {"pool_total_mib": None, "pool_used_mib": None}
    pool = backend.xp.get_default_memory_pool()
    return {
        "pool_total_mib": pool.total_bytes() / (1024 ** 2),
        "pool_used_mib": pool.used_bytes() / (1024 ** 2),
    }


def _clear_pool(backend: Backend) -> None:
    if backend.is_gpu():
        backend.xp.get_default_memory_pool().free_all_blocks()
        backend.xp.get_default_pinned_memory_pool().free_all_blocks()
        _sync(backend)


def _make_fields(grid: Grid, rhs_count: int, seed: int):
    rng = np.random.default_rng(seed)
    axes = [np.linspace(0.0, 1.0, n + 1) for n in grid.N]
    xx, yy = np.meshgrid(axes[0], axes[1], indexing="ij")
    rho = 1.0 + 0.25 * np.sin(2.0 * np.pi * xx) * np.cos(2.0 * np.pi * yy)
    rho += 0.05 * rng.standard_normal(grid.shape)
    rho = np.maximum(rho, 0.2)

    rhs_fields = []
    for _ in range(rhs_count):
        rhs = rng.standard_normal(grid.shape)
        rhs -= float(rhs.mean())
        rhs_fields.append(rhs)
    return rho, rhs_fields


def _make_config(n: int, *, method: str, tolerance: float, maxiter: int) -> SimulationConfig:
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)),
        solver=SolverConfig(
            ppe_solver_type="fd_iterative" if method == "cg" else "fd_direct",
            pseudo_tol=tolerance,
            pseudo_maxiter=maxiter,
        ),
    )
    cfg.solver.ppe_iteration_method = method
    cfg.solver.ppe_preconditioner = "jacobi"
    return cfg


def _relative_norm(backend: Backend, arr, ref) -> float:
    xp = backend.xp
    numerator = float(backend.asnumpy(xp.linalg.norm(xp.asarray(arr).ravel())))
    denominator = float(backend.asnumpy(xp.linalg.norm(xp.asarray(ref).ravel())))
    return numerator / max(denominator, 1.0e-300)


def _residual_rel(backend: Backend, solver, pressure, rhs) -> float:
    xp = backend.xp
    rhs_dev = xp.asarray(rhs).copy()
    rhs_dev.ravel()[solver._pin_dof] = 0.0
    residual = solver.apply(xp.asarray(pressure)) - rhs_dev
    return _relative_norm(backend, residual, rhs_dev)


def _benchmark_direct(backend: Backend, grid: Grid, rho, rhs_fields: list) -> tuple[dict, list]:
    solver = PPESolverFDDirect(backend, grid, bc_type="wall")
    rho_dev = backend.xp.asarray(rho)
    rhs_dev = [backend.xp.asarray(rhs) for rhs in rhs_fields]

    def run():
        _sync(backend)
        t0 = time.perf_counter()
        solver.prepare_operator(rho_dev)
        _sync(backend)
        setup_s = time.perf_counter() - t0
        solutions = []
        solve_times = []
        for rhs in rhs_dev:
            _sync(backend)
            s0 = time.perf_counter()
            solutions.append(solver.solve(rhs, rho_dev, dt=1.0))
            _sync(backend)
            solve_times.append(time.perf_counter() - s0)
        return {
            "setup_s": setup_s,
            "solve_s": float(sum(solve_times)),
            "solve_mean_s": float(np.mean(solve_times)),
            "solutions": solutions,
        }

    measured = _time_block(backend, run)
    payload = measured.payload
    solutions = payload.pop("solutions")
    pool_stats = _pool_stats(backend)
    residual_solver = _matrixfree_reference(backend, grid, rho)
    residual_rel_max = max(
        _residual_rel(backend, residual_solver, sol, rhs)
        for sol, rhs in zip(solutions, rhs_fields)
    )
    payload.update(pool_stats)
    payload.update(
        {
            "method": "fd_direct",
            "tolerance": 0.0,
            "total_s": measured.elapsed_s,
            "proc_peak_mib": measured.proc_peak_mib,
            "residual_rel_max": residual_rel_max,
            "rel_error_vs_direct_max": 0.0,
            "status": "ok",
        }
    )
    return payload, solutions


def _matrixfree_reference(backend: Backend, grid: Grid, rho):
    cfg = _make_config(grid.N[0], method="cg", tolerance=1.0e-8, maxiter=1)
    solver = PPESolverFDMatrixFree(backend, cfg, grid, bc_type="wall")
    solver.prepare_operator(backend.xp.asarray(rho))
    return solver


def _benchmark_cg(
    backend: Backend,
    grid: Grid,
    rho,
    rhs_fields: list,
    direct_solutions: list,
    *,
    tolerance: float,
    maxiter: int,
) -> dict:
    cfg = _make_config(grid.N[0], method="cg", tolerance=tolerance, maxiter=maxiter)
    solver = PPESolverFDMatrixFree(backend, cfg, grid, bc_type="wall")
    rho_dev = backend.xp.asarray(rho)
    rhs_dev = [backend.xp.asarray(rhs) for rhs in rhs_fields]

    def run():
        solutions = []
        solve_times = []
        diagnostics = []
        for rhs in rhs_dev:
            _sync(backend)
            s0 = time.perf_counter()
            solutions.append(solver.solve(rhs, rho_dev, dt=1.0))
            _sync(backend)
            solve_times.append(time.perf_counter() - s0)
            diagnostics.append(dict(getattr(solver, "last_diagnostics", {})))
        return {
            "setup_s": 0.0,
            "solve_s": float(sum(solve_times)),
            "solve_mean_s": float(np.mean(solve_times)),
            "solutions": solutions,
            "diagnostics": diagnostics,
        }

    try:
        measured = _time_block(backend, run)
    except Exception as exc:
        return {
            "method": "fd_cg",
            "tolerance": tolerance,
            "status": f"failed: {type(exc).__name__}: {exc}",
            "total_s": math.nan,
            "setup_s": 0.0,
            "solve_s": math.nan,
            "solve_mean_s": math.nan,
            "proc_peak_mib": None,
            **_pool_stats(backend),
        }
    payload = measured.payload
    solutions = payload.pop("solutions")
    payload.update(_pool_stats(backend))
    payload.update(
        {
            "method": "fd_cg",
            "tolerance": tolerance,
            "total_s": measured.elapsed_s,
            "proc_peak_mib": measured.proc_peak_mib,
            "residual_rel_max": max(
                _residual_rel(backend, solver, sol, rhs)
                for sol, rhs in zip(solutions, rhs_fields)
            ),
            "rel_error_vs_direct_max": max(
                _relative_norm(backend, sol - backend.xp.asarray(ref), ref)
                for sol, ref in zip(solutions, direct_solutions)
            ),
            "status": "ok",
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="64,128")
    parser.add_argument("--cg-tols", default="1e-6,1e-8")
    parser.add_argument("--rhs-count", type=int, default=3)
    parser.add_argument("--maxiter", type=int, default=2000)
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument(
        "--output",
        default="experiment/ch14/results/fd_ll_solver_bench/fd_ll_solver_bench.json",
    )
    args = parser.parse_args()

    backend = Backend()
    sizes = [int(value) for value in args.sizes.split(",") if value.strip()]
    tolerances = [float(value) for value in args.cg_tols.split(",") if value.strip()]
    rows: list[dict] = []
    if not args.no_warmup:
        warm_cfg = _make_config(16, method="cg", tolerance=1.0e-4, maxiter=200)
        warm_grid = Grid(warm_cfg.grid, backend)
        warm_rho, warm_rhs = _make_fields(warm_grid, 1, args.seed)
        _warm_direct, warm_solutions = _benchmark_direct(backend, warm_grid, warm_rho, warm_rhs)
        warm_refs = [np.asarray(backend.asnumpy(solution)) for solution in warm_solutions]
        _benchmark_cg(
            backend,
            warm_grid,
            warm_rho,
            warm_rhs,
            warm_refs,
            tolerance=1.0e-4,
            maxiter=200,
        )
        _clear_pool(backend)
    for n in sizes:
        _clear_pool(backend)
        cfg = _make_config(n, method="cg", tolerance=1.0e-8, maxiter=args.maxiter)
        grid = Grid(cfg.grid, backend)
        rho, rhs_fields = _make_fields(grid, args.rhs_count, args.seed + n)
        direct_row, direct_solutions_dev = _benchmark_direct(backend, grid, rho, rhs_fields)
        direct_solutions = [
            np.asarray(backend.asnumpy(solution)) for solution in direct_solutions_dev
        ]
        direct_row["n"] = n
        direct_row["device"] = backend.device
        direct_row["rhs_count"] = args.rhs_count
        rows.append(direct_row)
        del direct_solutions_dev
        for tol in tolerances:
            _clear_pool(backend)
            cg_row = _benchmark_cg(
                backend,
                grid,
                rho,
                rhs_fields,
                direct_solutions=direct_solutions,
                tolerance=tol,
                maxiter=args.maxiter,
            )
            cg_row["n"] = n
            cg_row["device"] = backend.device
            cg_row["rhs_count"] = args.rhs_count
            rows.append(cg_row)
            _clear_pool(backend)
        del direct_solutions

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "device": backend.device,
        "sizes": sizes,
        "cg_tolerances": tolerances,
        "rhs_count": args.rhs_count,
        "maxiter": args.maxiter,
        "rows": rows,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
