#!/usr/bin/env python3
"""PhaseRegion atlas smoke oracle for a closed bubble plus top air layer.

A3 mapping
----------
Equation:
    Own the gas region ``Omega_g = Omega_bubble union Omega_layer``.  The
    interface is ``Gamma = boundary Omega_g`` and the energy is
    ``E = sigma (L_bubble + L_layer)``.
Discretization:
    Store the region as one ``PhaseRegionBatch`` with a closed radial bubble
    component and a graph top-layer component.  The cell measure is assembled as
    ``q_phys = Q_h(component_bubble) + Q_h(component_layer)``.  A synthetic
    transported measure ``q_T`` is split as ``q_T = q_phys + r``.
Code:
    This is a no-runtime smoke oracle.  It does not build capillary force,
    pressure, velocity, nonlinear optimization, a runtime adapter, or T/8.
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from twophase.backend import Backend  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.geometry import (  # noqa: E402
    BoundaryAttachment,
    ChartType,
    ConstraintPolicy,
    InterfaceAtlas,
    PhaseRegionBatch,
    PhaseRole,
    TopologyType,
    closed_polygon_geometry,
    closed_radial_chart_from_modes,
    closed_radial_q_from_chart,
    component_offsets_from_batch_ids,
    enum_values,
    graph_q_from_eta,
    graph_segment_energy_gradient,
)
from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()

OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"


def _grid(n: int) -> Grid:
    backend = Backend(use_gpu=False)
    return Grid(GridConfig(ndim=2, N=(int(n), int(n)), L=(1.0, 1.0), alpha_grid=1.0), backend)


def _top_layer_eta(x_edges: np.ndarray, *, height: float, amplitude: float, mode: int) -> np.ndarray:
    eta = float(height) + float(amplitude) * np.cos(2.0 * np.pi * int(mode) * x_edges)
    eta[-1] = eta[0]
    return eta


def _cell_area(grid: Grid) -> np.ndarray:
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    return dx[:, None] * dy[None, :]


def _active_payload(q_component: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    flat = np.asarray(q_component, dtype=float).ravel()
    ids = np.flatnonzero(flat != 0.0).astype(np.int64)
    return ids, flat[ids]


def _zero_total_cell_residual(
    q_phys: np.ndarray,
    cell_area: np.ndarray,
    *,
    fraction: float,
) -> np.ndarray:
    theta = np.divide(q_phys, cell_area, out=np.zeros_like(q_phys), where=cell_area > 0.0)
    mask = (theta > 5.0e-2) & (theta < 1.0 - 5.0e-2)
    if np.count_nonzero(mask) < 4:
        raise AssertionError("not enough cut cells for synthetic residual")
    i, j = np.indices(q_phys.shape)
    pattern = mask * np.sin(0.37 * i + 0.61 * j) * np.cos(0.11 * i - 0.29 * j)
    pattern = pattern - mask * float(np.sum(pattern) / np.count_nonzero(mask))
    positive = pattern > 0.0
    negative = pattern < 0.0
    limits = []
    if np.any(positive):
        limits.append(np.min((cell_area - q_phys)[positive] / pattern[positive]))
    if np.any(negative):
        limits.append(np.min(q_phys[negative] / (-pattern[negative])))
    scale = float(fraction) * max(float(min(limits)), 0.0)
    residual = scale * pattern
    residual = residual - mask * float(np.sum(residual) / np.count_nonzero(mask))
    return residual


def _bubble_fd_residual(vertices: np.ndarray) -> float:
    theta = np.linspace(0.0, 2.0 * np.pi, vertices.shape[0], endpoint=False)
    direction = np.stack((np.cos(3.0 * theta), np.sin(5.0 * theta)), axis=-1)
    geometry = closed_polygon_geometry(vertices, sigma=1.0)
    eps = 1.0e-7
    plus = closed_polygon_geometry(vertices + eps * direction, sigma=1.0)
    minus = closed_polygon_geometry(vertices - eps * direction, sigma=1.0)
    fd_length = (float(plus.length) - float(minus.length)) / (2.0 * eps)
    grad_length = float(np.sum(np.asarray(geometry.surface_gradient) * direction))
    return abs(fd_length - grad_length)


def _graph_fd_residual(x_edges: np.ndarray, eta: np.ndarray) -> float:
    x_unique = x_edges[:-1]
    direction_unique = np.cos(4.0 * 2.0 * np.pi * x_unique)
    direction = np.r_[direction_unique, direction_unique[0]]
    energy = graph_segment_energy_gradient(x_edges, eta, sigma=1.0)
    eps = 1.0e-7
    plus = graph_segment_energy_gradient(x_edges, eta + eps * direction, sigma=1.0)
    minus = graph_segment_energy_gradient(x_edges, eta - eps * direction, sigma=1.0)
    fd_length = (float(plus.energy) - float(minus.energy)) / (2.0 * eps)
    grad_length = float(np.sum(np.asarray(energy.nodal_gradient) * direction_unique))
    return abs(fd_length - grad_length)


def _build_region(
    *,
    bubble_state,
    eta_layer: np.ndarray,
    q_bubble: np.ndarray,
    q_layer: np.ndarray,
) -> PhaseRegionBatch:
    component_to_batch = np.array((0, 0), dtype=np.int64)
    bubble_vertices = np.asarray(bubble_state.vertices, dtype=float)
    x_edges = np.linspace(0.0, 1.0, eta_layer.shape[0])
    layer_vertices = np.stack((x_edges, eta_layer), axis=-1)
    bubble_active_ids, bubble_active_weights = _active_payload(q_bubble)
    layer_active_ids, layer_active_weights = _active_payload(q_layer)
    atlas = InterfaceAtlas(
        batch_size=1,
        component_offsets=component_offsets_from_batch_ids(1, component_to_batch),
        component_to_batch=component_to_batch,
        chart_type=enum_values((ChartType.CLOSED_RADIAL, ChartType.GRAPH)),
        topology=enum_values((TopologyType.CLOSED, TopologyType.GRAPH_PERIODIC)),
        attachment=enum_values((BoundaryAttachment.NONE, BoundaryAttachment.TOP)),
        orientation=np.array((1.0, -1.0)),
        phase_role=enum_values((PhaseRole.GAS_INSIDE, PhaseRole.GAS_ABOVE)),
        constraint_policy=enum_values(
            (ConstraintPolicy.COMPONENT_VOLUME, ConstraintPolicy.TOTAL_VOLUME)
        ),
        dof_offsets=np.array((0, 4, 4 + eta_layer.size), dtype=np.int64),
        vertex_offsets=np.array(
            (0, bubble_vertices.shape[0], bubble_vertices.shape[0] + layer_vertices.shape[0]),
            dtype=np.int64,
        ),
        active_cell_offsets=np.array(
            (0, bubble_active_ids.size, bubble_active_ids.size + layer_active_ids.size),
            dtype=np.int64,
        ),
    )
    dofs = np.concatenate(
        (
            np.asarray(
                (
                    float(bubble_state.center[0]),
                    float(bubble_state.center[1]),
                    float(bubble_state.base_radius),
                    float(bubble_state.modes[0].cos),
                )
            ),
            eta_layer,
        )
    )
    return PhaseRegionBatch(
        atlas=atlas,
        dofs=dofs,
        vertices=np.vstack((bubble_vertices, layer_vertices)),
        active_cell_ids=np.concatenate((bubble_active_ids, layer_active_ids)),
        active_weights=np.concatenate((bubble_active_weights, layer_active_weights)),
        metric_epoch=0,
    )


def _compute(args) -> dict[str, object]:
    grid = _grid(int(args.n))
    x_edges = np.asarray(grid.coords[0], dtype=float)
    cell_area = _cell_area(grid)
    theta = np.linspace(0.0, 2.0 * np.pi, int(args.theta_count), endpoint=False)
    bubble = closed_radial_chart_from_modes(
        theta,
        center=(0.5, 0.38),
        base_radius=float(args.bubble_radius),
        modes=((2, float(args.bubble_amplitude)),),
    )
    eta_layer = _top_layer_eta(
        x_edges,
        height=float(args.layer_height),
        amplitude=float(args.layer_amplitude),
        mode=int(args.layer_mode),
    )
    q_bubble = np.asarray(closed_radial_q_from_chart(grid, bubble).q, dtype=float)
    q_below_layer = np.asarray(graph_q_from_eta(grid, eta_layer).q, dtype=float)
    q_layer = cell_area - q_below_layer
    q_phys = q_bubble + q_layer
    if float(np.max(q_phys - cell_area)) > float(args.bound_tolerance):
        raise AssertionError("bubble and top layer overlap in cell measure")
    residual = _zero_total_cell_residual(
        q_phys,
        cell_area,
        fraction=float(args.residual_fraction),
    )
    q_target = q_phys + residual
    if float(np.min(q_target)) < -float(args.bound_tolerance):
        raise AssertionError("synthetic q_T became negative")
    if float(np.max(q_target - cell_area)) > float(args.bound_tolerance):
        raise AssertionError("synthetic q_T exceeded cell capacity")

    region = _build_region(
        bubble_state=bubble,
        eta_layer=eta_layer,
        q_bubble=q_bubble,
        q_layer=q_layer,
    )
    bubble_geo = closed_polygon_geometry(bubble.vertices, sigma=float(args.sigma))
    layer_energy = graph_segment_energy_gradient(x_edges, eta_layer, sigma=float(args.sigma))
    bubble_fd = _bubble_fd_residual(np.asarray(bubble.vertices, dtype=float))
    layer_fd = _graph_fd_residual(x_edges, eta_layer)
    active_bubble_ids, active_bubble_weights = region.active_cells_for_component(0)
    active_layer_ids, active_layer_weights = region.active_cells_for_component(1)
    bubble_volume = float(np.sum(q_bubble))
    layer_volume = float(np.sum(q_layer))
    total_volume = float(np.sum(q_phys))
    if abs(float(np.sum(active_bubble_weights)) - bubble_volume) > 1.0e-14:
        raise AssertionError("bubble active payload does not sum to component q")
    if abs(float(np.sum(active_layer_weights)) - layer_volume) > 1.0e-14:
        raise AssertionError("layer active payload does not sum to component q")
    if float(bubble_fd) > float(args.fd_tolerance):
        raise AssertionError("bubble perimeter covector failed finite-difference check")
    if float(layer_fd) > float(args.fd_tolerance):
        raise AssertionError("layer perimeter covector failed finite-difference check")
    if abs(float(np.sum(residual))) > float(args.volume_tolerance):
        raise AssertionError("synthetic residual is not total-volume neutral")

    return {
        "x_edges": x_edges,
        "y_edges": np.asarray(grid.coords[1], dtype=float),
        "cell_area": cell_area,
        "q_bubble": q_bubble,
        "q_layer": q_layer,
        "q_phys": q_phys,
        "q_target": q_target,
        "residual": residual,
        "bubble_vertices": np.asarray(bubble.vertices, dtype=float),
        "layer_vertices": np.stack((x_edges, eta_layer), axis=-1),
        "component_counts": region.atlas.component_counts_by_batch(),
        "graph_components": region.atlas.component_indices_for_chart(ChartType.GRAPH),
        "bubble_active_count": int(active_bubble_ids.size),
        "layer_active_count": int(active_layer_ids.size),
        "bubble_volume": bubble_volume,
        "layer_volume": layer_volume,
        "total_volume": total_volume,
        "target_volume": float(np.sum(q_target)),
        "residual_volume_abs": abs(float(np.sum(residual))),
        "residual_l2": float(np.sqrt(np.sum(residual * residual))),
        "bubble_length": float(bubble_geo.length),
        "layer_length": float(layer_energy.energy) / float(args.sigma),
        "total_perimeter": float(bubble_geo.length) + float(layer_energy.energy) / float(args.sigma),
        "bubble_fd_residual": bubble_fd,
        "layer_fd_residual": layer_fd,
        "force_admissible": 0.0,
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    cell_area = np.asarray(results["cell_area"], dtype=float)
    bubble_vertices = np.asarray(results["bubble_vertices"], dtype=float)
    layer_vertices = np.asarray(results["layer_vertices"], dtype=float)
    panels = (
        ("bubble component", np.asarray(results["q_bubble"], dtype=float) / cell_area, "viridis"),
        ("top layer component", np.asarray(results["q_layer"], dtype=float) / cell_area, "viridis"),
        ("q_phys", np.asarray(results["q_phys"], dtype=float) / cell_area, "viridis"),
        ("q_T synthetic", np.asarray(results["q_target"], dtype=float) / cell_area, "viridis"),
        ("r / cell area", np.asarray(results["residual"], dtype=float) / cell_area, "RdBu_r"),
    )
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 6.9), constrained_layout=True)
    for ax, (title, field, cmap) in zip(axes.flat, panels):
        vmax_abs = max(float(np.max(np.abs(field))), 1.0e-12)
        if cmap == "RdBu_r":
            vmin, vmax = -vmax_abs, vmax_abs
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
        ax.plot(
            np.r_[bubble_vertices[:, 0], bubble_vertices[0, 0]],
            np.r_[bubble_vertices[:, 1], bubble_vertices[0, 1]],
            color="black",
            linewidth=1.0,
        )
        ax.plot(layer_vertices[:, 0], layer_vertices[:, 1], color="black", linewidth=1.0)
        ax.set_title(title)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        fig.colorbar(mesh, ax=ax)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0.0,
        1.0,
        "\n".join(
            (
                "PhaseRegion atlas smoke oracle",
                f"bubble volume = {float(results['bubble_volume']):.8e}",
                f"layer volume = {float(results['layer_volume']):.8e}",
                f"total perimeter = {float(results['total_perimeter']):.8e}",
                f"residual L2 = {float(results['residual_l2']):.8e}",
                "force_admissible = 0",
            )
        ),
        va="top",
        family="monospace",
    )
    save_figure(fig, OUT / "phase_region_atlas_smoke_oracle")
    return (OUT / "phase_region_atlas_smoke_oracle").with_suffix(".pdf")


def _print_summary(results: dict[str, object], figure_path: pathlib.Path) -> None:
    print("metric,value")
    for key in (
        "bubble_volume",
        "layer_volume",
        "total_volume",
        "target_volume",
        "residual_volume_abs",
        "residual_l2",
        "bubble_length",
        "layer_length",
        "total_perimeter",
        "bubble_fd_residual",
        "layer_fd_residual",
        "force_admissible",
    ):
        print(key, f"{float(results[key]):.12e}", sep=",")
    print("component_counts", np.asarray(results["component_counts"]).tolist(), sep=",")
    print("graph_components", np.asarray(results["graph_components"]).tolist(), sep=",")
    print(f"figure,{figure_path}")
    print(f"==> phase-region atlas smoke oracle PASS; outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument("--n", type=int, default=96)
    parser.add_argument("--theta-count", type=int, default=192)
    parser.add_argument("--bubble-radius", type=float, default=0.12)
    parser.add_argument("--bubble-amplitude", type=float, default=9.0e-3)
    parser.add_argument("--layer-height", type=float, default=0.78)
    parser.add_argument("--layer-amplitude", type=float, default=2.0e-2)
    parser.add_argument("--layer-mode", type=int, default=2)
    parser.add_argument("--residual-fraction", type=float, default=3.0e-2)
    parser.add_argument("--sigma", type=float, default=1.0)
    parser.add_argument("--bound-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--volume-tolerance", type=float, default=1.0e-14)
    parser.add_argument("--fd-tolerance", type=float, default=1.0e-7)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(args)
        save_results(NPZ, results)
    figure_path = _plot(results)
    _print_summary(results, figure_path)


if __name__ == "__main__":
    main()
