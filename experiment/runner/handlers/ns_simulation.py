"""ch14 NS-simulation handlers — capillary wave and circle-interface cases.

These handlers consume the ``ExperimentConfig`` schema (top-level
``grid``/``physics``/``run``/``output``/``initial_condition``...) loaded
via ``twophase.simulation.config_io.load_experiment_config`` and drive
``twophase.simulation.ns_pipeline.run_simulation``.

Dispatch (registered handler keys mirror ``initial_condition.type``
values found in ch14 YAMLs):

  capillary_wave  → CapillaryWaveHandler
  circle          → CircleInterfaceHandler
  ellipse         → CircleInterfaceHandler
  perturbed_circle → CircleInterfaceHandler

Both share the same lifecycle (``run`` for live simulation, ``plot`` for
plot-only/regenerate from saved data) and only differ semantically.
"""

from __future__ import annotations

import pathlib
import pickle
import sys

import matplotlib.pyplot as plt
import numpy as np

from ..registry import ExperimentHandler, register_handler


# ── Shared lifecycle helpers ──────────────────────────────────────────────────

def _add_snapshot_series(flat: dict, snaps) -> None:
    """Store field snapshots as explicit time-series arrays in data.npz."""
    if not snaps:
        return

    flat["fields/times"] = np.asarray([snap["t"] for snap in snaps], dtype=float)
    for field in ("psi", "u", "v", "p", "rho"):
        if field in snaps[0]:
            flat[f"fields/{field}"] = np.stack(
                [np.asarray(snap[field]) for snap in snaps], axis=0,
            )
    if "p" in snaps[0]:
        flat["fields/pressure"] = flat["fields/p"]
    if "u" in snaps[0] and "v" in snaps[0]:
        flat["fields/velocity"] = np.stack(
            [
                np.stack([np.asarray(snap["u"]), np.asarray(snap["v"])], axis=0)
                for snap in snaps
            ],
            axis=0,
        )
    if "grid_coords" in snaps[0]:
        for axis, coord in enumerate(snaps[0]["grid_coords"]):
            flat[f"fields/grid_coords/{axis}"] = np.asarray(coord)


def _snapshots_from_field_series(results: dict) -> list[dict]:
    """Reconstruct plot snapshots from field arrays saved in data.npz."""
    if "fields/times" not in results:
        return []

    fields = {
        "psi": "fields/psi",
        "u": "fields/u",
        "v": "fields/v",
        "p": "fields/pressure" if "fields/pressure" in results else "fields/p",
        "rho": "fields/rho",
    }
    grid_coords = []
    axis = 0
    while f"fields/grid_coords/{axis}" in results:
        grid_coords.append(np.asarray(results[f"fields/grid_coords/{axis}"]))
        axis += 1

    snaps = []
    for index, time in enumerate(np.asarray(results["fields/times"])):
        snap = {"t": float(time)}
        for field, key in fields.items():
            if key in results:
                snap[field] = np.asarray(results[key][index])
        if grid_coords:
            snap["grid_coords"] = [coord.copy() for coord in grid_coords]
        snaps.append(snap)
    return snaps


def _run_single(cfg, label: str, outdir: pathlib.Path) -> dict:
    from twophase.simulation.ns_pipeline import run_simulation
    from twophase.tools.plot_factory import generate_figures
    from twophase.tools.experiment import save_results

    outdir.mkdir(parents=True, exist_ok=True)
    npz_path = outdir / "data.npz"

    ph = cfg.physics
    print(f"[{label}] σ={ph.sigma:.5f}  μ_l/μ_g={ph.mu_l:.5f}/{ph.mu_g:.5f}"
          f"  ρ_l/ρ_g={ph.rho_l / ph.rho_g:.0f}")
    print(f"[{label}] Running simulation...")

    results = run_simulation(cfg)

    if cfg.output.save_npz:
        flat: dict = {}
        for k, v in results.items():
            if isinstance(v, np.ndarray):
                flat[k] = v
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    flat[f"{k}/{kk}"] = np.asarray(vv)
        _add_snapshot_series(flat, results.get("snapshots"))
        save_results(npz_path, flat)

        snaps = results.get("snapshots")
        if snaps:
            with open(outdir / "snapshots.pkl", "wb") as fh:
                pickle.dump(snaps, fh)

    generate_figures(cfg, results, outdir)
    print(f"[{label}] saved → {outdir}")
    return results


