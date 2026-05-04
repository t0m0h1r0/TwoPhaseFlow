"""Tests for the generic interface-stress closure.

A3 chain:
    CHK-RA-CH14-006/007
      -> affine jump condition G_Γ(p;j)=G(p)-B_Γj
      -> `InterfaceStressContext`
      -> two-cell manufactured jump tests
"""

from __future__ import annotations

import numpy as np

from twophase.backend import Backend
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ppe.fccd_matrixfree import PPESolverFCCDMatrixFree
from twophase.simulation.divergence_ops import FCCDDivergenceOperator
from twophase.coupling.capillary_geometry import apply_wall_compatible_curvature
from twophase.coupling.face_geometry_curvature import implicit_face_curvatures_2d
from twophase.coupling.interface_stress_closure import (
    build_interface_stress_context,
    build_young_laplace_interface_stress_context,
    evaluate_interface_face_curvature_lg,
    signed_pressure_jump_gradient,
)
from twophase.coupling.transport_variational_capillary import (
    marching_squares_surface_energy_gradient_2d,
    p2_trace_surface_energy_ale_discrete_gradient_2d,
    p2_trace_surface_energy_discrete_gradient_2d,
    p2_trace_surface_energy_2d,
    p2_trace_surface_energy_gradient_2d,
    p2_trace_surface_energy_hessian_product_2d,
)


def _make_two_cell_operator():
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(2, 2), L=(2.0, 2.0)),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)
    return grid, FCCDDivergenceOperator(fccd)


def test_signed_pressure_jump_gradient_orientation():
    """Liquid-to-gas and gas-to-liquid faces must have opposite signs."""
    grid, _ = _make_two_cell_operator()
    psi = np.ones(grid.shape)
    psi[1:, :] = 0.0
    kappa = np.full(grid.shape, 2.0)
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        kappa=kappa,
        sigma=3.0,
    )

    jump_x = signed_pressure_jump_gradient(
        xp=np,
        grid=grid,
        context=context,
        axis=0,
    )

    np.testing.assert_allclose(jump_x[0, :], -6.0)
    np.testing.assert_allclose(jump_x[1, :], 0.0)

    reversed_context = build_interface_stress_context(
        xp=np,
        psi=1.0 - psi,
        kappa=kappa,
        sigma=3.0,
    )
    reversed_jump_x = signed_pressure_jump_gradient(
        xp=np,
        grid=grid,
        context=reversed_context,
        axis=0,
    )
    np.testing.assert_allclose(reversed_jump_x[0, :], 6.0)
    np.testing.assert_allclose(reversed_jump_x[1, :], 0.0)


def test_transport_variational_jump_is_transport_adjoint_work():
    """Variational route must match the actual FCCD face-transport work."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(16, 16), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    x, y = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    phi = ((x - 0.52) / 0.24) ** 2 + ((y - 0.47) / 0.19) ** 2 - 1.0
    psi = 1.0 / (1.0 + np.exp(phi / 0.04))
    sigma = 0.072
    surface_gradient = marching_squares_surface_energy_gradient_2d(
        xp=np,
        grid=grid,
        psi=psi,
        sigma=sigma,
    )
    transport_rhs = np.zeros_like(psi)
    jump_power = 0.0
    context = build_young_laplace_interface_stress_context(
        xp=np,
        psi=psi,
        kappa_lg=np.zeros_like(psi),
        sigma=sigma,
        face_curvature_method="transport_variational",
    )
    for axis in range(grid.ndim):
        face_value = fccd.face_value(psi, axis)
        face_velocity = 0.01 * np.ones_like(face_value)
        if axis == 1:
            face_velocity = -0.015 * np.ones_like(face_value)
        transport_rhs -= fccd.face_divergence(face_value * face_velocity, axis)
        jump_gradient = signed_pressure_jump_gradient(
            xp=np,
            grid=grid,
            context=context,
            axis=axis,
            fccd=fccd,
        )
        d_face = grid.coords[axis][1:] - grid.coords[axis][:-1]
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        face_area = grid.h[1 - axis]
        area_shape = [1] * grid.ndim
        area_shape[1 - axis] = -1
        jump_power += np.sum(
            face_velocity
            * jump_gradient
            * d_face.reshape(d_shape)
            * face_area.reshape(area_shape)
        )

    surface_rate = np.sum(surface_gradient * transport_rhs)
    np.testing.assert_allclose(jump_power, -surface_rate, rtol=1.0e-12, atol=1.0e-14)


def test_transport_variational_p2_gradient_matches_discrete_energy_derivative():
    """P2 variational gradient must be the derivative of the P2 trace energy."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)), backend)
    x_coord, y_coord = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    phi = ((x_coord - 0.51) / 0.25) ** 2 + ((y_coord - 0.48) / 0.18) ** 2 - 1.0
    psi = 1.0 / (1.0 + np.exp(phi / 0.035))
    direction = np.sin(2.0 * np.pi * x_coord) * np.cos(2.0 * np.pi * y_coord)
    sigma = 0.072

    gradient = p2_trace_surface_energy_gradient_2d(
        xp=np,
        grid=grid,
        psi=psi,
        sigma=sigma,
    )
    step = (
        np.sqrt(np.finfo(psi.dtype).eps)
        * (1.0 + np.linalg.norm(psi))
        / (1.0 + np.linalg.norm(direction))
    )
    energy_plus = p2_trace_surface_energy_2d(
        xp=np,
        grid=grid,
        psi=psi + step * direction,
        sigma=sigma,
    )
    energy_minus = p2_trace_surface_energy_2d(
        xp=np,
        grid=grid,
        psi=psi - step * direction,
        sigma=sigma,
    )

    finite_difference = (energy_plus - energy_minus) / (2.0 * step)
    directional_derivative = np.sum(gradient * direction)
    np.testing.assert_allclose(
        directional_derivative,
        finite_difference,
        rtol=2.0e-5,
        atol=1.0e-8,
    )


