from types import SimpleNamespace

import numpy as np
import pytest

from twophase.levelset.wall_contact import WallContact, WallContactSet, WallTrace
from twophase.simulation.checkpoint import (
    CheckpointError,
    config_fingerprint,
    load_checkpoint,
    save_checkpoint,
)


class _Backend:
    xp = np
    device = "cpu"

    def to_host(self, arr):
        return arr


class _Grid:
    ndim = 2
    shape = (3, 3)
    N = (2, 2)
    L = (1.0, 1.0)

    def __init__(self):
        self.coords = [np.array([0.0, 0.5, 1.0]), np.array([0.0, 0.5, 1.0])]
        self.h = [np.full(3, 0.5), np.full(3, 0.5)]

    def _build_metrics(self, ccd=None):
        self.metrics_rebuilt = True

    def meshgrid(self):
        return np.meshgrid(*self.coords, indexing="ij")


class _GridAware:
    def __init__(self):
        self.updated = False
        self.invalidated = False

    def update_grid(self, grid):
        self.updated = True

    def invalidate_cache(self):
        self.invalidated = True

    def update_weights(self):
        self.updated = True


def _solver():
    solver = SimpleNamespace(
        _backend=_Backend(),
        _grid=_Grid(),
        _ccd=None,
        _reinit=_GridAware(),
        _ppe_solver=_GridAware(),
        _fccd_div_op=_GridAware(),
        _runtime_setup_ctx=None,
        _runtime_timestep_ctx=None,
        _p_prev_dev=np.full((3, 3), 7.0),
        _p_base_prev_dev=np.full((3, 3), 8.0),
        _p_prev_accel_face_components=[np.ones((3, 3)), np.full((3, 3), 2.0)],
        _conv_prev=[np.full((3, 3), 3.0), np.full((3, 3), 4.0)],
        _velocity_prev=[np.full((3, 3), 5.0), np.full((3, 3), 6.0)],
        _projected_face_components=None,
        _conv_ab2_ready=True,
        _velocity_bdf2_ready=True,
        _wall_contacts=WallContactSet.empty(),
    )
    solver.set_wall_contacts = lambda contacts: setattr(solver, "_wall_contacts", contacts)
    return solver


def _write_config(
    path,
    *,
    t_final=0.1,
    cfl=0.05,
    snap_interval=0.05,
    output_dir="results/a",
):
    path.write_text(
        "\n".join(
            [
                "run:",
                f"  T_final: {t_final}",
                f"  cfl: {cfl}",
                "  snap_times: [0.0, 0.1]",
                f"  snap_interval: {snap_interval}",
                "  print_every: 10",
                "  debug_diagnostics: false",
                "grid:",
                "  NX: 2",
                "  NY: 2",
                "output:",
                f"  dir: {output_dir}",
                "  save_npz: true",
                "  figures:",
                "    - type: time_series",
                "      field: kinetic_energy",
            ]
        )
    )


def test_config_fingerprint_ignores_final_time_and_visualization_paths(tmp_path):
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    c = tmp_path / "c.yaml"
    d = tmp_path / "d.yaml"
    _write_config(a, t_final=0.1, cfl=0.05)
    _write_config(
        b,
        t_final=0.2,
        cfl=0.05,
        snap_interval=0.02,
        output_dir="results/changed",
    )
    _write_config(c, t_final=0.1, cfl=0.08)
    d.write_text(a.read_text().replace("field: kinetic_energy", "field: volume"))

    assert config_fingerprint(a) == config_fingerprint(b)
    assert config_fingerprint(a) == config_fingerprint(d)
    assert config_fingerprint(a) != config_fingerprint(c)


