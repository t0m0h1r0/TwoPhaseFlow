import importlib
import sys
from pathlib import Path

import numpy as np

from twophase.simulation.config_io import ExperimentConfig


def _load_ch13_runner():
    """Load the unified runner's NS-simulation handler module (CHK-232).

    The legacy ``experiment/ch13/run.py`` was retired; the snapshot
    serialization helpers now live in
    ``experiment/runner/handlers/ns_simulation.py``.
    """
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module("experiment.runner.handlers.ns_simulation")


def test_snapshot_fields_are_saved_as_npz_series():
    runner = _load_ch13_runner()
    flat = {}
    snaps = [
        {
            "t": 0.0,
            "psi": np.zeros((2, 2)),
            "u": np.ones((2, 2)),
            "v": np.full((2, 2), 2.0),
            "p": np.full((2, 2), 3.0),
            "rho": np.full((2, 2), 1000.0),
            "grid_coords": [np.array([0.0, 1.0]), np.array([0.0, 1.0])],
        },
        {
            "t": 0.5,
            "psi": np.ones((2, 2)),
            "u": np.full((2, 2), 4.0),
            "v": np.full((2, 2), 5.0),
            "p": np.full((2, 2), 6.0),
            "rho": np.full((2, 2), 1.2),
            "grid_coords": [np.array([0.0, 1.0]), np.array([0.0, 1.0])],
        },
    ]

    runner._add_snapshot_series(flat, snaps)

    assert flat["fields/times"].tolist() == [0.0, 0.5]
    assert flat["fields/psi"].shape == (2, 2, 2)
    assert flat["fields/u"].shape == (2, 2, 2)
    assert flat["fields/v"].shape == (2, 2, 2)
    assert flat["fields/velocity"].shape == (2, 2, 2, 2)
    assert flat["fields/p"].shape == (2, 2, 2)
    assert flat["fields/pressure"].shape == (2, 2, 2)
    assert flat["fields/rho"].shape == (2, 2, 2)
    assert flat["fields/grid_coords/0"].tolist() == [0.0, 1.0]


def test_snapshot_fields_reconstruct_plot_snapshots():
    runner = _load_ch13_runner()
    results = {
        "fields/times": np.array([0.0, 0.5]),
        "fields/psi": np.zeros((2, 2, 2)),
        "fields/u": np.ones((2, 2, 2)),
        "fields/v": np.full((2, 2, 2), 2.0),
        "fields/pressure": np.full((2, 2, 2), 3.0),
        "fields/grid_coords/0": np.array([0.0, 1.0]),
        "fields/grid_coords/1": np.array([0.0, 1.0]),
    }

    snaps = runner._snapshots_from_field_series(results)

    assert [snap["t"] for snap in snaps] == [0.0, 0.5]
    assert snaps[0]["psi"].shape == (2, 2)
    assert snaps[1]["u"].shape == (2, 2)
    assert np.all(snaps[0]["p"] == 3.0)
    assert len(snaps[0]["grid_coords"]) == 2


def test_ch13_config_set_is_two_production_files():
    config_dir = Path(__file__).resolve().parents[3] / "experiment/ch13/config"

    config_names = sorted(path.name for path in config_dir.glob("*.yaml"))

    assert config_names == [
        "ch13_capillary_water_air_alpha2_n128.yaml",
        "ch13_rising_bubble_water_air_alpha2_n128x256.yaml",
    ]


def test_ch13_configs_emit_required_field_snapshots():
    config_dir = Path(__file__).resolve().parents[3] / "experiment/ch13/config"

    for path in sorted(config_dir.glob("*.yaml")):
        cfg = ExperimentConfig.from_yaml(path)
        snapshot_fields = {
            spec.get("field")
            for spec in cfg.output.figures
            if spec.get("type") == "snapshot_series"
        }

        assert cfg.output.save_npz is True
        assert cfg.run.snap_interval is not None
        assert cfg.run.snap_interval > 0.0
        assert {"psi", "velocity", "pressure"} <= snapshot_fields
