#!/usr/bin/env python3
"""Few-step PhaseRegion graph-chart capillary-wave experiment.

A3 mapping
----------
Equation:
    Own the gas phase region ``Omega_g={y>eta(x)}`` and graph boundary
    ``Gamma_h``.  The graph energy is
    ``E_h[eta]=sigma sum_i sqrt(dx_i^2 + (eta_{i+1}-eta_i)^2)``.  For the
    first dynamic gate, restrict ``eta`` to the Ch14 capillary-wave mode and
    use the second variation ``K_h=d^2E_h/dA^2`` plus the rigid-wall two-layer
    dispersion relation to define the modal mass
    ``M_mode = K_h / omega^2``.
Discretization:
    Step the single graph amplitude with velocity-Verlet under the linearized
    variational force ``-K_h A``.  At every step, rebuild ``q_l=Q_h(eta)``, map
    to the PhaseRegion gas owner ``q_g=|C|-q_l``, assemble a ``GAS_ABOVE`` graph
    ``PhaseRegionBatch``, and check residual, volume, symmetry, energy drift,
    and the linear exact capillary-wave reference.
Code:
    This is a fixed-grid reduced graph-chart experiment.  It does not connect a
    face cochain to the Navier--Stokes runtime, run pressure projection, skip a
    production rebuild, add damping/smoothing, or change CFL/tolerances.
"""

from __future__ import annotations

from copy import deepcopy
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
    component_offsets_from_batch_ids,
    enum_values,
    graph_q_from_eta,
    graph_q_from_eta_column_integral,
    graph_segment_energy_gradient,
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

CONFIG = ROOT / "experiment/ch14/config/ch14_capillary.yaml"
DEFAULT_STEPS = 8
DEFAULT_DT = 2.0e-5
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


@dataclass(frozen=True)
class ModalGeometry:
    """Fixed graph modal basis and effective capillary-wave mass."""

    basis_nodes: np.ndarray
    basis_unique: np.ndarray
    basis_cell: np.ndarray
    basis_mean: float
    stiffness: float
    omega: float
    mass: float
    period: float


def _wave_from_config(cfg: ExperimentConfig) -> CapillaryWaveSpec:
    objects = tuple(cfg.initial_condition.get("objects", ()))
    if len(objects) != 1 or objects[0].get("type") != "capillary_wave":
        raise ValueError("capillary graph steps expects one capillary_wave object")
    obj = objects[0]
    if obj.get("axis") != "y":
        raise ValueError("capillary graph steps expects a y-axis graph")
    if obj.get("interior_phase") != "liquid":
        raise ValueError("capillary graph steps expects liquid below the graph")
    return CapillaryWaveSpec(
        mean=float(obj["mean"]),
        amplitude=float(obj["amplitude"]),
        mode=int(obj["mode"]),
        length=float(obj["length"]),
        phase=float(obj.get("phase", 0.0)),
    )


def _load_phase_region_graph_config(
    config_path: pathlib.Path,
) -> tuple[ExperimentConfig, dict[str, Any]]:
    """Load a full or wrapper YAML for the PhaseRegion graph route."""
    yaml = require_pyyaml()
    with pathlib.Path(config_path).open() as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict):
        raise ValueError("PhaseRegion graph config must be a YAML mapping")

    if "base_config" in raw:
        base_path = pathlib.Path(str(raw["base_config"]))
        if not base_path.is_absolute():
            base_path = pathlib.Path(config_path).parent / base_path
        with base_path.open() as fh:
            merged = yaml.safe_load(fh) or {}
        if not isinstance(merged, dict):
            raise ValueError("PhaseRegion graph base_config must be a YAML mapping")
        merged = deepcopy(merged)
        for key in (
            "experiment",
            "grid",
            "interface",
            "physics",
            "run",
            "numerics",
            "output",
            "diagnostics",
            "initial_condition",
            "initial_velocity",
            "boundary_condition",
        ):
            if key in raw:
                merged[key] = deepcopy(raw[key])
        cfg = ExperimentConfig.from_dict(merged)
        route = raw.get("phase_region_graph", {})
    else:
        cfg = ExperimentConfig.from_yaml(config_path)
        route = raw.get("phase_region_graph", {})
    if route is None:
        route = {}
    if not isinstance(route, dict):
        raise ValueError("phase_region_graph section must be a YAML mapping")
    return cfg, dict(route)


