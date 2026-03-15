"""
Navier-Stokes 各項の抽象インターフェース。

ISP（インターフェース分離原則）に基づき、NS各項を最小インターフェースで定義する。
DIP（依存性逆転原則）に基づき、Predictor は INSTerm 抽象にのみ依存する。

新しい物理モデル（熱伝導項、磁場項等）を追加する場合:
    1. INSTerm を継承したクラスを作成する
    2. compute(...) を実装する
    3. SimulationBuilder の ns_terms リストに追加する
    → Predictor 自体の変更は不要（OCP準拠）
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


class INSTerm(ABC):
    """Navier-Stokes 右辺の各項の共通インターフェース。

    全ての NS 項（対流・粘性・重力・表面張力）はこのインターフェースを実装する。
    Predictor は INSTerm のリストとして各項を受け取り、具象クラスを知らない。
    """

    @abstractmethod
    def compute(
        self,
        vel: List,
        rho: "array",
        mu: "array",
        kappa: "array",
        psi: "array",
        ccd: "CCDSolver",
        dt: float,
    ) -> List:
        """NS 右辺の各成分（速度場の各軸）を返す。

        Parameters
        ----------
        vel   : 速度成分リスト [u, v[, w]]（時刻 n）
        rho   : 密度場 ρ̃^{n+1}
        mu    : 粘性場 μ̃^{n+1}
        kappa : 界面曲率 κ
        psi   : CLS 場 ψ
        ccd   : CCD 微分ソルバー
        dt    : タイムステップ幅

        Returns
        -------
        term_components : List[array]
            各速度成分に対するこの項の寄与 [f_0, f_1[, f_2]]
        """
