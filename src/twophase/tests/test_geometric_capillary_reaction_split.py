"""Pressure-adjoint split tests for geometric AO capillarity."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.simulation.geometric_capillary_reaction_split import (
    build_geometric_capillary_reaction_split,
)


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
