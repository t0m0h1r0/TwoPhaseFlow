#!/usr/bin/env python3
"""Minimal graph-chart variational oracle for Ch14 capillarity.

A3 mapping
----------
Equation:
    Own the graph interface ``Gamma_h={(x, eta(x))}``, define
    ``E[eta]=sigma int sqrt(1+eta_x^2) dx``, and derive ``q=Q_h(Gamma_h)``.
Discretization:
    Periodic graph segments carry the surface energy and its exact discrete
    nodal variation.  The finite-volume measure ``q`` is evaluated with the
    existing P1 cut-cell geometry on the gauge ``phi(x,y)=y-eta(x)``.
Code:
    This script is an experiment oracle only.  It is not a runtime fallback and
    does not change Ch14 production capillary transport or projection.
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


def _mode_basis(x: np.ndarray, *, mode: int, length: float) -> tuple[np.ndarray, np.ndarray]:
    phase = 2.0 * np.pi * int(mode) * x / float(length)
    return np.cos(phase), np.sin(phase)


def _weighted_projection(values: np.ndarray, basis: np.ndarray, weights: np.ndarray) -> float:
    denom = float(np.sum(weights * basis * basis))
    if denom <= 0.0:
        return 0.0
    return float(np.sum(weights * values * basis) / denom)


def _graph_eta(x: np.ndarray, *, length: float, base_height: float, amplitude: float, mode: int) -> np.ndarray:
    return float(base_height) + float(amplitude) * np.cos(
        2.0 * np.pi * int(mode) * x / float(length)
    )


def _graph_energy_and_gradient(
    x_edges: np.ndarray,
    eta_unique: np.ndarray,
    *,
    sigma: float,
) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Return segment energy and exact nodal gradient for a periodic graph."""
    dx = np.diff(x_edges)
    eta_next = np.roll(eta_unique, -1)
    d_eta = eta_next - eta_unique
    segment_length = np.sqrt(dx * dx + d_eta * d_eta)
    slope_right = d_eta / segment_length
    slope_left = np.roll(slope_right, 1)
    nodal_gradient = float(sigma) * (slope_left - slope_right)
    energy = float(sigma) * float(np.sum(segment_length))
    weights = 0.5 * (dx + np.roll(dx, 1))
    return energy, nodal_gradient, weights, segment_length


def _p1_geometry_for_eta(grid: Grid, eta_nodes: np.ndarray):
    x_nodes = np.asarray(grid.coords[0], dtype=float)
    y_nodes = np.asarray(grid.coords[1], dtype=float)
    _x, y = np.meshgrid(x_nodes, y_nodes, indexing="ij")
    phi = y - eta_nodes.reshape((-1, 1))
    return cut_geometry_2d(grid, phi, level=0.0), phi


