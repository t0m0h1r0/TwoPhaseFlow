#!/usr/bin/env python3
"""Short capillary-wave direction diagnostic for the AO production route."""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.levelset.wall_contact import WallContactSet  # noqa: E402
from twophase.simulation.config_io import load_experiment_config  # noqa: E402
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver  # noqa: E402
from twophase.simulation.boundary_hodge import wall_trace_from_faces  # noqa: E402
from twophase.simulation.ns_step_services import (  # noqa: E402
    _geometric_to_projection_face_pair_2d,
)
from twophase.simulation.ns_step_state import NSStepRequest  # noqa: E402
from twophase.simulation.runner import (  # noqa: E402
    _capture_runtime_snapshot,
    _geometric_liquid_volume,
    _geometric_phase_diagnostic_psi,
    _snapshot_needs_projection_fields,
)
from twophase.tools.diagnostics import DiagnosticCollector  # noqa: E402


def _to_host(backend, value):
    return np.asarray(backend.to_host(value))


def _min_grid_spacing(grid):
    return tuple(float(np.min(np.diff(np.asarray(coords)))) for coords in grid.coords)


def _interface_samples(psi, field, x_coord, y_coord, *, y_mid: float):
    psi = np.asarray(psi)
    field = np.asarray(field)
    x_coord = np.asarray(x_coord)
    y_coord = np.asarray(y_coord)
    rows = []
    eta = []
    field_int = []
    for i in range(psi.shape[0]):
        s0 = psi[i, :-1] - 0.5
        s1 = psi[i, 1:] - 0.5
        crossings = np.flatnonzero(s0 * s1 < 0.0)
        if crossings.size == 0:
            continue
        j = int(crossings[0])
        denom = psi[i, j + 1] - psi[i, j]
        frac = 0.0 if abs(denom) < 1.0e-30 else (0.5 - psi[i, j]) / denom
        y_int = y_coord[i, j] + frac * (y_coord[i, j + 1] - y_coord[i, j])
        rows.append(x_coord[i, j])
        eta.append(y_int - y_mid)
        field_int.append(field[i, j] + frac * (field[i, j + 1] - field[i, j]))
    return np.asarray(rows), np.asarray(eta), np.asarray(field_int)


def _weighted_cos_projection(x, values, *, mode: int, length: float):
    if x.size < 2:
        return 0.0
    basis = np.cos(2.0 * np.pi * int(mode) * x / float(length))
    dx = np.diff(x)
    weights = np.zeros_like(x)
    weights[0] = 0.5 * dx[0]
    weights[-1] = 0.5 * dx[-1]
    if x.size > 2:
        weights[1:-1] = 0.5 * (dx[:-1] + dx[1:])
    denom = float(np.sum(weights * basis * basis))
    if denom <= 0.0:
        return 0.0
    return float(np.sum(weights * np.asarray(values) * basis) / denom)


def _interface_mode_projection(psi, v, x_coord, y_coord, *, mode: int, length: float, y_mid: float):
    x, eta, v_int = _interface_samples(psi, v, x_coord, y_coord, y_mid=y_mid)
    if x.size < 2:
        return 0.0, 0.0, 0.0
    eta_mode = _weighted_cos_projection(x, eta, mode=mode, length=length)
    v_mode = _weighted_cos_projection(x, v_int, mode=mode, length=length)
    return eta_mode, v_mode, float(np.max(np.abs(v_int)))


def _q_height_mode(backend, grid, phase, *, mode: int, length: float, y_mid: float):
    """Return the AO-owned column-volume graph mode from q itself."""
    if phase is None:
        return 0.0
    q = _to_host(backend, phase.q)
    x_edges = np.asarray(grid.coords[0], dtype=float)
    y_edges = np.asarray(grid.coords[1], dtype=float)
    dx = np.diff(x_edges)
    x_center = 0.5 * (x_edges[:-1] + x_edges[1:])
    height = y_edges[0] + np.sum(q, axis=1) / dx
    return _weighted_cos_projection(
        x_center,
        height - y_mid,
        mode=mode,
        length=length,
    )


