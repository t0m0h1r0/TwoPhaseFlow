"""Tests for the backend-native FD PPE matrix builder."""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ppe.fd_ppe_matrix import FDPPEMatrix


def _build_matrix(n: int = 8):
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    return backend, grid, FDPPEMatrix(grid, backend, ccd)


def test_fd_ppe_matrix_vectorized_assembly_matches_legacy_host_loop():
    """The GPU-first vector assembly preserves the pre-existing FD operator."""
    _backend, grid, builder = _build_matrix(n=8)
    rng = np.random.default_rng(20260506)
    rho = 1.0 + rng.random(grid.shape)

    rows, cols, vals = builder._assemble(rho)
    rho_dev, drho_x, drho_y = builder._density_fields(rho)
    rows_ref, cols_ref, vals_ref = builder._assemble_host_legacy(
        np.asarray(rho_dev),
        np.asarray(drho_x),
        np.asarray(drho_y),
    )

    actual = csr_matrix(
        (vals, (rows, cols)),
        shape=(builder._n_dof, builder._n_dof),
    ).toarray()
    expected = csr_matrix(
        (vals_ref, (rows_ref, cols_ref)),
        shape=(builder._n_dof, builder._n_dof),
    ).toarray()

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=0.0)


def test_fd_ppe_matrix_factorize_and_helmholtz_filter_cpu():
    """Pinned FD PPE and Helmholtz factors remain usable on the CPU backend."""
    _backend, grid, builder = _build_matrix(n=8)
    rng = np.random.default_rng(20260507)
    rho = 1.0 + rng.random(grid.shape)
    rhs = rng.standard_normal(grid.shape).ravel()
    rhs[builder._pin_dof] = 0.0

    pressure = builder.factorize(rho).solve(rhs)
    filtered = builder.build_helmholtz_filter(
        rho,
        alpha=0.25 * builder._h**2,
    ).solve(pressure)

    assert np.isfinite(pressure).all()
    assert np.isfinite(filtered).all()
