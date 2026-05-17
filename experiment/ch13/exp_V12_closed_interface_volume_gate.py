#!/usr/bin/env python3
"""[V12] Closed-interface volume-admission gate for Chapter 14.2.

Paper refs: Chapter 13 V12 and Chapter 14.2.

Symbol map:
    V_P1   -> ``sharp_area``    P1/marching-squares liquid area
    M_psi  -> ``diffuse_mass``  nodal diffuse CLS mass
    G_h    -> ``solver._grid``  current nonuniform metric epoch

This gate does not tune the oscillating-droplet benchmark.  It checks the
current Chapter 14.2 YAML boundary and records that the older
``sharp_phase_volume`` Ridge--Eikonal invariant is not an admissible patch for
the current ``active_geometry_capillary`` state space.  The gate also runs a
short current-config prefix and measures both diffuse mass and sharp P1 area.
"""

from __future__ import annotations

import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np
import yaml

from experiment.ch14.diagnose_droplet_volume_rca import (  # noqa: E402
    CONFIG,
    _diffuse_mass,
    _periodic_unique_domain_area,
    _sharp_area,
)
from twophase.simulation.config_models import ExperimentConfig  # noqa: E402
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver  # noqa: E402
from twophase.simulation.ns_step_state import NSStepRequest  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = ROOT / "paper" / "figures" / "ch13_v12_closed_interface_volume_gate"


def _columns(rows: list[dict]) -> dict[str, np.ndarray]:
    keys = sorted({key for row in rows for key in row})
    return {key: np.asarray([row.get(key, "") for row in rows]) for key in keys}


def _rows(table: dict[str, np.ndarray]) -> list[dict]:
    keys = list(table.keys())
    n = len(np.asarray(table[keys[0]])) if keys else 0
    return [{key: np.asarray(table[key])[i].item() for key in keys} for i in range(n)]


def _relative(new: float, old: float) -> float:
    return float((new - old) / max(abs(old), 1.0e-30))


def _base_raw() -> dict:
    raw = yaml.safe_load(CONFIG.read_text())
    raw = copy.deepcopy(raw)
    raw["run"]["time"]["print_every"] = 10**9
    return raw


def _build_solver(raw: dict):
    cfg = ExperimentConfig.from_dict(raw)
    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    ph = cfg.physics
    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
    return cfg, solver, psi, u, v


def _variant_raws() -> list[tuple[str, dict]]:
    current = _base_raw()

    sharp_on_compat = _base_raw()
    sharp_on_compat["interface"]["reinitialization"]["profile"][
        "volume_constraint"
    ] = "sharp_phase_volume"

    ridge_on_active = _base_raw()
    ridge_on_active["interface"]["reinitialization"]["algorithm"] = "ridge_eikonal"
    ridge_on_active["interface"]["reinitialization"]["profile"][
        "volume_constraint"
    ] = "sharp_phase_volume"

    return [
        ("current_active_geometry", current),
        ("sharp_volume_on_compatibility_projection", sharp_on_compat),
        ("ridge_eikonal_on_active_geometry", ridge_on_active),
    ]


def _config_rows() -> list[dict]:
    rows: list[dict] = []
    for label, raw in _variant_raws():
        reinit = raw["interface"]["reinitialization"]
        profile = reinit.get("profile", {})
        try:
            cfg, _solver, _psi, _u, _v = _build_solver(raw)
            rows.append(
                {
                    "label": label,
                    "status": "ok",
                    "error": "",
                    "state_space": str(raw["interface"].get("state_space", "")),
                    "algorithm": str(reinit.get("algorithm", "")),
                    "volume_constraint": str(profile.get("volume_constraint", "default")),
                    "parsed_reinit_method": str(cfg.run.reinit_method),
                    "parsed_volume_constraint": str(cfg.run.reinit_volume_constraint),
                }
            )
        except Exception as exc:  # pragma: no cover - diagnostic CLI path
            rows.append(
                {
                    "label": label,
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "state_space": str(raw["interface"].get("state_space", "")),
                    "algorithm": str(reinit.get("algorithm", "")),
                    "volume_constraint": str(profile.get("volume_constraint", "default")),
                    "parsed_reinit_method": "",
                    "parsed_volume_constraint": "",
                }
            )
    return rows


def _metric_rows() -> list[dict]:
    _cfg, solver, psi, _u, _v = _build_solver(_base_raw())
    del psi
    grid_sum = float(np.sum(solver._backend.to_host(solver._grid.cell_volumes())))
    physical = _periodic_unique_domain_area(solver)
    return [
        {
            "metric": "periodic_metric_area",
            "grid_dv_sum": grid_sum,
            "periodic_unique_area": physical,
            "relative_overcount": _relative(grid_sum, physical),
        }
    ]


