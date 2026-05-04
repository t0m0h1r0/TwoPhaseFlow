#!/usr/bin/env python3
"""Manufactured capillary-work gate for ch14 pressure-jump runs.

Symbol mapping
--------------
``E_Γ`` -> ``surface_energy``
``j_gl = p_g - p_l`` -> ``pressure_jump_gas_minus_liquid``
``B_Γ(j)`` -> ``signed_pressure_jump_gradient``
``P_Γ`` -> ``jump_power``

A3 chain
--------
Equation: ``d(E_K + σ|Γ|)/dt = -D`` and
``P_Γ = ∫_Γ j_gl V_lg dS = -d(σ|Γ|)/dt``
  -> Discretization: compare finite-difference changes of the configured
     discrete ``σ|Γ_h|`` with the pressure-jump face work used by the
     projection-native velocity state
  -> Code: configured variational trace energy plus
     ``signed_pressure_jump_gradient`` on the same cut faces as the PPE.
"""

from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from twophase.coupling.interface_stress_closure import (  # noqa: E402
    build_young_laplace_interface_stress_context,
    evaluate_interface_face_curvature_lg,
    signed_pressure_jump_gradient,
)
from twophase.coupling.transport_variational_capillary import (  # noqa: E402
    p2_trace_surface_energy_2d,
    p2_trace_surface_energy_gradient_2d,
)
from twophase.simulation.config_io import load_experiment_config  # noqa: E402
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver  # noqa: E402
from twophase.simulation.ns_step_state import NSStepRequest  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    save_figure,
    save_results,
)


@dataclass(frozen=True)
class WorkState:
    """Capillary-work state retained across one interface-advection step."""

    time: float
    surface_energy: float
    jump_power: float | None


@dataclass(frozen=True)
class TransportRates:
    """Surface-energy rates induced by the actual interface transport map."""

    transport_rate: float
    advection_rate: float
    transport_linear_rate: float
    advection_linear_rate: float
    variational_power: float


def _resolve_config(name: str) -> pathlib.Path:
    path = pathlib.Path(name)
    if path.exists():
        return path.resolve()
    config_dir = pathlib.Path(__file__).resolve().parent / "config"
    for candidate in (config_dir / name, config_dir / f"{name}.yaml"):
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"config not found: {name}")


def _host(backend, array) -> np.ndarray:
    return np.asarray(backend.to_host(array))


def _device_copy(backend, array):
    return backend.xp.array(array, copy=True)


def _surface_energy(solver, psi, *, sigma: float) -> float:
    if getattr(solver, "_curvature_method", "") == "transport_variational_p2":
        energy = p2_trace_surface_energy_2d(
            xp=solver.backend.xp,
            grid=solver._grid,
            psi=solver.backend.xp.asarray(psi),
            sigma=sigma,
        )
        return float(np.asarray(solver.backend.to_host(energy)))
    return float(
        sigma
        * _surface_length_from_psi(_host(solver.backend, psi), solver._grid.coords)
    )


