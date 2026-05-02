#!/usr/bin/env python3
"""Theory-first controls for the N=64 oscillating-droplet blowup."""

from __future__ import annotations

import copy
import math
import pathlib
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.simulation.ns_pipeline import run_simulation  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    experiment_argparser,
    experiment_dir,
    load_results,
    save_results,
)


BASE_CONFIG = ROOT / "experiment/ch14/config/ch14_oscillating_droplet_n64.yaml"
TARGET_FINAL = 0.02


@dataclass(frozen=True)
class ProbeCase:
    label: str
    hypothesis: str
    mutate: Callable[[dict], None]


def _set_time(raw: dict, final: float = TARGET_FINAL) -> None:
    raw["run"]["time"]["final"] = final
    raw["run"]["time"]["print_every"] = 100
    raw["run"].setdefault("debug", {})["step_diagnostics"] = True


def _set_output(raw: dict, label: str) -> None:
    raw["output"]["dir"] = f"results/ch14_osc_n64_hypotheses/{label}"
    raw["output"]["snapshots"]["interval"] = 0.01


def _set_axis_alpha(raw: dict, alpha: float) -> None:
    axes = raw["grid"]["distribution"]["axes"]
    for axis in ("x", "y"):
        axes[axis]["monitors"]["interface"]["alpha"] = alpha


def _set_uniform_grid(raw: dict) -> None:
    raw["grid"]["distribution"] = {"type": "uniform", "schedule": 0}
    raw["interface"]["thickness"]["mode"] = "global"


def _set_circle(raw: dict) -> None:
    radius = math.sqrt(0.055 * 0.045)
    raw["experiment"]["type"] = "circle"
    raw["diagnostics"] = ["volume_conservation", "kinetic_energy"]
    raw["initial_condition"]["objects"] = [
        {
            "type": "circle",
            "center": [0.5, 0.5],
            "radius": radius,
            "interior_phase": "liquid",
        }
    ]


def _set_semi_axes(raw: dict, axes: tuple[float, float]) -> None:
    raw["initial_condition"]["objects"][0]["semi_axes"] = [axes[0], axes[1]]


def _set_zero_viscosity_explicit(raw: dict) -> None:
    raw["physics"]["phases"]["liquid"]["mu"] = 0.0
    raw["physics"]["phases"]["gas"]["mu"] = 0.0
    raw["numerics"]["momentum"]["terms"]["viscosity"]["time_integrator"] = "forward_euler"


def _cases() -> list[ProbeCase]:
    return [
        ProbeCase(
            "base_alpha4",
            "Reference: alpha-4 every-step fitted grid, period-one sigma.",
            lambda raw: None,
        ),
        ProbeCase(
            "cfl_0p05",
            "Capillary CFL violation would move or remove the failure when dt is quartered.",
            lambda raw: raw["run"]["time"].update({"cfl": 0.05}),
        ),
        ProbeCase(
            "sigma_0",
            "If capillary forcing is the energy source, removing sigma removes the blowup.",
            lambda raw: raw["physics"].update({"surface_tension": 0.0}),
        ),
        ProbeCase(
            "sigma_water",
            "Capillary stiffness scales with sigma; water-air sigma should greatly reduce forcing.",
            lambda raw: raw["physics"].update({"surface_tension": 0.072}),
        ),
        ProbeCase(
            "rho_equal",
            "Density-jump PPE coupling is primary if equal density stabilizes the run.",
            lambda raw: (
                raw["physics"]["phases"]["gas"].update({"rho": 1000.0, "mu": 1.0e-3})
            ),
        ),
        ProbeCase(
            "mu0_no_visc_dc",
            "Viscous DC is primary only if removing viscosity/DC removes the blowup.",
            _set_zero_viscosity_explicit,
        ),
        ProbeCase(
            "static_grid",
            "Every-step ALE remap is primary if schedule=0 stabilizes the same fitted grid.",
            lambda raw: raw["grid"]["distribution"].update({"schedule": 0}),
        ),
        ProbeCase(
            "alpha2_dynamic",
            "Metric concentration is primary if weaker alpha=2 fitting stabilizes the run.",
            lambda raw: _set_axis_alpha(raw, 2.0),
        ),
        ProbeCase(
            "uniform_grid",
            "Nonuniform metric/geometry closure is primary if a uniform grid stabilizes it.",
            _set_uniform_grid,
        ),
        ProbeCase(
            "circle_static",
            "A static circle tests balanced-force pressure jump without oscillatory shape energy.",
            _set_circle,
        ),
        ProbeCase(
            "small_amp",
            "Ellipse amplitude/curvature noise is primary if a smaller n=2 perturbation stabilizes.",
            lambda raw: _set_semi_axes(raw, (0.0525, 0.0475)),
        ),
        ProbeCase(
            "drop_1p5x",
            "Under-resolution is primary if a 1.5x droplet delays or stabilizes the route.",
            lambda raw: _set_semi_axes(raw, (0.0825, 0.0675)),
        ),
        ProbeCase(
            "drop_2x",
            "Under-resolution is primary if doubling the droplet size stabilizes the route.",
            lambda raw: _set_semi_axes(raw, (0.11, 0.09)),
        ),
    ]


