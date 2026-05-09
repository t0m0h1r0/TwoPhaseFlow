from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from pathlib import Path


def _load_experiment_runner_main():
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module("experiment.runner.main")


def test_configured_outdir_uses_stem_for_legacy_results_default(tmp_path):
    runner = _load_experiment_runner_main()
    config_path = tmp_path / "ch14" / "config" / "case.yaml"
    config_path.parent.mkdir(parents=True)
    cfg = SimpleNamespace(output=SimpleNamespace(dir="results"))

    assert runner._configured_outdir(config_path, cfg) == (
        tmp_path / "ch14" / "results" / "case"
    )


def test_configured_outdir_respects_yaml_relative_dir(tmp_path):
    runner = _load_experiment_runner_main()
    config_path = tmp_path / "ch14" / "config" / "case.yaml"
    config_path.parent.mkdir(parents=True)
    cfg = SimpleNamespace(output=SimpleNamespace(dir="results/custom_case"))

    assert runner._configured_outdir(config_path, cfg) == (
        tmp_path / "ch14" / "results" / "custom_case"
    )
