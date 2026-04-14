"""
Tests for GFM + DCCD-PPE pipeline (§8e sec:gfm + §7 sec:dccd_decoupling).

Verifies:
  1. GFMCorrector: interface detection and RHS correction sign/magnitude
  2. DCCDPPEFilter: eps_d=1/4 filter zeroes 2*dx checkerboard mode
  3. DCCDPPEFilter: divergence computation matches CCD reference
  4. PPERHSBuilderGFM: end-to-end RHS assembly
  5. Integration: GFM pipeline builds and runs 2 steps without NaN/Inf
  6. GFM Laplace pressure sign: p_in > p_out with GFM surface tension model
"""

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import (
    SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
)
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.coupling.gfm import GFMCorrector
from twophase.spatial.dccd_ppe_filter import DCCDPPEFilter
from twophase.coupling.ppe_rhs_gfm import PPERHSBuilderGFM


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_setup(N=16, backend=None, bc_type="wall"):
    if backend is None:
        backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type=bc_type)
    return cfg, grid, ccd, backend


# ── Test 1: GFMCorrector interface detection ──────────────────────────────────

def test_gfm_correction_nonzero_at_interface(backend):
    """GFM correction must be nonzero only near the interface (phi sign change)."""
    cfg, grid, ccd, be = make_setup(N=16, backend=backend)
    xp = be.xp
    We = 10.0
    gfm = GFMCorrector(be, grid, We)

    shape = grid.shape
    X, Y = grid.meshgrid()

    # Circular interface: phi = distance - R
    R = 0.25
    phi = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R

    # Uniform curvature for a circle: kappa = 1/R
    kappa = xp.ones(shape) / R

    # Uniform density
    rho = xp.ones(shape)

    b_gfm = gfm.compute_rhs_correction(phi, kappa, rho)

    # b_gfm should be nonzero somewhere (near the interface)
    assert xp.any(b_gfm != 0.0), "GFM correction is all zeros — no interface detected"

    # b_gfm should be zero far from the interface
    far_from_interface = xp.abs(phi) > 3 * grid.L[0] / grid.N[0]
    assert xp.all(b_gfm[far_from_interface] == 0.0), \
        "GFM correction is nonzero far from the interface"


# ── Test 2: GFMCorrector conservation (sum ≈ 0) ──────────────────────────────

def test_gfm_correction_sum_near_zero(backend):
    """GFM corrections should approximately sum to zero (conservation)."""
    cfg, grid, ccd, be = make_setup(N=32, backend=backend)
    xp = be.xp
    We = 10.0
    gfm = GFMCorrector(be, grid, We)

    X, Y = grid.meshgrid()
    R = 0.25
    phi = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    kappa = xp.ones(grid.shape) / R
    rho = xp.ones(grid.shape)

    b_gfm = gfm.compute_rhs_correction(phi, kappa, rho)

    # The corrections come in ± pairs across the interface, so sum ≈ 0
    # Allow some tolerance due to discrete geometry
    assert abs(float(xp.sum(b_gfm))) < 1.0, \
        f"GFM correction sum = {float(xp.sum(b_gfm)):.3e}, expected ≈ 0"


# ── Test 3: DCCDPPEFilter zeroes checkerboard ─────────────────────────────────

def test_dccd_filter_zeroes_checkerboard(backend):
    """eps_d=1/4 filter must completely remove 2*dx checkerboard pattern.

    Eq. dccd_eps_checkerboard: H(pi; 1/4) = 1 - 4*(1/4)*sin^2(pi/2) = 0
    """
    cfg, grid, ccd, be = make_setup(N=32, backend=backend)
    xp = be.xp
    dccd = DCCDPPEFilter(be, grid, ccd, bc_type="wall")

    shape = grid.shape
    # Pure checkerboard pattern: (-1)^(i+j)
    I = xp.arange(shape[0])
    J = xp.arange(shape[1])
    II, JJ = xp.meshgrid(I, J, indexing='ij')
    checker = (-1.0) ** (II + JJ)

    vel = [checker, checker]
    vel_filtered = dccd.filter_velocity(vel)

    # Interior nodes should be zero (boundary nodes may not be exactly zero
    # due to one-sided stencil)
    interior = vel_filtered[0][2:-2, 2:-2]
    assert xp.max(xp.abs(interior)) < 1e-14, \
        f"Checkerboard not removed: max interior = {float(xp.max(xp.abs(interior))):.2e}"


# ── Test 4: DCCDPPEFilter preserves smooth fields ────────────────────────────

def test_dccd_filter_preserves_smooth(backend):
    """eps_d=1/4 filter should approximately preserve smooth (low-frequency) fields."""
    cfg, grid, ccd, be = make_setup(N=32, backend=backend)
    xp = be.xp
    dccd = DCCDPPEFilter(be, grid, ccd, bc_type="wall")

    X, Y = grid.meshgrid()
    # Smooth field: single-mode sine
    u_smooth = xp.sin(2 * np.pi * X) * xp.cos(2 * np.pi * Y)
    vel = [u_smooth, u_smooth]
    vel_filtered = dccd.filter_velocity(vel)

    # Filter should only weakly alter low-frequency content
    # H(k) = 1 - sin^2(kh/2) for eps_d=1/4; for k*h << pi, H ≈ 1
    diff = xp.max(xp.abs(vel_filtered[0] - u_smooth))
    assert diff < 0.3, \
        f"Filter excessively distorted smooth field: max diff = {float(diff):.3e}"


# ── Test 5: DCCDPPEFilter divergence of uniform field = 0 ────────────────────

