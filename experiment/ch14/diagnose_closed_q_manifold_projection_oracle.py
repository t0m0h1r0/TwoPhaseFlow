#!/usr/bin/env python3
"""Closed radial q-to-interface-manifold projection oracle.

A3 mapping
----------
Equation:
    Use the same ``q_T=Q_h(Gamma*)+r`` split as the graph oracle, but with a
    closed radial chart ``Gamma_h=X(theta)``.
Discretization:
    Use a star-shaped mode-2 radial chart, polygonal surface energy/area
    covectors, and a CPU P1 finite-volume ``Q_h`` measurement from the radial
    gauge.  High cell-scale residuals are diagnostic and do not alter the
    admitted closed mode.
Code:
    This is an experiment oracle only.  It does not connect Ch14 runtime,
    pressure, velocity, nonlinear optimization, or T/8.
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
from twophase.geometry.interface_charts import (  # noqa: E402
    closed_polygon_geometry,
    closed_radial_chart_from_modes,
)
from twophase.geometry.q_manifold_projection import (  # noqa: E402
    closed_mode_restoring_action,
    closed_radial_q_from_chart,
    project_closed_radial_mode_f0,
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


def _closed_high_residual(grid: Grid, q: np.ndarray, *, mode: int, fraction: float) -> np.ndarray:
    q_arr = np.asarray(q, dtype=float)
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    cell_area = dx[:, None] * dy[None, :]
    theta = np.divide(q_arr, cell_area, out=np.zeros_like(q_arr), where=cell_area > 0.0)
    mask = (theta > 1.0e-3) & (theta < 1.0 - 1.0e-3)
    x_center = 0.5 * (np.asarray(grid.coords[0])[:-1] + np.asarray(grid.coords[0])[1:])
    y_center = 0.5 * (np.asarray(grid.coords[1])[:-1] + np.asarray(grid.coords[1])[1:])
    x, y = np.meshgrid(x_center, y_center, indexing="ij")
    angle = np.mod(np.arctan2(y - 0.5, x - 0.5), 2.0 * np.pi)
    pattern = mask * np.sin(7.0 * angle + 0.3 * np.cos(5.0 * angle))
    basis = np.stack((mask.astype(float), mask * np.cos(int(mode) * angle)), axis=-1)
    gram = np.einsum("ija,ijb->ab", basis, basis)
    rhs = np.einsum("ija,ij->a", basis, pattern)
    coeff = np.linalg.solve(gram, rhs)
    residual = pattern - np.einsum("ija,a->ij", basis, coeff)
    positive = residual > 0.0
    negative = residual < 0.0
    limits = []
    if np.any(positive):
        limits.append(np.min((cell_area - q_arr)[positive] / residual[positive]))
    if np.any(negative):
        limits.append(np.min(q_arr[negative] / (-residual[negative])))
    scale = float(fraction) * max(min(limits), 0.0)
    return q_arr + scale * residual


def _gradient_fd_residual(vertices: np.ndarray) -> tuple[float, float]:
    theta = np.linspace(0.0, 2.0 * np.pi, vertices.shape[0], endpoint=False)
    direction = np.stack((np.cos(3.0 * theta), np.sin(5.0 * theta)), axis=-1)
    geometry = closed_polygon_geometry(vertices, sigma=1.0)
    eps = 1.0e-7
    plus = closed_polygon_geometry(vertices + eps * direction, sigma=1.0)
    minus = closed_polygon_geometry(vertices - eps * direction, sigma=1.0)
    fd_length = (float(plus.length) - float(minus.length)) / (2.0 * eps)
    fd_area = (float(plus.area) - float(minus.area)) / (2.0 * eps)
    grad_length = float(np.sum(np.asarray(geometry.surface_gradient) * direction))
    grad_area = float(np.sum(np.asarray(geometry.area_gradient) * direction))
    return abs(fd_length - grad_length), abs(fd_area - grad_area)


def _case_metrics(grid: Grid, *, name: str, q_target: np.ndarray, args) -> dict[str, object]:
    projection = project_closed_radial_mode_f0(
        grid,
        q_target,
        center=(0.5, 0.5),
        mode=int(args.mode),
        theta_count=int(args.theta_count),
        sigma=float(args.sigma),
    )
    state = projection.gamma_state
    length_fd, area_fd = _gradient_fd_residual(np.asarray(state.vertices, dtype=float))
    restoring_action = closed_mode_restoring_action(
        projection.energy_report,
        state.vertices,
        state.theta,
        mode=int(args.mode),
    )
    return {
        "name": name,
        "q_target": q_target,
        "q_phys": projection.q_phys,
        "residual": projection.residual,
        "vertices": np.asarray(state.vertices, dtype=float),
        "coeff_cos": float(state.coefficient_map()[f"cos_{int(args.mode)}"]),
        "polygon_area": float(projection.energy_report["polygon_area"]),
        "q_area": float(np.sum(projection.q_phys)),
        "residual_l2": projection.residual_report.l2,
        "residual_area_abs": projection.residual_report.total_volume_abs,
        "restoring_action": restoring_action,
        "length_fd_residual": length_fd,
        "area_fd_residual": area_fd,
    }


def _compute(args) -> dict[str, object]:
    grid = _grid(int(args.n))
    theta = np.linspace(0.0, 2.0 * np.pi, int(args.theta_count), endpoint=False)
    circle = closed_radial_chart_from_modes(
        theta,
        center=(0.5, 0.5),
        base_radius=float(args.radius),
        modes=(),
    )
    mode2 = closed_radial_chart_from_modes(
        theta,
        center=(0.5, 0.5),
        base_radius=float(args.radius),
        modes=((int(args.mode), float(args.amplitude)),),
    )
    q_circle = closed_radial_q_from_chart(grid, circle).q
    q_mode2 = closed_radial_q_from_chart(grid, mode2).q
    q_high = _closed_high_residual(
        grid,
        q_mode2,
        mode=int(args.mode),
        fraction=float(args.high_fraction),
    )
    cases = {
        "circle": _case_metrics(grid, name="circle", q_target=q_circle, args=args),
        "mode2": _case_metrics(grid, name="mode2", q_target=q_mode2, args=args),
        "high_residual": _case_metrics(grid, name="high_residual", q_target=q_high, args=args),
    }
    circle_length = float(closed_polygon_geometry(circle.vertices, sigma=1.0).length)
    mode2_length = float(closed_polygon_geometry(mode2.vertices, sigma=1.0).length)
    if mode2_length <= circle_length:
        raise AssertionError("mode-2 closed chart did not increase surface energy")
    if abs(cases["mode2"]["q_area"] - cases["mode2"]["polygon_area"]) > float(args.area_tolerance):
        raise AssertionError("closed q area does not match polygon area within oracle tolerance")
    if float(cases["mode2"]["restoring_action"]) >= 0.0:
        raise AssertionError("closed mode restoring action has the wrong sign")
    if float(cases["mode2"]["length_fd_residual"]) > float(args.fd_tolerance):
        raise AssertionError("closed length covector failed finite-difference check")
    if float(cases["mode2"]["area_fd_residual"]) > float(args.fd_tolerance):
        raise AssertionError("closed area covector failed finite-difference check")
    if float(cases["high_residual"]["residual_l2"]) <= float(cases["mode2"]["residual_l2"]):
        raise AssertionError("closed high residual was not isolated as residual")
    if abs(float(cases["high_residual"]["coeff_cos"]) - float(cases["mode2"]["coeff_cos"])) > 3.0e-4:
        raise AssertionError("closed high residual changed the admitted mode")
    return {
        "x_edges": np.asarray(grid.coords[0], dtype=float),
        "y_edges": np.asarray(grid.coords[1], dtype=float),
        "cell_area": np.diff(np.asarray(grid.coords[0]))[:, None]
        * np.diff(np.asarray(grid.coords[1]))[None, :],
        "circle_length": circle_length,
        "mode2_length": mode2_length,
        **cases,
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    cell_area = np.asarray(results["cell_area"], dtype=float)
    case_names = ("circle", "mode2", "high_residual")
    fig, axes = plt.subplots(3, 3, figsize=(10.8, 8.4), constrained_layout=True)
    for row, name in enumerate(case_names):
        case = results[name]
        q_target = np.asarray(case["q_target"], dtype=float)
        q_phys = np.asarray(case["q_phys"], dtype=float)
        residual = np.asarray(case["residual"], dtype=float)
        vertices = np.asarray(case["vertices"], dtype=float)
        theta_target = q_target / cell_area
        theta_phys = q_phys / cell_area
        residual_theta = residual / cell_area
        panels = (
            (theta_target, "q_T", "viridis", 0.0, 1.0),
            (theta_phys, "Q_h(X*)", "viridis", 0.0, 1.0),
            (
                residual_theta,
                "r = q_T - Q_h(X*)",
                "RdBu_r",
                -max(float(np.max(np.abs(residual_theta))), 1.0e-12),
                max(float(np.max(np.abs(residual_theta))), 1.0e-12),
            ),
        )
        for col, (field, title, cmap, vmin, vmax) in enumerate(panels):
            ax = axes[row, col]
            mesh = ax.pcolormesh(
                x_edges,
                y_edges,
                field.T,
                shading="auto",
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
            )
            ax.plot(vertices[:, 0], vertices[:, 1], color="black", linewidth=1.0)
            ax.plot(
                np.r_[vertices[:, 0], vertices[0, 0]],
                np.r_[vertices[:, 1], vertices[0, 1]],
                color="black",
                linewidth=1.0,
            )
            ax.set_title(f"{name}: {title}")
            ax.set_aspect("equal", adjustable="box")
            fig.colorbar(mesh, ax=ax)
    for ax in axes.flat:
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    save_figure(fig, OUT / "closed_q_manifold_projection_oracle")
    return (OUT / "closed_q_manifold_projection_oracle").with_suffix(".pdf")


def _print_summary(results: dict[str, object], figure_path: pathlib.Path) -> None:
    print("case,residual_l2,residual_area_abs,coeff_cos,restoring_action,length_fd,area_fd")
    for name in ("circle", "mode2", "high_residual"):
        case = results[name]
        print(
            name,
            f"{float(case['residual_l2']):.12e}",
            f"{float(case['residual_area_abs']):.12e}",
            f"{float(case['coeff_cos']):.12e}",
            f"{float(case['restoring_action']):.12e}",
            f"{float(case['length_fd_residual']):.12e}",
            f"{float(case['area_fd_residual']):.12e}",
            sep=",",
        )
    print(f"length_excess,{float(results['mode2_length']) - float(results['circle_length']):.12e}")
    print(f"figure,{figure_path}")
    print(f"==> closed q-manifold projection oracle PASS; outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument("--n", type=int, default=96)
    parser.add_argument("--theta-count", type=int, default=192)
    parser.add_argument("--radius", type=float, default=0.22)
    parser.add_argument("--mode", type=int, default=2)
    parser.add_argument("--amplitude", type=float, default=1.6e-2)
    parser.add_argument("--high-fraction", type=float, default=5.0e-2)
    parser.add_argument("--sigma", type=float, default=1.0)
    parser.add_argument("--area-tolerance", type=float, default=8.0e-4)
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
