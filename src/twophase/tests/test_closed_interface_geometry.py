"""Closed-interface fixed-stratum geometry tests."""

from __future__ import annotations

import numpy as np

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.coupling.closed_interface_geometry import (
    fixed_stratum_directional_derivative_check,
    liquid_area_2d,
    liquid_area_gradient_2d,
    trace_surface_length_2d,
    trace_surface_length_gradient_2d,
)
from twophase.coupling.transport_variational_capillary import (
    marching_squares_liquid_area_2d,
)
from twophase.coupling.closed_interface_stratum import (
    build_closed_interface_stratum,
)


def _grid(n=16):
    backend = Backend(use_gpu=False)
    return Grid(GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)), backend), backend


def _linear_psi(grid, *, offset=0.63):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    return X + 0.35 * Y - offset


def test_stratum_hash_is_stable_inside_same_cut_pattern():
    grid, backend = _grid(12)
    xp = backend.xp
    psi = _linear_psi(grid)
    perturbation = 1.0e-5 * np.sin(2.0 * np.pi * np.asarray(grid.coords[0]))[:, None]

    stratum = build_closed_interface_stratum(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=0.0,
    )

    assert stratum.regular
    assert stratum.cut_cell_count > 0
    assert stratum.matches(
        xp=xp,
        grid=grid,
        psi=psi + perturbation,
    )


def test_stratum_marks_threshold_touch_as_irregular():
    grid, backend = _grid(4)
    xp = backend.xp
    psi = _linear_psi(grid)
    psi[2, 2] = 0.0

    stratum = build_closed_interface_stratum(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=0.0,
    )

    assert not stratum.regular
    assert stratum.threshold_touch_count == 1


def test_trace_length_and_area_match_axis_aligned_half_plane():
    grid, backend = _grid(8)
    xp = backend.xp
    x = np.asarray(grid.coords[0])
    X, _ = np.meshgrid(x, np.asarray(grid.coords[1]), indexing="ij")
    psi = X - 0.4

    length = trace_surface_length_2d(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=0.0,
    )
    area = liquid_area_2d(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=0.0,
    )

    np.testing.assert_allclose(float(length), 1.0)
    np.testing.assert_allclose(float(area), 0.6)


def test_vectorized_liquid_area_matches_legacy_polygon_cases():
    grid, backend = _grid(4)
    xp = backend.xp
    rng = np.random.default_rng(20260508)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    psi = X - 0.43 + 0.17 * np.sin(2.0 * np.pi * Y) + 0.03 * rng.standard_normal(X.shape)

    legacy = liquid_area_2d(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=0.0,
    )
    vectorized = marching_squares_liquid_area_2d(
        xp=xp,
        grid=grid,
        psi=psi,
        phase_threshold=0.0,
    )

    np.testing.assert_allclose(float(vectorized), float(legacy), rtol=0.0, atol=1.0e-14)


def test_vectorized_liquid_area_matches_legacy_for_all_cell_cases():
    grid, backend = _grid(1)
    xp = backend.xp

    for case_id in range(16):
        psi = np.empty((2, 2), dtype=float)
        corner_indices = ((0, 0), (1, 0), (1, 1), (0, 1))
        for corner, index in enumerate(corner_indices):
            if case_id & (1 << corner):
                psi[index] = 0.7 + 0.03 * corner
            else:
                psi[index] = -0.4 - 0.05 * corner

        legacy = liquid_area_2d(
            xp=xp,
            grid=grid,
            psi=psi,
            phase_threshold=0.0,
        )
        vectorized = marching_squares_liquid_area_2d(
            xp=xp,
            grid=grid,
            psi=psi,
            phase_threshold=0.0,
        )

        np.testing.assert_allclose(
            float(vectorized),
            float(legacy),
            rtol=0.0,
            atol=1.0e-14,
            err_msg=f"case_id={case_id}",
        )


def test_trace_length_gradient_matches_fixed_stratum_difference():
    grid, backend = _grid(16)
    xp = backend.xp
    psi = _linear_psi(grid)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    direction = np.sin(np.pi * X) * np.cos(2.0 * np.pi * Y)

    check = fixed_stratum_directional_derivative_check(
        xp=xp,
        grid=grid,
        psi=psi,
        direction=direction,
        value_fn=trace_surface_length_2d,
        gradient_fn=trace_surface_length_gradient_2d,
        epsilon=1.0e-6,
        phase_threshold=0.0,
    )

    assert check.valid, check.reason
    assert check.residual < 1.0e-7


def test_liquid_area_gradient_matches_fixed_stratum_difference():
    grid, backend = _grid(16)
    xp = backend.xp
    psi = _linear_psi(grid)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    direction = np.cos(2.0 * np.pi * X) * np.sin(np.pi * Y)

    check = fixed_stratum_directional_derivative_check(
        xp=xp,
        grid=grid,
        psi=psi,
        direction=direction,
        value_fn=liquid_area_2d,
        gradient_fn=liquid_area_gradient_2d,
        epsilon=1.0e-6,
        phase_threshold=0.0,
    )

    assert check.valid, check.reason
    assert check.residual < 1.0e-7


def test_fixed_stratum_check_fails_closed_on_irregular_base():
    grid, backend = _grid(4)
    xp = backend.xp
    psi = _linear_psi(grid)
    psi[2, 2] = 0.0
    direction = np.ones_like(psi)

    check = fixed_stratum_directional_derivative_check(
        xp=xp,
        grid=grid,
        psi=psi,
        direction=direction,
        value_fn=liquid_area_2d,
        gradient_fn=liquid_area_gradient_2d,
        epsilon=1.0e-6,
        phase_threshold=0.0,
    )

    assert not check.valid
    assert check.reason == "irregular_base_stratum"
