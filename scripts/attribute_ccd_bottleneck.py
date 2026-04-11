#!/usr/bin/env python3
"""Attribution profiler for exp11_18 hot path.

Runs a controlled number of DissipativeCCDAdvection.advance() calls and
times each stage with explicit cuda sync. Goal: confirm whether
CCDSolver._differentiate_wall_raw + BlockTridiagSolver.solve dominate,
or whether something else is the real bottleneck.

Stages measured:
  1. advance()          — full TVD-RK3 step (outer)
  2. _rhs()             — single RHS build (one RK stage)
  3. ccd.differentiate  — just CCDSolver._differentiate_wall_raw
  4. block_tridiag.solve — just the BlockTridiagSolver.solve inner body
  5. filter stencil     — _dccd_filter_stencil fused op
  6. RHS python-loop    — the for idx in range(n_int) rhs[...] assembly

Each stage is repeated `--reps` times with a cudaDeviceSynchronize before
and after to isolate the cost. All measurements are in microseconds.

Usage:
  TWOPHASE_USE_GPU=1 python scripts/attribute_ccd_bottleneck.py --N 64 --reps 50
  TWOPHASE_USE_GPU=0 python scripts/attribute_ccd_bottleneck.py --N 64 --reps 50
"""
from __future__ import annotations
import sys
import time
import pathlib
import argparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
from twophase.backend import Backend  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.ccd.ccd_solver import CCDSolver  # noqa: E402
from twophase.levelset.advection import DissipativeCCDAdvection  # noqa: E402
from twophase.levelset.heaviside import heaviside  # noqa: E402


def _sync():
    try:
        import cupy as cp
        cp.cuda.runtime.deviceSynchronize()
    except Exception:
        pass


class Measurement:
    __slots__ = ("label", "count", "us_per_call", "total_us")

    def __init__(self, label, count, total_us):
        self.label = label
        self.count = count
        self.total_us = total_us
        self.us_per_call = total_us / count if count else 0.0


