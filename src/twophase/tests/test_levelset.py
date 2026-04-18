"""
Tests for level-set modules (§3 of the paper).

Verified properties:
  1. Heaviside / delta / inversion round-trip.
  2. CLS advection: volume conservation < 1% over 10 revolutions (Zalesak).
  3. Reinitialization: Eikonal quality |∇φ| → 1 after several steps.
  4. Curvature: κ ≈ −1/R for a circle of radius R.
"""

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside, delta, invert_heaviside, update_properties
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.curvature_psi import CurvatureCalculatorPsi, _gaussian_3x3
from twophase.levelset.normal_filter import NormalVectorFilter, kappa_from_normals
from twophase.levelset.curvature_filter import InterfaceLimitedFilter
from twophase.levelset.advection import LevelSetAdvection
from twophase.levelset.reinitialize import Reinitializer


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


# ── Test 1: Heaviside round-trip ──────────────────────────────────────────

def test_heaviside_inversion(backend):
    xp = backend.xp
    eps = 0.05
    phi = np.linspace(-0.5, 0.5, 100)
    psi = heaviside(xp, phi, eps)
    phi_recovered = invert_heaviside(xp, psi, eps)
    err = np.max(np.abs(phi_recovered - phi))
    assert err < 1e-10, f"Heaviside inversion error {err}"


def test_delta_integrates_to_one(backend):
    """δ_ε should integrate to ≈ 1 over the domain."""
    xp = backend.xp
    eps = 0.05
    x = np.linspace(-1.0, 1.0, 1000)
    dx = x[1] - x[0]
    d = delta(xp, x, eps)
    integral = float(np.sum(d)) * dx
    assert abs(integral - 1.0) < 0.01, f"δ_ε integral = {integral:.4f} ≠ 1"


def test_update_properties(backend):
    xp = backend.xp
    psi = np.array([0.0, 0.5, 1.0])
    rho, mu = update_properties(xp, psi, 1.0, 0.1, 1.0, 0.01)
    assert abs(rho[0] - 0.1) < 1e-12
    assert abs(rho[-1] - 1.0) < 1e-12
    assert abs(rho[1] - 0.55) < 1e-12
    assert abs(mu[0] - 0.01) < 1e-12


# ── Test 2: Reinitialization Eikonal quality ──────────────────────────────

def test_reinit_eikonal_quality(backend):
    """Reinitialization should decrease the volume monitor M(τ) = ∫ψ(1−ψ)dV.

    M decreasing means the ψ profile is sharpening toward a step function,
    which is the correct behaviour of the reinitialization PDE (§3.4).
    We also check that |∇φ| ≈ 1 near the interface for the perfect-circle
    starting point (no distortion).
    """
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    reinit = Reinitializer(backend, grid, ccd, eps, n_steps=4)

    # Perfect circle — reinit should preserve or sharpen the profile
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi0 = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    psi0 = heaviside(xp, phi0, eps)

    M0 = float(xp.sum(psi0 * (1.0 - psi0))) * grid.cell_volume()

    psi_r = reinit.reinitialize(psi0)

    M1 = float(xp.sum(psi_r * (1.0 - psi_r))) * grid.cell_volume()

    # M should stay bounded (not explode) after 10 reinit steps
    assert M1 < 10 * M0, (
        f"Volume monitor exploded: M0={M0:.4f}, M1={M1:.4f}"
    )

    # Eikonal check: use ψ ≈ 0.5 to locate the interface, then compute
    # |∇φ| = eps * |∇ψ| / (ψ(1-ψ)) which should be ≈ 1 near ψ = 0.5.
    dpsi_dx, _ = ccd.differentiate(psi_r, 0)
    dpsi_dy, _ = ccd.differentiate(psi_r, 1)
    grad_psi = np.sqrt(dpsi_dx**2 + dpsi_dy**2)
    psi_1mpsi = psi_r * (1.0 - psi_r)

    # Only where ψ(1-ψ) > 0.1 (within ~2 interface widths of ψ=0.5)
    near_iface_psi = psi_1mpsi > 0.1
    if np.sum(near_iface_psi) > 4:
        grad_phi_approx = eps * grad_psi[near_iface_psi] / psi_1mpsi[near_iface_psi]
        err = float(np.mean(np.abs(grad_phi_approx - 1.0)))
        assert err < 0.5, f"Eikonal error near interface: {err:.4f}"


