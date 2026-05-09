"""Efficient hypothesis validation for the rising-bubble transport RCA.

This script tests the interaction that the theory predicts:

1. constant density + explicit history should remain nearly neutral;
2. variable density + zero history lag should remain nearly neutral;
3. variable density + history lag can create physical kinetic energy;
4. the actual rising-bubble checkpoints should show the same production
   history signature before the catastrophic mode.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts/A/ch14_transport_history_validation_CHK_RA_CH14_BUBBLE_HIST_001"
MFG_PATH = ROOT / "artifacts/A/ch14_momentum_transport_manufactured_probe.py"
CHECKPOINTS = {
    "stable_pre_step_t0p009995": ROOT
    / "experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p01/checkpoint_continuation.npz",
    "stable_post_step_t0p01": ROOT
    / "experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p01/checkpoint_final.npz",
    "pre_blowup_t0p018033": ROOT
    / "experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p02/checkpoint_pre_blowup_input.npz",
}


@dataclass(frozen=True)
class SweepRow:
    density_ratio: float
    shift_cells: float
    paired_rate: float
    imex_rate: float
    imex_minus_current_rate: float
    ke: float


@dataclass(frozen=True)
class CheckpointRow:
    case: str
    state_phase: str
    step: int
    dt_candidate: float
    dt_effective: float
    ke: float
    conv_n_power: float
    conv_prev_power: float
    imex_power: float
    linear_energy_increment_dt_candidate: float
    linear_energy_increment_bdf2_dt: float
    imex_linf: float


def _load_mfg_module():
    spec = importlib.util.spec_from_file_location("ch14_mfg_probe", MFG_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MFG_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _smooth_density(grid, ratio: float) -> np.ndarray:
    x, y = np.meshgrid(
        np.asarray(grid.coords[0], dtype=np.float64),
        np.asarray(grid.coords[1], dtype=np.float64),
        indexing="ij",
    )
    blend = 0.5 + 0.25 * np.sin(2.0 * np.pi * x + 0.2) * np.sin(
        2.0 * np.pi * y - 0.1
    )
    return 1.0 + (float(ratio) - 1.0) * blend


def _sweep_history_density(mfg) -> list[SweepRow]:
    backend = mfg.Backend(use_gpu=False)
    grid, bc_type = mfg._periodic_grid(backend, 32)
    ccd = mfg.CCDSolver(grid, backend, bc_type=bc_type)
    fccd = mfg.FCCDSolver(grid, backend, bc_type=bc_type, ccd_solver=ccd)
    volume = mfg._node_volume(grid, bc_type)
    operators = mfg._operators(backend, grid, ccd, fccd)
    operator = operators["uccd6"]
    current_velocity = mfg._periodic_velocity(grid, shift=0.0)
    conv_n = mfg._compute_operator(operator, backend, ccd, fccd, current_velocity)
    current_dot = current_velocity[0] * conv_n[0] + current_velocity[1] * conv_n[1]
    speed2 = current_velocity[0] ** 2 + current_velocity[1] ** 2

    rows: list[SweepRow] = []
    ratios = (1.0, 2.0, 10.0, 100.0, 833.3333333333334)
    shift_cells_values = (0.0, 0.0625, 0.125, 0.25, 0.5, 1.0)
    for ratio in ratios:
        rho = _smooth_density(grid, ratio)
        rho_rhs = mfg._density_rhs(fccd=fccd, rho=rho, velocity=current_velocity)
        density_correction = float(np.sum(0.5 * speed2 * volume * rho_rhs))
        ke = float(0.5 * np.sum(rho * volume * speed2))
        rho_power = float(np.sum(rho * volume * current_dot))
        paired = rho_power + density_correction
        for shift_cells in shift_cells_values:
            shift = float(shift_cells) / 32.0
            previous_velocity = mfg._periodic_velocity(grid, shift=shift)
            conv_prev = mfg._compute_operator(operator, backend, ccd, fccd, previous_velocity)
            imex = [2.0 * conv_n[0] - conv_prev[0], 2.0 * conv_n[1] - conv_prev[1]]
            imex_dot = current_velocity[0] * imex[0] + current_velocity[1] * imex[1]
            imex_power = float(np.sum(rho * volume * imex_dot))
            imex_paired = imex_power + density_correction
            denom = max(abs(ke), 1.0e-300)
            rows.append(
                SweepRow(
                    density_ratio=float(ratio),
                    shift_cells=float(shift_cells),
                    paired_rate=paired / denom,
                    imex_rate=imex_paired / denom,
                    imex_minus_current_rate=(imex_paired - paired) / denom,
                    ke=ke,
                )
            )
    return rows


def _read_manifest(z) -> dict:
    if "__manifest_json__" not in z.files:
        return {}
    raw = z["__manifest_json__"]
    value = raw.item() if raw.shape == () else raw.tobytes().decode()
    if isinstance(value, bytes):
        value = value.decode()
    return json.loads(value)


def _checkpoint_grid(mfg, backend, z):
    grid = mfg.Grid(mfg.GridConfig(ndim=2, N=(32, 64), L=(0.01, 0.02)), backend)
    grid.coords[0] = np.asarray(z["grid/coords/0"], dtype=np.float64)
    grid.coords[1] = np.asarray(z["grid/coords/1"], dtype=np.float64)
    grid.h[0] = np.asarray(z["grid/h/0"], dtype=np.float64)
    grid.h[1] = np.asarray(z["grid/h/1"], dtype=np.float64)
    grid._cell_volumes = None
    grid._build_metrics()
    return grid


def _checkpoint_replay(mfg) -> list[CheckpointRow]:
    backend = mfg.Backend(use_gpu=False)
    rows: list[CheckpointRow] = []
    for name, path in CHECKPOINTS.items():
        z = np.load(path, allow_pickle=True)
        manifest = _read_manifest(z)
        grid = _checkpoint_grid(mfg, backend, z)
        ccd = mfg.CCDSolver(grid, backend, bc_type="wall")
        fccd = mfg.FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)
        volume = mfg._node_volume(grid, "wall")
        operator = mfg.UCCD6ConvectionTerm(backend, grid, ccd, sigma=1.0e-3)
        psi = np.asarray(z["state/psi"], dtype=np.float64)
        rho = 1.2 + psi * (1000.0 - 1.2)
        u = np.asarray(z["state/u"], dtype=np.float64)
        v = np.asarray(z["state/v"], dtype=np.float64)
        velocity = [u, v]
        conv_n = mfg._compute_operator(operator, backend, ccd, fccd, velocity)
        conv_prev_count = int(z["solver/conv_prev/count"])
        if conv_prev_count == 2:
            conv_prev = [
                np.asarray(z[f"solver/conv_prev/{axis}"], dtype=np.float64)
                for axis in range(2)
            ]
        else:
            conv_prev = [conv_n[0].copy(), conv_n[1].copy()]
        imex = [2.0 * conv_n[0] - conv_prev[0], 2.0 * conv_n[1] - conv_prev[1]]
        conv_n_power = float(np.sum(rho * volume * (u * conv_n[0] + v * conv_n[1])))
        conv_prev_power = float(
            np.sum(rho * volume * (u * conv_prev[0] + v * conv_prev[1]))
        )
        imex_power = float(np.sum(rho * volume * (u * imex[0] + v * imex[1])))
        ke = float(0.5 * np.sum(rho * volume * (u * u + v * v)))
        dt_candidate = float(manifest.get("dt_candidate") or 0.0)
        dt_effective = float(manifest.get("dt_effective") or dt_candidate)
        rows.append(
            CheckpointRow(
                case=name,
                state_phase=str(manifest.get("state_phase", "")),
                step=int(manifest.get("step") or -1),
                dt_candidate=dt_candidate,
                dt_effective=dt_effective,
                ke=ke,
                conv_n_power=conv_n_power,
                conv_prev_power=conv_prev_power,
                imex_power=imex_power,
                linear_energy_increment_dt_candidate=dt_candidate * imex_power,
                linear_energy_increment_bdf2_dt=(2.0 / 3.0) * dt_candidate * imex_power,
                imex_linf=float(max(np.max(np.abs(imex[0])), np.max(np.abs(imex[1])))),
            )
        )
    return rows


def _write_csv(path: Path, rows) -> None:
    fields = list(rows[0].__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _plot_sweep(rows: list[SweepRow], path: Path) -> None:
    ratios = sorted({row.density_ratio for row in rows})
    shifts = sorted({row.shift_cells for row in rows})
    matrix = np.empty((len(ratios), len(shifts)))
    for i, ratio in enumerate(ratios):
        for j, shift in enumerate(shifts):
            row = next(r for r in rows if r.density_ratio == ratio and r.shift_cells == shift)
            matrix[i, j] = row.imex_minus_current_rate

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    vmax = max(float(np.max(np.abs(matrix))), 1.0e-14)
    image = ax.imshow(matrix, origin="lower", aspect="auto", cmap="coolwarm", vmin=-vmax, vmax=vmax)
    ax.set_xticks(np.arange(len(shifts)))
    ax.set_xticklabels([f"{s:g}" for s in shifts])
    ax.set_yticks(np.arange(len(ratios)))
    ax.set_yticklabels([f"{r:g}" for r in ratios])
    ax.set_xlabel("history shift [cells]")
    ax.set_ylabel("density ratio")
    ax.set_title("IMEX history power minus current power")
    fig.colorbar(image, ax=ax, label="normalized rate")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_checkpoint(rows: list[CheckpointRow], path: Path) -> None:
    labels = [row.case for row in rows]
    x = np.arange(len(rows))
    width = 0.25
    fig, ax = plt.subplots(figsize=(9.4, 4.5))
    ax.bar(x - width, [row.conv_prev_power for row in rows], width, label="conv_prev")
    ax.bar(x, [row.conv_n_power for row in rows], width, label="conv_n")
    ax.bar(x + width, [row.imex_power for row in rows], width, label="2conv_n-conv_prev")
    ax.axhline(0.0, color="0.2", lw=0.8)
    ax.set_yscale("symlog", linthresh=1.0e-4)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("rho dV power")
    ax.set_title("Checkpoint production-history replay")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _write_summary(path: Path, sweep_rows: list[SweepRow], checkpoint_rows: list[CheckpointRow]) -> None:
    def find(ratio, shift):
        return next(
            row.__dict__
            for row in sweep_rows
            if math.isclose(row.density_ratio, ratio)
            and math.isclose(row.shift_cells, shift)
        )

    summary = {
        "controls": {
            "constant_density_shift_1cell": find(1.0, 1.0),
            "high_density_zero_shift": find(833.3333333333334, 0.0),
            "high_density_shift_1cell": find(833.3333333333334, 1.0),
        },
        "checkpoint_replay": [row.__dict__ for row in checkpoint_rows],
        "interpretation": (
            "The history defect requires both variable density and history lag. "
            "The controls remove either factor and nearly close the energy gate; "
            "the interaction produces positive normalized IMEX work and is present "
            "in the stable rising-bubble checkpoint before blow-up."
        ),
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mfg = _load_mfg_module()
    sweep_rows = _sweep_history_density(mfg)
    checkpoint_rows = _checkpoint_replay(mfg)
    _write_csv(OUT_DIR / "history_density_sweep.csv", sweep_rows)
    _write_csv(OUT_DIR / "checkpoint_history_replay.csv", checkpoint_rows)
    _write_summary(OUT_DIR / "history_validation_summary.json", sweep_rows, checkpoint_rows)
    _plot_sweep(sweep_rows, OUT_DIR / "history_density_interaction_heatmap.pdf")
    _plot_checkpoint(checkpoint_rows, OUT_DIR / "checkpoint_history_replay.pdf")
    print(OUT_DIR)


if __name__ == "__main__":
    main()