def test_config_fingerprint_ignores_nested_run_time_output_paths(tmp_path):
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    c = tmp_path / "c.yaml"
    a.write_text(
        "\n".join([
            "run:",
            "  time:",
            "    final: 1.0",
            "    cfl: 0.2",
            "    print_every: 200",
            "  debug:",
            "    step_diagnostics: false",
            "output:",
            "  dir: results/a",
            "  snapshots:",
            "    interval: 1.0",
            "physics:",
            "  surface_tension: 0.072",
        ])
    )
    b.write_text(
        a.read_text()
        .replace("final: 1.0", "final: 2.5")
        .replace("print_every: 200", "print_every: 50")
        .replace("step_diagnostics: false", "step_diagnostics: true")
        .replace("dir: results/a", "dir: results/b")
        .replace("interval: 1.0", "interval: 0.5")
    )
    c.write_text(a.read_text().replace("cfl: 0.2", "cfl: 0.1"))

    assert config_fingerprint(a) == config_fingerprint(b)
    assert config_fingerprint(a) != config_fingerprint(c)


def test_checkpoint_roundtrip_restores_solver_runtime_state(tmp_path):
    config = tmp_path / "cfg.yaml"
    _write_config(config)
    path = tmp_path / "checkpoint_final.npz"
    solver = _solver()

    save_checkpoint(
        path,
        solver=solver,
        psi=np.ones((3, 3)),
        u=np.full((3, 3), 2.0),
        v=np.full((3, 3), 3.0),
        p=np.full((3, 3), 4.0),
        t=0.125,
        step=5,
        config_path=config,
        results={"times": np.array([0.0, 0.125])},
        snapshots=[
            {
                "t": 0.125,
                "psi": np.ones((3, 3)),
                "psi_before_transport": np.zeros((3, 3)),
                "psi_after_transport_before_reinit": np.full((3, 3), 0.25),
                "psi_after_reinit": np.full((3, 3), 0.5),
                "pressure_accel_faces": [
                    np.full((2, 3), 9.0),
                    np.full((3, 2), 10.0),
                ],
            }
        ],
        debug_history=[{"kappa_max": 1.0}],
        state_phase="pre_step",
        dt_candidate=0.01,
        dt_effective=0.004,
        terminal_clamped=True,
    )

    restored_solver = _solver()
    state = load_checkpoint(path, solver=restored_solver, config_path=config)

    assert state["t"] == 0.125
    assert state["step"] == 5
    assert state["state_phase"] == "pre_step"
    assert state["dt_candidate"] == 0.01
    assert state["dt_effective"] == 0.004
    assert state["terminal_clamped"] is True
    assert isinstance(state["grid_hash"], str)
    assert np.all(state["u"] == 2.0)
    assert np.all(restored_solver._p_prev_dev == 7.0)
    assert restored_solver._conv_ab2_ready is True
    assert restored_solver._reinit.updated is True
    assert restored_solver._ppe_solver.invalidated is True
    assert state["results"]["times"].tolist() == [0.0, 0.125]
    assert state["snapshots"][0]["t"] == 0.125
    assert np.all(state["snapshots"][0]["psi_before_transport"] == 0.0)
    assert np.all(state["snapshots"][0]["psi_after_transport_before_reinit"] == 0.25)
    assert np.all(state["snapshots"][0]["psi_after_reinit"] == 0.5)
    assert np.all(state["snapshots"][0]["pressure_accel_faces"][0] == 9.0)
    assert np.all(state["snapshots"][0]["pressure_accel_faces"][1] == 10.0)
    assert state["debug_history"] == [{"kappa_max": 1.0}]


def test_checkpoint_preserves_per_snapshot_nonuniform_grid_coords(tmp_path):
    config = tmp_path / "cfg.yaml"
    _write_config(config)
    path = tmp_path / "checkpoint_final.npz"
    solver = _solver()

    save_checkpoint(
        path,
        solver=solver,
        psi=np.ones((3, 3)),
        u=np.zeros((3, 3)),
        v=np.zeros((3, 3)),
        p=np.zeros((3, 3)),
        t=0.25,
        step=2,
        config_path=config,
        snapshots=[
            {
                "t": 0.125,
                "psi": np.ones((3, 3)),
                "grid_coords": [
                    np.array([0.0, 0.4, 1.0]),
                    np.array([0.0, 0.5, 1.0]),
                ],
            },
            {
                "t": 0.25,
                "psi": np.ones((3, 3)),
                "grid_coords": [
                    np.array([0.0, 0.6, 1.0]),
                    np.array([0.0, 0.7, 1.0]),
                ],
            },
        ],
    )

    state = load_checkpoint(path, solver=_solver(), config_path=config)

    assert state["snapshots"][0]["grid_coords"][0].tolist() == [0.0, 0.4, 1.0]
    assert state["snapshots"][1]["grid_coords"][0].tolist() == [0.0, 0.6, 1.0]
    assert state["snapshots"][1]["grid_coords"][1].tolist() == [0.0, 0.7, 1.0]


