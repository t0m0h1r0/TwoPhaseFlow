"""
Integration test — SimulationBuilder + TwoPhaseSimulation core loop.

Exercises the full 7-step pipeline (§9.1) end-to-end via the sole
construction path (ASM-001: SimulationBuilder).

Verifies:
  1. SimulationBuilder.build() returns TwoPhaseSimulation without error.
  2. step_forward() runs 2 steps with no NaN / Inf in any field.

Notes:
  - Grid: N=16 (fast; node-centered grid → field shape (N+1)×(N+1) = 17×17).
  - Solver: 'fvm_direct' keeps this smoke on the production PPE family.
"""

import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.config import (
    SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
)
from twophase.simulation.builder import SimulationBuilder
from twophase.simulation._core import TwoPhaseSimulation
from twophase.simulation.initial_conditions import InitialConditionBuilder, Circle


# ── Benchmark parameters (§10.3 Benchmark 1) ──────────────────────────────────

N      = 16
R      = 0.25
CENTER = (0.5, 0.5)
WE     = 1.0


# ── Fixture ────────────────────────────────────────────────────────────────────

def _make_sim() -> TwoPhaseSimulation:
    """Build a minimal stationary-droplet simulation (N=16, solver='lu')."""
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(
            Re=100.0,
            Fr=1e6,        # effectively no gravity
            We=WE,
            rho_ratio=0.1,
            mu_ratio=0.1,
        ),
        numerics=NumericsConfig(
            epsilon_factor=1.5,
            reinit_steps=2,
            cfl_number=0.3,
            t_end=0.1,
            bc_type="wall",
            advection_scheme="dissipative_ccd",
        ),
        solver=SolverConfig(ppe_solver_type="fvm_direct"),
    )
    sim = SimulationBuilder(cfg).build()

    # Initialize CLS field: liquid droplet at center, gas background
    # Convention: ψ ≈ 0 → liquid, ψ ≈ 1 → gas  (§2: ψ_l≈0, ψ_g≈1)
    sim.psi.data[:] = (
        InitialConditionBuilder(background_phase='gas')
        .add(Circle(center=CENTER, radius=R, interior_phase='liquid'))
        .build(sim.grid, sim.eps)
    )
    return sim


@pytest.fixture
def sim():
    return _make_sim()


# ── Test 1: Builder constructs ─────────────────────────────────────────────────

def test_builder_constructs(sim):
    """SimulationBuilder must return a TwoPhaseSimulation (ASM-001).

    Node-centered grid: field shape = (N+1, N+1) = (17, 17) for N=16.
    """
    assert isinstance(sim, TwoPhaseSimulation)
    assert sim.grid is not None
    expected_shape = sim.grid.shape   # (N+1, N+1) for node-centered grid
    assert sim.psi.data.shape      == expected_shape
    assert sim.pressure.data.shape == expected_shape
    assert sim.velocity[0].shape   == expected_shape
    assert sim.velocity[1].shape   == expected_shape


# ── Test 2: step_forward — no NaN / Inf ───────────────────────────────────────

def test_step_forward_no_nan(sim):
    """2 calls to step_forward(dt) must not produce NaN or Inf in any field."""
    dt = 1e-3
    # Mirrors sim.run(): initialise properties/curvature before first step
    sim._update_properties()
    sim._update_curvature()

    sim.step_forward(dt)
    sim.step_forward(dt)

    xp = sim.backend.xp
    for name, arr in [
        ("pressure",   sim.pressure.data),
        ("velocity[0]", sim.velocity[0]),
        ("velocity[1]", sim.velocity[1]),
        ("psi",        sim.psi.data),
        ("rho",        sim.rho.data),
        ("kappa",      sim.kappa.data),
    ]:
        assert not xp.any(xp.isnan(arr)), f"{name} contains NaN after 2 steps"
        assert not xp.any(xp.isinf(arr)), f"{name} contains Inf after 2 steps"
