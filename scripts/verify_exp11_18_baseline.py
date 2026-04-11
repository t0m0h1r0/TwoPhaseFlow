#!/usr/bin/env python3
"""Verify exp11_18 outputs against committed CPU baseline (PR-5 bit-exactness).

Runs Test A (subset), Test B (N=64 fast), Test C (N=64 subset) on current code,
compares each numeric field against experiment/ch11/results/18_cls_dccd_conservation/data.npz.

Tolerances:
  - L2, Linf, mass_err: relative <= 1e-13, absolute <= 1e-15
  - sum_periodic, sum_wall: absolute <= 1e-12
"""
from __future__ import annotations
import sys
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiment" / "ch11"))

import exp11_18_cls_dccd_conservation as exp  # noqa: E402


BASELINE = ROOT / "experiment/ch11/results/18_cls_dccd_conservation/data.npz"


def _get_entry(arr, key, value):
    for e in arr:
        if e[key] == value:
            return e
    raise KeyError(f"{key}={value} not found")


def _cmp(label, got, want, rtol=1e-13, atol=1e-15):
    if isinstance(want, (int, float)) and abs(want) < 1e-12:
        ok = abs(got - want) <= max(atol, abs(want) * rtol + 1e-14)
    else:
        ok = abs(got - want) <= max(atol, abs(want) * rtol)
    status = "OK " if ok else "FAIL"
    print(f"  [{status}] {label}: got={got:.15e} want={want:.15e} diff={got - want:+.3e}")
    return ok


def main():
    base = np.load(BASELINE, allow_pickle=True)
    all_ok = True

    # Test A: N=64 only (fast)
    print("== Test A ==")
    rA = exp.test_dccd_sum_property(Ns=[64])
    want = _get_entry(base["test_a"], "N", 64)
    all_ok &= _cmp("sum_periodic N=64", rA[0]["sum_periodic"], want["sum_periodic"], atol=5e-14)
    all_ok &= _cmp("sum_wall     N=64", rA[0]["sum_wall"],     want["sum_wall"],     atol=5e-14)

    # Test B: N=64 all 4 configs
    print("== Test B (N=64) ==")
    rB = exp.test_convergence(Ns=[64], reinit_freq=10)
    for cfg in ("split", "split+mc", "unified", "unified+mc"):
        want = _get_entry(base[f"test_b__{cfg}"], "N", 64)
        got = rB[cfg][0]
        print(f"  -- {cfg} --")
        all_ok &= _cmp("L2      ", got["L2"],       want["L2"])
        all_ok &= _cmp("Linf    ", got["Linf"],     want["Linf"])
        all_ok &= _cmp("mass_err", got["mass_err"], want["mass_err"], atol=1e-14)

    # Test C: freq=10 only
    print("== Test C (N=64, freq=10) ==")
    rC = exp.test_reinit_sensitivity(N=64, freqs=[10])
    for cfg in ("split+mc", "unified+mc"):
        want = _get_entry(base[f"test_c__{cfg}"], "freq", 10)
        got = rC[cfg][0]
        print(f"  -- {cfg} --")
        all_ok &= _cmp("L2      ", got["L2"],       want["L2"])
        all_ok &= _cmp("Linf    ", got["Linf"],     want["Linf"])
        all_ok &= _cmp("mass_err", got["mass_err"], want["mass_err"], atol=1e-14)

    print("\n" + ("ALL PASS" if all_ok else "FAIL — bit-exactness broken"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
