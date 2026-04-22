"""Unified experiment runner entry point.

Invoked via ``experiment/run.py``:

    python experiment/run.py --config exp11_01_ccd_convergence
    python experiment/run.py --config exp11_01_ccd_convergence --plot-only
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
    ROOT / "ch11" / "config",
    ROOT / "ch12" / "config",
]


def _resolve_config(name: str) -> pathlib.Path:
    """Return absolute path to the YAML for ``name``.

    Accepts:
    - Absolute path (returned as-is if exists)
    - Relative path from cwd or experiment/ root
    - Bare stem (e.g. ``exp11_01_ccd_convergence``) → searched in chapter config dirs
    """
    p = pathlib.Path(name)

    # Absolute or cwd-relative path
    if p.is_absolute() and p.exists():
        return p
    if p.exists():
        return p.resolve()

    # Try relative to experiment/ root
    for base in [ROOT, *_CHAPTER_CONFIG_DIRS]:
        candidate = base / name
        if candidate.exists():
            return candidate.resolve()
        # Try appending .yaml
        candidate_yaml = base / (name + ".yaml")
        if candidate_yaml.exists():
            return candidate_yaml.resolve()

    raise FileNotFoundError(
        f"Config not found: '{name}'\n"
        f"Searched: {[str(d) for d in [ROOT, *_CHAPTER_CONFIG_DIRS]]}"
    )


def _outdir(config_path: pathlib.Path) -> pathlib.Path:
    """Derive results directory from YAML location.

    experiment/ch11/config/exp11_01_foo.yaml → experiment/ch11/results/exp11_01_foo/
    Any other location: config_path.parent.parent / results / stem
    """
    if config_path.parent.name == "config":
        return config_path.parent.parent / "results" / config_path.stem
    return config_path.parent / "results" / config_path.stem


def _dispatch(config_path: pathlib.Path, plot_only: bool) -> None:
    # Lazy imports after sys.path is set up
    from .config_loader import load_component_config
    from .registry import HANDLER_REGISTRY
    # Trigger registrations (handlers, schemes, solutions)
    from . import handlers, schemes, solutions  # noqa: F401

    cfg = load_component_config(config_path)
    exp_type = cfg.experiment.get("type", "")
    handler = HANDLER_REGISTRY.get(exp_type)
    if handler is None:
        raise ValueError(
            f"Unknown experiment type '{exp_type}'. "
            f"Registered types: {sorted(HANDLER_REGISTRY)}"
        )

    outdir = _outdir(config_path)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"==> [{cfg.experiment.get('id', '?')}] {cfg.experiment.get('title', '')}")
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
        description="YAML-driven experiment runner (ch11/ch12).",
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
