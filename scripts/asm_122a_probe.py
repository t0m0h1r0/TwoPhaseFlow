#!/usr/bin/env python3
"""ASM-122A Split GPU/CPU drift diagnostic probe.

Plan: .claude/plans/snoopy-mapping-hoare.md  (CHK-124, 2026-04-11)

Reproduces exp11_21 Zalesak single-case step loop at reduced N and records
per-cycle drift signatures under 4 monkey-patched probes:

  1. baseline      — current Split hot path (no patch)
  2. clip-deadband — replaces xp.clip(q, 0, 1) with dead-band variant
  3. cn-adi-cpu    — forces GPU CN-ADI through Python Thomas branch
  4. ccd-no-ainv   — forces CCD wall-BC solver through lu_solve branch

Probes 3 and 4 are no-ops on the CPU backend (the GPU branches they target
are not taken). Probe 2 is backend-neutral. Probe 1 is the baseline.

The probe runs the same Zalesak step loop twice in a single process (pass
"A" and pass "B"), compares ψ snapshots at fixed checkpoints, and writes
per-checkpoint metrics to CSV. For Phase A smoke (CPU-only), both passes
use the NumPy backend and the reported drift should be identically zero,
which validates the harness shape. For Phase B diagnosis, pass A is CPU
and pass B is GPU (via TWOPHASE_USE_GPU=1) and the reported drift is the
real signal.

Usage (local CPU smoke, ≤30 s):
  python scripts/asm_122a_probe.py --probe baseline --N 64 --n-steps 100

Usage (remote GPU, Phase B):
  make run EXP=scripts/asm_122a_probe.py ARGS="--probe baseline --N 64 --n-steps 800"
  (repeat for --probe clip-deadband / cn-adi-cpu / ccd-no-ainv)

Zero src/twophase/ edits — all probes are runtime monkey-patches applied
only within this script. Paper-exact reference (PR-5) lives in src/; this
harness is diagnostic-only.
"""
from __future__ import annotations

import argparse
import csv
import os
import pathlib
import sys
import time
from typing import Callable, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside
from twophase.initial_conditions.shapes import ZalesakDisk
from twophase.initial_conditions.velocity_fields import RigidRotation


PROBES = ("baseline", "clip-deadband", "cn-adi-cpu", "ccd-no-ainv", "matmul-all-cpu")


# ── Probe 2: clip-deadband ────────────────────────────────────────────────
#
# Replace the two xp.clip(q, 0, 1) sites in SplitReinitizer.reinitialize
# with a dead-band variant:
#
#     q_db = xp.where((q > DEAD) & (q < 1 - DEAD), q, xp.clip(q, 0, 1))
#
# Rationale: the hypothesis is that ~1e-11 pointwise noise from CN-ADI
# matmul can push one side of the clip boundary to snap while the other
# does not, amplifying to O(1) at slot-edge cells. A dead band stabilizes
# the branch decision by treating anything within [DEAD, 1-DEAD] as
# interior (unclipped). If drift drops to ~1e-9 under this probe, the
# clip boundary is confirmed as the chaotic amplifier.

_DEAD = 1e-9


def _install_clip_deadband(split_reinit) -> Callable[[], None]:
    """Swap SplitReinitizer.reinitialize with a dead-band clip variant.

    Returns an unpatch() callable to restore the original method.
    """
    xp = split_reinit.xp
    orig = split_reinit.reinitialize

    def db_clip(q):
        return xp.where((q > _DEAD) & (q < 1.0 - _DEAD), q, xp.clip(q, 0.0, 1.0))

    def patched_reinitialize(psi):
        from twophase.levelset.reinit_ops import dccd_compression_div, cn_diffusion_axis
        from twophase.levelset.heaviside import apply_mass_correction

        q = xp.copy(psi)
        dV = split_reinit._dV
        M_old = xp.sum(q * dV)

        for _ in range(split_reinit.n_steps):
            div_comp = dccd_compression_div(
                xp, q, split_reinit.ccd, split_reinit.grid,
                split_reinit._bc, split_reinit._eps_d_comp,
            )
            q_star = db_clip(q - split_reinit.dtau * div_comp)

            q_new = q_star
            for ax in range(split_reinit.grid.ndim):
                q_new = cn_diffusion_axis(
                    xp, q_new, ax, split_reinit.eps, split_reinit.dtau,
                    split_reinit._h[ax], split_reinit._cn_factors[ax],
                )
            q = db_clip(q_new)

        if split_reinit._mass_correction:
            q = apply_mass_correction(xp, q, dV, M_old)

        return q

    split_reinit.reinitialize = patched_reinitialize

    def unpatch():
        split_reinit.reinitialize = orig

    return unpatch


