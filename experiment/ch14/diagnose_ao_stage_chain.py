#!/usr/bin/env python3
"""Stage-by-stage AO-Fast capillary-wave failure probe.

This diagnostic executes the same private solver stages as ``step_request`` but
prints the intermediate face-state metrics before the PPE solve.  It is meant
to localise whether the blow-up is born in q transport, capillary splitting,
momentum prediction, PPE solution, or velocity correction.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.levelset.wall_contact import WallContactSet  # noqa: E402
from twophase.simulation.config_io import load_experiment_config  # noqa: E402
from twophase.simulation.ns_pipeline import (  # noqa: E402
    TwoPhaseNSSolver,
    _apply_bc,
)
from twophase.simulation.ns_step_state import NSStepRequest  # noqa: E402


def _scalar(backend, value) -> float:
    return float(np.asarray(backend.to_host(value)))


def _field_linf(backend, value) -> float:
    if value is None:
        return 0.0
    xp = backend.xp
    return _scalar(backend, xp.max(xp.abs(xp.asarray(value))))


def _field_minmax(backend, value) -> tuple[float, float]:
    if value is None:
        return 0.0, 0.0
    xp = backend.xp
    array = xp.asarray(value)
    return _scalar(backend, xp.min(array)), _scalar(backend, xp.max(array))


def _face_linf(backend, faces) -> float:
    if faces is None:
        return 0.0
    xp = backend.xp
    return max(_scalar(backend, xp.max(xp.abs(face))) for face in faces)


def _face_div_linf(backend, div_op, faces) -> float:
    if faces is None or not hasattr(div_op, "divergence_from_faces"):
        return 0.0
    xp = backend.xp
    div = div_op.divergence_from_faces([xp.asarray(face) for face in faces])
    return _scalar(backend, xp.max(xp.abs(div)))


def _manual_step(solver, request, *, force_predictor_startup: bool = False):
    state = solver._prepare_step_inputs(request)
    prepared_previous_face_linf = _face_linf(
        solver._backend,
        state.previous_pressure_accel_face_components,
    )
    prepared_previous_face_div = _face_div_linf(
        solver._backend,
        solver._div_op,
        state.previous_pressure_accel_face_components,
    )
    state = solver._advance_interface_stage(state)
    solver._last_interface_projection_fields = state.interface_projection_fields
    state = solver._materialise_step_fields(state)
    rho_min, rho_max = _field_minmax(solver._backend, state.rho)
    mu_min, mu_max = _field_minmax(solver._backend, state.mu_field)
    state = solver._surface_tension_stage(state)
    history_metrics = {
        "conv_ab2_ready": float(bool(solver._conv_ab2_ready)),
        "velocity_bdf2_ready": float(bool(solver._velocity_bdf2_ready)),
        "velocity_prev_linf": max(
            _field_linf(solver._backend, solver._velocity_prev[0]),
            _field_linf(solver._backend, solver._velocity_prev[1]),
        )
        if solver._velocity_prev is not None
        else 0.0,
    }
    if force_predictor_startup:
        solver._conv_ab2_ready = False
        solver._conv_prev = None
        solver._velocity_bdf2_ready = False
        solver._velocity_prev = None
    state = solver._predict_velocity_stage(state)
    _apply_bc(state.u_star, state.v_star, state.bc_hook, solver.bc_type)
    viscous_diag = getattr(solver._viscous_predictor, "last_diagnostics", {})
    viscous_history = list(getattr(solver._viscous_predictor, "last_residual_history", []))
    viscous_residual0 = float(viscous_history[0]) if viscous_history else 0.0
    viscous_residual_min = float(min(viscous_history)) if viscous_history else 0.0
    viscous_residual_growth = (
        float(viscous_history[-1]) / max(viscous_residual0, 1.0e-300)
        if viscous_history
        else 0.0
    )
    predictor_metrics = {
        "prepared_previous_face_linf": prepared_previous_face_linf,
        "prepared_previous_face_div": prepared_previous_face_div,
        "rho_min": rho_min,
        "rho_max": rho_max,
        "mu_min": mu_min,
        "mu_max": mu_max,
        **history_metrics,
        "viscous_dc_final_residual": float(
            viscous_diag.get("viscous_dc_final_residual", 0.0)
        ),
        "viscous_dc_initial_residual": viscous_residual0,
        "viscous_dc_min_residual": viscous_residual_min,
        "viscous_dc_growth": viscous_residual_growth,
        "viscous_dc_corrections": float(
            viscous_diag.get("viscous_dc_corrections", 0.0)
        ),
        "viscous_dc_converged": float(
            viscous_diag.get("viscous_dc_converged", 0.0)
        ),
        "viscous_gmres_info": float(viscous_diag.get("viscous_gmres_info", 0.0)),
        "u_star_linf": _field_linf(solver._backend, state.u_star),
        "v_star_linf": _field_linf(solver._backend, state.v_star),
        "predictor_face_linf": _face_linf(
            solver._backend,
            state.predictor_face_components,
        ),
        "predictor_face_div": _face_div_linf(
            solver._backend,
            solver._div_op,
            state.predictor_face_components,
        ),
        "pressure_history_face_linf": _face_linf(
            solver._backend,
            state.pressure_history_face_components,
        ),
        "pressure_history_face_div": _face_div_linf(
            solver._backend,
            solver._div_op,
            state.pressure_history_face_components,
        ),
    }
    state = solver._solve_pressure_stage(state)
    pressure_metrics = {
        "pressure_increment_linf": _field_linf(
            solver._backend,
            state.pressure_increment,
        ),
        "pressure_base_linf": _field_linf(solver._backend, state.pressure_base),
        "pressure_face_linf": _face_linf(
            solver._backend,
            state.pressure_accel_face_components,
        ),
        "pressure_face_div": _face_div_linf(
            solver._backend,
            solver._div_op,
            state.pressure_accel_face_components,
        ),
        "ppe_dc_relative_l2": float(
            getattr(solver._ppe_solver, "last_diagnostics", {}).get(
                "ppe_dc_final_relative_l2",
                0.0,
            )
        ),
        "ppe_dc_converged": float(
            getattr(solver._ppe_solver, "last_diagnostics", {}).get(
                "ppe_dc_converged",
                0.0,
            )
        ),
    }
    state = solver._correct_velocity_stage(state)
    solver._commit_geometric_phase_state_after_downstream(state)
    if solver._conservative_common_flux_enabled():
        if state.geometric_runtime_material is not None:
            state.conservative_transport_certificate[
                "ao_static_legacy_conservative_publish_skipped"
            ] = True
            solver._conservative_density = None
            solver._conservative_momentum_components = None
        else:
            state = solver._publish_conservative_state(state)
    solver._projected_face_components = state.projected_face_components
    solver._record_step_diagnostics(state)
    corrector_metrics = {
        "projected_face_linf": _face_linf(
            solver._backend,
            state.projected_face_components,
        ),
        "projected_face_div": _face_div_linf(
            solver._backend,
            solver._div_op,
            state.projected_face_components,
        ),
        "u_linf": _field_linf(solver._backend, state.u),
        "v_linf": _field_linf(solver._backend, state.v),
        "diag_ppe_rhs": solver._step_diag.last.get("ppe_rhs_max", 0.0),
        "diag_div_u": solver._step_diag.last.get("div_u_max", 0.0),
    }
    return state, predictor_metrics, pressure_metrics, corrector_metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument(
        "--pressure-history",
        choices=("as_config", "face_acceleration", "pressure_coordinate"),
        default="as_config",
    )
    parser.add_argument(
        "--history-extrapolation",
        choices=("as_config", "constant", "bdf2"),
        default="as_config",
    )
    parser.add_argument(
        "--viscous-solver",
        choices=("as_config", "defect_correction", "gmres"),
        default="as_config",
    )
    parser.add_argument(
        "--viscous-dc-low-operator",
        choices=("as_config", "component", "scalar"),
        default="as_config",
    )
    parser.add_argument(
        "--viscous-spatial",
        choices=("as_config", "ccd_bulk", "conservative_stress", "ccd_stress_legacy"),
        default="as_config",
    )
    parser.add_argument("--viscous-dc-relaxation", type=float)
    parser.add_argument("--viscous-dc-max-iterations", type=int)
    parser.add_argument("--force-predictor-startup", action="store_true")
    parser.add_argument("--backend", choices=("as_env", "cpu", "gpu"), default="as_env")
    args = parser.parse_args()

    if args.backend != "as_env":
        os.environ["TWOPHASE_USE_GPU"] = "1" if args.backend == "gpu" else "0"

    cfg = load_experiment_config(args.config)
    overrides = {"run.debug_diagnostics": True}
    if args.pressure_history != "as_config":
        overrides["run.pressure_history_mode"] = args.pressure_history
    if args.history_extrapolation != "as_config":
        overrides["run.pressure_history_extrapolation"] = args.history_extrapolation
    if args.viscous_solver != "as_config":
        overrides["run.viscous_solver"] = args.viscous_solver
    if args.viscous_dc_low_operator != "as_config":
        overrides["run.viscous_dc_low_operator"] = args.viscous_dc_low_operator
    if args.viscous_spatial != "as_config":
        overrides["run.viscous_spatial_scheme"] = args.viscous_spatial
    if args.viscous_dc_relaxation is not None:
        overrides["run.viscous_dc_relaxation"] = args.viscous_dc_relaxation
    if args.viscous_dc_max_iterations is not None:
        overrides["run.viscous_dc_max_iterations"] = args.viscous_dc_max_iterations
    cfg = cfg.override(**overrides)
    solver = TwoPhaseNSSolver.from_config(cfg)
    backend = solver._backend
    xp = backend.xp

    psi = solver.build_ic(cfg)
    wall_contacts = WallContactSet.detect_from_psi(
        np.asarray(backend.to_host(psi)),
        solver._grid,
        bc_type=solver.bc_type,
    )
    solver.set_wall_contacts(wall_contacts)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    ph = cfg.physics
    p = None
    t = 0.0

    columns = [
        "step",
        "t",
        "dt",
        "prepared_prev_face",
        "prepared_prev_div",
        "rho_min",
        "rho_max",
        "mu_min",
        "mu_max",
        "conv_ready",
        "velocity_ready",
        "velocity_prev",
        "viscous_dc_residual",
        "viscous_dc_residual0",
        "viscous_dc_residual_min",
        "viscous_dc_growth",
        "viscous_dc_corrections",
        "viscous_dc_converged",
        "viscous_gmres_info",
        "u_star",
        "predictor_face",
        "predictor_div",
        "history_face",
        "history_div",
        "pressure_increment",
        "pressure_base",
        "pressure_face",
        "pressure_div",
        "projected_face",
        "projected_div",
        "u",
        "ppe_rhs",
        "div_u",
        "ppe_dc_rel",
        "ppe_dc_converged",
    ]
    print(",".join(columns))
    for step in range(args.steps):
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
        try:
            state, predictor, pressure, corrector = _manual_step(
                solver,
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
                force_predictor_startup=args.force_predictor_startup,
            )
        except ValueError as exc:
            print("FAIL_CLOSE", step + 1, f"{t:.12e}", f"{dt:.12e}", str(exc), sep=",")
            break
        t += dt
        psi, u, v, p = state.psi, state.u, state.v, state.pressure
        del p
        print(
            step + 1,
            f"{t:.12e}",
            f"{dt:.12e}",
            f"{predictor['prepared_previous_face_linf']:.12e}",
            f"{predictor['prepared_previous_face_div']:.12e}",
            f"{predictor['rho_min']:.12e}",
            f"{predictor['rho_max']:.12e}",
            f"{predictor['mu_min']:.12e}",
            f"{predictor['mu_max']:.12e}",
            f"{predictor['conv_ab2_ready']:.12e}",
            f"{predictor['velocity_bdf2_ready']:.12e}",
            f"{predictor['velocity_prev_linf']:.12e}",
            f"{predictor['viscous_dc_final_residual']:.12e}",
            f"{predictor['viscous_dc_initial_residual']:.12e}",
            f"{predictor['viscous_dc_min_residual']:.12e}",
            f"{predictor['viscous_dc_growth']:.12e}",
            f"{predictor['viscous_dc_corrections']:.12e}",
            f"{predictor['viscous_dc_converged']:.12e}",
            f"{predictor['viscous_gmres_info']:.12e}",
            f"{max(predictor['u_star_linf'], predictor['v_star_linf']):.12e}",
            f"{predictor['predictor_face_linf']:.12e}",
            f"{predictor['predictor_face_div']:.12e}",
            f"{predictor['pressure_history_face_linf']:.12e}",
            f"{predictor['pressure_history_face_div']:.12e}",
            f"{pressure['pressure_increment_linf']:.12e}",
            f"{pressure['pressure_base_linf']:.12e}",
            f"{pressure['pressure_face_linf']:.12e}",
            f"{pressure['pressure_face_div']:.12e}",
            f"{corrector['projected_face_linf']:.12e}",
            f"{corrector['projected_face_div']:.12e}",
            f"{max(corrector['u_linf'], corrector['v_linf']):.12e}",
            f"{corrector['diag_ppe_rhs']:.12e}",
            f"{corrector['diag_div_u']:.12e}",
            f"{pressure['ppe_dc_relative_l2']:.12e}",
            f"{pressure['ppe_dc_converged']:.12e}",
            sep=",",
        )


if __name__ == "__main__":
    main()
