"""Diagnostics for SP-AD interface-projection energy accounting."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.coupling.interface_stress_closure import InterfaceStressContext
from twophase.levelset.transport_strategy import PsiDirectTransport
from twophase.simulation.interface_projection_diagnostics import (
    capillary_component_hodge_augmented_projection,
    capillary_external_component_saddle_projection,
    capillary_jump_range_projection,
    capillary_face_cochain_diagnostics,
    reinit_projection_diagnostics,
)


def _circle_psi(grid, *, radius: float = 0.25):
    X, Y = grid.meshgrid()
    phi = ((X - 0.5) ** 2 + (Y - 0.5) ** 2) ** 0.5 - radius
    eps = 1.5 * min(float(np.min(h)) for h in grid.h)
    return 1.0 / (1.0 + grid.xp.exp(phi / eps))


def test_reinit_projection_diagnostics_identity_is_zero():
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)), backend)
    psi = _circle_psi(grid)

    diag = reinit_projection_diagnostics(
        xp=backend.xp,
        backend=backend,
        grid=grid,
        psi_before=psi,
        psi_after=psi.copy(),
        sigma=0.072,
    )

    assert diag["reinit_triggered"] == pytest.approx(1.0)
    assert diag["reinit_volume_delta"] == pytest.approx(0.0, abs=1.0e-14)
    assert diag["reinit_surface_energy_delta"] == pytest.approx(0.0, abs=1.0e-14)
    assert diag["reinit_linf_delta"] == pytest.approx(0.0, abs=1.0e-14)
    assert diag["reinit_zero_level_displacement"] == pytest.approx(0.0, abs=1.0e-14)
    assert diag["reinit_zero_crossing_change_count"] == pytest.approx(0.0)


def test_reinit_projection_diagnostics_detects_trace_motion():
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)), backend)
    psi_before = _circle_psi(grid, radius=0.25)
    psi_after = _circle_psi(grid, radius=0.27)

    diag = reinit_projection_diagnostics(
        xp=backend.xp,
        backend=backend,
        grid=grid,
        psi_before=psi_before,
        psi_after=psi_after,
        sigma=0.072,
    )

    assert abs(diag["reinit_volume_delta"]) > 0.0
    assert abs(diag["reinit_surface_energy_delta"]) > 0.0
    assert diag["reinit_linf_delta"] > 0.0
    assert diag["reinit_zero_level_displacement"] > 0.0


def test_capillary_face_cochain_diagnostics_exposes_divergence_small_face_large():
    backend = Backend(use_gpu=False)
    xp = backend.xp
    faces = [xp.ones((3, 4)), -2.0 * xp.ones((4, 3))]

    class ZeroDivergence:
        def divergence_from_faces(self, face_components):
            return xp.zeros((4, 4))

    diag = capillary_face_cochain_diagnostics(
        xp=xp,
        backend=backend,
        div_op=ZeroDivergence(),
        face_components=faces,
    )

    assert diag["capillary_face_linf"] == pytest.approx(2.0)
    assert diag["capillary_face_divergence_linf"] == pytest.approx(0.0)
    assert diag["capillary_hodge_residual"] == pytest.approx(2.0)
    assert diag["capillary_hodge_divergence_linf"] == pytest.approx(0.0)
    assert diag["capillary_range_projection_solved"] == pytest.approx(0.0)


def test_capillary_face_cochain_diagnostics_reports_weighted_hodge_norms():
    backend = Backend(use_gpu=False)
    xp = backend.xp
    faces = [xp.asarray([[3.0, 4.0]])]
    projection = [xp.asarray([[1.0, 1.0]])]
    hodge = [faces[0] - projection[0]]
    weights = [xp.asarray([[2.0, 8.0]])]

    class ZeroDivergence:
        def divergence_from_faces(self, face_components):
            return xp.zeros((1, 2))

    diag = capillary_face_cochain_diagnostics(
        xp=xp,
        backend=backend,
        div_op=ZeroDivergence(),
        face_components=hodge,
        capillary_jump_components=faces,
        range_projection_components=projection,
        hodge_residual_components=hodge,
        face_weight_components=weights,
    )

    assert diag["capillary_jump_weighted_l2"] == pytest.approx(
        np.sqrt(3.0 * 3.0 * 2.0 + 4.0 * 4.0 * 8.0)
    )
    assert diag["capillary_range_projection_weighted_l2"] == pytest.approx(
        np.sqrt(1.0 * 1.0 * 2.0 + 1.0 * 1.0 * 8.0)
    )
    assert diag["capillary_hodge_weighted_l2"] == pytest.approx(
        np.sqrt(2.0 * 2.0 * 2.0 + 3.0 * 3.0 * 8.0)
    )
    assert diag["capillary_static_critical_residual_ratio"] == pytest.approx(0.0)


def test_capillary_face_cochain_diagnostics_reports_static_criticality():
    backend = Backend(use_gpu=False)

    static_criticality = type(
        "StaticCriticality",
        (),
        {
            "surface_vertex_l2": 3.0,
            "residual_l2": 0.75,
            "residual_ratio": 0.25,
            "component_count": 2,
        },
    )()

    class ZeroDivergence:
        def divergence_from_faces(self, face_components):
            return np.zeros((1, 1))

    diag = capillary_face_cochain_diagnostics(
        xp=np,
        backend=backend,
        div_op=ZeroDivergence(),
        face_components=[np.zeros((1, 1))],
        static_criticality=static_criticality,
    )

    assert diag["capillary_static_critical_surface_l2"] == pytest.approx(3.0)
    assert diag["capillary_static_critical_residual_l2"] == pytest.approx(0.75)
    assert diag["capillary_static_critical_residual_ratio"] == pytest.approx(0.25)
    assert diag["capillary_static_critical_component_count"] == pytest.approx(2.0)


def test_capillary_jump_range_projection_restores_solver_and_removes_range_part():
    xp = np
    rho = xp.ones((2, 2))
    jump = xp.full((2, 2), 3.0)
    context = InterfaceStressContext(
        psi=xp.ones((2, 2)),
        pressure_jump_gas_minus_liquid=jump,
        kappa_lg=xp.ones((2, 2)),
        sigma=1.0,
    )

    class IdentityRangeFaces:
        def pressure_fluxes(self, pressure, rho, **kwargs):
            flux_context = kwargs["interface_stress_context"]
            pressure_arr = xp.asarray(pressure)
            if flux_context.pressure_jump_gas_minus_liquid is None:
                return [pressure_arr]
            return [pressure_arr - flux_context.pressure_jump_gas_minus_liquid]

        def divergence_from_faces(self, face_components):
            return xp.asarray(face_components[0])

    class RestorableSolver:
        def __init__(self):
            self.marker = "original"
            self.last_diagnostics = {"ppe_dc_converged": 1.0}

        def set_interface_jump_context(self, **kwargs):
            self.marker = f"sigma={kwargs['sigma']}"

        def invalidate_cache(self):
            self.cache_invalidated = True

        def solve(self, rhs, rho, dt=0.0, p_init=None):
            self.marker = "mutated-by-solve"
            self.last_diagnostics = {"overwritten": 1.0}
            return xp.asarray(rhs)

    div_op = IdentityRangeFaces()
    ppe_solver = RestorableSolver()
    projection = capillary_jump_range_projection(
        xp=xp,
        div_op=div_op,
        ppe_solver=ppe_solver,
        rho=rho,
        pressure_flux_kwargs={"interface_stress_context": context},
    )

    np.testing.assert_allclose(projection["capillary_jump_components"][0], jump)
    np.testing.assert_allclose(projection["range_projection_components"][0], jump)
    np.testing.assert_allclose(projection["hodge_residual_components"][0], 0.0)
    assert ppe_solver.marker == "original"
    assert ppe_solver.last_diagnostics == {"ppe_dc_converged": 1.0}
    assert not hasattr(ppe_solver, "cache_invalidated")

    diag = capillary_face_cochain_diagnostics(
        xp=xp,
        backend=Backend(use_gpu=False),
        div_op=div_op,
        face_components=[xp.zeros_like(rho)],
        **projection,
    )
    assert diag["capillary_jump_linf"] == pytest.approx(3.0)
    assert diag["capillary_range_projection_linf"] == pytest.approx(3.0)
    assert diag["capillary_hodge_residual"] == pytest.approx(0.0)
    assert diag["capillary_range_projection_solved"] == pytest.approx(1.0)


def test_component_hodge_augmented_projection_removes_unit_reaction_component():
    xp = np
    rho = xp.ones(2)
    jump = xp.asarray([2.0, 4.0])
    context = InterfaceStressContext(
        psi=xp.asarray([1.0, 0.0]),
        pressure_jump_gas_minus_liquid=jump,
        kappa_lg=xp.zeros(2),
        sigma=1.0,
    )

    class ZeroRangeFaces:
        def pressure_fluxes(self, pressure, rho, **kwargs):
            flux_context = kwargs["interface_stress_context"]
            if flux_context.pressure_jump_gas_minus_liquid is None:
                return [xp.zeros_like(rho)]
            return [-xp.asarray(flux_context.pressure_jump_gas_minus_liquid)]

        def divergence_from_faces(self, face_components):
            return xp.zeros_like(face_components[0])

    class ZeroRangeSolver:
        def set_interface_jump_context(self, **kwargs):
            self.sigma = kwargs["sigma"]

        def solve(self, rhs, rho, dt=0.0, p_init=None):
            return xp.zeros_like(rho)

    projection = capillary_component_hodge_augmented_projection(
        xp=xp,
        div_op=ZeroRangeFaces(),
        ppe_solver=ZeroRangeSolver(),
        rho=rho,
        pressure_flux_kwargs={"interface_stress_context": context},
    )

    np.testing.assert_allclose(
        projection["component_hodge_coefficients"],
        3.0,
    )
    np.testing.assert_allclose(
        projection["corrected_jump_components"][0],
        xp.asarray([-1.0, 1.0]),
    )
    np.testing.assert_allclose(
        projection["hodge_residual_components"][0],
        xp.asarray([-1.0, 1.0]),
    )


def test_external_component_saddle_projection_removes_reaction_row():
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

        def invalidate_cache(self):
            self.invalidated = True

        def set_static_operator_cache(self, enabled):
            cache_events.append(bool(enabled))

        def solve(self, rhs, rho, dt=0.0, p_init=None):
            return xp.asarray(rhs)

    cache_events = []
    solver = MeanRangeSolver()
    projection = capillary_external_component_saddle_projection(
        xp=xp,
        div_op=MeanRangeFaces(),
        ppe_solver=solver,
        rho=rho,
        pressure_flux_kwargs={},
        raw_components=raw,
        component_reaction_components=reaction,
        face_weight_components=[2.0 * xp.ones_like(raw[0])],
    )

    np.testing.assert_allclose(projection["component_hodge_coefficients"], 1.0)
    np.testing.assert_allclose(projection["corrected_jump_components"][0], 0.0)
    np.testing.assert_allclose(projection["hodge_residual_components"][0], 0.0)
    assert projection["contract_active_metric"] == pytest.approx(1.0)
    assert projection["contract_pressure_adjoint_residual"] == pytest.approx(0.0)
    assert projection["contract_saddle_constraint_linf"] == pytest.approx(0.0)
    assert cache_events == [True]
    assert not hasattr(solver, "invalidated")


def test_psi_direct_transport_records_reinit_projection_pair():
    backend = Backend(use_gpu=False)
    xp = backend.xp

    class GridStub:
        def cell_volumes(self):
            return xp.ones((2, 2))

    class IdentityAdvection:
        def advance(self, psi, velocity, dt):
            return xp.asarray(psi)

    class SmoothingReinitializer:
        def reinitialize(self, psi):
            return 0.5 * xp.asarray(psi) + 0.25

    psi = xp.asarray([[0.0, 0.2], [0.8, 1.0]])
    transport = PsiDirectTransport(
        backend,
        IdentityAdvection(),
        SmoothingReinitializer(),
        reinit_every=1,
        grid=GridStub(),
        mass_correction=True,
    )
    transport.record_reinit_projection = True

    result = transport.advance(
        psi,
        [xp.zeros_like(psi), xp.zeros_like(psi)],
        dt=0.1,
        step_index=1,
    )

    projection = transport.last_reinit_projection
    assert projection["triggered"] is True
    np.testing.assert_allclose(projection["psi_before"], psi)
    np.testing.assert_allclose(projection["psi_after"], result)
    np.testing.assert_allclose(projection["psi_before_transport"], psi)
    np.testing.assert_allclose(
        projection["psi_after_transport_before_reinit"],
        psi,
    )
    np.testing.assert_allclose(projection["psi_after_reinit"], result)
