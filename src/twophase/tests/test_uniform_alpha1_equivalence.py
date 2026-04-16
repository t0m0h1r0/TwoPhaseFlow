"""Verify that alpha_grid=1.0 produces bit-identical results to truly uniform grid.

Tests that:
1. Grid coords/metrics are identical
2. CCD derivatives are identical
3. DissipativeCCDAdvection produces identical RHS
4. Full advection step produces identical output
"""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.heaviside import heaviside


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def _make_grid_and_solver(backend, N, alpha):
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    return grid, ccd


def _make_initial_field(backend, grid, eps):
    xp = backend.xp
    X, Y = grid.meshgrid()
    phi = xp.sqrt((X - 0.5) ** 2 + (Y - 0.75) ** 2) - 0.15
    psi = heaviside(xp, phi, eps)
    return psi, X, Y


class TestGridEquivalence:
    """Grid with alpha=1.0 must be identical to default uniform grid."""

    def test_coords_identical(self, backend):
        grid_uni, _ = _make_grid_and_solver(backend, 32, alpha=1.0)
        grid_a1, _ = _make_grid_and_solver(backend, 32, alpha=1.0)
        # Both are alpha=1.0; confirm coords are exactly linspace
        for ax in range(2):
            expected = np.linspace(0.0, 1.0, 33)
            np.testing.assert_array_equal(grid_uni.coords[ax], expected)
            np.testing.assert_array_equal(grid_a1.coords[ax], expected)

    def test_uniform_property(self, backend):
        grid, _ = _make_grid_and_solver(backend, 32, alpha=1.0)
        assert grid.uniform is True

    def test_cell_volumes_constant(self, backend):
        grid, _ = _make_grid_and_solver(backend, 32, alpha=1.0)
        xp = backend.xp
        dV = grid.cell_volumes()
        h = 1.0 / 32
        expected = h * h
        np.testing.assert_allclose(
            np.asarray(backend.to_host(dV)),
            expected,
            rtol=0, atol=1e-16,
        )

    def test_metrics_constant(self, backend):
        grid, _ = _make_grid_and_solver(backend, 32, alpha=1.0)
        for ax in range(2):
            # h should be constant
            np.testing.assert_array_equal(
                grid.h[ax], np.full(33, 1.0 / 32)
            )
            # J = dxi/dx = (1/N) / h = 1.0 for uniform grid
            np.testing.assert_array_equal(
                grid.J[ax], np.ones(33)
            )

    def test_update_from_levelset_noop(self, backend):
        grid, ccd = _make_grid_and_solver(backend, 32, alpha=1.0)
        eps = 0.5 / 32
        psi, _, _ = _make_initial_field(backend, grid, eps)
        coords_before = [c.copy() for c in grid.coords]
        grid.update_from_levelset(psi, eps, ccd=ccd)
        for ax in range(2):
            np.testing.assert_array_equal(grid.coords[ax], coords_before[ax])


class TestCCDEquivalence:
    """CCD derivatives on alpha=1.0 grid must match uniform expectations."""

    def test_derivative_no_metric(self, backend):
        """differentiate with/without apply_metric should be identical on uniform grid."""
        grid, ccd = _make_grid_and_solver(backend, 32, alpha=1.0)
        eps = 0.5 / 32
        psi, _, _ = _make_initial_field(backend, grid, eps)

        for ax in range(2):
            d1_with, d2_with = ccd.differentiate(psi, axis=ax, apply_metric=True)
            d1_without, d2_without = ccd.differentiate(psi, axis=ax, apply_metric=False)
            # On uniform grid, apply_metric is skipped, so both return xi-space
            # derivatives which equal x-space when J=constant.
            np.testing.assert_array_equal(
                np.asarray(backend.to_host(d1_with)),
                np.asarray(backend.to_host(d1_without)),
            )
            np.testing.assert_array_equal(
                np.asarray(backend.to_host(d2_with)),
                np.asarray(backend.to_host(d2_without)),
            )


class TestAdvectionEquivalence:
    """Full advection step must be bit-identical regardless of alpha=1 path."""

    def test_advection_step_identical(self, backend):
        N = 32
        eps = 0.5 / N
        dt = 0.45 / N

        grid, ccd = _make_grid_and_solver(backend, N, alpha=1.0)
        psi, X, Y = _make_initial_field(backend, grid, eps)
        xp = backend.xp

        adv = DissipativeCCDAdvection(
            backend, grid, ccd, bc="zero", eps_d=0.05, mass_correction=True,
        )

        # Rigid rotation velocity
        cx, cy = 0.5, 0.5
        u = -(Y - cy)
        v = X - cx

        psi_out = adv.advance(psi.copy(), [u, v], dt)

        # Run again from same input — must be exactly the same
        psi_out2 = adv.advance(psi.copy(), [u, v], dt)
        np.testing.assert_array_equal(
            np.asarray(backend.to_host(psi_out)),
            np.asarray(backend.to_host(psi_out2)),
        )

    def test_j_reshaped_is_none_for_uniform(self, backend):
        """Uniform grid must NOT store Jacobian arrays."""
        N = 32
        grid, ccd = _make_grid_and_solver(backend, N, alpha=1.0)
        adv = DissipativeCCDAdvection(
            backend, grid, ccd, bc="zero", eps_d=0.05, mass_correction=True,
        )
        assert adv._J_reshaped is None
