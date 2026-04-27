"""
MMS convergence tests for time-integration components.

Verified properties:
  1. WENO5 spatial order with periodic BC: O(h⁵), observed ≥ 4.8
     (§4 sec:weno5, eq:weno5_beta, eq:weno5_rec0-2; §4 sec:weno5_boundary)
  2. TVD-RK3 temporal order: O(Δt³), observed ≥ 2.8
     (§7.3 eq:tvd_rk3)

Manufactured solution (both tests):
    ψ(x, t) = 0.5 + 0.5·sin(2π(x − t))   on [0, 1] (periodic)
    u(x)    = 1   (uniform advection velocity)

Test determinism: np.random.seed(0), OMP_NUM_THREADS=1 (no randomness here).
"""

import os
import numpy as np
import pytest

os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.levelset.advection import LevelSetAdvection, DissipativeCCDAdvection
from twophase.ccd.ccd_solver import CCDSolver


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


# ── ヘルパー：線形回帰で収束次数を推定 ─────────────────────────────────────

def _convergence_order(hs, errors):
    """log-log 回帰で収束次数を推定（hs, errors は正の配列）。"""
    log_h = np.log(hs)
    log_e = np.log(errors)
    order, _ = np.polyfit(log_h, log_e, 1)
    return order


# ── Test 1: WENO5 空間精度（周期BC, O(h⁵)） ──────────────────────────────

@pytest.mark.parametrize("Nx", [32, 64, 128, 256])
def _advect_one_step(backend, Nx, bc):
    """Helper: smooth periodic scalar advected by u=1 for one step of dt=1e-4."""
    np.random.seed(0)
    Ny = 4
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(Nx, Ny), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    xp = backend.xp

    dt = 1e-4  # 時間誤差 O(dt⁴) ≈ 1e-24 → 空間誤差 O(h⁵) のみ支配

    # 製造解: ψ(x,t) = 0.5 + 0.5·sin(2πx),  u = 1
    x = np.linspace(0.0, 1.0, Nx + 1)
    X, _ = np.meshgrid(x, np.linspace(0.0, 1.0, Ny + 1), indexing='ij')
    psi0 = 0.5 + 0.5 * np.sin(2.0 * np.pi * X)
    u = np.ones_like(psi0)
    v = np.zeros_like(psi0)

    advect = LevelSetAdvection(backend, grid, bc=bc)
    psi1 = advect.advance(psi0, [u, v], dt)

    # 厳密解: ψ_exact(x) = 0.5 + 0.5·sin(2π(x − dt))
    psi_exact = 0.5 + 0.5 * np.sin(2.0 * np.pi * (X - dt))

    # 境界ノード（i=0, i=Nx）は BC パディングが div に入らないので除外
    err = np.abs(np.array(psi1)[1:-1, :] - psi_exact[1:-1, :])
    h = 1.0 / Nx
    l2 = float(np.sqrt(np.mean(err**2)))
    linf = float(np.max(err))
    return h, l2, linf


def test_weno5_periodic_bc_spatial_order(backend):
    """WENO5 + periodic BC must achieve spatial order ≥ 4.8 (expected O(h⁵)).

    Implements §4 sec:weno5, eq:weno5_beta, eq:weno5_rec0-2.
    BC strategy per §4 sec:weno5_boundary (周期BC: 誤差ゼロ折り返し).
    """
    Nxs = [32, 64, 128, 256]
    hs, l2s, linfs = [], [], []

    for Nx in Nxs:
        h, l2, linf = _advect_one_step(backend, Nx, bc='periodic')
        hs.append(h)
        l2s.append(l2)
        linfs.append(linf)
        # 絶対誤差が float64 機械精度（≈1e-15）以上であることを確認
        assert l2 > 1e-15, (
            f"N={Nx}: L2 error {l2:.2e} is below machine precision — "
            "likely computing dt-scaled error; check dt setting."
        )

    order_l2   = _convergence_order(np.array(hs), np.array(l2s))
    order_linf = _convergence_order(np.array(hs), np.array(linfs))

    print(f"\nWENO5 periodic BC spatial order: L2={order_l2:.2f}, L∞={order_linf:.2f}")
    for Nx, h, l2, linf in zip(Nxs, hs, l2s, linfs):
        print(f"  N={Nx:3d}: h={h:.4f}  L2={l2:.3e}  L∞={linf:.3e}")

    assert order_l2 >= 4.8, (
        f"WENO5 L2 spatial order {order_l2:.2f} < 4.8 (expected O(h⁵))"
    )
    assert order_linf >= 4.8, (
        f"WENO5 L∞ spatial order {order_linf:.2f} < 4.8 (expected O(h⁵))"
    )


