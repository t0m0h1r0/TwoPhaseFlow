import importlib.util
from pathlib import Path

import numpy as np


def _load_ch13_runner():
    root = Path(__file__).resolve().parents[3]
    path = root / "experiment" / "ch13" / "run.py"
    spec = importlib.util.spec_from_file_location("ch13_run", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert flat["fields/p"].shape == (2, 2, 2)
    assert flat["fields/rho"].shape == (2, 2, 2)
    assert flat["fields/grid_coords/0"].tolist() == [0.0, 1.0]


def test_snapshot_fields_reconstruct_plot_snapshots():
    runner = _load_ch13_runner()
    results = {
        "fields/times": np.array([0.0, 0.5]),
        "fields/psi": np.zeros((2, 2, 2)),
        "fields/u": np.ones((2, 2, 2)),
        "fields/v": np.full((2, 2, 2), 2.0),
        "fields/p": np.full((2, 2, 2), 3.0),
        "fields/grid_coords/0": np.array([0.0, 1.0]),
        "fields/grid_coords/1": np.array([0.0, 1.0]),
    }

    snaps = runner._snapshots_from_field_series(results)

    assert [snap["t"] for snap in snaps] == [0.0, 0.5]
    assert snaps[0]["psi"].shape == (2, 2)
    assert snaps[1]["u"].shape == (2, 2)
    assert len(snaps[0]["grid_coords"]) == 2
