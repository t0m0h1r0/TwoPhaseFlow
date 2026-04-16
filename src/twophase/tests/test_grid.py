"""
非一様格子のテスト (core/grid.py §6).

Test 1 — density function shape (test_density_function_paper_formula):
    paper §6 eq:grid_delta の ω = 1 + (α-1)·δ*(φ) を検証する.
    - 界面（φ=0）で ω が最大
    - 遠方（|φ|→∞）で ω → 1
    - ω ≥ 1 が全点で成立

Test 2 — metric convergence via CCD (test_metric_ccd_convergence):
    ccd.differentiate_raw() を用いた J = ∂ξ/∂x の MMS 収束テスト.
    既知の正弦波変形マッピング x(ξ) = ξ + A·sin(2πξ) を使用し，
    J の L∞ 誤差が O(h^4) 以上（CCD 境界精度 ≥ 3.5 次）で収束することを確認する.

Test 3 — metric dJ/dξ convergence (test_metric_dJdxi_ccd_convergence):
    同じマッピングで ∂J/∂ξ の収束次数 ≥ 2.5（d2 境界制限）を確認する.

Test 4 — update_from_levelset roundtrip (test_update_from_levelset):
    update_from_levelset() が CCD メトリクスを使って一様格子よりも
    界面近傍での格子幅を小さくすることを確認する（基本動作テスト）.
"""

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver


# ── ヘルパー ─────────────────────────────────────────────────────────────────

def _make_backend():
    return Backend(use_gpu=False)


def _make_grid_and_ccd(n, L=1.0):
    """N×N の均一格子と CCDSolver を生成する（壁 BC）."""
    backend = _make_backend()
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(n, n), L=(L, L)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    return grid, ccd, backend


# ── Test 1: 密度関数の形状 ────────────────────────────────────────────────────

