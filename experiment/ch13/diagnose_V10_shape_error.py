#!/usr/bin/env python3
"""Diagnose V10-a/b CLS shape-error mechanisms.

This script is a measurement probe, not a remedy.  It keeps the Chapter 13
V10 FCCD/TVD-RK3 transport path and varies only geometry, resolution, CFL,
mass correction, and reinitialization knobs that separate mathematical
hypotheses about shape loss.

Usage
-----
  make run EXP=experiment/ch13/diagnose_V10_shape_error.py
  make run EXP=experiment/ch13/diagnose_V10_shape_error.py ARGS=--plot-only
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import numpy as np

import exp_V10_cls_advection_nonuniform as v10
from twophase.tools.experiment import experiment_argparser, experiment_dir, load_results, save_results

OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

ZALESAK_CASES = (
    ("slot_N64", {"N": 64, "alpha": 1.0}),
    ("slot_N128", {"N": 128, "alpha": 1.0}),
    ("circle_N128", {"N": 128, "alpha": 1.0, "shape": "circle"}),
    ("wide_slot_N128", {"N": 128, "alpha": 1.0, "slot_width": 0.10}),
    ("slot_N128_no_mc", {"N": 128, "alpha": 1.0, "mass_correction_every": 0}),
    ("slot_N128_mc1", {"N": 128, "alpha": 1.0, "mass_correction_every": 1}),
    ("slot_N128_cfl_half", {"N": 128, "alpha": 1.0, "cfl": 0.125}),
    ("slot_N128_eps1", {"N": 128, "alpha": 1.0, "eps_ratio": 1.0}),
)

SINGLE_VORTEX_CASES = (
    ("sv_N64_T1", {"N": 64, "alpha": 1.0, "T": 1.0, "phase_divisions": 16}),
    ("sv_N64_T2", {"N": 64, "alpha": 1.0, "T": 2.0, "phase_divisions": 16}),
    ("sv_N64_T4", {"N": 64, "alpha": 1.0, "T": 4.0, "phase_divisions": 16}),
    ("sv_N64_T8", {"N": 64, "alpha": 1.0, "T": 8.0, "phase_divisions": 16}),
    ("sv_N64_T8_no_reinit", {
        "N": 64, "alpha": 1.0, "T": 8.0, "phase_divisions": 16,
        "reinit_every": 0,
    }),
    ("sv_N64_T8_reinit1", {
        "N": 64, "alpha": 1.0, "T": 8.0, "phase_divisions": 16,
        "reinit_every": 1,
    }),
    ("sv_N64_T8_mass_off", {
        "N": 64, "alpha": 1.0, "T": 8.0, "phase_divisions": 16,
        "mass_correction": False,
    }),
    ("sv_N64_T8_cfl_half", {
        "N": 64, "alpha": 1.0, "T": 8.0, "phase_divisions": 16,
        "cfl": 0.125,
    }),
    ("sv_N128_T2", {"N": 128, "alpha": 1.0, "T": 2.0, "phase_divisions": 16}),
    ("sv_N128_T4", {"N": 128, "alpha": 1.0, "T": 4.0, "phase_divisions": 16}),
)


def _drop_fields(row: dict) -> dict:
    omitted = {
        "X", "Y", "psi0", "psi_T", "psi_half",
        "phase_psi", "phase_X", "phase_Y",
    }
    return {key: value for key, value in row.items() if key not in omitted}


def _threshold_width_proxy(psi: np.ndarray, h: float) -> tuple[float, float, float]:
    mask = np.asarray(psi) > 0.5
    area = float(np.sum(mask) * h * h)
    edge_x = np.count_nonzero(mask[1:, :] != mask[:-1, :])
    edge_y = np.count_nonzero(mask[:, 1:] != mask[:, :-1])
    perimeter = float((edge_x + edge_y) * h)
    width = float(2.0 * area / perimeter) if perimeter > 0.0 else float("nan")
    return area, perimeter, width


def _compact_zalesak(label: str, run: dict) -> dict:
    h = float(run["h_min"])
    eps = float(run["eps_ratio"]) * h
    return {
        **_drop_fields(run),
        "label": label,
        "slot_over_h": float(run["slot_width"] / h),
        "slot_over_eps": float(run["slot_width"] / eps),
    }


def _compact_single_vortex(label: str, run: dict) -> dict:
    h = float(run["h_min"])
    half = np.asarray(run["psi_half"])
    area_half, perimeter_half, width_half = _threshold_width_proxy(half, h)
    return {
        **_drop_fields(run),
        "label": label,
        "half_area": area_half,
        "half_perimeter": perimeter_half,
        "half_width_proxy": width_half,
        "half_width_over_h": float(width_half / h),
    }


def run_all() -> dict:
    zalesak: dict[str, dict] = {}
    for label, kwargs in ZALESAK_CASES:
        print(f"[V10-shape] Zalesak {label}")
        zalesak[label] = _compact_zalesak(label, v10._run(**kwargs))

    single_vortex: dict[str, dict] = {}
    for label, kwargs in SINGLE_VORTEX_CASES:
        print(f"[V10-shape] single-vortex {label}")
        single_vortex[label] = _compact_single_vortex(label, v10._run_single_vortex(**kwargs))

    return {
        "zalesak": zalesak,
        "single_vortex": single_vortex,
        "meta": {
            "purpose": "RA-CH13-V10-SHAPE diagnostic variants",
            "baseline_npz": "experiment/ch13/results/V10_cls_advection_nonuniform/data.npz",
        },
    }


def print_summary(results: dict) -> None:
    print("V10-a Zalesak diagnostic variants:")
    for label, row in results["zalesak"].items():
        print(
            f"  {label:>18}  N={int(row['N']):>3}  "
            f"cent={row['centroid_err']:.3e}  L1={row['shape_l1']:.3e}  "
            f"mass={row['volume_drift']:.3e}  slot/h={row['slot_over_h']:.2f}"
        )
    print("V10-b single-vortex diagnostic variants:")
    for label, row in results["single_vortex"].items():
        print(
            f"  {label:>18}  N={int(row['N']):>3}  T={row['T']:.1f}  "
            f"L1={row['reversal_l1']:.3e}  mass={row['volume_drift']:.3e}  "
            f"reinit={int(row['reinit_count']):>3}  w/h={row['half_width_over_h']:.2f}"
        )


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    print_summary(results)
    print(f"==> V10 diagnostic outputs in {OUT}")


if __name__ == "__main__":
    main()
