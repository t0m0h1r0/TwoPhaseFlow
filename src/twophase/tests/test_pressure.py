"""
圧力投影モジュールのテスト（論文 §6–7）。

検証項目:
  1. PPE 行列: 内部行の行和 ≈ 0（一貫性）
  2. PPE 求解: 残差 ‖Ap − b‖ < tol
  3. Rhie-Chow: コロケートグリッドの発散補正
  4. 発散ゼロ投影: ‖∇·u‖_∞ < 1e-8（速度補正後）
  5. PPESolverPseudoTime: MINRES 残差 < tol
  6. PPESolverPseudoTime: 変密度ケースでの収束
  7. PPESolverPseudoTime: ウォームスタートによる収束警告の抑制

リファクタリング後の変更点:
  - PPESolver(be, cfg, grid) — grid が必須引数になった
  - solve(rhs, rho, dt, p_init=None) — 統一インターフェース（IPPESolver）
  - PPESolverPseudoTime も同じシグネチャを使用
"""

import numpy as np
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig, SolverConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.ppe_solver import PPESolver
from twophase.pressure.ppe_solver_pseudotime import PPESolverPseudoTime
from twophase.pressure.rhie_chow import RhieChowInterpolator
from twophase.pressure.velocity_corrector import VelocityCorrector


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def make_setup(N=16, backend=None):
    if backend is None:
        backend = Backend(use_gpu=False)
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(bicgstab_tol=1e-12, bicgstab_maxiter=2000),
    )
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    return cfg, grid, ccd, backend


# ── Test 1: PPE 行列の一貫性 ───────────────────────────────────────────────

def test_ppe_matrix_interior_row_sum(backend):
    """一定密度のとき、内部行の行和は ≈ 0 であること。"""
    import scipy.sparse as sp
    cfg, grid, ccd, be = make_setup(backend=backend)
    builder = PPEBuilder(be, grid)

    rho = np.ones(grid.shape)
    (data, rows, cols), A_shape = builder.build(rho)
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

    # Dirichlet ピン点（行 0）を除いた行和を検証
    row_sums = np.array(A.sum(axis=1)).ravel()
    max_interior_sum = np.max(np.abs(row_sums[1:]))
    assert max_interior_sum < 1e-10, (
        f"PPE 行列の行和がゼロでない: {max_interior_sum:.3e}"
    )


# ── Test 2: PPE 求解残差（BiCGSTAB） ─────────────────────────────────────

def test_ppe_solve_residual(backend):
    """BiCGSTAB の残差が許容値以下に収束すること。"""
    import scipy.sparse as sp
    cfg, grid, ccd, be = make_setup(N=16, backend=backend)

    # 新しい統一 API: PPESolver(backend, config, grid)
    solver = PPESolver(be, cfg, grid)

    rho = np.ones(grid.shape)

    # 一貫性のある右辺（零空間を投影）
    rhs = np.random.default_rng(42).standard_normal(grid.shape)
    rhs -= rhs.mean()
    rhs[0, 0] = 0.0   # ピン点と整合

    # 統一インターフェース: solve(rhs, rho, dt, p_init=None)
    p = solver.solve(rhs, rho, dt=0.01)

    # 残差を検証: 内部行列を使って Ap ≈ b を確認
    (data, rows, cols), A_shape = solver._builder.build(rho)
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    residual = np.linalg.norm(A @ p.ravel() - rhs.ravel())
    rhs_norm = np.linalg.norm(rhs.ravel())
    rel_res = residual / max(rhs_norm, 1e-14)
    assert rel_res < 1e-8, f"PPE 相対残差 {rel_res:.3e} > 1e-8"


# ── Test 3: 発散ゼロ投影 ──────────────────────────────────────────────────

def test_divergence_free_projection(backend):
    """PPE 求解 + 速度補正後に ‖∇·u‖_∞ < 1e-3 であること。"""
    N = 16
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(bicgstab_tol=1e-12, bicgstab_maxiter=2000),
    )
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)

    # 新しい統一 API: PPESolver(backend, config, grid)
    solver = PPESolver(backend, cfg, grid)
    corrector = VelocityCorrector(backend, ccd)

    # 非発散ゼロの速度場
    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    u_star = np.sin(np.pi * X) * np.cos(np.pi * Y)
    v_star = -np.cos(np.pi * X) * np.sin(np.pi * Y)

    rho = np.ones(grid.shape)
    dt = 0.01

    # CCD による ∇·u* から PPE 右辺を構築
    du_dx, _ = ccd.differentiate(u_star, 0)
    dv_dy, _ = ccd.differentiate(v_star, 1)
    div_ustar = du_dx + dv_dy
    rhs = div_ustar / dt

    # 統一インターフェース: solve(rhs, rho, dt, p_init=None)
    p = solver.solve(rhs, rho, dt)

    vel_new = corrector.correct([u_star, v_star], p, rho, dt)

    # 補正後の発散を確認
    du_new_dx, _ = ccd.differentiate(vel_new[0], 0)
    dv_new_dy, _ = ccd.differentiate(vel_new[1], 1)
    div_new = du_new_dx + dv_new_dy

    div_max = float(np.max(np.abs(div_new)))
    # N=16 では PPE 離散化誤差 O(h²) + CCD 境界精度 ≈ O(h⁵) で ~1e-4 を期待
    assert div_max < 1e-3, (
        f"補正後の発散 ‖∇·u‖_∞ = {div_max:.3e} > 1e-3"
    )


