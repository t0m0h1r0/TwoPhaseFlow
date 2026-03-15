"""
Navier-Stokes 各項の抽象インターフェース。

ISP（インターフェース分離原則）に基づき、NS各項を最小インターフェースで定義する。
DIP（依存性逆転原則）に基づき、Predictor は INSTerm 抽象にのみ依存する。

設計方針（2026-03-15 3rd pass）:
    - ccd はコンストラクタ注入パターンに統一（他の演算子と一貫）。
    - compute() シグネチャから ccd を除去。
    - 新しい物理モデルを INSTerm として実装する際は、
      コンストラクタで ccd を受け取る設計を推奨する。

新しい物理モデル（熱伝導項、磁場項等）を追加する場合:
    1. INSTerm を継承したクラスを作成する
    2. __init__(self, backend, ccd, ...) で ccd を受け取る
    3. compute(vel, rho, mu, kappa, psi, dt) を実装する
    4. SimulationBuilder で注入する
    → Predictor 自体の変更は不要（OCP準拠）
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List


class INSTerm(ABC):
    """Navier-Stokes 右辺の各項の共通インターフェース。

    全ての NS 項（対流・粘性・重力・表面張力）はこのインターフェースを実装する。
    Predictor は INSTerm のリストとして各項を受け取り、具象クラスを知らない。

    注: ccd（CCDSolver）はコンストラクタで注入する設計を推奨する。
        compute() には渡さないことで、呼び出し元（Predictor）の
        シグネチャが ccd の詳細を知る必要をなくす（ISP）。
    """

    @abstractmethod
    def compute(
        self,
        vel: List,
        rho: "array",
        mu: "array",
        kappa: "array",
        psi: "array",
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
        dt    : タイムステップ幅

        Returns
        -------
        term_components : List[array]
            各速度成分に対するこの項の寄与 [f_0, f_1[, f_2]]
        """