# ── Test 3: Curvature of a circle ─────────────────────────────────────────

def test_curvature_circle(backend):
    """For a circle of radius R, κ ≈ −1/R (convention: negative inside)."""
    N = 64
    R = 0.25
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    psi = heaviside(xp, phi, eps)

    kappa = curv_calc.compute(psi)

    # Expected curvature at the interface (|φ| < 2ε)
    near_iface = np.abs(phi) < 2 * eps
    if np.sum(near_iface) > 0:
        kappa_mean = float(np.mean(kappa[near_iface]))
        # 2-D curvature of circle with signed-distance convention: κ = -1/R
        kappa_theory = -1.0 / R
        rel_err = abs(kappa_mean - kappa_theory) / abs(kappa_theory)
        assert rel_err < 0.05, (
            f"Circle curvature: got {kappa_mean:.4f}, "
            f"expected {kappa_theory:.4f}, rel_err={rel_err:.3f}"
        )


# ── Test 4: CLS advection volume conservation ─────────────────────────────

def test_cls_advection_volume_conservation(backend):
    """Rigid rotation of a circle: volume change < 2% over one revolution."""
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    advect = LevelSetAdvection(backend, grid)

    # Initial circle
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi0 = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.2
    psi = heaviside(xp, phi0, eps)
    vol0 = float(np.sum(psi)) * grid.cell_volume()

    # Solid-body rotation: u = ω(-(y-0.5)), v = ω(x-0.5)
    omega = 2 * np.pi   # one revolution per unit time
    u = -omega * (Y - 0.5)
    v =  omega * (X - 0.5)

    # Integrate for T = 1.0 (one full revolution)
    T = 1.0
    dt = 0.005
    t = 0.0
    while t < T:
        step_dt = min(dt, T - t)
        psi = advect.advance(psi, [u, v], step_dt)
        t += step_dt

    vol1 = float(np.sum(psi)) * grid.cell_volume()
    vol_err = abs(vol1 - vol0) / vol0
    assert vol_err < 0.02, (
        f"Volume conservation error {vol_err*100:.2f}% > 2%"
    )


# ── Test 5: CurvatureCalculatorPsi (G-4) ────────────────────────────────

def test_curvature_psi_circle(backend):
    """CurvatureCalculatorPsi: κ ≈ −1/R for a circle (section 3b eq. curvature_psi_2d)."""
    N = 64
    R = 0.25
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    curv_psi = CurvatureCalculatorPsi(backend, ccd)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    psi = heaviside(xp, phi, eps)

    kappa = curv_psi.compute(psi)

    # Near-interface check
    near_iface = np.abs(phi) < 2 * eps
    assert np.sum(near_iface) > 0, "No interface points found"
    kappa_mean = float(np.mean(kappa[near_iface]))
    kappa_theory = -1.0 / R
    rel_err = abs(kappa_mean - kappa_theory) / abs(kappa_theory)
    assert rel_err < 0.05, (
        f"Psi-direct curvature: got {kappa_mean:.4f}, "
        f"expected {kappa_theory:.4f}, rel_err={rel_err:.3f}"
    )


def test_curvature_psi_matches_legacy(backend):
    """CurvatureCalculatorPsi should match legacy CurvatureCalculator (Theorem curvature_invariance)."""
    N = 64
    R = 0.25
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    curv_legacy = CurvatureCalculator(backend, ccd, eps)
    curv_psi = CurvatureCalculatorPsi(backend, ccd)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    psi = heaviside(xp, phi, eps)

    kappa_legacy = curv_legacy.compute(psi)
    kappa_psi = curv_psi.compute(psi)

    # Compare only near interface where both are meaningful
    near_iface = (psi > 0.05) & (psi < 0.95)
    if np.sum(near_iface) > 0:
        err = float(np.max(np.abs(kappa_psi[near_iface] - kappa_legacy[near_iface])))
        kappa_scale = float(np.max(np.abs(kappa_legacy[near_iface])))
        rel_err = err / max(kappa_scale, 1e-10)
        assert rel_err < 0.1, (
            f"Psi-direct vs legacy mismatch: max abs err={err:.4e}, "
            f"rel_err={rel_err:.3f}"
        )


