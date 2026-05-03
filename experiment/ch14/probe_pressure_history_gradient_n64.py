#!/usr/bin/env python3
"""Minimal pressure-history-gradient probe for the N=64 static droplet.

Theory target:
    In pressure-jump surface tension, the pressure gradient used by any
    predictor/projection stage must be the same jump-aware gradient
    ``G_Γ(p; j)=G(p)-B_Γ(j)`` that appears in the affine PPE.  A plain gradient
    of a Young--Laplace jump field is not a physical bulk acceleration.

This script is diagnostic only.  It compares the normal alpha-2 static route
against a monkey-patched route that removes the previous-pressure predictor
gradient.  The latter is not proposed as a fix; it tests whether the pressure
history gradient is a dominant injection path.
"""

from __future__ import annotations

import copy
import math
import pathlib
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import twophase.simulation.ns_pipeline as ns_pipeline  # noqa: E402
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    experiment_argparser,
    experiment_dir,
    load_results,
    save_results,
)


BASE_CONFIG = ROOT / "experiment/ch14/config/ch14_static_droplet_n64_alpha2_like_oscillating.yaml"
TARGET_FINAL = 0.40


@dataclass(frozen=True)
class ProbeCase:
    label: str
    hypothesis: str
    disable_previous_pressure_gradient: bool = False


def _cases() -> tuple[ProbeCase, ...]:
    return (
        ProbeCase(
            label="baseline",
            hypothesis="normal IPC predictor uses the stored previous pressure gradient",
        ),
        ProbeCase(
            label="no_prev_pressure_gradient",
            hypothesis=(
                "diagnostic: remove previous-pressure predictor gradient; "
                "if residual pressure drops, history gradient is an injection path"
            ),
            disable_previous_pressure_gradient=True,
        ),
    )


def _build_config(raw_base: dict, label: str) -> ExperimentConfig:
    raw = copy.deepcopy(raw_base)
    raw["run"]["time"]["final"] = TARGET_FINAL
    raw["run"]["time"]["print_every"] = 200
    raw["output"]["dir"] = f"results/ch14_pressure_history_gradient_n64/{label}"
    raw["output"]["snapshots"]["interval"] = 0.05
    raw["output"]["figures"] = []
    return ExperimentConfig.from_dict(raw)


@contextmanager
def _pressure_history_patch(disabled: bool):
    if not disabled:
        yield
        return

    original = ns_pipeline.compute_ns_predictor_stage

    def without_previous_pressure_gradient(state, **kwargs):
        state.previous_pressure = None
        return original(state, **kwargs)

    ns_pipeline.compute_ns_predictor_stage = without_previous_pressure_gradient
    try:
        yield
    finally:
        ns_pipeline.compute_ns_predictor_stage = original


def _phase_fraction(density: np.ndarray) -> np.ndarray:
    density_min = float(np.nanmin(density))
    density_max = float(np.nanmax(density))
    return (density - density_min) / max(density_max - density_min, 1.0e-300)


def _pressure_summary(snapshot: dict) -> dict[str, float]:
    pressure = np.asarray(snapshot["p"], dtype=float)
    phase_fraction = _phase_fraction(np.asarray(snapshot["rho"], dtype=float))
    liquid = phase_fraction > 0.95
    gas = phase_fraction < 0.05
    liquid_mean = float(np.mean(pressure[liquid]))
    gas_mean = float(np.mean(pressure[gas]))
    liquid_residual = pressure[liquid] - liquid_mean
    gas_residual = pressure[gas] - gas_mean
    jump = liquid_mean - gas_mean
    return {
        "snapshot_time": float(snapshot["t"]),
        "jump": jump,
        "jump_abs_error": abs(jump - 0.288),
        "liquid_residual_rms": math.sqrt(float(np.mean(liquid_residual * liquid_residual))),
        "gas_residual_rms": math.sqrt(float(np.mean(gas_residual * gas_residual))),
        "liquid_residual_max_abs": float(np.max(np.abs(liquid_residual))),
        "gas_residual_max_abs": float(np.max(np.abs(gas_residual))),
    }


