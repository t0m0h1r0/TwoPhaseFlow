"""Manufactured energy-identity probes for two-phase momentum transport.

The probe isolates whether convection and its explicit history respect the
physical density-weighted kinetic-energy metric.  It does not advance the
rising-bubble simulation and does not change production code.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ns_terms.convection import ConvectionTerm
from twophase.ns_terms.fccd_convection import FCCDConvectionTerm
from twophase.ns_terms.uccd6_convection import UCCD6ConvectionTerm


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts/A/ch14_momentum_transport_manufactured_CHK_RA_CH14_BUBBLE_MFG_001"
CHECKPOINT_GRID = (
    ROOT
    / "experiment/ch14/results/_tmp_ch14_rising_bubble_si10mm_n32x64_rollback_20260508c_t0p01/checkpoint_final.npz"
)


@dataclass(frozen=True)
class ProbeCase:
    grid_name: str
    density_name: str
    operator_name: str
    history_name: str
    n_effective: int
    ke: float
    unit_power: float
    rho_power: float
    density_correction: float
    paired_power: float
    cross_prev_rho_power: float
    imex_rho_power: float
    imex_paired_power: float
    current_linf: float
    imex_linf: float
    normalized_paired_rate: float
    normalized_imex_rate: float


class _Context:
    pass


def _periodic_grid(backend: Backend, n: int) -> tuple[Grid, str]:
    return Grid(GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)), backend), "periodic"


def _wall_checkpoint_grid(backend: Backend) -> tuple[Grid, str]:
    z = np.load(CHECKPOINT_GRID, allow_pickle=True)
    grid = Grid(GridConfig(ndim=2, N=(32, 64), L=(0.01, 0.02)), backend)
    grid.coords[0] = np.asarray(z["grid/coords/0"], dtype=np.float64)
    grid.coords[1] = np.asarray(z["grid/coords/1"], dtype=np.float64)
    grid.h[0] = np.asarray(z["grid/h/0"], dtype=np.float64)
    grid.h[1] = np.asarray(z["grid/h/1"], dtype=np.float64)
    grid._cell_volumes = None
    grid._build_metrics()
    return grid, "wall"


def _periodic_volume(grid: Grid) -> np.ndarray:
    dx = float(grid.L[0]) / int(grid.N[0])
    dy = float(grid.L[1]) / int(grid.N[1])
    volume = np.full(grid.shape, dx * dy, dtype=np.float64)
    volume[-1, :] = 0.0
    volume[:, -1] = 0.0
    return volume


def _wall_volume(grid: Grid) -> np.ndarray:
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


def _node_volume(grid: Grid, bc_type: str) -> np.ndarray:
    return _periodic_volume(grid) if bc_type == "periodic" else _wall_volume(grid)


def _mesh(grid: Grid) -> tuple[np.ndarray, np.ndarray]:
    return np.meshgrid(
        np.asarray(grid.coords[0], dtype=np.float64),
        np.asarray(grid.coords[1], dtype=np.float64),
        indexing="ij",
    )


def _periodic_velocity(grid: Grid, *, shift: float = 0.0) -> list[np.ndarray]:
    x, y = _mesh(grid)
    xh = x + shift
    u = np.sin(2.0 * np.pi * xh) * np.cos(2.0 * np.pi * y)
    v = -np.cos(2.0 * np.pi * xh) * np.sin(2.0 * np.pi * y)
    return [u, v]


def _wall_velocity(grid: Grid, *, shift: float = 0.0) -> list[np.ndarray]:
    x, y = _mesh(grid)
    lx, ly = float(grid.L[0]), float(grid.L[1])
    phase = shift / max(lx, 1.0e-30)
    sx = np.sin(np.pi * x / lx)
    cx = np.cos(np.pi * x / lx)
    sy = np.sin(np.pi * y / ly)
    cy = np.cos(np.pi * y / ly)
    # Streamfunction psi_s = A sin^2(pi x/Lx) sin^2(pi y/Ly), with a mild
    # interior phase modulation that keeps zero-normal wall velocity.
    mod = 1.0 + 0.15 * np.sin(2.0 * np.pi * x / lx + phase)
    dmod_dx = 0.15 * (2.0 * np.pi / lx) * np.cos(2.0 * np.pi * x / lx + phase)
    amp = 0.02
    u = amp * mod * sx**2 * (2.0 * np.pi / ly) * sy * cy
    v = -amp * (2.0 * sx * cx * (np.pi / lx) * mod + sx**2 * dmod_dx) * sy**2
    return [u, v]


def _density(grid: Grid, bc_type: str, name: str) -> np.ndarray:
    x, y = _mesh(grid)
    if name == "constant":
        return np.ones(grid.shape, dtype=np.float64)
    if name == "smooth_mild":
        lx, ly = float(grid.L[0]), float(grid.L[1])
        return 1.0 + 0.3 * np.sin(2.0 * np.pi * x / lx + 0.2) * np.sin(
            2.0 * np.pi * y / ly - 0.1
        )
    if name == "smooth_high_ratio":
        lx, ly = float(grid.L[0]), float(grid.L[1])
        blend = 0.5 + 0.25 * np.sin(2.0 * np.pi * x / lx + 0.2) * np.sin(
            2.0 * np.pi * y / ly - 0.1
        )
        return 1.2 + (1000.0 - 1.2) * blend
    if name == "bubble_high_ratio":
        lx, ly = float(grid.L[0]), float(grid.L[1])
        r = np.sqrt((x - 0.5 * lx) ** 2 + (y - 0.35 * ly) ** 2)
        radius = 0.22 * min(lx, ly)
        eps = 0.06 * min(lx, ly)
        liquid_indicator = 1.0 / (1.0 + np.exp(-(r - radius) / eps))
        return 1.2 + (1000.0 - 1.2) * liquid_indicator
    raise ValueError(f"unknown density case {name!r}")


def _density_rhs(
    *,
    fccd: FCCDSolver,
    rho: np.ndarray,
    velocity: list[np.ndarray],
) -> np.ndarray:
    xp = fccd.xp
    rho_dev = xp.asarray(rho)
    rhs = xp.zeros_like(rho_dev)
    for axis in range(fccd.grid.ndim):
        flux = fccd.face_value(rho_dev, axis) * fccd.face_value(
            xp.asarray(velocity[axis]),
            axis,
        )
        rhs = rhs - fccd.face_divergence(flux, axis)
    return np.asarray(rhs)


def _operators(backend: Backend, grid: Grid, ccd: CCDSolver, fccd: FCCDSolver):
    return {
        "ccd": ConvectionTerm(backend),
        "uccd6": UCCD6ConvectionTerm(backend, grid, ccd, sigma=1.0e-3),
        "fccd_flux": FCCDConvectionTerm(backend, fccd, mode="flux"),
        "fccd_nodal": FCCDConvectionTerm(backend, fccd, mode="node"),
    }


def _compute_operator(operator, backend: Backend, ccd: CCDSolver, fccd: FCCDSolver, velocity):
    ctx = _Context()
    ctx.velocity = [backend.xp.asarray(component) for component in velocity]
    ctx.ccd = ccd
    ctx.fccd = fccd
    return [np.asarray(component) for component in operator.compute(ctx)]


def _probe_grid(
    *,
    backend: Backend,
    grid: Grid,
    bc_type: str,
    grid_name: str,
    density_names: tuple[str, ...],
    history_shift: float,
) -> list[ProbeCase]:
    ccd = CCDSolver(grid, backend, bc_type=bc_type)
    fccd = FCCDSolver(grid, backend, bc_type=bc_type, ccd_solver=ccd)
    volume = _node_volume(grid, bc_type)
    current_velocity = (
        _periodic_velocity(grid, shift=0.0)
        if bc_type == "periodic"
        else _wall_velocity(grid, shift=0.0)
    )
    previous_velocity = (
        _periodic_velocity(grid, shift=history_shift)
        if bc_type == "periodic"
        else _wall_velocity(grid, shift=history_shift)
    )
    speed2 = current_velocity[0] ** 2 + current_velocity[1] ** 2
    rows: list[ProbeCase] = []
    for density_name in density_names:
        rho = _density(grid, bc_type, density_name)
        rho_rhs = _density_rhs(fccd=fccd, rho=rho, velocity=current_velocity)
        density_correction = float(np.sum(0.5 * speed2 * volume * rho_rhs))
        ke = float(0.5 * np.sum(rho * volume * speed2))
        for operator_name, operator in _operators(backend, grid, ccd, fccd).items():
            conv_n = _compute_operator(operator, backend, ccd, fccd, current_velocity)
            conv_prev = _compute_operator(operator, backend, ccd, fccd, previous_velocity)
            current_dot = current_velocity[0] * conv_n[0] + current_velocity[1] * conv_n[1]
            prev_cross_dot = (
                current_velocity[0] * conv_prev[0] + current_velocity[1] * conv_prev[1]
            )
            imex = [2.0 * conv_n[0] - conv_prev[0], 2.0 * conv_n[1] - conv_prev[1]]
            imex_dot = current_velocity[0] * imex[0] + current_velocity[1] * imex[1]
            unit_power = float(np.sum(volume * current_dot))
            rho_power = float(np.sum(rho * volume * current_dot))
            paired_power = float(rho_power + density_correction)
            cross_prev = float(np.sum(rho * volume * prev_cross_dot))
            imex_power = float(np.sum(rho * volume * imex_dot))
            imex_paired = float(imex_power + density_correction)
            denom = max(abs(ke), 1.0e-300)
            rows.append(
                ProbeCase(
                    grid_name=grid_name,
                    density_name=density_name,
                    operator_name=operator_name,
                    history_name=f"shift={history_shift:.6g}",
                    n_effective=int(grid.N[0]),
                    ke=ke,
                    unit_power=unit_power,
                    rho_power=rho_power,
                    density_correction=density_correction,
                    paired_power=paired_power,
                    cross_prev_rho_power=cross_prev,
                    imex_rho_power=imex_power,
                    imex_paired_power=imex_paired,
                    current_linf=float(
                        max(np.max(np.abs(conv_n[0])), np.max(np.abs(conv_n[1])))
                    ),
                    imex_linf=float(
                        max(np.max(np.abs(imex[0])), np.max(np.abs(imex[1])))
                    ),
                    normalized_paired_rate=paired_power / denom,
                    normalized_imex_rate=imex_paired / denom,
                )
            )
    return rows


def _write_csv(rows: list[ProbeCase], path: Path) -> None:
    fieldnames = list(ProbeCase.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def _plot_convergence(rows: list[ProbeCase], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), sharey=True)
    operators = ("ccd", "uccd6", "fccd_flux", "fccd_nodal")
    densities = ("constant", "smooth_mild", "smooth_high_ratio", "bubble_high_ratio")
    for ax, metric in zip(axes, ("normalized_paired_rate", "normalized_imex_rate"), strict=True):
        for density_name in densities:
            values = []
            ns = []
            for n in (16, 32, 64):
                selected = [
                    row
                    for row in rows
                    if row.grid_name == "periodic_uniform"
                    and row.operator_name == "uccd6"
                    and row.density_name == density_name
                    and row.n_effective == n
                ]
                if selected:
                    ns.append(n)
                    values.append(abs(getattr(selected[0], metric)))
            ax.loglog(ns, values, marker="o", label=density_name)
        ax.set_xlabel("N")
        ax.set_ylabel(f"|{metric}|")
        ax.set_title("UCCD6 periodic manufactured")
        ax.grid(True, which="both", lw=0.3, alpha=0.4)
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _plot_wall_summary(rows: list[ProbeCase], path: Path) -> None:
    selected = [
        row
        for row in rows
        if row.grid_name == "rising_bubble_saved_wall_grid"
        and row.density_name in {"constant", "bubble_high_ratio"}
    ]
    labels = [f"{row.operator_name}\n{row.density_name}" for row in selected]
    x = np.arange(len(selected))
    fig, ax = plt.subplots(figsize=(11.0, 4.4))
    ax.bar(x - 0.18, [row.normalized_paired_rate for row in selected], width=0.34, label="paired")
    ax.bar(x + 0.18, [row.normalized_imex_rate for row in selected], width=0.34, label="IMEX paired")
    ax.axhline(0.0, color="0.2", lw=0.8)
    ax.set_yscale("symlog", linthresh=1.0e-8)
    ax.set_ylabel("power / kinetic energy")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.legend(frameon=False)
    ax.set_title("Saved wall/nonuniform grid manufactured probe")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _write_summary(rows: list[ProbeCase], path: Path) -> None:
    def select(**kwargs):
        return [
            row.__dict__
            for row in rows
            if all(getattr(row, key) == value for key, value in kwargs.items())
        ]

    summary = {
        "periodic_uccd6_n32": select(grid_name="periodic_uniform", operator_name="uccd6", n_effective=32),
        "saved_wall_grid": select(grid_name="rising_bubble_saved_wall_grid"),
        "interpretation": (
            "The continuum paired transport power should vanish for closed or "
            "periodic divergence-free manufactured fields. Non-vanishing paired "
            "or IMEX-paired power isolates a momentum transport/time-history "
            "energy-metric defect independent of capillary geometry."
        ),
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    backend = Backend(use_gpu=False)
    rows: list[ProbeCase] = []
    density_names = ("constant", "smooth_mild", "smooth_high_ratio", "bubble_high_ratio")
    for n in (16, 32, 64):
        grid, bc_type = _periodic_grid(backend, n)
        rows.extend(
            _probe_grid(
                backend=backend,
                grid=grid,
                bc_type=bc_type,
                grid_name="periodic_uniform",
                density_names=density_names,
                history_shift=0.37 / n,
            )
        )
    wall_grid, wall_bc = _wall_checkpoint_grid(backend)
    rows.extend(
        _probe_grid(
            backend=backend,
            grid=wall_grid,
            bc_type=wall_bc,
            grid_name="rising_bubble_saved_wall_grid",
            density_names=density_names,
            history_shift=0.00037,
        )
    )
    _write_csv(rows, OUT_DIR / "manufactured_energy_identity.csv")
    _write_summary(rows, OUT_DIR / "manufactured_energy_identity_summary.json")
    _plot_convergence(rows, OUT_DIR / "periodic_uccd6_convergence.pdf")
    _plot_wall_summary(rows, OUT_DIR / "saved_wall_grid_summary.pdf")
    print(OUT_DIR)


if __name__ == "__main__":
    main()
