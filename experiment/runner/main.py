"""Unified experiment runner entry point (YAML-driven, ch14).

Invoked via ``experiment/run.py``:

    python experiment/run.py --config ch14_capillary
    python experiment/run.py --config ch14_rising_bubble --plot-only
    python experiment/run.py --config ch14_rayleigh_taylor
    python experiment/run.py --all

Chapter 12 unit tests (U1-U9) are standalone Python scripts under
``experiment/ch12/exp_U*.py`` — invoke them directly, not through this runner.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

# ROOT = experiment/ directory
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Chapter config directories searched in order when a bare stem is given
_CHAPTER_CONFIG_DIRS = [
    ROOT / "ch14" / "config",
]


def _resolve_config(name: str) -> pathlib.Path:
    """Return absolute path to the YAML for ``name``.

    Accepts:
    - Absolute path (returned as-is if exists)
    - Relative path from cwd or experiment/ root
    - Bare stem (e.g. ``ch14_capillary``) → searched in chapter config dirs
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


def _configured_outdir(config_path: pathlib.Path, cfg) -> pathlib.Path:
    """Resolve the YAML output directory while preserving legacy defaults."""
    output = getattr(cfg, "output", None)
    raw_dir = getattr(output, "dir", None)
    if raw_dir and raw_dir != "results":
        p = pathlib.Path(raw_dir)
        if p.is_absolute():
            return p
        base = config_path.parent.parent if config_path.parent.name == "config" else config_path.parent
        return base / p
    return _outdir(config_path)


def _peek_handler_key(config_path: pathlib.Path) -> str:
    """Read just enough of the YAML to choose a handler.

    ch14 schema → ``experiment.type`` (e.g. ``capillary_wave``, ``circle``).
    Legacy configs with ``initial_condition.type`` are also accepted.
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


def _dispatch(
    config_path: pathlib.Path,
    plot_only: bool,
    *,
    resume_from: pathlib.Path | None = None,
    final_time: float | None = None,
    checkpoint_final: bool = True,
    checkpoint_every_steps: int | None = None,
    checkpoint_interval: float | None = None,
) -> None:
    from .registry import HANDLER_REGISTRY
    from . import handlers  # noqa: F401  trigger handler registrations

    handler_key = _peek_handler_key(config_path)
    handler = HANDLER_REGISTRY.get(handler_key)
    if handler is None:
        raise ValueError(
            f"Unknown experiment/handler key '{handler_key}'. "
            f"Registered: {sorted(HANDLER_REGISTRY)}"
        )

    cfg = handler.load_config(config_path)
    if final_time is not None:
        cfg = cfg.override(**{"run.T_final": float(final_time)})
    outdir = _configured_outdir(config_path, cfg)
    outdir.mkdir(parents=True, exist_ok=True)
    cfg._config_path = config_path
    cfg._checkpoint_path = outdir / "checkpoint_final.npz" if checkpoint_final else None
    cfg._resume_from = resume_from
    cfg._checkpoint_every_steps = checkpoint_every_steps
    cfg._checkpoint_interval = (
        checkpoint_interval
        if checkpoint_interval is not None
        else getattr(cfg.output, "checkpoint_interval", None)
    )

    title = ""
    exp_meta = getattr(cfg, "experiment", None)
    if isinstance(exp_meta, dict):
        title = f"[{exp_meta.get('id', '?')}] {exp_meta.get('title', '')}"
    print(f"==> {title or config_path.stem}")
    print(f"    config : {config_path}")
    print(f"    outdir : {outdir}")

    if plot_only:
        if resume_from is not None:
            raise ValueError("--resume-from cannot be combined with --plot-only")
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
        description="YAML-driven experiment runner (ch14).",
    )
    parser.add_argument("--config", default=None,
                        help="Config YAML name or path (stem or full path).")
    parser.add_argument("--plot-only", action="store_true",
                        help="Re-plot from saved .npz without rerunning.")
    parser.add_argument("--resume-from", default=None,
                        help="Explicitly resume from a ch14 checkpoint .npz.")
    parser.add_argument("--final-time", type=float, default=None,
                        help="Override run.time.final at launch without editing the YAML.")
    parser.add_argument("--no-checkpoint-final", action="store_true",
                        help="Do not write outdir/checkpoint_final.npz after a run.")
    parser.add_argument("--checkpoint-every-steps", type=int, default=None,
                        help="Also refresh the checkpoint every N completed steps.")
    parser.add_argument("--checkpoint-interval", type=float, default=None,
                        help="Write restartable checkpoints every physical-time interval.")
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
            _dispatch(
                cp,
                plot_only=args.plot_only,
                final_time=args.final_time,
                checkpoint_final=not args.no_checkpoint_final,
                checkpoint_every_steps=args.checkpoint_every_steps,
                checkpoint_interval=args.checkpoint_interval,
            )
        return

    if args.config is None:
        parser.print_help()
        sys.exit(1)

    _dispatch(
        _resolve_config(args.config),
        plot_only=args.plot_only,
        resume_from=pathlib.Path(args.resume_from).resolve() if args.resume_from else None,
        final_time=args.final_time,
        checkpoint_final=not args.no_checkpoint_final,
        checkpoint_every_steps=args.checkpoint_every_steps,
        checkpoint_interval=args.checkpoint_interval,
    )
