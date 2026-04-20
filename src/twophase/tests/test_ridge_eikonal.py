"""Unit tests for Ridge-Eikonal non-uniform reinitializer (CHK-159).

Covers V1 ridge topology, V2 sigma_eff convergence, V3 non-uniform FMM
residual, V5 CPU/GPU parity. V4 volume and V6 backward-compat land in a
second pass once the builder / config wire-up is live.
"""

from __future__ import annotations

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.ridge_eikonal import (
    NonUniformFMM,
    RidgeExtractor,
    RidgeEikonalReinitializer,
)


# ── fixtures & helpers ──────────────────────────────────────────────────

@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def _mk_grid(n=64, L=1.0, alpha=1.0, backend=None):
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(n, n), L=(L, L), alpha_grid=alpha)
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    if alpha > 1.0:
        x = np.linspace(0.0, L, n + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")
        phi0 = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - 0.25
        eps = 1.5 * (L / n)
        psi0 = 1.0 / (1.0 + np.exp(-phi0 / eps))
        grid.update_from_levelset(psi0, eps=eps, ccd=ccd)
    return grid, ccd


def _phi_circle(grid, cx, cy, R):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    return np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - R


# ── V1 — ridge topology (two disks vs merged) ──────────────────────────

def test_ridge_topology_two_disks(backend):
    grid, _ = _mk_grid(n=64, L=1.0, alpha=1.0, backend=backend)
    phi_a = _phi_circle(grid, 0.30, 0.5, 0.15)
    phi_b = _phi_circle(grid, 0.70, 0.5, 0.15)
    phi_union = np.minimum(phi_a, phi_b)  # two disconnected disks

    ext = RidgeExtractor(backend, grid, sigma_0=3.0)
    xi = ext.compute_xi_ridge(phi_union)
    assert np.all(np.isfinite(np.asarray(xi))), "xi_ridge must be finite"
    mask = np.asarray(ext.extract_ridge_mask(xi))
    assert mask.any(), "two disks should yield a non-empty ridge mask"
    # A ridge mask with two disconnected disks should touch both halves.
    left  = mask[:, :33].sum()
    right = mask[:, 32:].sum()
    assert left > 0 and right > 0, (
        f"ridge should appear under both disks (left={left}, right={right})"
    )


def test_ridge_topology_single_merged_disk(backend):
    grid, _ = _mk_grid(n=64, L=1.0, alpha=1.0, backend=backend)
    phi = _phi_circle(grid, 0.5, 0.5, 0.25)  # single disk
    ext = RidgeExtractor(backend, grid, sigma_0=3.0)
    xi = ext.compute_xi_ridge(phi)
    mask = np.asarray(ext.extract_ridge_mask(xi))
    # A single convex region must produce a non-empty ridge concentrated near the centre.
    assert mask.any(), "single disk should yield a non-empty ridge mask"
    ii, jj = np.where(mask)
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    cx = x[ii].mean()
    cy = y[jj].mean()
    assert abs(cx - 0.5) < 0.1 and abs(cy - 0.5) < 0.1, (
        f"ridge centroid ({cx:.3f}, {cy:.3f}) should be near (0.5, 0.5)"
    )


# ── V2 — sigma_eff spatial scaling under alpha=2 stretching ────────────

def test_sigma_eff_convergence_alpha2(backend):
    """sigma_eff(x) tracks h(x)·sigma_0/h_ref exactly at every node."""
    grid, _ = _mk_grid(n=64, L=1.0, alpha=2.0, backend=backend)
    sigma_0 = 3.0
    ext = RidgeExtractor(backend, grid, sigma_0=sigma_0)
    h_ref_exp = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
    hx = np.asarray(grid.h[0]).reshape(-1, 1)
    hy = np.asarray(grid.h[1]).reshape(1, -1)
    h_field = np.sqrt(hx * hy)
    sigma_expected = sigma_0 * h_field / h_ref_exp
    sigma_actual = np.asarray(ext.sigma_eff)
    err = np.max(np.abs(sigma_actual - sigma_expected))
    assert err < 1e-12, f"sigma_eff mismatch Linf={err:.3e}"
    # Stretching must produce spatial variation of sigma_eff.
    assert sigma_actual.max() / sigma_actual.min() > 1.1, (
        "alpha=2 should produce >10% spread in sigma_eff"
    )


# ── V3 — non-uniform FMM Eikonal residual on stretched grid ────────────

def _eikonal_residual_phys(phi, grid):
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    gx = np.zeros_like(phi)
    gy = np.zeros_like(phi)
    dx = np.diff(x)
    dy = np.diff(y)
    gx[1:-1, :] = (phi[2:, :] - phi[:-2, :]) / (dx[:-1] + dx[1:]).reshape(-1, 1)
    gy[:, 1:-1] = (phi[:, 2:] - phi[:, :-2]) / (dy[:-1] + dy[1:]).reshape(1, -1)
    # One-sided at boundaries.
    gx[0,  :] = (phi[1, :] - phi[0, :])  / dx[0]
    gx[-1, :] = (phi[-1, :] - phi[-2, :]) / dx[-1]
    gy[:, 0]  = (phi[:, 1] - phi[:, 0])  / dy[0]
    gy[:, -1] = (phi[:, -1] - phi[:, -2]) / dy[-1]
    return np.sqrt(gx * gx + gy * gy)


@pytest.mark.parametrize("alpha", [1.0, 2.0, 3.0])
def test_fmm_eikonal_residual(backend, alpha):
    """|grad_x phi_fmm| - 1 in physical space stays below a reasonable band.

    FMM is first-order accurate; we assert a band <0.35 excluding the
    interface and domain boundaries. Caustic cells are excluded via a
    trimming mask (phi close to zero).
    """
    grid, _ = _mk_grid(n=64, L=1.0, alpha=alpha, backend=backend)
    phi_exact = _phi_circle(grid, 0.5, 0.5, 0.25)
    fmm = NonUniformFMM(grid)
    phi_fmm = fmm.solve(phi_exact.copy())

    g_abs = _eikonal_residual_phys(phi_fmm, grid)
    # Exclude interface (where |phi| ≈ 0) and outer 2-node band.
    trim = np.ones_like(phi_fmm, dtype=bool)
    trim[:2, :] = False; trim[-2:, :] = False
    trim[:, :2] = False; trim[:, -2:] = False
    trim &= np.abs(phi_fmm) > 2.0 * float(np.min(grid.h[0]))
    res = np.abs(g_abs[trim] - 1.0)
    # Caustic-cell spikes are bounded to a few outliers (<0.5% of nodes).
    p99 = np.percentile(res, 99.0)
    assert p99 < 0.35, (
        f"alpha={alpha}: FMM Eikonal residual 99th pct too wide (p99={p99:.3f})"
    )
    # Mean residual should tighten further.
    assert res.mean() < 0.1, (
        f"alpha={alpha}: FMM mean Eikonal residual {res.mean():.3f} too high"
    )


def test_fmm_physical_coord_seeding(backend):
    """FMM distance at a node adjacent to the interface equals the
    physical-coordinate linear-interpolation seed (not an index fraction)."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=backend)
    # Interface at x=0.5 (axis-aligned plane, trivial to trace).
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi_in = X - 0.5
    fmm = NonUniformFMM(grid)
    phi_out = fmm.solve(phi_in)
    # For this field |phi| is the exact x-distance to the plane x=0.5.
    err = np.max(np.abs(np.abs(phi_out) - np.abs(phi_in)))
    # Axis-aligned 1-D interface + physical seeding: FMM should reconstruct
    # to machine precision (up to floating-point quadratic rounding ~1e-12).
    assert err < 1e-10, f"1D physical-seed reconstruction err={err:.3e}"


# ── V5 — CPU/GPU parity (CPU-only under this test; GPU gated elsewhere) ─

def test_sigma_eff_cpu_fuse_identity(backend):
    """On CPU backend, @_fuse must be identity — kernels produce the
    same values as a plain numpy expression."""
    grid, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=backend)
    ext = RidgeExtractor(backend, grid, sigma_0=3.0)
    hx = np.asarray(grid.h[0]).reshape(-1, 1)
    hy = np.asarray(grid.h[1]).reshape(1, -1)
    h_field = np.sqrt(hx * hy)
    h_ref = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
    sigma_expect = 3.0 * h_field / h_ref
    np.testing.assert_allclose(np.asarray(ext.sigma_eff), sigma_expect, rtol=0, atol=1e-14)


def test_reinit_preserves_shape(backend):
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    phi_exact = _phi_circle(grid, 0.5, 0.5, 0.25)
    eps = 1.5 * (1.0 / 32)
    psi = 1.0 / (1.0 + np.exp(-phi_exact / eps))
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps, sigma_0=3.0, eps_scale=1.4, mass_correction=True,
    )
    psi_out = reinit.reinitialize(psi)
    psi_out = np.asarray(psi_out)
    assert psi_out.shape == psi.shape
    assert np.all((psi_out >= -1e-6) & (psi_out <= 1.0 + 1e-6)), (
        f"psi out of [0,1]: min={psi_out.min()}, max={psi_out.max()}"
    )


# ── V4 — volume conservation (integration) ─────────────────────────────

@pytest.mark.parametrize("alpha", [1.0, 2.0])
def test_volume_conservation_single_step(backend, alpha):
    """One reinit pass on a static circle preserves volume within 5%."""
    grid, ccd = _mk_grid(n=64, L=1.0, alpha=alpha, backend=backend)
    phi_exact = _phi_circle(grid, 0.5, 0.5, 0.25)
    eps = 1.5 * float(np.min(grid.h[0]))
    psi = 1.0 / (1.0 + np.exp(-phi_exact / eps))
    reinit = RidgeEikonalReinitializer(
        backend, grid, ccd, eps=eps, sigma_0=3.0, eps_scale=1.4, mass_correction=True,
    )
    dV = np.asarray(grid.cell_volumes())
    V_in = float(np.sum(np.asarray(psi) * dV))
    psi_out = np.asarray(reinit.reinitialize(psi))
    V_out = float(np.sum(psi_out * dV))
    rel = abs(V_out - V_in) / max(abs(V_in), 1e-30)
    assert rel < 0.05, f"alpha={alpha}: volume drift {rel*100:.2f}% > 5%"


# ── V6 — backward compatibility via builder (default='split') ──────────

def test_backcompat_default_is_split():
    """NumericsConfig default reinit_method must remain 'split'."""
    from twophase.config import NumericsConfig
    nc = NumericsConfig()
    assert nc.reinit_method == "split"
    assert nc.ridge_sigma_0 == 3.0


def test_backcompat_builder_default_builds_split(backend):
    """Building the Reinitializer facade with defaults picks SplitReinitializer."""
    from twophase.levelset.reinitialize import Reinitializer
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    eps = 1.5 * (1.0 / 32)
    r = Reinitializer(backend, grid, ccd, eps, n_steps=4, bc="neumann")
    # Strategy instance should be SplitReinitializer (no ridge side-effects).
    from twophase.levelset.reinit_split import SplitReinitializer
    assert isinstance(r._strategy, SplitReinitializer)


def test_builder_registers_ridge_eikonal(backend):
    """Explicit method='ridge_eikonal' picks RidgeEikonalReinitializer."""
    from twophase.levelset.reinitialize import Reinitializer
    grid, ccd = _mk_grid(n=32, L=1.0, alpha=1.0, backend=backend)
    eps = 1.5 * (1.0 / 32)
    r = Reinitializer(
        backend, grid, ccd, eps, n_steps=4, bc="neumann",
        method="ridge_eikonal", sigma_0=3.0,
    )
    assert isinstance(r._strategy, RidgeEikonalReinitializer)


@pytest.mark.gpu
def test_gpu_parity_ridge_kernels():
    """V5: CPU/GPU parity of fused kernels (gated behind --gpu)."""
    cpu = Backend(use_gpu=False)
    try:
        gpu = Backend(use_gpu=True)
    except Exception as e:
        pytest.skip(f"GPU backend unavailable: {e}")
    grid_cpu, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=cpu)
    grid_gpu, _ = _mk_grid(n=32, L=1.0, alpha=2.0, backend=gpu)
    ext_cpu = RidgeExtractor(cpu, grid_cpu, sigma_0=3.0)
    ext_gpu = RidgeExtractor(gpu, grid_gpu, sigma_0=3.0)
    s_cpu = np.asarray(ext_cpu.sigma_eff)
    s_gpu = ext_gpu.sigma_eff
    s_gpu = s_gpu.get() if hasattr(s_gpu, "get") else np.asarray(s_gpu)
    np.testing.assert_allclose(s_cpu, s_gpu, rtol=1e-12, atol=1e-14)