def _route_section(route: dict[str, Any], name: str) -> dict[str, Any]:
    section = route.get(name, {})
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(f"phase_region_graph.{name} must be a YAML mapping")
    return dict(section)


def _use_gpu_from_route(cli_use_gpu: bool | None, route: dict[str, Any]) -> bool:
    if cli_use_gpu is not None:
        return bool(cli_use_gpu)
    backend = _route_section(route, "backend")
    return bool(backend.get("use_gpu", False))


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
        raise ValueError("--steps or phase_region_graph.run.steps must be positive")
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
        raise ValueError("--dt or phase_region_graph.run.dt must be positive and finite")
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


def _grid_from_config(cfg: ExperimentConfig, *, use_gpu: bool = False) -> Grid:
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
        Backend(use_gpu=bool(use_gpu)),
    )
    grid.set_boundary_type(g.bc_type)
    return grid


def _phi_for_eta(grid: Grid, eta_nodes: np.ndarray) -> np.ndarray:
    _x, y = np.meshgrid(
        np.asarray(grid.coords[0], dtype=float),
        np.asarray(grid.coords[1], dtype=float),
        indexing="ij",
    )
    return y - np.asarray(eta_nodes, dtype=float).reshape((-1, 1))


def _initial_eta(x_edges: np.ndarray, spec: CapillaryWaveSpec) -> np.ndarray:
    eta = float(spec.mean) + float(spec.amplitude) * np.cos(
        2.0 * np.pi * int(spec.mode) * x_edges / float(spec.length) + float(spec.phase)
    )
    eta[-1] = eta[0]
    return eta


def _fit_grid_to_initial_graph(
    cfg: ExperimentConfig,
    spec: CapillaryWaveSpec,
    *,
    use_gpu: bool = False,
) -> Grid:
    if bool(use_gpu):
        step_backend = Backend(use_gpu=True)
        grid = _grid_from_config(cfg, use_gpu=False)
    else:
        step_backend = None
        grid = _grid_from_config(cfg, use_gpu=False)
    if float(cfg.grid.alpha_grid) <= 1.0:
        if step_backend is not None:
            _attach_step_backend(grid, step_backend)
        return grid
    eps = float(cfg.grid.eps_factor) * (float(cfg.grid.LX) / float(cfg.grid.NX))
    eta_uniform = _initial_eta(np.asarray(grid.coords[0], dtype=float), spec)
    psi_uniform = heaviside(np, -_phi_for_eta(grid, eta_uniform), eps)
    ccd = CCDSolver(grid, grid.backend, bc_type=cfg.grid.bc_type)
    grid.update_from_levelset(psi_uniform, eps, ccd=ccd)
    if step_backend is not None:
        _attach_step_backend(grid, step_backend)
    return grid


def _attach_step_backend(grid: Grid, backend: Backend) -> None:
    grid.backend = backend
    grid.xp = backend.xp
    grid._device_coord_cache.clear()
    grid._device_cell_width_cache.clear()
    grid._device_metric_cache.clear()
    grid._device_metric_gradient_cache.clear()


def _cell_area(grid: Grid, *, device: bool = False):
    if bool(device):
        dx = grid.device_cell_widths(0, dtype=float)
        dy = grid.device_cell_widths(1, dtype=float)
        return dx[:, None] * dy[None, :]
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