def _surface_length_from_psi(psi, coords, *, threshold: float = 0.5) -> float:
    """Return a marching-squares length for the ``psi=threshold`` contour."""
    psi = np.asarray(psi, dtype=float)
    x = np.asarray(coords[0], dtype=float)
    y = np.asarray(coords[1], dtype=float)
    value_scale = max(float(np.max(np.abs(psi - threshold))), 1.0)
    value_tol = np.finfo(psi.dtype).eps * value_scale * 64.0
    coord_scale = max(float(np.max(x) - np.min(x)), float(np.max(y) - np.min(y)), 1.0)
    coord_tol = np.finfo(float).eps * coord_scale * 64.0
    total = 0.0

    def add_unique(points, point):
        for existing in points:
            if np.linalg.norm(np.asarray(existing) - np.asarray(point)) <= coord_tol:
                return
        points.append(point)

    def edge_point(p0, p1, q0, q1):
        denom = q1 - q0
        if abs(denom) <= value_tol:
            theta = 0.5
        else:
            theta = -q0 / denom
        theta = min(max(theta, 0.0), 1.0)
        return (1.0 - theta) * np.asarray(p0) + theta * np.asarray(p1)

    for i in range(x.size - 1):
        for j in range(y.size - 1):
            vertices = (
                np.asarray((x[i], y[j])),
                np.asarray((x[i + 1], y[j])),
                np.asarray((x[i + 1], y[j + 1])),
                np.asarray((x[i], y[j + 1])),
            )
            values = (
                psi[i, j] - threshold,
                psi[i + 1, j] - threshold,
                psi[i + 1, j + 1] - threshold,
                psi[i, j + 1] - threshold,
            )
            points: list[np.ndarray] = []
            for edge in range(4):
                q0 = values[edge]
                q1 = values[(edge + 1) % 4]
                p0 = vertices[edge]
                p1 = vertices[(edge + 1) % 4]
                if abs(q0) <= value_tol:
                    add_unique(points, p0)
                if q0 * q1 < 0.0:
                    add_unique(points, edge_point(p0, p1, q0, q1))
            if len(points) == 2:
                total += float(np.linalg.norm(points[1] - points[0]))
            elif len(points) == 4:
                centre = sum(points) / 4.0
                ordered = sorted(
                    points,
                    key=lambda p: np.arctan2(float(p[1] - centre[1]), float(p[0] - centre[0])),
                )
                total += float(np.linalg.norm(ordered[1] - ordered[0]))
                total += float(np.linalg.norm(ordered[3] - ordered[2]))
    return total


def _edge_crossing_with_derivatives(
    values: list[float],
    points: list[np.ndarray],
    a: int,
    b: int,
    *,
    threshold: float,
):
    value_a = values[a] - threshold
    value_b = values[b] - threshold
    if value_a * value_b >= 0.0:
        return None
    denominator = values[b] - values[a]
    theta = (threshold - values[a]) / denominator
    point = (1.0 - theta) * points[a] + theta * points[b]
    dtheta_da = (threshold - values[b]) / (denominator * denominator)
    dtheta_db = -(threshold - values[a]) / (denominator * denominator)
    tangent = points[b] - points[a]
    return point, ((a, tangent * dtheta_da), (b, tangent * dtheta_db))


def _add_segment_gradient(
    gradient: np.ndarray,
    corners: list[tuple[int, int]],
    crossing_a,
    crossing_b,
    *,
    sigma: float,
) -> float:
    point_a, derivatives_a = crossing_a
    point_b, derivatives_b = crossing_b
    segment = point_b - point_a
    length = float(np.linalg.norm(segment))
    if length <= np.finfo(float).tiny:
        return 0.0
    direction = segment / length
    for local_index, derivative in derivatives_a:
        node = corners[local_index]
        gradient[node] -= sigma * float(np.dot(direction, derivative))
    for local_index, derivative in derivatives_b:
        node = corners[local_index]
        gradient[node] += sigma * float(np.dot(direction, derivative))
    return sigma * length


def _surface_energy_gradient_from_psi(
    psi,
    coords,
    *,
    sigma: float,
    threshold: float = 0.5,
) -> tuple[float, np.ndarray]:
    """Return ``σ|Γ_h|`` and its marching-squares derivative wrt nodal ψ."""
    psi = np.asarray(psi, dtype=float)
    x = np.asarray(coords[0], dtype=float)
    y = np.asarray(coords[1], dtype=float)
    gradient = np.zeros_like(psi, dtype=float)
    energy = 0.0
    edge_pairs = ((0, 1), (1, 2), (2, 3), (3, 0))

    for i in range(len(x) - 1):
        for j in range(len(y) - 1):
            points = [
                np.asarray((x[i], y[j]), dtype=float),
                np.asarray((x[i + 1], y[j]), dtype=float),
                np.asarray((x[i + 1], y[j + 1]), dtype=float),
                np.asarray((x[i], y[j + 1]), dtype=float),
            ]
            values = [
                float(psi[i, j]),
                float(psi[i + 1, j]),
                float(psi[i + 1, j + 1]),
                float(psi[i, j + 1]),
            ]
            corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            crossings = [
                crossing
                for a, b in edge_pairs
                if (
                    crossing := _edge_crossing_with_derivatives(
                        values,
                        points,
                        a,
                        b,
                        threshold=threshold,
                    )
                )
                is not None
            ]
            if len(crossings) == 2:
                energy += _add_segment_gradient(
                    gradient,
                    corners,
                    crossings[0],
                    crossings[1],
                    sigma=sigma,
                )
            elif len(crossings) == 4:
                centre = sum(crossing[0] for crossing in crossings) / 4.0
                ordered = sorted(
                    crossings,
                    key=lambda crossing: np.arctan2(
                        float(crossing[0][1] - centre[1]),
                        float(crossing[0][0] - centre[0]),
                    ),
                )
                energy += _add_segment_gradient(
                    gradient,
                    corners,
                    ordered[0],
                    ordered[1],
                    sigma=sigma,
                )
                energy += _add_segment_gradient(
                    gradient,
                    corners,
                    ordered[2],
                    ordered[3],
                    sigma=sigma,
                )
    return float(energy), gradient