def _short_prefix_rows(steps: int) -> list[dict]:
    cfg, solver, psi, u, v = _build_solver(_base_raw())
    ph = cfg.physics
    bc_hook = solver.make_bc_hook(cfg)
    mass0 = _diffuse_mass(solver, psi)
    area0 = _sharp_area(solver, psi)
    rows = [
        {
            "step": 0,
            "status": "ok",
            "time": 0.0,
            "mass_rel": 0.0,
            "sharp_area_rel": 0.0,
            "psi_max": float(np.max(solver._backend.to_host(psi))),
        }
    ]
    t = 0.0
    for step_index in range(max(1, steps)):
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
            t += dt
            status = "ok"
            mass = _diffuse_mass(solver, psi)
            area = _sharp_area(solver, psi)
            mass_rel = _relative(mass, mass0)
            sharp_area_rel = _relative(area, area0)
            psi_max = float(np.max(solver._backend.to_host(psi)))
        except Exception as exc:  # pragma: no cover - diagnostic CLI path
            status = f"error:{type(exc).__name__}: {exc}"
            mass_rel = np.nan
            sharp_area_rel = np.nan
            psi_max = np.nan
        rows.append(
            {
                "step": step_index + 1,
                "status": status,
                "time": t,
                "mass_rel": mass_rel,
                "sharp_area_rel": sharp_area_rel,
                "psi_max": psi_max,
            }
        )
        if not status.startswith("ok"):
            break
    return rows


def compute_results(steps: int) -> dict:
    return {
        "config_rows": _columns(_config_rows()),
        "metric_rows": _columns(_metric_rows()),
        "short_rows": _columns(_short_prefix_rows(steps)),
        "summary": {
            "requested_steps": int(max(1, steps)),
            "one_period_production_admissible": 0,
        },
    }


def assert_acceptance(results: dict) -> None:
    config = {str(row["label"]): row for row in _rows(results["config_rows"])}
    if str(config["current_active_geometry"]["status"]) != "ok":
        raise AssertionError("V12 current active-geometry config did not build")
    for label in (
        "sharp_volume_on_compatibility_projection",
        "ridge_eikonal_on_active_geometry",
    ):
        if str(config[label]["status"]) != "error":
            raise AssertionError(f"V12 invalid variant {label} was not rejected")


def make_figure(results: dict) -> None:
    config = _rows(results["config_rows"])
    short = _rows(results["short_rows"])
    metric = _rows(results["metric_rows"])[0]

    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.0))
    ax_cfg, ax_short, ax_metric = axes

    labels = [str(row["label"]) for row in config]
    status = [1.0 if str(row["status"]) == "ok" else 0.0 for row in config]
    ax_cfg.bar(np.arange(len(labels)), status, color="0.3")
    ax_cfg.set_ylim(-0.05, 1.05)
    ax_cfg.set_yticks([0, 1], ["rejected", "builds"])
    ax_cfg.set_xticks(np.arange(len(labels)), labels, rotation=30, ha="right")
    ax_cfg.set_title("config admission")

    steps = [int(row["step"]) for row in short]
    mass_rel = [float(row["mass_rel"]) for row in short]
    sharp_rel = [float(row["sharp_area_rel"]) for row in short]
    ax_short.plot(steps, mass_rel, marker="o", label="diffuse mass")
    ax_short.plot(steps, sharp_rel, marker="s", label="P1 sharp area")
    ax_short.axhline(0.0, color="0.1", linewidth=0.8)
    ax_short.set_xlabel("step")
    ax_short.set_ylabel("relative drift")
    ax_short.set_title("current-config prefix")
    ax_short.legend(fontsize=7)

    ax_metric.bar(
        [0],
        [float(metric["relative_overcount"])],
        color="0.35",
    )
    ax_metric.axhline(0.0, color="0.1", linewidth=0.8)
    ax_metric.set_xticks([0], ["periodic metric"])
    ax_metric.set_ylabel("relative overcount")
    ax_metric.set_title("metric audit")

    fig.suptitle("V12 closed-interface volume-admission gate")
    fig.tight_layout()
    save_figure(fig, OUT / "V12_closed_interface_volume_gate", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    for row in _rows(results["config_rows"]):
        print(
            f"V12 config {row['label']}: "
            f"status={row['status']}, "
            f"algorithm={row['algorithm']}, "
            f"volume_constraint={row['volume_constraint']}, "
            f"parsed_method={row['parsed_reinit_method']}, "
            f"parsed_volume={row['parsed_volume_constraint']}"
        )
        if str(row["error"]):
            print(f"V12 config {row['label']} error={row['error']}")
    metric = _rows(results["metric_rows"])[0]
    print(
        "V12 metric: "
        f"grid_dv_sum={float(metric['grid_dv_sum']):.12e}, "
        f"periodic_unique_area={float(metric['periodic_unique_area']):.12e}, "
        f"relative_overcount={float(metric['relative_overcount']):+.6e}"
    )
    for row in _rows(results["short_rows"]):
        print(
            f"V12 prefix step={int(row['step'])}: "
            f"status={row['status']}, "
            f"t={float(row['time']):.12e}, "
            f"mass_rel={float(row['mass_rel']):+.6e}, "
            f"sharp_area_rel={float(row['sharp_area_rel']):+.6e}"
        )
    print(f"==> V12 outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument(
        "--steps",
        type=int,
        default=2,
        help="Number of short current-config prefix steps to run.",
    )
    args = parser.parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = compute_results(args.steps)
        save_results(NPZ, results)
    assert_acceptance(results)
    make_figure(results)
    print_summary(results)


if __name__ == "__main__":
    main()