def _build_config(base: dict, case: ProbeCase) -> ExperimentConfig:
    raw = copy.deepcopy(base)
    _set_time(raw)
    _set_output(raw, case.label)
    case.mutate(raw)
    return ExperimentConfig.from_dict(raw)


def _array(results: dict, key: str) -> np.ndarray:
    value = results.get(key)
    if value is None:
        return np.asarray([], dtype=float)
    return np.asarray(value, dtype=float)


def _debug(results: dict, key: str) -> np.ndarray:
    debug = results.get("debug_diagnostics") or {}
    value = debug.get(key)
    if value is None:
        return np.asarray([], dtype=float)
    return np.asarray(value, dtype=float)


def _last(arr: np.ndarray) -> float:
    return float(arr[-1]) if arr.size else float("nan")


def _max(arr: np.ndarray) -> float:
    return float(np.nanmax(arr)) if arr.size else float("nan")


def _min(arr: np.ndarray) -> float:
    return float(np.nanmin(arr)) if arr.size else float("nan")


def _summarize(label: str, hypothesis: str, results: dict, elapsed: float) -> dict[str, float | str]:
    times = _array(results, "times")
    kinetic = _array(results, "kinetic_energy")
    volume = _array(results, "volume_conservation")
    signed_def = _array(results, "signed_deformation")
    final_t = _last(times)
    max_ke = _max(kinetic)
    blowup = bool(max_ke > 1.0e6 and final_t < TARGET_FINAL - 1.0e-10)
    return {
        "label": label,
        "hypothesis": hypothesis,
        "status": "BLOWUP" if blowup else "COMPLETED",
        "elapsed_s": elapsed,
        "steps": float(times.size),
        "final_t": final_t,
        "max_ke": max_ke,
        "final_ke": _last(kinetic),
        "max_volume_drift": _max(volume),
        "final_volume_drift": _last(volume),
        "signed_deformation_initial": float(signed_def[0]) if signed_def.size else float("nan"),
        "signed_deformation_final": _last(signed_def),
        "max_kappa": _max(_debug(results, "kappa_max")),
        "max_ppe_rhs": _max(_debug(results, "ppe_rhs_max")),
        "max_bf_residual": _max(_debug(results, "bf_residual_max")),
        "max_div_u": _max(_debug(results, "div_u_max")),
        "min_dt_limit": _min(_debug(results, "dt_limit")),
        "min_dt_capillary": _min(_debug(results, "dt_capillary")),
        "min_dt_advective": _min(_debug(results, "dt_advective")),
        "h_min": _last(_debug(results, "h_min")),
    }


def _pack(summaries: list[dict[str, float | str]]) -> dict[str, np.ndarray]:
    keys = list(summaries[0])
    packed: dict[str, np.ndarray] = {}
    for key in keys:
        values = [summary[key] for summary in summaries]
        if isinstance(values[0], str):
            packed[key] = np.asarray(values, dtype=object)
        else:
            packed[key] = np.asarray(values, dtype=float)
    return packed


def _print_summary(summaries: list[dict[str, float | str]]) -> None:
    header = (
        "label,status,steps,final_t,max_ke,max_vol,max_bf,max_div,"
        "min_dt,min_dt_cap,h_min"
    )
    print(header)
    for row in summaries:
        print(
            f"{row['label']},{row['status']},{row['steps']:.0f},"
            f"{row['final_t']:.6g},{row['max_ke']:.6e},"
            f"{row['max_volume_drift']:.6e},{row['max_bf_residual']:.6e},"
            f"{row['max_div_u']:.6e},{row['min_dt_limit']:.6e},"
            f"{row['min_dt_capillary']:.6e},{row['h_min']:.6e}"
        )


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


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument(
        "--case",
        action="append",
        default=None,
        help="Run only the named case. May be repeated.",
    )
    args = parser.parse_args()

    outdir = experiment_dir(__file__, "ch14_oscillating_droplet_n64_hypotheses")
    npz_path = outdir / "data.npz"
    if args.plot_only:
        _print_summary(_load_summary(npz_path))
        return

    with open(BASE_CONFIG) as fh:
        base = yaml.safe_load(fh)

    selected = set(args.case or [])
    cases = [case for case in _cases() if not selected or case.label in selected]
    if not cases:
        raise ValueError(f"No cases selected from {sorted(case.label for case in _cases())}")

    summaries: list[dict[str, float | str]] = []
    for case in cases:
        print(f"\n=== {case.label}: {case.hypothesis} ===")
        cfg = _build_config(base, case)
        start = time.perf_counter()
        results = run_simulation(cfg)
        elapsed = time.perf_counter() - start
        summaries.append(_summarize(case.label, case.hypothesis, results, elapsed))

    _print_summary(summaries)
    save_results(npz_path, _pack(summaries))


if __name__ == "__main__":
    main()