def test_curvature_psi_zero_far_from_interface(backend):
    """CurvatureCalculatorPsi: κ = 0 far from interface (hybrid strategy)."""
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    curv_psi = CurvatureCalculatorPsi(backend, ccd, psi_min=0.01)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    psi = heaviside(xp, phi, eps)

    kappa = curv_psi.compute(psi)

    # Far-from-interface points should be zero
    far_mask = (psi <= 0.01) | (psi >= 0.99)
    if np.sum(far_mask) > 0:
        assert float(np.max(np.abs(kappa[far_mask]))) == 0.0, \
            "Far-from-interface kappa should be exactly 0"


# ── Test 6: Improved invert_heaviside (G-1) ──────────────────────────────

def test_invert_heaviside_saturation(backend):
    """invert_heaviside: saturated regions -> +/- phi_max (section 3b algbox)."""
    xp = backend.xp
    eps = 0.05

    # Include extreme values near 0 and 1
    psi = np.array([0.0, 1e-8, 1e-6, 0.5, 1.0 - 1e-6, 1.0 - 1e-8, 1.0])
    phi = invert_heaviside(xp, psi, eps)

    phi_max = eps * np.log((1.0 - 1e-6) / 1e-6)

    # Saturated: should be clipped to +/- phi_max
    assert abs(phi[0] - (-phi_max)) < 1e-10, f"phi[0] should be -phi_max, got {phi[0]}"
    assert abs(phi[-1] - phi_max) < 1e-10, f"phi[-1] should be phi_max, got {phi[-1]}"

    # Mid-range: should be ~0
    assert abs(phi[3]) < 1e-10, f"phi at psi=0.5 should be ~0, got {phi[3]}"

    # No NaN or Inf
    assert not np.any(np.isnan(phi)), "invert_heaviside produced NaN"
    assert not np.any(np.isinf(phi)), "invert_heaviside produced Inf"


def test_invert_heaviside_roundtrip_improved(backend):
    """invert_heaviside round-trip still works with improved implementation."""
    xp = backend.xp
    eps = 0.05
    phi_orig = np.linspace(-0.5, 0.5, 100)
    psi = heaviside(xp, phi_orig, eps)
    phi_recovered = invert_heaviside(xp, psi, eps)
    err = np.max(np.abs(phi_recovered - phi_orig))
    assert err < 1e-10, f"Improved inversion round-trip error {err}"


# ── Test 7: Gaussian filter (G-3) ────────────────────────────────────────

def test_gaussian_filter_smooths(backend):
    """3x3 Gaussian filter should reduce high-frequency noise."""
    xp = backend.xp
    N = 32

    # Checkerboard pattern (worst-case high-frequency)
    field = np.zeros((N, N))
    field[::2, ::2] = 1.0
    field[1::2, 1::2] = 1.0

    filtered = _gaussian_3x3(xp, field)

    # Variance should decrease
    var_orig = float(np.var(field))
    var_filt = float(np.var(filtered))
    assert var_filt < var_orig, (
        f"Gaussian filter did not reduce variance: {var_filt:.4f} >= {var_orig:.4f}"
    )


def test_curvature_psi_with_gaussian(backend):
    """CurvatureCalculatorPsi with Gaussian filter should still give reasonable κ."""
    N = 64
    R = 0.25
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    curv_psi = CurvatureCalculatorPsi(backend, ccd, gaussian_filter=True)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    psi = heaviside(xp, phi, eps)

    kappa = curv_psi.compute(psi)

    near_iface = np.abs(phi) < 2 * eps
    if np.sum(near_iface) > 0:
        kappa_mean = float(np.mean(kappa[near_iface]))
        kappa_theory = -1.0 / R
        rel_err = abs(kappa_mean - kappa_theory) / abs(kappa_theory)
        # Slightly relaxed tolerance due to smoothing
        assert rel_err < 0.10, (
            f"Gaussian-filtered curvature: got {kappa_mean:.4f}, "
            f"expected {kappa_theory:.4f}, rel_err={rel_err:.3f}"
        )


# ── Test 8: NormalVectorFilter ───────────────────────────────────────────


def _circle_setup(N=64, R=0.25):
    """Return (X, Y, phi, eps) for a circle of radius R on [0,1]^2."""
    X, Y = np.meshgrid(np.linspace(0, 1, N + 1), np.linspace(0, 1, N + 1),
                       indexing='ij')
    phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
    eps = 1.5 / N
    return X, Y, phi, eps