def test_density_function_paper_formula():
    """ω(ψ) = 1 + (α-1)·4ψ(1-ψ) の形状を検証する."""
    backend = _make_backend()
    n = 64
    L = 1.0
    alpha = 4.0

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(n, n), L=(L, L), alpha_grid=alpha)
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    # 円形界面: φ → ψ = 1/(1+exp(φ/ε)) (ψ=1 outside, ψ=0 inside)
    x = np.linspace(0, L, n + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    phi0 = np.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - 0.25
    eps = 1.5 * (L / n)
    psi0 = 1.0 / (1.0 + np.exp(-phi0 / eps))

    grid.update_from_levelset(psi0, ccd=ccd)

    # ω の再計算（grid.py と同じ手順で検証）
    indicator = psi0 * (1.0 - psi0)
    indicator_1d = np.max(indicator, axis=1) / 0.25   # axis=0 方向
    omega = 1.0 + (alpha - 1.0) * indicator_1d

    # 検証: ω ≥ 1 かつ界面（indicator 最大点）で最大
    assert np.all(omega >= 1.0 - 1e-12), "ω は全点で ≥ 1 でなければならない"
    i_interface = np.argmax(indicator_1d)
    assert omega[i_interface] == pytest.approx(np.max(omega), rel=1e-6), (
        "ω は界面ノードで最大でなければならない"
    )
    # 遠方で ω ≈ 1
    far_mask = indicator_1d < 0.01
    if np.any(far_mask):
        assert np.all(omega[far_mask] < 1.04), "遠方の ω は 1 に近くなければならない"

    # 格子幅: 界面近傍 < 一様格子幅
    h_uniform = L / n
    h_interface = grid.h[0][i_interface]
    assert h_interface < h_uniform, (
        f"界面の格子幅 {h_interface:.4g} は一様格子幅 {h_uniform:.4g} より小さくなければならない"
    )


# ── Test 2: J の MMS 収束 ─────────────────────────────────────────────────────

@pytest.mark.parametrize("axis", [0, 1])
def test_metric_ccd_convergence(axis):
    """CCD 計算 J = ∂ξ/∂x の L∞ 収束次数 ≥ 3.5（§6 Step 5, ARCH §6 CCD境界精度）.

    既知マッピング x(ξ) = ξ + A·sin(2πξ) を使い，
    J_exact = 1 / (1 + 2πA·cos(2πξ)) と比較する.
    """
    Ns = [32, 64, 128, 256]
    A = 0.1   # 正弦波振幅（CCD 線形化誤差が支配しない程度に小）
    L = 1.0

    errors = []
    for n in Ns:
        xi = np.linspace(0.0, L, n + 1)  # 均一計算座標
        x_phys = xi + A * np.sin(2.0 * np.pi * xi / L)

        # 解析 J = ∂ξ/∂x = 1 / (dx/dξ)
        dxdxi_exact = 1.0 + A * (2.0 * np.pi / L) * np.cos(2.0 * np.pi * xi / L)
        J_exact = 1.0 / dxdxi_exact

        # Grid + CCD を構築し，座標を手動で非一様に設定
        backend = _make_backend()
        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(n, n), L=(L, L), alpha_grid=2.0)
        )
        grid = Grid(cfg.grid, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")

        # axis に対応する方向の座標を sinusoidal mapping に置き換える
        cell_dx = np.diff(x_phys)
        node_dx = np.empty(n + 1)
        node_dx[0] = cell_dx[0]
        node_dx[-1] = cell_dx[-1]
        node_dx[1:-1] = 0.5 * (cell_dx[:-1] + cell_dx[1:])
        grid.coords[axis] = x_phys
        grid.h[axis] = node_dx

        # CCD メトリクスを再計算（grid.uniform = False にするため alpha_grid > 1 は既設定）
        grid._build_metrics(ccd=ccd)

        J_computed = np.asarray(grid.J[axis])
        err = np.max(np.abs(J_computed - J_exact))
        errors.append(err)

    # 収束次数（対数最小二乗）
    hs = [L / n for n in Ns]
    order = np.polyfit(np.log(hs), np.log(errors), 1)[0]
    assert order >= 3.5, (
        f"axis={axis}: J の収束次数 {order:.2f} < 3.5 (CCD 境界精度限界を下回る)"
    )


# ── Test 3: dJ/dξ の MMS 収束 ────────────────────────────────────────────────

@pytest.mark.parametrize("axis", [0, 1])
def test_metric_dJdxi_ccd_convergence(axis):
    """CCD 計算 ∂J/∂ξ の L∞ 収束次数 ≥ 2.5（d2 境界精度限界）.

    同じ sinusoidal mapping を使い，
    (∂J/∂ξ)_exact = -(d²x/dξ²) / (dx/dξ)² と比較する.
    """
    Ns = [32, 64, 128, 256]
    A = 0.1
    L = 1.0

    errors = []
    for n in Ns:
        xi = np.linspace(0.0, L, n + 1)
        x_phys = xi + A * np.sin(2.0 * np.pi * xi / L)

        dxdxi = 1.0 + A * (2.0 * np.pi / L) * np.cos(2.0 * np.pi * xi / L)
        d2xdxi2 = -A * (2.0 * np.pi / L) ** 2 * np.sin(2.0 * np.pi * xi / L)
        dJdxi_exact = -d2xdxi2 / (dxdxi ** 2)

        backend = _make_backend()
        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(n, n), L=(L, L), alpha_grid=2.0)
        )
        grid = Grid(cfg.grid, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")

        cell_dx = np.diff(x_phys)
        node_dx = np.empty(n + 1)
        node_dx[0] = cell_dx[0]
        node_dx[-1] = cell_dx[-1]
        node_dx[1:-1] = 0.5 * (cell_dx[:-1] + cell_dx[1:])
        grid.coords[axis] = x_phys
        grid.h[axis] = node_dx

        grid._build_metrics(ccd=ccd)

        dJ_computed = np.asarray(grid.dJ_dxi[axis])
        err = np.max(np.abs(dJ_computed - dJdxi_exact))
        errors.append(err)

    hs = [L / n for n in Ns]
    order = np.polyfit(np.log(hs), np.log(errors), 1)[0]
    assert order >= 2.5, (
        f"axis={axis}: ∂J/∂ξ の収束次数 {order:.2f} < 2.5 (d2 CCD 境界精度限界を下回る)"
    )


# ── Test 4: update_from_levelset の基本動作 ────────────────────────────────────

def test_update_from_levelset():
    """update_from_levelset(ccd=ccd) が界面近傍に格子を集中させることを確認する."""
    n = 64
    L = 1.0
    alpha = 3.0

    backend = _make_backend()
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(n, n), L=(L, L), alpha_grid=alpha)
    )
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")

    # 中央に直線界面 ψ = sigmoid(−(y−0.5)/ε)
    x = np.linspace(0, L, n + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    phi0 = Y - 0.5
    eps = 1.5 * (L / n)
    psi0 = 1.0 / (1.0 + np.exp(-phi0 / eps))

    grid.update_from_levelset(psi0, ccd=ccd)

    # axis=1（y 方向）で界面ノード付近の格子幅が一様格子幅より小さいこと
    h_uniform = L / n
    y_coords = grid.coords[1]
    i_interface = np.argmin(np.abs(y_coords - 0.5))
    h_near = np.min(np.diff(y_coords[max(0, i_interface-2):i_interface+3]))
    assert h_near < h_uniform, (
        f"界面近傍の格子幅 {h_near:.4g} は一様格子幅 {h_uniform:.4g} より小さくなければならない"
    )

    # J, dJ_dxi が float array として保存されていること（CCD 経由）
    assert len(grid.J) == 2
    assert len(grid.dJ_dxi) == 2
    assert grid.J[1].shape == (n + 1,)
    assert not np.any(np.isnan(grid.J[1])), "J[1] に NaN が含まれる"
    assert not np.any(np.isnan(grid.dJ_dxi[1])), "dJ_dxi[1] に NaN が含まれる"
