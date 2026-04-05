"""
境界条件の物理仕様層 (what)。

BCType enum と BoundarySpec dataclass を提供する。
各ソルバーの数値実装 (how) には介入しない。

  - BCType: 'wall' / 'periodic' を型安全に扱う enum
  - BoundarySpec: BC種別 + grid shape から pin DOF 等を導出する frozen dataclass
  - pad_ghost_cells: ゴーストセル充填の公開ユーティリティ
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class BCType(str, Enum):
    """境界条件の種別。str 継承により YAML 文字列値との互換性を保つ。"""

    WALL = "wall"
    PERIODIC = "periodic"


@dataclass(frozen=True)
class BoundarySpec:
    """境界条件の物理仕様。

    PPE ソルバー等が必要とする共通情報（pin DOF, 周期判定）を
    一箇所で導出し、重複計算を排除する。

    Parameters
    ----------
    bc_type : BCType
        境界条件の種別。
    shape : tuple[int, ...]
        grid.shape — ノード数 (Nx+1, Ny+1[, Nz+1])。
    N : tuple[int, ...]
        grid.N — 各軸のセル数 (Nx, Ny[, Nz])。
    """

    bc_type: BCType
    shape: tuple[int, ...]
    N: tuple[int, ...]

    @property
    def is_periodic(self) -> bool:
        return self.bc_type is BCType.PERIODIC

    @property
    def is_wall(self) -> bool:
        return self.bc_type is BCType.WALL

    @property
    def pin_dof(self) -> int:
        """PPE ゲージピンの DOF インデックス。

        Wall BC: ドメイン中央 (N//2, N//2, ...) — 全対称操作に不変。
        Periodic BC: ノード 0 — 並進対称性により任意ノードが等価。
        """
        if self.is_periodic:
            return 0
        centre_idx = tuple(n // 2 for n in self.N)
        return int(np.ravel_multi_index(centre_idx, self.shape))

    def pin_dof_in_shape(self, reduced_shape: tuple[int, ...]) -> int:
        """縮退空間（周期 BC の N×N 空間等）での pin DOF。

        Parameters
        ----------
        reduced_shape : tuple[int, ...]
            縮退後の格子形状。
        """
        if self.is_periodic:
            return 0
        centre_idx = tuple(n // 2 for n in self.N)
        return int(np.ravel_multi_index(centre_idx, reduced_shape))


def apply_thomas_neumann(a, b, c, rhs) -> None:
    """Thomas 法の壁 Neumann BC: 両端を恒等行 (Δq=0) に設定する。

    ADI/sweep 型 PPE ソルバーの共通パターン。
    境界ノード i=0, i=-1 で a=0, b=1, c=0, rhs=0 とし、
    壁面での圧力増分を凍結する。

    Parameters
    ----------
    a, b, c : ndarray — 3重対角の下・主・上対角（in-place 変更）
    rhs     : ndarray — 右辺ベクトル（in-place 変更）
    """
    a[0] = 0.0;  b[0] = 1.0;  c[0] = 0.0
    a[-1] = 0.0; b[-1] = 1.0; c[-1] = 0.0
    rhs[0] = 0.0
    rhs[-1] = 0.0


def pin_sparse_row(L_lil, rhs_flat, pin_dof: int) -> None:
    """疎行列のゲージピン行を恒等行に設定する。

    PPE の null space を除去するために、pin_dof 行を
    ``L[pin, :] = 0, L[pin, pin] = 1, rhs[pin] = 0``
    に書き換える。

    Parameters
    ----------
    L_lil    : scipy.sparse.lil_matrix — in-place 変更
    rhs_flat : ndarray (1D) — in-place 変更
    pin_dof  : int — ピン対象の DOF インデックス
    """
    L_lil[pin_dof, :] = 0.0
    L_lil[pin_dof, pin_dof] = 1.0
    rhs_flat[pin_dof] = 0.0


def pad_ghost_cells(xp, arr, axis: int, n_ghost: int, bc_type: str):
    """配列にゴーストセルを付加する。

    §4 sec:weno5_boundary に基づくゴーストセル戦略。

    Parameters
    ----------
    xp        : array namespace (numpy or cupy)
    arr       : 対象配列
    axis      : パディング軸
    n_ghost   : 片側のゴーストセル数 (WENO5 では 3)
    bc_type   : 'periodic' | 'neumann' | 'outflow' | 'zero'

    Returns
    -------
    パディング済み配列 (axis 方向に +2*n_ghost)
    """
    n = arr.shape[axis]

    def _sl(start, stop=None):
        s = [slice(None)] * arr.ndim
        s[axis] = slice(start, stop)
        return tuple(s)

    if bc_type == "periodic":
        left = arr[_sl(n - 1 - n_ghost, n - 1)]
        right = arr[_sl(1, 1 + n_ghost)]
        return xp.concatenate([left, arr, right], axis=axis)

    elif bc_type == "neumann":
        left = xp.flip(arr[_sl(0, n_ghost)], axis=axis)
        right = xp.flip(arr[_sl(n - n_ghost, n)], axis=axis)
        return xp.concatenate([left, arr, right], axis=axis)

    elif bc_type == "outflow":
        left = xp.repeat(arr[_sl(0, 1)], n_ghost, axis=axis)
        right = xp.repeat(arr[_sl(n - 1, n)], n_ghost, axis=axis)
        return xp.concatenate([left, arr, right], axis=axis)

    else:  # 'zero'
        shape_pad = list(arr.shape)
        shape_pad[axis] = n_ghost
        pad = xp.zeros(shape_pad, dtype=arr.dtype)
        return xp.concatenate([pad, arr, pad], axis=axis)
