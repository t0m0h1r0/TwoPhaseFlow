"""Closed-interface Riesz virtual-work diagnostics."""

from __future__ import annotations

import numpy as np

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.coupling.closed_interface_riesz import (
    _dense_divergence_matrix,
    _flatten_face_components,
    _unflatten_face_components,
    closed_interface_riesz_cochain,
    component_reaction_hodge_gate,
    face_measure_components,
    fixed_stratum_virtual_work_check,
    weighted_hodge_decomposition,
)
from twophase.simulation.divergence_ops import FCCDDivergenceOperator


def _setup(n=12):
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    return grid, backend, fccd, FCCDDivergenceOperator(fccd)


def _circle_psi(grid, *, radius=0.247):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - radius
    eps = 1.5 / grid.N[0]
    return 1.0 / (1.0 + np.exp(phi / eps))


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


def test_surface_riesz_matches_fixed_stratum_virtual_work():
    grid, backend, fccd, _ = _setup(12)
    xp = backend.xp
    psi = _ellipse_psi(grid)
    cochain = closed_interface_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=psi,
        fccd=fccd,
        sigma=0.072,
    )

    check = fixed_stratum_virtual_work_check(
        xp=xp,
        grid=grid,
        fccd=fccd,
        cochain=cochain,
        face_velocity_components=cochain.surface_acceleration,
        epsilon=1.0e-7,
    )

    assert check.valid, check.reason
    assert check.finite_difference_gradient_residual < 1.0e-6
    assert check.riesz_residual < 1.0e-12
    assert check.finite_difference_power_residual < 1.0e-6


def test_weighted_hodge_projection_leaves_divergence_free_residual():
    grid, backend, fccd, div_op = _setup(8)
    xp = backend.xp
    psi = _ellipse_psi(grid)
    cochain = closed_interface_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=psi,
        fccd=fccd,
        sigma=0.072,
    )

    decomposition = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=cochain.surface_acceleration,
        face_weight_components=cochain.face_weight_components,
    )

    assert decomposition.component_weighted_l2 > 0.0
    assert decomposition.hodge_weighted_l2 > 0.0
    assert decomposition.hodge_divergence_linf < 1.0e-9


def test_weighted_hodge_projection_recovers_manufactured_pressure_range():
    """Analytic finite-dimensional check: ``c=M_f^{-1}D_f^T p`` has no Hodge part."""
    grid, backend, _, div_op = _setup(16)
    xp = backend.xp
    weights = face_measure_components(xp=xp, grid=grid)
    D, shapes, sizes = _dense_divergence_matrix(
        xp=xp,
        div_op=div_op,
        face_templates=weights,
    )
    weight_flat = _flatten_face_components(xp, weights)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    potential = (
        np.sin(2.0 * np.pi * X) * np.cos(3.0 * np.pi * Y)
        + 0.31 * np.cos(np.pi * X + 0.2) * np.sin(2.0 * np.pi * Y + 0.1)
    )
    range_flat = (D.T @ potential.ravel()) / weight_flat
    range_components = _unflatten_face_components(xp, range_flat, shapes, sizes)

    decomposition = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=range_components,
        face_weight_components=weights,
    )
    hodge_flat = _flatten_face_components(xp, decomposition.hodge_components)
    recovered_flat = _flatten_face_components(xp, decomposition.range_components)
    source_linf = max(float(np.max(np.abs(D @ range_flat))), 1.0)

    assert np.sqrt(float(np.sum(hodge_flat * hodge_flat * weight_flat))) < 1.0e-10
    np.testing.assert_allclose(recovered_flat, range_flat, rtol=1.0e-10, atol=1.0e-10)
    assert decomposition.hodge_divergence_linf < 1.0e-9
    assert decomposition.hodge_divergence_linf / source_linf < 1.0e-12


def test_component_reaction_gate_reveals_circle_is_not_static_for_this_transport():
    grid, backend, fccd, div_op = _setup(12)
    xp = backend.xp
    cochain = closed_interface_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=_circle_psi(grid),
        fccd=fccd,
        sigma=0.072,
    )

    gate = component_reaction_hodge_gate(
        xp=xp,
        div_op=div_op,
        cochain=cochain,
    )

    assert gate.surface_hodge_weighted_l2 > 5.0e-2
    assert gate.residual_weighted_l2 > 1.0e-2
    assert gate.residual_ratio > 1.0e-1
    assert gate.residual_divergence_linf < 1.0e-8


def test_ellipse_has_nonzero_surface_hodge_drive_under_same_gate():
    grid, backend, fccd, div_op = _setup(12)
    xp = backend.xp
    cochain = closed_interface_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=_ellipse_psi(grid),
        fccd=fccd,
        sigma=0.072,
    )

    gate = component_reaction_hodge_gate(
        xp=xp,
        div_op=div_op,
        cochain=cochain,
    )

    assert gate.surface_hodge_weighted_l2 > 1.0e-1
    assert gate.residual_weighted_l2 > 1.0e-2
    assert gate.residual_divergence_linf < 1.0e-8