# ── Probe 3: cn-adi-cpu ───────────────────────────────────────────────────
#
# Force the SplitReinitizer CN-ADI hot path through the CPU Python Thomas
# branch even when backend.is_gpu(). We do this by zeroing the cached
# A_inv_dev tensor in each axis's cn_factors tuple. reinit_ops.cn_diffusion_axis
# then takes the else branch. No-op on CPU (A_inv_dev is already None).

def _install_cn_adi_cpu(split_reinit) -> Callable[[], None]:
    orig_factors = list(split_reinit._cn_factors)
    patched = []
    for f in orig_factors:
        thomas_f, m_diag, sup, A_inv_dev = f
        patched.append((thomas_f, m_diag, sup, None))
    split_reinit._cn_factors = patched

    def unpatch():
        split_reinit._cn_factors = orig_factors

    return unpatch


# ── Probe 4: ccd-no-ainv ──────────────────────────────────────────────────
#
# Force the CCD wall-BC solver to skip the GPU A_inv_dev @ rhs_flat matmul
# path and fall through to lu_solve (CHK-119's pre-round-5 codepath). We
# monkey-patch the CCDSolver's _axis_info dicts so info['A_inv_dev'] is
# replaced with None, then override _differentiate_wall_raw to route around
# the `if backend.device == "gpu"` check.
#
# No-op on CPU (the GPU branch is not taken).

class _LuSolveViaMatmul:
    """Proxy whose ``@`` operator invokes lu_solve instead of a dense matmul.

    Substituted for ``info['A_inv_dev']`` in the probe-4 monkey-patch: the
    existing ``x_flat = info['A_inv_dev'] @ rhs_flat`` site transparently
    routes through ``backend.linalg.lu_solve((lu, piv), rhs_flat)`` without
    touching the dispatch branch or the method body.
    """

    __slots__ = ("backend", "lu", "piv")

    def __init__(self, backend, lu, piv):
        self.backend = backend
        self.lu = lu
        self.piv = piv

    def __matmul__(self, rhs_flat):
        return self.backend.linalg.lu_solve((self.lu, self.piv), rhs_flat)


def _install_ccd_no_ainv(ccd) -> Callable[[], None]:
    if ccd.backend.device != "gpu":
        return lambda: None  # no-op on CPU

    # CCDSolver caches per-axis solver state in self._solvers (wall BC) and
    # self._periodic_solvers (periodic BC). Each entry is an info dict
    # containing 'A_inv_dev', 'lu', 'piv', ... (ccd_solver.py:283+).
    saved: list = []
    for cache_name in ("_solvers", "_periodic_solvers"):
        cache = getattr(ccd, cache_name, None) or {}
        for ax_key, info in cache.items():
            orig = info.get('A_inv_dev', None)
            if orig is None:
                continue  # already on lu_solve path; nothing to swap
            saved.append((cache_name, ax_key, orig))
            info['A_inv_dev'] = _LuSolveViaMatmul(
                ccd.backend, info['lu'], info['piv'],
            )

    def unpatch():
        for cache_name, ax_key, orig in saved:
            getattr(ccd, cache_name)[ax_key]['A_inv_dev'] = orig

    return unpatch


# ── Probe harness ─────────────────────────────────────────────────────────

