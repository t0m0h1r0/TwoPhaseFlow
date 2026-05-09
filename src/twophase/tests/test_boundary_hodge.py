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
    face_mass_inner_product,
    project_wall_trace,
    restricted_pressure_fluxes,
    wall_trace_adjoint,
    wall_trace_from_faces,
)
from twophase.simulation.divergence_ops import FCCDDivergenceOperator


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


def _vec(faces):
    return np.concatenate([np.asarray(face).ravel() for face in faces])


def _unvec(values, grid):
    faces = []
    offset = 0
    for axis in range(grid.ndim):
        shape = list(grid.shape)
        shape[axis] = grid.N[axis]
        size = int(np.prod(shape))
        faces.append(values[offset : offset + size].reshape(tuple(shape)))
        offset += size
    return faces


def _assemble_face_matrix(grid, apply_column):
    face_size = sum(
        int(np.prod(tuple(grid.N[axis] if i == axis else grid.shape[i] for i in range(grid.ndim))))
        for axis in range(grid.ndim)
    )
    columns = []
    for index in range(face_size):
        basis = np.zeros(face_size)
        basis[index] = 1.0
        columns.append(apply_column(_unvec(basis, grid)))
    return np.column_stack(columns)


def _node_widths(grid):
    widths = []
    for axis in range(grid.ndim):
        coords = np.asarray(grid.coords[axis], dtype=float)
        d_face = coords[1:] - coords[:-1]
        width = np.empty_like(coords)
        width[0] = 0.5 * d_face[0]
        width[-1] = 0.5 * d_face[-1]
        width[1:-1] = 0.5 * (coords[2:] - coords[:-2])
        widths.append(width)
    return widths


def _nodal_volume(grid):
    wx, wy = _node_widths(grid)
    return wx[:, None] * wy[None, :]


def _pressure_inner(grid, pressure, divergence):
    return float(np.vdot(pressure, _nodal_volume(grid) * divergence).real)


def _pressure_kwargs():
    return {
        "pressure_gradient": "fccd",
        "pressure_force_contract": "variational_adjoint",
        "coefficient_scheme": "phase_density",
        "interface_coupling_scheme": "none",
    }


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


def test_wall_retraction_is_idempotent_and_metric_self_adjoint():
    backend, grid, fccd = _grid(nx=7, ny=6)
    rng = np.random.default_rng(13)
    rho = _rho(grid)
    faces_a = _random_faces(rng, grid)
    faces_b = _random_faces(rng, grid)

    projection_a = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=faces_a,
        rho=rho,
        bc_type="wall",
        tolerance=1.0e-12,
        max_iterations=160,
    )
    projection_aa = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=projection_a.face_components,
        rho=rho,
        bc_type="wall",
        tolerance=1.0e-12,
        max_iterations=160,
    )
    assert np.linalg.norm(_vec(projection_aa.face_components) - _vec(projection_a.face_components)) < 1.0e-10

    projection_b = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=faces_b,
        rho=rho,
        bc_type="wall",
        tolerance=1.0e-12,
        max_iterations=160,
    )
    left = face_mass_inner_product(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        rho=rho,
        left_components=projection_a.face_components,
        right_components=faces_b,
    )
    right = face_mass_inner_product(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        rho=rho,
        left_components=faces_a,
        right_components=projection_b.face_components,
    )
    assert abs(float(left) - float(right)) < 1.0e-9


def test_restricted_pressure_fluxes_project_pressure_reaction_into_wall_space():
    backend, grid, fccd = _grid(nx=7, ny=6)
    div_op = FCCDDivergenceOperator(fccd)
    rng = np.random.default_rng(14)
    pressure = rng.normal(size=grid.shape)
    rho = _rho(grid)
    kwargs = _pressure_kwargs()
    raw_faces = div_op.pressure_fluxes(pressure, rho, **kwargs)
    raw_trace = wall_trace_from_faces(backend.xp, grid, raw_faces, "wall")

    restricted = restricted_pressure_fluxes(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=div_op,
        pressure=pressure,
        rho=rho,
        bc_type="wall",
        pressure_flux_kwargs=kwargs,
        tolerance=1.0e-12,
        max_iterations=160,
    )

    trace = wall_trace_from_faces(
        backend.xp,
        grid,
        restricted.face_components,
        "wall",
    )
    assert float(np.max(np.abs(raw_trace))) > 1.0e-8
    assert float(np.max(np.abs(trace))) < 1.0e-10
    assert restricted.diagnostics["constrained_face_space_pressure_cg_converged"] == 1.0


