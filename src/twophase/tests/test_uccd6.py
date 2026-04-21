"""Tests for UCCD6 (sixth-order upwind CCD with hyperviscosity).

Verified properties (SP-H / WIKI-T-062):
  V1  apply_rhs operator is consistent with -a·D1^CCD u at σ → smooth-mode limit.
  V2  Convergence of ``apply_rhs`` on sin(2πx) is ≥ 5.5 (target O(h^6) from
      D1^CCD; hyperviscosity is O(h^7) subdominant).
  V3  Discrete energy ½||U||_h^2 decreases monotonically under RK3 integration.
  V4  Periodic long-time advection: error after one full period is O(h^6).
  V5  Hyperviscosity Fourier symbol ω_2(θ)^8 > 0 for θ ∈ (0, π] (dissipation).
"""

import numpy as np
import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.uccd6 import UCCD6Operator


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def cpu_backend():
    return Backend(use_gpu=False)


def make_grid_1d_like(N: int, backend, L: float = 1.0):
    """Build an (N+1)x5 quasi-1D grid for UCCD6 testing along axis 0.

    Uses 2-D grid to exercise batch handling of CCDSolver.
    """
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, 4), L=(L, 1.0))
    )
    return Grid(cfg.grid, backend)


# ── V1: operator consistency (hyperviscosity subdominant on smooth data) ──

def test_apply_rhs_matches_pure_advection_on_smooth(cpu_backend):
    """For σ = 1.0 and smooth data, ``apply_rhs`` ≈ -a·u' to within O(h^6).

    The hyperviscosity contribution is ~σ|a| h^7 k^8 on mode k; for N = 64
    and k = 2π this is ~10^-8 × k cos(kx) ≪ advection term.
    """
    N = 64
    L = 1.0
    a = 1.0
    sigma = 1.0

    grid = make_grid_1d_like(N, cpu_backend, L=L)
    op = UCCD6Operator(grid, cpu_backend, sigma=sigma, bc_type="periodic")

    x = np.asarray(grid.coords[0])
    u = np.sin(2 * np.pi * x)
    u2d = np.broadcast_to(u[:, None], (N + 1, 5)).copy()

    rhs = op.apply_rhs(u2d, axis=0, a=a)
    rhs_expected = -a * 2 * np.pi * np.cos(2 * np.pi * x)
    rhs_expected_2d = np.broadcast_to(rhs_expected[:, None], (N + 1, 5)).copy()

    err = float(np.max(np.abs(rhs - rhs_expected_2d)))
    assert err < 5e-6, f"err={err!r} too large for smooth advection"


# ── V2: convergence of apply_rhs on smooth data ─────────────────────────

def test_apply_rhs_convergence_rate(cpu_backend):
    """Spatial convergence of ``apply_rhs`` is ≥ 5.5 (target O(h^6))."""
    Ns = [16, 32, 64, 128]
    errs = []
    for N in Ns:
        L = 1.0
        grid = make_grid_1d_like(N, cpu_backend, L=L)
        op = UCCD6Operator(grid, cpu_backend, sigma=1.0, bc_type="periodic")
        x = np.asarray(grid.coords[0])
        u = np.sin(2 * np.pi * x)
        u2d = np.broadcast_to(u[:, None], (N + 1, 5)).copy()
        rhs = op.apply_rhs(u2d, axis=0, a=1.0)
        rhs_exact = -2 * np.pi * np.cos(2 * np.pi * x)
        rhs_exact_2d = np.broadcast_to(rhs_exact[:, None], (N + 1, 5)).copy()
        errs.append(float(np.max(np.abs(rhs - rhs_exact_2d))))

    slopes = [np.log2(errs[i] / errs[i + 1]) for i in range(len(Ns) - 1)]
    mean_slope = float(np.mean(slopes))
    assert mean_slope >= 5.5, f"slopes={slopes!r} mean={mean_slope!r}"


# ── V3: discrete L² energy monotonically decreases under RK3 ────────────

