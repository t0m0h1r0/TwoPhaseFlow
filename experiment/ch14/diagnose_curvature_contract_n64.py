#!/usr/bin/env python3
"""Record the Young--Laplace curvature contract for the N=64 static droplet."""

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
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.tools.experiment import experiment_argparser, experiment_dir, save_results  # noqa: E402


BASE_CONFIG = ROOT / "experiment/ch14/config/ch14_static_droplet_n64_alpha2_like_oscillating.yaml"
STATIC_GRID_CONFIG = (
    ROOT / "experiment/ch14/config/ch14_static_droplet_n64_alpha2_staticgrid_pressure_probe.yaml"
)
TARGET_FINAL = 0.40
EXPECTED_KAPPA = 4.0
SURFACE_TENSION = 0.072
ANGULAR_MODES = (4, 8, 16, 32)


def _build_config(reinit_every: int | None, *, static_grid: bool) -> ExperimentConfig:
    config_path = STATIC_GRID_CONFIG if static_grid else BASE_CONFIG
    with open(config_path) as file:
        raw = yaml.safe_load(file)
    raw = copy.deepcopy(raw)
    raw["run"]["time"]["final"] = TARGET_FINAL
    raw["run"]["time"]["print_every"] = 200
    suffix = "static_grid" if static_grid else "baseline"
    if reinit_every is not None:
        suffix = f"{suffix}_reinit{reinit_every}"
    raw["output"]["dir"] = f"results/ch14_curvature_contract_n64/{suffix}"
    raw["output"]["snapshots"]["interval"] = TARGET_FINAL
    raw["output"]["figures"] = []
    if reinit_every is not None:
        raw["interface"]["reinitialization"]["schedule"]["every_steps"] = int(
            reinit_every
        )
    return ExperimentConfig.from_dict(raw)


def _host(backend, value) -> np.ndarray:
    return np.asarray(backend.to_host(value), dtype=float)