def _negative_face_divergence_adjoint(solver, nodal_covector, axis: int):
    """Return ``(-D_f)^T`` for the FCCD face-divergence used by transport."""
    xp = solver.backend.xp
    fccd = solver._fccd
    covector = xp.moveaxis(xp.asarray(nodal_covector), axis, 0)
    n_faces = solver._grid.N[axis]
    weights = fccd._weights[axis]
    if fccd._axis_periodic(axis):
        unique = xp.array(covector[:n_faces], copy=True)
        unique[0] = unique[0] + covector[n_faces]
        if weights["uniform"]:
            weighted = unique * weights["inv_H"]
        else:
            inv_width = fccd._broadcast_axis0(
                weights["inv_H_periodic_node"],
                unique.ndim,
            )
            weighted = unique * inv_width
        adjoint = xp.roll(weighted, -1, axis=0) - weighted
        return xp.moveaxis(adjoint, 0, axis)

    if weights["uniform"]:
        weighted = covector * weights["inv_H"]
    else:
        inv_width = fccd._broadcast_axis0(weights["inv_H_node"], covector.ndim)
        weighted = covector * inv_width
    adjoint = weighted[:-1] - weighted[1:]
    return xp.moveaxis(adjoint, 0, axis)


def _variational_transport_power(solver, psi, face_velocity_components, *, sigma: float):
    """Return ``-<δE/δψ, T'(ψ; u_f)>`` for the actual face transport RHS."""
    xp = solver.backend.xp
    if getattr(solver, "_curvature_method", "") in {
        "transport_variational_p2",
        "transport_variational_p2_midpoint",
        "transport_variational_p2_discrete_gradient",
        "transport_variational_p2_ale_discrete_gradient",
    }:
        gradient = p2_trace_surface_energy_gradient_2d(
            xp=xp,
            grid=solver._grid,
            psi=xp.asarray(psi),
            sigma=sigma,
        )
    else:
        _, gradient_host = _surface_energy_gradient_from_psi(
            _host(solver.backend, psi),
            solver._grid.coords,
            sigma=sigma,
        )
        gradient = xp.asarray(gradient_host)
    power = xp.asarray(0.0)
    for axis, face_velocity in enumerate(face_velocity_components):
        psi_face = solver._fccd.face_value(psi, axis)
        adjoint = _negative_face_divergence_adjoint(solver, gradient, axis)
        surface_rate_covector = psi_face * adjoint
        power = power - xp.sum(xp.asarray(face_velocity) * surface_rate_covector)
    return float(np.asarray(solver.backend.to_host(power)))