def _face_y_mode(
    backend,
    div_op,
    grid,
    psi_host,
    face_pair,
    x_coord,
    y_coord,
    *,
    mode: int,
    length: float,
    y_mid: float,
    boundary,
):
    xp = backend.xp
    faces = [xp.asarray(component) for component in face_pair]
    geometric_shapes = ((int(grid.N[0]) + 1, int(grid.N[1])), (int(grid.N[0]), int(grid.N[1]) + 1))
    projection_shapes = ((int(grid.N[0]), int(grid.N[1]) + 1), (int(grid.N[0]) + 1, int(grid.N[1])))
    shapes = tuple(tuple(face.shape) for face in faces)
    if shapes == geometric_shapes:
        projected = _geometric_to_projection_face_pair_2d(
            xp=xp,
            grid=grid,
            face_pair=faces,
            boundary=boundary,
        )
    elif shapes == projection_shapes:
        projected = faces
    else:
        return 0.0
    y_component = _to_host(backend, div_op.reconstruct_nodes(projected)[1])
    x, _, values = _interface_samples(
        psi_host,
        y_component,
        x_coord,
        y_coord,
        y_mid=y_mid,
    )
    return _weighted_cos_projection(x, values, mode=mode, length=length)


def _face_wall_linf(backend, div_op, grid, face_pair, *, boundary, bc_type: str):
    if face_pair is None:
        return 0.0
    xp = backend.xp
    faces = [xp.asarray(component) for component in face_pair]
    geometric_shapes = ((int(grid.N[0]) + 1, int(grid.N[1])), (int(grid.N[0]), int(grid.N[1]) + 1))
    projection_shapes = ((int(grid.N[0]), int(grid.N[1]) + 1), (int(grid.N[0]) + 1, int(grid.N[1])))
    shapes = tuple(tuple(face.shape) for face in faces)
    if shapes == geometric_shapes:
        projected = _geometric_to_projection_face_pair_2d(
            xp=xp,
            grid=grid,
            face_pair=faces,
            boundary=boundary,
        )
    elif shapes == projection_shapes:
        projected = faces
    else:
        return float("nan")
    trace = wall_trace_from_faces(xp, grid, projected, bc_type)
    if getattr(trace, "size", 0) == 0:
        return 0.0
    return float(np.asarray(backend.to_host(xp.max(xp.abs(trace)))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--pressure-history", choices=("as_config", "face_acceleration", "pressure_coordinate"), default="as_config")
    parser.add_argument("--history-extrapolation", choices=("as_config", "constant", "bdf2"), default="constant")
    parser.add_argument("--runner-initial-grid-rebuild", action="store_true")
    parser.add_argument("--runner-reset-after-grid-rebuild", action="store_true")
    parser.add_argument("--runner-diagnostic-psi-feedback", action="store_true")
    parser.add_argument("--runner-observation-side-effects", action="store_true")
    parser.add_argument("--debug-diagnostics", action="store_true")
    parser.add_argument("--active-projection-pcg-max-iterations", type=int)
    parser.add_argument("--grid-rebuild-frequency", type=int)
    parser.add_argument("--print-every", type=int, default=1)
    parser.add_argument("--residual-report-every", type=int, default=0)
    parser.add_argument("--certificate-report-every", type=int, default=0)
    args = parser.parse_args()

    cfg = load_experiment_config(args.config)
    overrides = {}
    if args.debug_diagnostics:
        overrides["run.debug_diagnostics"] = True
    if args.active_projection_pcg_max_iterations is not None:
        overrides["interface_state_space.active_projection_pcg_max_iterations"] = (
            args.active_projection_pcg_max_iterations
        )
    if args.grid_rebuild_frequency is not None:
        overrides["grid.grid_rebuild_freq"] = args.grid_rebuild_frequency
    if args.pressure_history != "as_config":
        overrides["run.pressure_history_mode"] = args.pressure_history
    if args.history_extrapolation != "as_config":
        overrides["run.pressure_history_extrapolation"] = args.history_extrapolation
    cfg = cfg.override(**overrides)

    solver = TwoPhaseNSSolver.from_config(cfg)
    backend = solver._backend
    grid = solver._grid
    psi = solver.build_ic(cfg)
    wall_contacts = WallContactSet.detect_from_psi(
        _to_host(backend, psi),
        grid,
        bc_type=solver.bc_type,
    )
    solver.set_wall_contacts(wall_contacts)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    ph = cfg.physics
    if args.runner_initial_grid_rebuild and solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
        if args.runner_reset_after_grid_rebuild:
            psi = solver.build_ic(cfg)
            u, v = solver.build_velocity(cfg, psi)
        wall_contacts = WallContactSet.detect_from_psi(
            _to_host(backend, psi),
            solver._grid,
            bc_type=solver.bc_type,
        )
        solver.set_wall_contacts(wall_contacts)
    p = None
    x_coord = _to_host(backend, solver.X)
    y_coord = _to_host(backend, solver.Y)
    mode = 2
    length = float(grid.L[0])
    y_mid = 0.5 * float(grid.L[1])
    collector = None
    snaps = []
    if args.runner_observation_side_effects:
        collector = DiagnosticCollector(
            cfg.diagnostics,
            solver.X,
            solver.Y,
            solver.h,
            rho_l=ph.rho_l,
            rho_g=ph.rho_g,
            sigma=ph.sigma,
            R=float(cfg.initial_condition.get("radius", 0.25)),
        )
        if collector.needs_retained_geometry():
            collector.retain_device_geometry(backend.xp, solver.X, solver.Y, psi.shape)
    snap_times = list(cfg.run.snap_times)
    snap_idx = 0

    print(
        "step,t,dt,eta_cos,eta_theta_cos,eta_phi_cos,q_height_cos,"
        "q_rate_cos,v_cos,v_abs_max,"
        "min_dx,min_dy,"
        "compat_linf,div_u,raw_accel_cos,predictor_accel_cos,"
        "reaction_accel_cos,balanced_accel_cos,projected_face_linf,yl_normal,"
        "ppe_dc_linf,ppe_dc_conv,ppe_rhs,face_hodge_pre,face_hodge_post,"
        "projected_wall_linf,predictor_wall_linf,reaction_wall_linf,balanced_wall_linf"
    )
    initial_phase = getattr(solver, "_geometric_phase_state", None)
    prev_q_height_mode = _q_height_mode(
        backend,
        solver._grid,
        initial_phase,
        mode=mode,
        length=length,
        y_mid=y_mid,
    )
    t = 0.0
    eta_mode, v_mode, v_abs = _interface_mode_projection(
        _to_host(backend, psi),
        _to_host(backend, v),
        x_coord,
        y_coord,
        mode=mode,
        length=length,
        y_mid=y_mid,
    )
    print(
        0,
        f"{t:.12e}",
        "0.000000000000e+00",
        f"{eta_mode:.12e}",
        f"{eta_mode:.12e}",
        f"{eta_mode:.12e}",
        f"{prev_q_height_mode:.12e}",
        "0.000000000000e+00",
        f"{v_mode:.12e}",
        f"{v_abs:.12e}",
        f"{_min_grid_spacing(solver._grid)[0]:.12e}",
        f"{_min_grid_spacing(solver._grid)[1]:.12e}",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        "0.000000000000e+00",
        sep=",",
    )

    for step in range(args.steps):
        psi, u, v, _grid_rebuilt = solver.prepare_geometric_grid_for_timestep(
            psi,
            u,
            v,
            dt=0.0,
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
        )
        budget = solver.dt_budget(
            u,
            v,
            ph,
            cfg.run.cfl,
            cfl_advective=cfg.run.cfl_advective,
            cfl_capillary=cfg.run.cfl_capillary,
            cfl_viscous=cfg.run.cfl_viscous,
        )
        dt = float(budget.dt)
        if args.runner_observation_side_effects:
            will_snapshot = snap_idx < len(snap_times) and t + dt >= snap_times[snap_idx]
            solver._record_interface_projection_fields = bool(
                will_snapshot and _snapshot_needs_projection_fields(cfg)
            )
        try:
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
        except ValueError as exc:
            if "GPU AO capillary fail-close" not in str(exc):
                raise
            print("FAIL_CLOSE", step + 1, f"{t:.12e}", f"{dt:.12e}", str(exc), sep=",")
            break
        t += dt
        if args.runner_diagnostic_psi_feedback:
            psi = _geometric_phase_diagnostic_psi(solver, psi)
        if collector is not None:
            control_volumes = solver._grid.cell_volumes()
            grid_will_rebuild = (
                solver._alpha_grid > 1.0
                and solver._rebuild_freq > 0
                and step > 0
                and (step % solver._rebuild_freq == 0)
            )
            if grid_will_rebuild and collector.needs_retained_geometry():
                collector.X = solver.X
                collector.Y = solver.Y
                collector.retain_device_geometry(
                    backend.xp,
                    solver.X,
                    solver.Y,
                    psi.shape,
                )
            liquid_volume = _geometric_liquid_volume(solver)
            if liquid_volume is None:
                collector.collect(
                    t,
                    psi,
                    u,
                    v,
                    backend.xp.asarray(p),
                    dV=control_volumes,
                )
            else:
                collector.collect(
                    t,
                    psi,
                    u,
                    v,
                    backend.xp.asarray(p),
                    dV=control_volumes,
                    liquid_volume=liquid_volume,
                )
            snaps.append(_capture_runtime_snapshot(solver, ph, t, psi, u, v, p))
            while snap_idx < len(snap_times) and t >= snap_times[snap_idx]:
                snap_idx += 1
        grid = solver._grid
        x_coord = _to_host(backend, solver.X)
        y_coord = _to_host(backend, solver.Y)
        phase = solver._geometric_phase_state
        cap = solver._last_geometric_runtime_capillary
        app = solver._last_geometric_runtime_capillary_application
        step_diag = solver._step_diag.last
        projected_faces = getattr(solver, "_projected_face_components", None)
        xp = backend.xp
        if projected_faces is None:
            projected_linf = 0.0
        else:
            projected_linf = max(
                float(np.asarray(backend.to_host(xp.max(xp.abs(face)))))
                for face in projected_faces
            )
        psi_host = _to_host(backend, psi)
        theta_view = _to_host(
            backend,
            solver._geometric_cell_to_node_view(phase.theta),
        )
        phi_view = _to_host(
            backend,
            _geometric_phase_diagnostic_psi(solver, psi),
        )
        eta_mode, v_mode, v_abs = _interface_mode_projection(
            psi_host,
            _to_host(backend, v),
            x_coord,
            y_coord,
            mode=mode,
            length=length,
            y_mid=y_mid,
        )
        eta_theta_mode, _, _ = _interface_mode_projection(
            theta_view,
            _to_host(backend, v),
            x_coord,
            y_coord,
            mode=mode,
            length=length,
            y_mid=y_mid,
        )
        eta_phi_mode, _, _ = _interface_mode_projection(
            phi_view,
            _to_host(backend, v),
            x_coord,
            y_coord,
            mode=mode,
            length=length,
            y_mid=y_mid,
        )
        q_height_mode = _q_height_mode(
            backend,
            grid,
            phase,
            mode=mode,
            length=length,
            y_mid=y_mid,
        )
        q_rate_mode = (
            (q_height_mode - prev_q_height_mode) / dt
            if dt > 0.0
            else 0.0
        )
        prev_q_height_mode = q_height_mode
        boundary = tuple(cap.material.face_hodge.boundary)
        raw_accel_mode = _face_y_mode(
            backend,
            solver._div_op,
            grid,
            psi_host,
            cap.capillary_force_acceleration,
            x_coord,
            y_coord,
            mode=mode,
            length=length,
            y_mid=y_mid,
            boundary=boundary,
        )
        predictor_accel_mode = _face_y_mode(
            backend,
            solver._div_op,
            grid,
            psi_host,
            app.predictor_face_acceleration,
            x_coord,
            y_coord,
            mode=mode,
            length=length,
            y_mid=y_mid,
            boundary=boundary,
        )
        reaction_accel_mode = _face_y_mode(
            backend,
            solver._div_op,
            grid,
            psi_host,
            app.pressure_reaction_face_acceleration,
            x_coord,
            y_coord,
            mode=mode,
            length=length,
            y_mid=y_mid,
            boundary=boundary,
        )
        balanced_accel_mode = _face_y_mode(
            backend,
            solver._div_op,
            grid,
            psi_host,
            [
                xp.asarray(left) - xp.asarray(right)
                for left, right in zip(
                    app.predictor_face_acceleration,
                    app.pressure_reaction_face_acceleration,
                    strict=True,
                )
            ],
            x_coord,
            y_coord,
            mode=mode,
            length=length,
            y_mid=y_mid,
            boundary=boundary,
        )
        projected_wall_linf = _face_wall_linf(
            backend,
            solver._div_op,
            grid,
            projected_faces,
            boundary=boundary,
            bc_type=solver.bc_type,
        )
        predictor_wall_linf = _face_wall_linf(
            backend,
            solver._div_op,
            grid,
            app.predictor_face_acceleration,
            boundary=boundary,
            bc_type=solver.bc_type,
        )
        reaction_wall_linf = _face_wall_linf(
            backend,
            solver._div_op,
            grid,
            app.pressure_reaction_face_acceleration,
            boundary=boundary,
            bc_type=solver.bc_type,
        )
        balanced_wall_linf = _face_wall_linf(
            backend,
            solver._div_op,
            grid,
            [
                xp.asarray(left) - xp.asarray(right)
                for left, right in zip(
                    app.predictor_face_acceleration,
                    app.pressure_reaction_face_acceleration,
                    strict=True,
                )
            ],
            boundary=boundary,
            bc_type=solver.bc_type,
        )
        compat = float(np.asarray(backend.to_host(phase.compatibility_residual_linf)))
        if args.residual_report_every > 0 and (
            (step + 1) % int(args.residual_report_every) == 0
            or step + 1 == args.steps
        ):
            derivatives = (
                cap.pressure_capillary_hodge
                .capillary_riesz
                .surface_covector
                .derivatives
            )
            residual_dev = xp.asarray(phase.q) - xp.asarray(phase.geometry.q)
            row_norm_dev = xp.sum(
                xp.asarray(derivatives.jq_local) * xp.asarray(derivatives.jq_local),
                axis=-1,
            )
            active_dev = row_norm_dev > xp.asarray(1.0e-12) * xp.max(row_norm_dev)
            residual = _to_host(backend, residual_dev)
            row_norm = _to_host(backend, row_norm_dev)
            active = _to_host(backend, active_dev).astype(bool)
            cases = _to_host(backend, phase.stratum.cell_cases)
            imax = np.unravel_index(int(np.argmax(np.abs(residual))), residual.shape)
            print(
                "RESIDUAL",
                step + 1,
                int(imax[0]),
                int(imax[1]),
                f"{float(residual[imax]):.12e}",
                bool(active[imax]),
                int(cases[imax]),
                f"{float(row_norm[imax]):.12e}",
                f"{float(_to_host(backend, phase.q)[imax]):.12e}",
                f"{float(_to_host(backend, phase.geometry.q)[imax]):.12e}",
                sep=",",
            )
        if args.certificate_report_every > 0 and (
            (step + 1) % int(args.certificate_report_every) == 0
            or step + 1 == args.steps
        ):
            certificate = dict(
                getattr(solver, "_last_conservative_transport_certificate", None)
                or {}
            )
            keys = (
                "ao_pressure_reaction_projection_raw_l2",
                "ao_pressure_reaction_projection_corrected_l2",
                "ao_pressure_reaction_projection_range_l2",
                "ao_pressure_reaction_projection_balanced_l2",
                "ao_pressure_reaction_projection_pressure_adjoint_residual",
                "ao_pressure_reaction_projection_saddle_constraint_linf",
                "ao_capillary_pressure_jump_acceleration_linf",
                "ao_capillary_pressure_jump_rhs_linf",
                "ao_scalar_ppe_rhs_linf",
                "ao_projected_face_div_linf",
            )
            values = [certificate.get(key, float("nan")) for key in keys]
            print(
                "CERT",
                step + 1,
                *(f"{float(value):.12e}" for value in values),
                sep=",",
            )
        if (step + 1) % max(int(args.print_every), 1) != 0 and step + 1 != args.steps:
            continue
        min_dx, min_dy = _min_grid_spacing(grid)
        print(
            step + 1,
            f"{t:.12e}",
            f"{dt:.12e}",
            f"{eta_mode:.12e}",
            f"{eta_theta_mode:.12e}",
            f"{eta_phi_mode:.12e}",
            f"{q_height_mode:.12e}",
            f"{q_rate_mode:.12e}",
            f"{v_mode:.12e}",
            f"{v_abs:.12e}",
            f"{min_dx:.12e}",
            f"{min_dy:.12e}",
            f"{compat:.12e}",
            f"{step_diag.get('div_u_max', 0.0):.12e}",
            f"{raw_accel_mode:.12e}",
            f"{predictor_accel_mode:.12e}",
            f"{reaction_accel_mode:.12e}",
            f"{balanced_accel_mode:.12e}",
            f"{projected_linf:.12e}",
            f"{float(np.asarray(backend.to_host(cap.young_laplace_normal_residual_linf))):.12e}",
            f"{step_diag.get('ppe_dc_final_residual_linf', 0.0):.12e}",
            f"{step_diag.get('ppe_dc_converged', 0.0):.12e}",
            f"{step_diag.get('ppe_rhs_max', 0.0):.12e}",
            f"{solver.reproject_stats.get('pre_div_linf', 0.0):.12e}",
            f"{solver.reproject_stats.get('post_div_linf', 0.0):.12e}",
            f"{projected_wall_linf:.12e}",
            f"{predictor_wall_linf:.12e}",
            f"{reaction_wall_linf:.12e}",
            f"{balanced_wall_linf:.12e}",
            sep=",",
        )


if __name__ == "__main__":
    main()
