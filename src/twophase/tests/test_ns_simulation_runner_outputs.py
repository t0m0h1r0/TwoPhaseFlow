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


def test_runtime_snapshots_skip_projection_fields_unless_requested():
    runner = importlib.import_module("twophase.simulation.runner")
    cfg = SimpleNamespace(
        output=SimpleNamespace(
            figures=[
                {"type": "snapshot_series", "field": "psi"},
                {"type": "snapshot_series", "field": "velocity"},
                {"type": "timeseries", "field": "psi_after_reinit"},
                "ignored",
            ]
        )
    )

    assert not runner._snapshot_needs_projection_fields(cfg)

    cfg.output.figures.append(
        {"type": "snapshot_series", "field": "psi_after_reinit"}
    )

    assert runner._snapshot_needs_projection_fields(cfg)


def test_pre_blowup_checkpoint_guard_preserves_only_subcritical_states(tmp_path):
    runner = importlib.import_module("twophase.simulation.runner")
    limit = runner.BLOWUP_KINETIC_ENERGY_LIMIT

    assert not runner._should_refresh_pre_blowup_checkpoint(0.0)
    assert not runner._should_refresh_pre_blowup_checkpoint(np.nan)
    assert not runner._should_refresh_pre_blowup_checkpoint(1.01 * limit)
    assert runner._should_refresh_pre_blowup_checkpoint(
        runner.PRE_BLOWUP_CHECKPOINT_FRACTION * limit
    )
    assert runner._should_refresh_pre_blowup_checkpoint(0.5 * limit)

    path = runner._pre_blowup_checkpoint_path(tmp_path / "checkpoint_final.npz")
    assert path == tmp_path / "checkpoint_pre_blowup_input.npz"


