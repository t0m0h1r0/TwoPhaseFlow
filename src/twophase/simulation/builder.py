"""
SimulationBuilder — legacy ``TwoPhaseSimulation`` の構築を担うビルダー。

設計方針:
    - TwoPhaseSimulation.__init__ の「God Constructor」問題を解消する（SRP）。
    - 具象クラスの直接インスタンス化を Builder に集約し、
      TwoPhaseSimulation はインターフェースのみに依存できるようにする（DIP）。
    - デフォルトの依存関係は build() で自動組み立て。
    - with_* メソッドでコンポーネントを個別に差し替え可能（OCP）。

使用例（デフォルト構築）::

    from twophase.simulation.builder import SimulationBuilder

    sim = SimulationBuilder(config).build()

使用例（カスタム PPEソルバーを注入）::

    from twophase.ppe.interfaces import  # (removed) PPESolverPseudoTime
    from twophase.simulation.builder import SimulationBuilder

    solver = PPESolverPseudoTime(backend, config, grid)
    sim = SimulationBuilder(config).with_ppe_solver(solver).build()

使用例（カスタム対流項を注入）::

    from twophase.simulation.builder import SimulationBuilder

    sim = (SimulationBuilder(config)
           .with_convection(MyCustomConvectionTerm(backend))
           .build())
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from ..config import SimulationConfig
from .legacy_builder_runtime import build_legacy_simulation_components

if TYPE_CHECKING:
    from ..ppe.interfaces import IPPESolver
    from ..ns_terms.interfaces import INSTerm
    from ._core import TwoPhaseSimulation


class SimulationBuilder:
    """Legacy ``TwoPhaseSimulation`` を段階的に組み立てるビルダー。

    Parameters
    ----------
    config : SimulationConfig
    """

    def __init__(self, config: SimulationConfig):
        self._config = config
        # オプションで差し替えるコンポーネント（None = デフォルト生成）
        self._ppe_solver: Optional["IPPESolver"] = None
        # NS 各項: 具象型ではなく INSTerm インターフェース型で保持（DIP）
        self._convection: Optional["INSTerm"] = None
        self._viscous: Optional["INSTerm"] = None
        self._gravity: Optional["INSTerm"] = None
        self._surface_tension: Optional["INSTerm"] = None

    # ── カスタムコンポーネントの注入メソッド ─────────────────────────────

    def with_ppe_solver(self, solver: "IPPESolver") -> "SimulationBuilder":
        """カスタム PPE ソルバーを注入する。

        Parameters
        ----------
        solver : IPPESolver を実装した任意のソルバー
        """
        self._ppe_solver = solver
        return self

    def with_convection(self, term: "INSTerm") -> "SimulationBuilder":
        """カスタム対流項を注入する。INSTerm インターフェースを実装した任意の項を受け付ける。"""
        self._convection = term
        return self

    def with_viscous(self, term: "INSTerm") -> "SimulationBuilder":
        """カスタム粘性項を注入する。INSTerm インターフェースを実装した任意の項を受け付ける。"""
        self._viscous = term
        return self

    def with_gravity(self, term: "INSTerm") -> "SimulationBuilder":
        """カスタム重力項を注入する。INSTerm インターフェースを実装した任意の項を受け付ける。"""
        self._gravity = term
        return self

    def with_surface_tension(self, term: "INSTerm") -> "SimulationBuilder":
        """カスタム表面張力項を注入する。INSTerm インターフェースを実装した任意の項を受け付ける。"""
        self._surface_tension = term
        return self

    # ── 構築メソッド ─────────────────────────────────────────────────────

    def build(self) -> "TwoPhaseSimulation":
        """設定とオプション依存関係から TwoPhaseSimulation を組み立てる。

        具象クラスのインスタンス化はすべてここで行う。
        TwoPhaseSimulation.__init__ はこのメソッドが返すオブジェクトを受け取るだけにする。

        Returns
        -------
        sim : 初期化済み TwoPhaseSimulation インスタンス
        """
        from ._core import TwoPhaseSimulation
        components = build_legacy_simulation_components(
            config=self._config,
            ppe_solver=self._ppe_solver,
            convection_term=self._convection,
            viscous_term=self._viscous,
            gravity_term=self._gravity,
            surface_tension_term=self._surface_tension,
        )
        return TwoPhaseSimulation._from_components(components)


# DO NOT DELETE — legacy builder retained per C2.
SimulationBuilderLegacy = SimulationBuilder