def _jump_power_from_faces(
    solver,
    psi,
    face_velocity_components,
    *,
    sigma: float,
    psi_previous=None,
) -> float | None:
    """Return the pressure-jump face work paired with projected face velocity."""
    if face_velocity_components is None or sigma <= 0.0:
        return None
    xp = solver.backend.xp
    method = getattr(solver, "_curvature_method", "")
    context_psi = xp.asarray(psi)
    context_psi_previous = None
    if psi_previous is not None and method == "transport_variational_p2_midpoint":
        previous = xp.asarray(psi_previous)
        context_psi = xp.asarray(0.5, dtype=context_psi.dtype) * (
            previous + context_psi
        )
    elif method in {
        "transport_variational_p2_discrete_gradient",
        "transport_variational_p2_ale_discrete_gradient",
    }:
        if psi_previous is None:
            return None
        context_psi_previous = xp.asarray(psi_previous)
    context = build_young_laplace_interface_stress_context(
        xp=xp,
        psi=context_psi,
        psi_previous=context_psi_previous,
        kappa_lg=xp.zeros_like(context_psi),
        sigma=sigma,
        face_curvature_method=method,
    )
    face_curvature_lg = evaluate_interface_face_curvature_lg(
        xp=xp,
        grid=solver._grid,
        context=context,
        fccd=solver._fccd,
    )
    power = xp.asarray(0.0)
    ndim = solver._grid.ndim
    for axis, face_velocity in enumerate(face_velocity_components):
        jump_gradient = signed_pressure_jump_gradient(
            xp=xp,
            grid=solver._grid,
            context=context,
            axis=axis,
            face_curvature_lg=face_curvature_lg,
            fccd=solver._fccd,
        )
        coords_axis = xp.asarray(solver._grid.coords[axis])
        face_distance = coords_axis[1:] - coords_axis[:-1]
        distance_shape = [1] * ndim
        distance_shape[axis] = -1
        signed_jump = jump_gradient * face_distance.reshape(distance_shape)
        transverse_axis = 1 - axis
        face_area = xp.asarray(solver._grid.h[transverse_axis])
        area_shape = [1] * ndim
        area_shape[transverse_axis] = -1
        power = power + xp.sum(xp.asarray(face_velocity) * signed_jump * face_area.reshape(area_shape))
    return float(np.asarray(solver.backend.to_host(power)))


def _transported_surface_energy(
    solver,
    psi,
    face_velocity_components,
    dt: float,
    *,
    sigma: float,
    step_index: int,
    scale: float,
    include_mass_correction: bool,
) -> float:
    xp = solver.backend.xp
    psi_probe = _device_copy(solver.backend, psi)
    scaled_faces = [xp.asarray(face) * float(scale) for face in face_velocity_components]
    if include_mass_correction:
        advance_face = solver._transport.advance_with_face_velocity
        psi_new = advance_face(
            psi_probe,
            scaled_faces,
            dt,
            step_index=step_index,
        )
    else:
        advance_face = solver._transport.advection.advance_with_face_velocity
        psi_new = advance_face(psi_probe, scaled_faces, dt)
    return _surface_energy(solver, psi_new, sigma=sigma)


def _transport_rates(
    solver,
    psi,
    face_velocity_components,
    dt: float,
    *,
    sigma: float,
    step_index: int,
    base_surface_energy: float,
    linear_eps: float,
) -> TransportRates:
    transport_energy = _transported_surface_energy(
        solver,
        psi,
        face_velocity_components,
        dt,
        sigma=sigma,
        step_index=step_index,
        scale=1.0,
        include_mass_correction=True,
    )
    advection_energy = _transported_surface_energy(
        solver,
        psi,
        face_velocity_components,
        dt,
        sigma=sigma,
        step_index=step_index,
        scale=1.0,
        include_mass_correction=False,
    )
    transport_energy_plus = _transported_surface_energy(
        solver,
        psi,
        face_velocity_components,
        dt,
        sigma=sigma,
        step_index=step_index,
        scale=linear_eps,
        include_mass_correction=True,
    )
    transport_energy_minus = _transported_surface_energy(
        solver,
        psi,
        face_velocity_components,
        dt,
        sigma=sigma,
        step_index=step_index,
        scale=-linear_eps,
        include_mass_correction=True,
    )
    advection_energy_plus = _transported_surface_energy(
        solver,
        psi,
        face_velocity_components,
        dt,
        sigma=sigma,
        step_index=step_index,
        scale=linear_eps,
        include_mass_correction=False,
    )
    advection_energy_minus = _transported_surface_energy(
        solver,
        psi,
        face_velocity_components,
        dt,
        sigma=sigma,
        step_index=step_index,
        scale=-linear_eps,
        include_mass_correction=False,
    )
    return TransportRates(
        transport_rate=float((transport_energy - base_surface_energy) / dt),
        advection_rate=float((advection_energy - base_surface_energy) / dt),
        transport_linear_rate=float(
            (transport_energy_plus - transport_energy_minus)
            / (2.0 * linear_eps * dt)
        ),
        advection_linear_rate=float(
            (advection_energy_plus - advection_energy_minus)
            / (2.0 * linear_eps * dt)
        ),
        variational_power=_variational_transport_power(
            solver,
            psi,
            face_velocity_components,
            sigma=sigma,
        ),
    )