def _build_case(backend: Backend, N: int, eps_ratio: float = 1.0):
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h
    X, Y = grid.meshgrid()

    xp = backend.xp
    X_h, Y_h = backend.to_host(X), backend.to_host(Y)
    phi0_h = ZalesakDisk(center=(0.5, 0.75), radius=0.15,
                        slot_width=0.05, slot_depth=0.25).sdf(X_h, Y_h)
    phi0 = xp.asarray(phi0_h)
    psi0 = heaviside(xp, phi0, eps)

    T = 2 * np.pi
    vf = RigidRotation(center=(0.5, 0.5), period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero", eps_d=0.05,
                                  mass_correction=True)
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="zero",
                           method="split")

    return grid, ccd, adv, reinit, psi0, vf, X, Y, h


def _apply_probe(probe: str, split_reinit, ccd) -> Callable[[], None]:
    if probe == "baseline":
        return lambda: None
    if probe == "clip-deadband":
        return _install_clip_deadband(split_reinit)
    if probe == "cn-adi-cpu":
        return _install_cn_adi_cpu(split_reinit)
    if probe == "ccd-no-ainv":
        return _install_ccd_no_ainv(ccd)
    if probe == "matmul-all-cpu":
        # Additivity cross-check: cn-adi-cpu AND ccd-no-ainv active together.
        # If drift drops ~= (probe3 drop + probe4 drop), the two matmul
        # sources are independent and the residual is chaos-dominated
        # (FUNDAMENTAL classification). If drift drops >> sum, they couple
        # and at least one is structural.
        un3 = _install_cn_adi_cpu(split_reinit)
        un4 = _install_ccd_no_ainv(ccd)

        def unpatch():
            un4()
            un3()

        return unpatch
    raise ValueError(f"unknown probe: {probe}")


def _clip_counts(xp, psi) -> Tuple[int, int]:
    low = int(xp.sum(psi < 1e-12))
    high = int(xp.sum(psi > 1.0 - 1e-12))
    return low, high


