"""
CCD PPE ソルバー共通ユーティリティ。

反復型 PPE ソルバー（sweep, iim, iterative）で重複していた
数値計算パターンを集約する:

  - precompute_density_gradients: 密度勾配の CCD 事前計算
  - compute_ccd_laplacian: 変密度 CCD ラプラシアン
  - compute_ccd_laplacian_with_derivatives: 同上 + dp/d2p リスト
  - compute_lts_dtau: LTS 局所時間刻み
  - check_convergence: ピン除外残差ノルム
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver


def precompute_density_gradients(
    rho_np: np.ndarray,
    ccd: "CCDSolver",
    backend: "Backend",
) -> list[np.ndarray]:
    """密度勾配を CCD で事前計算する（反復中は凍結）。

    Parameters
    ----------
    rho_np  : np.ndarray — 密度場（ホスト配列）
    ccd     : CCDSolver
    backend : Backend

    Returns
    -------
    drho : list[np.ndarray] — 各軸の ∂ρ/∂x_i（ホスト配列）
    """
    xp = backend.xp
    rho_dev = xp.asarray(rho_np)
    ndim = rho_np.ndim
    drho: list[np.ndarray] = []
    for ax in range(ndim):
        drho_ax, _ = ccd.differentiate(rho_dev, ax)
        drho.append(np.asarray(backend.to_host(drho_ax), dtype=float))
    return drho


def compute_ccd_laplacian(
    p_np: np.ndarray,
    rho_np: np.ndarray,
    drho: list[np.ndarray],
    ccd: "CCDSolver",
    backend: "Backend",
) -> np.ndarray:
    """変密度 CCD ラプラシアン L_CCD^ρ(p) を計算する。

    L_CCD^ρ(p) = Σ_ax [ d²p/dx² / ρ  −  (∂ρ/∂x / ρ²) · dp/dx ]

    Parameters
    ----------
    p_np    : np.ndarray — 圧力場（ホスト配列）
    rho_np  : np.ndarray — 密度場（ホスト配列）
    drho    : list[np.ndarray] — 各軸の密度勾配（ホスト配列）
    ccd     : CCDSolver
    backend : Backend

    Returns
    -------
    Lp : np.ndarray — ラプラシアン結果（ホスト配列）
    """
    xp = backend.xp
    p_dev = xp.asarray(p_np)
    rho_dev = xp.asarray(rho_np)
    Lp = xp.zeros(p_np.shape, dtype=float)
    for ax in range(p_np.ndim):
        dp_ax, d2p_ax = ccd.differentiate(p_dev, ax)
        drho_dev = xp.asarray(drho[ax])
        Lp += d2p_ax / rho_dev - (drho_dev / rho_dev ** 2) * dp_ax
    return np.asarray(backend.to_host(Lp))


def compute_ccd_laplacian_with_derivatives(
    p_np: np.ndarray,
    rho_np: np.ndarray,
    drho: list[np.ndarray],
    ccd: "CCDSolver",
    backend: "Backend",
) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
    """変密度 CCD ラプラシアン + 各軸微分を計算する。

    Returns
    -------
    Lp      : np.ndarray — ラプラシアン結果
    dp_list : list[np.ndarray] — 各軸の 1 階微分
    d2p_list: list[np.ndarray] — 各軸の 2 階微分
    """
    xp = backend.xp
    p_dev = xp.asarray(p_np)
    rho_dev = xp.asarray(rho_np)
    Lp = xp.zeros(p_np.shape, dtype=float)
    dp_list: list[np.ndarray] = []
    d2p_list: list[np.ndarray] = []
    for ax in range(p_np.ndim):
        dp_ax, d2p_ax = ccd.differentiate(p_dev, ax)
        drho_dev = xp.asarray(drho[ax])
        Lp += d2p_ax / rho_dev - (drho_dev / rho_dev ** 2) * dp_ax
        dp_list.append(np.asarray(backend.to_host(dp_ax), dtype=float))
        d2p_list.append(np.asarray(backend.to_host(d2p_ax), dtype=float))
    Lp_np = np.asarray(backend.to_host(Lp))
    return Lp_np, dp_list, d2p_list


def compute_lts_dtau(
    rho_np: np.ndarray,
    c_tau: float,
    h_min: float,
) -> np.ndarray:
    """LTS 局所時間刻み Δτᵢⱼ = C_τ · ρᵢⱼ · h_min² / 2  (§8d eq:dtau_lts)。

    密度依存性が打ち消されるため気液相で均等な収束速度を得る。
    """
    return c_tau * rho_np * (h_min ** 2) / 2.0


def check_convergence(
    R: np.ndarray,
    pin_dof: int,
    tol: float,
) -> tuple[float, bool]:
    """ピン DOF を除外した残差 L2 ノルムで収束判定する。

    Parameters
    ----------
    R       : np.ndarray — 残差場
    pin_dof : int — ゲージピンの DOF インデックス
    tol     : float — 収束閾値

    Returns
    -------
    residual : float — L2 ノルム
    converged : bool — residual < tol
    """
    R_flat = R.ravel().copy()
    R_flat[pin_dof] = 0.0
    residual = float(np.sqrt(np.dot(R_flat, R_flat)))
    return residual, residual < tol
