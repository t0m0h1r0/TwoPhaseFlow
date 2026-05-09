"""Boundary-constrained face Hodge tests."""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from twophase.backend import Backend
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.simulation.boundary_hodge import (
    project_wall_trace,
    wall_trace_adjoint,
    wall_trace_from_faces,
)


def _grid(nx=6, ny=5, *, bc_type="wall"):
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(nx, ny), L=(1.0, 1.2))
    )
    grid = Grid(cfg.grid, backend)
    return backend, grid, FCCDSolver(grid, backend, bc_type=bc_type)


def _random_faces(rng, grid):
    faces = []
    for axis in range(grid.ndim):
        shape = list(grid.shape)
        shape[axis] = grid.N[axis]
        faces.append(rng.normal(size=tuple(shape)))
    return faces


def _rho(grid):
    x = np.asarray(grid.coords[0])[:, None]
    y = np.asarray(grid.coords[1])[None, :]
    return 2.0 + 0.1 * np.sin(2.0 * np.pi * x) * np.cos(np.pi * y / grid.L[1])


def test_wall_trace_adjoint_matches_reconstruction_trace():
    backend, grid, _fccd = _grid()
    rng = np.random.default_rng(10)
    faces = _random_faces(rng, grid)
    trace = wall_trace_from_faces(backend.xp, grid, faces, "wall")
    trace_covector = rng.normal(size=trace.shape)

    adjoint = wall_trace_adjoint(backend.xp, grid, trace_covector, "wall")
    left = float(np.vdot(trace_covector, trace).real)
    right = sum(float(np.vdot(face, adj).real) for face, adj in zip(faces, adjoint))

    assert abs(left - right) < 1.0e-12


def test_periodic_wall_trace_adjoint_uses_unique_periodic_images():
    backend, grid, _fccd = _grid(bc_type="periodic_wall")
    rng = np.random.default_rng(11)
    faces = _random_faces(rng, grid)
    trace = wall_trace_from_faces(backend.xp, grid, faces, "periodic_wall")
    trace_covector = rng.normal(size=trace.shape)

    adjoint = wall_trace_adjoint(backend.xp, grid, trace_covector, "periodic_wall")
    left = float(np.vdot(trace_covector, trace).real)
    right = sum(float(np.vdot(face, adj).real) for face, adj in zip(faces, adjoint))

    assert abs(left - right) < 1.0e-12


def test_wall_trace_projection_removes_no_slip_reconstruction_trace():
    backend, grid, fccd = _grid(nx=7, ny=6)
    rng = np.random.default_rng(12)
    faces = _random_faces(rng, grid)

    projection = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=faces,
        rho=_rho(grid),
        bc_type="wall",
        tolerance=1.0e-12,
        max_iterations=120,
    )

    trace = wall_trace_from_faces(
        backend.xp,
        grid,
        projection.face_components,
        "wall",
    )
    assert float(np.max(np.abs(trace))) < 1.0e-10
    assert projection.diagnostics["boundary_hodge_cg_converged"] == 1.0
