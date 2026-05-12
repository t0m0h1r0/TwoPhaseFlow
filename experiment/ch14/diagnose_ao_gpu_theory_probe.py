#!/usr/bin/env python3
"""Short AO-GPU theory probe for ch14 capillary-wave failure analysis."""

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
from twophase.simulation.ns_step_state import NSStepRequest  # noqa: E402


def _scalar(backend, value) -> float:
    return float(np.asarray(backend.to_host(value)))


def _face_linf(backend, faces) -> float:
    xp = backend.xp
    return max(_scalar(backend, xp.max(xp.abs(face))) for face in faces)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--pressure-history", choices=("as_config", "face_acceleration", "pressure_coordinate"), default="as_config")
    parser.add_argument("--history-extrapolation", choices=("as_config", "constant", "bdf2"), default="as_config")
    args = parser.parse_args()

    cfg = load_experiment_config(args.config)
    overrides = {"run.debug_diagnostics": True}
    if args.pressure_history != "as_config":
        overrides["run.pressure_history_mode"] = args.pressure_history
    if args.history_extrapolation != "as_config":
        overrides["run.pressure_history_extrapolation"] = args.history_extrapolation
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

    print(
        "step,t,dt,compat_linf,force_l2,reaction_l2,balanced_l2,"
        "force_face_linf,reaction_face_linf,pressure_residual_l2,"
        "pressure_normal_residual_linf,ppe_rhs,div_u,ke"
    )
    t = 0.0
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
            print(
                "FAIL_CLOSE",
                step + 1,
                f"{t:.12e}",
                f"{dt:.12e}",
                str(exc),
                sep=",",
            )
            break
        t += dt
        phase = solver._geometric_phase_state
        cap = solver._last_geometric_runtime_capillary
        app = solver._last_geometric_runtime_capillary_application
        diag = solver._step_diag.last
        ke = 0.5 * (xp.sum(xp.asarray(u) * xp.asarray(u)) + xp.sum(xp.asarray(v) * xp.asarray(v)))
        print(
            step + 1,
            f"{t:.12e}",
            f"{dt:.12e}",
            f"{_scalar(backend, phase.compatibility_residual_linf):.12e}",
            f"{_scalar(backend, cap.capillary_force_weighted_acceleration_l2):.12e}",
            f"{_scalar(backend, cap.pressure_reaction_weighted_acceleration_l2):.12e}",
            f"{_scalar(backend, app.pressure_balanced_increment_weighted_l2):.12e}",
            f"{_face_linf(backend, cap.capillary_force_face_covectors):.12e}",
            f"{_face_linf(backend, cap.pressure_reaction_face_covectors):.12e}",
            f"{_scalar(backend, cap.young_laplace_residual_l2):.12e}",
            f"{_scalar(backend, cap.young_laplace_normal_residual_linf):.12e}",
            f"{diag.get('ppe_rhs_max', 0.0):.12e}",
            f"{diag.get('div_u_max', 0.0):.12e}",
            f"{_scalar(backend, ke):.12e}",
            sep=",",
        )


if __name__ == "__main__":
    main()
