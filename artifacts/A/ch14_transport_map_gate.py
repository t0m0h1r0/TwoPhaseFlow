"""Exact-map gates for the rising-bubble transport RCA.

The test checks the strongest theoretical statement available offline:
when density and momentum are moved by the same volume-preserving map, kinetic
energy is preserved for pure transport.  When density and velocity/momentum use
different maps or explicit velocity histories, the energy gate opens.
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
OUT_DIR = ROOT / "artifacts/A/ch14_transport_map_gate_CHK_RA_CH14_BUBBLE_MAP_001"


@dataclass(frozen=True)
class MapGateRow:
    candidate: str
    density_ratio: float
    shift_cells: float
    n: int
    energy0: float
    energy1: float
    relative_delta: float
    mass_delta: float
    notes: str


def _mesh(n: int):
    x = np.linspace(0.0, 1.0, n, endpoint=False)
    y = np.linspace(0.0, 1.0, n, endpoint=False)
    return np.meshgrid(x, y, indexing="ij")


def _velocity(x, y, *, shift: float = 0.0):
    xs = (x - shift) % 1.0
    # Divergence-free periodic field from a multi-mode stream function.
    u = np.sin(2.0 * np.pi * xs) * np.cos(2.0 * np.pi * y)
    v = -np.cos(2.0 * np.pi * xs) * np.sin(2.0 * np.pi * y)
    u += 0.35 * np.sin(4.0 * np.pi * xs + 0.25) * np.cos(2.0 * np.pi * y - 0.15)
    v += -0.70 * np.cos(4.0 * np.pi * xs + 0.25) * np.sin(2.0 * np.pi * y - 0.15)
    u += 0.44 * np.cos(2.0 * np.pi * xs - 0.40) * np.cos(4.0 * np.pi * y + 0.30)
    v += 0.22 * np.sin(2.0 * np.pi * xs - 0.40) * np.sin(4.0 * np.pi * y + 0.30)
    return [u, v]


def _density(x, y, ratio: float, *, shift: float = 0.0):
    xs = (x - shift) % 1.0
    blend = (
        0.5
        + 0.12 * np.sin(2.0 * np.pi * xs + 0.2) * np.sin(2.0 * np.pi * y - 0.1)
        + 0.08 * np.cos(4.0 * np.pi * xs - 0.3)
        + 0.06 * np.cos(4.0 * np.pi * y + 0.4)
        + 0.04 * np.sin(2.0 * np.pi * (xs + y) + 0.7)
    )
    return 1.0 + (float(ratio) - 1.0) * blend


def _energy(rho, velocity):
    return float(0.5 * np.mean(rho * (velocity[0] ** 2 + velocity[1] ** 2)))


def _mass(rho):
    return float(np.mean(rho))


def _rows_for(n: int, ratio: float, shift_cells: float) -> list[MapGateRow]:
    x, y = _mesh(n)
    shift = float(shift_cells) / float(n)
    rho0 = _density(x, y, ratio, shift=0.0)
    u0 = _velocity(x, y, shift=0.0)
    e0 = _energy(rho0, u0)
    m0 = _mass(rho0)

    rho_map = _density(x, y, ratio, shift=shift)
    u_map = _velocity(x, y, shift=shift)
    rho_prev = _density(x, y, ratio, shift=-shift)
    u_prev = _velocity(x, y, shift=-shift)

    candidates = {}
    candidates["common_exact_map"] = (
        rho_map,
        u_map,
        "rho and velocity are both pullbacks by the same map",
    )
    candidates["density_map_velocity_current"] = (
        rho_map,
        u0,
        "density moved, velocity left at current grid",
    )
    candidates["density_map_velocity_imex"] = (
        rho_map,
        [2.0 * u0[0] - u_prev[0], 2.0 * u0[1] - u_prev[1]],
        "density moved, velocity updated by explicit history",
    )
    candidates["density_current_velocity_map"] = (
        rho0,
        u_map,
        "velocity moved, density left at current grid",
    )
    candidates["density_map_momentum_lagged"] = (
        rho_map,
        [
            (rho0 * u0[0]) / rho_map,
            (rho0 * u0[1]) / rho_map,
        ],
        "momentum kept on old map and divided by moved density",
    )
    candidates["independent_opposite_maps"] = (
        rho_map,
        _velocity(x, y, shift=-shift),
        "density and velocity use opposite maps",
    )

    rows = []
    for name, (rho1, u1, notes) in candidates.items():
        e1 = _energy(rho1, u1)
        rows.append(
            MapGateRow(
                candidate=name,
                density_ratio=float(ratio),
                shift_cells=float(shift_cells),
                n=int(n),
                energy0=e0,
                energy1=e1,
                relative_delta=(e1 - e0) / max(abs(e0), 1.0e-300),
                mass_delta=_mass(rho1) - m0,
                notes=notes,
            )
        )
    return rows


def _run() -> list[MapGateRow]:
    rows: list[MapGateRow] = []
    for n in (32, 64, 128):
        for ratio in (1.0, 10.0, 100.0, 833.3333333333334):
            for shift_cells in (0.0, 0.25, 0.5, 1.0, 2.0):
                rows.extend(_rows_for(n, ratio, shift_cells))
    return rows


def _write_csv(rows: list[MapGateRow], path: Path) -> None:
    fields = list(MapGateRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _plot(rows: list[MapGateRow], path: Path) -> None:
    selected = [
        row
        for row in rows
        if row.n == 64
        and row.density_ratio == 833.3333333333334
        and row.shift_cells == 1.0
    ]
    labels = [row.candidate for row in selected]
    values = [row.relative_delta for row in selected]
    x = np.arange(len(values))
    fig, ax = plt.subplots(figsize=(10.8, 4.5))
    ax.bar(x, values)
    ax.axhline(0.0, color="0.2", lw=0.8)
    ax.set_yscale("symlog", linthresh=1.0e-14)
    ax.set_ylabel("(E1 - E0) / E0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=55, ha="right", fontsize=8)
    ax.set_title("Exact transport map energy gate")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _write_summary(rows: list[MapGateRow], path: Path) -> None:
    def pick(candidate, ratio, shift, n=64):
        return next(
            row.__dict__
            for row in rows
            if row.candidate == candidate
            and row.density_ratio == ratio
            and row.shift_cells == shift
            and row.n == n
        )

    summary = {
        "n64_ratio833_shift1": [
            pick(candidate, 833.3333333333334, 1.0)
            for candidate in sorted({row.candidate for row in rows})
        ],
        "controls": {
            "common_map_ratio833_shift2": pick("common_exact_map", 833.3333333333334, 2.0),
            "imex_velocity_ratio1_shift1": pick("density_map_velocity_imex", 1.0, 1.0),
            "imex_velocity_ratio833_shift1": pick(
                "density_map_velocity_imex",
                833.3333333333334,
                1.0,
            ),
        },
        "interpretation": (
            "Pure transport preserves kinetic energy when rho and velocity "
            "are pullbacks by the same volume-preserving map.  Energy opens "
            "when density and velocity/momentum are evaluated on different "
            "maps, identifying map consistency as the structural requirement."
        ),
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = _run()
    _write_csv(rows, OUT_DIR / "transport_map_gate.csv")
    _write_summary(rows, OUT_DIR / "transport_map_gate_summary.json")
    _plot(rows, OUT_DIR / "transport_map_gate.pdf")
    print(OUT_DIR)


if __name__ == "__main__":
    main()
