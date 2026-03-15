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
        self.bc_type = config.numerics.bc_type
        self.ndim = config.grid.ndim

    def apply(self, velocity: "VectorField") -> None:
        """速度場に境界条件を適用する。

        Parameters
        ----------
        velocity : VectorField — in-place で修正される
        """
        if self.bc_type == "wall":
            self._apply_wall(velocity)
        # 'periodic' は追加の処理不要（将来実装可能）

    def _apply_wall(self, velocity: "VectorField") -> None:
        """全境界面でノースリップ条件（u = 0）を適用する。"""
        for ax in range(self.ndim):
            u = velocity[ax]
            # 各軸の最小・最大境界面のスライスを構築
            sl_lo = [slice(None)] * self.ndim
            sl_hi = [slice(None)] * self.ndim
            sl_lo[ax] = 0
            sl_hi[ax] = -1
            u[tuple(sl_lo)] = 0.0
            u[tuple(sl_hi)] = 0.0