def test_checkpoint_skips_partial_endpoint_snapshot_fields(tmp_path):
    config = tmp_path / "cfg.yaml"
    _write_config(config)
    path = tmp_path / "checkpoint_final.npz"
    solver = _solver()

    save_checkpoint(
        path,
        solver=solver,
        psi=np.ones((3, 3)),
        u=np.zeros((3, 3)),
        v=np.zeros((3, 3)),
        p=np.zeros((3, 3)),
        t=0.25,
        step=2,
        config_path=config,
        snapshots=[
            {
                "t": 0.125,
                "psi": np.ones((3, 3)),
                "psi_before_transport": np.zeros((3, 3)),
            },
            {"t": 0.25, "psi": np.ones((3, 3))},
        ],
    )

    restored_solver = _solver()
    state = load_checkpoint(path, solver=restored_solver, config_path=config)

    assert len(state["snapshots"]) == 2
    assert "psi_before_transport" not in state["snapshots"][0]
    assert "psi_before_transport" not in state["snapshots"][1]


def test_checkpoint_wall_contacts_roundtrip_as_binary_float_arrays(tmp_path):
    config = tmp_path / "cfg.yaml"
    _write_config(config)
    path = tmp_path / "checkpoint_final.npz"
    solver = _solver()
    coordinate = np.float64(np.pi / 7.0)
    trace_values = tuple(np.asarray([0.1, 0.5, 0.9], dtype=np.float64))
    solver._wall_contacts = WallContactSet(
        contacts=(
            WallContact(
                wall_axis=0,
                wall_side="lo",
                tangent_axis=1,
                coordinate=float(coordinate),
                orientation=-1.0,
                mode="pinned_no_slip",
                angle_mode="initial",
                level=0.5,
            ),
        ),
        traces=(
            WallTrace(
                wall_axis=0,
                wall_side="lo",
                tangent_axis=1,
                tangent_coordinates=(0.0, float(coordinate), 1.0),
                values=tuple(float(v) for v in trace_values),
                level=0.5,
            ),
        ),
    )

    save_checkpoint(
        path,
        solver=solver,
        psi=np.ones((3, 3)),
        u=np.ones((3, 3)),
        v=np.ones((3, 3)),
        p=np.ones((3, 3)),
        t=0.1,
        step=1,
        config_path=config,
    )

    with np.load(path, allow_pickle=False) as data:
        assert "solver/wall_contacts_json" not in data.files
        assert data["solver/wall_contacts/contacts"].dtype == np.float64

    restored = _solver()
    load_checkpoint(path, solver=restored, config_path=config)

    contact = restored._wall_contacts.contacts[0]
    trace = restored._wall_contacts.traces[0]
    assert np.float64(contact.coordinate).tobytes() == coordinate.tobytes()
    assert np.asarray(trace.values, dtype=np.float64).tobytes() == np.asarray(
        trace_values, dtype=np.float64
    ).tobytes()


def test_checkpoint_rejects_non_time_config_drift(tmp_path):
    config = tmp_path / "cfg.yaml"
    changed = tmp_path / "changed.yaml"
    _write_config(config, t_final=0.1, cfl=0.05)
    _write_config(changed, t_final=0.2, cfl=0.08)
    path = tmp_path / "checkpoint_final.npz"

    save_checkpoint(
        path,
        solver=_solver(),
        psi=np.ones((3, 3)),
        u=np.ones((3, 3)),
        v=np.ones((3, 3)),
        p=np.ones((3, 3)),
        t=0.1,
        step=1,
        config_path=config,
    )

    with pytest.raises(CheckpointError, match="config fingerprint"):
        load_checkpoint(path, solver=_solver(), config_path=changed)