def test_energy_monotone_decrease(cpu_backend):
    """Under RK3 the discrete L^2 energy never increases (per SP-H §4).

    Explicit RK3 stability limit (SP-H §5 Remark): at the Nyquist the
    hyperviscosity eigenvalue is σ·ω_2(π)^8/h ≈ 8500σ/h; for RK3 we need
    dt·|λ| ≤ √3. With σ = O(1) and h = 1/64 this forces dt ≲ 3×10⁻⁶ — not
    useful for testing. CN is unconditionally stable but requires a GMRES
    setup; for RK3 we use the CFL-safe regime σ = h where hyperviscosity
    and advection have comparable time-step limits.
    """
    N = 64
    L = 1.0
    a = 1.0
    h = L / N
    # RK3 CFL: dt ≤ √3 h / (8500 σ); with dt = 0.4 h we need σ ≤ 5e-4.
    sigma = 1e-4
    dt = 0.4 * h / abs(a)

    grid = make_grid_1d_like(N, cpu_backend, L=L)
    op = UCCD6Operator(grid, cpu_backend, sigma=sigma, bc_type="periodic")

    x = np.asarray(grid.coords[0])
    # Superpose a well-resolved mode (k=2π) and an under-resolved mode
    # (k=8π near the upper half of the spectrum) so hyperviscosity activates.
    u = np.sin(2 * np.pi * x) + 0.5 * np.sin(8 * np.pi * x)
    u2d = np.broadcast_to(u[:, None], (N + 1, 5)).copy()

    n_steps = 40
    energies = [op.energy(u2d)]
    for _ in range(n_steps):
        u2d = op.rk3_step(u2d, axis=0, a=a, dt=dt)
        energies.append(op.energy(u2d))

    energies = np.asarray(energies)
    diffs = np.diff(energies)
    max_increase = float(np.max(diffs))
    assert max_increase <= 1e-10 * energies[0], (
        f"energy increased: max Δ = {max_increase!r}, E0 = {energies[0]!r}"
    )
    assert energies[-1] < energies[0]


# ── V4: long-time convergence (one full period, fixed σ) ────────────────

def test_periodic_advection_convergence(cpu_backend):
    """Advect sin(2πx) by one period; check error scales as ≥ O(h^5).

    Uses σ = 1e-3 (CFL-safe for explicit RK3 up to N=128) with
    dt = 0.4 h^2 / |a| so that RK3 temporal error ~ dt^3 ~ h^6 matches the
    spatial order. Hyperviscosity at smooth mode k=2π is ~σ·h^7·(2π)^8 — a
    factor of 1e-13 × (1/h)^7 — negligible for the smooth convergence test.
    """
    Ns = [16, 32, 64]
    errs = []
    for N in Ns:
        L = 1.0
        a = 1.0
        grid = make_grid_1d_like(N, cpu_backend, L=L)
        op = UCCD6Operator(grid, cpu_backend, sigma=1e-3, bc_type="periodic")
        x = np.asarray(grid.coords[0])
        u0 = np.sin(2 * np.pi * x)
        u = np.broadcast_to(u0[:, None], (N + 1, 5)).copy()

        h = L / N
        T = 1.0
        dt = 0.4 * h * h / abs(a)
        n_steps = int(np.ceil(T / dt))
        dt_adj = T / n_steps

        for _ in range(n_steps):
            u = op.rk3_step(u, axis=0, a=a, dt=dt_adj)

        u_exact = np.broadcast_to(u0[:, None], (N + 1, 5)).copy()
        errs.append(float(np.max(np.abs(u - u_exact))))

    slopes = [np.log2(errs[i] / errs[i + 1]) for i in range(len(Ns) - 1)]
    assert min(slopes) >= 4.5, f"slopes={slopes!r}, errs={errs!r}"


# ── V5: Fourier symbol positivity ────────────────────────────────────────

def test_hyperviscosity_symbol_nonpositive(cpu_backend):
    """Re λ(θ) from hyperviscosity is ≤ 0 for all θ, strict for θ ∈ (0, π]."""
    N = 64
    grid = make_grid_1d_like(N, cpu_backend)
    op = UCCD6Operator(grid, cpu_backend, sigma=1.0, bc_type="periodic")

    theta = np.linspace(-np.pi, np.pi, 2048, endpoint=True)
    sym = op.hyperviscosity_symbol(theta)
    sym = np.asarray(sym)
    assert float(np.max(sym)) <= 0.0
    # Strictly negative at Nyquist: ω_2(π)^2 = (81 + 48 - 33) / (48 - 40 + 2) = 96/10 = 9.6
    idx_pi = np.argmax(theta)
    assert sym[idx_pi] < -1e-3
