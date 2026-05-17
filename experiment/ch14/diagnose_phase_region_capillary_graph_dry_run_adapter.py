#!/usr/bin/env python3
"""PhaseRegion graph dry-run adapter for the Ch14 capillary-wave input.

A3 mapping
----------
Equation:
    Runtime capillary-wave data declares a liquid region below a periodic graph
    ``Gamma_h = {(x, eta(x))}``.  The PhaseRegion theory owns the gas phase
    ``Omega_g = {y > eta(x)}``, so ``q_g = |C| - q_l`` and
    ``E_h[Omega_g] = sigma * Perimeter(Gamma_h)``.
Discretization:
    Read the canonical Ch14 capillary-wave YAML, build its fitted diagnostic
    grid, compare the runtime ``phi`` cell measure to ``Q_h(eta)``, then store
    a single ``GAS_ABOVE`` graph component in ``PhaseRegionBatch`` and assemble
    the gas residual with ``assemble_phase_region_measurement``.
Code:
    This is a diagnostic dry run only.  It does not advance a solver step,
    assemble a face cochain, project pressure/velocity, run a nonlinear
    optimizer, or provide a hidden CPU fallback for GPU runtime execution.
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
    component_offsets_from_batch_ids,
    enum_values,
    graph_q_from_eta,
    graph_segment_energy_gradient,
    map_cell_measure_to_phase_owner,
)
from twophase.geometry.phase_state import GeometricPhaseState  # noqa: E402
from twophase.levelset.heaviside import heaviside  # noqa: E402
from twophase.simulation.config_loader import require_pyyaml  # noqa: E402
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

CONFIG = ROOT / "experiment/ch14/config/ch14_capillary.yaml"
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"


@dataclass(frozen=True)
class CapillaryWaveSpec:
    """Periodic capillary-wave graph declared by the Ch14 YAML."""

    mean: float
    amplitude: float
    mode: int
    length: float
    phase: float


def _wave_from_config(cfg: ExperimentConfig) -> CapillaryWaveSpec:
    objects = tuple(cfg.initial_condition.get("objects", ()))
    if len(objects) != 1 or objects[0].get("type") != "capillary_wave":
        raise ValueError("capillary graph dry-run expects one capillary_wave object")
    obj = objects[0]
    if obj.get("axis") != "y":
        raise ValueError("capillary graph dry-run expects a y-axis graph")
    if obj.get("interior_phase") != "liquid":
        raise ValueError("capillary graph dry-run expects liquid below the graph")
    return CapillaryWaveSpec(
        mean=float(obj["mean"]),
        amplitude=float(obj["amplitude"]),
        mode=int(obj["mode"]),
        length=float(obj["length"]),
        phase=float(obj.get("phase", 0.0)),
    )


def _load_phase_region_graph_config(config_path: pathlib.Path) -> ExperimentConfig:
    """Load the canonical PhaseRegion wrapper or its legacy base config."""
    yaml = require_pyyaml()
    with pathlib.Path(config_path).open() as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError("PhaseRegion graph config must be a YAML mapping")
    if "base_config" not in raw:
        return ExperimentConfig.from_yaml(config_path)
    base_path = pathlib.Path(str(raw["base_config"]))
    if not base_path.is_absolute():
        base_path = pathlib.Path(config_path).parent / base_path
    return ExperimentConfig.from_yaml(base_path)


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


def _eta(x_edges: np.ndarray, spec: CapillaryWaveSpec) -> np.ndarray:
    eta = float(spec.mean) + float(spec.amplitude) * np.cos(
        2.0 * np.pi * int(spec.mode) * x_edges / float(spec.length) + float(spec.phase)
    )
    eta[-1] = eta[0]
    return eta


def _phi_for_eta(grid: Grid, eta_nodes: np.ndarray) -> np.ndarray:
    _x, y = np.meshgrid(
        np.asarray(grid.coords[0], dtype=float),
        np.asarray(grid.coords[1], dtype=float),
        indexing="ij",
    )
    return y - np.asarray(eta_nodes, dtype=float).reshape((-1, 1))


def _phase_state_on_capillary_grid(cfg: ExperimentConfig, spec: CapillaryWaveSpec):
    grid = _grid_from_config(cfg)
    eps = float(cfg.grid.eps_factor) * (float(cfg.grid.LX) / float(cfg.grid.NX))
    if float(cfg.grid.alpha_grid) > 1.0:
        eta_uniform = _eta(np.asarray(grid.coords[0], dtype=float), spec)
        phi_uniform = _phi_for_eta(grid, eta_uniform)
        psi_uniform = heaviside(np, -phi_uniform, eps)
        ccd = CCDSolver(grid, grid.backend, bc_type=cfg.grid.bc_type)
        grid.update_from_levelset(psi_uniform, eps, ccd=ccd)
    eta_nodes = _eta(np.asarray(grid.coords[0], dtype=float), spec)
    phi = _phi_for_eta(grid, eta_nodes)
    return grid, eta_nodes, GeometricPhaseState.from_phi(grid, phi)


def _cell_area(grid: Grid) -> np.ndarray:
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    return dx[:, None] * dy[None, :]


def _active_payload(q_component: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    flat = np.asarray(q_component, dtype=float).ravel()
    ids = np.flatnonzero(flat != 0.0).astype(np.int64)
    return ids, flat[ids]


def _region_from_graph_gas_above(
    *,
    x_edges: np.ndarray,
    eta_nodes: np.ndarray,
    q_g_phys: np.ndarray,
) -> PhaseRegionBatch:
    component_to_batch = np.array((0,), dtype=np.int64)
    vertices = np.stack((x_edges, eta_nodes), axis=-1)
    active_ids, active_weights = _active_payload(q_g_phys)
    atlas = InterfaceAtlas(
        batch_size=1,
        component_offsets=component_offsets_from_batch_ids(1, component_to_batch),
        component_to_batch=component_to_batch,
        chart_type=enum_values((ChartType.GRAPH,)),
        topology=enum_values((TopologyType.GRAPH_PERIODIC,)),
        attachment=enum_values((BoundaryAttachment.TOP,)),
        orientation=np.array((-1.0,)),
        phase_role=enum_values((PhaseRole.GAS_ABOVE,)),
        constraint_policy=enum_values((ConstraintPolicy.TOTAL_VOLUME,)),
        dof_offsets=np.array((0, eta_nodes.size), dtype=np.int64),
        vertex_offsets=np.array((0, vertices.shape[0]), dtype=np.int64),
        active_cell_offsets=np.array((0, active_ids.size), dtype=np.int64),
    )
    return PhaseRegionBatch(
        atlas=atlas,
        dofs=np.asarray(eta_nodes, dtype=float),
        vertices=vertices,
        active_cell_ids=active_ids,
        active_weights=active_weights,
        metric_epoch=0,
    )


def _weighted_projection(values: np.ndarray, basis: np.ndarray, weights: np.ndarray) -> float:
    denom = float(np.sum(weights * basis * basis))
    if denom <= 0.0:
        return 0.0
    return float(np.sum(weights * values * basis) / denom)


def _graph_variation_checks(
    x_edges: np.ndarray,
    eta_nodes: np.ndarray,
    spec: CapillaryWaveSpec,
    *,
    sigma: float,
    finite_difference_step: float,
) -> dict[str, float]:
    energy = graph_segment_energy_gradient(x_edges, eta_nodes, sigma=float(sigma))
    x_unique = np.asarray(x_edges, dtype=float)[:-1]
    weights = np.asarray(energy.weights, dtype=float)
    nodal_gradient = np.asarray(energy.nodal_gradient, dtype=float)
    mode_unique = np.cos(
        2.0 * np.pi * int(spec.mode) * x_unique / float(spec.length) + float(spec.phase)
    )
    mode_nodes = np.r_[mode_unique, mode_unique[0]]
    force_density = -nodal_gradient / weights
    eta_mode = _weighted_projection(eta_nodes[:-1] - float(spec.mean), mode_unique, weights)
    force_mode = _weighted_projection(force_density, mode_unique, weights)
    step = float(finite_difference_step)
    plus = graph_segment_energy_gradient(x_edges, eta_nodes + step * mode_nodes, sigma=float(sigma))
    minus = graph_segment_energy_gradient(x_edges, eta_nodes - step * mode_nodes, sigma=float(sigma))
    fd_rate = (float(plus.energy) - float(minus.energy)) / (2.0 * step)
    exact_rate = float(np.sum(nodal_gradient * mode_unique))

    zero_eta = np.full_like(eta_nodes, float(spec.mean), dtype=float)
    sweep_amplitudes = np.asarray(
        (0.0, 0.5 * float(spec.amplitude), float(spec.amplitude), 1.5 * float(spec.amplitude)),
        dtype=float,
    )
    sweep_energy = []
    for amplitude in sweep_amplitudes:
        eta_sweep = float(spec.mean) + float(amplitude) * np.cos(
            2.0 * np.pi * int(spec.mode) * x_edges / float(spec.length) + float(spec.phase)
        )
        eta_sweep[-1] = eta_sweep[0]
        sweep_energy.append(float(graph_segment_energy_gradient(x_edges, eta_sweep, sigma=float(sigma)).energy))
    energy_zero = float(graph_segment_energy_gradient(x_edges, zero_eta, sigma=float(sigma)).energy)
    return {
        "surface_energy": float(energy.energy),
        "perimeter": float(energy.energy) / float(sigma),
        "eta_mode": float(eta_mode),
        "force_mode": float(force_mode),
        "force_sign_product": float(eta_mode * force_mode),
        "dE_dmode_fd": float(fd_rate),
        "dE_dmode_exact": float(exact_rate),
        "dE_dmode_abs_error": abs(float(fd_rate) - float(exact_rate)),
        "energy_zero": float(energy_zero),
        "energy_increment": float(energy.energy) - float(energy_zero),
        "sweep_energy_min_increment": float(np.min(np.diff(np.asarray(sweep_energy)))),
    }


def _compute(
    config_path: pathlib.Path,
    *,
    q_match_tolerance: float,
    residual_volume_tolerance: float,
    variation_tolerance: float,
    finite_difference_step: float,
) -> dict[str, object]:
    cfg = _load_phase_region_graph_config(config_path)
    spec = _wave_from_config(cfg)
    grid, eta_nodes, phase_state = _phase_state_on_capillary_grid(cfg, spec)
    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    cell_area = _cell_area(grid)
    q_l_runtime = np.asarray(phase_state.q, dtype=float)
    q_l_graph = np.asarray(graph_q_from_eta(grid, eta_nodes).q, dtype=float)
    runtime_graph_q_linf = float(np.max(np.abs(q_l_runtime - q_l_graph)))
    if runtime_graph_q_linf > float(q_match_tolerance):
        raise AssertionError("runtime phi cell measure disagrees with graph Q_h")

    owner_map = map_cell_measure_to_phase_owner(
        q_l_runtime,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
    )
    q_g_phys = cell_area - q_l_graph
    region = _region_from_graph_gas_above(
        x_edges=x_edges,
        eta_nodes=eta_nodes,
        q_g_phys=q_g_phys,
    )
    variation = _graph_variation_checks(
        x_edges,
        eta_nodes,
        spec,
        sigma=float(cfg.physics.sigma),
        finite_difference_step=float(finite_difference_step),
    )
    measurement = assemble_phase_region_measurement(
        region,
        q_g_phys[None, ...],
        np.array((variation["perimeter"],), dtype=float),
        q_target=owner_map.q_owner,
        cell_area=cell_area,
    )
    if measurement.residual is None:
        raise AssertionError("capillary graph dry-run residual was not assembled")
    if abs(float(measurement.residual_volume[0])) > float(residual_volume_tolerance):
        raise AssertionError("capillary graph residual volume exceeds tolerance")
    if variation["dE_dmode_abs_error"] > float(variation_tolerance):
        raise AssertionError("graph energy covector failed finite-difference check")
    if variation["force_sign_product"] >= 0.0:
        raise AssertionError("graph restoring force does not oppose the capillary-wave mode")
    if variation["energy_increment"] <= 0.0:
        raise AssertionError("capillary graph energy did not increase over the flat interface")
    if variation["sweep_energy_min_increment"] < -float(variation_tolerance):
        raise AssertionError("capillary graph energy sweep is not monotone")

    dx = np.diff(x_edges)
    eta_center = 0.5 * (eta_nodes[:-1] + eta_nodes[1:])
    column_height = np.sum(q_l_graph, axis=1) / dx
    exact_liquid_volume = float(np.sum(dx * eta_center))
    active_ids, active_weights = region.active_cells_for_component(0)
    metrics = {
        "runtime_steps": 0.0,
        "source_phase": float(CellMeasurePhase.LIQUID),
        "owner_phase": float(CellMeasurePhase.GAS),
        "complement_used": float(owner_map.complement_used),
        "liquid_runtime_volume": float(owner_map.source_volume),
        "liquid_graph_volume": float(np.sum(q_l_graph)),
        "exact_liquid_volume": exact_liquid_volume,
        "gas_target_volume": float(owner_map.owner_volume),
        "gas_physical_volume": float(measurement.batch_volumes[0]),
        "component_volume": float(measurement.component_volumes[0]),
        "component_perimeter": float(measurement.component_perimeters[0]),
        "batch_perimeter": float(measurement.batch_perimeters[0]),
        "residual_l2": float(measurement.residual_l2),
        "residual_linf": float(measurement.residual_linf),
        "residual_volume_abs": abs(float(measurement.residual_volume[0])),
        "runtime_graph_q_linf": runtime_graph_q_linf,
        "column_height_linf": float(np.max(np.abs(column_height - eta_center))),
        "liquid_exact_volume_abs": abs(float(np.sum(q_l_graph)) - exact_liquid_volume),
        "compat_linf": float(phase_state.compatibility_residual_linf),
        "q_min": float(measurement.q_min),
        "capacity_excess_linf": float(measurement.capacity_excess_linf),
        "grid_alpha": float(cfg.grid.alpha_grid),
        "min_dx": float(np.min(dx)),
        "min_dy": float(np.min(np.diff(y_edges))),
        "phase_role_gas_above": float(region.atlas.phase_role[0]),
        "boundary_attachment_top": float(region.atlas.attachment[0]),
        "active_count": float(active_ids.size),
        "active_weight_volume_abs": abs(float(np.sum(active_weights)) - float(measurement.component_volumes[0])),
        "phase_region_graph_admitted": 1.0,
        "force_admissible": float(measurement.force_admissible),
    }
    metrics.update(variation)
    return {
        "metrics": metrics,
        "fields": {
            "q_l_runtime": q_l_runtime,
            "q_l_graph": q_l_graph,
            "q_g_target": np.asarray(owner_map.q_owner, dtype=float),
            "q_g_phys": q_g_phys,
            "residual_g": np.asarray(measurement.residual[0], dtype=float),
            "cell_area": cell_area,
            "phi": np.asarray(phase_state.phi, dtype=float),
            "x_edges": x_edges,
            "y_edges": y_edges,
            "eta_nodes": eta_nodes,
            "eta_center": eta_center,
            "column_height": column_height,
        },
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    fields = results["fields"]
    metrics = results["metrics"]
    x_edges = np.asarray(fields["x_edges"], dtype=float)
    y_edges = np.asarray(fields["y_edges"], dtype=float)
    eta_nodes = np.asarray(fields["eta_nodes"], dtype=float)
    cell_area = np.asarray(fields["cell_area"], dtype=float)
    panels = (
        ("runtime q_l / |C|", np.asarray(fields["q_l_runtime"], dtype=float) / cell_area, "viridis"),
        ("owner q_g target / |C|", np.asarray(fields["q_g_target"], dtype=float) / cell_area, "viridis"),
        ("PhaseRegion q_g phys / |C|", np.asarray(fields["q_g_phys"], dtype=float) / cell_area, "viridis"),
        ("r_g / |C|", np.asarray(fields["residual_g"], dtype=float) / cell_area, "RdBu_r"),
    )
    fig, axes = plt.subplots(2, 3, figsize=(11.4, 7.0), constrained_layout=True)
    for ax, (title, field, cmap) in zip(axes.flat[:4], panels):
        if cmap == "RdBu_r":
            vmax = max(float(np.max(np.abs(field))), 1.0e-30)
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
        ax.plot(eta_nodes * 0.0 + x_edges, eta_nodes, color="white", lw=1.3)
        ax.plot(x_edges, eta_nodes, color="black", lw=0.5)
        ax.set_title(title)
        ax.set_aspect("equal")
        fig.colorbar(mesh, ax=ax, shrink=0.82)

    axes.flat[4].plot(
        x_edges[:-1],
        np.asarray(fields["column_height"], dtype=float),
        color="#34656d",
        label="Q_h column height",
    )
    axes.flat[4].plot(
        x_edges[:-1],
        np.asarray(fields["eta_center"], dtype=float),
        color="black",
        linestyle=":",
        label="P1 graph segment height",
    )
    axes.flat[4].set_title("graph measure exactness")
    axes.flat[4].legend(loc="best")

    axes.flat[5].axis("off")
    axes.flat[5].text(
        0.0,
        1.0,
        "\n".join(
            (
                "PhaseRegion capillary graph dry run",
                "source_phase = LIQUID",
                "owner_phase = GAS_ABOVE",
                f"runtime_graph_q_linf = {float(metrics['runtime_graph_q_linf']):.8e}",
                f"column_height_linf = {float(metrics['column_height_linf']):.8e}",
                f"residual_l2 = {float(metrics['residual_l2']):.8e}",
                f"dE fd error = {float(metrics['dE_dmode_abs_error']):.8e}",
                f"force_mode = {float(metrics['force_mode']):.8e}",
                f"perimeter = {float(metrics['batch_perimeter']):.8e}",
                "phase_region_graph_admitted = 1",
                "force_admissible = 0",
            )
        ),
        va="top",
        ha="left",
        family="monospace",
        fontsize=8.0,
    )
    save_figure(fig, OUT / "phase_region_capillary_graph_dry_run_adapter")
    plt.close(fig)
    return (OUT / "phase_region_capillary_graph_dry_run_adapter").with_suffix(".pdf")


def main() -> None:
    parser = experiment_argparser("Ch14 PhaseRegion capillary graph dry-run adapter")
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--q-match-tolerance", type=float, default=1.0e-16)
    parser.add_argument("--residual-volume-tolerance", type=float, default=1.0e-16)
    parser.add_argument("--variation-tolerance", type=float, default=1.0e-10)
    parser.add_argument("--finite-difference-step", type=float, default=1.0e-8)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(
            pathlib.Path(args.config),
            q_match_tolerance=float(args.q_match_tolerance),
            residual_volume_tolerance=float(args.residual_volume_tolerance),
            variation_tolerance=float(args.variation_tolerance),
            finite_difference_step=float(args.finite_difference_step),
        )
        save_results(NPZ, results)
    pdf = _plot(results)
    metrics = results["metrics"]
    print(
        "PHASE_REGION_CAPILLARY_GRAPH_DRY_RUN "
        f"phase_region_graph_admitted={float(metrics['phase_region_graph_admitted']):.1f} "
        f"complement_used={float(metrics['complement_used']):.1f} "
        f"gas_target_volume={float(metrics['gas_target_volume']):.12e} "
        f"gas_physical_volume={float(metrics['gas_physical_volume']):.12e} "
        f"residual_l2={float(metrics['residual_l2']):.12e} "
        f"runtime_graph_q_linf={float(metrics['runtime_graph_q_linf']):.12e} "
        f"column_height_linf={float(metrics['column_height_linf']):.12e} "
        f"dE_dmode_abs_error={float(metrics['dE_dmode_abs_error']):.12e} "
        f"force_sign_product={float(metrics['force_sign_product']):.12e} "
        f"perimeter={float(metrics['batch_perimeter']):.12e} "
        f"force_admissible={float(metrics['force_admissible']):.1f} "
        f"pdf={pdf}"
    )


if __name__ == "__main__":
    main()
