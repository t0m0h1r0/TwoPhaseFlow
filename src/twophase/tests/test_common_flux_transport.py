"""Common-flux transport ledger tests."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.levelset.fccd_advection import FCCDLevelSetAdvection
from twophase.simulation.conservative_transport import (
    ConservativeCommonFluxTransport,
)
from twophase.simulation.ns_grid_rebuild import rebuild_ns_grid
from twophase.simulation.ns_runtime_config import normalise_ns_scheme_runtime
from twophase.simulation.ns_solver_options import SolverSchemeOptions


def _periodic_case(n: int = 12):
    backend = Backend(use_gpu=False)
    xp = backend.xp
    grid = Grid(GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)), backend)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")
    advection = FCCDLevelSetAdvection(
        backend,
        grid,
        fccd,
        mode="flux",
        mass_correction=False,
    )
    x, y = grid.meshgrid()
    psi = 0.45 + 0.08 * xp.sin(2.0 * xp.pi * x) * xp.cos(2.0 * xp.pi * y)
    face_velocity = [
        xp.full((n, n + 1), 0.035),
        xp.full((n + 1, n), -0.025),
    ]
    return backend, grid, fccd, advection, psi, face_velocity


def test_fccd_face_transport_ledger_reproduces_endpoint():
    """The recorded stage flux path must match the existing TVD-RK3 endpoint."""
    _backend, _grid, _fccd, advection, psi, face_velocity = _periodic_case()
    dt = 0.02

    psi_ref = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        dt,
        clip_bounds=None,
    )
    psi_new, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        dt,
        clip_bounds=None,
        return_ledger=True,
    )

    np.testing.assert_allclose(psi_new, psi_ref, rtol=0.0, atol=1.0e-14)
    np.testing.assert_allclose(ledger.psi_after_transport, psi_ref, rtol=0.0, atol=1.0e-14)
    assert len(ledger.stages) == 3
    assert all(len(stage.phase_fluxes) == 2 for stage in ledger.stages)
    np.testing.assert_allclose(ledger.stages[0].phase_state, psi, rtol=0.0, atol=0.0)
    assert not any(stage.post_stage_projected for stage in ledger.stages)


def test_common_flux_preserves_uniform_velocity_energy():
    """Mass and momentum consume the exact recorded phase flux stage-by-stage."""
    _backend, grid, fccd, advection, psi, face_velocity = _periodic_case()
    rho_l = 1000.0
    rho_g = 1.2
    velocity = (0.4, -0.3)
    dt = 0.02

    psi_new, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        dt,
        clip_bounds=None,
        return_ledger=True,
    )
    density = rho_g + (rho_l - rho_g) * ledger.psi_before
    momentum = tuple(density * component for component in velocity)

    transport = ConservativeCommonFluxTransport(Backend(use_gpu=False), grid, fccd)
    result = transport.advance(
        density,
        momentum,
        ledger,
        rho_l=rho_l,
        rho_g=rho_g,
    )

    expected_density = rho_g + (rho_l - rho_g) * psi_new
    np.testing.assert_allclose(result.density, expected_density, rtol=1.0e-12, atol=1.0e-11)
    for component, expected_velocity in zip(result.velocity_components, velocity):
        np.testing.assert_allclose(
            component,
            np.full_like(expected_density, expected_velocity),
            rtol=1.0e-12,
            atol=1.0e-12,
        )
    assert float(result.kinetic_energy_delta) <= 1.0e-10
    assert result.certificate_status == "passed"


def test_common_flux_rejects_unremapped_post_stage_projection():
    """A clipped ψ stage is not accepted as conservative momentum transport."""
    _backend, grid, fccd, advection, psi, face_velocity = _periodic_case()
    rho_l = 10.0
    rho_g = 1.0
    _psi_new, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        0.02,
        return_ledger=True,
    )
    density = rho_g + (rho_l - rho_g) * ledger.psi_before
    momentum = (density * 0.1, density * 0.0)
    transport = ConservativeCommonFluxTransport(Backend(use_gpu=False), grid, fccd)

    with pytest.raises(ValueError, match="unclipped transport ledger"):
        transport.advance(density, momentum, ledger, rho_l=rho_l, rho_g=rho_g)


def test_common_flux_rejects_zero_velocity_clipped_ledger():
    """Even zero-velocity clipping needs a certified (q,M,P) remap."""
    backend, grid, fccd, advection, psi, _face_velocity = _periodic_case()
    xp = backend.xp
    face_velocity = [
        xp.zeros((grid.N[0], grid.N[1] + 1)),
        xp.zeros((grid.N[0] + 1, grid.N[1])),
    ]
    rho_l = 10.0
    rho_g = 1.0
    _psi_new, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        0.02,
        return_ledger=True,
    )
    density = rho_g + (rho_l - rho_g) * ledger.psi_before
    momentum = (density * 0.0, density * 0.0)
    transport = ConservativeCommonFluxTransport(Backend(use_gpu=False), grid, fccd)

    assert ledger.zero_velocity
    with pytest.raises(ValueError, match="unclipped transport ledger"):
        transport.advance(density, momentum, ledger, rho_l=rho_l, rho_g=rho_g)


def test_common_flux_accepts_bound_preserving_flux_limiter():
    """The admissibility limiter changes fluxes, not q alone."""
    _backend, grid, fccd, advection, psi, face_velocity = _periodic_case()
    rho_l = 1000.0
    rho_g = 1.2

    psi_new, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        0.02,
        clip_bounds=None,
        bound_preserving=True,
        return_ledger=True,
    )
    density = rho_g + (rho_l - rho_g) * ledger.psi_before
    momentum = (density * 0.2, density * -0.1)
    transport = ConservativeCommonFluxTransport(Backend(use_gpu=False), grid, fccd)
    result = transport.advance(density, momentum, ledger, rho_l=rho_l, rho_g=rho_g)

    assert ledger.clip_bounds is None
    assert not any(stage.post_stage_projected for stage in ledger.stages)
    expected_density = rho_g + (rho_l - rho_g) * psi_new
    np.testing.assert_allclose(result.density, expected_density, rtol=1.0e-12)


def test_bound_preserving_limiter_keeps_phase_invariant_domain():
    """CFL-admissible high-order fluxes are limited without clipping q."""
    _backend, _grid, _fccd, advection, psi, face_velocity = _periodic_case()
    strong_faces = [20.0 * component for component in face_velocity]

    psi_new, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        strong_faces,
        0.02,
        clip_bounds=None,
        bound_preserving=True,
        return_ledger=True,
    )

    assert ledger.clip_bounds is None
    assert not any(stage.post_stage_projected for stage in ledger.stages)
    assert np.min(psi_new) >= -1.0e-12
    assert np.max(psi_new) <= 1.0 + 1.0e-12


def test_conservative_grid_rebuild_preserves_phase_and_momentum_integrals():
    """Dynamic fitted-grid remap must act on q and rho*u, not velocity alone."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    n = 16
    grid = Grid(
        GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0), alpha_grid=2.0),
        backend,
    )
    fccd = FCCDSolver(grid, backend, bc_type="wall")
    ccd = CCDSolver(grid, backend, bc_type="wall")
    x, y = grid.meshgrid()
    psi = 0.5 + 0.25 * xp.tanh((0.23 - ((x - 0.5) ** 2 + (y - 0.5) ** 2)) / 0.04)
    psi = xp.clip(psi, 0.0, 1.0)
    rho_l = 10.0
    rho_g = 1.0
    density = rho_g + (rho_l - rho_g) * psi
    u = 0.2 + 0.1 * x
    v = -0.1 + 0.05 * y
    momentum = (density * u, density * v)
    dV_old = grid.cell_volumes()
    q_target = float(xp.sum(psi * dV_old))
    m_targets = [float(xp.sum(component * dV_old)) for component in momentum]

    result = rebuild_ns_grid(
        backend=backend,
        grid=grid,
        ccd=ccd,
        eps=0.04,
        alpha_grid=2.0,
        psi=psi,
        u=u,
        v=v,
        rho_l=rho_l,
        rho_g=rho_g,
        use_local_eps=False,
        curvature_operator=type("Curv", (), {"eps": 0.04})(),
        make_eps_field=lambda: 0.04,
        reinitializer=type("Reinit", (), {"update_grid": lambda self, grid: None})(),
        ppe_solver=type(
            "PPE",
            (),
            {
                "update_grid": lambda self, grid: None,
                "invalidate_cache": lambda self: None,
            },
        )(),
        fccd_div_op=type("Div", (), {"update_weights": lambda self: None})(),
        div_op=None,
        ppe_runtime=None,
        reprojector=type(
            "Reprojector",
            (),
            {"reproject": lambda self, psi, u, v, *args, **kwargs: (u, v)},
        )(),
        conservative_momentum_components=momentum,
        bc_type="wall",
    )

    dV_new = grid.cell_volumes()
    assert float(xp.sum(result.psi * dV_new)) == pytest.approx(q_target, abs=1.0e-12)
    assert result.momentum_components is not None
    for component, target in zip(result.momentum_components, m_targets, strict=True):
        assert float(xp.sum(component * dV_new)) == pytest.approx(target, abs=1.0e-12)
    np.testing.assert_allclose(result.density, rho_g + (rho_l - rho_g) * result.psi)
    np.testing.assert_allclose(result.u, result.momentum_components[0] / result.density)
    np.testing.assert_allclose(result.v, result.momentum_components[1] / result.density)


def test_common_flux_rejects_density_not_affine_in_phase():
    """Density is the affine image of q, not a separately retracted field."""
    _backend, grid, fccd, advection, psi, face_velocity = _periodic_case()
    rho_l = 1000.0
    rho_g = 1.2
    _psi_new, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        0.02,
        clip_bounds=None,
        return_ledger=True,
    )
    density = rho_g + (rho_l - rho_g) * ledger.psi_before
    density = density.copy()
    density[0, 0] += 1.0
    momentum = (density * 0.25, density * -0.5)
    transport = ConservativeCommonFluxTransport(Backend(use_gpu=False), grid, fccd)

    with pytest.raises(ValueError, match="affine phase density"):
        transport.advance(density, momentum, ledger, rho_l=rho_l, rho_g=rho_g)


def test_conservative_common_flux_yaml_route_normalises():
    """The YAML UX reaches a distinct conservative runtime route."""
    options = SolverSchemeOptions(
        momentum_form="conservative_common_flux",
        convection_time_scheme="ab2",
        viscous_time_scheme="crank_nicolson",
    )

    state = normalise_ns_scheme_runtime(options)

    assert state.momentum_form == "conservative_common_flux"
