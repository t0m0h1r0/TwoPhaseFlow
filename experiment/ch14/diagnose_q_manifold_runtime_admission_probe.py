#!/usr/bin/env python3
"""Short q-manifold admission probe for the Ch14 droplet runtime input.

A3 mapping
----------
Equation:
    Admit a runtime-facing cell-volume snapshot only as
    ``q_T = Q_h(Gamma*) + r`` with visible residual budget.
Discretization:
    Read the canonical Ch14 oscillating-droplet YAML, build its initial
    ellipse gauge on the configured grid as a CPU-labeled diagnostic snapshot,
    and project the resulting cell-volume field to one closed radial mode.
Code:
    This is an admission probe only.  It does not advance a time step, assemble
    capillary force, invoke pressure projection, run T/8, or provide a hidden
    CPU fallback for GPU runtime execution.
"""

from __future__ import annotations

from dataclasses import dataclass
import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from twophase.backend import Backend  # noqa: E402
from twophase.ccd.ccd_solver import CCDSolver  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.geometry.phase_state import GeometricPhaseState  # noqa: E402
from twophase.geometry.q_manifold_projection import (  # noqa: E402
    project_closed_radial_mode_f0,
)
from twophase.levelset.heaviside import heaviside  # noqa: E402
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()

CONFIG = ROOT / "experiment/ch14/config/ch14_oscillating_droplet.yaml"
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"


@dataclass(frozen=True)
class EllipseSpec:
    center: tuple[float, float]
    semi_axes: tuple[float, float]


def _ellipse_from_config(cfg: ExperimentConfig) -> EllipseSpec:
    objects = tuple(cfg.initial_condition.get("objects", ()))
    if len(objects) != 1 or objects[0].get("type") != "ellipse":
        raise ValueError("runtime admission probe expects one ellipse object")
    obj = objects[0]
    if obj.get("interior_phase") != "liquid":
        raise ValueError("runtime admission probe expects liquid inside the ellipse")
    center = tuple(float(value) for value in obj["center"])
    semi_axes = tuple(float(value) for value in obj["semi_axes"])
    if len(center) != 2 or len(semi_axes) != 2:
        raise ValueError("ellipse center and semi_axes must be two-dimensional")
    return EllipseSpec(center=center, semi_axes=semi_axes)


def _grid_from_config(cfg: ExperimentConfig) -> Grid:
    g = cfg.grid
    grid = Grid(
        GridConfig(
            ndim=2,
            N=(int(g.NX), int(g.NY)),
            L=(float(g.LX), float(g.LY)),
            alpha_grid=float(g.alpha_grid),
            fitting_axes=tuple(bool(value) for value in g.fitting_axes),
            fitting_alpha_grid=tuple(float(value) for value in g.fitting_alpha_grid),
            eps_g_factor=float(g.eps_g_factor),
            fitting_eps_g_factor=tuple(float(value) for value in g.fitting_eps_g_factor),
            eps_g_cells=g.eps_g_cells,
            fitting_eps_g_cells=tuple(g.fitting_eps_g_cells),
            wall_refinement_axes=tuple(bool(value) for value in g.wall_refinement_axes),
            wall_alpha_grid=tuple(float(value) for value in g.wall_alpha_grid),
            wall_eps_g_factor=float(g.wall_eps_g_factor),
            wall_eps_g_factor_axes=tuple(float(value) for value in g.wall_eps_g_factor_axes),
            wall_eps_g_cells=tuple(g.wall_eps_g_cells),
            wall_sides=tuple(tuple(side for side in sides) for sides in g.wall_sides),
            dx_min_floor=float(g.dx_min_floor),
            fitting_dx_min_floor=tuple(float(value) for value in g.fitting_dx_min_floor),
        ),
        Backend(use_gpu=False),
    )
    grid.set_boundary_type(g.bc_type)
    return grid


def _ellipse_phi(grid: Grid, ellipse: EllipseSpec) -> np.ndarray:
    x, y = np.meshgrid(
        np.asarray(grid.coords[0], dtype=float),
        np.asarray(grid.coords[1], dtype=float),
        indexing="ij",
    )
    cx, cy = ellipse.center
    ax, ay = ellipse.semi_axes
    scaled_radius = np.sqrt(((x - cx) / ax) ** 2 + ((y - cy) / ay) ** 2)
    return (scaled_radius - 1.0) * min(ax, ay)


def _phase_state_on_admission_grid(cfg: ExperimentConfig, ellipse: EllipseSpec):
    grid = _grid_from_config(cfg)
    eps = float(cfg.grid.eps_factor) * (float(cfg.grid.LX) / float(cfg.grid.NX))
    if float(cfg.grid.alpha_grid) > 1.0:
        phi_uniform = _ellipse_phi(grid, ellipse)
        psi_uniform = heaviside(np, -phi_uniform, eps)
        ccd = CCDSolver(grid, grid.backend, bc_type=cfg.grid.bc_type)
        grid.update_from_levelset(psi_uniform, eps, ccd=ccd)
    phi = _ellipse_phi(grid, ellipse)
    return grid, GeometricPhaseState.from_phi(grid, phi)


