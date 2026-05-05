"""In-memory ch14 diagnostic variants derived from canonical YAML files.

Checked-in YAMLs are limited to one file per experiment type. Short gates,
diagnostic probes, and historical N64 controls must be built from those
canonical files at runtime instead of adding more YAML files under
``experiment/ch14/config``.
"""

from __future__ import annotations

import copy
import pathlib

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "experiment/ch14/config"


def load_canonical_yaml(stem: str) -> dict:
    path = CONFIG_DIR / f"{stem}.yaml"
    return copy.deepcopy(yaml.safe_load(path.read_text()))


def _set_axis_alpha(raw: dict, alpha: float) -> None:
    axes = raw["grid"]["distribution"]["axes"]
    for axis in ("x", "y"):
        axes[axis]["monitors"]["interface"]["alpha"] = float(alpha)


def _replace_pressure_snapshot_with_hodge(raw: dict) -> None:
    for figure in raw["output"].get("figures", []):
        if figure.get("type") == "snapshot_series" and figure.get("field") == "pressure":
            figure["field"] = "pressure_hodge"
            figure["file_prefix"] = "pressure_hodge_t"


def _set_oscillating_omega(raw: dict, omega0: float) -> None:
    for figure in raw["output"].get("figures", []):
        analytical = figure.get("analytical")
        if isinstance(analytical, dict) and analytical.get("formula") == "prosperetti":
            analytical["omega0"] = float(omega0)


def n64_static_like_oscillating(
    *,
    alpha: float = 2.0,
    static_grid: bool = False,
    output_name: str = "ch14_static_droplet_n64_alpha2_like_oscillating",
) -> dict:
    """Return the historical N64 dynamic-stack static-droplet control."""

    raw = load_canonical_yaml("ch14_static_droplet")
    raw["grid"]["cells"] = [64, 64]
    raw["grid"]["distribution"]["schedule"] = 0 if static_grid else 1
    _set_axis_alpha(raw, alpha)

    raw["interface"]["geometry"]["curvature"]["cap"] = 40.0
    raw["interface"]["reinitialization"]["schedule"]["every_steps"] = 0
    raw["numerics"]["interface"].pop("tracking", None)

    terms = raw["numerics"]["momentum"]["terms"]
    terms["convection"]["time_integrator"] = "imex_bdf2"
    terms["viscosity"]["time_integrator"] = "implicit_bdf2"
    terms["viscosity"]["solver"] = {
        "kind": "defect_correction",
        "tolerance": 1.0e-8,
        "corrections": {"max_iterations": 3, "relaxation": 0.8},
    }

    time = raw["run"]["time"]
    time.pop("dt", None)
    time["final"] = 1.5
    time["cfl"] = 0.2
    time["print_every"] = 200

    raw["output"]["dir"] = f"results/{output_name}"
    raw["output"]["snapshots"]["interval"] = 0.05
    return raw


def n64_oscillating_droplet(
    *,
    alpha: float = 4.0,
    dc_iterations: int | None = None,
    one_period: bool = False,
    output_name: str = "ch14_oscillating_droplet_n64",
) -> dict:
    """Return a historical N64 oscillating-droplet diagnostic control."""

    raw = load_canonical_yaml("ch14_oscillating_droplet")
    raw["grid"]["cells"] = [64, 64]
    _set_axis_alpha(raw, alpha)
    raw["initial_condition"]["objects"][0]["semi_axes"] = [0.275, 0.225]
    raw["physics"]["surface_tension"] = 0.072
    _set_oscillating_omega(raw, 0.167435)

    if dc_iterations is not None:
        raw["numerics"]["projection"]["poisson"]["solver"]["corrections"][
            "max_iterations"
        ] = int(dc_iterations)

    raw["output"]["dir"] = f"results/{output_name}"
    if one_period:
        raw["diagnostics"] = [
            "volume_conservation",
            "kinetic_energy",
            "deformation",
            "signed_deformation",
            "pressure_contrast",
        ]
        raw["interface"]["geometry"]["curvature"] = {
            "method": "transport_variational_p2_ale_discrete_gradient"
        }
        raw["run"]["time"]["final"] = 37.52611644626026
        raw["output"]["snapshots"]["interval"] = 1.0
        _replace_pressure_snapshot_with_hodge(raw)

    return raw