def _dispersion_omega(cfg: ExperimentConfig, spec: CapillaryWaveSpec) -> float:
    k = 2.0 * np.pi * int(spec.mode) / float(spec.length)
    lower = 0.0
    upper = float(cfg.grid.LY)
    h_l = float(spec.mean) - lower
    h_g = upper - float(spec.mean)
    if h_l <= 0.0 or h_g <= 0.0:
        raise ValueError("capillary graph mean must stay between the y walls")
    rho_l = float(cfg.physics.rho_l)
    rho_g = float(cfg.physics.rho_g)
    sigma = float(cfg.physics.sigma)
    denominator = rho_l / np.tanh(k * h_l) + rho_g / np.tanh(k * h_g)
    return float(np.sqrt(sigma * k * k * k / denominator))


def _modal_geometry(
    cfg: ExperimentConfig,
    spec: CapillaryWaveSpec,
    x_edges: np.ndarray,
    *,
    stiffness_probe_fraction: float,
) -> ModalGeometry:
    dx = np.diff(np.asarray(x_edges, dtype=float))
    raw_nodes = np.cos(
        2.0 * np.pi * int(spec.mode) * x_edges / float(spec.length) + float(spec.phase)
    )
    raw_nodes[-1] = raw_nodes[0]
    raw_cell = 0.5 * (raw_nodes[:-1] + raw_nodes[1:])
    basis_mean = float(np.sum(dx * raw_cell) / np.sum(dx))
    basis_nodes = raw_nodes - basis_mean
    basis_nodes[-1] = basis_nodes[0]
    basis_cell = 0.5 * (basis_nodes[:-1] + basis_nodes[1:])
    if abs(float(np.sum(dx * basis_cell))) > 5.0e-18:
        raise AssertionError("volume-corrected graph basis is not volume-free")

    sigma = float(cfg.physics.sigma)
    probe = max(float(stiffness_probe_fraction) * abs(float(spec.amplitude)), 1.0e-9)
    zero = _eta_from_amplitude(spec, basis_nodes, amplitude=0.0)
    plus = _eta_from_amplitude(spec, basis_nodes, amplitude=probe)
    minus = _eta_from_amplitude(spec, basis_nodes, amplitude=-probe)
    e0 = float(graph_segment_energy_gradient(x_edges, zero, sigma=sigma).energy)
    ep = float(graph_segment_energy_gradient(x_edges, plus, sigma=sigma).energy)
    em = float(graph_segment_energy_gradient(x_edges, minus, sigma=sigma).energy)
    stiffness = float((ep - 2.0 * e0 + em) / (probe * probe))
    if not np.isfinite(stiffness) or stiffness <= 0.0:
        raise AssertionError("graph modal stiffness must be positive")
    omega = _dispersion_omega(cfg, spec)
    mass = stiffness / (omega * omega)
    return ModalGeometry(
        basis_nodes=basis_nodes,
        basis_unique=basis_nodes[:-1],
        basis_cell=basis_cell,
        basis_mean=basis_mean,
        stiffness=stiffness,
        omega=omega,
        mass=float(mass),
        period=float(2.0 * np.pi / omega),
    )


def _eta_from_amplitude(
    spec: CapillaryWaveSpec,
    basis_nodes: np.ndarray,
    *,
    amplitude: float,
) -> np.ndarray:
    eta = float(spec.mean) + float(amplitude) * np.asarray(basis_nodes, dtype=float)
    eta[-1] = eta[0]
    return eta


def _surface_energy_and_linear_rate(
    x_edges: np.ndarray,
    spec: CapillaryWaveSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
    sigma: float,
) -> tuple[float, float]:
    eta = _eta_from_amplitude(spec, modal.basis_nodes, amplitude=float(amplitude))
    energy = graph_segment_energy_gradient(x_edges, eta, sigma=float(sigma))
    rate = float(modal.stiffness) * float(amplitude)
    return float(energy.energy), rate


