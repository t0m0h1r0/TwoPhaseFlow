#!/usr/bin/env python3
"""PhaseRegion force/work-pairing oracle for a closed capillary chart.

A3 mapping
----------
Equation:
    Own the gas/liquid phase region through its boundary
    ``Gamma_h = X(theta)``.  The closed-chart capillary energy is
    ``E_h[X] = sigma L[X]`` with volume constraint ``A_h[X]``.  The pressure
    reaction removes the area-gradient component, so the capillary force
    covector is ``F_h = -(dE_h - beta dA_h)``.
Discretization:
    Use the existing polygonal closed curve chart.  Work is paired in the same
    vertex Euclidean metric used by the closed-chart oracle:
    ``F_h dot v = -dE_h dot v`` for first-order area-free variations.
Code:
    This is an experiment oracle only.  It does not connect the Ch14 runtime,
    pressure projection, velocity space, nonlinear optimization, micro-steps,
    or T/8.
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from twophase.geometry import (  # noqa: E402
    closed_mode_restoring_action,
    closed_polygon_geometry,
    closed_radial_chart_from_modes,
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


def _radial_mode_direction(vertices: np.ndarray, theta: np.ndarray, *, mode: int, phase: str) -> np.ndarray:
    center = np.mean(vertices, axis=0)
    radial = vertices - center
    radial_norm = np.linalg.norm(radial, axis=-1)
    radial_unit = radial / radial_norm[:, None]
    if phase == "cos":
        shape = np.cos(float(mode) * theta)
    elif phase == "sin":
        shape = np.sin(float(mode) * theta)
    else:
        raise ValueError("phase must be 'cos' or 'sin'")
    return shape[:, None] * radial_unit


def _area_free_direction(direction: np.ndarray, area_gradient: np.ndarray) -> np.ndarray:
    area_norm_sq = float(np.sum(area_gradient * area_gradient))
    if area_norm_sq <= 0.0:
        raise AssertionError("area gradient vanished")
    return direction - float(np.sum(area_gradient * direction) / area_norm_sq) * area_gradient


def _central_difference(
    vertices: np.ndarray,
    direction: np.ndarray,
    *,
    eps: float,
    sigma: float,
) -> tuple[float, float]:
    plus = closed_polygon_geometry(vertices + float(eps) * direction, sigma=float(sigma))
    minus = closed_polygon_geometry(vertices - float(eps) * direction, sigma=float(sigma))
    fd_energy = (float(plus.length) * float(sigma) - float(minus.length) * float(sigma)) / (
        2.0 * float(eps)
    )
    fd_area = (float(plus.area) - float(minus.area)) / (2.0 * float(eps))
    return fd_energy, fd_area


def _energy(vertices: np.ndarray, *, sigma: float) -> float:
    return float(sigma) * float(closed_polygon_geometry(vertices, sigma=float(sigma)).length)


def _compute(args) -> dict[str, object]:
    theta = np.linspace(0.0, 2.0 * np.pi, int(args.theta_count), endpoint=False)
    state = closed_radial_chart_from_modes(
        theta,
        center=(float(args.center_x), float(args.center_y)),
        base_radius=float(args.radius),
        modes=((int(args.mode), float(args.amplitude)),),
    )
    vertices = np.asarray(state.vertices, dtype=float)
    geometry = closed_polygon_geometry(vertices, sigma=float(args.sigma))
    surface_gradient = np.asarray(geometry.surface_gradient, dtype=float)
    area_gradient = np.asarray(geometry.area_gradient, dtype=float)
    area_norm_sq = float(np.sum(area_gradient * area_gradient))
    if area_norm_sq <= 0.0:
        raise AssertionError("area gradient norm is zero")

    beta = float(np.sum(surface_gradient * area_gradient) / area_norm_sq)
    constrained_gradient = surface_gradient - beta * area_gradient
    force = -constrained_gradient

    cos_direction = _radial_mode_direction(vertices, theta, mode=int(args.mode), phase="cos")
    sin_direction = _radial_mode_direction(vertices, theta, mode=int(args.mode), phase="sin")
    area_free_cos = _area_free_direction(cos_direction, area_gradient)

    fd_energy, fd_area = _central_difference(
        vertices,
        cos_direction,
        eps=float(args.fd_eps),
        sigma=float(args.sigma),
    )
    fd_energy_area_free, fd_area_area_free = _central_difference(
        vertices,
        area_free_cos,
        eps=float(args.fd_eps),
        sigma=float(args.sigma),
    )
    grad_energy = float(np.sum(surface_gradient * cos_direction))
    grad_area = float(np.sum(area_gradient * cos_direction))
    constrained_rate = float(np.sum(constrained_gradient * area_free_cos))
    work_rate = float(np.sum(force * area_free_cos))
    force_mode_action = float(np.sum(force * cos_direction))
    sine_action = float(np.sum(force * sin_direction))
    restoring_action = closed_mode_restoring_action(geometry, vertices, theta, mode=int(args.mode))
    force_area_reaction = float(np.sum(force * area_gradient))

    force_scale = max(float(np.max(np.linalg.norm(force, axis=1))), 1.0e-30)
    step = float(args.energy_step) * float(args.radius) / force_scale
    stepped_vertices = vertices + step * force
    stepped_geometry = closed_polygon_geometry(stepped_vertices, sigma=float(args.sigma))
    energy_before = _energy(vertices, sigma=float(args.sigma))
    energy_after = _energy(stepped_vertices, sigma=float(args.sigma))
    area_after = float(stepped_geometry.area)

    surface_fd_error = abs(fd_energy - grad_energy)
    area_fd_error = abs(fd_area - grad_area)
    area_free_fd_error = abs(fd_energy_area_free - constrained_rate)
    area_free_rate_abs = abs(float(np.sum(area_gradient * area_free_cos)))
    work_pairing_error = abs(work_rate + constrained_rate)
    restoring_error = abs(restoring_action - force_mode_action)
    energy_drop = energy_before - energy_after
    area_step_change = abs(area_after - float(geometry.area))

    if surface_fd_error > float(args.fd_tolerance):
        raise AssertionError("surface-energy covector failed finite-difference check")
    if area_fd_error > float(args.fd_tolerance):
        raise AssertionError("area covector failed finite-difference check")
    if abs(fd_area_area_free) > float(args.area_rate_tolerance):
        raise AssertionError("area-free direction has nonzero finite-difference area rate")
    if area_free_rate_abs > float(args.area_rate_tolerance):
        raise AssertionError("area-free direction has nonzero analytic area rate")
    if area_free_fd_error > float(args.fd_tolerance):
        raise AssertionError("area-free constrained energy rate failed finite-difference check")
    if abs(force_area_reaction) > float(args.area_reaction_tolerance):
        raise AssertionError("force is not orthogonal to the area reaction")
    if work_pairing_error > float(args.work_tolerance):
        raise AssertionError("force/work pairing does not close in the vertex metric")
    if restoring_error > float(args.work_tolerance):
        raise AssertionError("force mode action disagrees with closed-mode helper")
    if float(args.amplitude) * force_mode_action >= 0.0:
        raise AssertionError("closed mode force has the wrong restoring sign")
    if abs(sine_action) > float(args.phase_tolerance) * max(abs(force_mode_action), 1.0):
        raise AssertionError("orthogonal phase action is too large")
    if energy_drop <= 0.0:
        raise AssertionError("short constrained-force step did not lower energy")

    return {
        "theta": theta,
        "vertices": vertices,
        "force": force,
        "cos_direction": cos_direction,
        "area_free_cos": area_free_cos,
        "energy_before": energy_before,
        "energy_after": energy_after,
        "energy_drop": energy_drop,
        "area_before": float(geometry.area),
        "area_after": area_after,
        "area_step_change": area_step_change,
        "beta": beta,
        "surface_fd_error": surface_fd_error,
        "area_fd_error": area_fd_error,
        "area_free_fd_error": area_free_fd_error,
        "fd_area_area_free": abs(fd_area_area_free),
        "area_free_rate_abs": area_free_rate_abs,
        "force_area_reaction": abs(force_area_reaction),
        "work_pairing_error": work_pairing_error,
        "force_mode_action": force_mode_action,
        "sine_action_abs": abs(sine_action),
        "restoring_action": restoring_action,
        "restoring_error": restoring_error,
        "length": float(geometry.length),
        "sigma": float(args.sigma),
        "mode": int(args.mode),
        "amplitude": float(args.amplitude),
        "energy_step": step,
        "force_admissible": 0.0,
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    vertices = np.asarray(results["vertices"], dtype=float)
    force = np.asarray(results["force"], dtype=float)
    area_free_cos = np.asarray(results["area_free_cos"], dtype=float)
    force_stride = max(vertices.shape[0] // 32, 1)
    force_norm = max(float(np.max(np.linalg.norm(force, axis=1))), 1.0e-30)
    variation_norm = max(float(np.max(np.linalg.norm(area_free_cos, axis=1))), 1.0e-30)

    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.8), constrained_layout=True)
    ax = axes[0]
    ax.plot(
        np.r_[vertices[:, 0], vertices[0, 0]],
        np.r_[vertices[:, 1], vertices[0, 1]],
        color="black",
        linewidth=1.2,
    )
    ax.quiver(
        vertices[::force_stride, 0],
        vertices[::force_stride, 1],
        force[::force_stride, 0] / force_norm,
        force[::force_stride, 1] / force_norm,
        angles="xy",
        scale_units="xy",
        scale=28.0,
        color="#0b6e4f",
        width=0.005,
    )
    ax.set_title("closed chart force")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    ax = axes[1]
    ax.plot(
        np.r_[vertices[:, 0], vertices[0, 0]],
        np.r_[vertices[:, 1], vertices[0, 1]],
        color="black",
        linewidth=1.2,
    )
    ax.quiver(
        vertices[::force_stride, 0],
        vertices[::force_stride, 1],
        area_free_cos[::force_stride, 0] / variation_norm,
        area_free_cos[::force_stride, 1] / variation_norm,
        angles="xy",
        scale_units="xy",
        scale=28.0,
        color="#7b2cbf",
        width=0.005,
    )
    ax.set_title("area-free mode variation")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    ax = axes[2]
    labels = (
        "dE FD",
        "dA FD",
        "work",
        "area rxn",
        "phase",
        "E drop",
    )
    values = (
        float(results["surface_fd_error"]),
        float(results["area_fd_error"]),
        float(results["work_pairing_error"]),
        float(results["force_area_reaction"]),
        float(results["sine_action_abs"]),
        max(float(results["energy_drop"]), 1.0e-30),
    )
    ax.bar(np.arange(len(labels)), np.log10(np.maximum(values, 1.0e-30)), color="#355c7d")
    ax.set_xticks(np.arange(len(labels)), labels, rotation=30, ha="right")
    ax.set_ylabel("log10 magnitude")
    ax.set_title("force/work checks")
    ax.grid(axis="y", alpha=0.25)
    ax.text(
        0.03,
        0.97,
        "\n".join(
            (
                f"mode = {int(results['mode'])}",
                f"amp = {float(results['amplitude']):.3e}",
                f"F.mode = {float(results['force_mode_action']):.8e}",
                f"E0-E1 = {float(results['energy_drop']):.8e}",
                "force_admissible = 0",
            )
        ),
        transform=ax.transAxes,
        va="top",
        family="monospace",
        fontsize=8,
    )

    save_figure(fig, OUT / "phase_region_force_work_oracle")
    return (OUT / "phase_region_force_work_oracle").with_suffix(".pdf")


def _print_summary(results: dict[str, object], figure_path: pathlib.Path) -> None:
    print("metric,value")
    for key in (
        "energy_before",
        "energy_after",
        "energy_drop",
        "area_before",
        "area_after",
        "area_step_change",
        "surface_fd_error",
        "area_fd_error",
        "area_free_fd_error",
        "fd_area_area_free",
        "area_free_rate_abs",
        "force_area_reaction",
        "work_pairing_error",
        "force_mode_action",
        "sine_action_abs",
        "restoring_action",
        "restoring_error",
        "force_admissible",
    ):
        print(key, f"{float(results[key]):.12e}", sep=",")
    print(f"figure,{figure_path}")
    print(f"==> phase-region force/work oracle PASS; outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument("--theta-count", type=int, default=192)
    parser.add_argument("--center-x", type=float, default=0.5)
    parser.add_argument("--center-y", type=float, default=0.5)
    parser.add_argument("--radius", type=float, default=0.22)
    parser.add_argument("--mode", type=int, default=2)
    parser.add_argument("--amplitude", type=float, default=1.6e-2)
    parser.add_argument("--sigma", type=float, default=1.0)
    parser.add_argument("--fd-eps", type=float, default=1.0e-7)
    parser.add_argument("--energy-step", type=float, default=2.0e-4)
    parser.add_argument("--fd-tolerance", type=float, default=1.0e-7)
    parser.add_argument("--area-rate-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--area-reaction-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--work-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--phase-tolerance", type=float, default=1.0e-11)
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