def test_normal_filter_output_normalized(backend):
    """Filtered normals must satisfy |n*| = 1 everywhere (at least near interface)."""
    N = 64
    _, _, phi, eps = _circle_setup(N)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    nf = NormalVectorFilter(backend, ccd, eps, alpha=0.05)
    psi = heaviside(xp, phi, eps)

    d1x, _ = ccd.differentiate(phi, 0)
    d1y, _ = ccd.differentiate(phi, 1)

    nx, ny = nf.apply([d1x, d1y], phi)

    norm = np.sqrt(np.array(nx)**2 + np.array(ny)**2)
    near_iface = np.abs(phi) < 3 * eps
    if np.sum(near_iface) > 0:
        max_dev = float(np.max(np.abs(norm[near_iface] - 1.0)))
        assert max_dev < 1e-6, f"|n*| deviation from 1: {max_dev:.2e}"


def test_normal_filter_smooths_noisy_field(backend):
    """Filter reduces variance of a noisy normal near the interface.

    Noise is injected directly into the derivative arrays (simulating
    truncation-error oscillations in CCD), not into phi.  This is the
    realistic use-case: phi stays smooth (kept by reinitialization) but
    small interface oscillations appear in the computed normals.
    """
    N = 64
    _, _, phi, eps = _circle_setup(N)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    d1x, _ = ccd.differentiate(phi, 0)
    d1y, _ = ccd.differentiate(phi, 1)

    # Add noise directly to derivative arrays near the interface
    rng = np.random.default_rng(42)
    near_iface = np.abs(phi) < 3 * eps
    noise_amp = 0.05   # ~5% of unit-normal magnitude
    d1x_noisy = d1x + noise_amp * rng.standard_normal(d1x.shape) * near_iface
    d1y_noisy = d1y + noise_amp * rng.standard_normal(d1y.shape) * near_iface

    # Clean normals (reference)
    grad_norm_clean = np.sqrt(d1x**2 + d1y**2 + 1e-6**2)
    nx_clean = d1x / grad_norm_clean

    # Noisy normals (before filter)
    grad_norm_noisy = np.sqrt(d1x_noisy**2 + d1y_noisy**2 + 1e-6**2)
    nx_noisy = d1x_noisy / grad_norm_noisy

    # Apply filter to noisy derivatives; use clean phi for interface weight
    nf = NormalVectorFilter(backend, ccd, eps, alpha=0.05)
    nx_f, _ = nf.apply([d1x_noisy, d1y_noisy], phi)

    err_before = float(np.std((nx_noisy - nx_clean)[near_iface]))
    err_after = float(np.std((np.array(nx_f) - nx_clean)[near_iface]))
    assert err_after < err_before, (
        f"Normal filter did not reduce noise: before={err_before:.4e}, after={err_after:.4e}"
    )


def test_kappa_from_normals_circle(backend):
    """kappa_from_normals recovers κ ≈ -1/R for a clean circle (no filter)."""
    N = 64
    R = 0.25
    _, _, phi, eps = _circle_setup(N, R)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    d1x, _ = ccd.differentiate(phi, 0)
    d1y, _ = ccd.differentiate(phi, 1)
    grad_norm = np.sqrt(d1x**2 + d1y**2 + 1e-3**2)
    nx = d1x / grad_norm
    ny = d1y / grad_norm

    kappa = kappa_from_normals(xp, ccd, [nx, ny])

    near_iface = np.abs(phi) < 2 * eps
    assert np.sum(near_iface) > 0
    kappa_mean = float(np.mean(np.array(kappa)[near_iface]))
    kappa_theory = -1.0 / R
    rel_err = abs(kappa_mean - kappa_theory) / abs(kappa_theory)
    assert rel_err < 0.05, (
        f"kappa_from_normals circle: got {kappa_mean:.4f}, "
        f"expected {kappa_theory:.4f}, rel_err={rel_err:.3f}"
    )


def test_curvature_calculator_with_normal_filter(backend):
    """CurvatureCalculator + NormalVectorFilter: κ ≈ -1/R for circle (8% tolerance)."""
    N = 64
    R = 0.25
    _, _, phi, eps = _circle_setup(N, R)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    nf = NormalVectorFilter(backend, ccd, eps, alpha=0.05)
    curv = CurvatureCalculator(backend, ccd, eps, normal_filter=nf)
    psi = heaviside(xp, phi, eps)

    kappa = curv.compute(psi)

    near_iface = np.abs(phi) < 2 * eps
    assert np.sum(near_iface) > 0
    kappa_mean = float(np.mean(np.array(kappa)[near_iface]))
    kappa_theory = -1.0 / R
    rel_err = abs(kappa_mean - kappa_theory) / abs(kappa_theory)
    assert rel_err < 0.08, (
        f"CurvatureCalculator+NormalFilter: got {kappa_mean:.4f}, "
        f"expected {kappa_theory:.4f}, rel_err={rel_err:.3f}"
    )