def test_restricted_pressure_green_identity_on_full_wall_space():
    backend, grid, fccd = _grid(nx=7, ny=6)
    div_op = FCCDDivergenceOperator(fccd)
    rng = np.random.default_rng(15)
    pressure = rng.normal(size=grid.shape)
    rho = np.ones(grid.shape)
    eta = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=_random_faces(rng, grid),
        rho=rho,
        bc_type="wall",
        tolerance=1.0e-12,
        max_iterations=180,
    ).face_components
    restricted = restricted_pressure_fluxes(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=div_op,
        pressure=pressure,
        rho=rho,
        bc_type="wall",
        pressure_flux_kwargs=_pressure_kwargs(),
        tolerance=1.0e-12,
        max_iterations=180,
    )

    lhs = float(
        face_mass_inner_product(
            xp=backend.xp,
            grid=grid,
            fccd=fccd,
            rho=rho,
            left_components=restricted.face_components,
            right_components=eta,
        )
    )
    rhs = _pressure_inner(grid, pressure, div_op.divergence_from_faces(eta))
    scale = abs(lhs) + abs(rhs) + 1.0e-300
    assert abs(lhs + rhs) / scale < 1.0e-10


def test_restricted_pressure_rank_gate_passes_full_wall_topology():
    backend, grid, fccd = _grid(nx=6, ny=5)
    div_op = FCCDDivergenceOperator(fccd)
    rho = np.ones(grid.shape)
    pressure_kwargs = _pressure_kwargs()

    d_mat = _assemble_face_matrix(
        grid,
        lambda faces: np.asarray(div_op.divergence_from_faces(faces)).ravel(),
    )
    p_w = _assemble_face_matrix(
        grid,
        lambda faces: _vec(
            project_wall_trace(
                xp=backend.xp,
                grid=grid,
                fccd=fccd,
                face_components=faces,
                rho=rho,
                bc_type="wall",
                tolerance=1.0e-12,
                max_iterations=180,
            ).face_components
        ),
    )
    pressure_columns = []
    for index in range(int(np.prod(grid.shape))):
        pressure = np.zeros(grid.shape)
        pressure.ravel()[index] = 1.0
        pressure_columns.append(
            _vec(div_op.pressure_fluxes(pressure, rho, **pressure_kwargs))
        )
    g_mat = np.column_stack(pressure_columns)

    rank_restricted_divergence = np.linalg.matrix_rank(d_mat @ p_w, tol=1.0e-10)
    rank_restricted_pressure = np.linalg.matrix_rank(d_mat @ p_w @ g_mat, tol=1.0e-10)
    assert rank_restricted_pressure == rank_restricted_divergence


def test_restricted_pressure_manufactured_projection_recovers_kw_state():
    backend, grid, fccd = _grid(nx=6, ny=5)
    div_op = FCCDDivergenceOperator(fccd)
    rho = np.ones(grid.shape)
    rng = np.random.default_rng(16)

    d_mat = _assemble_face_matrix(
        grid,
        lambda faces: np.asarray(div_op.divergence_from_faces(faces)).ravel(),
    )
    p_w = _assemble_face_matrix(
        grid,
        lambda faces: _vec(
            project_wall_trace(
                xp=backend.xp,
                grid=grid,
                fccd=fccd,
                face_components=faces,
                rho=rho,
                bc_type="wall",
                tolerance=1.0e-12,
                max_iterations=180,
            ).face_components
        ),
    )
    pressure_columns = []
    for index in range(int(np.prod(grid.shape))):
        pressure = np.zeros(grid.shape)
        pressure.ravel()[index] = 1.0
        pressure_columns.append(
            _vec(div_op.pressure_fluxes(pressure, rho, **_pressure_kwargs()))
        )
    g_mat = np.column_stack(pressure_columns)
    restricted_operator = d_mat @ p_w @ g_mat

    _u, _s, vt = np.linalg.svd(d_mat @ p_w, full_matrices=True)
    rank = np.linalg.matrix_rank(d_mat @ p_w, tol=1.0e-10)
    null_basis = vt[rank:].T
    h = p_w @ (null_basis @ rng.normal(size=null_basis.shape[1]))
    p0 = rng.normal(size=g_mat.shape[1])
    f_dag = h + p_w @ g_mat @ p0

    p_hat, *_ = np.linalg.lstsq(restricted_operator, d_mat @ f_dag, rcond=None)
    f_new = p_w @ f_dag - p_w @ g_mat @ p_hat
    relative_error = np.linalg.norm(f_new - h) / max(np.linalg.norm(h), 1.0e-300)
    wall_trace = wall_trace_from_faces(backend.xp, grid, _unvec(f_new, grid), "wall")

    assert relative_error < 1.0e-10
    assert np.linalg.norm(d_mat @ f_new) < 1.0e-10
    assert float(np.max(np.abs(wall_trace))) < 1.0e-10
