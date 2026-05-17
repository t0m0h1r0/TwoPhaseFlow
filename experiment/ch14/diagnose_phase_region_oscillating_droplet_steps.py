#!/usr/bin/env python3
"""Few-step PhaseRegion closed-chart oscillating-droplet experiment.

A3 mapping
----------
Equation:
    Own the liquid droplet as a closed radial chart ``Omega_l`` with boundary
    ``Gamma_h = X(theta)`` and derive the gas owner by complement.  The
    capillary energy is ``E_h[X] = sigma L_h[X]`` under fixed droplet area.
    For the first dynamic gate, restrict the chart to the Ch14 mode-2 radial
    deformation and use the second variation ``K_h=d^2E_h/dA^2`` at the circle
    plus the YAML Rayleigh-Lamb/Prosperetti frequency ``omega0`` to define
    ``M_mode = K_h / omega0^2``.
Discretization:
    Step the scalar mode amplitude with velocity-Verlet under the linearized
    variational force ``-K_h A``.  At every time level, rebuild
    ``q_l=Q_h(X(A))``, map to ``q_g=|C|-q_l``, assemble a ``GAS_OUTSIDE``
    closed ``PhaseRegionBatch``, and check residual, volume, energy trend, and
    exact linear oscillator phase.
Code:
    This is a fixed-grid reduced closed-chart experiment.  It does not connect
    a face cochain to the Navier--Stokes runtime, run pressure projection, skip
    a production rebuild, add damping/smoothing, or change CFL/tolerances.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import pathlib
import sys
import time
from typing import Any

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
    closed_radial_chart_from_modes,
    closed_radial_q_from_chart,
    component_offsets_from_batch_ids,
    enum_values,
    map_cell_measure_to_phase_owner,
)
from twophase.levelset.heaviside import heaviside  # noqa: E402
from twophase.simulation.config_loader import require_pyyaml  # noqa: E402
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.tools.plot_factory import generate_figures  # noqa: E402
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

CONFIG = ROOT / "experiment/ch14/config/ch14_oscillating_droplet.yaml"
DEFAULT_STEPS = 8
DEFAULT_DT = 2.0e-5
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"


@dataclass(frozen=True)
class EllipseSpec:
    """Initial liquid ellipse declared by the Ch14 runtime YAML."""

    center: tuple[float, float]
    semi_axes: tuple[float, float]


@dataclass(frozen=True)
class ModalGeometry:
    """Fixed closed-chart modal constants for the reduced droplet oscillator."""

    theta: np.ndarray
    mode: int
    area_over_pi: float
    initial_amplitude: float
    stiffness: float
    omega: float
    mass: float
    period: float


def _ellipse_from_config(cfg: ExperimentConfig) -> EllipseSpec:
    objects = tuple(cfg.initial_condition.get("objects", ()))
    if len(objects) != 1 or objects[0].get("type") != "ellipse":
        raise ValueError("closed droplet steps expects one ellipse object")
    obj = objects[0]
    if obj.get("interior_phase") != "liquid":
        raise ValueError("closed droplet steps expects liquid inside the ellipse")
    center = tuple(float(value) for value in obj["center"])
    semi_axes = tuple(float(value) for value in obj["semi_axes"])
    if len(center) != 2 or len(semi_axes) != 2:
        raise ValueError("ellipse center and semi_axes must be two-dimensional")
    if semi_axes[0] <= 0.0 or semi_axes[1] <= 0.0:
        raise ValueError("ellipse semi_axes must be positive")
    return EllipseSpec(center=center, semi_axes=semi_axes)


def _load_phase_region_droplet_config(
    config_path: pathlib.Path,
) -> tuple[ExperimentConfig, dict[str, Any]]:
    """Load the canonical PhaseRegion closed-chart droplet route."""
    yaml = require_pyyaml()
    with pathlib.Path(config_path).open() as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError("PhaseRegion droplet config must be a YAML mapping")
    cfg = ExperimentConfig.from_yaml(config_path)
    route = raw.get("phase_region_droplet", {})
    if route is None:
        route = {}
    if not isinstance(route, dict):
        raise ValueError("phase_region_droplet section must be a YAML mapping")
    return cfg, dict(route)


def _route_section(route: dict[str, Any], name: str) -> dict[str, Any]:
    section = route.get(name, {})
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(f"phase_region_droplet.{name} must be a YAML mapping")
    return dict(section)


def _omega_from_config(cfg: ExperimentConfig) -> float:
    for figure in cfg.output.figures:
        analytical = dict(figure.get("analytical", {}) or {})
        if analytical.get("formula") == "prosperetti" and "omega0" in analytical:
            omega = float(analytical["omega0"])
            if omega > 0.0 and np.isfinite(omega):
                return omega
    raise ValueError("closed droplet steps requires a positive Prosperetti omega0")


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


def _fit_grid_to_initial_ellipse(cfg: ExperimentConfig, ellipse: EllipseSpec) -> Grid:
    grid = _grid_from_config(cfg)
    if float(cfg.grid.alpha_grid) <= 1.0:
        return grid
    eps = float(cfg.grid.eps_factor) * (float(cfg.grid.LX) / float(cfg.grid.NX))
    phi_uniform = _ellipse_phi(grid, ellipse)
    psi_uniform = heaviside(np, -phi_uniform, eps)
    ccd = CCDSolver(grid, grid.backend, bc_type=cfg.grid.bc_type)
    grid.update_from_levelset(psi_uniform, eps, ccd=ccd)
    return grid


def _cell_area(grid: Grid) -> np.ndarray:
    dx = np.diff(np.asarray(grid.coords[0], dtype=float))
    dy = np.diff(np.asarray(grid.coords[1], dtype=float))
    return dx[:, None] * dy[None, :]


def _volume_closed_cell_measure(
    q_source: np.ndarray,
    cell_area: np.ndarray,
    *,
    target_volume: float,
    capacity_tolerance: float,
) -> tuple[np.ndarray, float, float]:
    """Close a chart-derived cell measure to the chart's fixed total volume."""
    q = np.asarray(q_source, dtype=float).copy()
    area = np.asarray(cell_area, dtype=float)
    delta = float(target_volume) - float(np.sum(q))
    raw_delta_abs = abs(delta)
    if raw_delta_abs <= 1.0e-18:
        return q, raw_delta_abs, 0.0

    lower_margin = q
    upper_margin = area - q
    if delta > 0.0:
        capacity = upper_margin
    else:
        capacity = lower_margin
    admissible = capacity > float(capacity_tolerance)
    interface_weight = np.minimum(lower_margin, upper_margin)
    weights = np.where(admissible, interface_weight, 0.0)
    if float(np.sum(weights)) <= abs(delta):
        weights = np.where(admissible, capacity, 0.0)
    weight_sum = float(np.sum(weights))
    if weight_sum <= 0.0 or weight_sum + float(capacity_tolerance) < abs(delta):
        raise AssertionError("closed chart q volume closure has insufficient capacity")

    q = q + delta * weights / weight_sum
    if np.any(q < -float(capacity_tolerance)) or np.any(q - area > float(capacity_tolerance)):
        raise AssertionError("closed chart q volume closure violated cell capacity")
    closed_delta_abs = abs(float(target_volume) - float(np.sum(q)))
    return q, raw_delta_abs, closed_delta_abs


