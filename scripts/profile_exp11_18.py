#!/usr/bin/env python3
"""Profiling harness for exp11_18 CuPy tuning.

Measures:
  - wall-clock per test section (A/B/C)
  - host-sync count via cupy.ndarray monkey-patch (TWOPHASE_PROFILE_SYNCS=1)

Usage:
  TWOPHASE_USE_GPU=1 TWOPHASE_PROFILE_SYNCS=1 python scripts/profile_exp11_18.py
  TWOPHASE_USE_GPU=0 python scripts/profile_exp11_18.py  # CPU wall-clock only
"""
from __future__ import annotations

import os
import sys
import time
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiment" / "ch11"))


# ── Sync counter (monkey-patch) ──────────────────────────────────────────

class SyncCounter:
    def __init__(self):
        self.count = 0
        self.by_kind = {}

    def bump(self, kind: str):
        self.count += 1
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1

    def reset(self):
        self.count = 0
        self.by_kind = {}


_COUNTER = SyncCounter()


def _install_sync_counter():
    """Wrap cupy.ndarray host-sync methods with counting decorators.

    Only installed when TWOPHASE_PROFILE_SYNCS=1 and cupy is importable.
    """
    try:
        import cupy as cp
    except ImportError:
        return False

    _orig_float = cp.ndarray.__float__
    _orig_bool = cp.ndarray.__bool__
    _orig_item = cp.ndarray.item
    _orig_get = cp.ndarray.get

    def _counted_float(self):
        _COUNTER.bump("float")
        return _orig_float(self)

    def _counted_bool(self):
        _COUNTER.bump("bool")
        return _orig_bool(self)

    def _counted_item(self, *a, **kw):
        _COUNTER.bump("item")
        return _orig_item(self, *a, **kw)

    def _counted_get(self, *a, **kw):
        _COUNTER.bump("get")
        return _orig_get(self, *a, **kw)

    cp.ndarray.__float__ = _counted_float
    cp.ndarray.__bool__ = _counted_bool
    cp.ndarray.item = _counted_item
    cp.ndarray.get = _counted_get
    return True


# ── Wall-clock helper with device sync ──────────────────────────────────

def _sync_device():
    try:
        import cupy as cp
        cp.cuda.runtime.deviceSynchronize()
    except Exception:
        pass


class Timer:
    def __init__(self, label: str):
        self.label = label
        self.elapsed_ms = 0.0
        self.syncs = 0

    def __enter__(self):
        _sync_device()
        _COUNTER.reset()
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        _sync_device()
        self.elapsed_ms = (time.perf_counter() - self._t0) * 1000.0
        self.syncs = _COUNTER.count


# ── Main ────────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ns-A", type=int, nargs="+", default=[64, 128])
    ap.add_argument("--Ns-B", type=int, nargs="+", default=[64])
    ap.add_argument("--reinit-freq-B", type=int, default=10)
    ap.add_argument("--N-C", type=int, default=64)
    ap.add_argument("--freqs-C", type=int, nargs="+", default=[5, 10])
    ap.add_argument("--skip-B", action="store_true")
    ap.add_argument("--skip-C", action="store_true")
    args = ap.parse_args()

    profile_syncs = os.environ.get("TWOPHASE_PROFILE_SYNCS", "0") == "1"
    sync_active = profile_syncs and _install_sync_counter()

    # Import after monkey-patch install so counts are captured
    import exp11_18_cls_dccd_conservation as exp

    rows = []

    with Timer("Test A (DCCD sum)") as t:
        exp.test_dccd_sum_property(Ns=args.Ns_A)
    rows.append(t)

    if not args.skip_B:
        with Timer("Test B (convergence)") as t:
            exp.test_convergence(Ns=args.Ns_B, reinit_freq=args.reinit_freq_B)
        rows.append(t)

    if not args.skip_C:
        with Timer("Test C (reinit sens.)") as t:
            exp.test_reinit_sensitivity(N=args.N_C, freqs=args.freqs_C)
        rows.append(t)

    print("\n" + "=" * 64)
    print(f"{'section':<28} {'wall_ms':>12} {'syncs':>10}")
    print("-" * 64)
    for r in rows:
        syncs_str = f"{r.syncs}" if sync_active else "n/a"
        print(f"{r.label:<28} {r.elapsed_ms:>12.1f} {syncs_str:>10}")
    print("=" * 64)

    if sync_active and _COUNTER.by_kind:
        print("Sync breakdown (last section):", _COUNTER.by_kind)


if __name__ == "__main__":
    main()