def _step_verlet(
    x_edges: np.ndarray,
    spec: CapillaryWaveSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
    velocity: float,
    dt: float,
    sigma: float,
) -> tuple[float, float]:
    _surface_energy, rate = _surface_energy_and_linear_rate(
        x_edges,
        spec,
        modal,
        amplitude=float(amplitude),
        sigma=float(sigma),
    )
    half_velocity = float(velocity) - 0.5 * float(dt) * rate / float(modal.mass)
    new_amplitude = float(amplitude) + float(dt) * half_velocity
    _new_surface_energy, new_rate = _surface_energy_and_linear_rate(
        x_edges,
        spec,
        modal,
        amplitude=new_amplitude,
        sigma=float(sigma),
    )
    new_velocity = half_velocity - 0.5 * float(dt) * new_rate / float(modal.mass)
    return new_amplitude, new_velocity


def _measure_phase_region(
    grid: Grid,
    x_edges: np.ndarray,
    spec: CapillaryWaveSpec,
    modal: ModalGeometry,
    *,
    amplitude: float,
    cell_area: np.ndarray,
    sigma: float,
    use_fast_graph_q: bool,
) -> dict[str, object]:
    eta = _eta_from_amplitude(spec, modal.basis_nodes, amplitude=float(amplitude))
    if bool(use_fast_graph_q):
        q_l = graph_q_from_eta_column_integral(
            grid,
            grid.backend.xp.asarray(eta),
        ).q
    else:
        q_l = np.asarray(graph_q_from_eta(grid, eta).q, dtype=float)
    owner = map_cell_measure_to_phase_owner(
        q_l,
        cell_area,
        source_phase=CellMeasurePhase.LIQUID,
        owner_phase=CellMeasurePhase.GAS,
    )
    q_g = owner.q_owner
    q_g_host = np.asarray(grid.backend.to_host(q_g), dtype=float)
    region = _region_from_graph_gas_above(
        x_edges=x_edges,
        eta_nodes=eta,
        q_g_phys=q_g_host,
    )
    energy = graph_segment_energy_gradient(x_edges, eta, sigma=float(sigma))
    measurement = assemble_phase_region_measurement(
        region,
        q_g[None, ...],
        np.array((float(energy.energy) / float(sigma),), dtype=float),
        q_target=owner.q_owner,
        cell_area=cell_area,
    )
    if measurement.residual is None:
        raise AssertionError("PhaseRegion graph step did not assemble residual")
    return {
        "eta": eta,
        "q_l": np.asarray(grid.backend.to_host(q_l), dtype=float),
        "q_g": q_g_host,
        "residual_l2": float(measurement.residual_l2),
        "residual_linf": float(measurement.residual_linf),
        "residual_volume_abs": abs(grid.backend.to_scalar(measurement.residual_volume[0])),
        "gas_volume": grid.backend.to_scalar(measurement.batch_volumes[0]),
        "liquid_volume": grid.backend.to_scalar(grid.backend.xp.sum(q_l)),
        "perimeter": grid.backend.to_scalar(measurement.batch_perimeters[0]),
    }