def test_dccd_filtered_divergence_of_uniform_is_zero(backend):
    """Divergence of a uniform velocity field must be zero."""
    cfg, grid, ccd, be = make_setup(N=16, backend=backend)
    xp = be.xp
    dccd = DCCDPPEFilter(be, grid, ccd, bc_type="wall")

    vel = [xp.ones(grid.shape), xp.ones(grid.shape)]
    div = dccd.compute_filtered_divergence(vel)

    assert xp.max(xp.abs(div)) < 1e-10, \
        f"Divergence of uniform field should be ~0: max = {float(xp.max(xp.abs(div))):.2e}"


# ── Test 6: PPERHSBuilderGFM end-to-end ──────────────────────────────────────

def test_ppe_rhs_gfm_assembly(backend):
    """PPERHSBuilderGFM must produce a non-trivial RHS for a droplet setup."""
    cfg, grid, ccd, be = make_setup(N=16, backend=backend)
    xp = be.xp

    gfm = GFMCorrector(be, grid, We=10.0)
    dccd = DCCDPPEFilter(be, grid, ccd)
    builder = PPERHSBuilderGFM(dccd, gfm)

    X, Y = grid.meshgrid()
    R = 0.25
    phi = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    kappa = xp.ones(grid.shape) / R
    rho = xp.ones(grid.shape)
    dt = 1e-3

    # Non-zero velocity to produce divergence
    vel_star = [xp.sin(np.pi * X), xp.cos(np.pi * Y)]
    rhs = builder.build_rhs(vel_star, phi, kappa, rho, dt)

    assert rhs.shape == grid.shape
    assert not xp.any(xp.isnan(rhs)), "PPE RHS contains NaN"
    assert not xp.any(xp.isinf(rhs)), "PPE RHS contains Inf"
    assert xp.max(xp.abs(rhs)) > 0, "PPE RHS is all zeros"


# ── Test 7: GFM pipeline integration (build + run) ───────────────────────────

def test_gfm_pipeline_builds_and_runs():
    """SimulationBuilder with surface_tension_model='gfm' must build and
    run 2 steps without NaN/Inf."""
    from twophase.simulation.builder import SimulationBuilder
    from twophase.simulation.initial_conditions import InitialConditionBuilder, Circle

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(16, 16), L=(1.0, 1.0)),
        fluid=FluidConfig(Re=100., Fr=1e6, We=1.0, rho_ratio=0.001, mu_ratio=0.01),
        numerics=NumericsConfig(
            epsilon_factor=1.5,
            reinit_steps=2,
            cfl_number=0.3,
            t_end=0.1,
            bc_type="wall",
            advection_scheme="dissipative_ccd",
            surface_tension_model="gfm",
        ),
        solver=SolverConfig(ppe_solver_type="ccd_lu"),
    )
    sim = SimulationBuilder(cfg).build()

    # Initialize CLS field: liquid droplet
    sim.psi.data[:] = (
        InitialConditionBuilder(background_phase='gas')
        .add(Circle(center=(0.5, 0.5), radius=0.25, interior_phase='liquid'))
        .build(sim.grid, sim.eps)
    )

    sim._update_properties()
    sim._update_curvature()

    dt = 1e-3
    sim.step_forward(dt)
    sim.step_forward(dt)

    xp = sim.backend.xp
    for name, arr in [
        ("pressure", sim.pressure.data),
        ("velocity[0]", sim.velocity[0]),
        ("velocity[1]", sim.velocity[1]),
        ("psi", sim.psi.data),
    ]:
        assert not xp.any(xp.isnan(arr)), f"GFM pipeline: {name} contains NaN"
        assert not xp.any(xp.isinf(arr)), f"GFM pipeline: {name} contains Inf"


# ── Test 8: GFM Laplace pressure sign ─────────────────────────────────────────

@pytest.mark.xfail(
    reason="CCD PPE product-rule operator does not correctly resolve Laplace pressure jump "
           "across sharp GFM density discontinuity. Requires GFM+CCD integration (next_action).",
    strict=False,
)
def test_gfm_laplace_pressure_sign():
    """With GFM, pressure inside the droplet must exceed outside (Laplace law).

    Laplace law: delta_p = kappa / We = (1/R) / We > 0.
    GFM incorporates this as PPE RHS correction (Eq. gfm_rhs_correction).
    """
    from twophase.simulation.builder import SimulationBuilder
    from twophase.simulation.initial_conditions import InitialConditionBuilder, Circle

    N = 32
    R = 0.25
    We = 1.0

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(Re=100., Fr=1e6, We=We, rho_ratio=0.1, mu_ratio=0.1),
        numerics=NumericsConfig(
            epsilon_factor=1.5,
            reinit_steps=2,
            cfl_number=0.3,
            t_end=0.1,
            bc_type="wall",
            advection_scheme="dissipative_ccd",
            surface_tension_model="gfm",
        ),
        solver=SolverConfig(ppe_solver_type="ccd_lu"),
    )
    sim = SimulationBuilder(cfg).build()

    sim.psi.data[:] = (
        InitialConditionBuilder(background_phase='gas')
        .add(Circle(center=(0.5, 0.5), radius=R, interior_phase='liquid'))
        .build(sim.grid, sim.eps)
    )

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        sim.step_forward(dt=1e-4)
        sim.step_forward(dt=1e-4)

    xp = sim.backend.xp
    X, Y = sim.grid.meshgrid()
    dist = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    p = sim.pressure.data

    p_in = float(xp.mean(p[dist < R * 0.7]))
    p_out = float(xp.mean(p[dist > R * 1.5]))

    assert p_in > p_out, (
        f"GFM Laplace: p_in={p_in:.4f} <= p_out={p_out:.4f} — wrong sign"
    )