def test_transport_variational_p2_discrete_gradient_matches_energy_delta():
    """Discrete-gradient route must satisfy the finite-step chain rule."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)), backend)
    x_coord, y_coord = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    phi_previous = (
        ((x_coord - 0.51) / 0.25) ** 2
        + ((y_coord - 0.48) / 0.18) ** 2
        - 1.0
    )
    phi_current = (
        ((x_coord - 0.512) / 0.247) ** 2
        + ((y_coord - 0.481) / 0.183) ** 2
        - 1.0
    )
    psi_previous = 1.0 / (1.0 + np.exp(phi_previous / 0.035))
    psi_current = 1.0 / (1.0 + np.exp(phi_current / 0.035))
    sigma = 0.072

    discrete_gradient = p2_trace_surface_energy_discrete_gradient_2d(
        xp=np,
        grid=grid,
        psi_previous=psi_previous,
        psi=psi_current,
        sigma=sigma,
    )
    energy_delta = p2_trace_surface_energy_2d(
        xp=np,
        grid=grid,
        psi=psi_current,
        sigma=sigma,
    ) - p2_trace_surface_energy_2d(
        xp=np,
        grid=grid,
        psi=psi_previous,
        sigma=sigma,
    )

    np.testing.assert_allclose(
        np.sum(discrete_gradient * (psi_current - psi_previous)),
        energy_delta,
        rtol=1.0e-12,
        atol=1.0e-14,
    )


def test_transport_variational_p2_ale_discrete_gradient_matches_energy_delta():
    """Reduced-ALE discrete gradient must close cross-grid surface energy."""
    backend = Backend(use_gpu=False)
    previous_grid = Grid(GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)), backend)
    current_grid = Grid(GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)), backend)
    base = np.linspace(0.0, 1.0, 25)
    current_grid.coords[0] = base + 0.01 * np.sin(np.pi * base)
    current_grid.coords[1] = base + 0.008 * np.sin(np.pi * base)
    x_coord, y_coord = np.meshgrid(current_grid.coords[0], current_grid.coords[1], indexing="ij")
    x_old, y_old = np.meshgrid(previous_grid.coords[0], previous_grid.coords[1], indexing="ij")
    phi_previous = (
        ((x_old - 0.51) / 0.25) ** 2
        + ((y_old - 0.48) / 0.18) ** 2
        - 1.0
    )
    phi_remapped = (
        ((x_coord - 0.511) / 0.249) ** 2
        + ((y_coord - 0.4805) / 0.181) ** 2
        - 1.0
    )
    phi_current = (
        ((x_coord - 0.512) / 0.247) ** 2
        + ((y_coord - 0.481) / 0.183) ** 2
        - 1.0
    )
    psi_previous_old = 1.0 / (1.0 + np.exp(phi_previous / 0.035))
    psi_previous_remapped = 1.0 / (1.0 + np.exp(phi_remapped / 0.035))
    psi_current = 1.0 / (1.0 + np.exp(phi_current / 0.035))
    sigma = 0.072
    previous_energy = p2_trace_surface_energy_2d(
        xp=np,
        grid=previous_grid,
        psi=psi_previous_old,
        sigma=sigma,
    )

    discrete_gradient = p2_trace_surface_energy_ale_discrete_gradient_2d(
        xp=np,
        grid=current_grid,
        psi_previous=psi_previous_remapped,
        psi=psi_current,
        sigma=sigma,
        previous_surface_energy=previous_energy,
    )
    energy_delta = p2_trace_surface_energy_2d(
        xp=np,
        grid=current_grid,
        psi=psi_current,
        sigma=sigma,
    ) - previous_energy

    np.testing.assert_allclose(
        np.sum(discrete_gradient * (psi_current - psi_previous_remapped)),
        energy_delta,
        rtol=1.0e-12,
        atol=1.0e-14,
    )


def test_transport_variational_p2_jump_is_transport_adjoint_work():
    """P2 jump route must preserve exact discrete transport work adjointness."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(16, 16), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    x_coord, y_coord = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    phi = ((x_coord - 0.52) / 0.24) ** 2 + ((y_coord - 0.47) / 0.19) ** 2 - 1.0
    psi = 1.0 / (1.0 + np.exp(phi / 0.04))
    sigma = 0.072
    surface_gradient = p2_trace_surface_energy_gradient_2d(
        xp=np,
        grid=grid,
        psi=psi,
        sigma=sigma,
    )
    transport_rhs = np.zeros_like(psi)
    jump_power = 0.0
    context = build_young_laplace_interface_stress_context(
        xp=np,
        psi=psi,
        kappa_lg=np.zeros_like(psi),
        sigma=sigma,
        face_curvature_method="transport_variational_p2",
    )
    for axis in range(grid.ndim):
        face_value = fccd.face_value(psi, axis)
        face_velocity = 0.01 * np.ones_like(face_value)
        if axis == 1:
            face_velocity = -0.015 * np.ones_like(face_value)
        transport_rhs -= fccd.face_divergence(face_value * face_velocity, axis)
        jump_gradient = signed_pressure_jump_gradient(
            xp=np,
            grid=grid,
            context=context,
            axis=axis,
            fccd=fccd,
        )
        d_face = grid.coords[axis][1:] - grid.coords[axis][:-1]
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        face_area = grid.h[1 - axis]
        area_shape = [1] * grid.ndim
        area_shape[1 - axis] = -1
        jump_power += np.sum(
            face_velocity
            * jump_gradient
            * d_face.reshape(d_shape)
            * face_area.reshape(area_shape)
        )

    surface_rate = np.sum(surface_gradient * transport_rhs)
    np.testing.assert_allclose(jump_power, -surface_rate, rtol=1.0e-12, atol=1.0e-14)