def _step_count_from_route(
    cli_steps: int | None,
    route: dict[str, Any],
    cfg: ExperimentConfig,
) -> int:
    if cli_steps is not None:
        step_count = int(cli_steps)
    elif cfg.run.T_final is not None and cfg.run.dt_fixed is not None:
        step_count = int(round(float(cfg.run.T_final) / float(cfg.run.dt_fixed)))
    else:
        run = _route_section(route, "run")
        if "steps" in run:
            step_count = int(run["steps"])
        elif "periods" in run and "steps_per_period" in run:
            step_count = int(round(float(run["periods"]) * int(run["steps_per_period"])))
        else:
            step_count = DEFAULT_STEPS
    if step_count <= 0:
        raise ValueError("--steps or phase_region_droplet.run.steps must be positive")
    return step_count


def _dt_from_route(
    cli_dt: float | None,
    route: dict[str, Any],
    cfg: ExperimentConfig,
    *,
    modal: ModalGeometry,
    step_count: int,
) -> float:
    if cli_dt is not None:
        dt_value = float(cli_dt)
    elif cfg.run.T_final is not None and step_count > 0:
        dt_value = float(cfg.run.T_final) / float(step_count)
    elif cfg.run.dt_fixed is not None:
        dt_value = float(cfg.run.dt_fixed)
    else:
        run = _route_section(route, "run")
        if "dt" in run:
            dt_value = float(run["dt"])
        elif "periods" in run:
            dt_value = float(modal.period) * float(run["periods"]) / float(step_count)
        else:
            dt_value = DEFAULT_DT
    if not np.isfinite(dt_value) or dt_value <= 0.0:
        raise ValueError("--dt or phase_region_droplet.run.dt must be positive and finite")
    return dt_value


def _capillary_cfl_dt_limit(
    cfg: ExperimentConfig,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
) -> float:
    h_min = min(
        float(np.min(np.diff(np.asarray(x_edges, dtype=float)))),
        float(np.min(np.diff(np.asarray(y_edges, dtype=float)))),
    )
    sigma = float(cfg.physics.sigma)
    if sigma <= 0.0:
        return float("inf")
    rho_sum = float(cfg.physics.rho_l) + float(cfg.physics.rho_g)
    return float(
        float(cfg.run.cfl_capillary)
        * np.sqrt(rho_sum * h_min ** 3 / (2.0 * np.pi * sigma))
    )


def _time_grid_from_config(
    cli_steps: int | None,
    cli_dt: float | None,
    route: dict[str, Any],
    cfg: ExperimentConfig,
    *,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    modal: ModalGeometry,
) -> tuple[int, float, float]:
    if cli_dt is not None:
        dt_limit = float(cli_dt)
    elif cfg.run.dt_fixed is not None:
        dt_limit = float(cfg.run.dt_fixed)
    else:
        dt_limit = _capillary_cfl_dt_limit(cfg, x_edges, y_edges)
    if not np.isfinite(dt_limit) or dt_limit <= 0.0:
        dt_limit = _dt_from_route(None, route, cfg, modal=modal, step_count=DEFAULT_STEPS)

    if cli_steps is not None:
        step_count = _step_count_from_route(cli_steps, route, cfg)
    elif cfg.run.T_final is not None:
        step_count = max(1, int(np.ceil(float(cfg.run.T_final) / float(dt_limit))))
    else:
        step_count = _step_count_from_route(None, route, cfg)

    if cfg.run.T_final is not None and cli_dt is None:
        dt_value = float(cfg.run.T_final) / float(step_count)
    elif cfg.run.T_final is not None and cli_steps is None:
        dt_value = float(cfg.run.T_final) / float(step_count)
    else:
        dt_value = _dt_from_route(cli_dt, route, cfg, modal=modal, step_count=step_count)
    if dt_value <= 0.0:
        raise ValueError("time step must be positive")
    return int(step_count), float(dt_value), float(dt_limit)