def _reduced_graph_snapshot_fields(
    cfg: ExperimentConfig,
    spec: CapillaryWaveSpec,
    modal: ModalGeometry,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    amplitudes: np.ndarray,
    velocities: np.ndarray,
    snapshot_indices: np.ndarray,
) -> dict[str, np.ndarray]:
    x_nodes = np.asarray(x_edges, dtype=float)
    y_nodes = np.asarray(y_edges, dtype=float)
    k = 2.0 * np.pi * int(spec.mode) / float(spec.length)
    phase = k * x_nodes + float(spec.phase)
    cosx = np.cos(phase)[:, None]
    sinx = np.sin(phase)[:, None]
    h_l = float(spec.mean)
    h_g = float(cfg.grid.LY) - float(spec.mean)
    if h_l <= 0.0 or h_g <= 0.0:
        raise ValueError("capillary graph diagnostic fields require positive layer depths")
    liquid_u_shape = np.cosh(k * y_nodes)[None, :] / np.sinh(k * h_l)
    liquid_v_shape = np.sinh(k * y_nodes)[None, :] / np.sinh(k * h_l)
    gas_y = float(cfg.grid.LY) - y_nodes
    gas_u_shape = np.cosh(k * gas_y)[None, :] / np.sinh(k * h_g)
    gas_v_shape = np.sinh(k * gas_y)[None, :] / np.sinh(k * h_g)
    phi_snapshots = []
    u_snapshots = []
    v_snapshots = []
    pressure_snapshots = []
    rho_snapshots = []
    psi_snapshots = []
    for out_index, step_index in enumerate(np.asarray(snapshot_indices, dtype=int)):
        amplitude = float(amplitudes[step_index])
        modal_velocity = float(velocities[step_index])
        modal_acceleration = -float(modal.omega) ** 2 * amplitude
        eta_nodes = _eta_from_amplitude(spec, modal.basis_nodes, amplitude=amplitude)
        phi = y_nodes[None, :] - eta_nodes[:, None]
        psi = (phi <= 0.0).astype(float)

        u_l = -modal_velocity * sinx * liquid_u_shape
        v_l = modal_velocity * cosx * liquid_v_shape
        u_g = modal_velocity * sinx * gas_u_shape
        v_g = modal_velocity * cosx * gas_v_shape
        p_l = -float(cfg.physics.rho_l) * modal_acceleration / k * cosx * liquid_u_shape
        p_g = float(cfg.physics.rho_g) * modal_acceleration / k * cosx * gas_u_shape

        liquid_fraction = psi
        gas_fraction = 1.0 - liquid_fraction
        psi_snapshots.append(psi)
        phi_snapshots.append(phi)
        u_snapshots.append(liquid_fraction * u_l + gas_fraction * u_g)
        v_snapshots.append(liquid_fraction * v_l + gas_fraction * v_g)
        pressure_snapshots.append(liquid_fraction * p_l + gas_fraction * p_g)
        rho_snapshots.append(
            liquid_fraction * float(cfg.physics.rho_l)
            + gas_fraction * float(cfg.physics.rho_g)
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
    reference_amplitude_tolerance: float,
    reference_velocity_tolerance: float,
    energy_drift_tolerance: float,
    residual_tolerance: float,
    volume_tolerance: float,
    stiffness_probe_fraction: float,
    use_gpu: bool | None,
) -> dict[str, object]:
    cfg, route = _load_phase_region_graph_config(config_path)
    spec = _wave_from_config(cfg)
    route_use_gpu = _use_gpu_from_route(use_gpu, route)
    grid = _fit_grid_to_initial_graph(cfg, spec, use_gpu=route_use_gpu)
    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    cell_area = _cell_area(grid, device=route_use_gpu)
    modal = _modal_geometry(
        cfg,
        spec,
        x_edges,
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

    amplitude = float(spec.amplitude)
    velocity = 0.0
    times = [0.0]
    amplitudes = [amplitude]
    velocities = [velocity]
    energies = []
    q_residual_l2 = []
    q_residual_linf = []
    q_residual_volume = []
    gas_volumes = []
    liquid_volumes = []
    perimeters = []
    q_l_snapshots = []
    q_g_snapshots = []
    eta_snapshots = []
    step_wall_times = []

    sigma = float(cfg.physics.sigma)
    surface_energies = []
    for step_index in range(step_count + 1):
        _synchronize_backend(grid.backend)
        step_wall_start = time.perf_counter()
        measurement = _measure_phase_region(
            grid,
            x_edges,
            spec,
            modal,
            amplitude=amplitude,
            cell_area=cell_area,
            sigma=sigma,
            use_fast_graph_q=route_use_gpu,
        )
        surface_energy, _rate = _surface_energy_and_linear_rate(
            x_edges,
            spec,
            modal,
            amplitude=amplitude,
            sigma=sigma,
        )
        total_energy = (
            0.5 * float(modal.stiffness) * amplitude * amplitude
            + 0.5 * float(modal.mass) * velocity * velocity
        )
        surface_energies.append(float(surface_energy))
        energies.append(total_energy)
        q_residual_l2.append(float(measurement["residual_l2"]))
        q_residual_linf.append(float(measurement["residual_linf"]))
        q_residual_volume.append(float(measurement["residual_volume_abs"]))
        gas_volumes.append(float(measurement["gas_volume"]))
        liquid_volumes.append(float(measurement["liquid_volume"]))
        perimeters.append(float(measurement["perimeter"]))
        if step_index in snapshot_index_set:
            q_l_snapshots.append(np.asarray(measurement["q_l"], dtype=float))
            q_g_snapshots.append(np.asarray(measurement["q_g"], dtype=float))
            eta_snapshots.append(np.asarray(measurement["eta"], dtype=float))
        if step_index == step_count:
            _synchronize_backend(grid.backend)
            step_wall_times.append(time.perf_counter() - step_wall_start)
            break
        amplitude, velocity = _step_verlet(
            x_edges,
            spec,
            modal,
            amplitude=amplitude,
            velocity=velocity,
            dt=dt_value,
            sigma=sigma,
        )
        _synchronize_backend(grid.backend)
        step_wall_times.append(time.perf_counter() - step_wall_start)
        times.append((step_index + 1) * dt_value)
        amplitudes.append(amplitude)
        velocities.append(velocity)

    times_arr = np.asarray(times, dtype=float)
    amplitudes_arr = np.asarray(amplitudes, dtype=float)
    velocities_arr = np.asarray(velocities, dtype=float)
    energy_arr = np.asarray(energies, dtype=float)
    kinetic_energy = 0.5 * float(modal.mass) * velocities_arr * velocities_arr
    exact_amplitude = float(spec.amplitude) * np.cos(float(modal.omega) * times_arr)
    exact_velocity = -float(spec.amplitude) * float(modal.omega) * np.sin(
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

    if float(np.max(amplitude_error)) > float(reference_amplitude_tolerance):
        raise AssertionError("PhaseRegion graph steps exceed amplitude reference tolerance")
    if float(np.max(velocity_error)) > float(reference_velocity_tolerance):
        raise AssertionError("PhaseRegion graph steps exceed velocity reference tolerance")
    if float(np.max(energy_drift)) > float(energy_drift_tolerance):
        raise AssertionError("PhaseRegion graph steps exceed energy drift tolerance")
    if float(np.max(q_residual_l2)) > float(residual_tolerance):
        raise AssertionError("PhaseRegion graph steps produced nonzero residual")
    if float(np.max(volume_drift)) > float(volume_tolerance):
        raise AssertionError("PhaseRegion graph steps changed phase volume")

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
        "basis_mean": float(modal.basis_mean),
        "max_amplitude_error": float(np.max(amplitude_error)),
        "max_velocity_error": float(np.max(velocity_error)),
        "max_energy_drift": float(np.max(energy_drift)),
        "max_residual_l2": float(np.max(q_residual_l2)),
        "max_residual_linf": float(np.max(q_residual_linf)),
        "max_residual_volume_abs": float(np.max(q_residual_volume)),
        "max_volume_drift": float(np.max(volume_drift)),
        "final_amplitude": float(amplitudes_arr[-1]),
        "final_exact_amplitude": float(exact_amplitude[-1]),
        "final_velocity": float(velocities_arr[-1]),
        "final_exact_velocity": float(exact_velocity[-1]),
        "initial_energy": float(energy_arr[0]),
        "final_energy": float(energy_arr[-1]),
        "grid_alpha": float(cfg.grid.alpha_grid),
        "min_dx": float(np.min(np.diff(x_edges))),
        "min_dy": float(np.min(np.diff(y_edges))),
        "phase_region_graph_steps_admitted": 1.0,
        "force_admissible": 0.0,
        "step_backend_gpu": 1.0 if grid.backend.is_gpu() else 0.0,
        "q_measurement_fast_column_integral": 1.0 if route_use_gpu else 0.0,
        "mean_step_wall_seconds": float(np.mean(step_wall_times)),
        "max_step_wall_seconds": float(np.max(step_wall_times)),
        "target_step_wall_seconds": 2.0e-1,
        "target_met": 1.0 if float(np.max(step_wall_times)) <= 2.0e-1 else 0.0,
    }
    q_l_snapshot_arr = np.stack(q_l_snapshots, axis=0)
    q_g_snapshot_arr = np.stack(q_g_snapshots, axis=0)
    eta_snapshot_arr = np.stack(eta_snapshots, axis=0)
    reduced_fields = _reduced_graph_snapshot_fields(
        cfg,
        spec,
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
    initial_volume = max(float(gas_volumes_arr[0] + liquid_volumes_arr[0]), 1.0e-30)
    return {
        "metrics": metrics,
        "times": times_arr,
        "amplitude": amplitudes_arr,
        "signed_interface_amplitude": amplitudes_arr,
        "velocity": velocities_arr,
        "exact_amplitude": exact_amplitude,
        "exact_velocity": exact_velocity,
        "kinetic_energy": kinetic_energy,
        "total_energy": energy_arr,
        "surface_energy": np.asarray(surface_energies, dtype=float),
        "relative_energy_drift": energy_drift,
        "volume_conservation": volume_drift / initial_volume,
        "q_residual_l2": np.asarray(q_residual_l2, dtype=float),
        "q_residual_linf": np.asarray(q_residual_linf, dtype=float),
        "volume_drift": volume_drift,
        "x_edges": x_edges,
        "y_edges": y_edges,
        "cell_area": np.asarray(grid.backend.to_host(cell_area), dtype=float),
        "snapshot_indices": snapshot_indices,
        "snapshot_times": times_arr[snapshot_indices],
        "snapshot_config_times": np.asarray(list(cfg.run.snap_times), dtype=float),
        "q_l_snapshots": q_l_snapshot_arr,
        "q_g_snapshots": q_g_snapshot_arr,
        "eta_snapshots": eta_snapshot_arr,
        **reduced_fields,
        "snapshots": snapshots,
        "q_l_initial": q_l_snapshots[0],
        "q_l_final": q_l_snapshots[-1],
        "q_g_initial": q_g_snapshots[0],
        "q_g_final": q_g_snapshots[-1],
        "eta_initial": eta_snapshots[0],
        "eta_final": eta_snapshots[-1],
    }


def _synchronize_backend(backend: Backend) -> None:
    if backend.is_gpu():
        backend.xp.cuda.Stream.null.synchronize()


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
    eta_initial = np.asarray(results["eta_initial"], dtype=float)
    eta_final = np.asarray(results["eta_final"], dtype=float)

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
        ax.plot(x_edges, eta_initial, color="white", lw=0.8, linestyle=":")
        ax.plot(x_edges, eta_final, color="black", lw=0.8)
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
        label="PhaseRegion graph",
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
                "PhaseRegion graph few-step",
                f"steps = {int(metrics['steps'])}",
                f"t/T = {float(metrics['t_over_T']):.8e}",
                f"max |A-A_exact| = {float(metrics['max_amplitude_error']):.8e}",
                f"max |V-V_exact| = {float(metrics['max_velocity_error']):.8e}",
                f"max energy drift = {float(metrics['max_energy_drift']):.8e}",
                f"max residual L2 = {float(metrics['max_residual_l2']):.8e}",
                f"max volume drift = {float(metrics['max_volume_drift']):.8e}",
                f"max step wall = {float(metrics['max_step_wall_seconds']):.8e}s",
                "phase_region_graph_steps_admitted = 1",
                "force_admissible = 0",
            )
        ),
        va="top",
        ha="left",
        family="monospace",
        fontsize=8.0,
    )
    save_figure(fig, OUT / "phase_region_capillary_graph_steps")
    plt.close(fig)
    return (OUT / "phase_region_capillary_graph_steps").with_suffix(".pdf")


