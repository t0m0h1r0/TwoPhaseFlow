"""
境界条件ハンドラ。

単一責務の原則 (SRP) に従い、境界条件の適用ロジックを
TwoPhaseSimulation から分離した独立モジュール。

対応する境界条件:
    'wall'     — 全境界面でノースリップ / 法線方向非浸透
    'periodic' — 現バージョンでは何も行わない（将来実装用）
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..core.boundary import BCType

if TYPE_CHECKING:
    from ..config import SimulationConfig
    from ..core.field import VectorField


class BoundaryConditionHandler:
    """速度場への境界条件適用を担当するクラス。

    Parameters
    ----------
    config : SimulationConfig — bc_type, ndim を参照
    """

    def __init__(self, config: "SimulationConfig") -> None:
        bc = config.numerics.bc_type
        self.bc_type = BCType(bc) if isinstance(bc, str) else bc
        self.ndim = config.grid.ndim

    def apply(self, velocity: "VectorField") -> None:
        """速度場に境界条件を適用する。

        Parameters
        ----------
        velocity : VectorField — in-place で修正される
        """
        if self.bc_type is BCType.WALL:
            self._apply_wall(velocity)
        elif self.bc_type is BCType.PERIODIC:
            self._apply_periodic(velocity)

    def _boundary_slices(self, ax: int):
        """Return (sl_lo, sl_hi) index tuples selecting the two boundary planes along *ax*."""
        sl_lo = [slice(None)] * self.ndim
        sl_hi = [slice(None)] * self.ndim
        sl_lo[ax] = 0
        sl_hi[ax] = -1
        return tuple(sl_lo), tuple(sl_hi)

    def _apply_wall(self, velocity: "VectorField") -> None:
        """全境界面でノースリップ条件（u = 0）を適用する。

        wall_ax 方向に垂直な両壁面（インデックス 0 と -1）において，
        すべての速度成分（法線・接線を問わず）をゼロに設定する．
        これにより完全ノースリップ条件が保証される．

        注意: 以前の実装は velocity[ax] を ax 方向の壁面のみでゼロにしていたため，
        接線速度成分（例: u_x at y=0 壁）が未処理となり，
        壁面付近で速度が増大するバグがあった（Bug #wall-tangential）．
        """
        for wall_ax in range(self.ndim):        # 壁面の法線方向
            sl_lo, sl_hi = self._boundary_slices(wall_ax)
            for comp in range(self.ndim):       # 速度成分（法線・接線すべて）
                u = velocity[comp]
                u[sl_lo] = 0.0
                u[sl_hi] = 0.0

    def _apply_periodic(self, velocity: "VectorField") -> None:
        """周期境界条件: node 0 と node N を一致させる（node N ← node 0）。"""
        for ax in range(self.ndim):
            sl_first, sl_last = self._boundary_slices(ax)
            for c in range(self.ndim):
                u = velocity[c]
                u[sl_last] = u[sl_first]
