import numpy as np
import matplotlib.pyplot as plt
import pytest
from types import SimpleNamespace

from twophase.tools.plot_snapshot_figures import (
    build_snapshot_series_shared_spec,
    build_snapshot_series_renderers,
    masked_bulk_pressure,
    pressure_bulk_snapshot,
    pressure_difference_field,
    pressure_hodge_snapshot,
    velocity_snapshot,
)
from twophase.tools.plot_factory import generate_figures
from twophase.tools.pressure_representatives import (
    phase_hodge_pressure_representative_diagnostics,
    phase_hodge_pressure_representative,
)
from twophase.simulation.visualization import plot_velocity


def test_masked_bulk_pressure_is_retired_fail_closed():
    pressure = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
        ]
    )
    psi = np.array(
        [
            [0.0, 0.03, 0.10],
            [0.45, 0.50, 0.55],
            [0.90, 0.97, 1.0],
        ]
    )

    with pytest.raises(ValueError, match="retired"):
        masked_bulk_pressure(pressure, psi)


def test_snapshot_series_registry_exposes_hodge_pressure_only():
    renderers = build_snapshot_series_renderers()

    assert "pressure_bulk" not in renderers
    assert "pressure_hodge" in renderers


def test_generate_figures_fails_on_retired_pressure_bulk(tmp_path):
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
        output=SimpleNamespace(
            figures=[
                {
                    "type": "snapshot_series",
                    "field": "pressure_bulk",
                    "file_prefix": "pressure_bulk_t",
                }
            ]
        ),
    )
    snap = {
        "t": 0.0,
        "psi": np.ones((2, 2)),
        "p": np.ones((2, 2)),
    }

    with pytest.raises(ValueError, match="unknown field 'pressure_bulk'"):
        generate_figures(cfg, {"snapshots": [snap]}, tmp_path)


def test_pressure_bulk_snapshot_is_retired_fail_closed():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=2, NY=2),
    )
    snap = {
        "t": 0.0,
        "psi": np.array(
            [
                [0.0, 0.5, 1.0],
                [0.0, 0.5, 1.0],
                [0.0, 0.5, 1.0],
            ]
        ),
        "p": np.arange(9.0).reshape(3, 3),
    }

    with pytest.raises(ValueError, match="pressure_bulk is retired"):
        pressure_bulk_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg)


def test_phase_hodge_pressure_representative_recovers_same_phase_gradient():
    coords = [np.array([0.0, 1.0]), np.array([0.0, 1.0])]
    x, y = np.meshgrid(coords[0], coords[1], indexing="ij")
    pressure = x + 2.0 * y
    psi = np.ones_like(pressure)
    rho = np.ones_like(pressure)
    face_accel = [
        np.ones((1, 2)),
        np.full((2, 1), 2.0),
    ]

    represented = phase_hodge_pressure_representative(
        psi=psi,
        rho=rho,
        pressure=pressure,
        pressure_accel_faces=face_accel,
        coords=coords,
    )

    np.testing.assert_allclose(represented, pressure, atol=1.0e-12)


def test_phase_hodge_pressure_diagnostics_reports_nonintegrable_face_cochain():
    coords = [np.array([0.0, 1.0]), np.array([0.0, 1.0])]
    pressure = np.zeros((2, 2))
    psi = np.ones_like(pressure)
    rho = np.ones_like(pressure)
    face_accel = [
        np.array([[1.0, 0.0]]),
        np.array([[0.0], [0.0]]),
    ]

    diagnostics = phase_hodge_pressure_representative_diagnostics(
        psi=psi,
        rho=rho,
        pressure=pressure,
        pressure_accel_faces=face_accel,
        coords=coords,
    )

    assert diagnostics.used_face_count == 4
    assert diagnostics.face_relative_residual > 0.0
    assert diagnostics.face_residual_linf > 0.0


def test_pressure_hodge_snapshot_uses_face_cochain_representative():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
        physics=SimpleNamespace(rho_l=1.0, rho_g=1.0),
    )
    coords = [np.array([0.0, 1.0]), np.array([0.0, 1.0])]
    x, y = np.meshgrid(coords[0], coords[1], indexing="ij")
    snap = {
        "t": 0.0,
        "psi": np.ones((2, 2)),
        "p": x + 2.0 * y,
        "rho": np.ones((2, 2)),
        "pressure_accel_faces": [np.ones((1, 2)), np.full((2, 1), 2.0)],
        "grid_coords": coords,
    }

    fig = pressure_hodge_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg)

    assert fig.axes[0].get_title() == "Hodge pressure at t = 0.000"
    plt.close(fig)


