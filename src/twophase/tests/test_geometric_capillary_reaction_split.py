"""Pressure-adjoint split tests for geometric AO capillarity."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.simulation.geometric_capillary_reaction_split import (
    build_geometric_capillary_reaction_split,
)
from twophase.simulation.ns_step_services import _geometric_to_projection_face_pair_2d


def test_geometric_capillary_split_removes_component_reaction():
    xp = np
    rho = xp.ones(1)
    raw = [xp.asarray([1.0, -1.0])]
    reaction = [[xp.asarray([1.0, -1.0])]]

    class MeanRangeFaces:
        def divergence_from_faces(self, face_components):
            return xp.asarray([xp.sum(face_components[0])])

        def pressure_fluxes(self, pressure, rho, **kwargs):
            return [0.5 * xp.asarray(pressure)[0] * xp.ones(2)]

    class MeanRangeSolver:
        def set_interface_jump_context(self, **kwargs):
            self.context = kwargs

        def set_static_operator_cache(self, enabled):
            self.cache = bool(enabled)

        def solve(self, rhs, rho, dt=0.0, p_init=None):
            return xp.asarray(rhs)

    split = build_geometric_capillary_reaction_split(
        xp=xp,
        div_op=MeanRangeFaces(),
        ppe_solver=MeanRangeSolver(),
        rho=rho,
        pressure_flux_kwargs={},
        raw_source_face_acceleration=raw,
        component_reaction_face_accelerations=reaction,
        face_weight_components=[2.0 * xp.ones_like(raw[0])],
    )

    assert split.status == "pressure_component_hodge_split"
    np.testing.assert_allclose(split.component_coefficients, 1.0)
    np.testing.assert_allclose(split.corrected_source_face_acceleration[0], 0.0)
    np.testing.assert_allclose(split.pressure_range_coordinate, 0.0)
    np.testing.assert_allclose(split.balanced_face_acceleration[0], 0.0)
    assert split.raw_source_weighted_l2 == pytest.approx(2.0)
    assert split.balanced_weighted_l2 == pytest.approx(0.0)


def test_geometric_capillary_split_retains_nonpressure_hodge_drive():
    xp = np
    rho = xp.ones(1)
    raw = [xp.asarray([1.0, -1.0, 0.0])]
    reaction = [[xp.asarray([1.0, 1.0, -2.0])]]

    class MeanRangeFaces:
        def divergence_from_faces(self, face_components):
            return xp.asarray([xp.sum(face_components[0])])

        def pressure_fluxes(self, pressure, rho, **kwargs):
            return [(xp.asarray(pressure)[0] / 3.0) * xp.ones(3)]

    class MeanRangeSolver:
        def set_interface_jump_context(self, **kwargs):
            self.context = kwargs

        def solve(self, rhs, rho, dt=0.0, p_init=None):
            return xp.asarray(rhs)

    split = build_geometric_capillary_reaction_split(
        xp=xp,
        div_op=MeanRangeFaces(),
        ppe_solver=MeanRangeSolver(),
        rho=rho,
        pressure_flux_kwargs={},
        raw_source_face_acceleration=raw,
        component_reaction_face_accelerations=reaction,
        face_weight_components=[xp.ones_like(raw[0])],
    )

    np.testing.assert_allclose(split.component_coefficients, 0.0)
    np.testing.assert_allclose(split.pressure_range_face_acceleration[0], 0.0)
    np.testing.assert_allclose(split.balanced_face_acceleration[0], raw[0])
    assert split.balanced_weighted_l2 == pytest.approx(np.sqrt(2.0))


def test_ao_face_bridge_converts_volume_cochains_on_nonuniform_grid():
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(2, 3), L=(3.0, 3.0)), backend)
    grid.coords[0] = np.asarray([0.0, 1.0, 3.0])
    grid.coords[1] = np.asarray([0.0, 0.5, 1.5, 3.0])
    dx = np.diff(grid.coords[0])
    dy = np.diff(grid.coords[1])

    x_velocity = 2.0
    y_velocity = -3.0
    x_cochain = x_velocity * dy.reshape((1, 3)) * np.ones((3, 3))
    y_cochain = y_velocity * dx.reshape((2, 1)) * np.ones((2, 4))

    projected = _geometric_to_projection_face_pair_2d(
        xp=np,
        grid=grid,
        face_pair=[x_cochain, y_cochain],
        boundary=("periodic", "wall"),
    )

    np.testing.assert_allclose(projected[0], x_velocity)
    np.testing.assert_allclose(projected[1], y_velocity)


def test_ao_face_bridge_uses_periodic_seam_metric_weights():
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(2, 2), L=(3.0, 1.0)), backend)
    grid.coords[0] = np.asarray([0.0, 1.0, 3.0])
    grid.coords[1] = np.asarray([0.0, 0.25, 1.0])
    dx = np.diff(grid.coords[0])

    y_velocity = np.asarray([[10.0, 10.0, 10.0], [20.0, 20.0, 20.0]])
    y_cochain = y_velocity * dx.reshape((2, 1))
    x_cochain = np.zeros((3, 2))

    projected = _geometric_to_projection_face_pair_2d(
        xp=np,
        grid=grid,
        face_pair=[x_cochain, y_cochain],
        boundary=("periodic", "wall"),
    )

    expected_seam = (dx[0] * 20.0 + dx[-1] * 10.0) / (dx[-1] + dx[0])
    np.testing.assert_allclose(projected[1][0, :], expected_seam)
    np.testing.assert_allclose(projected[1][-1, :], expected_seam)