def _cut_face_geometry(
    psi: np.ndarray,
    kappa: np.ndarray,
    coords: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    kappa_chunks = []
    radius_chunks = []
    angle_chunks = []
    ndim = psi.ndim
    for axis in range(ndim):
        n_cells = psi.shape[axis] - 1

        def sl(start: int, stop: int):
            slices = [slice(None)] * ndim
            slices[axis] = slice(start, stop)
            return tuple(slices)

        psi_lo = psi[sl(0, n_cells)]
        psi_hi = psi[sl(1, n_cells + 1)]
        cut_face = (psi_lo < 0.5) != (psi_hi < 0.5)
        if not np.any(cut_face):
            continue
        kappa_lo = kappa[sl(0, n_cells)]
        kappa_hi = kappa[sl(1, n_cells + 1)]
        dpsi = psi_hi - psi_lo
        safe_dpsi = np.where(np.abs(dpsi) > 1.0e-30, dpsi, 1.0)
        theta = np.clip((0.5 - psi_lo) / safe_dpsi, 0.0, 1.0)
        kappa_face = (1.0 - theta) * kappa_lo + theta * kappa_hi
        other_axis = 1 - axis
        axis_shape = [1] * ndim
        axis_shape[axis] = psi.shape[axis]
        axis_coord = coords[axis].reshape(axis_shape)
        face_coord = (1.0 - theta) * np.broadcast_to(
            axis_coord[sl(0, n_cells)],
            psi_lo.shape,
        ) + theta * np.broadcast_to(axis_coord[sl(1, n_cells + 1)], psi_lo.shape)
        other_shape = [1] * ndim
        other_shape[other_axis] = psi.shape[other_axis]
        other_coord = np.broadcast_to(
            coords[other_axis].reshape(other_shape),
            psi_lo.shape,
        )
        if axis == 0:
            point_x = face_coord
            point_y = other_coord
        else:
            point_x = other_coord
            point_y = face_coord
        radius = np.sqrt((point_x - 0.5) ** 2 + (point_y - 0.5) ** 2)
        angle = np.arctan2(point_y - 0.5, point_x - 0.5)
        kappa_chunks.append(kappa_face[cut_face].ravel())
        radius_chunks.append(radius[cut_face].ravel())
        angle_chunks.append(angle[cut_face].ravel())
    if not kappa_chunks:
        empty = np.asarray([], dtype=float)
        return empty, empty, empty
    return (
        np.concatenate(kappa_chunks),
        np.concatenate(radius_chunks),
        np.concatenate(angle_chunks),
    )


def _radius_mode_amplitude(radius: np.ndarray, angle: np.ndarray, mode: int) -> float:
    if radius.size == 0:
        return float("nan")
    centered_radius = radius - float(np.mean(radius))
    coefficient = np.mean(centered_radius * np.exp(-1j * mode * angle))
    return float(2.0 * abs(coefficient))


@contextmanager
def _record_curvature(rows: list[dict[str, float]]):
    original_surface = ns_pipeline.compute_ns_surface_tension_stage

    def wrapped_surface_stage(state, **kwargs):
        state = original_surface(state, **kwargs)
        backend = kwargs["backend"]
        ccd = kwargs["ccd"]
        grid = kwargs["grid"]
        psi = _host(backend, state.psi)
        kappa = _host(backend, state.kappa)
        grad_components = []
        for axis in range(psi.ndim):
            grad_axis, _ = ccd.differentiate(state.psi, axis)
            grad_components.append(_host(backend, grad_axis))
        grad_norm = np.sqrt(sum(component * component for component in grad_components))
        coords = (
            np.asarray(grid.coords[0], dtype=float),
            np.asarray(grid.coords[1], dtype=float),
        )
        band = (psi > 0.01) & (psi < 0.99)
        if int(np.count_nonzero(band)) == 0:
            band = np.ones_like(psi, dtype=bool)
        band_kappa = kappa[band]
        kappa_error = band_kappa - EXPECTED_KAPPA
        face_kappa, face_radius, face_angle = _cut_face_geometry(psi, kappa, coords)
        face_grad_norm, _, _ = _cut_face_geometry(psi, grad_norm, coords)
        face_error = face_kappa - EXPECTED_KAPPA
        row = {
            "step": float(state.step_index),
            "time": float(getattr(state, "t", 0.0) or 0.0),
            "band_count": float(np.count_nonzero(band)),
            "kappa_mean": float(np.mean(band_kappa)),
            "kappa_std": float(np.std(band_kappa)),
            "kappa_min": float(np.min(band_kappa)),
            "kappa_max": float(np.max(band_kappa)),
            "kappa_error_rms": float(np.sqrt(np.mean(kappa_error * kappa_error))),
            "jump_std": float(SURFACE_TENSION * np.std(band_kappa)),
            "jump_error_rms": float(
                SURFACE_TENSION * np.sqrt(np.mean(kappa_error * kappa_error))
            ),
            "cut_face_count": float(face_kappa.size),
            "cut_face_kappa_mean": float(np.mean(face_kappa)),
            "cut_face_kappa_std": float(np.std(face_kappa)),
            "cut_face_kappa_min": float(np.min(face_kappa)),
            "cut_face_kappa_max": float(np.max(face_kappa)),
            "cut_face_kappa_error_rms": float(
                np.sqrt(np.mean(face_error * face_error))
            ),
            "cut_face_jump_std": float(SURFACE_TENSION * np.std(face_kappa)),
            "cut_face_radius_mean": float(np.mean(face_radius)),
            "cut_face_radius_std": float(np.std(face_radius)),
            "cut_face_radius_error_max": float(np.max(np.abs(face_radius - 0.25))),
            "cut_face_grad_norm_mean": float(np.mean(face_grad_norm)),
            "cut_face_grad_norm_std": float(np.std(face_grad_norm)),
            "cut_face_grad_norm_min": float(np.min(face_grad_norm)),
            "cut_face_grad_norm_max": float(np.max(face_grad_norm)),
        }
        for mode in ANGULAR_MODES:
            row[f"radius_m{mode}_amplitude"] = _radius_mode_amplitude(
                face_radius,
                face_angle,
                mode,
            )
        rows.append(
            row
        )
        return state

    ns_pipeline.compute_ns_surface_tension_stage = wrapped_surface_stage
    try:
        yield
    finally:
        ns_pipeline.compute_ns_surface_tension_stage = original_surface


def _pack(rows: list[dict[str, float]]) -> dict[str, np.ndarray]:
    return {key: np.asarray([row[key] for row in rows], dtype=float) for key in rows[0]}


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument(
        "--reinit-every",
        type=int,
        default=None,
        help="Diagnostic override for ridge-eikonal reinitialization schedule.",
    )
    parser.add_argument(
        "--static-grid",
        action="store_true",
        help="Use the alpha-2 static-grid pressure-control config.",
    )
    args = parser.parse_args()
    output_name = "ch14_curvature_contract_n64"
    if args.static_grid:
        output_name = f"{output_name}_static_grid"
    if args.reinit_every is not None:
        output_name = f"{output_name}_reinit{args.reinit_every}"
    outdir = experiment_dir(__file__, output_name)
    npz_path = outdir / "data.npz"
    if args.plot_only:
        data = np.load(npz_path)
        for index in (0, len(data["step"]) - 1):
            print(
                "step={:.0f}, kappa_mean={:.6e}, kappa_std={:.6e}, "
                "kappa_error_rms={:.6e}, jump_std={:.6e}, "
                "cut_face_kappa_mean={:.6e}, cut_face_kappa_std={:.6e}, "
                "r_std={:.6e}, r_m16={:.6e}, grad_min={:.6e}".format(
                    data["step"][index],
                    data["kappa_mean"][index],
                    data["kappa_std"][index],
                    data["kappa_error_rms"][index],
                    data["jump_std"][index],
                    data["cut_face_kappa_mean"][index],
                    data["cut_face_kappa_std"][index],
                    data["cut_face_radius_std"][index],
                    data["radius_m16_amplitude"][index],
                    data["cut_face_grad_norm_min"][index],
                )
            )
        return

    rows: list[dict[str, float]] = []
    with _record_curvature(rows):
        ns_pipeline.run_simulation(
            _build_config(args.reinit_every, static_grid=args.static_grid)
        )
    save_results(npz_path, _pack(rows))
    first = rows[0]
    final = rows[-1]
    print(
        "initial kappa_mean={:.6e}, std={:.6e}, jump_std={:.6e}; "
        "final kappa_mean={:.6e}, std={:.6e}, jump_std={:.6e}; "
        "final cut_face_mean={:.6e}, cut_face_std={:.6e}; "
        "final r_std={:.6e}, r_m16={:.6e}, grad_min={:.6e}".format(
            first["kappa_mean"],
            first["kappa_std"],
            first["jump_std"],
            final["kappa_mean"],
            final["kappa_std"],
            final["jump_std"],
            final["cut_face_kappa_mean"],
            final["cut_face_kappa_std"],
            final["cut_face_radius_std"],
            final["radius_m16_amplitude"],
            final["cut_face_grad_norm_min"],
        )
    )


if __name__ == "__main__":
    main()