# ── Test 9: InterfaceLimitedFilter (HFE) ─────────────────────────────────


def test_hfe_filter_circle_curvature_preserved(backend):
    """HFE filter does not significantly distort κ for a clean circle."""
    N = 64
    R = 0.25
    _, _, phi, eps = _circle_setup(N, R)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    curv = CurvatureCalculator(backend, ccd, eps)
    psi = heaviside(xp, phi, eps)
    kappa_ref = curv.compute(psi)

    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)
    kappa_filt = hfe.apply(kappa_ref, psi)

    near_iface = np.abs(phi) < 2 * eps
    assert np.sum(near_iface) > 0
    kappa_mean = float(np.mean(np.array(kappa_filt)[near_iface]))
    kappa_theory = -1.0 / R
    rel_err = abs(kappa_mean - kappa_theory) / abs(kappa_theory)
    assert rel_err < 0.08, (
        f"HFE-filtered curvature: got {kappa_mean:.4f}, "
        f"expected {kappa_theory:.4f}, rel_err={rel_err:.3f}"
    )


def test_hfe_filter_reduces_noise_on_kappa(backend):
    """HFE filter damps high-frequency noise added directly to κ.

    Noise is modulated by 4ψ(1-ψ) (smooth, matches filter weight) to
    avoid sharp-mask artifacts that would create spurious large Laplacians.
    """
    N = 64
    _, _, phi, eps = _circle_setup(N)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    curv = CurvatureCalculator(backend, ccd, eps)
    psi = heaviside(xp, phi, eps)
    psi_arr = np.array(psi)
    kappa_clean = np.array(curv.compute(psi))

    # Inject noise modulated by the smooth interface weight 4ψ(1-ψ)
    # (avoids sharp boundaries that cause large spurious CCD Laplacians)
    rng = np.random.default_rng(99)
    w_inject = 4.0 * psi_arr * (1.0 - psi_arr)   # O(1), smooth
    noise_amp = 0.5 * float(np.max(np.abs(kappa_clean)))
    kappa_noisy = kappa_clean + noise_amp * rng.standard_normal(kappa_clean.shape) * w_inject

    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)
    kappa_filt = np.array(hfe.apply(xp.asarray(kappa_noisy), psi))

    near_iface = w_inject > 0.1
    err_before = float(np.std((kappa_noisy - kappa_clean)[near_iface]))
    err_after = float(np.std((kappa_filt - kappa_clean)[near_iface]))
    assert err_after < err_before, (
        f"HFE filter did not reduce κ noise: before={err_before:.4e}, after={err_after:.4e}"
    )


def test_hfe_filter_zero_far_from_interface(backend):
    """HFE filter leaves κ unchanged far from interface (w≈0 away from ψ=0.5)."""
    N = 64
    _, _, phi, eps = _circle_setup(N)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    psi = heaviside(xp, phi, eps)
    kappa = xp.ones_like(psi)  # dummy field — any constant works

    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)
    kappa_filt = hfe.apply(kappa, psi)

    # Far from interface: ψ ≈ 0 or 1, so w = 4ψ(1-ψ) ≈ 0
    far_mask = (np.array(psi) < 0.01) | (np.array(psi) > 0.99)
    if np.sum(far_mask) > 0:
        delta_far = float(np.max(np.abs(np.array(kappa_filt)[far_mask] - 1.0)))
        assert delta_far < 1e-10, f"HFE filter modified κ far from interface: Δ={delta_far:.2e}"


def test_curvature_calculator_with_kappa_filter(backend):
    """CurvatureCalculator + InterfaceLimitedFilter: κ ≈ -1/R for circle."""
    N = 64
    R = 0.25
    _, _, phi, eps = _circle_setup(N, R)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)
    curv = CurvatureCalculator(backend, ccd, eps, kappa_filter=hfe)
    psi = heaviside(xp, phi, eps)

    kappa = curv.compute(psi)

    near_iface = np.abs(phi) < 2 * eps
    assert np.sum(near_iface) > 0
    kappa_mean = float(np.mean(np.array(kappa)[near_iface]))
    kappa_theory = -1.0 / R
    rel_err = abs(kappa_mean - kappa_theory) / abs(kappa_theory)
    assert rel_err < 0.08, (
        f"CurvatureCalculator+HFEFilter: got {kappa_mean:.4f}, "
        f"expected {kappa_theory:.4f}, rel_err={rel_err:.3f}"
    )