def test_run_simulation_saves_restartable_pre_blowup_state(tmp_path, monkeypatch):
    runner = importlib.import_module("twophase.simulation.runner")
    saves = []

    class FakeSolver:
        _alpha_grid = 1.0
        _rebuild_freq = 0
        _p_prev_accel_face_components = None
        _step_diag = SimpleNamespace(last={})
        _backend = SimpleNamespace(xp=np, to_host=lambda arr: arr)
        _grid = SimpleNamespace(ndim=2)
        bc_type = "periodic"
        X = np.zeros((2, 2))
        Y = np.zeros((2, 2))
        h = 1.0

        @classmethod
        def from_config(cls, cfg):
            return cls()

        def make_bc_hook(self, cfg):
            return None

        def set_wall_contacts(self, contacts):
            return None

        def dt_budget(self, *args, **kwargs):
            raise AssertionError("fixed-dt test should not ask for CFL budget")

        def step_request(self, request, return_host_pressure=False):
            return request.psi, request.u, request.v, np.zeros_like(request.psi)

    class FakeDiagnostics:
        def __init__(self, *args, **kwargs):
            self.values = []
            self._last = 0.0

        def needs_retained_geometry(self):
            return False

        def collect(self, *args, **kwargs):
            seq = [
                2.0 * runner.PRE_BLOWUP_CHECKPOINT_FRACTION
                * runner.BLOWUP_KINETIC_ENERGY_LIMIT,
                1.1 * runner.BLOWUP_KINETIC_ENERGY_LIMIT,
            ]
            self._last = seq[len(self.values)]
            self.values.append(self._last)

        def last(self, key, default=0.0):
            return self._last if key == "kinetic_energy" else default

        def to_arrays(self):
            return {
                "times": np.arange(1, len(self.values) + 1, dtype=float),
                "kinetic_energy": np.asarray(self.values, dtype=float),
            }

    def fake_load_checkpoint(path, *, solver, config_path):
        return {
            "t": 0.0,
            "step": 0,
            "state_phase": "pre_step",
            "dt_candidate": 1.0,
            "psi": np.zeros((2, 2)),
            "u": np.zeros((2, 2)),
            "v": np.zeros((2, 2)),
            "p": np.zeros((2, 2)),
            "results": {},
            "snapshots": [],
            "debug_history": [],
        }

    def fake_capture_checkpoint_frame(**kwargs):
        return {
            "path": None,
            "step": kwargs["step"],
            "t": kwargs["t"],
            "state_phase": kwargs["state_phase"],
            "manifest": {
                "time": float(kwargs["t"]),
                "step": int(kwargs["step"]),
            },
        }

    def fake_write_checkpoint_frame(path, frame):
        saves.append({
            "path": Path(path),
            "step": frame["step"],
            "t": frame["t"],
            "state_phase": frame["state_phase"],
        })

    def fake_save_checkpoint(path, **kwargs):
        saves.append({
            "path": Path(path),
            "step": kwargs["step"],
            "t": kwargs["t"],
            "state_phase": kwargs.get("state_phase"),
        })

    monkeypatch.setattr(
        "twophase.simulation.ns_pipeline.TwoPhaseNSSolver",
        FakeSolver,
    )
    monkeypatch.setattr(
        "twophase.simulation.checkpoint.load_checkpoint",
        fake_load_checkpoint,
    )
    monkeypatch.setattr(
        "twophase.simulation.checkpoint.save_checkpoint",
        fake_save_checkpoint,
    )
    monkeypatch.setattr(
        "twophase.simulation.checkpoint.capture_checkpoint_frame",
        fake_capture_checkpoint_frame,
    )
    monkeypatch.setattr(
        "twophase.simulation.checkpoint.write_checkpoint_frame",
        fake_write_checkpoint_frame,
    )
    monkeypatch.setattr(
        "twophase.tools.diagnostics.DiagnosticCollector",
        FakeDiagnostics,
    )

    cfg = SimpleNamespace(
        physics=SimpleNamespace(
            rho_l=1.0,
            rho_g=1.0,
            sigma=0.0,
            mu=0.0,
            g_acc=0.0,
            rho_ref=None,
            mu_l=None,
            mu_g=None,
        ),
        run=SimpleNamespace(
            T_final=2.0,
            max_steps=None,
            dt_fixed=1.0,
            snap_interval=None,
            snap_times=[],
            print_every=100,
            debug_diagnostics=False,
        ),
        output=SimpleNamespace(figures=[], checkpoint_interval=0.5),
        diagnostics=["kinetic_energy"],
        initial_condition={},
    )

    results = runner.run_simulation(
        cfg,
        resume_from=tmp_path / "checkpoint_old.npz",
        checkpoint_path=tmp_path / "checkpoint_final.npz",
        config_path=tmp_path / "cfg.yaml",
    )

    assert {
        "path": tmp_path / "checkpoint_pre_blowup_input.npz",
        "step": 0,
        "t": 0.0,
        "state_phase": "pre_step",
    } in saves
    assert saves[-1]["path"] == tmp_path / "checkpoint_final.npz"
    assert saves[-1]["state_phase"] == "post_step"
    assert bool(results["pre_blowup_checkpoint_written"])


