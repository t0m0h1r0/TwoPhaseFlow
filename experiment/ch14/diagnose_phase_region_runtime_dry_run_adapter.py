#!/usr/bin/env python3
"""PhaseRegion dry-run adapter for the Ch14 droplet runtime snapshot.

A3 mapping
----------
Equation:
    Runtime owns liquid cell volume ``q_l`` while the current PhaseRegion
    theory owns gas region ``Omega_g``.  The dry-run adapter must expose
    ``q_g = |C| - q_l`` before residual splitting.
Discretization:
    Build the Ch14 oscillating-droplet initial state without advancing time.
    Project the liquid snapshot to a closed radial chart, reinterpret that
    chart as a ``GAS_OUTSIDE`` PhaseRegion component, and assemble the gas
    residual ``r_g = q_target,g - Q_h(Omega_g)``.
Code:
    This is a diagnostic dry run only.  It does not advance a solver step,
    rebuild phi, assemble capillary force, project pressure/velocity, run a
    nonlinear optimizer, micro-step, or run T/8.
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
from twophase.geometry import (  # noqa: E402
    BoundaryAttachment,
    CellMeasurePhase,
    ChartType,
    ConstraintPolicy,
    InterfaceAtlas,
    PhaseRegionBatch,
    PhaseRole,
    TopologyType,
    assemble_phase_region_measurement,
    closed_polygon_geometry,
    component_offsets_from_batch_ids,
    enum_values,
    map_cell_measure_to_phase_owner,
    project_closed_radial_mode_f0,
)
from twophase.geometry.phase_state import GeometricPhaseState  # noqa: E402
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
    """Initial liquid ellipse declared by the Ch14 runtime YAML."""

    center: tuple[float, float]
    semi_axes: tuple[float, float]


def _ellipse_from_config(cfg: ExperimentConfig) -> EllipseSpec:
    objects = tuple(cfg.initial_condition.get("objects", ()))
    if len(objects) != 1 or objects[0].get("type") != "ellipse":
        raise ValueError("runtime dry-run expects one ellipse object")
    obj = objects[0]
    if obj.get("interior_phase") != "liquid":
        raise ValueError("runtime dry-run expects liquid inside the ellipse")
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


def _cell_area(grid: Grid) -> np.ndarray:
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    return dx[:, None] * dy[None, :]


def _active_payload(q_component: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    flat = np.asarray(q_component, dtype=float).ravel()
    ids = np.flatnonzero(flat != 0.0).astype(np.int64)
    return ids, flat[ids]


def _region_from_closed_gas_outside(
    gamma_state,
    q_g_phys: np.ndarray,
    *,
    mode: int,
) -> PhaseRegionBatch:
    component_to_batch = np.array((0,), dtype=np.int64)
    vertices = np.asarray(gamma_state.vertices, dtype=float)
    active_ids, active_weights = _active_payload(q_g_phys)
    coeffs = gamma_state.coefficient_map()
    atlas = InterfaceAtlas(
        batch_size=1,
        component_offsets=component_offsets_from_batch_ids(1, component_to_batch),
        component_to_batch=component_to_batch,
        chart_type=enum_values((ChartType.CLOSED_RADIAL,)),
        topology=enum_values((TopologyType.CLOSED,)),
        attachment=enum_values((BoundaryAttachment.NONE,)),
        orientation=np.array((-1.0,)),
        phase_role=enum_values((PhaseRole.GAS_OUTSIDE,)),
        constraint_policy=enum_values((ConstraintPolicy.TOTAL_VOLUME,)),
        dof_offsets=np.array((0, 4), dtype=np.int64),
        vertex_offsets=np.array((0, vertices.shape[0]), dtype=np.int64),
        active_cell_offsets=np.array((0, active_ids.size), dtype=np.int64),
    )
    dofs = np.asarray(
        (
            float(gamma_state.center[0]),
            float(gamma_state.center[1]),
            float(gamma_state.base_radius),
            float(coeffs[f"cos_{int(mode)}"]),
        ),
        dtype=float,
    )
    return PhaseRegionBatch(
        atlas=atlas,
        dofs=dofs,
        vertices=vertices,
        active_cell_ids=active_ids,
        active_weights=active_weights,
        metric_epoch=0,
    )


def _compute(
    config_path: pathlib.Path,
    *,
    theta_count: int,
    mode: int,
    capacity_tolerance: float,
    residual_volume_tolerance: float,
) -> dict[str, object]:
    cfg = ExperimentConfig.from_yaml(config_path)
    ellipse = _ellipse_from_config(cfg)
    grid, phase_state = _phase_state_on_admission_grid(cfg, ellipse)
    cell_area = _cell_area(grid)
    q_l_runtime = np.asarray(phase_state.q, dtype=float)
    owner_map = map_cell_measure_to_phase_owner(
        q_l_runtime,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        capacity_tolerance=float(capacity_tolerance),
    )
    liquid_projection = project_closed_radial_mode_f0(
        grid,
        q_l_runtime,
        center=ellipse.center,
        mode=int(mode),
        theta_count=int(theta_count),
        sigma=float(cfg.physics.sigma),
    )
    q_l_phys = np.asarray(liquid_projection.q_phys, dtype=float)
    q_g_phys = cell_area - q_l_phys
    region = _region_from_closed_gas_outside(
        liquid_projection.gamma_state,
        q_g_phys,
        mode=int(mode),
    )
    perimeter = closed_polygon_geometry(liquid_projection.gamma_state.vertices, sigma=1.0).length
    measurement = assemble_phase_region_measurement(
        region,
        q_g_phys[None, ...],
        np.array((float(perimeter),), dtype=float),
        q_target=owner_map.q_owner,
        cell_area=cell_area,
        capacity_tolerance=float(capacity_tolerance),
    )
    if measurement.residual is None:
        raise AssertionError("runtime dry-run residual was not assembled")
    if abs(float(measurement.residual_volume[0])) > float(residual_volume_tolerance):
        raise AssertionError("runtime dry-run residual volume exceeds tolerance")
    active_ids, active_weights = region.active_cells_for_component(0)
    if abs(float(np.sum(active_weights)) - float(measurement.component_volumes[0])) > 1.0e-12:
        raise AssertionError("active payload does not sum to component q")
    if int(region.atlas.phase_role[0]) != int(PhaseRole.GAS_OUTSIDE):
        raise AssertionError("runtime dry-run region must be GAS_OUTSIDE")
    if int(region.atlas.attachment[0]) != int(BoundaryAttachment.NONE):
        raise AssertionError("closed runtime dry-run component must have no attachment")

    residual_g = np.asarray(measurement.residual[0], dtype=float)
    residual_l = np.asarray(liquid_projection.residual, dtype=float)
    np.testing.assert_allclose(residual_g, -residual_l, atol=5.0e-14)
    dx_min = min(float(np.min(np.diff(np.asarray(coords)))) for coords in grid.coords)
    metrics = {
        "runtime_steps": 0.0,
        "source_phase": float(CellMeasurePhase.LIQUID),
        "owner_phase": float(CellMeasurePhase.GAS),
        "complement_used": float(owner_map.complement_used),
        "liquid_runtime_volume": float(owner_map.source_volume),
        "gas_target_volume": float(owner_map.owner_volume),
        "gas_physical_volume": float(measurement.batch_volumes[0]),
        "component_volume": float(measurement.component_volumes[0]),
        "component_perimeter": float(measurement.component_perimeters[0]),
        "batch_perimeter": float(measurement.batch_perimeters[0]),
        "residual_l2": float(measurement.residual_l2),
        "residual_linf": float(measurement.residual_linf),
        "residual_volume_abs": abs(float(measurement.residual_volume[0])),
        "liquid_projection_residual_l2": float(liquid_projection.residual_report.l2),
        "closed_mode_cos": float(liquid_projection.gamma_state.coefficient_map()[f"cos_{int(mode)}"]),
        "base_radius": float(liquid_projection.gamma_state.base_radius),
        "compat_linf": float(phase_state.compatibility_residual_linf),
        "q_min": float(measurement.q_min),
        "capacity_excess_linf": float(measurement.capacity_excess_linf),
        "grid_alpha": float(cfg.grid.alpha_grid),
        "min_dx": dx_min,
        "phase_role_gas_outside": float(region.atlas.phase_role[0]),
        "boundary_attachment_none": float(region.atlas.attachment[0]),
        "active_count": float(active_ids.size),
        "force_admissible": float(measurement.force_admissible),
    }
    return {
        "metrics": metrics,
        "fields": {
            "q_l_runtime": q_l_runtime,
            "q_g_target": np.asarray(owner_map.q_owner, dtype=float),
            "q_g_phys": q_g_phys,
            "residual_g": residual_g,
            "cell_area": cell_area,
            "phi": np.asarray(phase_state.phi, dtype=float),
            "x_edges": np.asarray(grid.coords[0], dtype=float),
            "y_edges": np.asarray(grid.coords[1], dtype=float),
            "gamma_vertices": np.asarray(liquid_projection.gamma_state.vertices, dtype=float),
        },
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    fields = results["fields"]
    metrics = results["metrics"]
    x_edges = np.asarray(fields["x_edges"], dtype=float)
    y_edges = np.asarray(fields["y_edges"], dtype=float)
    cell_area = np.asarray(fields["cell_area"], dtype=float)
    vertices = np.asarray(fields["gamma_vertices"], dtype=float)
    panels = (
        ("runtime q_l / |C|", np.asarray(fields["q_l_runtime"], dtype=float) / cell_area, "viridis"),
        ("owner q_g target / |C|", np.asarray(fields["q_g_target"], dtype=float) / cell_area, "viridis"),
        ("PhaseRegion q_g phys / |C|", np.asarray(fields["q_g_phys"], dtype=float) / cell_area, "viridis"),
        ("r_g / |C|", np.asarray(fields["residual_g"], dtype=float) / cell_area, "RdBu_r"),
    )
    fig, axes = plt.subplots(2, 3, figsize=(11.2, 7.0), constrained_layout=True)
    for ax, (title, field, cmap) in zip(axes.flat[:4], panels):
        if cmap == "RdBu_r":
            vmax = max(float(np.max(np.abs(field))), 1.0e-12)
            vmin = -vmax
        else:
            vmin, vmax = 0.0, 1.0
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
    axes.flat[4].axis("off")
    axes.flat[4].text(
        0.0,
        1.0,
        "\n".join(
            (
                "PhaseRegion runtime dry run",
                "source_phase = LIQUID",
                "owner_phase = GAS",
                f"complement_used = {int(metrics['complement_used'])}",
                f"gas_target_volume = {float(metrics['gas_target_volume']):.8e}",
                f"gas_physical_volume = {float(metrics['gas_physical_volume']):.8e}",
                f"residual_l2 = {float(metrics['residual_l2']):.8e}",
                f"residual_volume_abs = {float(metrics['residual_volume_abs']):.8e}",
                f"perimeter = {float(metrics['batch_perimeter']):.8e}",
                "force_admissible = 0",
            )
        ),
        va="top",
        ha="left",
        family="monospace",
        fontsize=8.0,
    )
    axes.flat[5].axis("off")
    save_figure(fig, OUT / "phase_region_runtime_dry_run_adapter")
    plt.close(fig)
    return (OUT / "phase_region_runtime_dry_run_adapter").with_suffix(".pdf")


def main() -> None:
    parser = experiment_argparser("Ch14 PhaseRegion runtime dry-run adapter")
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--theta-count", type=int, default=192)
    parser.add_argument("--mode", type=int, default=2)
    parser.add_argument("--capacity-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--residual-volume-tolerance", type=float, default=1.0e-5)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(
            pathlib.Path(args.config),
            theta_count=int(args.theta_count),
            mode=int(args.mode),
            capacity_tolerance=float(args.capacity_tolerance),
            residual_volume_tolerance=float(args.residual_volume_tolerance),
        )
        save_results(NPZ, results)
    pdf = _plot(results)
    metrics = results["metrics"]
    print(
        "PHASE_REGION_RUNTIME_DRY_RUN "
        f"complement_used={float(metrics['complement_used']):.1f} "
        f"gas_target_volume={float(metrics['gas_target_volume']):.12e} "
        f"gas_physical_volume={float(metrics['gas_physical_volume']):.12e} "
        f"residual_l2={float(metrics['residual_l2']):.12e} "
        f"residual_volume_abs={float(metrics['residual_volume_abs']):.12e} "
        f"perimeter={float(metrics['batch_perimeter']):.12e} "
        f"force_admissible={float(metrics['force_admissible']):.1f} "
        f"pdf={pdf}"
    )


if __name__ == "__main__":
    main()