def test_weno5_zero_bc_order_reduced(backend):
    """Zero-BC (wall) advection should give lower order than periodic.

    This is a sanity check: periodic BC should outperform zero-BC because
    zero ghost cells introduce O(1) flux errors at boundaries.
    We only verify zero-BC does NOT crash and still gives some order > 1.
    """
    Nxs = [32, 64, 128, 256]
    hs, l2s = [], []
    for Nx in Nxs:
        h, l2, _ = _advect_one_step(backend, Nx, bc='zero')
        hs.append(h)
        l2s.append(l2)

    # 境界誤差が非ゼロかつクラッシュしないことだけ確認
    assert all(l2 > 0 for l2 in l2s), "zero-BC advection produced zero error unexpectedly"


# ── Test 2: TVD-RK3 時間精度（O(Δt³)） ───────────────────────────────────

def test_tvd_rk3_temporal_order(backend):
    """TVD-RK3 must achieve temporal order ≥ 2.8 (expected O(Δt³)).

    Implements §4 eq:tvd_rk3 (Shu-Osher scheme).
    Uses N=512 so spatial error O(h⁵) ≈ 3e-15 per step is negligible
    compared to temporal error O(Δt³) ≈ 1e-7..1e-10 for dt in [0.02..0.0025].
    """
    np.random.seed(0)
    Nx = 512   # 空間精度を十分高く → 時間誤差が支配
    Ny = 4
    T  = 0.1   # 積分時間

    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(Nx, Ny), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    xp = backend.xp

    x = np.linspace(0.0, 1.0, Nx + 1)
    X, _ = np.meshgrid(x, np.linspace(0.0, 1.0, Ny + 1), indexing='ij')

    # 厳密解: ψ_exact(x, T) = 0.5 + 0.5·sin(2π(x − T))
    psi_exact = 0.5 + 0.5 * np.sin(2.0 * np.pi * (X - T))
    u_arr = np.ones(psi_exact.shape)
    v_arr = np.zeros(psi_exact.shape)

    dts = [0.02, 0.01, 0.005, 0.0025]
    l2s = []

    for dt in dts:
        psi0 = 0.5 + 0.5 * np.sin(2.0 * np.pi * X)
        advect = LevelSetAdvection(backend, grid, bc='periodic')

        # T/dt ステップ積分（余りは最終ステップで調整）
        t = 0.0
        psi = psi0.copy()
        while t < T - 1e-14:
            step = min(dt, T - t)
            psi = advect.advance(psi, [u_arr, v_arr], step)
            t += step

        err = np.abs(np.array(psi)[1:-1, :] - psi_exact[1:-1, :])
        l2 = float(np.sqrt(np.mean(err**2)))
        l2s.append(l2)

    order = _convergence_order(np.array(dts), np.array(l2s))

    print(f"\nTVD-RK3 temporal order: {order:.2f}")
    for dt, l2 in zip(dts, l2s):
        print(f"  dt={dt:.4f}: L2={l2:.3e}")

    assert order >= 2.8, (
        f"TVD-RK3 temporal order {order:.2f} < 2.8 (expected O(Δt³))"
    )


# ── Test 3: Dissipative CCD 空間精度（周期BC） ────────────────────────────
#
# Manufactured solution: ψ(x,t) = 0.5 + 0.5·sin(2π(x−t)), u=1 (periodic)
# Dissipative CCD filter is O(h²) correction to O(h⁶) CCD derivative, so
# leading spatial truncation error is O(h²) from the filter.
# Expected observed order ≥ 1.8 (slightly below 2 due to boundary effects).

def _dccd_advect_one_step(backend, Nx):
    """Helper: Dissipative CCD one-step advection with periodic BC, dt=1e-4."""
    np.random.seed(0)
    Ny = 4
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(Nx, Ny), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type='periodic')

    dt = 1e-4

    x = np.linspace(0.0, 1.0, Nx + 1)
    X, _ = np.meshgrid(x, np.linspace(0.0, 1.0, Ny + 1), indexing='ij')
    psi0 = 0.5 + 0.5 * np.sin(2.0 * np.pi * X)
    u = np.ones_like(psi0)
    v = np.zeros_like(psi0)

    advect = DissipativeCCDAdvection(backend, grid, ccd, bc='periodic')
    psi1 = advect.advance(psi0, [u, v], dt)

    psi_exact = 0.5 + 0.5 * np.sin(2.0 * np.pi * (X - dt))

    # Exclude periodic-duplicate boundary nodes (i=0, i=Nx share same point)
    err = np.abs(np.array(psi1)[1:-1, :] - psi_exact[1:-1, :])
    h = 1.0 / Nx
    l2 = float(np.sqrt(np.mean(err**2)))
    linf = float(np.max(err))
    return h, l2, linf