def test_transport_variational_p2_discrete_gradient_jump_is_adjoint_work():
    """Discrete-gradient jump must be adjoint to midpoint face transport."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(16, 16), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    x_coord, y_coord = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    phi_previous = (
        ((x_coord - 0.52) / 0.24) ** 2
        + ((y_coord - 0.47) / 0.19) ** 2
        - 1.0
    )
    phi_current = (
        ((x_coord - 0.522) / 0.237) ** 2
        + ((y_coord - 0.471) / 0.193) ** 2
        - 1.0
    )
    psi_previous = 1.0 / (1.0 + np.exp(phi_previous / 0.04))
    psi_current = 1.0 / (1.0 + np.exp(phi_current / 0.04))
    psi_midpoint = 0.5 * (psi_previous + psi_current)
    sigma = 0.072
    surface_gradient = p2_trace_surface_energy_discrete_gradient_2d(
        xp=np,
        grid=grid,
        psi_previous=psi_previous,
        psi=psi_current,
        sigma=sigma,
    )
    transport_rhs = np.zeros_like(psi_current)
    jump_power = 0.0
    context = build_young_laplace_interface_stress_context(
        xp=np,
        psi=psi_current,
        psi_previous=psi_previous,
        kappa_lg=np.zeros_like(psi_current),
        sigma=sigma,
        face_curvature_method="transport_variational_p2_discrete_gradient",
    )
    for axis in range(grid.ndim):
        face_value = fccd.face_value(psi_midpoint, axis)
        face_velocity = 0.01 * np.ones_like(face_value)
        if axis == 1:
            face_velocity = -0.015 * np.ones_like(face_value)
        transport_rhs -= fccd.face_divergence(face_value * face_velocity, axis)
        jump_gradient = signed_pressure_jump_gradient(
            xp=np,
            grid=grid,
            context=context,
            axis=axis,
            fccd=fccd,
        )
        d_face = grid.coords[axis][1:] - grid.coords[axis][:-1]
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        face_area = grid.h[1 - axis]
        area_shape = [1] * grid.ndim
        area_shape[1 - axis] = -1
        jump_power += np.sum(
            face_velocity
            * jump_gradient
            * d_face.reshape(d_shape)
            * face_area.reshape(area_shape)
        )

    surface_rate = np.sum(surface_gradient * transport_rhs)
    np.testing.assert_allclose(jump_power, -surface_rate, rtol=1.0e-12, atol=1.0e-14)


def test_transport_variational_p2_ale_discrete_gradient_jump_is_adjoint_work():
    """Reduced-ALE discrete-gradient jump must use the same adjoint work."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(16, 16), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    x_coord, y_coord = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    phi_previous = (
        ((x_coord - 0.52) / 0.24) ** 2
        + ((y_coord - 0.47) / 0.19) ** 2
        - 1.0
    )
    phi_current = (
        ((x_coord - 0.522) / 0.237) ** 2
        + ((y_coord - 0.471) / 0.193) ** 2
        - 1.0
    )
    psi_previous = 1.0 / (1.0 + np.exp(phi_previous / 0.04))
    psi_current = 1.0 / (1.0 + np.exp(phi_current / 0.04))
    psi_midpoint = 0.5 * (psi_previous + psi_current)
    sigma = 0.072
    previous_energy = p2_trace_surface_energy_2d(
        xp=np,
        grid=grid,
        psi=psi_previous,
        sigma=sigma,
    ) - 0.01 * sigma
    surface_gradient = p2_trace_surface_energy_ale_discrete_gradient_2d(
        xp=np,
        grid=grid,
        psi_previous=psi_previous,
        psi=psi_current,
        sigma=sigma,
        previous_surface_energy=previous_energy,
    )
    transport_rhs = np.zeros_like(psi_current)
    jump_power = 0.0
    context = build_young_laplace_interface_stress_context(
        xp=np,
        psi=psi_current,
        psi_previous=psi_previous,
        kappa_lg=np.zeros_like(psi_current),
        sigma=sigma,
        face_curvature_method="transport_variational_p2_ale_discrete_gradient",
        transport_variational_previous_surface_energy=previous_energy,
    )
    for axis in range(grid.ndim):
        face_value = fccd.face_value(psi_midpoint, axis)
        face_velocity = 0.01 * np.ones_like(face_value)
        if axis == 1:
            face_velocity = -0.015 * np.ones_like(face_value)
        transport_rhs -= fccd.face_divergence(face_value * face_velocity, axis)
        jump_gradient = signed_pressure_jump_gradient(
            xp=np,
            grid=grid,
            context=context,
            axis=axis,
            fccd=fccd,
        )
        d_face = grid.coords[axis][1:] - grid.coords[axis][:-1]
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        face_area = grid.h[1 - axis]
        area_shape = [1] * grid.ndim
        area_shape[1 - axis] = -1
        jump_power += np.sum(
            face_velocity
            * jump_gradient
            * d_face.reshape(d_shape)
            * face_area.reshape(area_shape)
        )

    surface_rate = np.sum(surface_gradient * transport_rhs)
    np.testing.assert_allclose(jump_power, -surface_rate, rtol=1.0e-12, atol=1.0e-14)


