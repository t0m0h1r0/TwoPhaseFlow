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
from twophase.config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ns_terms.convection import ConvectionTerm
from twophase.ns_terms.viscous import ViscousTerm
from twophase.ns_terms.gravity import GravityTerm
from twophase.ns_terms.surface_tension import SurfaceTensionTerm
from twophase.ns_terms.context import NSComputeContext
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_setup(N=16, backend=None):
    if backend is None:
        backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(Re=10., Fr=1., We=5.),
    )
    grid = Grid(cfg.grid, backend)
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

    ctx = NSComputeContext(velocity=[u, v], ccd=ccd, rho=np.ones_like(u), mu=1.0)
    result = conv.compute(ctx)
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

    ctx = NSComputeContext(velocity=[u, v], ccd=ccd, rho=np.ones_like(u), mu=1.0)
    result = conv.compute(ctx)
    # -(u·∇)u = -u * ∂u/∂x = -x * 1 = -x
    expected = -X
    err = np.max(np.abs(result[0] - expected))
    assert err < 1e-8, f"Convection -(u·∇)u error {err:.2e}"


# ── Test 2: Viscous term ──────────────────────────────────────────────────

def test_viscous_laplacian_constant_mu(backend):
    """For μ=const, Re=1: ccd_bulk stress divergence matches 2Δu."""
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
    # ccd_bulk intentionally uses CCD only for Layer-A gradients, then returns
    # through a low-order physical-coordinate stress divergence.  The expected
    # accuracy here is the conservative body, not the old all-CCD chain.
    assert err < 6e-1, f"Viscous stress-divergence error {err:.2e}"


def test_viscous_legacy_all_ccd_laplacian_constant_mu(backend):
    """Legacy all-CCD stress/divergence path remains available for comparison."""
    cfg, grid, ccd, be = make_setup(N=32, backend=backend)
    visc = ViscousTerm(
        be,
        Re=1.0,
        cn_viscous=False,
        spatial_scheme="ccd_stress_legacy",
    )

    N = 32
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    u = np.sin(2 * np.pi * X)
    v = np.zeros_like(u)
    mu = np.ones_like(u)
    rho = np.ones_like(u)

    result = visc.compute_explicit([u, v], mu, rho, ccd)
    expected = 2.0 * (-(2 * np.pi)**2 * np.sin(2 * np.pi * X))
    err = np.max(np.abs(result[0][1:-1, 1:-1] - expected[1:-1, 1:-1]))
    assert err < 3e-2, f"Legacy CCD viscous error {err:.2e}"


def test_viscous_ccd_bulk_uses_laplacian_away_from_interface(backend):
    """When psi marks pure bulk, ccd_bulk uses the cheap μΔ_CCD path."""
    cfg, grid, ccd, be = make_setup(N=32, backend=backend)
    visc = ViscousTerm(be, Re=1.0, cn_viscous=False, spatial_scheme="ccd_bulk")

    N = 32
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    u = np.sin(2 * np.pi * X)
    v = np.zeros_like(u)
    mu = np.ones_like(u)
    rho = np.ones_like(u)
    psi = np.zeros_like(u)

    result = visc.compute_explicit([u, v], mu, rho, ccd, psi=psi)
    expected = -(2 * np.pi)**2 * np.sin(2 * np.pi * X)
    err = np.max(np.abs(result[0][1:-1, 1:-1] - expected[1:-1, 1:-1]))
    assert err < 3e-2, f"Bulk CCD Laplacian error {err:.2e}"


def test_viscous_ccd_bulk_uses_stress_form_in_interface_band(backend):
    """When psi marks interface, ccd_bulk keeps the stress-divergence path."""
    cfg, grid, ccd, be = make_setup(N=32, backend=backend)
    visc = ViscousTerm(be, Re=1.0, cn_viscous=False, spatial_scheme="ccd_bulk")
    ref = ViscousTerm(
        be,
        Re=1.0,
        cn_viscous=False,
        spatial_scheme="conservative_stress",
    )

    N = 32
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    u = np.sin(2 * np.pi * X)
    v = np.zeros_like(u)
    mu = np.ones_like(u)
    rho = np.ones_like(u)
    psi = 0.5 * np.ones_like(u)

    result = visc.compute_explicit([u, v], mu, rho, ccd, psi=psi)
    expected = ref.compute_explicit([u, v], mu, rho, ccd)
    err = np.max(np.abs(result[0] - expected[0]))
    assert err < 1e-14, f"Interface band did not use stress-divergence: {err:.2e}"


# ── Test 3: Gravity ───────────────────────────────────────────────────────

def test_gravity_direction(backend):
    """Gravity must act on the last spatial axis with correct sign."""
    cfg, grid, ccd, be = make_setup(backend=backend)
    grav = GravityTerm(be, Fr=1.0, ndim=2)

    rho = np.ones((17, 17))
    ctx = NSComputeContext(velocity=[np.zeros_like(rho), np.zeros_like(rho)], ccd=ccd, rho=rho, mu=1.0)
    g = grav.compute(ctx)

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
    ctx = NSComputeContext(velocity=[np.zeros_like(rho), np.zeros_like(rho)], ccd=ccd, rho=rho, mu=1.0)
    g = grav.compute(ctx)
    expected = -1.0 / (Fr ** 2)
    assert np.allclose(g[1], expected), f"Gravity scaling with Fr={Fr} failed"


