"""Offline energy-budget probe for the SI rising-bubble blow-up RCA.

This script intentionally does not advance the simulation.  It evaluates
checkpoint fields against the discrete energy identities that a two-phase
momentum transport operator should satisfy.
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
from matplotlib.colors import SymLogNorm

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ns_terms.convection import ConvectionTerm
from twophase.ns_terms.fccd_convection import FCCDConvectionTerm
from twophase.ns_terms.uccd6_convection import UCCD6ConvectionTerm


ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = ROOT / "experiment/ch14/results"
OUT_DIR = ROOT / "artifacts/A/ch14_rising_bubble_energy_budget_CHK_RA_CH14_BUBBLE_ENERGY_001"

RHO_GAS = 1.2
RHO_LIQUID = 1000.0


@dataclass(frozen=True)
class Case:
    name: str
    checkpoint: Path
    label: str


CASES = (
    Case(
        "stable_t0p01",
        RESULT_ROOT
        / "_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p01"
        / "checkpoint_final.npz",
        "stable t~0.01",
    ),
    Case(
        "pre_blowup_t0p018033",
        RESULT_ROOT
        / "_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p02"
        / "checkpoint_pre_blowup_input.npz",
        "pre-blow-up",
    ),
    Case(
        "final_guard_t0p018033",
        RESULT_ROOT
        / "_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p02"
        / "checkpoint_final.npz",
        "guard final",
    ),
)


class _Context:
    pass


def _load_grid(backend: Backend, z: np.lib.npyio.NpzFile) -> Grid:
    grid = Grid(GridConfig(ndim=2, N=(32, 64), L=(0.01, 0.02)), backend)
    grid.coords[0] = np.asarray(z["grid/coords/0"], dtype=np.float64)
    grid.coords[1] = np.asarray(z["grid/coords/1"], dtype=np.float64)
    grid.h[0] = np.asarray(z["grid/h/0"], dtype=np.float64)
    grid.h[1] = np.asarray(z["grid/h/1"], dtype=np.float64)
    grid._cell_volumes = None
    grid._build_metrics()
    return grid


def _node_control_volumes(grid: Grid) -> np.ndarray:
    widths = []
    for axis in range(grid.ndim):
        coords = np.asarray(grid.coords[axis], dtype=np.float64)
        d = np.diff(coords)
        w = np.empty_like(coords)
        w[0] = 0.5 * d[0]
        w[-1] = 0.5 * d[-1]
        w[1:-1] = 0.5 * (coords[2:] - coords[:-2])
        widths.append(w)
    return widths[0][:, None] * widths[1][None, :]


def _density_from_psi(psi: np.ndarray) -> np.ndarray:
    return RHO_GAS + psi * (RHO_LIQUID - RHO_GAS)


def _density_transport_rhs(
    *,
    fccd: FCCDSolver,
    rho: np.ndarray,
    velocity: list[np.ndarray],
) -> np.ndarray:
    xp = fccd.xp
    rhs = xp.zeros_like(xp.asarray(rho))
    rho_dev = xp.asarray(rho)
    for axis in range(fccd.grid.ndim):
        flux = fccd.face_value(rho_dev, axis) * fccd.face_value(
            xp.asarray(velocity[axis]),
            axis,
        )
        rhs = rhs - fccd.face_divergence(flux, axis)
    return np.asarray(rhs)


def _phase_sums(local: np.ndarray, psi: np.ndarray) -> dict[str, float]:
    masks = {
        "gas_core": psi < 0.05,
        "gas_interface": (psi >= 0.05) & (psi < 0.5),
        "liquid_interface": (psi >= 0.5) & (psi < 0.95),
        "liquid_bulk": psi >= 0.95,
    }
    return {name: float(np.sum(local[mask])) for name, mask in masks.items()}


def _make_operators(backend: Backend, grid: Grid, ccd: CCDSolver, fccd: FCCDSolver):
    return {
        "ccd": ConvectionTerm(backend),
        "uccd6": UCCD6ConvectionTerm(backend, grid, ccd, sigma=1.0e-3),
        "fccd_flux": FCCDConvectionTerm(backend, fccd, mode="flux"),
        "fccd_nodal": FCCDConvectionTerm(backend, fccd, mode="node"),
    }


def _case_probe(case: Case, backend: Backend) -> tuple[list[dict], dict]:
    z = np.load(case.checkpoint, allow_pickle=True)
    grid = _load_grid(backend, z)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)
    xp = backend.xp

    psi = np.asarray(z["state/psi"], dtype=np.float64)
    u = np.asarray(z["state/u"], dtype=np.float64)
    v = np.asarray(z["state/v"], dtype=np.float64)
    rho = _density_from_psi(psi)
    volume = _node_control_volumes(grid)
    speed2 = u * u + v * v
    velocity = [u, v]
    rho_rhs = _density_transport_rhs(fccd=fccd, rho=rho, velocity=velocity)

    ctx = _Context()
    ctx.velocity = [xp.asarray(u), xp.asarray(v)]
    ctx.ccd = ccd
    ctx.fccd = fccd

    rows = []
    uccd6_maps = {}
    conv_prev_count = int(z["solver/conv_prev/count"]) if "solver/conv_prev/count" in z.files else 0
    conv_prev = (
        [
            np.asarray(z[f"solver/conv_prev/{axis}"], dtype=np.float64)
            for axis in range(conv_prev_count)
        ]
        if conv_prev_count == 2
        else None
    )
    for name, operator in _make_operators(backend, grid, ccd, fccd).items():
        conv = [np.asarray(component) for component in operator.compute(ctx)]
        imex_step = None
        if name == "uccd6" and conv_prev is not None:
            imex_step = [2.0 * conv[0] - conv_prev[0], 2.0 * conv[1] - conv_prev[1]]
        raw_power_density = u * conv[0] + v * conv[1]
        rho_momentum_density = rho * raw_power_density
        density_correction_density = 0.5 * speed2 * rho_rhs
        paired_density = rho_momentum_density + density_correction_density

        local_rho_power = volume * rho_momentum_density
        local_density_correction = volume * density_correction_density
        local_paired = volume * paired_density
        row = {
            "case": case.name,
            "case_label": case.label,
            "operator": name,
            "unit_no_volume_power": float(np.sum(raw_power_density)),
            "unit_volume_power": float(np.sum(volume * raw_power_density)),
            "rho_volume_power": float(np.sum(local_rho_power)),
            "density_transport_correction": float(np.sum(local_density_correction)),
            "paired_transport_power": float(np.sum(local_paired)),
            "conv_linf": float(max(np.max(np.abs(conv[0])), np.max(np.abs(conv[1])))),
            "conv_p99": float(
                max(
                    np.percentile(np.abs(conv[0]), 99.0),
                    np.percentile(np.abs(conv[1]), 99.0),
                )
            ),
            "ke": float(0.5 * np.sum(rho * volume * speed2)),
            "u_linf": float(np.max(np.abs(u))),
            "v_linf": float(np.max(np.abs(v))),
            "rho_rhs_linf": float(np.max(np.abs(rho_rhs))),
            "positive_rho_power": float(np.sum(local_rho_power[local_rho_power > 0.0])),
            "negative_rho_power": float(np.sum(local_rho_power[local_rho_power < 0.0])),
            "positive_paired_power": float(np.sum(local_paired[local_paired > 0.0])),
            "negative_paired_power": float(np.sum(local_paired[local_paired < 0.0])),
            "conv_prev_rho_volume_power": float(
                np.sum(volume * rho * (u * conv_prev[0] + v * conv_prev[1]))
            )
            if name == "uccd6" and conv_prev is not None
            else float("nan"),
            "imex_bdf2_rho_volume_power": float(
                np.sum(volume * rho * (u * imex_step[0] + v * imex_step[1]))
            )
            if imex_step is not None
            else float("nan"),
            "imex_bdf2_linf": float(
                max(np.max(np.abs(imex_step[0])), np.max(np.abs(imex_step[1])))
            )
            if imex_step is not None
            else float("nan"),
        }
        row.update(
            {
                f"rho_power_{key}": value
                for key, value in _phase_sums(local_rho_power, psi).items()
            }
        )
        row.update(
            {
                f"paired_power_{key}": value
                for key, value in _phase_sums(local_paired, psi).items()
            }
        )
        rows.append(row)
        if name == "uccd6":
            uccd6_maps = {
                "local_rho_power": local_rho_power,
                "local_paired": local_paired,
                "psi": psi,
                "u": u,
                "v": v,
                "x": np.asarray(grid.coords[0]),
                "y": np.asarray(grid.coords[1]),
            }
    return rows, uccd6_maps


def _write_csv(rows: list[dict], path: Path) -> None:
    keys = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _plot_budget(rows: list[dict], path: Path) -> None:
    selected = [row for row in rows if row["operator"] == "uccd6"]
    labels = [row["case_label"] for row in selected]
    x = np.arange(len(selected))
    width = 0.24
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    series = [
        ("unit_volume_power", "unit dV"),
        ("rho_volume_power", "rho dV"),
        ("paired_transport_power", "rho dV + density transport"),
    ]
    for offset, (key, label) in zip((-width, 0.0, width), series, strict=True):
        ax.bar(x + offset, [row[key] for row in selected], width=width, label=label)
    ax.axhline(0.0, color="0.2", lw=0.8)
    ax.set_yscale("symlog", linthresh=1.0e-7)
    ax.set_ylabel("convective power contribution")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("UCCD6 energy metric probe")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_imex_history(rows: list[dict], path: Path) -> None:
    selected = [row for row in rows if row["operator"] == "uccd6"]
    labels = [row["case_label"] for row in selected]
    x = np.arange(len(selected))
    width = 0.24
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    series = [
        ("conv_prev_rho_volume_power", "stored conv_prev"),
        ("rho_volume_power", "current conv_n"),
        ("imex_bdf2_rho_volume_power", "2 conv_n - conv_prev"),
    ]
    for offset, (key, label) in zip((-width, 0.0, width), series, strict=True):
        ax.bar(x + offset, [row[key] for row in selected], width=width, label=label)
    ax.axhline(0.0, color="0.2", lw=0.8)
    ax.set_yscale("symlog", linthresh=1.0e-7)
    ax.set_ylabel("rho dV power")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("UCCD6 IMEX-BDF2 history power")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_maps(maps_by_case: dict[str, dict], path: Path, key: str, title: str) -> None:
    vmax = max(
        float(np.max(np.abs(maps[key])))
        for maps in maps_by_case.values()
        if maps
    )
    linthresh = max(vmax * 1.0e-6, 1.0e-14)
    fig, axes = plt.subplots(1, len(CASES), figsize=(11.5, 3.8), sharex=True, sharey=True)
    if len(CASES) == 1:
        axes = [axes]
    image = None
    for ax, case in zip(axes, CASES, strict=True):
        maps = maps_by_case[case.name]
        x = maps["x"]
        y = maps["y"]
        X, Y = np.meshgrid(x, y, indexing="ij")
        image = ax.pcolormesh(
            X,
            Y,
            maps[key],
            shading="auto",
            cmap="coolwarm",
            norm=SymLogNorm(linthresh=linthresh, vmin=-vmax, vmax=vmax),
            rasterized=True,
        )
        ax.contour(X, Y, maps["psi"], levels=[0.5], colors="black", linewidths=0.7)
        stride_x = max(1, len(x) // 12)
        stride_y = max(1, len(y) // 18)
        ax.quiver(
            X[::stride_x, ::stride_y],
            Y[::stride_x, ::stride_y],
            maps["u"][::stride_x, ::stride_y],
            maps["v"][::stride_x, ::stride_y],
            color="0.15",
            angles="xy",
            scale_units="xy",
            scale=max(np.max(np.hypot(maps["u"], maps["v"])), 1.0e-14) / 0.0016,
            width=0.0025,
        )
        ax.set_aspect("equal")
        ax.set_title(case.label)
        ax.set_xlabel("x [m]")
    axes[0].set_ylabel("y [m]")
    fig.suptitle(title)
    fig.colorbar(image, ax=axes, fraction=0.025, pad=0.02)
    fig.savefig(path)
    plt.close(fig)


def _write_summary(rows: list[dict], path: Path) -> None:
    uccd6 = [row for row in rows if row["operator"] == "uccd6"]
    summary = {
        "case_count": len(CASES),
        "operator_count": len({row["operator"] for row in rows}),
        "uccd6": uccd6,
        "interpretation": (
            "A two-phase transport-compatible convection operator should not "
            "create positive rho-weighted kinetic energy on closed walls. "
            "Positive rho_volume_power or paired_transport_power identifies an "
            "energy-metric mismatch that cannot be repaired by pressure clipping "
            "or velocity damping."
        ),
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    backend = Backend(use_gpu=False)
    rows: list[dict] = []
    maps_by_case: dict[str, dict] = {}
    for case in CASES:
        case_rows, case_maps = _case_probe(case, backend)
        rows.extend(case_rows)
        maps_by_case[case.name] = case_maps

    _write_csv(rows, OUT_DIR / "energy_budget.csv")
    _write_summary(rows, OUT_DIR / "energy_budget_summary.json")
    _plot_budget(rows, OUT_DIR / "uccd6_energy_metric_probe.pdf")
    _plot_imex_history(rows, OUT_DIR / "uccd6_imex_history_power.pdf")
    _plot_maps(
        maps_by_case,
        OUT_DIR / "uccd6_local_rho_power_series.pdf",
        "local_rho_power",
        "UCCD6 local rho-weighted convective power",
    )
    _plot_maps(
        maps_by_case,
        OUT_DIR / "uccd6_local_paired_transport_power_series.pdf",
        "local_paired",
        "UCCD6 local paired transport power",
    )
    print(OUT_DIR)


if __name__ == "__main__":
    main()
