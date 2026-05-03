#!/usr/bin/env python3
"""Pressure-oscillation diagnostics for N=64 droplet controls.

Theory contract:
    A static circular droplet at rest satisfies ``u=0`` and ``grad p=0`` in
    each bulk phase, while the interface jump satisfies
    ``[p] = sigma kappa = sigma / R``.  The absolute pressure gauge is arbitrary,
    so the diagnostic removes phase means before measuring residual pressure
    oscillations.

Symbol mapping:
    ``pressure`` ↔ numerical pressure field
    ``phase_fraction`` ↔ liquid volume indicator reconstructed from density
    ``expected_jump`` ↔ Young--Laplace pressure jump ``sigma / R``
    ``curvature_proxy`` ↔ ``div(grad H / |grad H|)`` on the stored interface
"""

from __future__ import annotations

import csv
import math
import pathlib
import sys
from collections.abc import Iterable

import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    field_panel,
    save_figure,
    save_results,
)


RESULT_ROOT = ROOT / "experiment/ch14/results"
OUTPUT_NAME = "ch14_pressure_oscillation_n64_diagnostics"
EXPECTED_RADIUS = 0.25
SURFACE_TENSION = 0.072
EXPECTED_JUMP = SURFACE_TENSION / EXPECTED_RADIUS
ANGULAR_MODES = (2, 4, 8, 16)

CASES = {
    "static_alpha2": "ch14_static_droplet_n64_alpha2_like_oscillating",
    "static_alpha2_staticgrid": "ch14_static_droplet_n64_alpha2_staticgrid_pressure_probe",
    "static_alpha4": "ch14_static_droplet_n64_like_oscillating",
    "oscillating_alpha4": "ch14_oscillating_droplet_n64",
}


def _phase_fraction(density: np.ndarray) -> np.ndarray:
    density_min = float(np.nanmin(density))
    density_max = float(np.nanmax(density))
    return (density - density_min) / max(density_max - density_min, 1.0e-300)