def run_pass(backend: Backend, N: int, n_steps_cap: int, probe: str,
             checkpoint_every: int) -> List[dict]:
    """Single end-to-end pass. Returns a list of checkpoint dicts."""
    grid, ccd, adv, reinit, psi0, vf, X, Y, h = _build_case(backend, N)
    xp = backend.xp
    dV = xp.asarray(grid.cell_volumes())

    unpatch = _apply_probe(probe, reinit._strategy, ccd)

    try:
        T = 2 * np.pi
        dt = 0.45 / N
        n_steps_full = int(T / dt)
        n_steps = min(n_steps_full, n_steps_cap)
        dt = T / n_steps_full  # keep step size consistent with exp11_21

        reinit_freq = 20
        u, v = vf.compute(X, Y, t=0.0)

        psi = psi0.copy()
        records: List[dict] = []
        t0 = time.perf_counter()
        for step in range(n_steps):
            psi = adv.advance(psi, [u, v], dt)
            if (step + 1) % reinit_freq == 0:
                psi = reinit.reinitialize(psi)

            if (step + 1) % checkpoint_every == 0 or step == n_steps - 1:
                mass = float(xp.sum(psi * dV))
                low, high = _clip_counts(xp, psi)
                records.append({
                    "step": step + 1,
                    "mass": mass,
                    "clip_low": low,
                    "clip_high": high,
                    "psi_host": backend.to_host(psi).copy(),
                })
        wall = time.perf_counter() - t0
        records.append({"step": -1, "wall_s": wall})  # trailing row
        return records
    finally:
        unpatch()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", choices=PROBES, default="baseline")
    ap.add_argument("--N", type=int, default=64)
    ap.add_argument("--n-steps", type=int, default=100,
                    help="cap on advection steps (Phase A smoke: 100; "
                         "Phase B full: 800 at N=64 or 1788 at N=128)")
    ap.add_argument("--checkpoint-every", type=int, default=20,
                    help="record drift snapshot every K advection steps")
    ap.add_argument("--out-dir", type=pathlib.Path,
                    default=ROOT / "experiment" / "ch11" / "results" / "asm_122a")
    ap.add_argument("--pass-b", choices=("cpu", "gpu"), default="cpu",
                    help="Phase A smoke uses cpu/cpu (diff should be 0). "
                         "Phase B diagnosis uses cpu/gpu to measure drift.")
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[ASM-122A probe] N={args.N} n_steps={args.n_steps} probe={args.probe} "
          f"pass-b={args.pass_b} → {args.out_dir}")

    # Pass A = CPU reference
    backend_a = Backend(use_gpu=False)
    print(f"  [pass A] CPU baseline ({backend_a.device}) ...")
    records_a = run_pass(backend_a, args.N, args.n_steps, args.probe,
                         args.checkpoint_every)

    # Pass B = CPU (smoke) or GPU (diagnosis)
    use_gpu_b = args.pass_b == "gpu"
    backend_b = Backend(use_gpu=use_gpu_b)
    print(f"  [pass B] {'GPU' if use_gpu_b else 'CPU'} ({backend_b.device}) ...")
    records_b = run_pass(backend_b, args.N, args.n_steps, args.probe,
                         args.checkpoint_every)

    # Compare paired checkpoints (drop trailing wall-time sentinel)
    ckpts_a = [r for r in records_a if r["step"] != -1]
    ckpts_b = [r for r in records_b if r["step"] != -1]
    assert len(ckpts_a) == len(ckpts_b), \
        f"checkpoint count mismatch: A={len(ckpts_a)} B={len(ckpts_b)}"

    csv_path = args.out_dir / f"{args.probe}_{args.pass_b}.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "step", "mass_a", "mass_b", "mass_diff",
            "clip_low_a", "clip_low_b", "clip_high_a", "clip_high_b",
            "max_abs", "max_rel", "l2_abs",
        ])
        for ra, rb in zip(ckpts_a, ckpts_b):
            pa = ra["psi_host"].astype(np.float64)
            pb = rb["psi_host"].astype(np.float64)
            diff = pb - pa
            max_abs = float(np.max(np.abs(diff)))
            denom = np.maximum(np.abs(pa), 1e-12)
            max_rel = float(np.max(np.abs(diff) / denom))
            l2_abs = float(np.sqrt(np.mean(diff ** 2)))
            w.writerow([
                ra["step"],
                f"{ra['mass']:.16e}", f"{rb['mass']:.16e}",
                f"{rb['mass'] - ra['mass']:.3e}",
                ra["clip_low"], rb["clip_low"],
                ra["clip_high"], rb["clip_high"],
                f"{max_abs:.6e}", f"{max_rel:.6e}", f"{l2_abs:.6e}",
            ])

    wall_a = records_a[-1]["wall_s"]
    wall_b = records_b[-1]["wall_s"]
    print(f"  wall: A={wall_a:.2f}s  B={wall_b:.2f}s")

    last = ckpts_a[-1], ckpts_b[-1]
    pa = last[0]["psi_host"].astype(np.float64)
    pb = last[1]["psi_host"].astype(np.float64)
    diff = pb - pa
    max_abs = float(np.max(np.abs(diff)))
    max_rel = float(np.max(np.abs(diff) / np.maximum(np.abs(pa), 1e-12)))
    l2_abs = float(np.sqrt(np.mean(diff ** 2)))
    print(f"  final step={last[0]['step']}  max_abs={max_abs:.3e}  "
          f"max_rel={max_rel:.3e}  L2_abs={l2_abs:.3e}")
    print(f"  csv: {csv_path}")

    # Phase A smoke gate: cpu/cpu must give bit-exact zero drift.
    if args.pass_b == "cpu" and max_abs > 0.0:
        print(f"  [WARN] pass-b=cpu but drift > 0: max_abs={max_abs:.3e} — "
              "harness determinism regressed!")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
