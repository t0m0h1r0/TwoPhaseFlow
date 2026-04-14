"""
変密度 PPE 用ベクトル化 Thomas スウィープソルバー。

ADI/sweep 型 PPE ソルバー（sweep, iim, iterative）で重複していた
1D Thomas 法を集約する。

アルゴリズム:
  (1/Δτ − L_FD_axis) q = rhs を各軸の断面ごとに同時に解く。

境界条件 (Neumann ∂p/∂n = 0):
  ゴーストセル反射 q[-1] = q[1], q[N+1] = q[N-1] を適用。
  反対称差分が消えるため, 密度勾配項は境界で 0 になる。

  左壁 i=0:  a[0]=0,         b[0]=1/Δτ+2/(ρh²), c[0]=-2/(ρh²),   rhs 不変
  右壁 i=N:  a[-1]=-2/(ρh²), b[-1]=1/Δτ+2/(ρh²), c[-1]=0,         rhs 不変

CCD との整合性:
  CCD は境界で片側コンパクトスタンシルを用いる（Neumann 強制なし）。
  FD でも正しい Neumann 行を設定することで, DC 反復後に p が
  ∂p/∂n ≈ 0 を自然に満足し, CCD ラプラシアンとの不整合を防ぐ。
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

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

    # Neumann BC (Neumann ∂p/∂n=0): ゴーストセル反射 → 密度勾配項は消える
    # 左壁 i=0
    a[0] = 0.0
    b[0] = inv_dtau[0] + 2.0 * inv_rho_h2[0]
    c[0] = -2.0 * inv_rho_h2[0]
    # 右壁 i=N
    a[-1] = -2.0 * inv_rho_h2[-1]
    b[-1] = inv_dtau[-1] + 2.0 * inv_rho_h2[-1]
    c[-1] = 0.0

    rhs_m = rhs_f.copy()
    # rhs at boundaries is kept unchanged (R[0], R[-1] drive the correction)

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
