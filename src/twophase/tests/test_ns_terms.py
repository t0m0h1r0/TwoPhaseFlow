"""
Tests for Navier-Stokes term modules (§9 of the paper).

Verified properties:
  1. Convection term -(u·∇)u: exact for polynomial u.
  2. Viscous term: matches direct finite-difference Laplacian.
  3. Gravity: acts on correct axis, correct sign.
  4. Surface tension: localised at interface.
  5. Predictor: advances velocity without NaN for a simple test case.
"""

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ns_terms.convection import ConvectionTerm
from twophase.ns_terms.viscous import ViscousTerm
from twophase.ns_terms.gravity import GravityTerm
from twophase.ns_terms.surface_tension import SurfaceTensionTerm
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_setup(N=16, backend=None):
    if backend is None:
        backend = Backend(use_gpu=False)
    cfg = SimulationConfig(ndim=2, N=(N, N), L=(1.0, 1.0), Re=10., Fr=1., We=5.)
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    return cfg, grid, ccd, backend


# ── Test 1: Convection term ───────────────────────────────────────────────

def test_convection_u_grad_u(backend):
    """For u=(c,0), v=0: -(u·∇)u = (-c ∂u/∂x, 0) = 0 for uniform u."""
    cfg, grid, ccd, be = make_setup(backend=backend)
    conv = ConvectionTerm(be)

    N = 16
    u = np.ones((N+1, N+1)) * 2.0
    v = np.zeros((N+1, N+1))

    result = conv.compute([u, v], ccd)
    # -(u·∇)u = -(2*0, 0) = 0 for constant u
    assert np.max(np.abs(result[0])) < 1e-10, "Convection of uniform u should be 0"
    assert np.max(np.abs(result[1])) < 1e-10, "Convection of v=0 should be 0"


def test_convection_linear_u(backend):
    """For u = x, v = 0: -(u·∇)u_x = -x (evaluated at x)."""
    cfg, grid, ccd, be = make_setup(backend=backend)
    conv = ConvectionTerm(be)

    N = 16
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    u = X.copy()
    v = np.zeros_like(u)

    result = conv.compute([u, v], ccd)
    # -(u·∇)u = -u * ∂u/∂x = -x * 1 = -x
    expected = -X
    err = np.max(np.abs(result[0] - expected))
    assert err < 1e-8, f"Convection -(u·∇)u error {err:.2e}"


# ── Test 2: Viscous term ──────────────────────────────────────────────────

def test_viscous_laplacian_constant_mu(backend):
    """For μ=const, Re=1: viscous term = μ Δu / ρ."""
    cfg, grid, ccd, be = make_setup(N=32, backend=backend)
    visc = ViscousTerm(be, Re=1.0, cn_viscous=False)

    N = 32
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    # u = sin(2πx), known Laplacian = -(2π)² sin(2πx)
    u = np.sin(2 * np.pi * X)
    v = np.zeros_like(u)
    mu = np.ones_like(u)
    rho = np.ones_like(u)

    result = visc.compute_explicit([u, v], mu, rho, ccd)
    # For the symmetric strain-rate divergence with μ=const, ρ=const,
    # the x-component should be: (1/Re) * [∂²u/∂x² + ∂²u/∂y²
    #                                       + ∂/∂x(∂u/∂x + ∂u/∂y)] = (2/Re) Δu
    # But here we implement the full symmetric tensor, so result ≈ (2/Re) Δu
    lap_u = -(2 * np.pi)**2 * np.sin(2 * np.pi * X)   # ∂²u/∂x² (∂²u/∂y² = 0)
    # The symmetric tensor for u(x) only: V_x = (1/Re ρ) * (2 ∂²u/∂x² + 0) = 2 Δu / Re
    expected = 2.0 * lap_u   # Re=1, rho=1
    err = np.max(np.abs(result[0][1:-1, 1:-1] - expected[1:-1, 1:-1]))
    # Two chained CCD operations; O(h^5) boundary error amplified by 2nd CCD.
    # For N=32, h=1/32: expected error ≈ O((2π)^6 * h^5) ≈ 5e-3.
    assert err < 5e-3, f"Viscous laplacian error {err:.2e}"


# ── Test 3: Gravity ───────────────────────────────────────────────────────

def test_gravity_direction(backend):
    """Gravity must act on the last spatial axis with correct sign."""
    cfg, grid, ccd, be = make_setup(backend=backend)
    grav = GravityTerm(be, Fr=1.0, ndim=2)

    rho = np.ones((17, 17))
    g = grav.compute(rho, rho.shape)

    # x-component must be zero
    assert np.max(np.abs(g[0])) < 1e-14, "Gravity x-component should be 0"
    # y-component must be -rho / Fr^2 = -1
    assert np.allclose(g[1], -1.0), "Gravity y-component should be -ρ/Fr²"


def test_gravity_froude(backend):
    """Gravity force scales as 1/Fr²."""
    cfg, grid, ccd, be = make_setup(backend=backend)
    Fr = 2.0
    grav = GravityTerm(be, Fr=Fr, ndim=2)
    rho = np.ones((17, 17))
    g = grav.compute(rho, rho.shape)
    expected = -1.0 / (Fr ** 2)
    assert np.allclose(g[1], expected), f"Gravity scaling with Fr={Fr} failed"


# ── Test 4: Surface tension localisation ─────────────────────────────────

def test_surface_tension_localised(backend):
    """CSF force must be large only near the interface (|φ| < 3ε)."""
    N = 32
    cfg = SimulationConfig(ndim=2, N=(N, N), L=(1.0, 1.0), We=1.0)
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    st = SurfaceTensionTerm(backend, We=1.0)
    curv_calc = CurvatureCalculator(backend, eps)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.2
    psi = heaviside(xp, phi, eps)
    kappa = curv_calc.compute(psi, ccd)

    f_st = st.compute(kappa, psi, ccd)

    # Far from interface (|φ| > 5ε) force should be negligible
    far = np.abs(phi) > 5 * eps
    for comp in f_st:
        far_max = float(np.max(np.abs(comp[far])))
        # ∇ψ ≈ δ_ε exp(-φ²/2ε²); at |φ|=5ε, δ_ε ~ exp(-12.5)/ε ≈ 0
        assert far_max < 1.0, f"Surface tension far-field contamination: {far_max:.3e}"


# ── Test 5: Predictor no NaN ──────────────────────────────────────────────

def test_predictor_no_nan(backend):
    """Predictor must not produce NaN for a simple flow."""
    from twophase.ns_terms.predictor import Predictor
    N = 16
    cfg = SimulationConfig(ndim=2, N=(N, N), L=(1.0, 1.0),
                           Re=10., Fr=1., We=5., cn_viscous=False)
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp
    pred = Predictor(backend, cfg)

    eps = 1.5 / N
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    psi = heaviside(xp, phi, eps)
    rho = 0.1 + 0.9 * psi
    mu  = 0.01 + 0.99 * psi

    curv_calc = CurvatureCalculator(backend, eps)
    kappa = curv_calc.compute(psi, ccd)

    u = np.zeros((N+1, N+1))
    v = np.zeros((N+1, N+1))

    vel_star = pred.compute([u, v], rho, mu, kappa, psi, ccd, dt=0.01)
    for ax, vs in enumerate(vel_star):
        assert not np.any(np.isnan(vs)), f"NaN in vel_star component {ax}"
