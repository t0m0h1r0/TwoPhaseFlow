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
from twophase.coupling.interface_stress_closure import (
    build_interface_stress_context,
    build_young_laplace_interface_stress_context,
    signed_pressure_jump_gradient,
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
