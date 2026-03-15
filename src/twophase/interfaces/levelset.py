"""
レベルセット演算子の抽象インターフェース。

OCP（開放閉鎖原則）に基づき、レベルセット演算子の切り替えを可能にする。
DIP（依存性逆転原則）に基づき、TwoPhaseSimulation は具象クラスではなく
これらのインターフェースに依存する。

各インターフェースの実装を切り替えることで:
    - 時間積分スキームの変更（TVD-RK3 → RK4）
    - 再初期化アルゴリズムの変更
    - 曲率計算方法の変更
が、TwoPhaseSimulation 本体を変更せずに実現できる。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


class ILevelSetAdvection(ABC):
    """CLS 場の移流演算子の抽象インターフェース。

    実装: LevelSetAdvection（WENO5 + TVD-RK3）
    """

    @abstractmethod
    def advance(
        self,
        psi: "array",
        velocity_components: List,
        dt: float,
    ) -> "array":
        """CLS 場 ψ を時間 dt だけ移流させる。

        Parameters
        ----------
        psi                 : CLS 場 ψ ∈ [0,1]
        velocity_components : 速度成分リスト [u, v[, w]]
        dt                  : タイムステップ幅

        Returns
        -------
        psi_new : 移流後の CLS 場
        """


class IReinitializer(ABC):
    """CLS 場の再初期化演算子の抽象インターフェース。

    実装: Reinitializer（疑似時間 PDE, §3.4）
    """

    @abstractmethod
    def reinitialize(self, psi: "array") -> "array":
        """CLS 場を平衡プロファイルに再初期化する。

        Parameters
        ----------
        psi : 移流後の CLS 場 ψ

        Returns
        -------
        psi_new : 再初期化後の CLS 場
        """


class ICurvatureCalculator(ABC):
    """界面曲率計算の抽象インターフェース。

    実装: CurvatureCalculator（CCD 6次精度微分, §2.6）
    """

    @abstractmethod
    def compute(self, psi: "array") -> "array":
        """CLS 場 ψ から界面曲率 κ を計算する。

        Parameters
        ----------
        psi : CLS 場 ψ ∈ [0,1]

        Returns
        -------
        kappa : 界面曲率 κ（ψ と同形状の配列）
        """