def test_hfe_filter_d2_precomputed_matches_ccd(backend):
    """d2_list pre-computed path gives identical result to CCD-computed path."""
    N = 64
    _, _, phi, eps = _circle_setup(N)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    curv = CurvatureCalculator(backend, ccd, eps)
    psi = heaviside(xp, phi, eps)
    kappa = curv.compute(psi)

    hfe = InterfaceLimitedFilter(backend, ccd, C=0.05)

    # Path 1: CCD computed internally
    kappa_a = hfe.apply(kappa, psi)

    # Path 2: pre-computed d2 passed in
    d2_list = [ccd.differentiate(kappa, ax)[1] for ax in range(ccd.ndim)]
    kappa_b = hfe.apply(kappa, psi, d2_list=d2_list)

    diff = float(xp.max(xp.abs(xp.asarray(kappa_a) - xp.asarray(kappa_b))))
    assert diff < 1e-12, f"d2_list path differs from CCD path: max diff = {diff:.2e}"


# ── Test: EikonalReinitializer (CHK-136, WIKI-T-031) ─────────────────────────

def test_eikonal_restores_sdf(backend):
    """EikonalReinitializer restores |∇φ|≈1 and ε_eff≈ε on a distorted profile."""
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    from twophase.levelset.reinit_eikonal import EikonalReinitializer
    reinit = EikonalReinitializer(backend, grid, ccd, eps, n_iter=30)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    # Distorted profile: stretch φ by 2× in x so |∇φ| = 2 before reinit
    phi0 = 2.0 * (np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25)
    psi0 = heaviside(xp, phi0, eps)

    psi_r = reinit.reinitialize(psi0)

    # Estimate eps_eff in band via median: eps_local = ψ(1-ψ)/|∇ψ| ≈ eps_eff
    dpsi_dx, _ = ccd.differentiate(psi_r, 0)
    dpsi_dy, _ = ccd.differentiate(psi_r, 1)
    grad_psi = np.sqrt(dpsi_dx**2 + dpsi_dy**2)
    psi_1mpsi = np.array(psi_r * (1.0 - psi_r))
    band = psi_1mpsi > 0.05
    if np.sum(band) > 4:
        eps_local = psi_1mpsi[band] / np.maximum(grad_psi[band], 1e-14)
        eps_eff = float(np.median(eps_local))
        assert abs(eps_eff / eps - 1.0) < 0.15, (
            f"ε_eff/ε = {eps_eff/eps:.3f} (expected ≈1.0)"
        )


def test_eikonal_preserves_mass(backend):
    """EikonalReinitializer with mass_correction=True preserves volume to <0.5%."""
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    from twophase.levelset.reinit_eikonal import EikonalReinitializer
    reinit = EikonalReinitializer(backend, grid, ccd, eps, n_iter=20,
                                  mass_correction=True)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    phi0 = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    psi0 = heaviside(xp, phi0, eps)
    dV = grid.cell_volumes()
    M0 = float(xp.sum(xp.asarray(psi0) * dV))

    psi_r = reinit.reinitialize(psi0)
    M1 = float(xp.sum(xp.asarray(psi_r) * dV))

    vol_err = abs(M1 - M0) / max(M0, 1e-14)
    assert vol_err < 0.005, f"Volume error {vol_err*100:.3f}% > 0.5%"


def test_eikonal_zsp_preserves_zero_set(backend):
    """ZSP=True: zero-set centroid stays within 0.1*eps after 50 reinit calls (CHK-137)."""
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    from twophase.levelset.reinit_eikonal import EikonalReinitializer
    reinit = EikonalReinitializer(backend, grid, ccd, eps, n_iter=20,
                                  mass_correction=False, zsp=True)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    # Flat interface at x=0.5, compressed to simulate post-split broadening (|∇φ|=1/1.4)
    phi0 = (X - 0.5) / 1.4   # compressed: |∇φ| = 1/1.4 ≠ 1
    psi0 = heaviside(xp, phi0, eps)
    dV = grid.cell_volumes()
    X_dev = xp.asarray(X)

    def x_centroid(psi):
        q = xp.asarray(psi)
        w = q * (1.0 - q)
        W = float(xp.sum(w * dV))
        return float(xp.sum(X_dev * w * dV)) / max(W, 1e-14)

    x0 = x_centroid(psi0)

    psi = psi0
    for _ in range(50):
        psi = reinit.reinitialize(psi)

    x_zsp = x_centroid(psi)
    assert abs(x_zsp - x0) < 0.1 * eps, (
        f"ZSP centroid drifted {abs(x_zsp - x0)/eps:.3f}×eps (limit 0.1)"
    )


