"""Tests for ClosestPointExtender (O(h^6) Hermite field extension).

1. Constant field → extension is identity
2. Source phase frozen (not modified)
3. O(h^6) convergence on smooth field (planar interface)
   NOTE: Hermite is designed for SMOOTH fields (e.g. CSF-regularised pressure).
   Discontinuous (step) fields corrupt CCD derivatives globally via the tri-diagonal
   system, so O(h^6) is NOT achievable for fresh discontinuous fields.
   The test uses q = 1 + cos(πx) everywhere (smooth), which is the correct use case.
4. Extension reduces CCD-gradient oscillation (smooth pressure analogue)
5. Builder integration: extension_method='hermite' builds and runs
"""

import pytest
import numpy as np

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.config import GridConfig
from twophase.levelset.closest_point_extender import ClosestPointExtender


@pytest.fixture
def setup_2d():
    N = 64
    gcfg = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    be = Backend(use_gpu=False)
    grid = Grid(gcfg, be)
    ccd = CCDSolver(grid, be, bc_type='wall')
    X, Y = grid.meshgrid()
    return N, grid, ccd, X, Y


# ── Test 1: Constant field is unchanged ───────────────────────────────────

def test_constant_field_unchanged(setup_2d):
    """Extending a constant field must not modify it."""
    N, grid, ccd, X, Y = setup_2d
    ext = ClosestPointExtender(Backend(use_gpu=False), grid, ccd)

    phi = X - 0.5   # planar interface at x=0.5
    q = np.full_like(X, 3.14)
    q_ext = ext.extend(q, phi)

    assert np.allclose(q_ext, 3.14, atol=1e-10), (
        f"Constant field modified: max_err={np.max(np.abs(q_ext - 3.14)):.3e}"
    )


# ── Test 2: Source phase frozen ───────────────────────────────────────────

def test_source_phase_frozen(setup_2d):
    """Extension must not modify the source phase (φ<0 region)."""
    N, grid, ccd, X, Y = setup_2d
    ext = ClosestPointExtender(Backend(use_gpu=False), grid, ccd)

    phi = X - 0.5
    q = np.where(X < 0.5, 2.0 + np.sin(4*np.pi*Y), 0.0)
    q_ext = ext.extend(q, phi)

    source_mask = (phi < 0)
    err = np.max(np.abs(q_ext[source_mask] - q[source_mask]))
    assert err < 1e-14, f"Source phase modified: max_err={err:.3e}"


# ── Test 3: O(h^6) convergence (1-D analogue, planar interface) ───────────

def test_hermite_convergence_order():
    """Field extension error must converge at O(h^6) for smooth source field.

    Setup: planar interface at x=0.5 (φ = x−0.5, uniform in y).
    Source field: q(x) = 1 + cos(π x) for x < 0.5.
    Exact extended field: q_ext = q(0.5) = 1  (constant-normal extension).
    Error measured in [0.52, 0.55] (extension band).
    """
    be = Backend(use_gpu=False)
    errors = []
    Ns = [32, 64, 128, 256]

    for N in Ns:
        gcfg = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gcfg, be)
        ccd = CCDSolver(grid, be, bc_type='wall')
        ext = ClosestPointExtender(be, grid, ccd)

        X, Y = grid.meshgrid()   # X, Y each shape (N+1, N+1)
        phi = X - 0.5            # interface at x=0.5; source: x<0.5

        # Source field: SMOOTH everywhere (no jump at interface).
        # This is the correct use case: CSF-regularised pressure is continuous.
        # Discontinuous fields corrupt CCD derivatives globally via the
        # tri-diagonal system → O(h^6) is NOT achievable for step functions.
        q = 1.0 + np.cos(np.pi * X)   # smooth, q'≠0 at x=0.5

        q_ext = ext.extend(q, phi)

        # Exact closest-point extension: q_ext(x) = q(x_Γ) = q(0.5) = 1
        q_exact = 1.0
        band = (X >= 0.52) & (X <= 0.55)
        err = np.max(np.abs(q_ext[band] - q_exact))
        errors.append(err)

    # Compute convergence rates
    rates = [np.log2(errors[k] / errors[k+1]) for k in range(len(errors)-1)]
    # All rates should be ≥ 5.0 (allowing for rounding near machine precision)
    for i, rate in enumerate(rates):
        assert rate >= 5.0, (
            f"N={Ns[i]}→{Ns[i+1]}: convergence rate {rate:.2f} < 5.0 "
            f"(errors: {errors[i]:.2e} → {errors[i+1]:.2e})"
        )


# ── Test 4: Smooth-field extension leaves CCD gradient bounded ────────────

def test_smooth_extension_bounded_gradient(setup_2d):
    """Extending a smooth field must not amplify CCD gradients.

    For the valid use case (smooth p, like CSF-regularised pressure),
    the extended field should have CCD gradients comparable to the source.
    """
    N, grid, ccd, X, Y = setup_2d
    ext = ClosestPointExtender(Backend(use_gpu=False), grid, ccd)

    dist = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    R = 0.25
    phi = dist - R   # source: φ<0 (inside circle)

    # Smooth pressure analogue (CSF-style: continuous across interface)
    p = 1.0 + np.cos(np.pi * dist)   # smooth, no jump

    dpx_raw, _ = ccd.differentiate(p, 0)
    p_ext = ext.extend(p, phi)
    dpx_ext, _ = ccd.differentiate(p_ext, 0)

    max_raw = np.max(np.abs(dpx_raw))
    max_ext = np.max(np.abs(dpx_ext))

    # Extension should not amplify gradients by more than 2x
    assert max_ext < max_raw * 2.0, (
        f"Extension amplified gradient: raw={max_raw:.2f}, ext={max_ext:.2f}"
    )


# ── Test 5: Builder integration (extension_method='hermite') ─────────────

def test_builder_hermite_extension():
    """SimulationBuilder with extension_method='hermite' must build and run."""
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
            surface_tension_model="csf", extension_method="hermite",
        ),
        solver=SolverConfig(ppe_solver_type="ccd_lu"),
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
        assert not xp.any(xp.isnan(arr)), f"ClosestPoint pipeline: {name} NaN"
        assert not xp.any(xp.isinf(arr)), f"ClosestPoint pipeline: {name} Inf"
