"""Experiment I/O utilities: NPZ dict persistence and --plot-only argparse.

NPZ format convention
---------------------
Nested ``dict[str, dict[str, ndarray]]`` is flattened with ``__`` separator::

    {"label_A": {"kappa": arr, "p": arr}, "_meta": {"N": 64}}
    →  label_A__kappa, label_A__p, _meta__N

Scalars are stored as 0-d arrays and restored to Python float/int on load.

Usage::

    from twophase.experiment.io import save_results, load_results, experiment_argparser

    args = experiment_argparser("My experiment").parse_args()
    if args.plot_only:
        results = load_results(npz_path)
    else:
        results = compute()
        save_results(npz_path, results)
"""

from __future__ import annotations

import argparse
import pathlib
from typing import Any

import numpy as np


# ── NPZ save / load ──────────────────────────────────────────────────────────

def save_results(path: str | pathlib.Path, results: dict[str, Any]) -> None:
    """Save a (possibly nested) dict to ``.npz``.

    Keys containing ``=`` or ``.`` are sanitised for numpy compatibility.
    """
    flat: dict[str, Any] = {}
    for key, val in results.items():
        safe_key = _sanitise_key(key)
        if isinstance(val, dict):
            for k2, v2 in val.items():
                flat[f"{safe_key}__{k2}"] = np.asarray(v2)
        else:
            flat[safe_key] = np.asarray(val)

    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, **flat)
    print(f"Saved data → {path}")


def load_results(path: str | pathlib.Path) -> dict[str, Any]:
    """Load ``.npz`` written by :func:`save_results`.

    Restores nested structure and converts 0-d arrays to Python scalars.
    """
    data = np.load(path, allow_pickle=False)
    results: dict[str, Any] = {}
    for fullkey, val in data.items():
        val = _maybe_scalar(val)
        if "__" in fullkey:
            group, subkey = fullkey.split("__", 1)
            results.setdefault(group, {})[subkey] = val
        else:
            results[fullkey] = val
    return results


# ── Output directory helper ───────────────────────────────────────────────────

def experiment_dir(script_file: str, name: str | None = None) -> pathlib.Path:
    """Return ``experiment/ch{N}/results/{name}/``, creating it if needed.

    Parameters
    ----------
    script_file : str
        Pass ``__file__`` from the calling script.
    name : str, optional
        Sub-directory name.  Defaults to script stem without ``exp`` / ``viz``
        prefixes (e.g. ``exp12_ipc_ccdlu_droplet.py`` → ``ipc_ccdlu_droplet``).
    """
    p = pathlib.Path(script_file).resolve()
    if name is None:
        stem = p.stem
        # strip leading exp{NN}_ or viz_ch{NN}_ prefix
        for prefix in ("exp", "viz"):
            if stem.startswith(prefix):
                parts = stem.split("_", 1)
                if len(parts) > 1:
                    stem = parts[1]
                    # strip remaining chNN_ for viz files
                    if stem.startswith("ch") and "_" in stem:
                        stem = stem.split("_", 1)[1]
                break
        name = stem
    out = p.parent / "results" / name
    out.mkdir(parents=True, exist_ok=True)
    return out


# ── Argparse helper ───────────────────────────────────────────────────────────

def experiment_argparser(description: str = "") -> argparse.ArgumentParser:
    """Return an ``ArgumentParser`` pre-configured with ``--plot-only``."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--plot-only", action="store_true",
        help="Skip computation; re-plot from saved .npz data.",
    )
    return parser


# ── Internal helpers ──────────────────────────────────────────────────────────

def _sanitise_key(key: str) -> str:
    """Replace characters invalid in NPZ keys."""
    return key.replace("=", "_").replace(".", "p")


def _maybe_scalar(arr: np.ndarray) -> float | int | np.ndarray:
    """Convert 0-d numpy array to Python scalar."""
    if arr.ndim == 0:
        item = arr.item()
        if isinstance(item, (float, int, np.integer, np.floating)):
            return float(item) if isinstance(item, (float, np.floating)) else int(item)
        return item
    return arr