def _prepare_initial_state(cfg):
    from twophase.levelset.wall_contact import WallContactSet

    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    psi_host = np.asarray(solver._backend.to_host(psi))
    solver.set_wall_contacts(
        WallContactSet.detect_from_psi(psi_host, solver._grid, bc_type=solver.bc_type)
    )
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(
            psi,
            u,
            v,
            cfg.physics.rho_l,
            cfg.physics.rho_g,
        )
        print(f"  [capillary-work] grid built, h_min={solver.h_min:.4e}")
    return solver, psi, u, v, bc_hook


def run_gate(
    cfg,
    *,
    steps: int,
    max_time: float | None,
    linear_eps: float,
) -> dict[str, np.ndarray]:
    """Run the short capillary-work gate and return diagnostic arrays."""
    solver, psi, u, v, bc_hook = _prepare_initial_state(cfg)
    ph = cfg.physics
    time = 0.0
    previous = WorkState(
        time=0.0,
        surface_energy=_surface_energy(solver, psi, sigma=ph.sigma),
        jump_power=None,
    )
    rows: list[dict[str, float]] = []

    for step in range(steps):
        if max_time is not None and time >= max_time:
            break
        dt_budget = solver.dt_budget(
            u,
            v,
            ph,
            cfg.run.cfl,
            cfl_advective=cfg.run.cfl_advective,
            cfl_capillary=cfg.run.cfl_capillary,
            cfl_viscous=cfg.run.cfl_viscous,
        )
        dt = dt_budget.dt
        if max_time is not None:
            dt = min(dt, max_time - time)
        if dt <= np.finfo(float).eps * max(abs(time), 1.0):
            break

        psi_before = psi
        transport_face_components = solver._projected_face_components
        transport_rates = None
        if transport_face_components is not None:
            transport_rates = _transport_rates(
                solver,
                psi,
                transport_face_components,
                dt,
                sigma=ph.sigma,
                step_index=step,
                base_surface_energy=previous.surface_energy,
                linear_eps=linear_eps,
            )

        psi, u, v, p = solver.step_request(
            NSStepRequest(
                psi=psi,
                u=u,
                v=v,
                dt=dt,
                rho_l=ph.rho_l,
                rho_g=ph.rho_g,
                sigma=ph.sigma,
                mu=ph.mu,
                g_acc=ph.g_acc,
                rho_ref=ph.rho_ref,
                mu_l=ph.mu_l,
                mu_g=ph.mu_g,
                bc_hook=bc_hook,
                step_index=step,
            ),
            return_host_pressure=False,
        )
        del p
        time += dt
        surface_energy = _surface_energy(solver, psi, sigma=ph.sigma)
        surface_rate = (surface_energy - previous.surface_energy) / dt
        jump_power = _jump_power_from_faces(
            solver,
            psi,
            transport_face_components,
            sigma=ph.sigma,
            psi_previous=psi_before,
        )
        if jump_power is not None:
            residual_plus = surface_rate + jump_power
            residual_minus = surface_rate - jump_power
            scale = max(abs(surface_rate), abs(jump_power), np.finfo(float).tiny)
            row = {
                "step": float(step),
                "time": float(time),
                "dt": float(dt),
                "surface_energy": float(surface_energy),
                "surface_rate": float(surface_rate),
                "jump_power": float(jump_power),
                "residual_plus": float(residual_plus),
                "residual_minus": float(residual_minus),
                "relative_plus": float(abs(residual_plus) / scale),
                "relative_minus": float(abs(residual_minus) / scale),
                "dt_limiter_code": float(dt_budget.diagnostics()["dt_limiter_code"]),
            }
            if transport_rates is not None:
                linear_adjoint_residual = (
                    transport_rates.transport_linear_rate
                    + transport_rates.variational_power
                )
                linear_adjoint_scale = max(
                    abs(transport_rates.transport_linear_rate),
                    abs(transport_rates.variational_power),
                    np.finfo(float).tiny,
                )
                row.update(
                    {
                        "transport_rate": transport_rates.transport_rate,
                        "advection_rate": transport_rates.advection_rate,
                        "transport_linear_rate": transport_rates.transport_linear_rate,
                        "advection_linear_rate": transport_rates.advection_linear_rate,
                        "variational_power": transport_rates.variational_power,
                        "linear_adjoint_residual": linear_adjoint_residual,
                        "relative_linear_adjoint": abs(linear_adjoint_residual)
                        / linear_adjoint_scale,
                    }
                )
            rows.append(row)
        previous = WorkState(
            time=time,
            surface_energy=surface_energy,
            jump_power=None,
        )
        if step < 2 or (step + 1) % max(1, cfg.run.print_every) == 0:
            print(
                f"  step={step + 1:5d} t={time:.4e} "
                f"E={surface_energy:.6e} P={jump_power if jump_power is not None else np.nan:.6e}"
            )

    if not rows:
        raise RuntimeError("capillary-work gate produced no comparable rows")
    return {
        key: np.asarray([row[key] for row in rows], dtype=float)
        for key in rows[0]
    }