def test_time_checkpoints_do_not_clamp_discrete_timestep(tmp_path, monkeypatch):
    runner = importlib.import_module("twophase.simulation.runner")
    checkpoint = importlib.import_module("twophase.simulation.checkpoint")
    seen_dts = []
    captures = []
    writes = []

    class FakeSolver:
        _alpha_grid = 1.0
        _rebuild_freq = 0
        _p_prev_accel_face_components = None
        _step_diag = SimpleNamespace(last={})
        _backend = SimpleNamespace(xp=np, to_host=lambda arr: arr)
        _grid = SimpleNamespace(ndim=2)
        bc_type = "periodic"
        X = np.zeros((2, 2))
        Y = np.zeros((2, 2))
        h = 1.0

        @classmethod
        def from_config(cls, cfg):
            return cls()

        def build_ic(self, cfg):
            return np.zeros((2, 2), dtype=float)

        def build_velocity(self, cfg, psi):
            return np.zeros_like(psi), np.zeros_like(psi)

        def make_bc_hook(self, cfg):
            return None

        def set_wall_contacts(self, contacts):
            return None

        def dt_budget(self, *args, **kwargs):
            raise AssertionError("fixed-dt test should not ask for CFL budget")

        def step_request(self, request, return_host_pressure=False):
            seen_dts.append(float(request.dt))
            next_psi = request.psi + request.dt
            return next_psi, request.u, request.v, np.zeros_like(request.psi)

    class FakeDiagnostics:
        def __init__(self, *args, **kwargs):
            self.times = []

        def needs_retained_geometry(self):
            return False

        def collect(self, t, *args, **kwargs):
            self.times.append(float(t))

        def last(self, key, default=0.0):
            return 0.0

        def to_arrays(self):
            return {"times": np.asarray(self.times, dtype=float)}

    def fake_capture_checkpoint_frame(**kwargs):
        captures.append((float(kwargs["t"]), int(kwargs["step"])))
        return {
            "arrays": {},
            "manifest": {
                "time": float(kwargs["t"]),
                "step": int(kwargs["step"]),
            },
        }

    def fake_write_checkpoint_frame(path, frame):
        writes.append(
            (Path(path).name, frame["manifest"]["time"], frame["manifest"]["step"])
        )

    def fake_save_checkpoint(path, **kwargs):
        return None

    monkeypatch.setattr("twophase.simulation.ns_pipeline.TwoPhaseNSSolver", FakeSolver)
    monkeypatch.setattr("twophase.tools.diagnostics.DiagnosticCollector", FakeDiagnostics)
    monkeypatch.setattr(checkpoint, "capture_checkpoint_frame", fake_capture_checkpoint_frame)
    monkeypatch.setattr(checkpoint, "write_checkpoint_frame", fake_write_checkpoint_frame)
    monkeypatch.setattr(checkpoint, "save_checkpoint", fake_save_checkpoint)

    config = tmp_path / "cfg.yaml"
    config.write_text("run:\n  T_final: 0.8\n")
    cfg = SimpleNamespace(
        physics=SimpleNamespace(
            rho_l=1.0,
            rho_g=1.0,
            sigma=0.0,
            mu=0.0,
            g_acc=0.0,
            rho_ref=None,
            mu_l=None,
            mu_g=None,
        ),
        run=SimpleNamespace(
            T_final=0.8,
            max_steps=None,
            dt_fixed=0.2,
            snap_interval=None,
            snap_times=[],
            print_every=100,
            debug_diagnostics=False,
            cfl=1.0,
            cfl_advective=None,
            cfl_capillary=None,
            cfl_viscous=None,
        ),
        output=SimpleNamespace(figures=[], checkpoint_interval=0.5),
        diagnostics=[],
        initial_condition={},
    )

    runner.run_simulation(
        cfg,
        checkpoint_path=tmp_path / "checkpoint_final.npz",
        config_path=config,
    )

    np.testing.assert_allclose(seen_dts, [0.2, 0.2, 0.2, 0.2])
    assert captures == [(0.4, 2)]
    assert ("checkpoint_t0p5.npz", 0.4, 2) in writes