def _run_sweep(cfg, label: str, outdir: pathlib.Path) -> dict:
    from twophase.simulation.ns_pipeline import run_simulation
    from twophase.tools.plot_factory import generate_figures
    from twophase.tools.experiment import save_results

    outdir.mkdir(parents=True, exist_ok=True)
    npz_path = outdir / "data.npz"

    cases = cfg.sweep
    flat: dict[str, np.ndarray] = {}
    case_labels: list[str] = []

    for case in cases:
        case_label = case.get("label", "case")
        overrides = case.get("overrides", {})
        case_labels.append(case_label)

        print(f"\n[{label}] === {case_label} ===")
        cfg_case = cfg.override(**overrides)

        results = run_simulation(cfg_case)
        for k, v in results.items():
            if isinstance(v, np.ndarray):
                flat[f"{case_label}/{k}"] = v

        case_dir = outdir / case_label
        generate_figures(cfg_case, results, case_dir)

    flat["_case_labels"] = np.array(case_labels, dtype=object)
    if cfg.output.save_npz:
        save_results(npz_path, flat)
    _plot_sweep_summary(cfg, cases, flat, label, outdir)

    print(f"\n[{label}] sweep complete → {outdir}")
    return flat


def _plot_sweep_summary(cfg, cases, flat, label, outdir):
    from twophase.tools.experiment import COLORS

    diag_keys = [d for d in cfg.diagnostics if d != "kinetic_energy"]
    if not diag_keys:
        return

    primary = diag_keys[0]
    fig, ax = plt.subplots(figsize=(6, 4))

    for i, case in enumerate(cases):
        cl = case.get("label", "case")
        t_key = f"{cl}/times"
        d_key = f"{cl}/{primary}"
        if t_key in flat and d_key in flat:
            ax.plot(flat[t_key], flat[d_key],
                    color=COLORS[i % len(COLORS)], label=cl)

    ax.set_xlabel("t")
    ax.set_ylabel(primary)
    ax.set_title(f"{label} — sweep summary")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.savefig(outdir / "sweep_summary.pdf", bbox_inches="tight")
    plt.close(fig)


def _plot_only(cfg, label: str, outdir: pathlib.Path) -> None:
    from twophase.tools.plot_factory import generate_figures

    npz_path = outdir / "data.npz"
    if not npz_path.exists():
        print(f"[{label}] ERROR: {npz_path} not found. Run first without --plot-only.")
        sys.exit(1)

    results = dict(np.load(npz_path, allow_pickle=True))

    snap_path = outdir / "snapshots.pkl"
    if snap_path.exists():
        with open(snap_path, "rb") as fh:
            results["snapshots"] = pickle.load(fh)
    else:
        snaps = _snapshots_from_field_series(results)
        if snaps:
            results["snapshots"] = snaps

    if cfg.sweep:
        cases = cfg.sweep
        for case in cases:
            cl = case.get("label", "case")
            overrides = case.get("overrides", {})
            cfg_case = cfg.override(**overrides)
            case_results = {}
            for k, v in results.items():
                if k.startswith(f"{cl}/"):
                    case_results[k[len(cl) + 1:]] = v
            case_dir = outdir / cl
            generate_figures(cfg_case, case_results, case_dir)
        _plot_sweep_summary(cfg, cases, results, label, outdir)
    else:
        generate_figures(cfg, results, outdir)

    print(f"[{label}] plots regenerated → {outdir}")


# ── Handler base for ch14 schema ──────────────────────────────────────────────

class _NSSimulationHandler(ExperimentHandler):
    """Shared base: load_experiment_config + run/plot lifecycle."""

    @classmethod
    def load_config(cls, path):
        from twophase.simulation.config_io import load_experiment_config
        return load_experiment_config(path)

    def run(self, cfg, outdir: pathlib.Path) -> dict:
        label = outdir.name
        if cfg.sweep:
            return _run_sweep(cfg, label, outdir)
        return _run_single(cfg, label, outdir)

    def plot(self, cfg, outdir: pathlib.Path, results: dict | None = None) -> None:
        # Live results from run() already wrote figures; only re-render when
        # called standalone (plot-only mode → results is None).
        if results is not None:
            return
        _plot_only(cfg, outdir.name, outdir)


@register_handler("capillary_wave")
class CapillaryWaveHandler(_NSSimulationHandler):
    """Two-phase capillary-wave decay benchmark (Prosperetti reference)."""


@register_handler("circle")
@register_handler("ellipse")
@register_handler("perturbed_circle")
class CircleInterfaceHandler(_NSSimulationHandler):
    """Two-phase circle-interface benchmarks: static and oscillating droplets."""
