#!/usr/bin/env python3
"""Diagnose base-vs-physical pressure variables for the N=64 static droplet."""

from __future__ import annotations

import copy
import pathlib
import sys
from contextlib import contextmanager

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import twophase.simulation.ns_pipeline as ns_pipeline  # noqa: E402
from twophase.coupling.interface_stress_closure import (  # noqa: E402
    build_young_laplace_interface_stress_context,
)
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.tools.experiment import experiment_argparser, experiment_dir, save_results  # noqa: E402


BASE_CONFIG = ROOT / "experiment/ch14/config/ch14_static_droplet_n64_alpha2_like_oscillating.yaml"
TARGET_FINAL = 0.01


def _build_config() -> ExperimentConfig:
    with open(BASE_CONFIG) as file:
        raw = yaml.safe_load(file)
    raw = copy.deepcopy(raw)
    raw["run"]["time"]["final"] = TARGET_FINAL
    raw["run"]["time"]["print_every"] = 100000
    raw["output"]["dir"] = "results/ch14_pressure_variable_contract_n64"
    raw["output"]["snapshots"]["interval"] = TARGET_FINAL
    raw["output"]["figures"] = []
    return ExperimentConfig.from_dict(raw)


def _host(backend, value) -> np.ndarray:
    return np.asarray(backend.to_host(value), dtype=float)


def _rms(values: np.ndarray) -> float:
    if values.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(values * values)))


def _phase_jump(field: np.ndarray, rho: np.ndarray) -> float:
    density_min = float(np.nanmin(rho))
    density_max = float(np.nanmax(rho))
    phase = (rho - density_min) / max(density_max - density_min, 1.0e-300)
    liquid = phase > 0.95
    gas = phase < 0.05
    return float(np.mean(field[liquid]) - np.mean(field[gas]))


def _face_rms(backend, faces) -> float:
    chunks = [_host(backend, face).ravel() for face in faces]
    if not chunks:
        return float("nan")
    return _rms(np.concatenate(chunks))


@contextmanager
def _record_pressure_contract(rows: list[dict[str, float]]):
    original_pressure = ns_pipeline.solve_ns_pressure_stage

    def wrapped_pressure_stage(state, **kwargs):
        state, next_p_prev_dev, next_p_prev = original_pressure(state, **kwargs)
        backend = kwargs["backend"]
        div_op = kwargs["div_op"]
        ppe_solver = kwargs["ppe_solver"]
        base_increment = getattr(ppe_solver, "last_base_pressure", None)
        if base_increment is None:
            raise RuntimeError("pressure variable diagnostic requires last_base_pressure")

        pressure_increment = _host(backend, state.pressure_increment)
        base_increment_host = _host(backend, base_increment)
        pressure_total = _host(backend, state.pressure)
        pressure_base = _host(backend, state.pressure_base)
        density = _host(backend, state.rho)
        increment_delta = pressure_increment - base_increment_host
        total_delta = pressure_total - pressure_base

        previous_delta_rms = float("nan")
        if state.previous_pressure is not None and state.previous_base_pressure is not None:
            previous_delta = _host(backend, state.previous_pressure) - _host(
                backend, state.previous_base_pressure
            )
            previous_delta_rms = _rms(previous_delta.ravel())

        context = build_young_laplace_interface_stress_context(
            xp=backend.xp,
            psi=state.psi,
            kappa_lg=state.kappa,
            sigma=state.sigma,
        )
        affine_physical_faces = div_op.pressure_fluxes(
            state.pressure_increment,
            state.rho,
            pressure_gradient="fccd",
            coefficient_scheme="phase_separated",
            interface_coupling_scheme="affine_jump",
            interface_stress_context=context,
        )
        affine_base_faces = div_op.pressure_fluxes(
            base_increment,
            state.rho,
            pressure_gradient="fccd",
            coefficient_scheme="phase_separated",
            interface_coupling_scheme="affine_jump",
            interface_stress_context=context,
        )
        affine_face_diff = [
            physical_face - base_face
            for physical_face, base_face in zip(affine_physical_faces, affine_base_faces)
        ]

        rows.append(
            {
                "step": float(state.step_index),
                "dt": float(state.dt),
                "pressure_increment_minus_base_rms": _rms(increment_delta.ravel()),
                "pressure_increment_minus_base_jump": _phase_jump(increment_delta, density),
                "pressure_total_minus_base_rms": _rms(total_delta.ravel()),
                "pressure_total_minus_base_jump": _phase_jump(total_delta, density),
                "previous_pressure_minus_base_rms": previous_delta_rms,
                "affine_physical_increment_face_rms": _face_rms(
                    backend,
                    affine_physical_faces,
                ),
                "affine_base_increment_face_rms": _face_rms(backend, affine_base_faces),
                "affine_increment_face_difference_rms": _face_rms(
                    backend,
                    affine_face_diff,
                ),
            }
        )
        return state, next_p_prev_dev, next_p_prev

    ns_pipeline.solve_ns_pressure_stage = wrapped_pressure_stage
    try:
        yield
    finally:
        ns_pipeline.solve_ns_pressure_stage = original_pressure


def _pack(rows: list[dict[str, float]]) -> dict[str, np.ndarray]:
    return {key: np.asarray([row[key] for row in rows], dtype=float) for key in rows[0]}


def main() -> None:
    parser = experiment_argparser(__doc__)
    args = parser.parse_args()
    outdir = experiment_dir(__file__, "ch14_pressure_variable_contract_n64")
    npz_path = outdir / "data.npz"
    if args.plot_only:
        data = np.load(npz_path)
        keys = list(data.files)
        for index in range(len(data[keys[0]])):
            print(",".join(f"{key}={data[key][index]:.6e}" for key in keys))
        return

    rows: list[dict[str, float]] = []
    with _record_pressure_contract(rows):
        ns_pipeline.run_simulation(_build_config())
    save_results(npz_path, _pack(rows))
    final = rows[-1]
    print(
        "step={step:.0f}, inc_delta_rms={pressure_increment_minus_base_rms:.6e}, "
        "inc_delta_jump={pressure_increment_minus_base_jump:.6e}, "
        "prev_delta_rms={previous_pressure_minus_base_rms:.6e}, "
        "affine_face_diff_rms={affine_increment_face_difference_rms:.6e}".format(
            **final
        )
    )


if __name__ == "__main__":
    main()
