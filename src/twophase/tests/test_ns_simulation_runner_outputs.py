import importlib
import sys
from types import SimpleNamespace
from pathlib import Path

import numpy as np


def _load_ns_simulation_runner():
    """Load the unified runner's NS-simulation handler module (CHK-232)."""
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module("experiment.runner.handlers.ns_simulation")


def test_snapshot_fields_are_saved_as_npz_series():
    runner = _load_ns_simulation_runner()
    flat = {}
    snaps = [
        {
            "t": 0.0,
            "psi": np.zeros((2, 2)),
            "u": np.ones((2, 2)),
            "v": np.full((2, 2), 2.0),
            "p": np.full((2, 2), 3.0),
            "rho": np.full((2, 2), 1000.0),
            "pressure_accel_faces": [
                np.full((1, 2), 7.0),
                np.full((2, 1), 8.0),
            ],
            "psi_before_transport": np.full((2, 2), -1.0),
            "psi_after_transport_before_reinit": np.full((2, 2), 0.25),
            "psi_after_reinit": np.full((2, 2), 0.5),
            "grid_coords": [np.array([0.0, 1.0]), np.array([0.0, 1.0])],
        },
        {
            "t": 0.5,
            "psi": np.ones((2, 2)),
            "u": np.full((2, 2), 4.0),
            "v": np.full((2, 2), 5.0),
            "p": np.full((2, 2), 6.0),
            "rho": np.full((2, 2), 1.2),
            "pressure_accel_faces": [
                np.full((1, 2), 9.0),
                np.full((2, 1), 10.0),
            ],
            "psi_before_transport": np.full((2, 2), -2.0),
            "psi_after_transport_before_reinit": np.full((2, 2), 0.75),
            "psi_after_reinit": np.full((2, 2), 1.5),
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
    assert flat["fields/psi_before_transport"].shape == (2, 2, 2)
    assert flat["fields/psi_after_transport_before_reinit"].shape == (2, 2, 2)
    assert flat["fields/psi_after_reinit"].shape == (2, 2, 2)
    assert np.all(flat["fields/psi_after_transport_before_reinit"][1] == 0.75)
    assert flat["fields/pressure_accel_faces/0"].shape == (2, 1, 2)
    assert flat["fields/pressure_accel_faces/1"].shape == (2, 2, 1)
    assert flat["fields/grid_coords/0"].tolist() == [0.0, 1.0]


def test_snapshot_fields_reconstruct_plot_snapshots():
    runner = _load_ns_simulation_runner()
    results = {
        "fields/times": np.array([0.0, 0.5]),
        "fields/psi": np.zeros((2, 2, 2)),
        "fields/u": np.ones((2, 2, 2)),
        "fields/v": np.full((2, 2, 2), 2.0),
        "fields/pressure": np.full((2, 2, 2), 3.0),
        "fields/pressure_accel_faces/0": np.full((2, 1, 2), 7.0),
        "fields/pressure_accel_faces/1": np.full((2, 2, 1), 8.0),
        "fields/psi_before_transport": np.full((2, 2, 2), -1.0),
        "fields/psi_after_transport_before_reinit": np.full((2, 2, 2), 0.25),
        "fields/psi_after_reinit": np.full((2, 2, 2), 0.5),
        "fields/grid_coords/0": np.array([0.0, 1.0]),
        "fields/grid_coords/1": np.array([0.0, 1.0]),
    }

    snaps = runner._snapshots_from_field_series(results)

    assert [snap["t"] for snap in snaps] == [0.0, 0.5]
    assert snaps[0]["psi"].shape == (2, 2)
    assert snaps[1]["u"].shape == (2, 2)
    assert np.all(snaps[0]["p"] == 3.0)
    assert np.all(snaps[0]["psi_before_transport"] == -1.0)
    assert np.all(snaps[1]["psi_after_transport_before_reinit"] == 0.25)
    assert np.all(snaps[1]["psi_after_reinit"] == 0.5)
    assert np.all(snaps[0]["pressure_accel_faces"][0] == 7.0)
    assert np.all(snaps[1]["pressure_accel_faces"][1] == 8.0)
    assert len(snaps[0]["grid_coords"]) == 2


def test_run_single_respects_save_npz_false(tmp_path, monkeypatch):
    runner = _load_ns_simulation_runner()
    calls = {"save_results": 0, "generate_figures": 0}

    def fake_run_simulation(cfg, **kwargs):
        assert kwargs["checkpoint_path"] == tmp_path / "checkpoint_final.npz"
        return {"times": np.array([0.0]), "kinetic_energy": np.array([0.0])}

    def fake_save_results(path, flat):
        calls["save_results"] += 1

    def fake_generate_figures(cfg, results, outdir):
        calls["generate_figures"] += 1

    monkeypatch.setattr(
        "twophase.simulation.ns_pipeline.run_simulation",
        fake_run_simulation,
    )
    monkeypatch.setattr("twophase.tools.experiment.save_results", fake_save_results)
    monkeypatch.setattr(
        "twophase.tools.plot_factory.generate_figures",
        fake_generate_figures,
    )

    cfg = SimpleNamespace(
        physics=SimpleNamespace(sigma=0.072, mu_l=1.0e-3, mu_g=1.8e-5, rho_l=1000.0, rho_g=1.2),
        output=SimpleNamespace(save_npz=False),
        _checkpoint_path=tmp_path / "checkpoint_final.npz",
        _checkpoint_every_steps=None,
        _resume_from=None,
        _config_path=tmp_path / "cfg.yaml",
    )

    results = runner._run_single(cfg, "nosave", tmp_path)

    assert results["times"].tolist() == [0.0]
    assert calls == {"save_results": 0, "generate_figures": 1}
    assert not (tmp_path / "data.npz").exists()


def test_run_single_passes_explicit_resume_checkpoint_args(tmp_path, monkeypatch):
    runner = _load_ns_simulation_runner()
    seen = {}

    def fake_run_simulation(cfg, **kwargs):
        seen.update(kwargs)
        return {"times": np.array([0.0]), "kinetic_energy": np.array([0.0])}

    def fake_generate_figures(cfg, results, outdir):
        pass

    monkeypatch.setattr(
        "twophase.simulation.ns_pipeline.run_simulation",
        fake_run_simulation,
    )
    monkeypatch.setattr(
        "twophase.tools.plot_factory.generate_figures",
        fake_generate_figures,
    )

    cfg = SimpleNamespace(
        physics=SimpleNamespace(sigma=0.072, mu_l=1.0e-3, mu_g=1.8e-5, rho_l=1000.0, rho_g=1.2),
        output=SimpleNamespace(save_npz=False),
        _resume_from=tmp_path / "checkpoint_old.npz",
        _checkpoint_path=tmp_path / "checkpoint_final.npz",
        _checkpoint_every_steps=12,
        _config_path=tmp_path / "cfg.yaml",
    )

    runner._run_single(cfg, "resume", tmp_path)

    assert seen["resume_from"] == tmp_path / "checkpoint_old.npz"
    assert seen["checkpoint_path"] == tmp_path / "checkpoint_final.npz"
    assert seen["checkpoint_every_steps"] == 12
    assert seen["config_path"] == tmp_path / "cfg.yaml"