def test_transport_variational_p2_hessian_product_is_symmetric():
    """Newton-Krylov P2 HVP must inherit Hessian self-adjointness."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(24, 24), L=(1.0, 1.0)), backend)
    x_coord, y_coord = np.meshgrid(grid.coords[0], grid.coords[1], indexing="ij")
    phi = ((x_coord - 0.51) / 0.25) ** 2 + ((y_coord - 0.48) / 0.18) ** 2 - 1.0
    psi = 1.0 / (1.0 + np.exp(phi / 0.035))
    direction_a = np.sin(2.0 * np.pi * x_coord) * np.cos(2.0 * np.pi * y_coord)
    direction_b = np.cos(3.0 * np.pi * x_coord) * np.sin(2.0 * np.pi * y_coord)
    sigma = 0.072

    hessian_a = p2_trace_surface_energy_hessian_product_2d(
        xp=np,
        grid=grid,
        psi=psi,
        direction=direction_a,
        sigma=sigma,
    )
    hessian_b = p2_trace_surface_energy_hessian_product_2d(
        xp=np,
        grid=grid,
        psi=psi,
        direction=direction_b,
        sigma=sigma,
    )

    np.testing.assert_allclose(
        np.sum(direction_a * hessian_b),
        np.sum(hessian_a * direction_b),
        rtol=2.0e-4,
        atol=2.0e-7,
    )


def test_signed_pressure_jump_gradient_uses_nonuniform_physical_face_distance():
    """Nonuniform affine jumps use local ``H_f``, not a global ``h``."""
    grid, _ = _make_two_cell_operator()
    grid.coords[0] = np.asarray([0.0, 0.25, 2.0])
    psi = np.ones(grid.shape)
    psi[1:, :] = 0.0
    kappa = np.full(grid.shape, 2.0)
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        kappa=kappa,
        sigma=3.0,
    )

    jump_x = signed_pressure_jump_gradient(
        xp=np,
        grid=grid,
        context=context,
        axis=0,
    )

    np.testing.assert_allclose(jump_x[0, :], -24.0)
    np.testing.assert_allclose(jump_x[1, :], 0.0)


def test_young_laplace_jump_uses_cut_face_curvature_quadrature():
    """Young--Laplace jumps sample ``κ_Γ`` at the ψ=1/2 cut face."""
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(1, 1), L=(1.0, 1.0)),
    )
    grid = Grid(cfg.grid, backend)
    psi = np.asarray([[0.9, 0.9], [0.4, 0.4]])
    kappa_lg = np.asarray([[0.0, 0.0], [10.0, 10.0]])
    context = build_young_laplace_interface_stress_context(
        xp=np,
        psi=psi,
        kappa_lg=kappa_lg,
        sigma=1.0,
    )

    jump_x = signed_pressure_jump_gradient(
        xp=np,
        grid=grid,
        context=context,
        axis=0,
    )

    np.testing.assert_allclose(jump_x[0, :], -8.0)


def test_face_implicit_curvature_matches_circle_on_cut_faces():
    """GPU-ready face curvature evaluates the implicit geometry at Γ_f."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    x, y = grid.meshgrid()
    radius = 0.25
    interface_width = 1.5 * min(float(grid.h[0][0]), float(grid.h[1][0]))
    distance = radius - np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2)
    psi = 1.0 / (1.0 + np.exp(-distance / interface_width))

    faces = implicit_face_curvatures_2d(xp=np, grid=grid, psi=psi, fccd=fccd)
    kappa_faces = np.concatenate([face[np.abs(face) > 0.0] for face in faces])

    assert abs(float(np.mean(kappa_faces)) - 1.0 / radius) < 0.12
    assert float(np.std(kappa_faces)) < 0.25