def _snapshot_indices_from_times(
    snap_times: list[float],
    *,
    dt: float,
    step_count: int,
) -> np.ndarray:
    """Map configured snapshot times to the nearest reduced-route steps."""
    if not snap_times:
        return np.array((0, step_count), dtype=np.int64)
    indices: list[int] = []
    for raw_time in snap_times:
        time_value = float(raw_time)
        step_index = int(round(time_value / float(dt)))
        if 0 <= step_index <= int(step_count):
            indices.append(step_index)
    if 0 not in indices:
        indices.append(0)
    if int(step_count) not in indices:
        indices.append(int(step_count))
    return np.array(sorted(set(indices)), dtype=np.int64)


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


def _base_radius_for_amplitude(area_over_pi: float, amplitude: float) -> float:
    base_sq = float(area_over_pi) - 0.5 * float(amplitude) * float(amplitude)
    if base_sq <= 0.0:
        raise ValueError("area-preserving closed radial base radius became nonpositive")
    return float(np.sqrt(base_sq))


def _state_from_amplitude(
    ellipse: EllipseSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
):
    base_radius = _base_radius_for_amplitude(
        modal.area_over_pi,
        float(amplitude),
    )
    return closed_radial_chart_from_modes(
        modal.theta,
        center=ellipse.center,
        base_radius=base_radius,
        modes=((int(modal.mode), float(amplitude)),),
    )


def _surface_energy(
    ellipse: EllipseSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
    sigma: float,
) -> float:
    state = _state_from_amplitude(ellipse, modal, amplitude=float(amplitude))
    geometry = closed_polygon_geometry(state.vertices, sigma=float(sigma))
    return float(sigma) * float(geometry.length)


def _modal_geometry(
    cfg: ExperimentConfig,
    ellipse: EllipseSpec,
    *,
    theta_count: int,
    mode: int,
    stiffness_probe_fraction: float,
) -> ModalGeometry:
    if int(theta_count) < 16:
        raise ValueError("--theta-count must be at least 16")
    ax, ay = ellipse.semi_axes
    amplitude = 0.5 * (float(ax) - float(ay))
    if amplitude == 0.0:
        raise ValueError("closed droplet steps expects a nonzero mode amplitude")
    area_over_pi = float(ax) * float(ay)
    theta = np.linspace(0.0, 2.0 * np.pi, int(theta_count), endpoint=False)
    omega = _omega_from_config(cfg)
    probe = max(float(stiffness_probe_fraction) * abs(amplitude), 1.0e-9)
    zero_modal = ModalGeometry(
        theta=theta,
        mode=int(mode),
        area_over_pi=area_over_pi,
        initial_amplitude=amplitude,
        stiffness=1.0,
        omega=omega,
        mass=1.0,
        period=float(2.0 * np.pi / omega),
    )
    sigma = float(cfg.physics.sigma)
    e0 = _surface_energy(ellipse, zero_modal, amplitude=0.0, sigma=sigma)
    ep = _surface_energy(ellipse, zero_modal, amplitude=probe, sigma=sigma)
    em = _surface_energy(ellipse, zero_modal, amplitude=-probe, sigma=sigma)
    stiffness = float((ep - 2.0 * e0 + em) / (probe * probe))
    if not np.isfinite(stiffness) or stiffness <= 0.0:
        raise AssertionError("closed modal stiffness must be positive")
    return ModalGeometry(
        theta=theta,
        mode=int(mode),
        area_over_pi=area_over_pi,
        initial_amplitude=amplitude,
        stiffness=stiffness,
        omega=omega,
        mass=float(stiffness / (omega * omega)),
        period=float(2.0 * np.pi / omega),
    )


def _surface_energy_and_linear_rate(
    ellipse: EllipseSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
    sigma: float,
) -> tuple[float, float]:
    energy = _surface_energy(ellipse, modal, amplitude=float(amplitude), sigma=float(sigma))
    rate = float(modal.stiffness) * float(amplitude)
    return energy, rate


def _step_verlet(
    ellipse: EllipseSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
    velocity: float,
    dt: float,
    sigma: float,
) -> tuple[float, float]:
    _surface_energy_value, rate = _surface_energy_and_linear_rate(
        ellipse,
        modal,
        amplitude=float(amplitude),
        sigma=float(sigma),
    )
    half_velocity = float(velocity) - 0.5 * float(dt) * rate / float(modal.mass)
    new_amplitude = float(amplitude) + float(dt) * half_velocity
    _new_surface_energy, new_rate = _surface_energy_and_linear_rate(
        ellipse,
        modal,
        amplitude=new_amplitude,
        sigma=float(sigma),
    )
    new_velocity = half_velocity - 0.5 * float(dt) * new_rate / float(modal.mass)
    return new_amplitude, new_velocity


