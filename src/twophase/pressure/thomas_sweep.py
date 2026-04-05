"""
変密度 PPE 用ベクトル化 Thomas スウィープソルバー。

ADI/sweep 型 PPE ソルバー（sweep, iim, iterative）で重複していた
1D Thomas 法を集約する。

アルゴリズム:
  (1/Δτ − L_FD_axis) q = rhs を各軸の断面ごとに同時に解く。
  壁面 Neumann BC は恒等行（apply_thomas_neumann）で処理。
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

from ..core.boundary import apply_thomas_neumann

if TYPE_CHECKING:
    from ..core.grid import Grid


def thomas_sweep_1d(
    rhs_2d: np.ndarray,
    rho: np.ndarray,
    drho: np.ndarray,
    dtau: np.ndarray,
    axis: int,
    grid: "Grid",
) -> np.ndarray:
    """変密度 PPE の 1D Thomas スウィープ。

    (1/Δτ − L_FD_axis) q = rhs を解く。

    Parameters
    ----------
    rhs_2d : np.ndarray — 右辺（shape = grid.shape）
    rho    : np.ndarray — 密度場
    drho   : np.ndarray — axis 方向の密度勾配
    dtau   : np.ndarray — LTS 局所時間刻み
    axis   : int — スウィープ軸
    grid   : Grid

    Returns
    -------
    q : np.ndarray — 解（shape = grid.shape）
    """
    N = grid.N[axis]
    h = grid.L[axis] / N
    h2 = h * h

    # 先頭軸に移動してベクトル化
    rhs_f = np.moveaxis(rhs_2d, axis, 0)
    rho_f = np.moveaxis(rho, axis, 0)
    drho_f = np.moveaxis(drho, axis, 0)
    dtau_f = np.moveaxis(dtau, axis, 0)
    n = N + 1

    inv_dtau = 1.0 / dtau_f
    inv_rho_h2 = 1.0 / (rho_f * h2)
    drho_h = drho_f / (rho_f ** 2 * 2.0 * h)

    # 3重対角係数
    a = np.empty_like(rhs_f)
    b = np.empty_like(rhs_f)
    c = np.empty_like(rhs_f)

    a[1:-1] = -inv_rho_h2[1:-1] + drho_h[1:-1]
    b[1:-1] = inv_dtau[1:-1] + 2.0 * inv_rho_h2[1:-1]
    c[1:-1] = -inv_rho_h2[1:-1] - drho_h[1:-1]

    rhs_m = rhs_f.copy()
    apply_thomas_neumann(a, b, c, rhs_m)

    # 前進消去
    c_p = np.zeros_like(rhs_f)
    r_p = np.zeros_like(rhs_f)
    c_p[0] = c[0] / b[0]
    r_p[0] = rhs_m[0] / b[0]
    for i in range(1, n):
        denom = b[i] - a[i] * c_p[i - 1]
        c_p[i] = c[i] / denom
        r_p[i] = (rhs_m[i] - a[i] * r_p[i - 1]) / denom

    # 後退代入
    q = np.empty_like(rhs_f)
    q[-1] = r_p[-1]
    for i in range(n - 2, -1, -1):
        q[i] = r_p[i] - c_p[i] * q[i + 1]

    return np.moveaxis(q, 0, axis)
