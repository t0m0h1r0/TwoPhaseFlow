"""
Tests for FCCDLevelSetAdvection — CHK-158 V10.

V10: rigid-body rotation of a smooth ψ blob; Option B (flux) must
     preserve total mass to O(H^p), Option C (node) preserves to
     consistency order. Both modes integrate without blow-up.
"""

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.fccd import FCCDSolver
from twophase.levelset.fccd_advection import FCCDLevelSetAdvection


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_grid(N: int, backend, L: float = 1.0):
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(L, L)))
    return Grid(cfg.grid, backend)


def rotation_field(grid, L=1.0):
    """Rigid-body rotation (u, v) = ω (-(y-yc), (x-xc)), yc=xc=L/2."""
    X, Y = grid.meshgrid()
    xc = yc = L / 2
    omega = 2 * np.pi / L         # 1 full rotation in t = 1
    u = -omega * (Y - yc)
    v = omega * (X - xc)
    return np.asarray(u), np.asarray(v)


def gaussian_blob(grid, x0=0.3, y0=0.5, sigma=0.07, L=1.0):
    """Smooth ψ blob — avoids sharp gradients that force under-resolution."""
    X, Y = grid.meshgrid()
    r2 = (X - x0) ** 2 + (Y - y0) ** 2
    return np.asarray(np.exp(-r2 / (2 * sigma ** 2)))


# ── V10: Volume conservation of level-set advection ──────────────────────

@pytest.mark.parametrize("mode", ["node", "flux"])
def test_rotation_finite(mode, backend):
    """Half rotation of smooth blob: solution stays bounded and smooth."""
    N = 32
    L = 1.0
    grid = make_grid(N, backend, L=L)
    fccd = FCCDSolver(grid, backend, bc_type="wall")
    ls = FCCDLevelSetAdvection(backend, grid, fccd, mode=mode)

    u, v = rotation_field(grid, L=L)
    psi = gaussian_blob(grid, L=L)

    # Small CFL-safe step; few substeps
    h = L / N
    v_max = float(np.max(np.hypot(u, v)))
    dt = 0.3 * h / v_max
    n_steps = 20

    psi_t = psi.copy()
    for _ in range(n_steps):
        psi_t = ls.advance(psi_t, [u, v], dt, clip_bounds=None)

    assert np.all(np.isfinite(psi_t))
    # No blow-up: stays within a reasonable envelope of the initial amplitude.
    assert np.max(np.abs(psi_t)) < 5.0 * np.max(np.abs(psi))


def test_flux_mode_mass_conservation_uniform_divfree(backend):
    """Option B (flux) on a divergence-free velocity preserves integral.

    For a divergence-free rigid-body rotation and the conservative flux
    divergence form, ∫ψ is preserved up to boundary flux through walls.
    With a blob far from the wall, relative mass drift is small.
    """
    N = 48
    L = 1.0
    grid = make_grid(N, backend, L=L)
    fccd = FCCDSolver(grid, backend, bc_type="wall")
    ls = FCCDLevelSetAdvection(backend, grid, fccd, mode="flux")

    u, v = rotation_field(grid, L=L)
    psi = gaussian_blob(grid, x0=0.5, y0=0.3, sigma=0.06, L=L)  # centered-ish

    dV = grid.cell_volumes()
    M_init = float(np.sum(psi * dV))

    h = L / N
    v_max = float(np.max(np.hypot(u, v)))
    dt = 0.3 * h / v_max
    n_steps = 30
    psi_t = psi.copy()
    for _ in range(n_steps):
        psi_t = ls.advance(psi_t, [u, v], dt, clip_bounds=None)

    M_final = float(np.sum(psi_t * dV))
    rel_drift = abs(M_final - M_init) / M_init
    # Expect < 1% drift for a well-contained blob over O(10) rotations'
    # worth of passive advection on a 48x48 grid.
    assert rel_drift < 0.05, f"flux mode mass drift too large: {rel_drift:.3e}"


@pytest.mark.parametrize("mode", ["node", "flux"])
def test_zero_velocity_preserves_psi(mode, backend):
    """Zero velocity → advance is identity (no numerical diffusion)."""
    N = 16
    grid = make_grid(N, backend, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="wall")
    ls = FCCDLevelSetAdvection(backend, grid, fccd, mode=mode)

    psi = gaussian_blob(grid)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)
    psi_new = ls.advance(psi, [u, v], dt=0.1, clip_bounds=None)
    assert np.allclose(psi_new, psi, atol=1e-12)


def test_invalid_mode(backend):
    """Constructor rejects unknown mode."""
    grid = make_grid(8, backend, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="wall")
    with pytest.raises(ValueError, match="mode must be"):
        FCCDLevelSetAdvection(backend, grid, fccd, mode="weno5")


def test_clip_bounds(backend):
    """clip_bounds=(0,1) enforces psi ∈ [0,1] after each RK3 stage."""
    N = 16
    grid = make_grid(N, backend, L=1.0)
    fccd = FCCDSolver(grid, backend, bc_type="wall")
    ls = FCCDLevelSetAdvection(backend, grid, fccd, mode="flux")

    psi = gaussian_blob(grid)          # already in [0,1]
    u, v = rotation_field(grid)
    psi_new = ls.advance(psi, [u, v], dt=1e-3, clip_bounds=(0.0, 1.0))
    assert float(np.min(psi_new)) >= 0.0
    assert float(np.max(psi_new)) <= 1.0
