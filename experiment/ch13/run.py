#!/usr/bin/env python3
"""Unified §13 experiment runner.

All experiments are defined by YAML config files in ``config/``.  This
single script replaces the 8 individual ``exp13_0X_*.py`` wrappers.

Usage
-----
  # Single run (no sweep)
  python experiment/ch13/run.py exp13_03_rising_bubble

  # Sweep (if YAML has ``sweep:`` section)
  python experiment/ch13/run.py exp13_04_rt_sigma

  # Re-plot only (from saved .npz)
  python experiment/ch13/run.py exp13_03_rising_bubble --plot-only

  # Run all 8 experiments sequentially
  python experiment/ch13/run.py --all

Config resolution
-----------------
  exp13_03_rising_bubble
    → config/exp13_03_rising_bubble.yaml

  config/exp13_03_rising_bubble.yaml
    → as-is (relative to this script)

Sweep support
-------------
If the YAML has a ``sweep:`` section (list of ``{label, overrides}``
dicts), the runner iterates over cases using ``cfg.override(**overrides)``
and collects results per case.  Output is saved as ``data.npz`` with
keys prefixed by the case label.
"""

import sys
import pathlib
import argparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.simulation.config_io import load_experiment_config
from twophase.simulation.ns_pipeline import run_simulation
from twophase.tools.plot_factory import generate_figures
from twophase.tools.experiment import apply_style, save_results, COLORS

apply_style()

BASE = pathlib.Path(__file__).parent


# ── config resolution ────────────────────────────────────────────────────────

def _resolve_config(name: str) -> pathlib.Path:
    """Resolve a config name/path to an absolute YAML path."""
    candidates = [
        BASE / name,
        BASE / "config" / name,
        BASE / "config" / f"{name}.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Config not found: {name}\n"
        f"Tried: {[str(c) for c in candidates]}"
    )


def _outdir_from_config(cfg, config_path: pathlib.Path) -> pathlib.Path:
    """Determine output directory from config or filename."""
    if cfg.output.dir != "results":
        return BASE / cfg.output.dir
    # Derive from filename: exp13_03_rising_bubble → results/exp13_03
    stem = config_path.stem
    parts = stem.split("_")
    if len(parts) >= 2:
        short = f"{parts[0]}_{parts[1]}"  # exp13_03
    else:
        short = stem
    return BASE / "results" / short


# ── single run ────────────────────────────────────────────────────────────────

def _run_single(cfg, label: str, outdir: pathlib.Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    npz_path = outdir / "data.npz"

    ph = cfg.physics
    print(f"[{label}] σ={ph.sigma:.5f}  μ={ph.mu:.5f}"
          f"  ρ_l/ρ_g={ph.rho_l / ph.rho_g:.0f}")
    print(f"[{label}] Running simulation...")

    results = run_simulation(cfg)

    arrays = {k: v for k, v in results.items() if isinstance(v, np.ndarray)}
    save_results(npz_path, arrays)

    # Snapshots are list-of-dicts; save separately so --plot-only can access them
    import pickle
    snaps = results.get("snapshots")
    if snaps:
        with open(outdir / "snapshots.pkl", "wb") as _f:
            pickle.dump(snaps, _f)

    generate_figures(cfg, results, outdir)
    print(f"[{label}] saved → {outdir}")
    return results


# ── sweep run ─────────────────────────────────────────────────────────────────

def _run_sweep(cfg, label: str, outdir: pathlib.Path) -> dict:
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

        # Store arrays with label prefix
        for k, v in results.items():
            if isinstance(v, np.ndarray):
                flat[f"{case_label}/{k}"] = v

        # Generate per-case figures into a subdirectory
        case_dir = outdir / case_label
        generate_figures(cfg_case, results, case_dir)

    flat["_case_labels"] = np.array(case_labels, dtype=object)
    save_results(npz_path, flat)

    # Summary plot: overlay one key diagnostic per case
    _plot_sweep_summary(cfg, cases, flat, label, outdir)

    print(f"\n[{label}] sweep complete → {outdir}")
    return flat


def _plot_sweep_summary(cfg, cases, flat, label, outdir):
    """Auto-generate a sweep summary overlaying key diagnostics."""
    # Pick the first non-KE diagnostic
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


# ── plot-only ─────────────────────────────────────────────────────────────────

def _plot_only(cfg, label: str, outdir: pathlib.Path) -> None:
    npz_path = outdir / "data.npz"
    if not npz_path.exists():
        print(f"[{label}] ERROR: {npz_path} not found. Run first without --plot-only.")
        sys.exit(1)

    results = dict(np.load(npz_path, allow_pickle=True))

    # Restore snapshots from pickle if available (saved by _run_single)
    import pickle
    snap_path = outdir / "snapshots.pkl"
    if snap_path.exists():
        with open(snap_path, "rb") as _f:
            results["snapshots"] = pickle.load(_f)

    if cfg.sweep:
        cases = cfg.sweep
        for case in cases:
            cl = case.get("label", "case")
            overrides = case.get("overrides", {})
            cfg_case = cfg.override(**overrides)
            # Reconstruct per-case results from flat dict
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


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified §13 experiment runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "config", nargs="?", default=None,
        help="Config name or path (e.g. exp13_03_rising_bubble)",
    )
    parser.add_argument("--plot-only", action="store_true",
                        help="Regenerate plots from saved data.npz")
    parser.add_argument("--all", action="store_true",
                        help="Run all experiments in config/ sequentially")
    args = parser.parse_args()

    if args.all:
        configs = sorted((BASE / "config").glob("exp13_*.yaml"))
        for cp in configs:
            _dispatch(cp, plot_only=args.plot_only)
        return

    if args.config is None:
        parser.print_help()
        sys.exit(1)

    config_path = _resolve_config(args.config)
    _dispatch(config_path, plot_only=args.plot_only)


def _dispatch(config_path: pathlib.Path, plot_only: bool) -> None:
    cfg = load_experiment_config(config_path)
    label = config_path.stem
    outdir = _outdir_from_config(cfg, config_path)

    if plot_only:
        _plot_only(cfg, label, outdir)
    elif cfg.sweep:
        _run_sweep(cfg, label, outdir)
    else:
        _run_single(cfg, label, outdir)


if __name__ == "__main__":
    main()