def plot_results(results: dict[str, np.ndarray], outdir: pathlib.Path) -> None:
    """Write the gate residual PDF."""
    fig, axes = plt.subplots(2, 1, figsize=(6.5, 6.0), sharex=True)
    axes[0].plot(results["time"], results["surface_rate"], label=r"$dE_\Gamma/dt$")
    axes[0].plot(results["time"], results["jump_power"], label=r"$P_\Gamma$")
    axes[0].set_ylabel("power")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(fontsize=8)
    axes[1].semilogy(results["time"], results["relative_plus"], label=r"$|dE/dt+P|$")
    axes[1].semilogy(results["time"], results["relative_minus"], label=r"$|dE/dt-P|$")
    if "relative_linear_adjoint" in results:
        axes[1].semilogy(
            results["time"],
            results["relative_linear_adjoint"],
            label=r"linear adjoint",
        )
    axes[1].set_xlabel("time")
    axes[1].set_ylabel("relative residual")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(fontsize=8)
    save_figure(fig, outdir / "capillary_work_gate_residual.pdf")


def main() -> None:
    parser = experiment_argparser("Capillary work manufactured gate")
    parser.add_argument("--config", required=True, help="ch14 YAML path or stem")
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--max-time", type=float, default=None)
    parser.add_argument("--linear-eps", type=float, default=0.25)
    args = parser.parse_args()

    apply_style()
    config_path = _resolve_config(args.config)
    outdir = experiment_dir(__file__, "capillary_work_gate") / config_path.stem
    outdir.mkdir(parents=True, exist_ok=True)
    npz_path = outdir / "data.npz"
    if args.plot_only:
        from twophase.tools.experiment import load_results

        results = load_results(npz_path)
    else:
        cfg = load_experiment_config(config_path)
        results = run_gate(
            cfg,
            steps=int(args.steps),
            max_time=args.max_time,
            linear_eps=float(args.linear_eps),
        )
        save_results(npz_path, results)
    plot_results(results, outdir)
    best_plus = float(np.nanmin(results["relative_plus"]))
    best_minus = float(np.nanmin(results["relative_minus"]))
    print(f"best relative residuals: plus={best_plus:.3e}, minus={best_minus:.3e}")
    if "relative_linear_adjoint" in results:
        best_linear = float(np.nanmin(results["relative_linear_adjoint"]))
        print(f"best linear adjoint residual: {best_linear:.3e}")


if __name__ == "__main__":
    main()
