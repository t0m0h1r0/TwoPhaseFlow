#!/usr/bin/env python3
"""Zero-step Ch14 runtime force dry-run for the PhaseRegion route.

A3 mapping
----------
Equation:
    Runtime owns liquid volume ``q_l`` and PhaseRegion diagnostics own the gas
    complement ``q_g = |C|-q_l``.  The force endpoint is not advanced; it only
    checks the fixed-stratum identity
    ``dE_h[T_h(u_f)] + <s_f,u_f>_{M_f}=0`` for the runtime initial interface.
Discretization:
    Build the Ch14 oscillating-droplet initial state from the production YAML,
    convert ``q_l`` to the explicit gas owner, rebuild no state, and assemble a
    diagnostic closed-interface Riesz face cochain from the runtime ``phi``
    gauge on the admission grid.  The face metric uses runtime density-derived
    face masses.
Code:
    This is an experiment oracle only.  It does not advance time, connect force
    to pressure/velocity, run nonlinear optimization, micro-step, or run T/8.
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
from twophase.ccd.fccd import FCCDSolver  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.coupling.closed_interface_riesz import (  # noqa: E402
    closed_interface_riesz_cochain,
    component_reaction_hodge_gate,
    fixed_stratum_virtual_work_check,
    weighted_hodge_decomposition,
)
from twophase.coupling.phase_region_force_admission import (  # noqa: E402
    phase_region_face_mass_metric,
    scale_face_velocity_to_fixed_stratum,
)
from twophase.geometry import (  # noqa: E402
    CellMeasurePhase,
    map_cell_measure_to_phase_owner,
)
from twophase.geometry.phase_state import GeometricPhaseState  # noqa: E402
from twophase.levelset.heaviside import heaviside  # noqa: E402
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.simulation.divergence_ops import FCCDDivergenceOperator  # noqa: E402
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
        raise ValueError("runtime force dry-run expects one ellipse object")
    obj = objects[0]
    if obj.get("interior_phase") != "liquid":
        raise ValueError("runtime force dry-run expects liquid inside the ellipse")
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
    eps = _runtime_eps(cfg)
    if float(cfg.grid.alpha_grid) > 1.0:
        phi_uniform = _ellipse_phi(grid, ellipse)
        psi_uniform = heaviside(np, -phi_uniform, eps)
        ccd = CCDSolver(grid, grid.backend, bc_type=cfg.grid.bc_type)
        grid.update_from_levelset(psi_uniform, eps, ccd=ccd)
    phi = _ellipse_phi(grid, ellipse)
    return grid, GeometricPhaseState.from_phi(grid, phi)


def _runtime_eps(cfg: ExperimentConfig) -> float:
    return float(cfg.grid.eps_factor) * (float(cfg.grid.LX) / float(cfg.grid.NX))


def _cell_area(grid: Grid) -> np.ndarray:
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    return dx[:, None] * dy[None, :]


def _smooth_face_probe(grid: Grid) -> list[np.ndarray]:
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    x_faces = 0.5 * (x[:-1] + x[1:])
    y_faces = 0.5 * (y[:-1] + y[1:])
    lx = max(float(x[-1] - x[0]), 1.0e-30)
    ly = max(float(y[-1] - y[0]), 1.0e-30)
    X0, Y0 = np.meshgrid(x_faces, y, indexing="ij")
    X1, Y1 = np.meshgrid(x, y_faces, indexing="ij")
    return [
        np.sin(2.0 * np.pi * X0 / lx) * np.cos(np.pi * Y0 / ly),
        -0.5 * np.cos(np.pi * X1 / lx) * np.sin(2.0 * np.pi * Y1 / ly),
    ]


def _compute(
    config_path: pathlib.Path,
    *,
    capacity_tolerance: float,
    fd_eps: float,
    sign_fraction: float,
    riesz_tolerance: float,
    fd_power_tolerance: float,
    divergence_tolerance: float,
) -> dict[str, object]:
    cfg = ExperimentConfig.from_yaml(config_path)
    ellipse = _ellipse_from_config(cfg)
    grid, phase_state = _phase_state_on_admission_grid(cfg, ellipse)
    xp = grid.backend.xp
    cell_area = _cell_area(grid)
    q_l_runtime = np.asarray(phase_state.q, dtype=float)
    owner_map = map_cell_measure_to_phase_owner(
        q_l_runtime,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        capacity_tolerance=float(capacity_tolerance),
    )
    eps = _runtime_eps(cfg)
    psi = heaviside(np, -np.asarray(phase_state.phi, dtype=float), eps)
    ccd = CCDSolver(grid, grid.backend, bc_type=cfg.grid.bc_type)
    fccd = FCCDSolver(grid, grid.backend, bc_type=cfg.grid.bc_type, ccd_solver=ccd)
    div_op = FCCDDivergenceOperator(fccd)
    face_metric = phase_region_face_mass_metric(
        xp=xp,
        grid=grid,
        psi=psi,
        rho_l=float(cfg.physics.rho_l),
        rho_g=float(cfg.physics.rho_g),
    )
    cochain = closed_interface_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=psi,
        fccd=fccd,
        sigma=float(cfg.physics.sigma),
        face_weight_components=face_metric.face_weight_components,
    )
    sign_margin = float(np.min(np.abs(np.asarray(psi, dtype=float) - 0.5)))
    self_velocity = scale_face_velocity_to_fixed_stratum(
        xp=xp,
        fccd=fccd,
        psi=cochain.psi,
        face_velocity_components=cochain.surface_acceleration,
        fd_eps=float(fd_eps),
        sign_fraction=float(sign_fraction),
    )
    if not self_velocity.valid:
        raise AssertionError(f"runtime self velocity scaling failed: {self_velocity.reason}")
    check_self = fixed_stratum_virtual_work_check(
        xp=xp,
        grid=grid,
        fccd=fccd,
        cochain=cochain,
        face_velocity_components=self_velocity.face_velocity_components,
        epsilon=float(fd_eps),
    )
    smooth = [xp.asarray(component) for component in _smooth_face_probe(grid)]
    probe = [
        surface + 0.125 * smooth_component
        for surface, smooth_component in zip(cochain.surface_acceleration, smooth, strict=True)
    ]
    probe_velocity = scale_face_velocity_to_fixed_stratum(
        xp=xp,
        fccd=fccd,
        psi=cochain.psi,
        face_velocity_components=probe,
        fd_eps=float(fd_eps),
        sign_fraction=float(sign_fraction),
    )
    if not probe_velocity.valid:
        raise AssertionError(f"runtime probe velocity scaling failed: {probe_velocity.reason}")
    check_probe = fixed_stratum_virtual_work_check(
        xp=xp,
        grid=grid,
        fccd=fccd,
        cochain=cochain,
        face_velocity_components=probe_velocity.face_velocity_components,
        epsilon=float(fd_eps),
    )
    decomposition = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=cochain.surface_acceleration,
        face_weight_components=cochain.face_weight_components,
    )
    reaction_gate = component_reaction_hodge_gate(
        xp=xp,
        div_op=div_op,
        cochain=cochain,
    )
    if not check_self.valid:
        raise AssertionError(f"runtime self virtual work left stratum: {check_self.reason}")
    if not check_probe.valid:
        raise AssertionError(f"runtime probe virtual work left stratum: {check_probe.reason}")
    if check_self.riesz_residual > float(riesz_tolerance):
        raise AssertionError("runtime self Riesz work pairing failed")
    if check_probe.riesz_residual > float(riesz_tolerance):
        raise AssertionError("runtime probe Riesz work pairing failed")
    if check_self.finite_difference_power_residual > float(fd_power_tolerance):
        raise AssertionError("runtime self finite-difference power pairing failed")
    if check_probe.finite_difference_power_residual > float(fd_power_tolerance):
        raise AssertionError("runtime probe finite-difference power pairing failed")
    if decomposition.hodge_divergence_linf > float(divergence_tolerance):
        raise AssertionError("runtime Hodge residual is not divergence-free")
    if reaction_gate.residual_divergence_linf > float(divergence_tolerance):
        raise AssertionError("runtime reaction-gate residual is not divergence-free")

    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    metrics = {
        "runtime_steps": 0.0,
        "source_phase": float(CellMeasurePhase.LIQUID),
        "owner_phase": float(CellMeasurePhase.GAS),
        "complement_used": float(owner_map.complement_used),
        "liquid_runtime_volume": float(owner_map.source_volume),
        "gas_target_volume": float(owner_map.owner_volume),
        "compat_linf": float(phase_state.compatibility_residual_linf),
        "stratum_sign_margin": sign_margin,
        "self_fd_power_residual": float(check_self.finite_difference_power_residual),
        "self_riesz_residual": float(check_self.riesz_residual),
        "self_velocity_scale": float(self_velocity.scale),
        "self_finite_difference": float(check_self.finite_difference),
        "self_capillary_power": float(check_self.capillary_power),
        "probe_fd_power_residual": float(check_probe.finite_difference_power_residual),
        "probe_riesz_residual": float(check_probe.riesz_residual),
        "probe_velocity_scale": float(probe_velocity.scale),
        "probe_finite_difference": float(check_probe.finite_difference),
        "probe_capillary_power": float(check_probe.capillary_power),
        "component_weighted_l2": float(decomposition.component_weighted_l2),
        "range_weighted_l2": float(decomposition.range_weighted_l2),
        "hodge_weighted_l2": float(decomposition.hodge_weighted_l2),
        "hodge_divergence_linf": float(decomposition.hodge_divergence_linf),
        "reaction_beta": float(reaction_gate.beta),
        "reaction_residual_weighted_l2": float(reaction_gate.residual_weighted_l2),
        "reaction_residual_ratio": float(reaction_gate.residual_ratio),
        "reaction_residual_divergence_linf": float(reaction_gate.residual_divergence_linf),
        "sigma": float(cfg.physics.sigma),
        "rho_l": float(cfg.physics.rho_l),
        "rho_g": float(cfg.physics.rho_g),
        "grid_alpha": float(cfg.grid.alpha_grid),
        "min_dx": min(float(np.min(np.diff(x_edges))), float(np.min(np.diff(y_edges)))),
        "force_admissible": 0.0,
    }
    return {
        "metrics": metrics,
        "fields": {
            "x_edges": x_edges,
            "y_edges": y_edges,
            "q_l_runtime": q_l_runtime,
            "q_g_target": np.asarray(owner_map.q_owner, dtype=float),
            "cell_area": cell_area,
            "psi": np.asarray(psi, dtype=float),
            "surface_acceleration_0": np.asarray(cochain.surface_acceleration[0], dtype=float),
            "surface_acceleration_1": np.asarray(cochain.surface_acceleration[1], dtype=float),
            "hodge_component_0": np.asarray(decomposition.hodge_components[0], dtype=float),
            "hodge_component_1": np.asarray(decomposition.hodge_components[1], dtype=float),
            "reaction_residual_0": np.asarray(reaction_gate.residual_components[0], dtype=float),
            "reaction_residual_1": np.asarray(reaction_gate.residual_components[1], dtype=float),
        },
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    fields = results["fields"]
    metrics = results["metrics"]
    x_edges = np.asarray(fields["x_edges"], dtype=float)
    y_edges = np.asarray(fields["y_edges"], dtype=float)
    cell_area = np.asarray(fields["cell_area"], dtype=float)
    psi = np.asarray(fields["psi"], dtype=float)
    acceleration = [
        np.asarray(fields["surface_acceleration_0"], dtype=float),
        np.asarray(fields["surface_acceleration_1"], dtype=float),
    ]
    hodge = [
        np.asarray(fields["hodge_component_0"], dtype=float),
        np.asarray(fields["hodge_component_1"], dtype=float),
    ]
    Xc, Yc, u, v = _cell_center_vectors_from_edges(x_edges, y_edges, acceleration)
    _, _, uh, vh = _cell_center_vectors_from_edges(x_edges, y_edges, hodge)
    speed = np.sqrt(u * u + v * v)
    hodge_speed = np.sqrt(uh * uh + vh * vh)
    stride = max(Xc.shape[0] // 16, 1)

    fig, axes = plt.subplots(2, 3, figsize=(12.0, 7.0), constrained_layout=True)
    panels = (
        ("runtime q_l / |C|", np.asarray(fields["q_l_runtime"], dtype=float) / cell_area, "viridis"),
        ("owner q_g / |C|", np.asarray(fields["q_g_target"], dtype=float) / cell_area, "viridis"),
        ("runtime psi", psi[:-1, :-1], "viridis"),
    )
    for ax, (title, field, cmap) in zip(axes.flat[:3], panels):
        mesh = ax.pcolormesh(x_edges, y_edges, field.T, shading="auto", cmap=cmap, vmin=0.0, vmax=1.0)
        ax.contour(x_edges, y_edges, psi.T, levels=(0.5,), colors="black", linewidths=1.0)
        ax.set_title(title)
        ax.set_aspect("equal", adjustable="box")
        fig.colorbar(mesh, ax=ax, shrink=0.82)

    ax = axes.flat[3]
    mesh = ax.pcolormesh(Xc, Yc, speed.T, shading="auto", cmap="magma")
    ax.quiver(
        Xc[::stride, ::stride],
        Yc[::stride, ::stride],
        u[::stride, ::stride],
        v[::stride, ::stride],
        angles="xy",
        scale_units="xy",
        scale=max(float(np.max(speed)), 1.0e-30) * 180.0,
        color="white",
        width=0.004,
    )
    ax.set_title("runtime face cochain")
    ax.set_aspect("equal", adjustable="box")
    fig.colorbar(mesh, ax=ax, shrink=0.82)

    ax = axes.flat[4]
    mesh = ax.pcolormesh(Xc, Yc, hodge_speed.T, shading="auto", cmap="plasma")
    ax.set_title("Hodge residual magnitude")
    ax.set_aspect("equal", adjustable="box")
    fig.colorbar(mesh, ax=ax, shrink=0.82)

    ax = axes.flat[5]
    labels = (
        "self work",
        "probe work",
        "H div",
        "react div",
        "react ratio",
        "compat",
    )
    values = (
        float(metrics["self_fd_power_residual"]),
        float(metrics["probe_fd_power_residual"]),
        float(metrics["hodge_divergence_linf"]),
        float(metrics["reaction_residual_divergence_linf"]),
        float(metrics["reaction_residual_ratio"]),
        float(metrics["compat_linf"]),
    )
    ax.bar(np.arange(len(labels)), np.log10(np.maximum(values, 1.0e-30)), color="#3a506b")
    ax.set_xticks(np.arange(len(labels)), labels, rotation=30, ha="right")
    ax.set_ylabel("log10 magnitude")
    ax.set_title("runtime force dry-run checks")
    ax.grid(axis="y", alpha=0.25)
    ax.text(
        0.03,
        0.97,
        "\n".join(
            (
                f"runtime_steps = {float(metrics['runtime_steps']):.0f}",
                f"|s|_M = {float(metrics['component_weighted_l2']):.8e}",
                f"|H|_M = {float(metrics['hodge_weighted_l2']):.8e}",
                f"reaction ratio = {float(metrics['reaction_residual_ratio']):.8e}",
                "force_admissible = 0",
            )
        ),
        transform=ax.transAxes,
        va="top",
        family="monospace",
        fontsize=8,
    )
    for ax in axes.flat:
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    save_figure(fig, OUT / "phase_region_runtime_force_dry_run")
    return (OUT / "phase_region_runtime_force_dry_run").with_suffix(".pdf")


def _cell_center_vectors_from_edges(
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    face_components: list[np.ndarray],
) -> tuple[np.ndarray, ...]:
    xc = 0.5 * (x_edges[:-1] + x_edges[1:])
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])
    Xc, Yc = np.meshgrid(xc, yc, indexing="ij")
    u = 0.5 * (np.asarray(face_components[0])[:, :-1] + np.asarray(face_components[0])[:, 1:])
    v = 0.5 * (np.asarray(face_components[1])[:-1, :] + np.asarray(face_components[1])[1:, :])
    return Xc, Yc, u, v


def _print_summary(results: dict[str, object], figure_path: pathlib.Path) -> None:
    metrics = results["metrics"]
    print("metric,value")
    for key in (
        "runtime_steps",
        "complement_used",
        "liquid_runtime_volume",
        "gas_target_volume",
        "compat_linf",
        "stratum_sign_margin",
        "self_fd_power_residual",
        "self_riesz_residual",
        "self_velocity_scale",
        "self_finite_difference",
        "self_capillary_power",
        "probe_fd_power_residual",
        "probe_riesz_residual",
        "probe_velocity_scale",
        "probe_finite_difference",
        "probe_capillary_power",
        "component_weighted_l2",
        "range_weighted_l2",
        "hodge_weighted_l2",
        "hodge_divergence_linf",
        "reaction_beta",
        "reaction_residual_weighted_l2",
        "reaction_residual_ratio",
        "reaction_residual_divergence_linf",
        "sigma",
        "rho_l",
        "rho_g",
        "grid_alpha",
        "min_dx",
        "force_admissible",
    ):
        print(key, f"{float(metrics[key]):.12e}", sep=",")
    print(f"figure,{figure_path}")
    print(f"==> phase-region runtime force dry-run PASS; outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument("--config", type=pathlib.Path, default=CONFIG)
    parser.add_argument("--capacity-tolerance", type=float, default=1.0e-13)
    parser.add_argument("--fd-eps", type=float, default=1.0e-7)
    parser.add_argument("--sign-fraction", type=float, default=2.0e-2)
    parser.add_argument("--riesz-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--fd-power-tolerance", type=float, default=1.0e-5)
    parser.add_argument("--divergence-tolerance", type=float, default=1.0e-8)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(
            args.config,
            capacity_tolerance=float(args.capacity_tolerance),
            fd_eps=float(args.fd_eps),
            sign_fraction=float(args.sign_fraction),
            riesz_tolerance=float(args.riesz_tolerance),
            fd_power_tolerance=float(args.fd_power_tolerance),
            divergence_tolerance=float(args.divergence_tolerance),
        )
        save_results(NPZ, results)
    figure_path = _plot(results)
    _print_summary(results, figure_path)


if __name__ == "__main__":
    main()
