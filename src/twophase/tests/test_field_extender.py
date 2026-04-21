"""Tests for FieldExtender (Extension PDE, Aslam 2004).

1. Step function → extended field is smooth (CCD gradient bounded)
2. Constant field → extension is identity (no change)
3. Source phase frozen (not modified by extension)
4. Integration: SimulationBuilder with n_extend>0 builds and runs
"""

import pytest
import numpy as np

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.config import GridConfig


@pytest.fixture
def setup_2d():
    N = 32
    gcfg = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    be = Backend(use_gpu=False)
    grid = Grid(gcfg, be)
    ccd = CCDSolver(grid, be, bc_type='wall')
    X, Y = grid.meshgrid()
    return N, grid, ccd, X, Y


# ── Test 1: Step function extension reduces CCD gradient oscillation ──────

def test_extension_reduces_gibbs(setup_2d):
    """Extension of a step function must reduce CCD gradient magnitude."""
    from twophase.levelset.field_extender import FieldExtender

    N, grid, ccd, X, Y = setup_2d
    ext = FieldExtender(Backend(use_gpu=False), grid, ccd, n_iter=10)

    dist = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    R = 0.25
    phi = dist - R  # gas outside (φ>0), liquid inside (φ<0)

    # Sharp Laplace pressure: 4.0 inside, 0.0 outside
    p = np.where(dist < R, 4.0, 0.0)

    # CCD gradient of raw field
    dpx_raw, _ = ccd.differentiate(p, 0)
    max_raw = np.max(np.abs(dpx_raw))

    # Extend liquid into gas
    p_ext = ext.extend(p, phi)
    dpx_ext, _ = ccd.differentiate(p_ext, 0)
    max_ext = np.max(np.abs(dpx_ext))

    # Near-interface gradient should be significantly reduced
    near_if = (np.abs(dist - R) < 3.0 / N)
    max_raw_if = np.max(np.abs(dpx_raw[near_if]))
    max_ext_if = np.max(np.abs(dpx_ext[near_if]))

    assert max_ext_if < max_raw_if * 0.5, (
        f"Extension should reduce interface gradient by >50%: "
        f"raw={max_raw_if:.2f}, ext={max_ext_if:.2f}"
    )


# ── Test 2: Constant field is unchanged ───────────────────────────────────

def test_extension_preserves_constant(setup_2d):
    """Extending a constant field must not change it."""
    from twophase.levelset.field_extender import FieldExtender

    N, grid, ccd, X, Y = setup_2d
    ext = FieldExtender(Backend(use_gpu=False), grid, ccd, n_iter=5)

    phi = X - 0.5
    q = np.full_like(X, 3.14)
    q_ext = ext.extend(q, phi)

    assert np.allclose(q_ext, 3.14, atol=1e-12), "Constant field modified by extension"


# ── Test 3: Source phase is frozen ────────────────────────────────────────

def test_source_phase_frozen(setup_2d):
    """Extension must not modify the source phase (φ<0 region)."""
    from twophase.levelset.field_extender import FieldExtender

    N, grid, ccd, X, Y = setup_2d
    ext = FieldExtender(Backend(use_gpu=False), grid, ccd, n_iter=10)

    phi = X - 0.5  # liquid at x<0.5 (φ<0)
    q = np.where(X < 0.5, 4.0, 0.0)
    q_ext = ext.extend(q, phi)

    source_mask = (phi < 0)
    assert np.allclose(q_ext[source_mask], q[source_mask]), (
        "Source phase values were modified by extension"
    )


# ── Test 4: NaN in target phase must not propagate ───────────────────────

def test_extend_nan_in_target_phase(setup_2d):
    """NaN in the target (gas) phase must be replaced, not propagated."""
    from twophase.levelset.field_extender import FieldExtender

    N, grid, ccd, X, Y = setup_2d
    ext = FieldExtender(Backend(use_gpu=False), grid, ccd, n_iter=5)

    phi = X - 0.5  # liquid at x<0.5 (phi<0), gas at x>=0.5 (phi>=0)
    # Realistic case: q is uninitialized (NaN) in the target gas phase
    q = np.where(X < 0.5, 4.0, np.nan)
    q_ext = ext.extend(q, phi)

    assert not np.any(np.isnan(q_ext)), "NaN in target phase must not propagate"
    assert not np.any(np.isinf(q_ext)), "Inf must not appear after extension"


# ── Test 5: Builder integration with n_extend ────────────────────────────

def test_builder_with_extension():
    """SimulationBuilder with n_extend>0 must build and run 2 steps."""
    from twophase.simulation.builder import SimulationBuilder
    from twophase.simulation.initial_conditions import InitialConditionBuilder, Circle
    from twophase.config import (
        SimulationConfig, GridConfig, FluidConfig,
        NumericsConfig, SolverConfig,
    )

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(16, 16), L=(1.0, 1.0)),
        fluid=FluidConfig(Re=100., Fr=1e6, We=1.0, rho_ratio=0.001, mu_ratio=0.01),
        numerics=NumericsConfig(
            epsilon_factor=1.5, reinit_steps=2, cfl_number=0.3,
            t_end=0.1, bc_type="wall", advection_scheme="dissipative_ccd",
            surface_tension_model="csf", n_extend=5,
        ),
        solver=SolverConfig(ppe_solver_type="ccd_lu", allow_kronecker_lu=True),
    )
    sim = SimulationBuilder(cfg).build()

    sim.psi.data[:] = (
        InitialConditionBuilder(background_phase='gas')
        .add(Circle(center=(0.5, 0.5), radius=0.25, interior_phase='liquid'))
        .build(sim.grid, sim.eps)
    )
    sim._update_properties()
    sim._update_curvature()

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        sim.step_forward(dt=1e-4)
        sim.step_forward(dt=1e-4)

    xp = sim.backend.xp
    for name, arr in [
        ("pressure", sim.pressure.data),
        ("velocity[0]", sim.velocity[0]),
        ("psi", sim.psi.data),
    ]:
        assert not xp.any(xp.isnan(arr)), f"Extension pipeline: {name} contains NaN"
        assert not xp.any(xp.isinf(arr)), f"Extension pipeline: {name} contains Inf"