# ── Test 4: Surface tension localisation ─────────────────────────────────

def test_surface_tension_localised(backend):
    """CSF force must be large only near the interface (|φ| < 3ε)."""
    N = 32
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(We=1.0),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    st = SurfaceTensionTerm(backend, We=1.0)
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.2
    psi = heaviside(xp, phi, eps)
    kappa = curv_calc.compute(psi)

    ctx = NSComputeContext(velocity=[np.zeros_like(psi), np.zeros_like(psi)], ccd=ccd, rho=np.ones_like(psi), mu=1.0, kappa=kappa, psi=psi)
    f_st = st.compute(ctx)

    # Far from interface (|φ| > 5ε) force should be negligible
    far = np.abs(phi) > 5 * eps
    for comp in f_st:
        far_max = float(np.max(np.abs(comp[far])))
        # ∇ψ ≈ δ_ε exp(-φ²/2ε²); at |φ|=5ε, δ_ε ~ exp(-12.5)/ε ≈ 0
        assert far_max < 1.0, f"Surface tension far-field contamination: {far_max:.3e}"


# ── Test 5: Predictor no NaN ──────────────────────────────────────────────

def test_predictor_no_nan(backend):
    """Predictor must not produce NaN for a simple flow."""
    from twophase.time_integration.ab2_predictor import Predictor
    N = 16
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(Re=10., Fr=1., We=5.),
        numerics=NumericsConfig(cn_viscous=False),
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp
    pred = Predictor(backend, cfg, ccd)

    eps = 1.5 / N
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    psi = heaviside(xp, phi, eps)
    rho = 0.1 + 0.9 * psi
    mu  = 0.01 + 0.99 * psi

    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa = curv_calc.compute(psi)

    u = np.zeros((N+1, N+1))
    v = np.zeros((N+1, N+1))

    from twophase.core.flow_state import FlowState
    state = FlowState(velocity=[u, v], psi=psi, rho=rho, mu=mu, kappa=kappa, pressure=np.zeros_like(psi))
    vel_star = pred.compute(state, dt=0.01)
    for ax, vs in enumerate(vel_star):
        assert not np.any(np.isnan(vs)), f"NaN in vel_star component {ax}"


# ── Test 6: PicardCNAdvance strategy extraction (Phase 1) ────────────────

def test_picard_cn_advance_matches_inlined_heun(backend):
    """PicardCNAdvance must reproduce the pre-Phase-1 Heun P-C formula
    bit-for-bit, both when called directly and when dispatched through
    ViscousTerm.apply_cn_predictor with the default strategy."""
    from twophase.time_integration.cn_advance import PicardCNAdvance
    cfg, grid, ccd, be = make_setup(N=16, backend=backend)
    visc = ViscousTerm(be, Re=10.0, cn_viscous=True)  # default strategy = PicardCNAdvance

    N = 16
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    u_old = [np.sin(np.pi * X) * np.cos(np.pi * Y),
             -np.cos(np.pi * X) * np.sin(np.pi * Y)]
    mu  = np.ones_like(X) * 0.01
    rho = 0.5 + 0.5 * np.sin(np.pi * X) * np.sin(np.pi * Y)
    explicit_rhs = [np.zeros_like(X), -rho * 1.0]  # gravity-only RHS
    dt = 0.005

    # (a) Delegated path through apply_cn_predictor
    out_delegated = visc.apply_cn_predictor(u_old, explicit_rhs, mu, rho, ccd, dt)

    # (b) Direct strategy invocation
    strat = PicardCNAdvance(be)
    out_direct = strat.advance(u_old, explicit_rhs, mu, rho, visc, ccd, dt)

    # (c) Manual Heun reference (frozen formula)
    visc_n = visc._evaluate(u_old, mu, rho, ccd)
    u_pred = [u_old[c] + dt*(explicit_rhs[c]/rho + visc_n[c]) for c in range(2)]
    visc_star = visc._evaluate(u_pred, mu, rho, ccd)
    out_manual = [
        u_old[c] + dt*(explicit_rhs[c]/rho + 0.5*visc_n[c] + 0.5*visc_star[c])
        for c in range(2)
    ]

    for c in range(2):
        assert np.array_equal(out_delegated[c], out_direct[c]), (
            f"Delegated != direct strategy (component {c})")
        assert np.array_equal(out_direct[c], out_manual[c]), (
            f"Strategy != manual Heun (component {c})")


def test_cn_mode_factory_picard(backend):
    """make_cn_advance('picard') returns a PicardCNAdvance."""
    from twophase.time_integration.cn_advance import make_cn_advance, PicardCNAdvance
    s = make_cn_advance(backend, "picard")
    assert isinstance(s, PicardCNAdvance)