def test_face_implicit_curvature_matches_circle_family():
    """Compact cut-face curvature follows ``κ=1/R`` across radii/resolutions."""
    for cells, radius in ((32, 0.20), (64, 0.25), (96, 0.30)):
        backend = Backend(use_gpu=False)
        grid = Grid(GridConfig(ndim=2, N=(cells, cells), L=(1.0, 1.0)), backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
        x_coord, y_coord = grid.meshgrid()
        interface_width = 1.5 * min(float(grid.h[0][0]), float(grid.h[1][0]))
        distance = radius - np.sqrt((x_coord - 0.5) ** 2 + (y_coord - 0.5) ** 2)
        psi = 1.0 / (1.0 + np.exp(-distance / interface_width))

        faces = implicit_face_curvatures_2d(xp=np, grid=grid, psi=psi, fccd=fccd)
        kappa_faces = np.concatenate([face[np.abs(face) > 0.0] for face in faces])

        assert abs(float(np.mean(kappa_faces)) - 1.0 / radius) < 0.08
        assert float(np.std(kappa_faces)) < 0.08


def test_face_implicit_curvature_matches_ellipse_implicit_geometry():
    """Compact cut-face curvature matches the analytic ellipse level-set geometry."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(96, 96), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    x_coord, y_coord = grid.meshgrid()
    center_x, center_y = 0.5, 0.5
    semi_major, semi_minor = 0.30, 0.22
    interface_width = 1.5 * min(float(grid.h[0][0]), float(grid.h[1][0]))
    dx = x_coord - center_x
    dy = y_coord - center_y
    ellipse_radius = np.sqrt((dx / semi_major) ** 2 + (dy / semi_minor) ** 2)
    radius_safe = np.maximum(ellipse_radius, 1.0e-14)
    grad_radius = np.sqrt(
        (dx / (semi_major * semi_major * radius_safe)) ** 2
        + (dy / (semi_minor * semi_minor * radius_safe)) ** 2
    )
    ellipse_distance = (ellipse_radius - 1.0) / np.maximum(grad_radius, 1.0e-14)
    psi = 1.0 / (1.0 + np.exp(ellipse_distance / interface_width))
    faces = implicit_face_curvatures_2d(xp=np, grid=grid, psi=psi, fccd=fccd)
    samples = []
    expected = []
    for axis, kappa_face in enumerate(faces):
        if axis == 0:
            psi_lo, psi_hi = psi[:-1, :], psi[1:, :]
            x_lo, x_hi = x_coord[:-1, :], x_coord[1:, :]
            y_lo, y_hi = y_coord[:-1, :], y_coord[1:, :]
        else:
            psi_lo, psi_hi = psi[:, :-1], psi[:, 1:]
            x_lo, x_hi = x_coord[:, :-1], x_coord[:, 1:]
            y_lo, y_hi = y_coord[:, :-1], y_coord[:, 1:]
        cut_face = (psi_lo < 0.5) != (psi_hi < 0.5)
        theta = np.where(cut_face, (0.5 - psi_lo) / (psi_hi - psi_lo), 0.0)
        cut_x = (1.0 - theta) * x_lo + theta * x_hi
        cut_y = (1.0 - theta) * y_lo + theta * y_hi
        grad_x = 2.0 * (cut_x - center_x) / (semi_major * semi_major)
        grad_y = 2.0 * (cut_y - center_y) / (semi_minor * semi_minor)
        hess_xx = 2.0 / (semi_major * semi_major)
        hess_yy = 2.0 / (semi_minor * semi_minor)
        grad_sq = grad_x * grad_x + grad_y * grad_y
        analytic = np.zeros_like(grad_sq)
        analytic[cut_face] = (
            grad_y[cut_face] * grad_y[cut_face] * hess_xx
            + grad_x[cut_face] * grad_x[cut_face] * hess_yy
        ) / grad_sq[cut_face] ** 1.5
        samples.append(kappa_face[cut_face])
        expected.append(analytic[cut_face])
    sampled_kappa = np.concatenate(samples)
    analytic_kappa = np.concatenate(expected)

    np.testing.assert_allclose(sampled_kappa, analytic_kappa, rtol=0.05, atol=0.08)


def test_face_implicit_jump_uses_operation_local_face_curvature():
    """Face-implicit jumps use a local ``κ_f`` temporary, not context state."""
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(32, 32), L=(1.0, 1.0)), backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    fccd = FCCDSolver(grid, backend, bc_type="periodic", ccd_solver=ccd)
    x, y = grid.meshgrid()
    radius = 0.25
    interface_width = 1.5 * min(float(grid.h[0][0]), float(grid.h[1][0]))
    distance = radius - np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2)
    psi = 1.0 / (1.0 + np.exp(-distance / interface_width))
    context = build_young_laplace_interface_stress_context(
        xp=np,
        psi=psi,
        kappa_lg=np.zeros_like(psi),
        sigma=1.0,
        face_curvature_method="face_implicit",
    )

    face_curvature_lg = evaluate_interface_face_curvature_lg(
        xp=np,
        grid=grid,
        context=context,
        fccd=fccd,
    )
    jump_x = signed_pressure_jump_gradient(
        xp=np,
        grid=grid,
        context=context,
        axis=0,
        face_curvature_lg=face_curvature_lg,
    )

    assert face_curvature_lg is not None
    assert len(face_curvature_lg) == 2
    assert float(np.max(np.abs(jump_x))) > 0.0


def test_wall_compatible_curvature_uses_interior_limit():
    """No-slip wall contact curvature uses the one-sided interior limit."""
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(4, 4), L=(1.0, 1.0)),
    )
    grid = Grid(cfg.grid, backend)
    psi = np.full(grid.shape, 0.5)
    kappa = np.zeros(grid.shape)
    kappa[0, :] = 300.0
    kappa[1, :] = 40.0
    kappa[2, :] = 1.5
    kappa[3, :] = -40.0
    kappa[4, :] = -300.0

    closed = apply_wall_compatible_curvature(
        xp=np,
        grid=grid,
        psi=psi,
        kappa_lg=kappa,
        bc_type="wall",
        psi_min=0.01,
    )

    np.testing.assert_allclose(closed[0, 2], 1.5)
    np.testing.assert_allclose(closed[1, 2], 1.5)
    np.testing.assert_allclose(closed[3, 2], 1.5)
    np.testing.assert_allclose(closed[4, 2], 1.5)


def test_affine_jump_fvm_corrector_uses_same_nonuniform_jump_distance():
    """Face-flux corrector subtracts the same nonuniform ``B_f`` as the PPE."""
    grid, div_op = _make_two_cell_operator()
    grid.coords[0] = np.asarray([0.0, 0.25, 2.0])
    psi = np.ones(grid.shape)
    psi[1:, :] = 0.0
    kappa = np.full(grid.shape, 2.0)
    pressure = np.zeros(grid.shape)
    pressure[psi >= 0.5] = 6.0
    rho = np.ones(grid.shape)
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        kappa=kappa,
        sigma=3.0,
    )

    affine_faces = div_op.pressure_fluxes(
        pressure,
        rho,
        pressure_gradient="fvm",
        coefficient_scheme="phase_separated",
        interface_coupling_scheme="affine_jump",
        interface_stress_context=context,
    )

    np.testing.assert_allclose(affine_faces[0][0, :], 0.0, atol=1.0e-14)


def test_young_laplace_builder_stores_gas_minus_liquid_jump():
    """For ``κ_lg>0``, Young--Laplace gives ``p_g-p_l=-σκ_lg``."""
    psi = np.ones((2, 2))
    kappa_lg = np.full_like(psi, 2.0)

    context = build_young_laplace_interface_stress_context(
        xp=np,
        psi=psi,
        kappa_lg=kappa_lg,
        sigma=3.0,
    )

    np.testing.assert_allclose(context.pressure_jump_gas_minus_liquid, -6.0)
    np.testing.assert_allclose(context.kappa_lg, 2.0)


def test_explicit_pressure_jump_context_is_not_recomputed_from_curvature():
    """The affine operator consumes explicit ``p_g-p_l`` data, not raw ``σκ``."""
    psi = np.ones((2, 2))
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        pressure_jump_gas_minus_liquid=np.full_like(psi, 4.0),
        kappa_lg=np.full_like(psi, 99.0),
        sigma=3.0,
    )

    np.testing.assert_allclose(context.pressure_jump_gas_minus_liquid, 4.0)


def test_affine_jump_pressure_flux_preserves_cut_face_jump():
    """The phase-separated zero mask must not erase affine jump flux."""
    grid, div_op = _make_two_cell_operator()
    psi = np.ones(grid.shape)
    psi[1:, :] = 0.0
    kappa = np.full(grid.shape, 2.0)
    rho = np.ones(grid.shape)
    rho[psi >= 0.5] = 1000.0
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        kappa=kappa,
        sigma=3.0,
    )

    legacy_faces = div_op.pressure_fluxes(
        np.zeros(grid.shape),
        rho,
        coefficient_scheme="phase_separated",
    )
    affine_faces = div_op.pressure_fluxes(
        np.zeros(grid.shape),
        rho,
        coefficient_scheme="phase_separated",
        interface_coupling_scheme="affine_jump",
        interface_stress_context=context,
    )

    np.testing.assert_allclose(legacy_faces[0][0, :], 0.0)
    assert np.max(np.abs(affine_faces[0][0, :])) > 0.0


def test_affine_jump_flux_vanishes_when_pressure_satisfies_jump():
    """If ``p_gas-p_liquid=-σκ_lg``, then ``G_Γ`` is zero on the cut face."""
    grid, div_op = _make_two_cell_operator()
    psi = np.ones(grid.shape)
    psi[1:, :] = 0.0
    kappa = np.full(grid.shape, 2.0)
    rho = np.ones(grid.shape)
    rho[psi >= 0.5] = 1000.0
    pressure = np.zeros(grid.shape)
    pressure[psi >= 0.5] = 6.0
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        kappa=kappa,
        sigma=3.0,
    )

    affine_faces = div_op.pressure_fluxes(
        pressure,
        rho,
        coefficient_scheme="phase_separated",
        interface_coupling_scheme="affine_jump",
        interface_stress_context=context,
    )

    np.testing.assert_allclose(affine_faces[0][0, :], 0.0, atol=1.0e-14)


def test_affine_jump_cut_face_coefficient_uses_phase_resistance():
    """Cut faces use the interface-fraction density resistance, not midpoint rho."""
    grid, div_op = _make_two_cell_operator()
    psi = np.ones(grid.shape)
    psi[0, :] = 0.25
    kappa = np.full(grid.shape, 2.0)
    rho = np.full(grid.shape, 1000.0)
    rho[psi < 0.5] = 1.2
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        kappa=kappa,
        sigma=3.0,
    )
    pressure = np.zeros(grid.shape)

    affine_faces = div_op.pressure_fluxes(
        pressure,
        rho,
        coefficient_scheme="phase_separated",
        interface_coupling_scheme="affine_jump",
        interface_stress_context=context,
    )

    theta = (0.5 - psi[0, 0]) / (psi[1, 0] - psi[0, 0])
    expected_coeff = 1.0 / (theta * rho[0, 0] + (1.0 - theta) * rho[1, 0])
    expected_flux = -6.0 * expected_coeff
    midpoint_flux = -6.0 * (2.0 / (rho[0, 0] + rho[1, 0]))
    tolerance = np.finfo(float).eps * max(abs(expected_flux), 1.0) * 16.0
    np.testing.assert_allclose(affine_faces[0][0, :], expected_flux, atol=tolerance)
    assert not np.allclose(affine_faces[0][0, :], midpoint_flux, atol=tolerance)

    ppe_cfg = type(
        "Cfg",
        (),
        {
            "ppe_coefficient_scheme": "phase_separated",
            "ppe_interface_coupling_scheme": "affine_jump",
            "ppe_preconditioner": "none",
        },
    )()
    ppe = PPESolverFCCDMatrixFree(grid.backend, ppe_cfg, grid, div_op._fccd)
    ppe.set_interface_jump_context(psi=psi, kappa=kappa, sigma=3.0)
    ppe.prepare_operator(rho)
    np.testing.assert_allclose(ppe._coeff_face[0][0, :], expected_coeff)


def test_affine_jump_flux_vanishes_for_static_gas_bubble_sign():
    """For ``κ_lg<0``, the same law makes gas pressure higher."""
    grid, div_op = _make_two_cell_operator()
    psi = np.zeros(grid.shape)
    psi[1:, :] = 1.0
    kappa_lg = np.full(grid.shape, -2.0)
    rho = np.ones(grid.shape)
    rho[psi >= 0.5] = 1000.0
    pressure = np.zeros(grid.shape)
    pressure[psi < 0.5] = 6.0
    context = build_interface_stress_context(
        xp=np,
        psi=psi,
        kappa_lg=kappa_lg,
        sigma=3.0,
    )

    affine_faces = div_op.pressure_fluxes(
        pressure,
        rho,
        coefficient_scheme="phase_separated",
        interface_coupling_scheme="affine_jump",
        interface_stress_context=context,
    )

    np.testing.assert_allclose(context.pressure_jump_gas_minus_liquid, 6.0)
    np.testing.assert_allclose(affine_faces[0][0, :], 0.0, atol=1.0e-14)


def test_affine_jump_ppe_rhs_keeps_nonzero_cut_face_drive():
    """The affine PPE path must add ``D_f α_f B_Γ(j)`` instead of forming ``J``."""
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(2, 2), L=(2.0, 2.0)),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)
    ppe_cfg = type(
        "Cfg",
        (),
        {
            "ppe_coefficient_scheme": "phase_separated",
            "ppe_interface_coupling_scheme": "affine_jump",
            "ppe_preconditioner": "none",
        },
    )()
    ppe = PPESolverFCCDMatrixFree(backend, ppe_cfg, grid, fccd)
    psi = np.ones(grid.shape)
    psi[1:, :] = 0.0
    kappa = np.full(grid.shape, 2.0)
    rho = np.ones(grid.shape)
    rho[psi >= 0.5] = 1000.0

    ppe.set_interface_jump_context(psi=psi, kappa=kappa, sigma=3.0)
    ppe.prepare_operator(rho)
    rhs = ppe._add_affine_interface_jump_rhs(np.zeros(grid.shape))

    assert len(ppe._pin_dofs) == 1
    assert ppe._phase_threshold is None
    assert np.max(np.abs(rhs)) > 0.0
    np.testing.assert_allclose(ppe.apply_interface_jump(np.zeros(grid.shape)), 0.0)