def _ensure_snapshot_dicts(results: dict[str, object]) -> dict[str, object]:
    """Attach plot-factory snapshot dictionaries from the stored field arrays."""
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
    """Render the PhaseRegion graph measure at YAML-configured output times."""
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    cell_area = np.asarray(results["cell_area"], dtype=float)
    snapshot_times = np.asarray(results["snapshot_times"], dtype=float)
    period = float(results["metrics"]["period"])
    q_l = np.asarray(results["q_l_snapshots"], dtype=float) / cell_area[None, ...]
    q_g = np.asarray(results["q_g_snapshots"], dtype=float) / cell_area[None, ...]
    eta = np.asarray(results["eta_snapshots"], dtype=float)

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
            ax.plot(x_edges, eta[col], color="white" if row == 0 else "black", lw=0.85)
            ax.set_title(f"{name}\n{label}", fontsize=8.5)
            ax.set_aspect("equal")
            ax.tick_params(labelsize=7.0)
            if col == count - 1:
                fig.colorbar(mesh, ax=ax, shrink=0.78)
    save_figure(fig, OUT / "phase_region_capillary_graph_yaml_snapshots")
    plt.close(fig)
    return (OUT / "phase_region_capillary_graph_yaml_snapshots").with_suffix(".pdf")


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
    parser = experiment_argparser("Ch14 PhaseRegion capillary graph few-step experiment")
    parser.add_argument("--config", default=str(CONFIG))
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--reference-amplitude-tolerance", type=float, default=5.0e-10)
    parser.add_argument("--reference-velocity-tolerance", type=float, default=5.0e-8)
    parser.add_argument("--energy-drift-tolerance", type=float, default=2.0e-5)
    parser.add_argument("--residual-tolerance", type=float, default=1.0e-18)
    parser.add_argument("--volume-tolerance", type=float, default=1.0e-16)
    parser.add_argument("--stiffness-probe-fraction", type=float, default=1.0e-2)
    parser.add_argument("--use-gpu", action="store_true", default=None)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(
            pathlib.Path(args.config),
            steps=None if args.steps is None else int(args.steps),
            dt=None if args.dt is None else float(args.dt),
            reference_amplitude_tolerance=float(args.reference_amplitude_tolerance),
            reference_velocity_tolerance=float(args.reference_velocity_tolerance),
            energy_drift_tolerance=float(args.energy_drift_tolerance),
            residual_tolerance=float(args.residual_tolerance),
            volume_tolerance=float(args.volume_tolerance),
            stiffness_probe_fraction=float(args.stiffness_probe_fraction),
            use_gpu=args.use_gpu,
        )
        save_results(NPZ, results)
    results = _ensure_snapshot_dicts(results)
    cfg, _route = _load_phase_region_graph_config(pathlib.Path(args.config))
    _generate_configured_figures(cfg, results)
    pdf = _plot(results)
    snapshots_pdf = _plot_yaml_snapshots(results)
    metrics = results["metrics"]
    print(
        "PHASE_REGION_CAPILLARY_GRAPH_STEPS "
        f"phase_region_graph_steps_admitted={float(metrics['phase_region_graph_steps_admitted']):.1f} "
        f"steps={int(metrics['steps'])} "
        f"dt={float(metrics['dt']):.12e} "
        f"t_final={float(metrics['t_final']):.12e} "
        f"t_over_T={float(metrics['t_over_T']):.12e} "
        f"max_amplitude_error={float(metrics['max_amplitude_error']):.12e} "
        f"max_velocity_error={float(metrics['max_velocity_error']):.12e} "
        f"max_energy_drift={float(metrics['max_energy_drift']):.12e} "
        f"max_residual_l2={float(metrics['max_residual_l2']):.12e} "
        f"max_volume_drift={float(metrics['max_volume_drift']):.12e} "
        f"max_step_wall_seconds={float(metrics['max_step_wall_seconds']):.12e} "
        f"target_met={float(metrics['target_met']):.1f} "
        f"final_amplitude={float(metrics['final_amplitude']):.12e} "
        f"final_exact_amplitude={float(metrics['final_exact_amplitude']):.12e} "
        f"force_admissible={float(metrics['force_admissible']):.1f} "
        f"pdf={pdf} "
        f"snapshots_pdf={snapshots_pdf}"
    )


if __name__ == "__main__":
    main()