def test_cn_mode_factory_richardson(backend):
    """make_cn_advance('richardson_picard') wraps PicardCNAdvance."""
    from twophase.time_integration.cn_advance import (
        make_cn_advance, RichardsonCNAdvance, PicardCNAdvance,
    )
    s = make_cn_advance(backend, "richardson_picard")
    assert isinstance(s, RichardsonCNAdvance)
    assert isinstance(s.base, PicardCNAdvance)


def test_cn_mode_factory_unknown_raises(backend):
    from twophase.time_integration.cn_advance import make_cn_advance
    with pytest.raises(ValueError, match="cn_mode"):
        make_cn_advance(backend, "wibble")


def test_richardson_cn_lifts_order_on_pure_diffusion(backend):
    """Self-similarity refinement-ratio test for temporal order.

    On pure diffusion (constant μ, ρ, no explicit_rhs), the spatial
    discretization error is identical for every run at fixed h, so it
    cancels in any difference between runs. The temporal error expansion is

        u(dt) - u_exact = C · dt^p + O(dt^{p+1})

    giving the self-similarity ratio

        r(dt, dt/2) = |u(dt) - u(dt/2)| / |u(dt/2) - u(dt/4)|
                    ≈ 2^p

    so p ≈ log2(r). This bypasses spatial error completely.

    Targets:
      Picard                : p ≈ 2 (1-step Picard / Heun)
      Richardson-Picard     : p ≈ 3 (NOT 4). Richardson extrapolation lifts
                              by +1 order for a general method and by +2
                              order only when the base is SYMMETRIC
                              (e.g. trapezoidal rule / true implicit CN /
                              Padé-(2,2)) whose error expansion is in
                              EVEN powers of Δt. Heun is an explicit 2-stage
                              RK and is not symmetric; its expansion has all
                              powers, so only the leading Δt^2 term is
                              annihilated. See docs/memo/extended_cn_impl_
                              design.md §5.2 + Phase 2 note.

    The full O(Δt^4) will arrive in Phase 3 (true ImplicitCNAdvance) or
    Phase 4 (Pade22CNAdvance); Phase 6 composes Richardson on those to
    raise the global NS cross-term order.
    """
    from twophase.time_integration.cn_advance import PicardCNAdvance, RichardsonCNAdvance
    import math

    N = 16
    L = 1.0
    nu = 0.05
    cfg, grid, ccd, be = make_setup(N=N, backend=backend)
    visc = ViscousTerm(be, Re=1.0 / nu, cn_viscous=True)

    X, Y = np.meshgrid(np.linspace(0, L, N+1), np.linspace(0, L, N+1),
                       indexing='ij')
    u0 = np.sin(np.pi * X) * np.sin(np.pi * Y)  # zero at walls

    t_end = 0.02
    # dt sweep: 4 entries, each a halving. Pick the dts small enough to stay
    # below explicit viscous CFL h^2/(4·nu) ≈ 1/(4·16²·0.05) ≈ 2e-2.
    dts = [t_end / n for n in (4, 8, 16, 32)]

    def run(strategy, dt):
        u = [u0.copy(), np.zeros_like(X)]
        mu = np.ones_like(X)
        rho = np.ones_like(X)
        rhs = [np.zeros_like(X), np.zeros_like(X)]
        nsteps = int(round(t_end / dt))
        for _ in range(nsteps):
            u = strategy.advance(u, rhs, mu, rho, visc, ccd, dt)
        return u[0]

    picard = PicardCNAdvance(be)
    richardson = RichardsonCNAdvance(picard)

    sl = (slice(2, -2), slice(2, -2))  # avoid CCD boundary contamination

    sols_p = [run(picard,     dt)[sl] for dt in dts]
    sols_r = [run(richardson, dt)[sl] for dt in dts]

    # Self-similarity differences (same h, so spatial error cancels)
    diffs_p = [float(np.max(np.abs(sols_p[i] - sols_p[i+1])))
               for i in range(len(dts) - 1)]
    diffs_r = [float(np.max(np.abs(sols_r[i] - sols_r[i+1])))
               for i in range(len(dts) - 1)]

    # Refinement ratio: diffs[i] / diffs[i+1] ≈ 2^p
    ratio_p = diffs_p[-2] / diffs_p[-1]
    ratio_r = diffs_r[-2] / diffs_r[-1]
    order_p = math.log2(ratio_p)
    order_r = math.log2(ratio_r)

    assert 1.6 < order_p < 2.6, (
        f"Picard self-similarity order {order_p:.2f} not ≈ 2, "
        f"diffs_p={diffs_p}")
    # Richardson on Heun (non-symmetric base) gains +1 order, not +2 → p ≈ 3
    assert 2.6 < order_r < 3.6, (
        f"Richardson-Picard self-similarity order {order_r:.2f} not ≈ 3, "
        f"diffs_r={diffs_r}")
    # Richardson's finest difference is strictly smaller than Picard's
    assert diffs_r[-1] < diffs_p[-1]
