"""Trace-vertex Riesz capillary tests."""

from __future__ import annotations

import numpy as np

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.coupling.closed_interface_trace import (
    build_trace_graph_2d,
    trace_component_area_vertex_covectors,
    trace_component_areas,
    trace_graph_surface_length,
    trace_surface_vertex_covectors,
)
from twophase.coupling.closed_interface_trace_riesz import (
    closed_interface_trace_riesz_cochain,
    trace_component_hodge_projection,
    trace_hodge_weighted_l2,
    trace_riesz_work_check,
)
from twophase.coupling.closed_interface_trace_velocity import (
    ReconstructedNodalP1TraceVelocityMap,
    face_vertex_vjp_residual,
)
from twophase.simulation.divergence_ops import FCCDDivergenceOperator


def _setup(n=12):
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    return grid, backend, fccd, FCCDDivergenceOperator(fccd)


def _ellipse_psi(grid, *, a=0.275, b=0.225):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi = np.sqrt(((X - 0.5) / a) ** 2 + ((Y - 0.5) / b) ** 2) - 1.0
    eps = 1.5 / grid.N[0] / 0.25
    return 1.0 / (1.0 + np.exp(phi / eps))


def _smooth_face_velocity(grid, fccd):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    x_faces = 0.5 * (x[:-1] + x[1:])
    y_faces = 0.5 * (y[:-1] + y[1:])
    X0, Y0 = np.meshgrid(x_faces, y, indexing="ij")
    X1, Y1 = np.meshgrid(x, y_faces, indexing="ij")
    return [
        fccd.xp.asarray(np.sin(2.0 * np.pi * X0) * np.cos(np.pi * Y0)),
        fccd.xp.asarray(-0.5 * np.cos(np.pi * X1) * np.sin(2.0 * np.pi * Y1)),
    ]


def test_trace_graph_builds_closed_components():
    grid, backend, _, _ = _setup(16)
    graph = build_trace_graph_2d(
        xp=backend.xp,
        grid=grid,
        psi=_ellipse_psi(grid),
    )

    assert graph.vertices
    assert graph.segments
    assert len(graph.components) == 1
    assert trace_graph_surface_length(graph) > 0.0
    assert trace_component_areas(graph)[0] > 0.0


def test_trace_vertex_covectors_are_translation_neutral():
    grid, backend, _, _ = _setup(16)
    graph = build_trace_graph_2d(
        xp=backend.xp,
        grid=grid,
        psi=_ellipse_psi(grid),
    )
    surface = trace_surface_vertex_covectors(graph, sigma=0.072)
    volume = trace_component_area_vertex_covectors(graph)[0]

    surface_sum = np.sum(list(surface.values()), axis=0)
    volume_sum = np.sum(list(volume.values()), axis=0)
    np.testing.assert_allclose(surface_sum, 0.0, atol=1.0e-14)
    np.testing.assert_allclose(volume_sum, 0.0, atol=1.0e-14)


def test_trace_velocity_vjp_matches_dot_product():
    grid, backend, fccd, _ = _setup(12)
    xp = backend.xp
    graph = build_trace_graph_2d(xp=xp, grid=grid, psi=_ellipse_psi(grid))
    trace_map = ReconstructedNodalP1TraceVelocityMap(grid=grid, bc_type="periodic")
    rng = np.random.default_rng(12)
    covectors = {
        vertex.index: rng.normal(size=2)
        for vertex in graph.vertices
    }

    residual = face_vertex_vjp_residual(
        xp=xp,
        graph=graph,
        trace_velocity_map=trace_map,
        face_components=_smooth_face_velocity(grid, fccd),
        vertex_covectors=covectors,
    )

    assert residual < 1.0e-14


def test_trace_riesz_work_identities_hold():
    grid, backend, fccd, _ = _setup(12)
    xp = backend.xp
    cochain = closed_interface_trace_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=_ellipse_psi(grid),
        sigma=0.072,
        bc_type="periodic",
    )

    check = trace_riesz_work_check(
        xp=xp,
        cochain=cochain,
        face_velocity_components=cochain.surface_acceleration,
    )

    assert check.surface_riesz_residual < 1.0e-14
    assert abs(check.surface_gradient_action) > 1.0e-12


def test_trace_component_hodge_projection_is_divergence_free():
    grid, backend, _, div_op = _setup(10)
    xp = backend.xp
    cochain = closed_interface_trace_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=_ellipse_psi(grid),
        sigma=0.072,
        bc_type="periodic",
    )

    projection = trace_component_hodge_projection(
        xp=xp,
        div_op=div_op,
        cochain=cochain,
    )
    residual_norm = trace_hodge_weighted_l2(xp=xp, projection=projection)

    assert residual_norm > 0.0
    div = div_op.divergence_from_faces(projection.hodge_residual_components)
    assert float(np.max(np.abs(div))) < 1.0e-8
