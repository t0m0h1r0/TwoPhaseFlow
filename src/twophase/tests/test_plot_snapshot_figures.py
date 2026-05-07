import numpy as np
import matplotlib.pyplot as plt
import pytest
from types import SimpleNamespace

from twophase.tools.plot_snapshot_figures import (
    build_snapshot_series_renderers,
    masked_bulk_pressure,
    pressure_bulk_snapshot,
    pressure_hodge_snapshot,
    velocity_snapshot,
)
from twophase.tools.plot_factory import generate_figures
from twophase.tools.pressure_representatives import (
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


def test_velocity_snapshot_uses_normalized_speed_colored_quiver():
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
        {"t_idx": 0, "quiver_stride": 1},
        {"snapshots": [snap]},
        cfg,
    )

    quivers = [artist for artist in fig.axes[0].collections if hasattr(artist, "U")]
    assert len(quivers) == 1
    quiver = quivers[0]
    assert np.nanmax(np.sqrt(quiver.U ** 2 + quiver.V ** 2)) <= 1.0 + 1.0e-12
    np.testing.assert_allclose(quiver.get_array(), np.sqrt(u.ravel() ** 2 + v.ravel() ** 2))
    plt.close(fig)


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
    assert len(quivers) == 1
    assert quivers[0].cmap.name == "hot"
    plt.close(fig)