def time_block(label, fn, warmup=3, reps=50):
    for _ in range(warmup):
        fn()
    _sync()
    t0 = time.perf_counter()
    for _ in range(reps):
        fn()
    _sync()
    total_us = (time.perf_counter() - t0) * 1e6
    return Measurement(label, reps, total_us)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--reps", type=int, default=50)
    ap.add_argument("--bc", default="wall", choices=["wall", "periodic"])
    args = ap.parse_args()

    backend = Backend()
    xp = backend.xp
    print(f"[info] backend device = {backend.device}, N={args.N}, bc={args.bc}, reps={args.reps}")

    gc = GridConfig(ndim=2, N=(args.N, args.N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type=args.bc)
    X, Y = grid.meshgrid()
    eps = 1.5 / args.N
    phi0 = xp.sqrt((X - 0.5) ** 2 + (Y - 0.75) ** 2) - 0.15
    psi = heaviside(xp, phi0, eps)

    # Velocity field (single vortex, t=0)
    u = xp.sin(xp.pi * X) ** 2 * xp.sin(2 * xp.pi * Y)
    v = -(xp.sin(xp.pi * Y) ** 2) * xp.sin(2 * xp.pi * X)

    adv = DissipativeCCDAdvection(
        backend, grid, ccd,
        bc="zero" if args.bc == "wall" else "periodic",
        eps_d=0.05, mass_correction=True,
    )
    dt = 0.45 / args.N

    results = []

    # 1. full advance()
    results.append(time_block(
        "advance() full step",
        lambda: adv.advance(psi, [u, v], dt),
        warmup=5, reps=args.reps,
    ))

    # 2. single _rhs()
    results.append(time_block(
        "_rhs() one RK stage",
        lambda: adv._rhs(psi, [u, v]),
        warmup=5, reps=args.reps,
    ))

    # 3. ccd.differentiate single axis (both axes summed)
    def _ccd_both_axes():
        for ax in range(2):
            ccd.differentiate(psi, axis=ax)

    results.append(time_block(
        "ccd.differentiate (both axes)",
        _ccd_both_axes,
        warmup=5, reps=args.reps,
    ))

    # 4. Inner linear solve isolated.
    # Post-CHK-117: wall-BC path uses a single dense (2·n_int)² LU factor
    # via backend.linalg.lu_solve, same pattern as periodic. Benchmark
    # that directly instead of the retired BlockTridiagSolver.
    info = ccd._solvers[0] if args.bc == "wall" else None
    if info is not None:
        n_int = info["n_int"]
        batch = args.N + 1
        rhs_flat = xp.zeros((2 * n_int, batch))
        lu = info["lu"]
        piv = info["piv"]
        lu_solve = backend.linalg.lu_solve

        results.append(time_block(
            "wall LU lu_solve",
            lambda: lu_solve((lu, piv), rhs_flat),
            warmup=5, reps=args.reps,
        ))

    # 5. Fused filter stencil
    from twophase.levelset.advection import _dccd_filter_stencil
    fp = xp.zeros_like(psi)
    fp_p1 = xp.zeros_like(psi)
    fp_m1 = xp.zeros_like(psi)
    results.append(time_block(
        "_dccd_filter_stencil",
        lambda: _dccd_filter_stencil(fp, fp_p1, fp_m1, 0.05),
        warmup=5, reps=args.reps,
    ))

    # 6. Raw CCD python-loop RHS build (wall BC only)
    if args.bc == "wall":
        _A1 = 15.0 / 16.0
        _A2 = -15.0 / 16.0
        h = info["h"]
        f_flat = psi.reshape(args.N + 1, -1)

        def _rhs_build():
            rhs_local = xp.zeros((n_int, 2, f_flat.shape[1]))
            for idx in range(n_int):
                i = idx + 1
                rhs_local[idx, 0, :] = (_A1 / h) * (f_flat[i + 1] - f_flat[i - 1])
                rhs_local[idx, 1, :] = (_A2 / (h * h)) * (
                    f_flat[i - 1] - 2.0 * f_flat[i] + f_flat[i + 1]
                )
            return rhs_local

        results.append(time_block(
            "python-loop RHS build",
            _rhs_build,
            warmup=5, reps=args.reps,
        ))

    # Print table
    print()
    print("=" * 74)
    print(f"{'stage':<40} {'reps':>6} {'us/call':>12} {'total ms':>12}")
    print("-" * 74)
    advance_us = None
    for r in results:
        if r.label == "advance() full step":
            advance_us = r.us_per_call
        print(f"{r.label:<40} {r.count:>6} {r.us_per_call:>12.1f} {r.total_us / 1000:>12.1f}")
    print("=" * 74)

    # Attribution: each stage as % of advance()
    if advance_us:
        print()
        print(f"-- attribution (% of advance() = {advance_us:.1f} us) --")
        # advance calls _rhs 3x (TVD-RK3), each _rhs does 2-axis CCD, each axis 1 filter
        print(f"  _rhs()          : 3× per advance   = {3 * results[1].us_per_call / advance_us * 100:.1f}% "
              f"(3× {results[1].us_per_call:.1f} us = {3 * results[1].us_per_call:.1f} us)")
        print(f"  ccd.diff 2-axes : 3× per advance   = {3 * results[2].us_per_call / advance_us * 100:.1f}% "
              f"(3× {results[2].us_per_call:.1f} us = {3 * results[2].us_per_call:.1f} us)")
        if args.bc == "wall":
            print(f"  wall lu_solve   : 6× per advance   = {6 * results[3].us_per_call / advance_us * 100:.1f}% "
                  f"(6× {results[3].us_per_call:.1f} us = {6 * results[3].us_per_call:.1f} us)")
            print(f"  filter stencil  : 6× per advance   = {6 * results[4].us_per_call / advance_us * 100:.1f}% "
                  f"(6× {results[4].us_per_call:.1f} us = {6 * results[4].us_per_call:.1f} us)")
            print(f"  py-loop RHS     : 6× per advance   = {6 * results[5].us_per_call / advance_us * 100:.1f}% "
                  f"(6× {results[5].us_per_call:.1f} us = {6 * results[5].us_per_call:.1f} us)")


if __name__ == "__main__":
    main()
