"""Offline candidate gates for two-phase momentum transport histories.

The script compares small, theory-motivated transport-history candidates on the
same manufactured controls used by the rising-bubble RCA.  It is intentionally
offline: no production solver behavior is changed.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
MFG_PATH = ROOT / "artifacts/A/ch14_momentum_transport_manufactured_probe.py"
OUT_DIR = ROOT / "artifacts/A/ch14_transport_candidate_gate_CHK_RA_CH14_BUBBLE_CAND_001"


@dataclass(frozen=True)
class CandidateRow:
    candidate: str
    density_ratio: float
    shift_cells: float
    current_rate: float
    history_rate: float
    history_minus_current_rate: float
    ke: float
    linf: float


def _load_mfg_module():
    spec = importlib.util.spec_from_file_location("ch14_mfg_probe_for_candidates", MFG_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MFG_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _smooth_density(grid, ratio: float, *, shift: float = 0.0) -> np.ndarray:
    x, y = np.meshgrid(
        np.asarray(grid.coords[0], dtype=np.float64),
        np.asarray(grid.coords[1], dtype=np.float64),
        indexing="ij",
    )
    xs = x + shift
    blend = 0.5 + 0.25 * np.sin(2.0 * np.pi * xs + 0.2) * np.sin(
        2.0 * np.pi * y - 0.1
    )
    return 1.0 + (float(ratio) - 1.0) * blend


def _mass_momentum_rhs(mfg, fccd, rho: np.ndarray, velocity: list[np.ndarray]):
    xp = fccd.xp
    rho_dev = xp.asarray(rho)
    vel_dev = [xp.asarray(component) for component in velocity]
    mass_rhs = xp.zeros_like(rho_dev)
    momentum_rhs = [xp.zeros_like(rho_dev) for _ in range(fccd.grid.ndim)]
    for axis in range(fccd.grid.ndim):
        mass_flux = fccd.face_value(rho_dev, axis) * fccd.face_value(vel_dev[axis], axis)
        mass_rhs = mass_rhs - fccd.face_divergence(mass_flux, axis)
        for component in range(fccd.grid.ndim):
            mom_flux = mass_flux * fccd.face_value(vel_dev[component], axis)
            momentum_rhs[component] = momentum_rhs[component] - fccd.face_divergence(
                mom_flux,
                axis,
            )
    return np.asarray(mass_rhs), [np.asarray(component) for component in momentum_rhs]


def _velocity_from_momentum_rhs(
    rho: np.ndarray,
    velocity: list[np.ndarray],
    mass_rhs: np.ndarray,
    momentum_rhs: list[np.ndarray],
) -> list[np.ndarray]:
    return [
        (momentum_rhs[component] - velocity[component] * mass_rhs) / rho
        for component in range(len(velocity))
    ]


def _velocity_power_rate(
    *,
    rho: np.ndarray,
    volume: np.ndarray,
    velocity: list[np.ndarray],
    acceleration: list[np.ndarray],
    mass_rhs: np.ndarray,
) -> tuple[float, float]:
    speed2 = velocity[0] ** 2 + velocity[1] ** 2
    power = float(
        np.sum(
            rho
            * volume
            * (velocity[0] * acceleration[0] + velocity[1] * acceleration[1])
        )
        + np.sum(0.5 * speed2 * volume * mass_rhs)
    )
    ke = float(0.5 * np.sum(rho * volume * speed2))
    return power, power / max(abs(ke), 1.0e-300)


def _momentum_power_rate(
    *,
    volume: np.ndarray,
    velocity: list[np.ndarray],
    mass_rhs: np.ndarray,
    momentum_rhs: list[np.ndarray],
    ke: float,
) -> tuple[float, float]:
    speed2 = velocity[0] ** 2 + velocity[1] ** 2
    power = float(
        np.sum(volume * (velocity[0] * momentum_rhs[0] + velocity[1] * momentum_rhs[1]))
        - np.sum(0.5 * speed2 * volume * mass_rhs)
    )
    return power, power / max(abs(ke), 1.0e-300)


def _uccd6_acceleration(mfg, backend, ccd, fccd, velocity):
    operator = mfg.UCCD6ConvectionTerm(backend, fccd.grid, ccd, sigma=1.0e-3)
    return mfg._compute_operator(operator, backend, ccd, fccd, velocity)


def _run_gate() -> list[CandidateRow]:
    mfg = _load_mfg_module()
    backend = mfg.Backend(use_gpu=False)
    grid, bc_type = mfg._periodic_grid(backend, 32)
    ccd = mfg.CCDSolver(grid, backend, bc_type=bc_type)
    fccd = mfg.FCCDSolver(grid, backend, bc_type=bc_type, ccd_solver=ccd)
    volume = mfg._node_volume(grid, bc_type)

    rows: list[CandidateRow] = []
    ratios = (1.0, 10.0, 100.0, 833.3333333333334)
    shift_cells_values = (0.0, 0.25, 0.5, 1.0)
    current_velocity = mfg._periodic_velocity(grid, shift=0.0)
    for ratio in ratios:
        rho = _smooth_density(grid, ratio, shift=0.0)
        mass_rhs, momentum_rhs = _mass_momentum_rhs(mfg, fccd, rho, current_velocity)
        conservative_accel = _velocity_from_momentum_rhs(
            rho,
            current_velocity,
            mass_rhs,
            momentum_rhs,
        )
        uccd6_accel = _uccd6_acceleration(mfg, backend, ccd, fccd, current_velocity)
        ke = float(
            0.5
            * np.sum(
                rho
                * volume
                * (current_velocity[0] ** 2 + current_velocity[1] ** 2)
            )
        )
        current_uccd6_power, current_uccd6_rate = _velocity_power_rate(
            rho=rho,
            volume=volume,
            velocity=current_velocity,
            acceleration=uccd6_accel,
            mass_rhs=mass_rhs,
        )
        del current_uccd6_power
        current_cons_power, current_cons_rate = _velocity_power_rate(
            rho=rho,
            volume=volume,
            velocity=current_velocity,
            acceleration=conservative_accel,
            mass_rhs=mass_rhs,
        )
        del current_cons_power
        current_mom_power, current_mom_rate = _momentum_power_rate(
            volume=volume,
            velocity=current_velocity,
            mass_rhs=mass_rhs,
            momentum_rhs=momentum_rhs,
            ke=ke,
        )
        del current_mom_power

        for shift_cells in shift_cells_values:
            shift = float(shift_cells) / 32.0
            prev_velocity = mfg._periodic_velocity(grid, shift=shift)
            prev_rho = _smooth_density(grid, ratio, shift=shift)
            prev_mass_rhs, prev_momentum_rhs = _mass_momentum_rhs(
                mfg,
                fccd,
                prev_rho,
                prev_velocity,
            )
            prev_cons_accel = _velocity_from_momentum_rhs(
                prev_rho,
                prev_velocity,
                prev_mass_rhs,
                prev_momentum_rhs,
            )
            prev_uccd6_accel = _uccd6_acceleration(mfg, backend, ccd, fccd, prev_velocity)

            candidates = {
                "baseline_velocity_uccd6_imex": (
                    current_uccd6_rate,
                    [
                        2.0 * uccd6_accel[0] - prev_uccd6_accel[0],
                        2.0 * uccd6_accel[1] - prev_uccd6_accel[1],
                    ],
                    "velocity",
                ),
                "current_only_uccd6": (
                    current_uccd6_rate,
                    uccd6_accel,
                    "velocity",
                ),
                "conservative_velocity_imex": (
                    current_cons_rate,
                    [
                        2.0 * conservative_accel[0] - prev_cons_accel[0],
                        2.0 * conservative_accel[1] - prev_cons_accel[1],
                    ],
                    "velocity",
                ),
                "current_only_conservative_velocity": (
                    current_cons_rate,
                    conservative_accel,
                    "velocity",
                ),
                "consistent_momentum_history": (
                    current_mom_rate,
                    (
                        [2.0 * mass_rhs - prev_mass_rhs],
                        [
                            2.0 * momentum_rhs[0] - prev_momentum_rhs[0],
                            2.0 * momentum_rhs[1] - prev_momentum_rhs[1],
                        ],
                    ),
                    "momentum",
                ),
                "current_only_momentum": (
                    current_mom_rate,
                    ([mass_rhs], momentum_rhs),
                    "momentum",
                ),
            }
            for name, (current_rate, payload, kind) in candidates.items():
                if kind == "velocity":
                    _, history_rate = _velocity_power_rate(
                        rho=rho,
                        volume=volume,
                        velocity=current_velocity,
                        acceleration=payload,
                        mass_rhs=mass_rhs,
                    )
                    linf = float(max(np.max(np.abs(payload[0])), np.max(np.abs(payload[1]))))
                else:
                    mass_payload, momentum_payload = payload
                    _, history_rate = _momentum_power_rate(
                        volume=volume,
                        velocity=current_velocity,
                        mass_rhs=mass_payload[0],
                        momentum_rhs=momentum_payload,
                        ke=ke,
                    )
                    linf = float(
                        max(
                            np.max(np.abs(momentum_payload[0])),
                            np.max(np.abs(momentum_payload[1])),
                        )
                    )
                rows.append(
                    CandidateRow(
                        candidate=name,
                        density_ratio=float(ratio),
                        shift_cells=float(shift_cells),
                        current_rate=float(current_rate),
                        history_rate=float(history_rate),
                        history_minus_current_rate=float(history_rate - current_rate),
                        ke=ke,
                        linf=linf,
                    )
                )
    return rows


def _write_csv(rows: list[CandidateRow], path: Path) -> None:
    fields = list(CandidateRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _plot(rows: list[CandidateRow], path: Path) -> None:
    selected = [
        row
        for row in rows
        if row.shift_cells == 1.0
        and row.density_ratio in {1.0, 833.3333333333334}
    ]
    candidates = sorted({row.candidate for row in selected})
    labels = []
    values = []
    for candidate in candidates:
        for ratio in (1.0, 833.3333333333334):
            row = next(
                r
                for r in selected
                if r.candidate == candidate and r.density_ratio == ratio
            )
            labels.append(f"{candidate}\nratio={ratio:g}")
            values.append(row.history_minus_current_rate)
    x = np.arange(len(values))
    fig, ax = plt.subplots(figsize=(12.5, 4.8))
    ax.bar(x, values)
    ax.axhline(0.0, color="0.2", lw=0.8)
    ax.set_yscale("symlog", linthresh=1.0e-8)
    ax.set_ylabel("history-current normalized power")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=65, ha="right", fontsize=7)
    ax.set_title("Candidate history energy gate")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _write_summary(rows: list[CandidateRow], path: Path) -> None:
    def pick(candidate: str, ratio: float, shift: float):
        return next(
            row.__dict__
            for row in rows
            if row.candidate == candidate
            and row.density_ratio == ratio
            and row.shift_cells == shift
        )

    summary = {
        "ratio1_shift1": [
            pick(candidate, 1.0, 1.0)
            for candidate in sorted({row.candidate for row in rows})
        ],
        "ratio833_shift1": [
            pick(candidate, 833.3333333333334, 1.0)
            for candidate in sorted({row.candidate for row in rows})
        ],
        "interpretation": (
            "A viable candidate must keep history-current power near zero for "
            "both constant and variable density. Current-only controls close by "
            "construction. Naive conservative velocity and consistent momentum "
            "history are measured here as offline hypotheses, not production "
            "fixes."
        ),
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = _run_gate()
    _write_csv(rows, OUT_DIR / "candidate_gate.csv")
    _write_summary(rows, OUT_DIR / "candidate_gate_summary.json")
    _plot(rows, OUT_DIR / "candidate_history_gate.pdf")
    print(OUT_DIR)


if __name__ == "__main__":
    main()
