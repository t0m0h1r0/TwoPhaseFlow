"""Dense oracle tests for geometric cell-fraction C1."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.coupling.closed_interface_geometry import liquid_area_2d
from twophase.geometry.dense_reference import MetricCellComplex, cut_geometry_2d


def _grid(nx: int = 8, ny: int | None = None):
    ny = nx if ny is None else ny
    backend = Backend(use_gpu=False)
    return Grid(GridConfig(ndim=2, N=(nx, ny), L=(1.0, 1.0)), backend), backend


def _mesh(grid):
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    return np.meshgrid(x, y, indexing="ij")


def test_dense_reference_q_theta_and_surface_for_half_plane():
    grid, _backend = _grid(8)
    x, _ = _mesh(grid)
    phi = x - 0.4

    geometry = cut_geometry_2d(grid, phi)
    complex_h = MetricCellComplex.from_grid(grid)

    np.testing.assert_allclose(float(np.sum(geometry.q)), 0.4)
    np.testing.assert_allclose(geometry.surface_length, 1.0)
    np.testing.assert_allclose(
        np.asarray(geometry.theta),
        np.asarray(geometry.q) / np.asarray(complex_h.cell_measures),
    )
    assert np.all(np.asarray(geometry.theta) >= 0.0)
    assert np.all(np.asarray(geometry.theta) <= 1.0)


def test_dense_reference_q_sum_matches_existing_p1_area_oracle():
    grid, backend = _grid(12)
    x, y = _mesh(grid)
    phi = x + 0.35 * y - 0.63

    geometry = cut_geometry_2d(grid, phi)
    existing_oracle = liquid_area_2d(
        xp=backend.xp,
        grid=grid,
        psi=-phi,
        phase_threshold=0.0,
    )

    np.testing.assert_allclose(
        float(np.sum(geometry.q)),
        float(existing_oracle),
        atol=1.0e-14,
    )
    assert geometry.sign_margin > 0.0


def test_metric_cell_complex_cache_invalidates_on_new_coords():
    grid, _backend = _grid(4)

    first = MetricCellComplex.from_grid(grid)
    second = MetricCellComplex.from_grid(grid)
    assert second is first

    grid.coords[0] = np.asarray([0.0, 0.15, 0.45, 0.75, 1.0], dtype=float)
    third = MetricCellComplex.from_grid(grid)

    assert third is not first
    np.testing.assert_allclose(
        np.asarray(third.cell_measures)[:, 0],
        np.asarray([0.15, 0.30, 0.30, 0.25]) * 0.25,
    )


def test_dense_reference_rejects_degenerate_sign_stratum():
    grid, _backend = _grid(2)
    x, _ = _mesh(grid)

    with pytest.raises(ValueError, match="regular sign stratum"):
        cut_geometry_2d(grid, x - 0.5)