def _compute(config_path: pathlib.Path, *, theta_count: int) -> dict[str, object]:
    cfg = ExperimentConfig.from_yaml(config_path)
    ellipse = _ellipse_from_config(cfg)
    grid, phase_state = _phase_state_on_admission_grid(cfg, ellipse)
    q_target = np.asarray(phase_state.q, dtype=float)
    projection = project_closed_radial_mode_f0(
        grid,
        q_target,
        center=ellipse.center,
        mode=2,
        theta_count=int(theta_count),
        sigma=float(cfg.physics.sigma),
    )
    gamma = projection.gamma_state
    coeff = gamma.coefficient_map()["cos_2"]
    residual_report = projection.residual_report
    dx_min = min(float(np.min(np.diff(np.asarray(coords)))) for coords in grid.coords)
    metrics = {
        "target_area": float(np.sum(q_target)),
        "physical_area": float(np.sum(np.asarray(projection.q_phys))),
        "residual_l2": residual_report.l2,
        "relative_l2": residual_report.relative_l2,
        "residual_linf": residual_report.linf,
        "residual_area_abs": residual_report.total_volume_abs,
        "residual_column_linf": residual_report.column_linf,
        "closed_mode_cos_2": float(coeff),
        "base_radius": float(gamma.base_radius),
        "min_radius": float(projection.validity_report["min_radius"]),
        "surface_energy": float(projection.energy_report["surface_energy"]),
        "sign_margin": float(projection.validity_report["sign_margin"]),
        "compat_linf": float(phase_state.compatibility_residual_linf),
        "grid_alpha": float(cfg.grid.alpha_grid),
        "min_dx": dx_min,
        "runtime_steps": 0.0,
        "cpu_diagnostic_snapshot": 1.0,
        "force_admissible": 0.0,
    }
    return {
        "metrics": metrics,
        "fields": {
            "q_target": q_target,
            "q_phys": np.asarray(projection.q_phys, dtype=float),
            "residual": np.asarray(projection.residual, dtype=float),
            "phi": np.asarray(phase_state.phi, dtype=float),
            "x_edges": np.asarray(grid.coords[0], dtype=float),
            "y_edges": np.asarray(grid.coords[1], dtype=float),
            "gamma_vertices": np.asarray(gamma.vertices, dtype=float),
        },
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    fields = results["fields"]
    metrics = results["metrics"]
    x_edges = np.asarray(fields["x_edges"], dtype=float)
    y_edges = np.asarray(fields["y_edges"], dtype=float)
    vertices = np.asarray(fields["gamma_vertices"], dtype=float)
    panels = (
        ("runtime q_T snapshot", np.asarray(fields["q_target"], dtype=float), "viridis"),
        ("admitted q_phys", np.asarray(fields["q_phys"], dtype=float), "viridis"),
        ("residual r", np.asarray(fields["residual"], dtype=float), "coolwarm"),
    )
    fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.3), constrained_layout=True)
    for ax, (title, field, cmap) in zip(axes[:3], panels):
        if title == "residual r":
            vmax = float(np.max(np.abs(field)))
            vmin = -vmax
        else:
            vmin = vmax = None
        mesh = ax.pcolormesh(
            x_edges,
            y_edges,
            field.T,
            shading="auto",
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
        )
        ax.plot(vertices[:, 0], vertices[:, 1], color="white", lw=1.2)
        ax.plot(vertices[:, 0], vertices[:, 1], color="black", lw=0.4)
        ax.set_title(title)
        ax.set_aspect("equal")
        fig.colorbar(mesh, ax=ax, shrink=0.82)
    axes[3].axis("off")
    rows = [
        ("residual_l2", metrics["residual_l2"]),
        ("relative_l2", metrics["relative_l2"]),
        ("residual_area_abs", metrics["residual_area_abs"]),
        ("mode cos_2", metrics["closed_mode_cos_2"]),
        ("compat_linf", metrics["compat_linf"]),
        ("force_admissible", metrics["force_admissible"]),
    ]
    axes[3].text(
        0.0,
        1.0,
        "\n".join(f"{name}: {float(value):.6e}" for name, value in rows),
        va="top",
        ha="left",
        family="monospace",
        fontsize=8.0,
    )
    path = OUT / "q_manifold_runtime_admission_probe"
    save_figure(fig, path)
    plt.close(fig)
    return path.with_suffix(".pdf")


def main() -> None:
    parser = experiment_argparser("Ch14 q-manifold runtime-admission snapshot probe")
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--theta-count", type=int, default=192)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(pathlib.Path(args.config), theta_count=args.theta_count)
        save_results(NPZ, results)
    pdf = _plot(results)
    metrics = results["metrics"]
    print(
        "ADMISSION_PROBE "
        f"residual_l2={float(metrics['residual_l2']):.12e} "
        f"relative_l2={float(metrics['relative_l2']):.12e} "
        f"residual_area_abs={float(metrics['residual_area_abs']):.12e} "
        f"mode_cos_2={float(metrics['closed_mode_cos_2']):.12e} "
        f"compat_linf={float(metrics['compat_linf']):.12e} "
        f"force_admissible={float(metrics['force_admissible']):.1f} "
        f"pdf={pdf}"
    )


if __name__ == "__main__":
    main()