def test_pre_step_restart_matches_uninterrupted_run(tmp_path, monkeypatch):
    runner = importlib.import_module("twophase.simulation.runner")
    checkpoint = importlib.import_module("twophase.simulation.checkpoint")

    class FakeBackend:
        xp = np
        device = "cpu"

        def to_host(self, arr):
            return arr

    class FakeGrid:
        ndim = 2
        shape = (2, 2)
        N = (1, 1)
        L = (1.0, 1.0)

        def __init__(self):
            self.coords = [
                np.array([0.0, 1.0], dtype=float),
                np.array([0.0, 1.0], dtype=float),
            ]
            self.h = [
                np.array([1.0, 1.0], dtype=float),
                np.array([1.0, 1.0], dtype=float),
            ]

        def _build_metrics(self, ccd=None):
            self.metrics_rebuilt = True

        def meshgrid(self):
            return np.meshgrid(*self.coords, indexing="ij")

    class FakeGridAware:
        def update_grid(self, grid):
            self.grid = grid

        def invalidate_cache(self):
            self.invalidated = True

        def update_weights(self):
            self.weights_updated = True

    class FakeStepDiag:
        last = {}

    class FakeSolver:
        _alpha_grid = 1.0
        _rebuild_freq = 0
        bc_type = "periodic"
        h = 1.0

        @classmethod
        def from_config(cls, cfg):
            return cls()

        def __init__(self):
            self._backend = FakeBackend()
            self._grid = FakeGrid()
            self._ccd = None
            self._reinit = FakeGridAware()
            self._ppe_solver = FakeGridAware()
            self._fccd_div_op = FakeGridAware()
            self._runtime_setup_ctx = None
            self._runtime_timestep_ctx = None
            self._step_diag = FakeStepDiag()
            self._transport = None
            self._p_prev_dev = None
            self._p_base_prev_dev = None
            self._p_prev_accel_face_components = None
            self._conv_prev = None
            self._velocity_prev = None
            self._projected_face_components = None
            self._conv_ab2_ready = False
            self._velocity_bdf2_ready = False
            self._wall_contacts = None
            self.X, self.Y = self._grid.meshgrid()

        def set_wall_contacts(self, contacts):
            self._wall_contacts = contacts

        def build_ic(self, cfg):
            return np.array([[0.1, 0.2], [0.3, 0.4]], dtype=float)

        def build_velocity(self, cfg, psi):
            return (
                np.array([[0.0, 0.1], [0.2, 0.3]], dtype=float),
                np.array([[0.4, 0.5], [0.6, 0.7]], dtype=float),
            )

        def make_bc_hook(self, cfg):
            return None

        def step_request(self, request, return_host_pressure=False):
            zeros = np.zeros_like(request.psi)
            prev_u = self._velocity_prev[0] if self._velocity_prev else zeros
            prev_v = self._velocity_prev[1] if self._velocity_prev else zeros
            prev_c = self._conv_prev[0] if self._conv_prev else zeros
            prev_p = self._p_prev_dev if self._p_prev_dev is not None else zeros

            dt = float(request.dt)
            psi_next = request.psi + dt * (
                1.0 + request.u + 0.01 * prev_u + 0.001 * prev_p
            )
            u_next = request.u + dt * (
                2.0 + request.v + 0.02 * prev_c + 0.002 * prev_p
            )
            v_next = request.v + dt * (
                3.0 + request.psi + 0.03 * prev_v + 0.003 * prev_p
            )
            p_next = (
                psi_next
                + 2.0 * u_next
                - 0.5 * v_next
                + float(request.step_index)
            )

            self._p_prev_dev = p_next.copy()
            self._p_base_prev_dev = (p_next + 10.0).copy()
            self._p_prev_accel_face_components = [
                (u_next + 20.0).copy(),
                (v_next + 30.0).copy(),
            ]
            self._conv_prev = [(psi_next + 40.0).copy(), (u_next + 50.0).copy()]
            self._velocity_prev = [u_next.copy(), v_next.copy()]
            self._projected_face_components = [
                (psi_next + 60.0).copy(),
                (p_next + 70.0).copy(),
            ]
            self._conv_ab2_ready = True
            self._velocity_bdf2_ready = True
            return psi_next, u_next, v_next, p_next

    class FakeDiagnostics:
        def __init__(self, *args, **kwargs):
            self.times = []
            self.ke = []

        def needs_retained_geometry(self):
            return False

        def collect(self, t, psi, u, v, p, dV=None):
            self.times.append(float(t))
            self.ke.append(float(np.sum(u * u + v * v)))

        def last(self, key, default=0.0):
            return self.ke[-1] if key == "kinetic_energy" and self.ke else default

        def to_arrays(self):
            return {
                "times": np.asarray(self.times, dtype=float),
                "kinetic_energy": np.asarray(self.ke, dtype=float),
            }

    monkeypatch.setattr(
        "twophase.simulation.ns_pipeline.TwoPhaseNSSolver",
        FakeSolver,
    )
    monkeypatch.setattr(
        "twophase.tools.diagnostics.DiagnosticCollector",
        FakeDiagnostics,
    )

    config = tmp_path / "cfg.yaml"
    config.write_text(
        "\n".join(
            [
                "run:",
                "  T_final: 1.2",
                "  dt_fixed: 0.6",
                "output:",
                "  dir: results/restart-equivalence",
            ]
        )
    )

    def make_cfg(t_final):
        return SimpleNamespace(
            physics=SimpleNamespace(
                rho_l=1.0,
                rho_g=1.0,
                sigma=0.0,
                mu=0.0,
                g_acc=0.0,
                rho_ref=None,
                mu_l=None,
                mu_g=None,
            ),
            run=SimpleNamespace(
                T_final=t_final,
                max_steps=None,
                dt_fixed=0.6,
                snap_interval=None,
                snap_times=[],
                print_every=100,
                debug_diagnostics=False,
                cfl=1.0,
                cfl_advective=None,
                cfl_capillary=None,
                cfl_viscous=None,
            ),
            output=SimpleNamespace(figures=[]),
            diagnostics=["kinetic_energy"],
            initial_condition={},
        )

    continuous_dir = tmp_path / "continuous"
    split_dir = tmp_path / "split"

    continuous = runner.run_simulation(
        make_cfg(1.2),
        checkpoint_path=continuous_dir / "checkpoint_final.npz",
        config_path=config,
    )
    runner.run_simulation(
        make_cfg(1.0),
        checkpoint_path=split_dir / "checkpoint_final.npz",
        config_path=config,
    )
    continuation = split_dir / "checkpoint_continuation.npz"
    manifest = checkpoint.load_manifest(continuation)
    assert manifest["state_phase"] == "pre_step"
    assert manifest["time"] == 0.6
    assert manifest["step"] == 1
    assert manifest["dt_candidate"] == 0.6
    assert manifest["dt_effective"] == 0.4
    assert manifest["terminal_clamped"] is True

    restarted = runner.run_simulation(
        make_cfg(1.2),
        resume_from=continuation,
        checkpoint_path=split_dir / "checkpoint_final.npz",
        config_path=config,
    )

    with np.load(continuous_dir / "checkpoint_final.npz") as a, np.load(
        split_dir / "checkpoint_final.npz"
    ) as b:
        for key in (
            "state/psi",
            "state/u",
            "state/v",
            "state/p",
            "solver/p_prev_dev",
            "solver/p_base_prev_dev",
            "solver/conv_prev/0",
            "solver/conv_prev/1",
            "solver/velocity_prev/0",
            "solver/velocity_prev/1",
            "solver/projected_face_components/0",
            "solver/projected_face_components/1",
            "results/times",
            "results/kinetic_energy",
        ):
            np.testing.assert_array_equal(a[key], b[key], err_msg=key)

    assert continuous["times"].tolist() == [0.6, 1.2]
    assert restarted["times"].tolist() == [0.6, 1.2]
    np.testing.assert_array_equal(continuous["kinetic_energy"], restarted["kinetic_energy"])


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
            "grid_coords": [np.array([0.0, 2.0]), np.array([0.0, 3.0])],
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
    assert flat["fields/grid_coords/0"].shape == (2, 2)
    assert flat["fields/grid_coords/0"][0].tolist() == [0.0, 1.0]
    assert flat["fields/grid_coords/0"][1].tolist() == [0.0, 2.0]


def test_partial_endpoint_snapshot_fields_are_not_stacked():
    runner = _load_ns_simulation_runner()
    flat = {}
    snaps = [
        {
            "t": 0.0,
            "psi": np.zeros((2, 2)),
            "psi_before_transport": np.zeros((2, 2)),
            "psi_after_transport_before_reinit": np.ones((2, 2)),
            "psi_after_reinit": np.ones((2, 2)),
        },
        {"t": 0.5, "psi": np.ones((2, 2))},
    ]

    runner._add_snapshot_series(flat, snaps)

    assert "fields/psi" in flat
    assert "fields/psi_before_transport" not in flat
    assert "fields/psi_after_transport_before_reinit" not in flat
    assert "fields/psi_after_reinit" not in flat


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
        "fields/grid_coords/0": np.array([[0.0, 1.0], [0.0, 2.0]]),
        "fields/grid_coords/1": np.array([[0.0, 1.0], [0.0, 3.0]]),
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
    assert snaps[0]["grid_coords"][0].tolist() == [0.0, 1.0]
    assert snaps[1]["grid_coords"][0].tolist() == [0.0, 2.0]


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
