from types import SimpleNamespace

import numpy as np
import pytest

from twophase.levelset.wall_contact import WallContactSet
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
    return SimpleNamespace(
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
        set_wall_contacts=lambda contacts: None,
    )


def _write_config(path, *, t_final=0.1, cfl=0.05):
    path.write_text(
        "\n".join(
            [
                "run:",
                f"  T_final: {t_final}",
                f"  cfl: {cfl}",
                "grid:",
                "  NX: 2",
                "  NY: 2",
            ]
        )
    )


def test_config_fingerprint_ignores_only_final_time(tmp_path):
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    c = tmp_path / "c.yaml"
    _write_config(a, t_final=0.1, cfl=0.05)
    _write_config(b, t_final=0.2, cfl=0.05)
    _write_config(c, t_final=0.1, cfl=0.08)

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
        snapshots=[{"t": 0.125, "psi": np.ones((3, 3))}],
        debug_history=[{"kappa_max": 1.0}],
    )

    restored_solver = _solver()
    state = load_checkpoint(path, solver=restored_solver, config_path=config)

    assert state["t"] == 0.125
    assert state["step"] == 5
    assert np.all(state["u"] == 2.0)
    assert np.all(restored_solver._p_prev_dev == 7.0)
    assert restored_solver._conv_ab2_ready is True
    assert restored_solver._reinit.updated is True
    assert restored_solver._ppe_solver.invalidated is True
    assert state["results"]["times"].tolist() == [0.0, 0.125]
    assert state["snapshots"][0]["t"] == 0.125
    assert state["debug_history"] == [{"kappa_max": 1.0}]


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