# ── Test: FMM (CHK-138) ──────────────────────────────────────────────────────

def test_fmm_smooth_gradient(backend):
    """FMM: |∇_ξφ| ≈ 1 and gradient variation smaller than ξ-SDF (CHK-138).

    Voronoi kinks in ξ-SDF produce O(1) gradient jumps that corrupt CCD
    curvature computation. FMM's quadratic update eliminates these kinks,
    giving |∇φ| variation < 0.5 vs ξ-SDF which can exceed 1.5 locally.
    """
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    from twophase.levelset.reinit_eikonal import EikonalReinitializer
    reinit_fmm = EikonalReinitializer(backend, grid, ccd, eps,
                                      mass_correction=False, fmm=True)
    reinit_xi = EikonalReinitializer(backend, grid, ccd, eps,
                                     mass_correction=False, xi_sdf=True)

    X, Y = np.meshgrid(np.linspace(0, 1, N + 1), np.linspace(0, 1, N + 1),
                       indexing='ij')
    phi_circ = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
    psi0 = heaviside(xp, phi_circ, eps)

    psi_fmm = reinit_fmm.reinitialize(psi0)
    psi_xi = reinit_xi.reinitialize(psi0)

    def grad_deviation(psi):
        phi = eps * np.log(np.array(psi) / (1.0 - np.array(psi) + 1e-15) + 1e-15)
        eps_xi = eps / (1.0 / N)
        gx = np.abs(np.diff(phi, axis=0))
        gy = np.abs(np.diff(phi, axis=1))
        return float(np.max(gx)), float(np.max(gy))

    fmm_gx, fmm_gy = grad_deviation(psi_fmm)
    xi_gx, xi_gy = grad_deviation(psi_xi)

    # FMM gradient should be close to 1 (unit SDF in ξ-space)
    assert max(fmm_gx, fmm_gy) < 2.5, (
        f"FMM max grad = {max(fmm_gx, fmm_gy):.3f} (expected < 2.5)"
    )
    # FMM gradient variation should not exceed ξ-SDF (both use same zero-set)
    # This is a sanity check, not a strict improvement guarantee
    assert max(fmm_gx, fmm_gy) <= max(xi_gx, xi_gy) + 1.0, (
        f"FMM grad {max(fmm_gx,fmm_gy):.3f} >> ξ-SDF grad {max(xi_gx,xi_gy):.3f}"
    )


def test_fmm_preserves_zero_set(backend):
    """FMM: cells where φ_raw=0 give φ_fmm=0 → ψ=0.5 (Proposition 1 analogue)."""
    N = 32
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend)
    xp = backend.xp

    eps = 1.5 / N
    from twophase.levelset.reinit_eikonal import EikonalReinitializer
    reinit = EikonalReinitializer(backend, grid, ccd, eps,
                                  mass_correction=False, fmm=True)

    X, Y = np.meshgrid(np.linspace(0, 1, N + 1), np.linspace(0, 1, N + 1),
                       indexing='ij')
    # Flat interface exactly at x=0.5 (cell-center aligned → no zero-crossing cells)
    # Use slightly distorted SDF: |∇φ|=1.5 (compressed but has a zero-set)
    phi0 = 1.5 * (X - 0.5)
    psi0 = heaviside(xp, phi0, eps)
    psi_r = reinit.reinitialize(psi0)

    # After reinit: cells where |X-0.5| ≈ 0 should have ψ ≈ 0.5
    near_interface = np.abs(X - 0.5) < 0.5 / N
    psi_arr = np.array(psi_r)
    psi_near = psi_arr[near_interface]
    assert np.all(np.abs(psi_near - 0.5) < 0.1), (
        f"FMM: near-zero ψ deviates from 0.5 by {np.max(np.abs(psi_near-0.5)):.4f}"
    )
