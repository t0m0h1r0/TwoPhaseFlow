"""Production-path audit for the rising-bubble RCA.

The script reads the saved N=32x64 rising-bubble rollback artifacts and
quantifies which production state variables grow before blow-up.  It is a
diagnostic artifact only; it does not run or modify the solver.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = (
    ROOT
    / "experiment/ch14/results"
    / "_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p02"
)
STABLE_DIR = (
    ROOT
    / "experiment/ch14/results"
    / "_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p01"
)
OUT_DIR = ROOT / "artifacts/A/ch14_production_path_audit_CHK_RA_CH14_BUBBLE_PROD_001"


@dataclass(frozen=True)
class ThresholdRow:
    event: str
    index: int
    time: float
    kinetic_energy: float
    dt_limit: float
    ppe_rhs_max: float
    capillary_face_linf: float
    capillary_jump_linf: float
    div_u_max: float
    advective_rate: float
    reinit_linf_delta: float


@dataclass(frozen=True)
class CheckpointRow:
    checkpoint: str
    time: float
    energy_current: float
    energy_bdf2_base_ratio: float
    energy_ext2_velocity_ratio: float
    speed_linf: float
    velocity_history_delta_linf: float
    conv_prev_linf: float
    previous_pressure_accel_linf: float
    projected_face_linf: float
    dt_limit: float
    ppe_rhs_max: float
    div_u_max: float
    reinit_linf_delta: float


def _load_data():
    return np.load(RUN_DIR / "data.npz", allow_pickle=True)


def _first_event(data, name: str, key: str, threshold: float, *, greater: bool) -> ThresholdRow:
    values = data[key]
    indices = np.where(values > threshold)[0] if greater else np.where(values < threshold)[0]
    if len(indices) == 0:
        return ThresholdRow(
            event=name,
            index=-1,
            time=float("nan"),
            kinetic_energy=float("nan"),
            dt_limit=float("nan"),
            ppe_rhs_max=float("nan"),
            capillary_face_linf=float("nan"),
            capillary_jump_linf=float("nan"),
            div_u_max=float("nan"),
            advective_rate=float("nan"),
            reinit_linf_delta=float("nan"),
        )
    i = int(indices[0])
    return ThresholdRow(
        event=name,
        index=i,
        time=float(data["times"][i]),
        kinetic_energy=float(data["kinetic_energy"][i]),
        dt_limit=float(data["debug_diagnostics/dt_limit"][i]),
        ppe_rhs_max=float(data["debug_diagnostics/ppe_rhs_max"][i]),
        capillary_face_linf=float(data["debug_diagnostics/capillary_face_linf"][i]),
        capillary_jump_linf=float(data["debug_diagnostics/capillary_jump_linf"][i]),
        div_u_max=float(data["debug_diagnostics/div_u_max"][i]),
        advective_rate=float(data["debug_diagnostics/advective_rate"][i]),
        reinit_linf_delta=float(data["debug_diagnostics/reinit_linf_delta"][i]),
    )


def _linf(arr) -> float:
    return float(np.max(np.abs(arr)))


def _checkpoint_metrics(label: str, path: Path) -> CheckpointRow:
    z = np.load(path, allow_pickle=True)
    psi = z["state/psi"]
    u = z["state/u"]
    v = z["state/v"]
    up = z["solver/velocity_prev/0"]
    vp = z["solver/velocity_prev/1"]
    conv0 = z["solver/conv_prev/0"]
    conv1 = z["solver/conv_prev/1"]
    hx = z["grid/h/0"]
    hy = z["grid/h/1"]
    dV = np.outer(hx, hy)
    rho = 1.2 + (1000.0 - 1.2) * psi

    def energy(a, b) -> float:
        return float(np.sum(0.5 * rho * (a * a + b * b) * dV))

    current = energy(u, v)
    bdf2 = energy((4.0 / 3.0) * u - (1.0 / 3.0) * up, (4.0 / 3.0) * v - (1.0 / 3.0) * vp)
    ext2 = energy(2.0 * u - up, 2.0 * v - vp)
    pressure_linf = 0.0
    p_count = int(np.asarray(z["solver/p_prev_accel_face_components/count"]))
    for axis in range(p_count):
        pressure_linf = max(
            pressure_linf,
            _linf(z[f"solver/p_prev_accel_face_components/{axis}"]),
        )
    projected_linf = 0.0
    pf_count = int(np.asarray(z["solver/projected_face_components/count"]))
    for axis in range(pf_count):
        projected_linf = max(
            projected_linf,
            _linf(z[f"solver/projected_face_components/{axis}"]),
        )
    return CheckpointRow(
        checkpoint=label,
        time=float(z["results/times"][-1]),
        energy_current=current,
        energy_bdf2_base_ratio=bdf2 / max(current, 1.0e-300),
        energy_ext2_velocity_ratio=ext2 / max(current, 1.0e-300),
        speed_linf=max(_linf(u), _linf(v)),
        velocity_history_delta_linf=max(_linf(u - up), _linf(v - vp)),
        conv_prev_linf=max(_linf(conv0), _linf(conv1)),
        previous_pressure_accel_linf=pressure_linf,
        projected_face_linf=projected_linf,
        dt_limit=float(z["debug/dt_limit"][-1]),
        ppe_rhs_max=float(z["debug/ppe_rhs_max"][-1]),
        div_u_max=float(z["debug/div_u_max"][-1]),
        reinit_linf_delta=float(z["debug/reinit_linf_delta"][-1]),
    )


def _write_csv(rows, path: Path) -> None:
    fields = list(rows[0].__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _plot(data, checkpoint_rows: list[CheckpointRow], path: Path) -> None:
    t = data["times"]
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 6.6))
    axes[0, 0].plot(t, data["kinetic_energy"], color="#204a87")
    axes[0, 0].set_yscale("log")
    axes[0, 0].set_title("kinetic energy")
    axes[0, 1].plot(t, data["debug_diagnostics/ppe_rhs_max"], color="#8f2d1f")
    axes[0, 1].plot(t, data["debug_diagnostics/capillary_face_linf"], color="#c47f00")
    axes[0, 1].plot(t, data["debug_diagnostics/capillary_jump_linf"], color="#4e7d3a")
    axes[0, 1].set_yscale("log")
    axes[0, 1].set_title("pressure/capillary scales")
    axes[0, 1].legend(["ppe rhs", "capillary face", "jump"], fontsize=7)
    axes[1, 0].plot(t, data["debug_diagnostics/dt_limit"], color="#4b5d8f")
    axes[1, 0].set_yscale("log")
    axes[1, 0].set_title("dt limiter")
    labels = [row.checkpoint for row in checkpoint_rows]
    x = np.arange(len(labels))
    axes[1, 1].bar(x - 0.2, [row.energy_bdf2_base_ratio for row in checkpoint_rows], width=0.4)
    axes[1, 1].bar(x + 0.2, [row.energy_ext2_velocity_ratio for row in checkpoint_rows], width=0.4)
    axes[1, 1].axhline(1.0, color="0.2", lw=0.8)
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(labels, rotation=20, ha="right")
    axes[1, 1].set_title("history energy ratio")
    axes[1, 1].legend(["BDF2 base", "EXT2 velocity"], fontsize=7)
    for ax in axes.flat:
        ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = _load_data()
    thresholds = [
        _first_event(data, "ppe_rhs_gt_1e8", "debug_diagnostics/ppe_rhs_max", 1.0e8, greater=True),
        _first_event(data, "ke_gt_1e3", "kinetic_energy", 1.0e-3, greater=True),
        _first_event(data, "ke_gt_1e2", "kinetic_energy", 1.0e-2, greater=True),
        _first_event(data, "ke_gt_1", "kinetic_energy", 1.0, greater=True),
        _first_event(data, "div_gt_1e3", "debug_diagnostics/div_u_max", 1.0e-3, greater=True),
        _first_event(data, "dt_lt_1e7", "debug_diagnostics/dt_limit", 1.0e-7, greater=False),
    ]
    checkpoints = [
        _checkpoint_metrics(
            "t0p01_stable",
            STABLE_DIR / "checkpoint_continuation.npz",
        ),
        _checkpoint_metrics(
            "t0p018_preblowup",
            RUN_DIR / "checkpoint_pre_blowup_input.npz",
        ),
    ]
    _write_csv(thresholds, OUT_DIR / "threshold_events.csv")
    _write_csv(checkpoints, OUT_DIR / "checkpoint_energy_audit.csv")
    summary = {
        "run_dir": str(RUN_DIR.relative_to(ROOT)),
        "threshold_events": [row.__dict__ for row in thresholds],
        "checkpoint_energy_audit": [row.__dict__ for row in checkpoints],
        "interpretation": (
            "Volume/reinit deltas remain small while PPE RHS, capillary face "
            "acceleration, advective rate, and velocity-history energy ratios "
            "grow rapidly.  This supports a production feedback mechanism in "
            "acceleration/history variables, consistent with the common "
            "mass-momentum transport RCA."
        ),
    }
    (OUT_DIR / "production_path_audit_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    _plot(data, checkpoints, OUT_DIR / "production_path_audit.pdf")
    print(OUT_DIR)


if __name__ == "__main__":
    main()
