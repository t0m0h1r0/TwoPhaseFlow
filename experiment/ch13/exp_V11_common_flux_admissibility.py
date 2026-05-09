#!/usr/bin/env python3
"""[V11] Conservative common-flux admissibility gate.

Paper ref: Chapter 13 V11 (planned; common-flux integration gate).

Goal
----
Verify that the latest canonical ch14 rising-bubble stack reaches the
conservative_common_flux runtime route when reduced to a small verification
grid, and that inadmissible q-only reinitialization or dynamic remap settings
fail closed instead of silently becoming Chapter 13 evidence.

Setup
-----
  Base config: experiment/ch14/config/ch14_rising_bubble.yaml.
  Runtime override: grid.cells = [16, 32], run.time.dt = 1e-6,
  run.time.max_steps = 2, output to experiment/ch13/results/V11...
  Positive gate: two short NS steps, common FCCD ledger, conservative density
  and momentum present, affine density closure, common-flux energy certificate,
  checkpoint roundtrip of conservative state.
  Negative gates: reinitialization every step and dynamic grid remap.

Usage
-----
  python experiment/ch13/exp_V11_common_flux_admissibility.py
  python experiment/ch13/exp_V11_common_flux_admissibility.py --plot-only
"""

from __future__ import annotations

import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np
import yaml

