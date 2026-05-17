"""Tests for PhaseRegion force-admission contract helpers."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.coupling.closed_interface_riesz import (
    face_measure_components,
    transport_increment_from_face_velocity,
)
from twophase.coupling.phase_region_force_admission import (
    phase_region_face_mass_metric,
    scale_face_velocity_to_fixed_stratum,
    two_phase_nodal_density,
)


def _setup(nx: int = 4, ny: int = 5):
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(nx, ny), L=(1.2, 0.8)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    return grid, backend, fccd


def _nodal_psi(grid: Grid) -> np.ndarray:
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    X, Y = np.meshgrid(x / x[-1], y / y[-1], indexing="ij")
    return 0.52 + 0.18 * X + 0.08 * Y


def test_two_phase_nodal_density_matches_runtime_indicator_formula():
    grid, backend, _ = _setup()
    psi = _nodal_psi(grid)

    rho = two_phase_nodal_density(
        xp=backend.xp,
        psi=psi,
        rho_l=10.0,
        rho_g=2.0,
    )

    np.testing.assert_allclose(rho, 2.0 + 8.0 * psi)
    assert float(np.min(rho)) == pytest.approx(2.0 + 8.0 * float(np.min(psi)))
    assert float(np.max(rho)) == pytest.approx(2.0 + 8.0 * float(np.max(psi)))


def test_phase_region_face_metric_uses_nodal_density_on_faces():
    grid, backend, _ = _setup()
    xp = backend.xp
    psi = _nodal_psi(grid)
    metric = phase_region_face_mass_metric(
        xp=xp,
        grid=grid,
        psi=psi,
        rho_l=10.0,
        rho_g=2.0,
    )

    rho = 2.0 + 8.0 * psi
    measures = face_measure_components(xp=xp, grid=grid)
    expected_x = 0.5 * (rho[:-1, :] + rho[1:, :]) * np.asarray(measures[0])
    expected_y = 0.5 * (rho[:, :-1] + rho[:, 1:]) * np.asarray(measures[1])

    np.testing.assert_allclose(metric.rho_node, rho)
    np.testing.assert_allclose(metric.face_weight_components[0], expected_x)
    np.testing.assert_allclose(metric.face_weight_components[1], expected_y)
    assert metric.rho_min == pytest.approx(float(np.min(rho)))
    assert metric.rho_max == pytest.approx(float(np.max(rho)))


def test_phase_region_face_metric_rejects_cell_density_shape():
    grid, backend, _ = _setup()
    cell_indicator = np.full(tuple(grid.N), 0.6, dtype=float)

    with pytest.raises(ValueError, match="nodal grid shape"):
        phase_region_face_mass_metric(
            xp=backend.xp,
            grid=grid,
            psi=cell_indicator,
            rho_l=10.0,
            rho_g=2.0,
        )


def test_scale_face_velocity_to_fixed_stratum_limits_transport_increment():
    grid, backend, fccd = _setup()
    xp = backend.xp
    psi = _nodal_psi(grid)
    faces = [
        10.0 * xp.ones((grid.N[0], grid.N[1] + 1)),
        -8.0 * xp.ones((grid.N[0] + 1, grid.N[1])),
    ]
    fd_eps = 1.0e-3
    sign_fraction = 2.0e-2

    scaled = scale_face_velocity_to_fixed_stratum(
        xp=xp,
        fccd=fccd,
        psi=psi,
        face_velocity_components=faces,
        fd_eps=fd_eps,
        sign_fraction=sign_fraction,
    )

    delta = transport_increment_from_face_velocity(
        xp=xp,
        fccd=fccd,
        psi=psi,
        face_velocity_components=scaled.face_velocity_components,
    )
    signed = psi - 0.5
    plus = psi + fd_eps * np.asarray(delta)
    minus = psi - fd_eps * np.asarray(delta)

    assert scaled.valid, scaled.reason
    assert 0.0 < scaled.scale < 1.0
    limit = sign_fraction * scaled.sign_margin
    assert fd_eps * float(np.max(np.abs(delta))) <= limit + 1.0e-12
    np.testing.assert_array_equal(np.sign(plus - 0.5), np.sign(signed))
    np.testing.assert_array_equal(np.sign(minus - 0.5), np.sign(signed))


def test_scale_face_velocity_to_fixed_stratum_fails_on_zero_sign_margin():
    grid, backend, fccd = _setup()
    xp = backend.xp
    psi = np.full(tuple(grid.shape), 0.5, dtype=float)
    faces = [
        xp.ones((grid.N[0], grid.N[1] + 1)),
        xp.ones((grid.N[0] + 1, grid.N[1])),
    ]

    scaled = scale_face_velocity_to_fixed_stratum(
        xp=xp,
        fccd=fccd,
        psi=psi,
        face_velocity_components=faces,
        fd_eps=1.0e-3,
    )

    assert not scaled.valid
    assert scaled.reason == "zero_sign_margin"
    assert scaled.scale == 0.0
