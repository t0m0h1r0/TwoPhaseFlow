#!/usr/bin/env python3
"""Graph q-to-interface-manifold projection oracle.

A3 mapping
----------
Equation:
    Treat transported ``q_T`` as a measurement that may not lie on
    ``M_h={Q_h(Gamma_h)}``, then decompose ``q_T=Q_h(eta*)+r``.
Discretization:
    Use a low-mode periodic graph chart for ``eta*``.  The projection preserves
    total volume through the column-height mean and classifies cell-scale
    residuals that cannot be represented by the graph modes.
Code:
    This is an experiment oracle only.  It is not a production q/phi projector
    and does not alter Ch14 runtime transport, capillarity, or projection.
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
from twophase.geometry.p1_cut_geometry import cut_geometry_2d  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    COLORS,
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


def _mode_basis(x: np.ndarray, *, mode: int) -> tuple[np.ndarray, np.ndarray]:
    phase = 2.0 * np.pi * int(mode) * x
    return np.cos(phase), np.sin(phase)


def _weighted_projection(values: np.ndarray, basis: np.ndarray, weights: np.ndarray) -> float:
    denom = float(np.sum(weights * basis * basis))
    if denom <= 0.0:
        return 0.0
    return float(np.sum(weights * values * basis) / denom)


def _eta_from_modes(
    x: np.ndarray,
    *,
    base_height: float,
    modes: tuple[tuple[int, float], ...],
) -> np.ndarray:
    eta = np.full_like(x, float(base_height), dtype=float)
    for mode, amplitude in modes:
        eta = eta + float(amplitude) * np.cos(2.0 * np.pi * int(mode) * x)
    return eta


def _graph_energy_and_gradient(
    x_edges: np.ndarray,
    eta_unique: np.ndarray,
    *,
    sigma: float,
) -> tuple[float, np.ndarray, np.ndarray]:
    dx = np.diff(x_edges)
    eta_next = np.roll(eta_unique, -1)
    d_eta = eta_next - eta_unique
    segment_length = np.sqrt(dx * dx + d_eta * d_eta)
    slope_right = d_eta / segment_length
    slope_left = np.roll(slope_right, 1)
    nodal_gradient = float(sigma) * (slope_left - slope_right)
    weights = 0.5 * (dx + np.roll(dx, 1))
    return float(sigma) * float(np.sum(segment_length)), nodal_gradient, weights


def _p1_q_for_eta(grid: Grid, eta_nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y_nodes = np.asarray(grid.coords[1], dtype=float)
    _x, y = np.meshgrid(np.asarray(grid.coords[0], dtype=float), y_nodes, indexing="ij")
    phi = y - eta_nodes.reshape((-1, 1))
    geometry = cut_geometry_2d(grid, phi, level=0.0)
    return np.asarray(geometry.q, dtype=float), phi


def _column_height(grid: Grid, q: np.ndarray) -> np.ndarray:
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    return np.sum(np.asarray(q, dtype=float), axis=1) / dx


def _project_column_height_to_eta(
    grid: Grid,
    q_target: np.ndarray,
    *,
    max_mode: int,
) -> tuple[np.ndarray, dict[str, float]]:
    """Project ``q_T`` to a low-mode graph by matching column-volume modes."""
    x_edges = np.asarray(grid.coords[0], dtype=float)
    x_center = 0.5 * (x_edges[:-1] + x_edges[1:])
    dx = np.diff(x_edges)
    height = _column_height(grid, q_target)
    mean = float(np.sum(dx * height) / np.sum(dx))
    eta = np.full_like(x_edges, mean, dtype=float)
    coeffs: dict[str, float] = {"mean": mean}
    centered = height - mean
    n = int(height.size)
    for mode in range(1, int(max_mode) + 1):
        cos_c, sin_c = _mode_basis(x_center, mode=mode)
        cos_coef_center = _weighted_projection(centered, cos_c, dx)
        sin_coef_center = _weighted_projection(centered, sin_c, dx)
        cell_average_factor = np.cos(np.pi * mode / n)
        if abs(cell_average_factor) < 1.0e-14:
            cos_coef = 0.0
            sin_coef = 0.0
        else:
            cos_coef = cos_coef_center / cell_average_factor
            sin_coef = sin_coef_center / cell_average_factor
        cos_e, sin_e = _mode_basis(x_edges, mode=mode)
        eta = eta + cos_coef * cos_e + sin_coef * sin_e
        coeffs[f"cos_{mode}"] = float(cos_coef)
        coeffs[f"sin_{mode}"] = float(sin_coef)
    eta[-1] = eta[0]
    return eta, coeffs


def _add_zero_column_cell_residual(
    grid: Grid,
    q: np.ndarray,
    *,
    fraction: float,
) -> np.ndarray:
    """Add a bounded cell-scale perturbation with exactly zero column volume."""
    q_target = np.asarray(q, dtype=float).copy()
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    cell_area = dx[:, None] * dy[None, :]
    theta = np.divide(q_target, cell_area, out=np.zeros_like(q_target), where=cell_area > 0.0)
    for i in range(q_target.shape[0]):
        cut_candidates = np.flatnonzero((theta[i] > 1.0e-12) & (theta[i] < 1.0 - 1.0e-12))
        if cut_candidates.size == 0:
            continue
        j = int(cut_candidates[0])
        below = max(j - 1, 0)
        above = min(j + 1, q_target.shape[1] - 1)
        amount = min(
            float(fraction) * float(cell_area[i, j]),
            float(q_target[i, below]),
            float(cell_area[i, above] - q_target[i, above]),
        )
        if amount <= 0.0:
            continue
        q_target[i, below] -= amount
        q_target[i, above] += amount
    return q_target


def _case_metrics(
    grid: Grid,
    *,
    name: str,
    eta_reference: np.ndarray,
    q_target: np.ndarray,
    max_mode: int,
    sigma: float,
    force_mode: int,
) -> dict[str, np.ndarray | float | str]:
    x_edges = np.asarray(grid.coords[0], dtype=float)
    x_unique = x_edges[:-1]
    dx = np.diff(x_edges)
    eta_star, coeffs = _project_column_height_to_eta(grid, q_target, max_mode=max_mode)
    q_phys, _phi_star = _p1_q_for_eta(grid, eta_star)
    residual = q_target - q_phys
    residual_column = np.sum(residual, axis=1) / dx
    energy, gradient, weights = _graph_energy_and_gradient(
        x_edges,
        eta_star[:-1],
        sigma=sigma,
    )
    variation = gradient / weights
    force = -variation
    cos_force, _sin_force = _mode_basis(x_unique, mode=force_mode)
    eta_mode = _weighted_projection(
        eta_star[:-1] - float(np.sum(dx * eta_star[:-1]) / np.sum(dx)),
        cos_force,
        weights,
    )
    force_projection = _weighted_projection(force, cos_force, weights)
    q_norm = float(np.sqrt(np.sum(q_target * q_target)))
    residual_norm = float(np.sqrt(np.sum(residual * residual)))
    reference_delta = eta_star - eta_reference
    return {
        "name": name,
        "eta_star": eta_star,
        "q_target": q_target,
        "q_phys": q_phys,
        "residual": residual,
        "residual_column": residual_column,
        "energy": energy,
        "residual_l2": residual_norm,
        "residual_rel": residual_norm / max(q_norm, 1.0e-30),
        "residual_column_linf": float(np.max(np.abs(residual_column))),
        "eta_delta_linf": float(np.max(np.abs(reference_delta))),
        "eta_mode": eta_mode,
        "force_mode": force_projection,
        "force_sign_product": eta_mode * force_projection,
        **{f"coef_{key}": value for key, value in coeffs.items()},
    }


def _compute(args) -> dict:
    backend = Backend(use_gpu=False)
    grid = Grid(
        GridConfig(ndim=2, N=(int(args.nx), int(args.ny)), L=(1.0, 1.0), alpha_grid=1.0),
        backend,
    )
    x_edges = np.asarray(grid.coords[0], dtype=float)
    dx = np.diff(x_edges)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    cell_area = dx[:, None] * np.diff(y_edges)[None, :]

    eta_clean = _eta_from_modes(
        x_edges,
        base_height=float(args.base_height),
        modes=((int(args.base_mode), float(args.base_amplitude)),),
    )
    eta_low = _eta_from_modes(
        x_edges,
        base_height=float(args.base_height),
        modes=(
            (int(args.base_mode), float(args.base_amplitude)),
            (int(args.low_mode), float(args.low_amplitude)),
        ),
    )
    q_clean, _phi_clean = _p1_q_for_eta(grid, eta_clean)
    q_low, _phi_low = _p1_q_for_eta(grid, eta_low)
    q_high = _add_zero_column_cell_residual(
        grid,
        q_clean,
        fraction=float(args.high_fraction),
    )

    cases = {
        "clean": _case_metrics(
            grid,
            name="clean",
            eta_reference=eta_clean,
            q_target=q_clean,
            max_mode=int(args.max_mode),
            sigma=float(args.sigma),
            force_mode=int(args.base_mode),
        ),
        "low_mode": _case_metrics(
            grid,
            name="low_mode",
            eta_reference=eta_low,
            q_target=q_low,
            max_mode=int(args.max_mode),
            sigma=float(args.sigma),
            force_mode=int(args.base_mode),
        ),
        "high_residual": _case_metrics(
            grid,
            name="high_residual",
            eta_reference=eta_clean,
            q_target=q_high,
            max_mode=int(args.max_mode),
            sigma=float(args.sigma),
            force_mode=int(args.base_mode),
        ),
    }

    clean = cases["clean"]
    low = cases["low_mode"]
    high = cases["high_residual"]
    clean_tol = float(args.clean_tolerance)
    if float(clean["residual_l2"]) > clean_tol:
        raise AssertionError(f"clean case residual {clean['residual_l2']:.3e} exceeds tolerance")
    if float(low["residual_l2"]) > clean_tol:
        raise AssertionError(f"low-mode case residual {low['residual_l2']:.3e} exceeds tolerance")
    if float(high["residual_l2"]) <= 1.0e4 * clean_tol:
        raise AssertionError("high residual case did not leave a measurable off-manifold residual")
    if float(high["eta_delta_linf"]) > 1.0e-12:
        raise AssertionError("zero-column high residual changed the projected smooth graph")
    if float(high["residual_column_linf"]) > clean_tol:
        raise AssertionError("high residual projection failed to preserve column volume")
    for name, case in cases.items():
        if float(case["force_sign_product"]) >= 0.0:
            raise AssertionError(f"{name} restoring force does not oppose the base mode")

    results: dict[str, object] = {
        "x_edges": x_edges,
        "y_edges": y_edges,
        "cell_area": cell_area,
        "eta_clean": eta_clean,
        "eta_low": eta_low,
    }
    for name, case in cases.items():
        results[name] = {
            key: value
            for key, value in case.items()
            if key != "name"
        }
    return results


def _plot(results: dict) -> pathlib.Path:
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    fig, axes = plt.subplots(3, 3, figsize=(10.8, 8.4), constrained_layout=True)
    case_names = ("clean", "low_mode", "high_residual")
    for row, name in enumerate(case_names):
        eta_star = np.asarray(results[f"{name}"]["eta_star"], dtype=float)
        q_target = np.asarray(results[f"{name}"]["q_target"], dtype=float)
        q_phys = np.asarray(results[f"{name}"]["q_phys"], dtype=float)
        residual = np.asarray(results[f"{name}"]["residual"], dtype=float)
        cell_area = np.asarray(results["cell_area"], dtype=float)
        theta_target = q_target / cell_area
        theta_phys = q_phys / cell_area
        residual_theta = residual / cell_area

        ax = axes[row, 0]
        mesh = ax.pcolormesh(x_edges, y_edges, theta_target.T, shading="auto", vmin=0.0, vmax=1.0)
        ax.plot(x_edges, eta_star, color="black", linewidth=1.0)
        ax.set_title(f"{name}: q_T")
        ax.set_aspect("equal", adjustable="box")
        fig.colorbar(mesh, ax=ax)

        ax = axes[row, 1]
        mesh = ax.pcolormesh(x_edges, y_edges, theta_phys.T, shading="auto", vmin=0.0, vmax=1.0)
        ax.plot(x_edges, eta_star, color="black", linewidth=1.0)
        ax.set_title("Q_h(eta*)")
        ax.set_aspect("equal", adjustable="box")
        fig.colorbar(mesh, ax=ax)

        ax = axes[row, 2]
        limit = max(float(np.max(np.abs(residual_theta))), 1.0e-12)
        mesh = ax.pcolormesh(
            x_edges,
            y_edges,
            residual_theta.T,
            shading="auto",
            cmap="RdBu_r",
            vmin=-limit,
            vmax=limit,
        )
        ax.plot(x_edges, eta_star, color="black", linewidth=1.0)
        ax.set_title("r = q_T - Q_h(eta*)")
        ax.set_aspect("equal", adjustable="box")
        fig.colorbar(mesh, ax=ax)

    for ax in axes.flat:
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    save_figure(fig, OUT / "q_manifold_projection_oracle")
    return (OUT / "q_manifold_projection_oracle").with_suffix(".pdf")


def _print_summary(results: dict, figure_path: pathlib.Path) -> None:
    print("case,residual_l2,residual_rel,residual_column_linf,eta_delta_linf,force_sign_product")
    for name in ("clean", "low_mode", "high_residual"):
        case = results[name]
        print(
            name,
            f"{float(case['residual_l2']):.12e}",
            f"{float(case['residual_rel']):.12e}",
            f"{float(case['residual_column_linf']):.12e}",
            f"{float(case['eta_delta_linf']):.12e}",
            f"{float(case['force_sign_product']):.12e}",
            sep=",",
        )
    print(f"figure,{figure_path}")
    print(f"==> q-manifold projection oracle PASS; outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument("--nx", type=int, default=64)
    parser.add_argument("--ny", type=int, default=64)
    parser.add_argument("--base-height", type=float, default=0.455)
    parser.add_argument("--base-mode", type=int, default=2)
    parser.add_argument("--base-amplitude", type=float, default=4.0e-2)
    parser.add_argument("--low-mode", type=int, default=4)
    parser.add_argument("--low-amplitude", type=float, default=1.2e-2)
    parser.add_argument("--max-mode", type=int, default=4)
    parser.add_argument("--high-fraction", type=float, default=5.0e-2)
    parser.add_argument("--sigma", type=float, default=1.0)
    parser.add_argument("--clean-tolerance", type=float, default=1.0e-13)
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