def _compute(args) -> dict:
    if args.amplitude <= 0.0:
        raise ValueError("--amplitude must be positive for the mode oracle")
    if not 0.0 < args.base_height < 1.0:
        raise ValueError("--base-height must be inside the unit-height domain")
    if args.base_height - 2.0 * args.amplitude <= 0.0:
        raise ValueError("base height and amplitude put the graph below the domain")
    if args.base_height + 2.0 * args.amplitude >= 1.0:
        raise ValueError("base height and amplitude put the graph above the domain")

    backend = Backend(use_gpu=False)
    grid = Grid(
        GridConfig(ndim=2, N=(int(args.nx), int(args.ny)), L=(1.0, 1.0), alpha_grid=1.0),
        backend,
    )
    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    x_unique = x_edges[:-1]
    dx = np.diff(x_edges)
    x_center = 0.5 * (x_edges[:-1] + x_edges[1:])
    eta_nodes = _graph_eta(
        x_edges,
        length=1.0,
        base_height=float(args.base_height),
        amplitude=float(args.amplitude),
        mode=int(args.mode),
    )
    eta_unique = eta_nodes[:-1]
    eta_center = 0.5 * (eta_nodes[:-1] + eta_nodes[1:])

    geometry, phi = _p1_geometry_for_eta(grid, eta_nodes)
    q = np.asarray(geometry.q, dtype=float)
    cell_area = dx[:, None] * np.diff(y_edges)[None, :]
    theta = q / cell_area
    column_height = np.sum(q, axis=1) / dx

    energy, nodal_gradient, weights, _segment_length = _graph_energy_and_gradient(
        x_edges,
        eta_unique,
        sigma=float(args.sigma),
    )
    variation_density = nodal_gradient / weights
    restoring_force_density = -variation_density
    cos_nodes, sin_nodes = _mode_basis(x_unique, mode=int(args.mode), length=1.0)
    cos_centers, sin_centers = _mode_basis(x_center, mode=int(args.mode), length=1.0)

    def energy_at(amplitude: float) -> float:
        eta = _graph_eta(
            x_edges,
            length=1.0,
            base_height=float(args.base_height),
            amplitude=float(amplitude),
            mode=int(args.mode),
        )[:-1]
        return _graph_energy_and_gradient(x_edges, eta, sigma=float(args.sigma))[0]

    finite_eps = max(1.0e-8, 1.0e-5 * float(args.amplitude))
    d_energy_d_amp_fd = (
        energy_at(float(args.amplitude) + finite_eps)
        - energy_at(float(args.amplitude) - finite_eps)
    ) / (2.0 * finite_eps)
    d_energy_d_amp_exact = float(np.sum(nodal_gradient * cos_nodes))
    variation_mode = _weighted_projection(variation_density, cos_nodes, weights)
    variation_sine = _weighted_projection(variation_density, sin_nodes, weights)
    force_mode = _weighted_projection(restoring_force_density, cos_nodes, weights)
    eta_mode = _weighted_projection(
        eta_unique - float(args.base_height),
        cos_nodes,
        weights,
    )
    q_height_mode = _weighted_projection(
        column_height - float(args.base_height),
        cos_centers,
        dx,
    )
    q_height_expected_mode = _weighted_projection(
        eta_center - float(args.base_height),
        cos_centers,
        dx,
    )
    q_height_error_linf = float(np.max(np.abs(column_height - eta_center)))
    q_mode_error = abs(q_height_mode - q_height_expected_mode)
    volume_expected = float(np.sum(eta_center * dx))
    volume_error = abs(float(np.sum(q)) - volume_expected)
    surface_error = abs(float(geometry.surface_length) - energy / float(args.sigma))
    fd_rel_error = abs(d_energy_d_amp_fd - d_energy_d_amp_exact) / max(
        1.0,
        abs(d_energy_d_amp_fd),
        abs(d_energy_d_amp_exact),
    )
    force_sign_product = eta_mode * force_mode
    mirror_indices = np.mod(-np.arange(variation_density.size), variation_density.size)
    mirror_error = float(np.max(np.abs(variation_density - variation_density[mirror_indices])))

    sweep_amplitudes = np.asarray(
        [0.0, 0.5 * args.amplitude, args.amplitude, 1.5 * args.amplitude],
        dtype=float,
    )
    sweep_energy = np.asarray([energy_at(float(a)) for a in sweep_amplitudes])
    energy_increments = sweep_energy - sweep_energy[0]
    if np.any(np.diff(energy_increments) < -1.0e-13):
        raise AssertionError("graph energy is not monotone over the amplitude sweep")
    if force_sign_product >= 0.0:
        raise AssertionError("restoring force mode does not oppose the eta mode")
    if volume_error > args.tolerance:
        raise AssertionError(f"Q_h volume error {volume_error:.3e} exceeds tolerance")
    if q_height_error_linf > args.tolerance:
        raise AssertionError(
            f"Q_h column-height error {q_height_error_linf:.3e} exceeds tolerance"
        )
    if surface_error > args.tolerance:
        raise AssertionError(f"P1 surface error {surface_error:.3e} exceeds tolerance")
    if fd_rel_error > 5.0e-8:
        raise AssertionError(f"energy variation relative error {fd_rel_error:.3e} too large")
    if abs(variation_sine) > 5.0e-12:
        raise AssertionError(f"cosine graph leaked sine variation {variation_sine:.3e}")
    if mirror_error > 5.0e-10:
        raise AssertionError(f"mirror symmetry error {mirror_error:.3e} too large")

    metrics = {
        "eta_mode": eta_mode,
        "q_height_mode": q_height_mode,
        "q_height_expected_mode": q_height_expected_mode,
        "q_mode_error": q_mode_error,
        "q_height_error_linf": q_height_error_linf,
        "volume_error": volume_error,
        "surface_error": surface_error,
        "energy": energy,
        "d_energy_d_amp_fd": d_energy_d_amp_fd,
        "d_energy_d_amp_exact": d_energy_d_amp_exact,
        "fd_rel_error": fd_rel_error,
        "variation_mode": variation_mode,
        "variation_sine": variation_sine,
        "force_mode": force_mode,
        "force_sign_product": force_sign_product,
        "mirror_error": mirror_error,
    }
    return {
        "x_edges": x_edges,
        "y_edges": y_edges,
        "x_unique": x_unique,
        "x_center": x_center,
        "eta_nodes": eta_nodes,
        "eta_unique": eta_unique,
        "eta_center": eta_center,
        "q": q,
        "theta": theta,
        "phi": np.asarray(phi, dtype=float),
        "variation_density": variation_density,
        "restoring_force_density": restoring_force_density,
        "weights": weights,
        "sweep_amplitudes": sweep_amplitudes,
        "sweep_energy": sweep_energy,
        "metrics": metrics,
    }


