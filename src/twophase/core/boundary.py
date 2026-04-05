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