def _array(results: dict, key: str) -> np.ndarray:
    value = results.get(key)
    if value is None:
        return np.asarray([], dtype=float)
    return np.asarray(value, dtype=float)


def _summarize(case: ProbeCase, results: dict, elapsed: float) -> dict[str, float | str]:
    times = _array(results, "times")
    kinetic_energy = _array(results, "kinetic_energy")
    volume = _array(results, "volume_conservation")
    deformation = _array(results, "deformation")
    snapshots = results.get("snapshots") or []
    pressure = _pressure_summary(snapshots[-1]) if snapshots else {}
    final_t = float(times[-1]) if times.size else float("nan")
    status = "COMPLETED" if final_t >= TARGET_FINAL - 1.0e-12 else "BLOWUP"
    row: dict[str, float | str] = {
        "label": case.label,
        "hypothesis": case.hypothesis,
        "status": status,
        "elapsed": elapsed,
        "steps": float(times.size),
        "final_t": final_t,
        "max_ke": float(np.nanmax(kinetic_energy)) if kinetic_energy.size else float("nan"),
        "max_volume": float(np.nanmax(volume)) if volume.size else float("nan"),
        "max_deformation": float(np.nanmax(np.abs(deformation))) if deformation.size else float("nan"),
    }
    row.update(pressure)
    return row


def _pack(rows: list[dict[str, float | str]]) -> dict[str, np.ndarray]:
    keys = rows[0].keys()
    packed: dict[str, np.ndarray] = {}
    for key in keys:
        values = [row[key] for row in rows]
        if isinstance(values[0], str):
            packed[key] = np.asarray(values, dtype=object)
        else:
            packed[key] = np.asarray(values, dtype=float)
    return packed


def _load_summary(path: pathlib.Path) -> list[dict[str, float | str]]:
    loaded = load_results(path)
    labels = list(loaded["label"])
    summaries = []
    for index, label in enumerate(labels):
        row = {}
        for key, value in loaded.items():
            row[key] = value[index] if isinstance(value, np.ndarray) else value
        row["label"] = label
        summaries.append(row)
    return summaries


def _print_summary(rows: list[dict[str, float | str]]) -> None:
    print(
        "label,status,final_t,max_ke,max_volume,jump,jump_error,"
        "liquid_rms,gas_rms,max_deformation"
    )
    for row in rows:
        print(
            f"{row['label']},{row['status']},{float(row['final_t']):.8g},"
            f"{float(row['max_ke']):.6e},{float(row['max_volume']):.6e},"
            f"{float(row['jump']):.6e},{float(row['jump_abs_error']):.6e},"
            f"{float(row['liquid_residual_rms']):.6e},"
            f"{float(row['gas_residual_rms']):.6e},"
            f"{float(row['max_deformation']):.6e}"
        )


def main() -> None:
    parser = experiment_argparser(__doc__)
    args = parser.parse_args()

    outdir = experiment_dir(__file__, "ch14_pressure_history_gradient_n64")
    npz_path = outdir / "data.npz"
    if args.plot_only:
        _print_summary(_load_summary(npz_path))
        return

    with open(BASE_CONFIG) as file:
        raw_base = yaml.safe_load(file)

    rows: list[dict[str, float | str]] = []
    for case in _cases():
        print(f"\n=== {case.label}: {case.hypothesis} ===")
        cfg = _build_config(raw_base, case.label)
        start = time.perf_counter()
        with _pressure_history_patch(case.disable_previous_pressure_gradient):
            results = ns_pipeline.run_simulation(cfg)
        elapsed = time.perf_counter() - start
        rows.append(_summarize(case, results, elapsed))
        save_results(npz_path, _pack(rows))

    _print_summary(rows)


if __name__ == "__main__":
    main()