def test_pressure_hodge_snapshot_fails_on_nonintegrable_face_cochain():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
        physics=SimpleNamespace(rho_l=1.0, rho_g=1.0),
    )
    snap = {
        "t": 0.0,
        "psi": np.ones((2, 2)),
        "p": np.zeros((2, 2)),
        "rho": np.ones((2, 2)),
        "pressure_accel_faces": [
            np.array([[1.0, 0.0]]),
            np.array([[0.0], [0.0]]),
        ],
        "grid_coords": [np.array([0.0, 1.0]), np.array([0.0, 1.0])],
    }

    with pytest.raises(ValueError, match="cannot represent"):
        pressure_hodge_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg)


def test_pressure_hodge_snapshot_requires_face_cochain():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
        physics=SimpleNamespace(rho_l=1.0, rho_g=1.0),
    )
    snap = {
        "t": 0.0,
        "psi": np.ones((2, 2)),
        "p": np.ones((2, 2)),
        "rho": np.ones((2, 2)),
    }

    with pytest.raises(ValueError, match="requires pressure_accel_faces"):
        pressure_hodge_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg)


def test_velocity_snapshot_can_use_normalized_speed_colored_quiver():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=2, NY=2),
    )
    u = np.array(
        [
            [1.0, 0.0, -2.0],
            [0.0, 0.0, 0.0],
            [3.0, 4.0, 0.0],
        ]
    )
    v = np.array(
        [
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 0.0],
            [4.0, -3.0, 0.0],
        ]
    )
    snap = {
        "t": 0.0,
        "psi": np.ones((3, 3)),
        "u": u,
        "v": v,
    }

    fig = velocity_snapshot(
        {
            "t_idx": 0,
            "quiver_stride": 1,
            "arrow_color": None,
            "arrow_outline_color": None,
        },
        {"snapshots": [snap]},
        cfg,
    )

    quivers = [artist for artist in fig.axes[0].collections if hasattr(artist, "U")]
    assert len(quivers) == 1
    quiver = quivers[0]
    assert np.nanmax(np.sqrt(quiver.U ** 2 + quiver.V ** 2)) <= 1.0 + 1.0e-12
    np.testing.assert_allclose(quiver.get_array(), np.sqrt(u.ravel() ** 2 + v.ravel() ** 2))
    plt.close(fig)


def test_velocity_snapshot_defaults_to_haloed_uniform_arrows():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=2, NY=2),
    )
    snap = {
        "t": 0.0,
        "psi": np.ones((3, 3)),
        "u": np.ones((3, 3)),
        "v": np.zeros((3, 3)),
    }

    fig = velocity_snapshot(
        {"t_idx": 0, "quiver_stride": 1},
        {"snapshots": [snap]},
        cfg,
    )

    quivers = [artist for artist in fig.axes[0].collections if hasattr(artist, "U")]
    assert len(quivers) == 2
    assert quivers[-1].get_array() is None
    assert quivers[-1].get_alpha() == pytest.approx(0.9)
    assert quivers[0].width > quivers[-1].width
    plt.close(fig)


def test_velocity_snapshot_can_suppress_subthreshold_arrows():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
    )
    snap = {
        "t": 0.0,
        "psi": np.ones((2, 2)),
        "u": np.array([[1.0, 0.0], [0.1, 0.0]]),
        "v": np.zeros((2, 2)),
    }

    fig = velocity_snapshot(
        {
            "t_idx": 0,
            "quiver_stride": 1,
            "speed_vmax": 1.0,
            "quiver_min_speed_fraction": 0.5,
        },
        {"snapshots": [snap]},
        cfg,
    )

    quivers = [artist for artist in fig.axes[0].collections if hasattr(artist, "U")]
    assert len(quivers) == 2
    assert quivers[-1].U.size == 1
    plt.close(fig)


def test_velocity_snapshot_can_hide_field_and_color_arrows():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
    )
    snap = {
        "t": 0.0,
        "psi": np.ones((2, 2)),
        "u": np.array([[1.0, 0.0], [0.0, 0.0]]),
        "v": np.array([[0.0, 0.0], [2.0, 0.0]]),
    }

    fig = velocity_snapshot(
        {
            "t_idx": 0,
            "show_field": False,
            "contour": False,
            "quiver_stride": 1,
            "speed_vmax": 2.0,
        },
        {"snapshots": [snap]},
        cfg,
    )

    ax = fig.axes[0]
    quivers = [artist for artist in ax.collections if hasattr(artist, "U")]
    meshes = [artist for artist in ax.collections if not hasattr(artist, "U")]
    assert len(quivers) == 2
    assert quivers[-1].get_array() is not None
    assert quivers[-1].norm.vmax == pytest.approx(2.0)
    assert len(meshes) == 0
    assert len(fig.axes) == 2
    plt.close(fig)