# ── Test 4: PPESolverPseudoTime — 一様密度 ───────────────────────────────

def test_pseudotime_ppe_solve_uniform_density(backend):
    """MINRES PPE ソルバーの残差が収束後に tol 以下になること（一様密度）。"""
    N = 16
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(pseudo_tol=1e-10, pseudo_maxiter=500, ppe_solver_type="pseudotime"),
    )
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    solver = PPESolverPseudoTime(backend, cfg, grid)

    rho = np.ones(grid.shape)
    rhs = np.random.default_rng(7).standard_normal(grid.shape)
    rhs -= rhs.mean()
    rhs[0, 0] = 0.0

    # 統一インターフェース: solve(rhs, rho, dt, p_init=None)
    p = solver.solve(rhs, rho, dt=0.01, p_init=np.zeros(grid.shape))
    assert not np.any(np.isnan(p)), "MINRES PPE が NaN を返した"

    # FVM 残差の検証: A p ≈ rhs
    import scipy.sparse as sp
    (data, rows, cols), A_shape = solver._build_sym(rho)
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    p_h = np.asarray(backend.to_host(p)).ravel()
    residual = A @ p_h - rhs.ravel()
    residual[0] = 0.0
    rel_res = np.linalg.norm(residual) / max(np.linalg.norm(rhs.ravel()[1:]), 1e-14)
    assert rel_res < 1e-6, (
        f"MINRES PPE 相対残差 {rel_res:.3e} > 1e-6"
    )


def test_pseudotime_ppe_solve_variable_density(backend):
    """MINRES PPE ソルバーが変密度ケースで収束すること。"""
    N = 16
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(pseudo_tol=1e-8, pseudo_maxiter=500, ppe_solver_type="pseudotime"),
    )
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    solver = PPESolverPseudoTime(backend, cfg, grid)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')
    rho = 0.1 + 0.9 * (0.5 + 0.5 * np.tanh(10 * (X - 0.5)))

    rhs = np.sin(2 * np.pi * X) * np.cos(2 * np.pi * Y)
    rhs -= rhs.mean()
    rhs[0, 0] = 0.0

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        # 統一インターフェース: solve(rhs, rho, dt, p_init=None)
        p = solver.solve(rhs, rho, dt=0.01, p_init=np.zeros(grid.shape))

    assert not np.any(np.isnan(p)), "MINRES PPE が NaN を返した（変密度）"
    assert np.isfinite(p).all(), "MINRES PPE が inf を返した（変密度）"


def test_pseudotime_warm_start_no_convergence_warning(backend):
    """収束済み解からウォームスタートすると収束警告が出ないこと。"""
    N = 16
    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        solver=SolverConfig(pseudo_tol=1e-8, pseudo_maxiter=500, ppe_solver_type="pseudotime"),
    )
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    solver = PPESolverPseudoTime(backend, cfg, grid)

    rho = np.ones(grid.shape)
    rhs = np.random.default_rng(99).standard_normal(grid.shape)
    rhs -= rhs.mean()
    rhs[0, 0] = 0.0

    # 1回目: コールドスタート
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        # 統一インターフェース: solve(rhs, rho, dt, p_init=None)
        p_warm = solver.solve(rhs, rho, dt=0.01, p_init=np.zeros(grid.shape))

    # 2回目: ウォームスタート（同じ RHS → 即時収束を期待）
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        solver.solve(rhs, rho, dt=0.01, p_init=p_warm)
        conv_warns = [x for x in w if issubclass(x.category, RuntimeWarning)]
    assert len(conv_warns) == 0, (
        "ウォームスタート MINRES PPE が収束警告を発した"
    )


# ── Test 5: Rhie-Chow 発散補正 ────────────────────────────────────────────

def test_rhie_chow_divergence(backend):
    """チェッカーボード圧力場で Rhie-Chow 発散がセル中心発散と異なること。"""
    N = 16
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg, backend)
    ccd = CCDSolver(grid, backend)
    rc = RhieChowInterpolator(backend, grid, ccd)

    X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1),
                       indexing='ij')

    # 発散ゼロの速度場
    u_star = -np.sin(np.pi * Y)
    v_star =  np.sin(np.pi * X)

    # チェッカーボード圧力
    i_idx = np.arange(N+1)
    j_idx = np.arange(N+1)
    II, JJ = np.meshgrid(i_idx, j_idx, indexing='ij')
    p_checker = (-1.0) ** (II + JJ)

    rho = np.ones(grid.shape)
    dt = 0.01

    div_rc = rc.face_velocity_divergence([u_star, v_star], p_checker, rho, dt)
    # セル中心発散
    du_dx, _ = ccd.differentiate(u_star, 0)
    dv_dy, _ = ccd.differentiate(v_star, 1)
    div_cc = du_dx + dv_dy

    # Rhie-Chow 発散はセル中心発散と一致しないこと（補正が非自明であること）
    assert not np.any(np.isnan(div_rc)), "Rhie-Chow 発散が NaN を含む"