def _measure_phase_region(
    grid: Grid,
    ellipse: EllipseSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
    cell_area: np.ndarray,
    sigma: float,
    capacity_tolerance: float,
) -> dict[str, object]:
    state = _state_from_amplitude(ellipse, modal, amplitude=float(amplitude))
    q_l_raw = np.asarray(closed_radial_q_from_chart(grid, state).q, dtype=float)
    q_l, raw_closure_abs, closed_closure_abs = _volume_closed_cell_measure(
        q_l_raw,
        cell_area,
        target_volume=float(np.pi * modal.area_over_pi),
        capacity_tolerance=float(capacity_tolerance),
    )
    owner = map_cell_measure_to_phase_owner(
        q_l,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
        capacity_tolerance=float(capacity_tolerance),
    )
    q_g = cell_area - q_l
    region = _region_from_closed_gas_outside(
        state,
        q_g,
        mode=int(modal.mode),
    )
    geometry = closed_polygon_geometry(state.vertices, sigma=float(sigma))
    measurement = assemble_phase_region_measurement(
        region,
        q_g[None, ...],
        np.array((float(geometry.length),), dtype=float),
        q_target=owner.q_owner,
        cell_area=cell_area,
        capacity_tolerance=float(capacity_tolerance),
    )
    if measurement.residual is None:
        raise AssertionError("PhaseRegion closed step did not assemble residual")
    return {
        "state": state,
        "q_l": q_l,
        "q_g": q_g,
        "residual_l2": float(measurement.residual_l2),
        "residual_linf": float(measurement.residual_linf),
        "residual_volume_abs": abs(float(measurement.residual_volume[0])),
        "gas_volume": float(measurement.batch_volumes[0]),
        "liquid_volume": float(np.sum(q_l)),
        "perimeter": float(measurement.batch_perimeters[0]),
        "polygon_area": float(geometry.area),
        "base_radius": float(state.base_radius),
        "q_volume_closure_raw_abs": raw_closure_abs,
        "q_volume_closure_closed_abs": closed_closure_abs,
    }


def _reduced_droplet_snapshot_fields(
    cfg: ExperimentConfig,
    ellipse: EllipseSpec,
    modal: ModalGeometry,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    amplitudes: np.ndarray,
    velocities: np.ndarray,
    snapshot_indices: np.ndarray,
) -> dict[str, np.ndarray]:
    """Build linear Rayleigh-Lamb diagnostic fields at configured snapshots."""
    x_nodes = np.asarray(x_edges, dtype=float)
    y_nodes = np.asarray(y_edges, dtype=float)
    x_grid, y_grid = np.meshgrid(x_nodes, y_nodes, indexing="ij")
    cx, cy = ellipse.center
    rel_x = x_grid - float(cx)
    rel_y = y_grid - float(cy)
    radius = np.sqrt(rel_x ** 2 + rel_y ** 2)
    theta = np.arctan2(rel_y, rel_x)
    radius_safe = np.maximum(radius, 1.0e-14)
    mode = int(modal.mode)
    cos_mode = np.cos(mode * theta)
    sin_mode = np.sin(mode * theta)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    reference_radius = float(np.sqrt(modal.area_over_pi))
    inside_radius = np.maximum(radius_safe / reference_radius, 0.0)
    outside_radius = reference_radius / np.maximum(radius_safe, reference_radius * 1.0e-6)

    phi_snapshots = []
    psi_snapshots = []
    u_snapshots = []
    v_snapshots = []
    pressure_snapshots = []
    rho_snapshots = []
    for step_index in np.asarray(snapshot_indices, dtype=int):
        amplitude = float(amplitudes[step_index])
        modal_velocity = float(velocities[step_index])
        modal_acceleration = -float(modal.omega) ** 2 * amplitude
        base_radius = _base_radius_for_amplitude(modal.area_over_pi, amplitude)
        interface_radius = base_radius + amplitude * cos_mode
        phi = radius - interface_radius
        psi = (phi <= 0.0).astype(float)

        inner_power = inside_radius ** max(mode - 1, 0)
        outer_power = outside_radius ** (mode + 1)
        radial_velocity = (
            psi * modal_velocity * inner_power * cos_mode
            + (1.0 - psi) * modal_velocity * outer_power * cos_mode
        )
        tangential_velocity = (
            -psi * modal_velocity * inner_power * sin_mode
            + (1.0 - psi) * modal_velocity * outer_power * sin_mode
        )
        u = radial_velocity * cos_theta - tangential_velocity * sin_theta
        v = radial_velocity * sin_theta + tangential_velocity * cos_theta

        inner_potential = (radius_safe ** mode) / (mode * reference_radius ** (mode - 1))
        outer_potential = (
            reference_radius ** (mode + 1) / (mode * radius_safe ** mode)
        )
        p_l = -float(cfg.physics.rho_l) * modal_acceleration * inner_potential * cos_mode
        p_g = float(cfg.physics.rho_g) * modal_acceleration * outer_potential * cos_mode
        pressure = psi * p_l + (1.0 - psi) * p_g

        phi_snapshots.append(phi)
        psi_snapshots.append(psi)
        u_snapshots.append(u)
        v_snapshots.append(v)
        pressure_snapshots.append(pressure)
        rho_snapshots.append(
            psi * float(cfg.physics.rho_l)
            + (1.0 - psi) * float(cfg.physics.rho_g)
        )

    return {
        "psi_snapshots": np.stack(psi_snapshots, axis=0),
        "phi_snapshots": np.stack(phi_snapshots, axis=0),
        "u_snapshots": np.stack(u_snapshots, axis=0),
        "v_snapshots": np.stack(v_snapshots, axis=0),
        "pressure_snapshots": np.stack(pressure_snapshots, axis=0),
        "rho_snapshots": np.stack(rho_snapshots, axis=0),
    }