def test_snapshot_series_velocity_uses_shared_speed_and_raw_quiver_scale():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
    )
    psi = np.ones((2, 2))
    snaps = [
        {
            "t": 0.0,
            "psi": psi,
            "u": np.ones((2, 2)),
            "v": np.zeros((2, 2)),
        },
        {
            "t": 1.0,
            "psi": psi,
            "u": 3.0 * np.ones((2, 2)),
            "v": 4.0 * np.ones((2, 2)),
        },
    ]

    shared = build_snapshot_series_shared_spec(
        "velocity",
        {"normalize_arrows": False, "quiver_length_fraction": 0.05},
        snaps,
        cfg,
    )

    assert shared["speed_vmax"] == pytest.approx(5.0)
    assert shared["quiver_scale"] == pytest.approx(100.0)


def test_snapshot_series_velocity_can_use_robust_shared_color_axis():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
    )
    psi = np.ones((2, 2))
    snaps = [
        {
            "t": 0.0,
            "psi": psi,
            "u": np.array([[1.0, 1.0], [1.0, 1.0]]),
            "v": np.zeros((2, 2)),
        },
        {
            "t": 1.0,
            "psi": psi,
            "u": np.array([[1.0, 1.0], [1.0, 100.0]]),
            "v": np.zeros((2, 2)),
        },
    ]

    shared = build_snapshot_series_shared_spec(
        "velocity",
        {
            "speed_scale": "robust",
            "speed_vmax_percentile": 50.0,
            "speed_vmax_margin": 1.0,
            "normalize_arrows": False,
            "quiver_length_fraction": 0.1,
        },
        snaps,
        cfg,
    )

    assert shared["speed_vmax"] == pytest.approx(1.0)
    assert shared["quiver_scale"] == pytest.approx(1000.0)


def test_snapshot_series_velocity_radial_color_uses_symmetric_axis():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
    )
    psi = np.ones((2, 2))
    snap = {
        "t": 0.0,
        "psi": psi,
        "u": np.ones((2, 2)),
        "v": np.zeros((2, 2)),
    }

    shared = build_snapshot_series_shared_spec(
        "velocity",
        {
            "color_quantity": "radial",
            "velocity_center": [0.5, 0.5],
            "color_scale": "max",
            "normalize_arrows": False,
            "quiver_length_fraction": 0.1,
        },
        [snap],
        cfg,
    )

    assert shared["vmin"] < 0.0
    assert shared["vmax"] > 0.0
    assert abs(shared["vmin"]) == pytest.approx(shared["vmax"])
    assert shared["speed_vmax"] == pytest.approx(1.0)
    assert shared["quiver_scale"] == pytest.approx(10.0)


def test_snapshot_series_pressure_uses_shared_symmetric_color_axis():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
    )
    psi = np.ones((2, 2))
    snaps = [
        {"t": 0.0, "psi": psi, "p": np.array([[0.0, 1.0], [2.0, 0.5]])},
        {"t": 1.0, "psi": psi, "p": np.array([[-3.0, 0.0], [1.0, 2.0]])},
    ]

    shared = build_snapshot_series_shared_spec("pressure", {}, snaps, cfg)

    assert shared["vmin"] == pytest.approx(-3.0)
    assert shared["vmax"] == pytest.approx(3.0)


def test_pressure_difference_field_removes_snapshot_gauge():
    pressure = np.array([[100.0, 102.0], [101.0, 101.0]])

    anomaly = pressure_difference_field(pressure, {"pressure_reference": "mean"})

    np.testing.assert_allclose(anomaly, np.array([[-1.0, 1.0], [0.0, 0.0]]))


def test_snapshot_series_pressure_shared_axis_uses_pressure_reference():
    cfg = SimpleNamespace(
        grid=SimpleNamespace(LX=1.0, LY=1.0, NX=1, NY=1),
    )
    psi = np.ones((2, 2))
    snaps = [
        {"t": 0.0, "psi": psi, "p": np.array([[100.0, 102.0], [101.0, 101.0]])},
        {"t": 1.0, "psi": psi, "p": np.array([[200.0, 199.0], [201.0, 200.0]])},
    ]

    shared = build_snapshot_series_shared_spec(
        "pressure",
        {"pressure_reference": "mean"},
        snaps,
        cfg,
    )

    assert shared["vmin"] == pytest.approx(-1.0)
    assert shared["vmax"] == pytest.approx(1.0)


def test_plot_velocity_uses_clean_default_quiver_style():
    class GridStub:
        ndim = 2

        def meshgrid(self):
            coords = np.linspace(0.0, 1.0, 3)
            return np.meshgrid(coords, coords, indexing="ij")

    u = np.ones((3, 3))
    v = np.zeros((3, 3))

    fig = plot_velocity(u, v, GridStub(), quiver_stride=1)

    quivers = [artist for artist in fig.axes[0].collections if hasattr(artist, "U")]
    assert len(quivers) == 2
    assert quivers[-1].get_array() is None
    assert quivers[0].width > quivers[-1].width
    plt.close(fig)
