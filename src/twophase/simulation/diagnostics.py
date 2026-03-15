"""
診断レポータ。

単一責務の原則 (SRP) に従い、診断情報の出力ロジックを
TwoPhaseSimulation から分離した独立モジュール。

報告する診断値:
    - 現在時刻 t、タイムステップ幅 Δt
    - 速度の発散 |∇·u|_∞（非圧縮性の残差）
    - レベルセット体積 ∫ψ dV（体積保存誤差の指標）
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


class DiagnosticsReporter:
    """シミュレーション診断情報をコンソールに出力するクラス。

    Parameters
    ----------
    backend : Backend — xp (numpy/cupy) アクセス用
    grid    : Grid — 格子形状と格子体積用
    """

    def __init__(self, backend: "Backend", grid: "Grid") -> None:
        self.backend = backend
        self.grid = grid

    def report(self, sim, dt: float) -> None:
        """診断情報を計算してコンソールに出力する。

        Parameters
        ----------
        sim : TwoPhaseSimulation — 診断対象のシミュレーション
        dt  : float — 現在のタイムステップ幅
        """
        xp = self.backend.xp

        # 速度の発散を計算（非圧縮性残差）
        div = xp.zeros(self.grid.shape)
        for ax in range(self.grid.ndim):
            d1, _ = sim.ccd.differentiate(sim.velocity[ax], ax)
            div += d1
        div_max = float(xp.max(xp.abs(div)))

        # レベルセット体積（ψ の積分）
        dV = self.grid.cell_volume()
        vol = float(xp.sum(sim.psi.data)) * dV

        print(
            f"  t={sim.time:.5f}  dt={dt:.3e}  "
            f"|∇·u|_∞={div_max:.3e}  vol(ψ)={vol:.6f}"
        )
