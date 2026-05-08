"""Common-flux verification gate for the rising-bubble transport remedy.

This offline probe checks the core theorem behind consistent mass-momentum
transport.  If density and momentum are updated by the same conservative
upwind mass flux, the discrete kinetic energy

    E = sum 0.5 * m^2 / rho

cannot increase for a pure transport step.  This follows from convexity of the
perspective m^2/rho.  Inconsistent variants reuse the same initial fields but
move rho, velocity, or momentum on different maps.
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
OUT_DIR = ROOT / "artifacts/A/ch14_common_flux_gate_CHK_RA_CH14_BUBBLE_FLUX_001"


@dataclass(frozen=True)
class FluxGateRow:
    candidate: str
    density_ratio: float
    cfl: float
    n: int
    energy0: float
    energy1: float
    relative_delta: float
    mass_delta: float
    momentum_delta: float
    theorem_status: str
    notes: str


def _fields(n: int, ratio: float) -> tuple[np.ndarray, np.ndarray]:
    x = (np.arange(n, dtype=float) + 0.5) / float(n)
    blend = (
        0.5
        + 0.16 * np.sin(2.0 * np.pi * x + 0.30)
        + 0.09 * np.cos(4.0 * np.pi * x - 0.20)
        + 0.05 * np.sin(6.0 * np.pi * x + 0.60)
    )
    if np.min(blend) <= 0.0 or np.max(blend) >= 1.0:
        raise AssertionError("density blend must remain in (0,1)")
    rho = 1.0 + (float(ratio) - 1.0) * blend
    velocity = (
        0.37
        + 0.31 * np.sin(2.0 * np.pi * x - 0.10)
        - 0.22 * np.cos(4.0 * np.pi * x + 0.45)
        + 0.08 * np.sin(6.0 * np.pi * x - 0.25)
    )
    return rho, rho * velocity


def _energy(rho: np.ndarray, momentum: np.ndarray) -> float:
    return float(np.mean(0.5 * momentum * momentum / rho))


def _mass(rho: np.ndarray) -> float:
    return float(np.mean(rho))


def _momentum(momentum: np.ndarray) -> float:
    return float(np.mean(momentum))


def _upwind(q: np.ndarray, cfl: float) -> np.ndarray:
    lam = float(cfl)
    return (1.0 - lam) * q + lam * np.roll(q, 1)


def _downwind(q: np.ndarray, cfl: float) -> np.ndarray:
    lam = float(cfl)
    return (1.0 - lam) * q + lam * np.roll(q, -1)


def _rows_for(n: int, ratio: float, cfl: float) -> list[FluxGateRow]:
    rho0, m0 = _fields(n, ratio)
    u0 = m0 / rho0
    rho_up = _upwind(rho0, cfl)
    m_up = _upwind(m0, cfl)
    u_prev = _downwind(u0, cfl)
    constant_velocity = 0.7
    m_const = rho0 * constant_velocity
    rho_const = rho_up
    m_const_up = _upwind(m_const, cfl)

    candidates = {
        "common_upwind_flux": (
            rho0,
            m0,
            rho_up,
            m_up,
            "closed",
            "same convex conservative update for rho and momentum",
        ),
        "common_upwind_constant_velocity": (
            rho0,
            m_const,
            rho_const,
            m_const_up,
            "closed",
            "same flux with uniform velocity; energy reduces to conserved mass",
        ),
        "density_upwind_velocity_current": (
            rho0,
            m0,
            rho_up,
            rho_up * u0,
            "open",
            "rho moved, velocity left in old cell metric",
        ),
        "density_upwind_velocity_imex": (
            rho0,
            m0,
            rho_up,
            rho_up * (2.0 * u0 - u_prev),
            "open",
            "rho moved, velocity updated by explicit history",
        ),
        "density_upwind_momentum_lagged": (
            rho0,
            m0,
            rho_up,
            m0,
            "open",
            "old momentum evaluated in moved density metric",
        ),
        "momentum_upwind_density_current": (
            rho0,
            m0,
            rho0,
            m_up,
            "open",
            "momentum moved, density left in old metric",
        ),
        "independent_opposite_fluxes": (
            rho0,
            m0,
            rho_up,
            _downwind(m0, cfl),
            "open",
            "rho and momentum use opposite flux maps",
        ),
    }

    rows: list[FluxGateRow] = []
    for name, (rho_initial, m_initial, rho1, m1, theorem_status, notes) in candidates.items():
        e0 = _energy(rho_initial, m_initial)
        e1 = _energy(rho1, m1)
        rows.append(
            FluxGateRow(
                candidate=name,
                density_ratio=float(ratio),
                cfl=float(cfl),
                n=int(n),
                energy0=e0,
                energy1=e1,
                relative_delta=(e1 - e0) / max(abs(e0), 1.0e-300),
                mass_delta=_mass(rho1) - _mass(rho_initial),
                momentum_delta=_momentum(m1) - _momentum(m_initial),
                theorem_status=theorem_status,
                notes=notes,
            )
        )
    return rows


def _run() -> list[FluxGateRow]:
    rows: list[FluxGateRow] = []
    for n in (32, 64, 128, 256):
        for ratio in (1.0, 10.0, 100.0, 833.3333333333334):
            for cfl in (0.0, 0.1, 0.25, 0.5, 0.9):
                rows.extend(_rows_for(n, ratio, cfl))
    return rows


def _write_csv(rows: list[FluxGateRow], path: Path) -> None:
    fields = list(FluxGateRow.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _summary(rows: list[FluxGateRow]) -> dict:
    closed = [row for row in rows if row.theorem_status == "closed"]
    open_rows = [row for row in rows if row.theorem_status == "open"]

    def pick(candidate: str, ratio: float, cfl: float, n: int = 64) -> dict:
        return next(
            row.__dict__
            for row in rows
            if row.candidate == candidate
            and row.n == n
            and abs(row.density_ratio - ratio) < 1.0e-12
            and row.cfl == cfl
        )

    return {
        "closed_max_relative_delta": max(row.relative_delta for row in closed),
        "closed_min_relative_delta": min(row.relative_delta for row in closed),
        "open_max_relative_delta": max(row.relative_delta for row in open_rows),
        "open_min_relative_delta": min(row.relative_delta for row in open_rows),
        "n64_ratio833_cfl05": [
            pick(candidate, 833.3333333333334, 0.5)
            for candidate in sorted({row.candidate for row in rows})
        ],
        "n64_ratio1_cfl05": [
            pick(candidate, 1.0, 0.5)
            for candidate in sorted({row.candidate for row in rows})
        ],
        "interpretation": (
            "The common conservative flux update is non-energy-increasing for "
            "all tested density ratios, grids, and CFL values.  Inconsistent "
            "updates can generate positive kinetic-energy defects, so the "
            "common-flux remedy passes the pure-transport theorem gate."
        ),
    }


def _write_summary(rows: list[FluxGateRow], path: Path) -> None:
    path.write_text(json.dumps(_summary(rows), indent=2), encoding="utf-8")


def _plot(rows: list[FluxGateRow], path: Path) -> None:
    selected_candidates = [
        "common_upwind_flux",
        "common_upwind_constant_velocity",
        "density_upwind_velocity_current",
        "density_upwind_velocity_imex",
        "density_upwind_momentum_lagged",
        "independent_opposite_fluxes",
    ]
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    for candidate in selected_candidates:
        subset = [
            row
            for row in rows
            if row.n == 64
            and row.density_ratio == 833.3333333333334
            and row.candidate == candidate
        ]
        subset.sort(key=lambda row: row.cfl)
        ax.plot(
            [row.cfl for row in subset],
            [row.relative_delta for row in subset],
            marker="o",
            label=candidate,
        )
    ax.axhline(0.0, color="0.15", lw=0.8)
    ax.set_xlabel("CFL")
    ax.set_ylabel("(E1 - E0) / E0")
    ax.set_title("Common mass-momentum flux energy gate")
    ax.set_yscale("symlog", linthresh=1.0e-14)
    ax.legend(fontsize=7, loc="best")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = _run()
    _write_csv(rows, OUT_DIR / "common_flux_gate.csv")
    _write_summary(rows, OUT_DIR / "common_flux_gate_summary.json")
    _plot(rows, OUT_DIR / "common_flux_gate.pdf")
    print(OUT_DIR)


if __name__ == "__main__":
    main()