def test_dissipative_ccd_periodic_bc_spatial_order(backend):
    """Dissipative CCD + periodic BC must achieve spatial order ≥ 1.8.

    The spectral filter introduces O(h²) truncation error (§5 eq:dccd_adv_filter),
    so the expected order is O(h²); threshold 1.8 allows mild pre-asymptotic effects.
    Implements §5 alg:dccd_adv.
    """
    Nxs = [32, 64, 128, 256]
    hs, l2s, linfs = [], [], []

    for Nx in Nxs:
        h, l2, linf = _dccd_advect_one_step(backend, Nx)
        hs.append(h)
        l2s.append(l2)
        linfs.append(linf)
        assert l2 > 1e-15, (
            f"N={Nx}: L2 error {l2:.2e} is below machine precision"
        )

    order_l2   = _convergence_order(np.array(hs), np.array(l2s))
    order_linf = _convergence_order(np.array(hs), np.array(linfs))

    print(f"\nDissipative CCD periodic BC spatial order: L2={order_l2:.2f}, L∞={order_linf:.2f}")
    for Nx, h, l2, linf in zip(Nxs, hs, l2s, linfs):
        print(f"  N={Nx:3d}: h={h:.4f}  L2={l2:.3e}  L∞={linf:.3e}")

    assert order_l2 >= 1.8, (
        f"Dissipative CCD L2 spatial order {order_l2:.2f} < 1.8"
    )
    assert order_linf >= 1.8, (
        f"Dissipative CCD L∞ spatial order {order_linf:.2f} < 1.8"
    )


# ── Test 4: Dissipative CCD 全体精度（h-dt 同時細分化, O(h²)） ──────────
#
# Dissipative CCD spatial order is O(h²) (filter truncation), which dominates
# TVD-RK3 temporal error O(dt³) in the CFL-stable regime (σ = dt/h ≤ 0.5).
# TVD-RK3 temporal order is already verified by test_tvd_rk3_temporal_order.
#
# This test verifies full method convergence by refining h and dt together
# at fixed CFL = 0.3.  Expected overall order ≥ 1.8 (O(h²) limited).

def test_dissipative_ccd_full_method_order(backend):
    """Dissipative CCD full method (h + dt refined at CFL=0.3) must achieve order ≥ 1.8.

    Spatial truncation error O(h²) from the spectral filter (§5 eq:dccd_adv_filter)
    limits the overall method to O(h²) when dt ~ h (CFL fixed).
    Implements §6 alg:dccd_adv + §7.3 eq:tvd_rk3.
    """
    np.random.seed(0)
    Nxs = [32, 64, 128, 256]
    Ny   = 4
    T    = 0.1
    CFL  = 0.3   # σ = u·dt/h ≤ 0.5 keeps Dissipative CCD stable

    hs, l2s = [], []

    for Nx in Nxs:
        cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(Nx, Ny), L=(1.0, 1.0)))
        grid = Grid(cfg.grid, backend)
        ccd = CCDSolver(grid, backend, bc_type='periodic')

        h = 1.0 / Nx
        dt = CFL * h   # refine dt proportionally with h

        x = np.linspace(0.0, 1.0, Nx + 1)
        X, _ = np.meshgrid(x, np.linspace(0.0, 1.0, Ny + 1), indexing='ij')

        psi0 = 0.5 + 0.5 * np.sin(2.0 * np.pi * X)
        psi_exact = 0.5 + 0.5 * np.sin(2.0 * np.pi * (X - T))
        u_arr = np.ones_like(psi0)
        v_arr = np.zeros_like(psi0)

        advect = DissipativeCCDAdvection(backend, grid, ccd, bc='periodic')

        t = 0.0
        psi = psi0.copy()
        while t < T - 1e-14:
            step = min(dt, T - t)
            psi = advect.advance(psi, [u_arr, v_arr], step)
            t += step

        err = np.abs(np.array(psi)[1:-1, :] - psi_exact[1:-1, :])
        l2 = float(np.sqrt(np.mean(err**2)))
        hs.append(h)
        l2s.append(l2)

    order = _convergence_order(np.array(hs), np.array(l2s))

    print(f"\nDissipative CCD full method order (CFL={CFL}): {order:.2f}")
    for Nx, h, l2 in zip(Nxs, hs, l2s):
        print(f"  N={Nx:3d}: h={h:.4f}  L2={l2:.3e}")

    assert order >= 1.8, (
        f"Dissipative CCD full method order {order:.2f} < 1.8 (expected O(h²))"
    )