from twophase.levelset.wall_contact import WallContactSet
from twophase.simulation.checkpoint import load_checkpoint, save_checkpoint
from twophase.simulation.config_io import ExperimentConfig
from twophase.simulation.conservative_transport import ConservativeCommonFluxTransport
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.simulation.ns_step_state import NSStepRequest
from twophase.tools.experiment import (
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()
ROOT = pathlib.Path(__file__).resolve().parents[2]
CANONICAL_CONFIG = ROOT / "experiment" / "ch14" / "config" / "ch14_rising_bubble.yaml"
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = ROOT / "paper" / "figures" / "ch13_v11_common_flux_admissibility"

GRID_CELLS = (16, 32)
DT = 1.0e-6
MAX_STEPS = 2
TOL_AFFINE = 1.0e-9
TOL_ENERGY = 1.0e-9
TOL_CONSERVATION = 1.0e-8


def _load_base_raw() -> dict:
    with CANONICAL_CONFIG.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _runtime_raw(kind: str = "positive") -> dict:
    raw = copy.deepcopy(_load_base_raw())
    raw.setdefault("grid", {})["cells"] = list(GRID_CELLS)
    raw.setdefault("run", {}).setdefault("time", {})
    time_cfg = raw["run"]["time"]
    time_cfg["final"] = float(MAX_STEPS * DT)
    time_cfg["max_steps"] = int(MAX_STEPS)
    time_cfg["print_every"] = 1
    time_cfg.pop("cfl", None)
    time_cfg["dt"] = float(DT)
    raw["run"].setdefault("debug", {})["step_diagnostics"] = True
    raw.setdefault("output", {})["dir"] = str(OUT)
    raw["output"]["save_npz"] = True
    raw["output"]["snapshots"] = {"times": []}
    raw["output"].pop("figures", None)
    raw["output"].pop("checkpoints", None)

    if kind == "q_only_reinit":
        raw["interface"]["reinitialization"]["schedule"]["every_steps"] = 1
        raw["interface"]["reinitialization"]["schedule"]["mode"] = "fixed"
    elif kind == "dynamic_grid_remap":
        raw["grid"].setdefault("distribution", {})["schedule"] = 1
    elif kind != "positive":
        raise ValueError(f"unknown V11 runtime kind {kind!r}")
    return raw


def _write_runtime_config(kind: str) -> tuple[ExperimentConfig, pathlib.Path]:
    raw = _runtime_raw(kind)
    path = OUT / f"_V11_common_flux_admissibility_{kind}.yaml.out"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return ExperimentConfig.from_dict(raw), path


def _initial_state(cfg: ExperimentConfig):
    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    psi_initial_host = np.asarray(solver.backend.to_host(psi))
    wall_contacts = WallContactSet.detect_from_psi(
        psi_initial_host,
        solver._grid,
        bc_type=solver.bc_type,
    )
    solver.set_wall_contacts(wall_contacts)
    u, v = solver.build_velocity(cfg, psi)
    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(
            psi,
            u,
            v,
            cfg.physics.rho_l,
            cfg.physics.rho_g,
        )
    return solver, psi, u, v, solver.make_bc_hook(cfg)


def _copy_conservative_inputs(solver, psi, u, v, cfg: ExperimentConfig):
    xp = solver.backend.xp
    density = getattr(solver, "_conservative_density", None)
    if density is None:
        density = cfg.physics.rho_g + (cfg.physics.rho_l - cfg.physics.rho_g) * psi
    momentum = getattr(solver, "_conservative_momentum_components", None)
    if momentum is None:
        momentum = [density * u, density * v]
    return xp.array(density, copy=True), [xp.array(component, copy=True) for component in momentum]


def _integral(solver, value) -> float:
    xp = solver.backend.xp
    total = xp.sum(xp.asarray(value) * xp.asarray(solver._grid.cell_volumes()))
    return _scalar(solver, total)


def _scalar(solver, value) -> float:
    value = solver.backend.to_host(value)
    arr = np.asarray(value)
    return float(arr.item() if arr.shape == () else arr)


def _positive_gate() -> dict:
    cfg, cfg_path = _write_runtime_config("positive")
    solver, psi, u, v, bc_hook = _initial_state(cfg)
    ph = cfg.physics
    p = None
    pre_density = None
    pre_momentum = None
    for step_index in range(MAX_STEPS):
        pre_density, pre_momentum = _copy_conservative_inputs(solver, psi, u, v, cfg)
        psi, u, v, p = solver.step_request(
            NSStepRequest(
                psi=psi,
                u=u,
                v=v,
                dt=DT,
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

    ledger = getattr(solver._transport, "last_transport_ledger", None)
    if ledger is None:
        raise AssertionError("V11 positive gate did not retain a common-flux ledger")
    transport = ConservativeCommonFluxTransport(
        solver.backend,
        solver._grid,
        solver._fccd,
        divergence_operator=solver._div_op,
    )
    certificate = transport.advance(
        pre_density,
        tuple(pre_momentum),
        ledger,
        rho_l=ph.rho_l,
        rho_g=ph.rho_g,
    )
    xp = solver.backend.xp
    conservative_density = getattr(solver, "_conservative_density", None)
    conservative_momentum = getattr(solver, "_conservative_momentum_components", None)
    if conservative_density is None or conservative_momentum is None:
        raise AssertionError("V11 positive gate did not publish conservative state")
    expected_density = ph.rho_g + (ph.rho_l - ph.rho_g) * xp.asarray(psi)
    affine_error = _scalar(solver, xp.max(xp.abs(conservative_density - expected_density)))
    certificate_density_error = _scalar(
        solver,
        xp.max(xp.abs(certificate.density - expected_density)),
    )
    checkpoint_path = OUT / "V11_common_flux_checkpoint.npz"
    save_checkpoint(
        checkpoint_path,
        solver=solver,
        psi=psi,
        u=u,
        v=v,
        p=p,
        t=MAX_STEPS * DT,
        step=MAX_STEPS,
        config_path=cfg_path,
        results={"times": np.asarray([MAX_STEPS * DT])},
        snapshots=[],
        debug_history=[],
        state_phase="post_step",
    )
    restored_solver = TwoPhaseNSSolver.from_config(cfg)
    restored = load_checkpoint(checkpoint_path, solver=restored_solver, config_path=cfg_path)
    restored_density = getattr(restored_solver, "_conservative_density", None)
    restored_momentum = getattr(restored_solver, "_conservative_momentum_components", None)

    mass_delta = _integral(solver, certificate.density) - _integral(solver, pre_density)
    momentum_delta = [
        _integral(solver, certificate.momentum_components[axis])
        - _integral(solver, pre_momentum[axis])
        for axis in range(2)
    ]
    return {
        "candidate": "canonical_ch14_reduced_common_flux",
        "backend": solver.backend.device,
        "grid_nx": int(cfg.grid.NX),
        "grid_ny": int(cfg.grid.NY),
        "steps": int(MAX_STEPS),
        "dt": float(DT),
        "momentum_form_ok": int(solver._momentum_form == "conservative_common_flux"),
        "reinit_disabled": int(solver._interface_runtime.reinit_every == 0),
        "dynamic_remap_disabled": int(solver._interface_runtime.rebuild_freq == 0),
        "mass_correction_disabled": int(not solver._transport.mass_correction),
        "ledger_present": 1,
        "ledger_stage_count": int(len(ledger.stages)),
        "ledger_clipless": int(ledger.clip_bounds is None),
        "ledger_unprojected": int(not any(stage.post_stage_projected for stage in ledger.stages)),
        "ledger_zero_velocity": int(getattr(ledger, "zero_velocity", False)),
        "certificate_status": certificate.certificate_status,
        "certificate_energy_delta": _scalar(solver, certificate.kinetic_energy_delta),
        "certificate_density_error": certificate_density_error,
        "mass_delta": mass_delta,
        "momentum_x_delta": momentum_delta[0],
        "momentum_y_delta": momentum_delta[1],
        "affine_density_error": affine_error,
        "conservative_density_present": int(conservative_density is not None),
        "conservative_momentum_present": int(conservative_momentum is not None),
        "checkpoint_restored": int(
            restored_density is not None
            and restored_momentum is not None
            and tuple(restored["psi"].shape) == tuple(psi.shape)
        ),
    }


def _negative_gate(kind: str) -> dict:
    cfg, _cfg_path = _write_runtime_config(kind)
    solver, psi, u, v, bc_hook = _initial_state(cfg)
    ph = cfg.physics
    try:
        solver.step_request(
            NSStepRequest(
                psi=psi,
                u=u,
                v=v,
                dt=DT,
                rho_l=ph.rho_l,
                rho_g=ph.rho_g,
                sigma=ph.sigma,
                mu=ph.mu,
                g_acc=ph.g_acc,
                rho_ref=ph.rho_ref,
                mu_l=ph.mu_l,
                mu_g=ph.mu_g,
                bc_hook=bc_hook,
                step_index=1,
            ),
            return_host_pressure=False,
        )
    except NotImplementedError as exc:
        return {"candidate": kind, "rejected": 1, "message": str(exc)}
    except ValueError as exc:
        return {"candidate": kind, "rejected": 1, "message": str(exc)}
    return {"candidate": kind, "rejected": 0, "message": "unexpectedly accepted"}


def _columns(rows: list[dict]) -> dict:
    keys = sorted({key for row in rows for key in row})
    return {key: np.asarray([row.get(key, "") for row in rows]) for key in keys}


def run_all() -> dict:
    results = {
        "positive": _columns([_positive_gate()]),
        "negative": _columns([
            _negative_gate("q_only_reinit"),
            _negative_gate("dynamic_grid_remap"),
        ]),
    }
    _assert_acceptance(results)
    return results


def _assert_acceptance(results: dict) -> None:
    positive = results["positive"]
    required_flags = (
        "momentum_form_ok",
        "reinit_disabled",
        "dynamic_remap_disabled",
        "mass_correction_disabled",
        "ledger_present",
        "ledger_clipless",
        "ledger_unprojected",
        "conservative_density_present",
        "conservative_momentum_present",
        "checkpoint_restored",
    )
    for key in required_flags:
        if int(np.asarray(positive[key])[0]) != 1:
            raise AssertionError(f"V11 positive gate failed flag {key}")
    if int(np.asarray(positive["ledger_stage_count"])[0]) != 3:
        raise AssertionError("V11 common-flux ledger did not record three RK stages")
    if str(np.asarray(positive["certificate_status"])[0]) != "passed":
        raise AssertionError("V11 common-flux energy certificate did not pass")
    if float(np.asarray(positive["certificate_energy_delta"], dtype=float)[0]) > TOL_ENERGY:
        raise AssertionError("V11 common-flux transport increased kinetic energy")
    if float(np.asarray(positive["affine_density_error"], dtype=float)[0]) > TOL_AFFINE:
        raise AssertionError("V11 conservative density is not affine in q")
    if float(np.asarray(positive["certificate_density_error"], dtype=float)[0]) > TOL_AFFINE:
        raise AssertionError("V11 certificate density does not match q endpoint")
    if float(abs(np.asarray(positive["mass_delta"], dtype=float)[0])) > TOL_CONSERVATION:
        raise AssertionError("V11 common-flux certificate is not mass conservative")
    if not np.all(np.asarray(results["negative"]["rejected"], dtype=int) == 1):
        raise AssertionError("V11 negative controls were not fail-closed")


def make_figures(results: dict) -> None:
    positive = results["positive"]
    negative = results["negative"]
    fig, (ax_flags, ax_neg) = plt.subplots(1, 2, figsize=(10.5, 4.0))
    flag_names = [
        "momentum_form_ok",
        "ledger_clipless",
        "ledger_unprojected",
        "checkpoint_restored",
    ]
    ax_flags.bar(
        np.arange(len(flag_names)),
        [int(np.asarray(positive[name])[0]) for name in flag_names],
        color="0.35",
    )
    ax_flags.set_ylim(0, 1.1)
    ax_flags.set_xticks(np.arange(len(flag_names)), flag_names, rotation=25, ha="right")
    ax_flags.set_ylabel("pass flag")
    ax_flags.set_title("positive reduced-config gate")

    labels = [str(value) for value in np.asarray(negative["candidate"])]
    ax_neg.bar(
        np.arange(len(labels)),
        np.asarray(negative["rejected"], dtype=int),
        color="0.35",
    )
    ax_neg.set_ylim(0, 1.1)
    ax_neg.set_xticks(np.arange(len(labels)), labels, rotation=25, ha="right")
    ax_neg.set_ylabel("rejected")
    ax_neg.set_title("fail-close controls")
    fig.suptitle("V11 conservative common-flux admissibility")
    save_figure(fig, OUT / "V11_common_flux_admissibility", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    positive = results["positive"]
    negative = results["negative"]
    print("V11 backend:", str(np.asarray(positive["backend"])[0]))
    print("V11 ledger stages:", int(np.asarray(positive["ledger_stage_count"])[0]))
    print("V11 certificate energy delta:",
          f"{float(np.asarray(positive['certificate_energy_delta'], dtype=float)[0]):.3e}")
    print("V11 affine density error:",
          f"{float(np.asarray(positive['affine_density_error'], dtype=float)[0]):.3e}")
    print("V11 negative controls rejected:",
          f"{int(np.sum(np.asarray(negative['rejected'], dtype=int)))} / {len(negative['rejected'])}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    _assert_acceptance(results)
    make_figures(results)
    print_summary(results)
    print(f"==> V11 outputs in {OUT}")


if __name__ == "__main__":
    main()
