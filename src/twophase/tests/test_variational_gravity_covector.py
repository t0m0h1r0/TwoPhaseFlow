"""Variational gravity covector checks."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.simulation.face_boundary import zero_wall_normal_face_components
from twophase.simulation.gravity_covector import build_variational_gravity_faces


def _setup(nx=7, ny=8, *, bc_type="wall"):
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(nx, ny), L=(1.0, 1.4)), backend)
    ccd = CCDSolver(grid, backend, bc_type=bc_type)
    fccd = FCCDSolver(grid, backend, bc_type=bc_type, ccd_solver=ccd)
    return grid, backend, fccd


def _node_fields(grid):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    return np.meshgrid(x, y, indexing="ij")


def test_variational_gravity_covector_matches_common_flux_mass_virtual_work():
    grid, backend, fccd = _setup()
    xp = backend.xp
    X, Y = _node_fields(grid)
    rho = 1.1 + 0.07 * np.sin(2.0 * np.pi * X) + 0.03 * np.cos(np.pi * Y)
    gravity = build_variational_gravity_faces(
        xp=xp,
        fccd=fccd,
        rho=xp.asarray(rho),
        vertical_coordinate=xp.asarray(Y),
        g_acc=9.81,
        gravity_axis=1,
    )

    virtual_faces = []
    density_increment = xp.zeros_like(gravity.nodal_covector)
    for axis, face_density in enumerate(gravity.face_density_components):
        face_index = np.arange(face_density.size, dtype=float).reshape(face_density.shape)
        virtual_face = xp.asarray(
            0.13 * np.sin(0.17 * face_index) - 0.08 * np.cos(0.29 * face_index)
        )
        virtual_faces.append(virtual_face)
        density_increment = density_increment - fccd.face_divergence(
            face_density * virtual_face,
            axis=axis,
        )

    face_work = sum(
        xp.sum(covector * virtual_face)
        for covector, virtual_face in zip(
            gravity.covector_components,
            virtual_faces,
        )
    )
    potential_work = xp.sum(gravity.nodal_covector * density_increment)
    assert float(face_work + potential_work) == pytest.approx(
        0.0,
        rel=1.0e-12,
        abs=1.0e-12,
    )


def test_variational_gravity_rejects_periodic_gravity_axis():
    grid, backend, fccd = _setup(bc_type="periodic")
    xp = backend.xp
    _, Y = _node_fields(grid)

    with pytest.raises(ValueError, match="non-periodic gravity axis"):
        build_variational_gravity_faces(
            xp=xp,
            fccd=fccd,
            rho=xp.ones(grid.shape),
            vertical_coordinate=xp.asarray(Y),
            g_acc=9.81,
            gravity_axis=1,
        )


def test_constrained_single_phase_variational_gravity_is_vertical_hydrostatic():
    grid, backend, fccd = _setup()
    xp = backend.xp
    _, Y = _node_fields(grid)
    gravity = build_variational_gravity_faces(
        xp=xp,
        fccd=fccd,
        rho=xp.ones(grid.shape),
        vertical_coordinate=xp.asarray(Y),
        g_acc=9.81,
        gravity_axis=1,
    )

    constrained = zero_wall_normal_face_components(
        gravity.acceleration_components,
        xp=xp,
        bc_type="wall",
    )
    assert float(np.max(np.abs(constrained[0]))) == pytest.approx(0.0)
    assert np.allclose(np.asarray(constrained[1])[:, 1:-1], -9.81)
    assert float(np.max(np.abs(np.asarray(constrained[1])[:, [0, -1]]))) == (
        pytest.approx(0.0)
    )
