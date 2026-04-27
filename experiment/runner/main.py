"""Unified experiment runner entry point.

Invoked via ``experiment/run.py``:

    python experiment/run.py --config exp12_01_hydrostatic
    python experiment/run.py --config ch13_capillary_water_air_alpha2_n128 --plot-only
    python experiment/run.py --all
"""

from __future__ import annotations

import argparse
import pathlib
import sys

# ROOT = experiment/ directory
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Chapter config directories searched in order when a bare stem is given
_CHAPTER_CONFIG_DIRS = [
    ROOT / "ch12" / "config",
    ROOT / "ch13" / "config",
]


def _resolve_config(name: str) -> pathlib.Path:
    """Return absolute path to the YAML for ``name``.

    Accepts:
    - Absolute path (returned as-is if exists)
    - Relative path from cwd or experiment/ root
    - Bare stem (e.g. ``ch13_capillary_water_air_alpha2_n128``) → searched in chapter config dirs
    """
    p = pathlib.Path(name)

    if p.is_absolute() and p.exists():
        return p
    if p.exists():
        return p.resolve()

    for base in [ROOT, *_CHAPTER_CONFIG_DIRS]:
        candidate = base / name
        if candidate.exists():
            return candidate.resolve()
        candidate_yaml = base / (name + ".yaml")
        if candidate_yaml.exists():
            return candidate_yaml.resolve()

    raise FileNotFoundError(
        f"Config not found: '{name}'\n"
        f"Searched: {[str(d) for d in [ROOT, *_CHAPTER_CONFIG_DIRS]]}"
    )


def _outdir(config_path: pathlib.Path) -> pathlib.Path:
    """Derive results directory from YAML location.

    experiment/ch12/config/exp12_01_foo.yaml → experiment/ch12/results/exp12_01_foo/
    Any other location: config_path.parent.parent / results / stem
    """
    if config_path.parent.name == "config":
        return config_path.parent.parent / "results" / config_path.stem
    return config_path.parent / "results" / config_path.stem


def _peek_handler_key(config_path: pathlib.Path) -> str:
    """Read just enough of the YAML to choose a handler.

    ch11/ch12 schema → ``experiment.type`` (e.g. ``convergence_study``)
    ch13 schema     → ``initial_condition.type`` (e.g. ``capillary_wave``, ``circle``)
    """
    try:
        import yaml
    except ImportError as e:
        raise ImportError("PyYAML required: pip install pyyaml") from e

    with open(config_path) as fh:
        raw = yaml.safe_load(fh) or {}

    exp = raw.get("experiment")
    if isinstance(exp, dict) and exp.get("type"):
        return str(exp["type"])

    ic = raw.get("initial_condition")
    if isinstance(ic, dict) and ic.get("type"):
        return str(ic["type"])

    raise ValueError(
        f"Cannot determine handler for {config_path}: "
        "neither 'experiment.type' nor 'initial_condition.type' present."
    )


def _dispatch(config_path: pathlib.Path, plot_only: bool) -> None:
    from .registry import HANDLER_REGISTRY
    from . import handlers, schemes, solutions  # noqa: F401  trigger registrations

    handler_key = _peek_handler_key(config_path)
    handler = HANDLER_REGISTRY.get(handler_key)
    if handler is None:
        raise ValueError(
            f"Unknown experiment/handler key '{handler_key}'. "
            f"Registered: {sorted(HANDLER_REGISTRY)}"
        )

    cfg = handler.load_config(config_path)
    outdir = _outdir(config_path)
    outdir.mkdir(parents=True, exist_ok=True)

    title = ""
    exp_meta = getattr(cfg, "experiment", None)
    if isinstance(exp_meta, dict):
        title = f"[{exp_meta.get('id', '?')}] {exp_meta.get('title', '')}"
    print(f"==> {title or config_path.stem}")
    print(f"    config : {config_path}")
    print(f"    outdir : {outdir}")

    if plot_only:
        handler.plot(cfg, outdir)
    else:
        results = handler.run(cfg, outdir)
        handler.plot(cfg, outdir, results)

    print(f"==> Done: {config_path.stem}")


def main() -> None:
    from twophase.tools.experiment import apply_style
    apply_style()

    parser = argparse.ArgumentParser(
        prog="experiment/run.py",
        description="YAML-driven experiment runner (ch12/ch13).",
    )
    parser.add_argument("--config", default=None,
                        help="Config YAML name or path (stem or full path).")
    parser.add_argument("--plot-only", action="store_true",
                        help="Re-plot from saved .npz without rerunning.")
    parser.add_argument("--all", action="store_true",
                        help="Run all YAML configs in all chapter config/ directories.")
    args = parser.parse_args()

    if args.all:
        configs = []
        for d in _CHAPTER_CONFIG_DIRS:
            if d.exists():
                configs.extend(sorted(d.glob("*.yaml")))
        if not configs:
            print("No YAML configs found.", file=sys.stderr)
            sys.exit(1)
        for cp in configs:
            _dispatch(cp, plot_only=args.plot_only)
        return

    if args.config is None:
        parser.print_help()
        sys.exit(1)

    _dispatch(_resolve_config(args.config), plot_only=args.plot_only)