def _bulk_masks(phase_fraction: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    liquid_bulk = phase_fraction > 0.95
    gas_bulk = phase_fraction < 0.05
    interface_band = (phase_fraction > 0.10) & (phase_fraction < 0.90)
    if int(np.count_nonzero(liquid_bulk)) < 8:
        liquid_bulk = phase_fraction > 0.90
    if int(np.count_nonzero(gas_bulk)) < 8:
        gas_bulk = phase_fraction < 0.10
    return liquid_bulk, gas_bulk, interface_band


def _phase_residual_pressure(
    pressure: np.ndarray,
    phase_fraction: np.ndarray,
) -> tuple[np.ndarray, float, float, float]:
    liquid_bulk, gas_bulk, _ = _bulk_masks(phase_fraction)
    liquid_mean = float(np.mean(pressure[liquid_bulk]))
    gas_mean = float(np.mean(pressure[gas_bulk]))
    residual = np.where(phase_fraction >= 0.5, pressure - liquid_mean, pressure - gas_mean)
    jump = liquid_mean - gas_mean
    return residual, liquid_mean, gas_mean, jump


def _high_frequency_fraction(field: np.ndarray) -> float:
    centered_field = field - float(np.mean(field))
    spectrum = np.fft.fft2(centered_field)
    energy = np.abs(spectrum) ** 2
    freq_axis0 = np.fft.fftfreq(centered_field.shape[0])
    freq_axis1 = np.fft.fftfreq(centered_field.shape[1])
    freq0, freq1 = np.meshgrid(freq_axis0, freq_axis1, indexing="ij")
    radial_frequency = np.sqrt(freq0 * freq0 + freq1 * freq1)
    high_shell = radial_frequency > 0.35
    total_energy = float(np.sum(energy))
    if total_energy == 0.0:
        return 0.0
    return float(np.sum(energy[high_shell]) / total_energy)


def _checker_projection(field: np.ndarray) -> float:
    centered_field = field - float(np.mean(field))
    grid_axis0, grid_axis1 = np.indices(centered_field.shape)
    checker = np.where((grid_axis0 + grid_axis1) % 2 == 0, 1.0, -1.0)
    numerator = abs(float(np.mean(centered_field * checker)))
    denominator = math.sqrt(float(np.mean(centered_field * centered_field))) + 1.0e-300
    return numerator / denominator


def _angular_amplitudes(
    field: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    *,
    radius_inner: float,
    radius_outer: float,
    modes: Iterable[int] = ANGULAR_MODES,
) -> dict[str, float]:
    mesh_x, mesh_y = np.meshgrid(x_coords, y_coords, indexing="ij")
    radius = np.sqrt((mesh_x - 0.5) ** 2 + (mesh_y - 0.5) ** 2)
    angle = np.arctan2(mesh_y - 0.5, mesh_x - 0.5)
    annulus = (radius >= radius_inner) & (radius <= radius_outer)
    values = field[annulus]
    angles = angle[annulus]
    if values.size < 8:
        return {f"angular_m{mode}": float("nan") for mode in modes}
    centered_values = values - float(np.mean(values))
    rms_value = math.sqrt(float(np.mean(centered_values * centered_values))) + 1.0e-300
    amplitudes: dict[str, float] = {}
    for mode in modes:
        coefficient = np.mean(centered_values * np.exp(-1j * mode * angles))
        amplitudes[f"angular_m{mode}"] = float(2.0 * abs(coefficient) / rms_value)
    return amplitudes


def _curvature_proxy(
    phase_fraction: np.ndarray,
    x_coords: np.ndarray,
    y_coords: np.ndarray,
) -> np.ndarray:
    grad_x, grad_y = np.gradient(phase_fraction, x_coords, y_coords, edge_order=2)
    grad_norm = np.sqrt(grad_x * grad_x + grad_y * grad_y) + 1.0e-300
    normal_x = grad_x / grad_norm
    normal_y = grad_y / grad_norm
    normal_x_grad = np.gradient(normal_x, x_coords, axis=0, edge_order=2)
    normal_y_grad = np.gradient(normal_y, y_coords, axis=1, edge_order=2)
    return normal_x_grad + normal_y_grad


def _safe_corr(first_values: np.ndarray, second_values: np.ndarray) -> float:
    finite = np.isfinite(first_values) & np.isfinite(second_values)
    if int(np.count_nonzero(finite)) < 8:
        return float("nan")
    first_centered = first_values[finite] - float(np.mean(first_values[finite]))
    second_centered = second_values[finite] - float(np.mean(second_values[finite]))
    denominator = math.sqrt(float(np.mean(first_centered * first_centered)))
    denominator *= math.sqrt(float(np.mean(second_centered * second_centered)))
    if denominator == 0.0:
        return float("nan")
    return float(np.mean(first_centered * second_centered) / denominator)


def analyse_case(label: str, result_name: str) -> tuple[list[dict[str, float | str]], dict[str, np.ndarray]]:
    data_path = RESULT_ROOT / result_name / "data.npz"
    data = np.load(data_path, allow_pickle=True)
    x_coords = np.asarray(data["fields/grid_coords/0"], dtype=float)
    y_coords = np.asarray(data["fields/grid_coords/1"], dtype=float)
    pressure_series = np.asarray(data["fields/p"], dtype=float)
    density_series = np.asarray(data["fields/rho"], dtype=float)
    snapshot_times = np.asarray(data["fields/times"], dtype=float)
    kinetic_energy = np.asarray(data["kinetic_energy"], dtype=float)
    volume_drift = np.asarray(data["volume_conservation"], dtype=float)

    rows: list[dict[str, float | str]] = []
    residual_series = []
    phase_fraction_series = []
    curvature_series = []

    for snapshot_index, snapshot_time in enumerate(snapshot_times):
        pressure = pressure_series[snapshot_index]
        phase_fraction = _phase_fraction(density_series[snapshot_index])
        residual, liquid_mean, gas_mean, jump = _phase_residual_pressure(
            pressure,
            phase_fraction,
        )
        liquid_bulk, gas_bulk, interface_band = _bulk_masks(phase_fraction)
        curvature = _curvature_proxy(phase_fraction, x_coords, y_coords)

        bulk_mask = liquid_bulk | gas_bulk
        liquid_residual = residual[liquid_bulk]
        gas_residual = residual[gas_bulk]
        bulk_rms = math.sqrt(float(np.mean(residual[bulk_mask] * residual[bulk_mask])))
        liquid_rms = math.sqrt(float(np.mean(liquid_residual * liquid_residual)))
        gas_rms = math.sqrt(float(np.mean(gas_residual * gas_residual)))
        interface_rms = math.sqrt(float(np.mean(residual[interface_band] * residual[interface_band])))
        jump_error = min(abs(jump - EXPECTED_JUMP), abs(jump + EXPECTED_JUMP))
        curvature_band = curvature[interface_band]
        pressure_band = pressure[interface_band]
        mode_inside = _angular_amplitudes(
            residual,
            x_coords,
            y_coords,
            radius_inner=0.18,
            radius_outer=0.23,
        )
        mode_outside = _angular_amplitudes(
            residual,
            x_coords,
            y_coords,
            radius_inner=0.27,
            radius_outer=0.32,
        )

        row: dict[str, float | str] = {
            "case": label,
            "snapshot": float(snapshot_index),
            "time": float(snapshot_time),
            "pressure_mean": float(np.mean(pressure)),
            "pressure_std": float(np.std(pressure)),
            "liquid_mean": liquid_mean,
            "gas_mean": gas_mean,
            "jump": jump,
            "jump_abs_error": float(jump_error),
            "bulk_residual_rms": bulk_rms,
            "liquid_residual_rms": liquid_rms,
            "gas_residual_rms": gas_rms,
            "liquid_residual_max_abs": float(np.max(np.abs(liquid_residual))),
            "gas_residual_max_abs": float(np.max(np.abs(gas_residual))),
            "interface_residual_rms": interface_rms,
            "high_frequency_fraction": _high_frequency_fraction(residual),
            "checker_projection": _checker_projection(residual),
            "curvature_mean": float(np.mean(curvature_band)),
            "curvature_std": float(np.std(curvature_band)),
            "pressure_curvature_corr": _safe_corr(pressure_band, curvature_band),
        }
        for key, value in mode_inside.items():
            row[f"inside_{key}"] = value
        for key, value in mode_outside.items():
            row[f"outside_{key}"] = value
        rows.append(row)
        residual_series.append(residual)
        phase_fraction_series.append(phase_fraction)
        curvature_series.append(curvature)

    arrays = {
        "times": snapshot_times,
        "pressure": pressure_series,
        "phase_fraction": np.asarray(phase_fraction_series),
        "residual_pressure": np.asarray(residual_series),
        "curvature_proxy": np.asarray(curvature_series),
        "kinetic_energy": kinetic_energy,
        "volume_drift": volume_drift,
    }
    return rows, arrays


def write_csv(path: pathlib.Path, rows: list[dict[str, float | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved CSV → {path}")


def make_summary_figure(outdir: pathlib.Path, rows: list[dict[str, float | str]]) -> None:
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(8.0, 5.8), sharex=False)
    metrics = [
        ("bulk_residual_rms", "bulk residual RMS"),
        ("interface_residual_rms", "interface residual RMS"),
        ("high_frequency_fraction", "high-frequency energy fraction"),
        ("outside_angular_m4", "outside annulus m=4 amplitude"),
    ]
    for axis, (metric, title) in zip(axes.ravel(), metrics, strict=True):
        for label in CASES:
            case_rows = [row for row in rows if row["case"] == label]
            if not case_rows:
                continue
            times = [float(row["time"]) for row in case_rows]
            values = [float(row[metric]) for row in case_rows]
            axis.plot(times, values, marker="o", markersize=2.5, linewidth=1.0, label=label)
        axis.set_title(title)
        axis.set_xlabel("$t$")
        axis.grid(True, alpha=0.25)
    axes[0, 0].set_ylabel("pressure")
    axes[0, 1].set_ylabel("pressure")
    axes[1, 0].set_ylabel("fraction")
    axes[1, 1].set_ylabel("relative amplitude")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Pressure residual diagnostics after removing phase means", fontsize=11)
    fig.tight_layout()
    save_figure(fig, outdir / "pressure_residual_metrics.pdf")


def make_panel_figure(outdir: pathlib.Path, arrays_by_case: dict[str, dict[str, np.ndarray]]) -> None:
    apply_style()
    case_labels = [label for label in CASES if label in arrays_by_case]
    fig, axes = plt.subplots(len(case_labels), 2, figsize=(8.0, 3.0 * len(case_labels)))
    if len(case_labels) == 1:
        axes = np.asarray([axes])
    for row_index, label in enumerate(case_labels):
        arrays = arrays_by_case[label]
        final_index = arrays["times"].shape[0] - 1
        x_coords = np.load(RESULT_ROOT / CASES[label] / "data.npz", allow_pickle=True)["fields/grid_coords/0"]
        y_coords = np.load(RESULT_ROOT / CASES[label] / "data.npz", allow_pickle=True)["fields/grid_coords/1"]
        mesh_x, mesh_y = np.meshgrid(x_coords, y_coords, indexing="ij")
        residual = arrays["residual_pressure"][final_index]
        curvature = arrays["curvature_proxy"][final_index]
        phase_fraction = arrays["phase_fraction"][final_index]
        residual_vlim = float(np.nanpercentile(np.abs(residual), 99.0))
        curvature_vlim = float(np.nanpercentile(np.abs(curvature), 99.0))
        field_panel(
            axes[row_index, 0],
            mesh_x,
            mesh_y,
            residual,
            vlim=residual_vlim,
            contour_field=phase_fraction,
            contour_levels=(0.5,),
            cb_label="phase-mean residual p",
            title=f"{label}: residual pressure at t={arrays['times'][final_index]:.3f}",
        )
        field_panel(
            axes[row_index, 1],
            mesh_x,
            mesh_y,
            curvature,
            vlim=curvature_vlim,
            contour_field=phase_fraction,
            contour_levels=(0.5,),
            cb_label="curvature proxy",
            title=f"{label}: curvature proxy",
        )
    fig.tight_layout()
    save_figure(fig, outdir / "pressure_residual_final_panels.pdf")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument(
        "--cases",
        nargs="*",
        choices=sorted(CASES),
        default=sorted(CASES),
        help="Case labels to analyse.",
    )
    args = parser.parse_args()

    outdir = experiment_dir(__file__, OUTPUT_NAME)
    rows: list[dict[str, float | str]] = []
    arrays_by_case: dict[str, dict[str, np.ndarray]] = {}
    for label in args.cases:
        data_path = RESULT_ROOT / CASES[label] / "data.npz"
        if not data_path.exists():
            print(f"Skipping {label}: missing {data_path}")
            continue
        case_rows, arrays = analyse_case(label, CASES[label])
        rows.extend(case_rows)
        arrays_by_case[label] = arrays
    if not rows:
        raise FileNotFoundError("No requested pressure-diagnostic result files exist.")

    write_csv(outdir / "summary.csv", rows)
    save_results(outdir / "data.npz", {label: arrays for label, arrays in arrays_by_case.items()})
    make_summary_figure(outdir, rows)
    make_panel_figure(outdir, arrays_by_case)

    for label in args.cases:
        case_rows = [row for row in rows if row["case"] == label]
        final_row = case_rows[-1]
        print(
            label,
            "t=", f"{float(final_row['time']):.6g}",
            "bulk_rms=", f"{float(final_row['bulk_residual_rms']):.6e}",
            "hf=", f"{float(final_row['high_frequency_fraction']):.6e}",
            "m4_out=", f"{float(final_row['outside_angular_m4']):.6e}",
            "jump=", f"{float(final_row['jump']):.6e}",
        )


if __name__ == "__main__":
    main()
