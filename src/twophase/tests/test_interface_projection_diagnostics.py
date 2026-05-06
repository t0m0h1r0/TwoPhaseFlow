"""Diagnostics for SP-AD interface-projection energy accounting."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.levelset.transport_strategy import PsiDirectTransport
from twophase.simulation.interface_projection_diagnostics import (
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