def _compute(
    config_path: pathlib.Path,
    *,
    steps: int | None,
    dt: float | None,
    theta_count: int,
    mode: int,
    reference_amplitude_tolerance: float,
    reference_velocity_tolerance: float,
    energy_drift_tolerance: float,
    residual_tolerance: float,
    volume_tolerance: float,
    capacity_tolerance: float,
    stiffness_probe_fraction: float,
) -> dict[str, object]:
    cfg, route = _load_phase_region_droplet_config(config_path)
    ellipse = _ellipse_from_config(cfg)
    grid = _fit_grid_to_initial_ellipse(cfg, ellipse)
    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    cell_area = _cell_area(grid)
    modal = _modal_geometry(
        cfg,
        ellipse,
        theta_count=int(theta_count),
        mode=int(mode),
        stiffness_probe_fraction=float(stiffness_probe_fraction),
    )
    step_count, dt_value, dt_limit = _time_grid_from_config(
        steps,
        dt,
        route,
        cfg,
        x_edges=x_edges,
        y_edges=y_edges,
        modal=modal,
    )
    snapshot_indices = _snapshot_indices_from_times(
        list(cfg.run.snap_times),
        dt=dt_value,
        step_count=step_count,
    )
    snapshot_index_set = set(int(value) for value in snapshot_indices)

    amplitude = float(modal.initial_amplitude)
    velocity = 0.0
    times = [0.0]
    amplitudes = [amplitude]
    velocities = [velocity]
    energies = []
    surface_energies = []
    q_residual_l2 = []
    q_residual_linf = []
    q_residual_volume = []
    gas_volumes = []
    liquid_volumes = []
    perimeters = []
    polygon_areas = []
    base_radii = []
    q_volume_closure_raw_abs = []
    q_volume_closure_closed_abs = []
    q_l_snapshots = []
    q_g_snapshots = []
    vertices_snapshots = []
    step_wall_times = []

    sigma = float(cfg.physics.sigma)
    for step_index in range(step_count + 1):
        step_wall_start = time.perf_counter()
        measurement = _measure_phase_region(
            grid,
            ellipse,
            modal,
            amplitude=amplitude,
            cell_area=cell_area,
            sigma=sigma,
            capacity_tolerance=float(capacity_tolerance),
        )
        surface_energy, _rate = _surface_energy_and_linear_rate(
            ellipse,
            modal,
            amplitude=amplitude,
            sigma=sigma,
        )
        total_energy = (
            0.5 * float(modal.stiffness) * amplitude * amplitude
            + 0.5 * float(modal.mass) * velocity * velocity
        )
        surface_energies.append(float(surface_energy))
        energies.append(float(total_energy))
        q_residual_l2.append(float(measurement["residual_l2"]))
        q_residual_linf.append(float(measurement["residual_linf"]))
        q_residual_volume.append(float(measurement["residual_volume_abs"]))
        gas_volumes.append(float(measurement["gas_volume"]))
        liquid_volumes.append(float(measurement["liquid_volume"]))
        perimeters.append(float(measurement["perimeter"]))
        polygon_areas.append(float(measurement["polygon_area"]))
        base_radii.append(float(measurement["base_radius"]))
        q_volume_closure_raw_abs.append(float(measurement["q_volume_closure_raw_abs"]))
        q_volume_closure_closed_abs.append(
            float(measurement["q_volume_closure_closed_abs"])
        )
        if step_index in snapshot_index_set:
            q_l_snapshots.append(np.asarray(measurement["q_l"], dtype=float))
            q_g_snapshots.append(np.asarray(measurement["q_g"], dtype=float))
            vertices_snapshots.append(
                np.asarray(measurement["state"].vertices, dtype=float)
            )
        if step_index == step_count:
            step_wall_times.append(time.perf_counter() - step_wall_start)
            break
        amplitude, velocity = _step_verlet(
            ellipse,
            modal,
            amplitude=amplitude,
            velocity=velocity,
            dt=dt_value,
            sigma=sigma,
        )
        step_wall_times.append(time.perf_counter() - step_wall_start)
        times.append((step_index + 1) * dt_value)
        amplitudes.append(amplitude)
        velocities.append(velocity)

    times_arr = np.asarray(times, dtype=float)
    amplitudes_arr = np.asarray(amplitudes, dtype=float)
    velocities_arr = np.asarray(velocities, dtype=float)
    energy_arr = np.asarray(energies, dtype=float)
    kinetic_energy = 0.5 * float(modal.mass) * velocities_arr * velocities_arr
    exact_amplitude = float(modal.initial_amplitude) * np.cos(float(modal.omega) * times_arr)
    exact_velocity = -float(modal.initial_amplitude) * float(modal.omega) * np.sin(
        float(modal.omega) * times_arr
    )
    amplitude_error = np.abs(amplitudes_arr - exact_amplitude)
    velocity_error = np.abs(velocities_arr - exact_velocity)
    energy_scale = max(abs(float(energy_arr[0])), 1.0e-30)
    energy_drift = np.abs(energy_arr - float(energy_arr[0])) / energy_scale
    gas_volumes_arr = np.asarray(gas_volumes, dtype=float)
    liquid_volumes_arr = np.asarray(liquid_volumes, dtype=float)
    volume_drift = np.maximum(
        np.abs(gas_volumes_arr - float(gas_volumes_arr[0])),
        np.abs(liquid_volumes_arr - float(liquid_volumes_arr[0])),
    )
    polygon_area_drift = np.abs(
        np.asarray(polygon_areas, dtype=float) - float(polygon_areas[0])
    )
    mean_axis = 0.5 * (float(ellipse.semi_axes[0]) + float(ellipse.semi_axes[1]))

    if float(np.max(amplitude_error)) > float(reference_amplitude_tolerance):
        raise AssertionError("PhaseRegion droplet steps exceed amplitude reference tolerance")
    if float(np.max(velocity_error)) > float(reference_velocity_tolerance):
        raise AssertionError("PhaseRegion droplet steps exceed velocity reference tolerance")
    if float(np.max(energy_drift)) > float(energy_drift_tolerance):
        raise AssertionError("PhaseRegion droplet steps exceed energy drift tolerance")
    if float(np.max(q_residual_l2)) > float(residual_tolerance):
        raise AssertionError("PhaseRegion droplet steps produced nonzero residual")
    if float(np.max(volume_drift)) > float(volume_tolerance):
        raise AssertionError("PhaseRegion droplet steps changed phase volume")

    metrics = {
        "steps": float(step_count),
        "dt": dt_value,
        "dt_cfl_limit": float(dt_limit),
        "cfl": float(cfg.run.cfl),
        "cfl_capillary": float(cfg.run.cfl_capillary),
        "t_final": float(times_arr[-1]),
        "omega": float(modal.omega),
        "period": float(modal.period),
        "t_over_T": float(times_arr[-1] / modal.period),
        "modal_stiffness": float(modal.stiffness),
        "modal_mass": float(modal.mass),
        "initial_amplitude": float(modal.initial_amplitude),
        "area_over_pi": float(modal.area_over_pi),
        "max_amplitude_error": float(np.max(amplitude_error)),
        "max_velocity_error": float(np.max(velocity_error)),
        "max_energy_drift": float(np.max(energy_drift)),
        "max_residual_l2": float(np.max(q_residual_l2)),
        "max_residual_linf": float(np.max(q_residual_linf)),
        "max_residual_volume_abs": float(np.max(q_residual_volume)),
        "max_volume_drift": float(np.max(volume_drift)),
        "max_polygon_area_drift": float(np.max(polygon_area_drift)),
        "max_q_volume_closure_raw_abs": float(np.max(q_volume_closure_raw_abs)),
        "max_q_volume_closure_closed_abs": float(np.max(q_volume_closure_closed_abs)),
        "final_amplitude": float(amplitudes_arr[-1]),
        "final_exact_amplitude": float(exact_amplitude[-1]),
        "final_velocity": float(velocities_arr[-1]),
        "final_exact_velocity": float(exact_velocity[-1]),
        "initial_energy": float(energy_arr[0]),
        "final_energy": float(energy_arr[-1]),
        "initial_liquid_volume": float(liquid_volumes_arr[0]),
        "initial_gas_volume": float(gas_volumes_arr[0]),
        "grid_alpha": float(cfg.grid.alpha_grid),
        "min_dx": float(np.min(np.diff(x_edges))),
        "min_dy": float(np.min(np.diff(y_edges))),
        "phase_region_droplet_steps_admitted": 1.0,
        "force_admissible": 0.0,
        "step_backend_gpu": 0.0,
        "mean_step_wall_seconds": float(np.mean(step_wall_times)),
        "max_step_wall_seconds": float(np.max(step_wall_times)),
    }
    q_l_snapshot_arr = np.stack(q_l_snapshots, axis=0)
    q_g_snapshot_arr = np.stack(q_g_snapshots, axis=0)
    vertices_snapshot_arr = np.stack(vertices_snapshots, axis=0)
    reduced_fields = _reduced_droplet_snapshot_fields(
        cfg,
        ellipse,
        modal,
        x_edges,
        y_edges,
        amplitudes_arr,
        velocities_arr,
        snapshot_indices,
    )
    snapshots = []
    for out_index, snap_time in enumerate(times_arr[snapshot_indices]):
        snapshots.append(
            {
                "t": float(snap_time),
                "psi": reduced_fields["psi_snapshots"][out_index],
                "phi": reduced_fields["phi_snapshots"][out_index],
                "u": reduced_fields["u_snapshots"][out_index],
                "v": reduced_fields["v_snapshots"][out_index],
                "p": reduced_fields["pressure_snapshots"][out_index],
                "rho": reduced_fields["rho_snapshots"][out_index],
                "grid_coords": [x_edges, y_edges],
            }
        )
    initial_volume = max(float(liquid_volumes_arr[0]), 1.0e-30)
    return {
        "metrics": metrics,
        "times": times_arr,
        "amplitude": amplitudes_arr,
        "signed_deformation": amplitudes_arr / mean_axis,
        "velocity": velocities_arr,
        "exact_amplitude": exact_amplitude,
        "exact_velocity": exact_velocity,
        "kinetic_energy": kinetic_energy,
        "total_energy": energy_arr,
        "surface_energy": np.asarray(surface_energies, dtype=float),
        "relative_energy_drift": energy_drift,
        "q_residual_l2": np.asarray(q_residual_l2, dtype=float),
        "q_residual_linf": np.asarray(q_residual_linf, dtype=float),
        "volume_conservation": volume_drift / initial_volume,
        "volume_drift": volume_drift,
        "polygon_area_drift": polygon_area_drift,
        "q_volume_closure_raw_abs": np.asarray(q_volume_closure_raw_abs, dtype=float),
        "q_volume_closure_closed_abs": np.asarray(
            q_volume_closure_closed_abs,
            dtype=float,
        ),
        "x_edges": x_edges,
        "y_edges": y_edges,
        "cell_area": cell_area,
        "snapshot_indices": snapshot_indices,
        "snapshot_times": times_arr[snapshot_indices],
        "snapshot_config_times": np.asarray(list(cfg.run.snap_times), dtype=float),
        "q_l_snapshots": q_l_snapshot_arr,
        "q_g_snapshots": q_g_snapshot_arr,
        "vertices_snapshots": vertices_snapshot_arr,
        **reduced_fields,
        "snapshots": snapshots,
        "q_l_initial": q_l_snapshots[0],
        "q_l_final": q_l_snapshots[-1],
        "q_g_initial": q_g_snapshots[0],
        "q_g_final": q_g_snapshots[-1],
        "vertices_initial": vertices_snapshots[0],
        "vertices_final": vertices_snapshots[-1],
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    metrics = results["metrics"]
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    cell_area = np.asarray(results["cell_area"], dtype=float)
    times = np.asarray(results["times"], dtype=float)
    amplitude = np.asarray(results["amplitude"], dtype=float)
    exact_amplitude = np.asarray(results["exact_amplitude"], dtype=float)
    energy_drift = np.asarray(results["relative_energy_drift"], dtype=float)
    residual_l2 = np.asarray(results["q_residual_l2"], dtype=float)
    vertices_initial = np.asarray(results["vertices_initial"], dtype=float)
    vertices_final = np.asarray(results["vertices_final"], dtype=float)

    fig, axes = plt.subplots(2, 3, figsize=(11.8, 7.1), constrained_layout=True)
    fields = (
        ("q_l initial / |C|", np.asarray(results["q_l_initial"], dtype=float) / cell_area),
        ("q_l final / |C|", np.asarray(results["q_l_final"], dtype=float) / cell_area),
        ("q_g final / |C|", np.asarray(results["q_g_final"], dtype=float) / cell_area),
    )
    for ax, (title, field) in zip(axes[0], fields):
        mesh = ax.pcolormesh(
            x_edges,
            y_edges,
            field.T,
            shading="auto",
            cmap="viridis",
            vmin=0.0,
            vmax=1.0,
        )
        ax.plot(
            np.r_[vertices_initial[:, 0], vertices_initial[0, 0]],
            np.r_[vertices_initial[:, 1], vertices_initial[0, 1]],
            color="white",
            lw=1.0,
            linestyle=":",
        )
        ax.plot(
            np.r_[vertices_final[:, 0], vertices_final[0, 0]],
            np.r_[vertices_final[:, 1], vertices_final[0, 1]],
            color="black",
            lw=0.9,
        )
        ax.set_title(title)
        ax.set_aspect("equal")
        fig.colorbar(mesh, ax=ax, shrink=0.82)

    ax = axes[1, 0]
    amplitude_scale = max(abs(float(amplitude[0])), 1.0e-30)
    ax.plot(
        times,
        amplitude / amplitude_scale,
        color=COLORS[0],
        marker="o",
        label="PhaseRegion closed chart",
    )
    ax.plot(
        times,
        exact_amplitude / amplitude_scale,
        color="black",
        linestyle=":",
        label="linear exact",
    )
    ax.set_title("mode amplitude / A0")
    ax.set_xlabel("t")
    ax.ticklabel_format(axis="y", useOffset=False)
    ax.legend(loc="best")

    ax = axes[1, 1]
    ax.semilogy(times, np.maximum(energy_drift, 1.0e-30), color=COLORS[1], marker="o")
    ax.semilogy(times, np.maximum(residual_l2, 1.0e-30), color=COLORS[2], marker="s")
    ax.set_title("energy drift and q residual")
    ax.set_xlabel("t")
    ax.legend(("relative energy drift", "q residual L2"), loc="best")

    axes[1, 2].axis("off")
    axes[1, 2].text(
        0.0,
        1.0,
        "\n".join(
            (
                "PhaseRegion droplet few-step",
                f"steps = {int(metrics['steps'])}",
                f"t/T = {float(metrics['t_over_T']):.8e}",
                f"max |A-A_exact| = {float(metrics['max_amplitude_error']):.8e}",
                f"max |V-V_exact| = {float(metrics['max_velocity_error']):.8e}",
                f"max energy drift = {float(metrics['max_energy_drift']):.8e}",
                f"max residual L2 = {float(metrics['max_residual_l2']):.8e}",
                f"max volume drift = {float(metrics['max_volume_drift']):.8e}",
                f"max raw q closure = {float(metrics['max_q_volume_closure_raw_abs']):.8e}",
                f"max step wall = {float(metrics['max_step_wall_seconds']):.8e}s",
                "phase_region_droplet_steps_admitted = 1",
                "force_admissible = 0",
            )
        ),
        va="top",
        ha="left",
        family="monospace",
        fontsize=8.0,
    )
    save_figure(fig, OUT / "phase_region_oscillating_droplet_steps")
    plt.close(fig)
    return (OUT / "phase_region_oscillating_droplet_steps").with_suffix(".pdf")


def _ensure_snapshot_dicts(results: dict[str, object]) -> dict[str, object]:
    """Attach plot-factory snapshot dictionaries from stored reduced fields."""
    existing = results.get("snapshots")
    if isinstance(existing, list):
        return results
    out = dict(results)
    snapshot_times = np.asarray(out["snapshot_times"], dtype=float)
    x_edges = np.asarray(out["x_edges"], dtype=float)
    y_edges = np.asarray(out["y_edges"], dtype=float)
    snapshots = []
    for index, snap_time in enumerate(snapshot_times):
        snapshots.append(
            {
                "t": float(snap_time),
                "psi": np.asarray(out["psi_snapshots"], dtype=float)[index],
                "phi": np.asarray(out["phi_snapshots"], dtype=float)[index],
                "u": np.asarray(out["u_snapshots"], dtype=float)[index],
                "v": np.asarray(out["v_snapshots"], dtype=float)[index],
                "p": np.asarray(out["pressure_snapshots"], dtype=float)[index],
                "rho": np.asarray(out["rho_snapshots"], dtype=float)[index],
                "grid_coords": [x_edges, y_edges],
            }
        )
    out["snapshots"] = snapshots
    return out


def _plot_yaml_snapshots(results: dict[str, object]) -> pathlib.Path:
    """Render closed-chart phase measures at YAML-configured output times."""
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    cell_area = np.asarray(results["cell_area"], dtype=float)
    snapshot_times = np.asarray(results["snapshot_times"], dtype=float)
    period = float(results["metrics"]["period"])
    q_l = np.asarray(results["q_l_snapshots"], dtype=float) / cell_area[None, ...]
    q_g = np.asarray(results["q_g_snapshots"], dtype=float) / cell_area[None, ...]
    vertices = np.asarray(results["vertices_snapshots"], dtype=float)

    count = int(snapshot_times.size)
    fig, axes = plt.subplots(
        2,
        count,
        figsize=(2.35 * count, 4.55),
        constrained_layout=True,
        squeeze=False,
    )
    for col in range(count):
        label = f"t/T={snapshot_times[col] / period:.2f}"
        curve = vertices[col]
        curve_x = np.r_[curve[:, 0], curve[0, 0]]
        curve_y = np.r_[curve[:, 1], curve[0, 1]]
        for row, (name, fields) in enumerate((("q_l / |C|", q_l), ("q_g / |C|", q_g))):
            ax = axes[row, col]
            mesh = ax.pcolormesh(
                x_edges,
                y_edges,
                fields[col].T,
                shading="auto",
                cmap="viridis",
                vmin=0.0,
                vmax=1.0,
            )
            ax.plot(curve_x, curve_y, color="white" if row == 0 else "black", lw=0.85)
            ax.set_title(f"{name}\n{label}", fontsize=8.5)
            ax.set_aspect("equal")
            ax.tick_params(labelsize=7.0)
            if col == count - 1:
                fig.colorbar(mesh, ax=ax, shrink=0.78)
    save_figure(fig, OUT / "phase_region_oscillating_droplet_yaml_snapshots")
    plt.close(fig)
    return (OUT / "phase_region_oscillating_droplet_yaml_snapshots").with_suffix(".pdf")


def _generate_configured_figures(
    cfg: ExperimentConfig,
    results: dict[str, object],
) -> None:
    known_types = {"time_series", "snapshot_series"}
    figure_specs = [
        spec for spec in cfg.output.figures if str(spec.get("type", "")) in known_types
    ]
    if not figure_specs:
        return
    figure_cfg = replace(cfg, output=replace(cfg.output, figures=figure_specs))
    generate_figures(figure_cfg, results, OUT)


def main() -> None:
    parser = experiment_argparser("Ch14 PhaseRegion oscillating droplet few-step experiment")
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--theta-count", type=int, default=192)
    parser.add_argument("--mode", type=int, default=2)
    parser.add_argument("--reference-amplitude-tolerance", type=float, default=5.0e-10)
    parser.add_argument("--reference-velocity-tolerance", type=float, default=5.0e-8)
    parser.add_argument("--energy-drift-tolerance", type=float, default=2.0e-5)
    parser.add_argument("--residual-tolerance", type=float, default=1.0e-18)
    parser.add_argument("--volume-tolerance", type=float, default=1.0e-10)
    parser.add_argument("--capacity-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--stiffness-probe-fraction", type=float, default=1.0e-2)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(
            pathlib.Path(args.config),
            steps=None if args.steps is None else int(args.steps),
            dt=None if args.dt is None else float(args.dt),
            theta_count=int(args.theta_count),
            mode=int(args.mode),
            reference_amplitude_tolerance=float(args.reference_amplitude_tolerance),
            reference_velocity_tolerance=float(args.reference_velocity_tolerance),
            energy_drift_tolerance=float(args.energy_drift_tolerance),
            residual_tolerance=float(args.residual_tolerance),
            volume_tolerance=float(args.volume_tolerance),
            capacity_tolerance=float(args.capacity_tolerance),
            stiffness_probe_fraction=float(args.stiffness_probe_fraction),
        )
        save_results(NPZ, results)
    results = _ensure_snapshot_dicts(results)
    cfg, _route = _load_phase_region_droplet_config(pathlib.Path(args.config))
    _generate_configured_figures(cfg, results)
    pdf = _plot(results)
    snapshots_pdf = _plot_yaml_snapshots(results)
    metrics = results["metrics"]
    print(
        "PHASE_REGION_OSCILLATING_DROPLET_STEPS "
        f"phase_region_droplet_steps_admitted={float(metrics['phase_region_droplet_steps_admitted']):.1f} "
        f"steps={int(metrics['steps'])} "
        f"dt={float(metrics['dt']):.12e} "
        f"t_final={float(metrics['t_final']):.12e} "
        f"t_over_T={float(metrics['t_over_T']):.12e} "
        f"dt_cfl_limit={float(metrics['dt_cfl_limit']):.12e} "
        f"max_amplitude_error={float(metrics['max_amplitude_error']):.12e} "
        f"max_velocity_error={float(metrics['max_velocity_error']):.12e} "
        f"max_energy_drift={float(metrics['max_energy_drift']):.12e} "
        f"max_residual_l2={float(metrics['max_residual_l2']):.12e} "
        f"max_volume_drift={float(metrics['max_volume_drift']):.12e} "
        f"max_q_volume_closure_raw_abs={float(metrics['max_q_volume_closure_raw_abs']):.12e} "
        f"max_q_volume_closure_closed_abs={float(metrics['max_q_volume_closure_closed_abs']):.12e} "
        f"max_step_wall_seconds={float(metrics['max_step_wall_seconds']):.12e} "
        f"final_amplitude={float(metrics['final_amplitude']):.12e} "
        f"final_exact_amplitude={float(metrics['final_exact_amplitude']):.12e} "
        f"force_admissible={float(metrics['force_admissible']):.1f} "
        f"pdf={pdf} "
        f"snapshots_pdf={snapshots_pdf}"
    )


if __name__ == "__main__":
    main()