def _plot(results: dict) -> pathlib.Path:
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    x_unique = np.asarray(results["x_unique"], dtype=float)
    x_center = np.asarray(results["x_center"], dtype=float)
    eta_nodes = np.asarray(results["eta_nodes"], dtype=float)
    q = np.asarray(results["q"], dtype=float)
    theta = np.asarray(results["theta"], dtype=float)
    variation = np.asarray(results["variation_density"], dtype=float)
    force = np.asarray(results["restoring_force_density"], dtype=float)
    sweep_amplitudes = np.asarray(results["sweep_amplitudes"], dtype=float)
    sweep_energy = np.asarray(results["sweep_energy"], dtype=float)
    metrics = results["metrics"]

    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.4), constrained_layout=True)
    ax = axes[0, 0]
    mesh = ax.pcolormesh(x_edges, y_edges, theta.T, shading="auto", cmap="viridis", vmin=0.0, vmax=1.0)
    ax.plot(x_edges, eta_nodes, color="black", linewidth=1.4, label="Gamma_h graph")
    ax.set_title("Derived cell volume measure")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="upper right")
    fig.colorbar(mesh, ax=ax, label="theta = q / |C|")

    ax = axes[0, 1]
    ax.plot(x_unique, variation, color=COLORS[0], label="delta E / delta eta")
    ax.plot(x_unique, force, color=COLORS[1], linestyle="--", label="restoring force")
    ax.axhline(0.0, color="0.4", linewidth=0.8)
    ax.set_title("Variation and restoring mode")
    ax.set_xlabel("x")
    ax.legend(loc="best")

    ax = axes[1, 0]
    ax.plot(
        sweep_amplitudes * sweep_amplitudes,
        sweep_energy - sweep_energy[0],
        marker="o",
        color=COLORS[2],
    )
    ax.set_title("Energy grows with amplitude squared")
    ax.set_xlabel("A^2")
    ax.set_ylabel("E[A] - E[0]")

    ax = axes[1, 1]
    ax.plot(x_center, np.sum(q, axis=1) / np.diff(x_edges), color=COLORS[3], label="Q_h column height")
    ax.plot(
        x_center,
        np.asarray(results["eta_center"], dtype=float),
        color="black",
        linestyle=":",
        label="graph segment height",
    )
    ax.set_title("Q_h(eta) derived from Gamma_h")
    ax.set_xlabel("x")
    ax.legend(loc="best")
    text = (
        f"eta_mode={float(metrics['eta_mode']):.3e}\n"
        f"force_mode={float(metrics['force_mode']):.3e}\n"
        f"Q_h height err={float(metrics['q_height_error_linf']):.3e}\n"
        f"dE/dA rel err={float(metrics['fd_rel_error']):.3e}"
    )
    ax.text(0.02, 0.03, text, transform=ax.transAxes, va="bottom", ha="left")

    figure_path = OUT / "variational_capillary_oracle"
    save_figure(fig, figure_path)
    return figure_path.with_suffix(".pdf")


def _print_summary(results: dict, figure_path: pathlib.Path) -> None:
    metrics = results["metrics"]
    print("metric,value")
    for key in sorted(metrics):
        print(f"{key},{float(metrics[key]):.12e}")
    print(f"figure,{figure_path}")
    print(f"==> variational capillary oracle PASS; outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument("--nx", type=int, default=64)
    parser.add_argument("--ny", type=int, default=64)
    parser.add_argument("--mode", type=int, default=2)
    parser.add_argument("--amplitude", type=float, default=4.0e-2)
    parser.add_argument("--base-height", type=float, default=4.55e-1)
    parser.add_argument("--sigma", type=float, default=1.0)
    parser.add_argument("--tolerance", type=float, default=2.0e-13)
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
