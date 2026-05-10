#!/usr/bin/env python3
"""Diagnose sharp-volume loss in the ch14 oscillating-droplet stack.

The probe does not tune parameters or change the physical model.  It measures
which discrete map changes the geometric droplet area:

* direct ridge-eikonal reinitialization on the initial fitted grid;
* a short Navier--Stokes prefix using the configured common-flux pipeline;
* the metric volume implied by ``Grid.cell_volumes()``.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.coupling.closed_interface_geometry import liquid_area_2d  # noqa: E402
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver  # noqa: E402
from twophase.simulation.ns_step_state import NSStepRequest  # noqa: E402


CONFIG = ROOT / "experiment/ch14/config/ch14_oscillating_droplet.yaml"


def _host(solver: TwoPhaseNSSolver, value):
    return np.asarray(solver._backend.to_host(value))


def _raw_config(*, constraint: str, uniform: bool = False, static_grid: bool = False):
    raw = yaml.safe_load(CONFIG.read_text())
    raw = copy.deepcopy(raw)
    raw["interface"]["reinitialization"]["profile"]["volume_constraint"] = constraint
    if static_grid:
        raw["grid"]["distribution"]["schedule"] = 0
    if uniform:
        axes = raw["grid"]["distribution"]["axes"]
        axes["x"] = {"type": "uniform"}
        axes["y"] = {"type": "uniform"}
        raw["grid"]["distribution"]["schedule"] = 0
    raw["run"]["time"]["print_every"] = 10**9
    return raw


def _make_solver(*, constraint: str, uniform: bool = False, static_grid: bool = False):
    cfg = ExperimentConfig.from_dict(
        _raw_config(constraint=constraint, uniform=uniform, static_grid=static_grid)
    )
    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    ph = cfg.physics
    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
    return cfg, solver, psi, u, v


def _diffuse_mass(solver: TwoPhaseNSSolver, psi) -> float:
    return float(np.sum(_host(solver, psi) * _host(solver, solver._grid.cell_volumes())))


def _sharp_area(solver: TwoPhaseNSSolver, psi) -> float:
    return float(
        liquid_area_2d(
            xp=np,
            grid=solver._grid,
            psi=_host(solver, psi),
            phase_threshold=0.5,
        )
    )


def _periodic_unique_domain_area(solver: TwoPhaseNSSolver) -> float:
    widths = []
    for coords in solver._grid.coords:
        dx = np.diff(np.asarray(coords, dtype=float))
        widths.append(0.5 * (dx + np.roll(dx, 1)))
    return float(np.sum(widths[0][:, None] * widths[1][None, :]))


def metric_audit() -> None:
    cfg, solver, psi, _u, _v = _make_solver(constraint="diffuse_mass")
    del cfg, psi
    grid_sum = float(np.sum(_host(solver, solver._grid.cell_volumes())))
    true_periodic = _periodic_unique_domain_area(solver)
    h_sums = [float(np.sum(np.asarray(h))) for h in solver._grid.h]
    print(
        "METRIC_AUDIT "
        f"grid_dV_sum={grid_sum:.12e} "
        f"periodic_unique_area={true_periodic:.12e} "
        f"rel_overcount={(grid_sum - true_periodic) / true_periodic:+.6e} "
        f"h_sums={h_sums}"
    )


def direct_reinit_probe() -> None:
    variants = (
        ("dynamic_diffuse", "diffuse_mass", False, False),
        ("dynamic_sharp", "sharp_phase_volume", False, False),
        ("static_diffuse", "diffuse_mass", False, True),
        ("uniform_diffuse", "diffuse_mass", True, False),
        ("uniform_sharp", "sharp_phase_volume", True, False),
    )
    for label, constraint, uniform, static_grid in variants:
        _cfg, solver, psi, _u, _v = _make_solver(
            constraint=constraint,
            uniform=uniform,
            static_grid=static_grid,
        )
        mass0 = _diffuse_mass(solver, psi)
        area0 = _sharp_area(solver, psi)
        try:
            psi_after = solver._reinit.reinitialize(psi)
            mass1 = _diffuse_mass(solver, psi_after)
            area1 = _sharp_area(solver, psi_after)
            print(
                "DIRECT_REINIT "
                f"{label} status=OK "
                f"mass_rel={(mass1 - mass0) / mass0:+.6e} "
                f"sharp_area_rel={(area1 - area0) / area0:+.6e} "
                f"psi_max={float(np.max(_host(solver, psi_after))):.6e}"
            )
        except Exception as exc:  # pragma: no cover - diagnostic CLI path
            print(f"DIRECT_REINIT {label} status=FAIL error={type(exc).__name__}: {exc}")


def short_step_probe(
    steps: int,
    *,
    include_static: bool = False,
    include_uniform: bool = False,
) -> None:
    variants = [
        ("dynamic_diffuse", "diffuse_mass", False, False),
        ("dynamic_sharp", "sharp_phase_volume", False, False),
    ]
    if include_static:
        variants.extend(
            [
                ("static_diffuse", "diffuse_mass", True, False),
                ("static_sharp", "sharp_phase_volume", True, False),
            ]
        )
    if include_uniform:
        variants.extend(
            [
                ("uniform_diffuse", "diffuse_mass", False, True),
                ("uniform_sharp", "sharp_phase_volume", False, True),
            ]
        )
    for label, constraint, static_grid, uniform in variants:
        cfg, solver, psi, u, v = _make_solver(
            constraint=constraint,
            static_grid=static_grid,
            uniform=uniform,
        )
        ph = cfg.physics
        bc_hook = solver.make_bc_hook(cfg)
        mass0 = _diffuse_mass(solver, psi)
        area0 = _sharp_area(solver, psi)
        t = 0.0
        print(f"SHORT_STEP {label} step=0 t={t:.12e} mass_rel=+0.000000e+00 sharp_area_rel=+0.000000e+00")
        checkpoints = {1, 2, 3, 5, 10, steps}
        for step_index in range(steps):
            dt_budget = solver.dt_budget(
                u,
                v,
                ph,
                cfg.run.cfl,
                cfl_advective=cfg.run.cfl_advective,
                cfl_capillary=cfg.run.cfl_capillary,
                cfl_viscous=cfg.run.cfl_viscous,
            )
            dt = float(dt_budget.dt)
            try:
                psi, u, v, _p = solver.step_request(
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
                        step_index=step_index,
                    ),
                    return_host_pressure=False,
                )
            except Exception as exc:  # pragma: no cover - diagnostic CLI path
                print(f"SHORT_STEP {label} step={step_index + 1} status=FAIL error={type(exc).__name__}: {exc}")
                break
            t += dt
            step = step_index + 1
            if step in checkpoints:
                mass = _diffuse_mass(solver, psi)
                area = _sharp_area(solver, psi)
                print(
                    "SHORT_STEP "
                    f"{label} step={step} t={t:.12e} "
                    f"mass_rel={(mass - mass0) / mass0:+.6e} "
                    f"sharp_area_rel={(area - area0) / area0:+.6e} "
                    f"psi_max={float(np.max(_host(solver, psi))):.6e}"
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--skip-steps", action="store_true")
    parser.add_argument("--include-static-steps", action="store_true")
    parser.add_argument("--include-uniform-steps", action="store_true")
    args = parser.parse_args()

    metric_audit()
    direct_reinit_probe()
    if not args.skip_steps:
        short_step_probe(
            max(1, args.steps),
            include_static=args.include_static_steps,
            include_uniform=args.include_uniform_steps,
        )


if __name__ == "__main__":
    main()
