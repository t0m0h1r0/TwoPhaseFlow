import numpy as np
import matplotlib.pyplot as plt
from types import SimpleNamespace

from twophase.tools.plot_snapshot_figures import (
    build_snapshot_series_renderers,
    masked_bulk_pressure,
    pressure_bulk_snapshot,
)


def test_masked_bulk_pressure_keeps_only_one_sided_bulk_values():
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

    bulk_pressure = masked_bulk_pressure(
        pressure,
        psi,
        gas_max_psi=0.05,
        liquid_min_psi=0.95,
    )

    np.testing.assert_allclose(
        bulk_pressure[[0, 0, 2, 2], [0, 1, 1, 2]],
        [1.0, 2.0, 8.0, 9.0],
    )
    assert np.isnan(bulk_pressure[0, 2])
    assert np.isnan(bulk_pressure[1, 1])
    assert np.isnan(bulk_pressure[2, 0])


def test_snapshot_series_registry_exposes_bulk_pressure_renderer():
    renderers = build_snapshot_series_renderers()

    assert "pressure_bulk" in renderers


def test_pressure_bulk_snapshot_renders_without_interface_values():
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

    fig = pressure_bulk_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg)

    assert fig.axes[0].get_title() == "Bulk pressure at t = 0.000"
    plt.close(fig)
