"""
Integration test — SimulationBuilder + TwoPhaseSimulation core loop.

Exercises the full 7-step pipeline (§9.1) end-to-end via the sole
construction path (ASM-001: SimulationBuilder).

Verifies:
  1. SimulationBuilder.build() returns TwoPhaseSimulation without error.
  2. step_forward() runs 2 steps with no NaN / Inf in any field.
  3. After a short run, the Laplace pressure jump Δp = p_in − p_out
     is positive (correct sign) and physically bounded (< 15).

Notes:
  - Grid: N=16 (fast; node-centered grid → field shape (N+1)×(N+1) = 17×17).
  - Solver: 'lu' (direct sparse LU) — avoids BiCGSTAB convergence sensitivity
    at coarse resolution (§5 implicit solver policy: LU for small systems).
  - Absolute Laplace pressure accuracy (O(ε²) CSF error) is NOT asserted
    here; that is the responsibility of StationaryDropletBenchmark (§10.3,
    Priority 3).  This test only verifies sign correctness and pipeline
    stability.
  - Spatial (distance-based) mask is used instead of psi threshold because
    the CLS profile diffuses at N=16 (ε/R ≈ 0.37) and max(psi) may not
    reach 0.7 after a short run.
"""

import numpy as np
import pytest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.config import (
    SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
)
from twophase.simulation.builder import SimulationBuilder
from twophase.simulation._core import TwoPhaseSimulation
from twophase.initial_conditions import InitialConditionBuilder, Circle


# ── Benchmark parameters (§10.3 Benchmark 1) ──────────────────────────────────

N      = 16
R      = 0.25
CENTER = (0.5, 0.5)
WE     = 1.0
# Spatial mask radii (well inside / outside interface — robust to CLS diffusion)
R_IN   = R * 0.70   # 0.175 — safely inside liquid droplet
R_OUT  = R * 1.50   # 0.375 — safely outside in gas region


# ── Fixture ────────────────────────────────────────────────────────────────────

def _make_sim() -> TwoPhaseSimulation:
    """Build a minimal stationary-droplet simulation (N=16, solver='lu')."""
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(
            Re=100.0,
            Fr=1e6,        # effectively no gravity
            We=WE,
            rho_ratio=0.001,
            mu_ratio=0.01,
        ),
        numerics=NumericsConfig(
            epsilon_factor=1.5,
            reinit_steps=2,
            cfl_number=0.3,
            t_end=0.1,
            bc_type="wall",
            advection_scheme="dissipative_ccd",
        ),
        solver=SolverConfig(ppe_solver_type="lu"),   # direct LU — no convergence risk
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


# ── Test 3: Laplace pressure sign ─────────────────────────────────────────────

def test_laplace_pressure_sign(sim):
    """After a short run, pressure inside the droplet must exceed outside.

    Laplace law (§2, CSF): Δp = p_in − p_out = (1/We) κ = (1/We)/R > 0.
    At N=16 the CSF error is O(ε²) ≈ O((1.5/16)²) — absolute accuracy is
    NOT asserted here.  Sign correctness and physical boundedness are
    sufficient for an integration test; accuracy is verified by
    StationaryDropletBenchmark (§10.3, Priority 3).

    Spatial mask: distance from droplet centre rather than ψ threshold,
    because CLS diffuses at N=16 and max(ψ) may fall below 0.7 at t=0.02.
    """
    sim.run(t_end=0.02, output_interval=9999, verbose=False)

    xp = sim.backend.xp
    p  = sim.pressure.data
    X, Y = sim.grid.meshgrid()
    dist = xp.sqrt((X - CENTER[0])**2 + (Y - CENTER[1])**2)

    inside  = dist < R_IN
    outside = dist > R_OUT
    assert inside.sum()  > 0, f"No interior nodes found (dist < {R_IN})"
    assert outside.sum() > 0, f"No exterior nodes found (dist > {R_OUT})"

    p_in    = float(xp.mean(p[inside]))
    p_out   = float(xp.mean(p[outside]))
    delta_p = p_in - p_out

    assert delta_p > 0, (
        f"Δp = {delta_p:.4f}: pressure inside droplet must exceed outside "
        f"(Laplace law, §2 CSF)"
    )
    assert delta_p < 15.0, (
        f"Δp = {delta_p:.4f}: unphysically large — likely a solver blowup"
    )
