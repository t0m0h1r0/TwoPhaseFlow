"""
SimulationBuilder — TwoPhaseSimulation の構築を担うビルダー。

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

    from twophase.pressure.ppe_solver_pseudotime import PPESolverPseudoTime
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

from ..backend import Backend
from ..config import SimulationConfig
from ..core.grid import Grid
from ..core.field import ScalarField, VectorField
from ..core.components import SimulationComponents
from ..ccd.ccd_solver import CCDSolver
from ..levelset.advection import LevelSetAdvection
from ..levelset.reinitialize import Reinitializer
from ..levelset.curvature import CurvatureCalculator
from ..ns_terms.predictor import Predictor
from ..ns_terms.convection import ConvectionTerm
from ..ns_terms.viscous import ViscousTerm
from ..ns_terms.gravity import GravityTerm
from ..ns_terms.surface_tension import SurfaceTensionTerm
from ..pressure.rhie_chow import RhieChowInterpolator
from ..pressure.ppe_solver_factory import create_ppe_solver
from ..pressure.velocity_corrector import VelocityCorrector
from ..time_integration.cfl import CFLCalculator
from .boundary_condition import BoundaryConditionHandler
from .diagnostics import DiagnosticsReporter

if TYPE_CHECKING:
    from ..interfaces.ppe_solver import IPPESolver
    from ..interfaces.ns_terms import INSTerm
    from ._core import TwoPhaseSimulation


class SimulationBuilder:
    """TwoPhaseSimulation を段階的に組み立てるビルダー。

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

        # 基盤インフラの生成
        config = self._config
        backend = Backend(use_gpu=config.use_gpu)

        grid = Grid(config.grid, backend)
        dx_min = min(
            config.grid.L[ax] / config.grid.N[ax]
            for ax in range(config.grid.ndim)
        )
        eps = config.numerics.epsilon_factor * dx_min
        ccd = CCDSolver(grid, backend)

        # レベルセット演算子
        ls_advect = LevelSetAdvection(backend, grid)
        ls_reinit = Reinitializer(backend, grid, ccd, eps, config.numerics.reinit_steps)
        curvature_calc = CurvatureCalculator(backend, ccd, eps)

        # NS 各項（注入または自動生成）— ccd はコンストラクタ注入（ISP改善）
        predictor = Predictor(
            backend, config, ccd,
            convection=self._convection,
            viscous=self._viscous,
            gravity=self._gravity,
            surface_tension=self._surface_tension,
        )

        # 圧力ソルバー（注入または factory 経由）
        # ccd を渡すことで PPESolverPseudoTime が CCD matrix-free O(h⁶) を使用できる
        ppe_solver = self._ppe_solver or create_ppe_solver(config, backend, grid, ccd=ccd)

        # 補助演算子
        rhie_chow = RhieChowInterpolator(backend, grid, ccd)
        vel_corrector = VelocityCorrector(backend, grid)
        cfl_calc = CFLCalculator(
            backend, grid, config.numerics.cfl_number,
            We=config.fluid.We,
            rho_ratio=config.fluid.rho_ratio,
            cn_viscous=config.numerics.cn_viscous,
        )

        # 境界条件・診断
        bc_handler = BoundaryConditionHandler(config)
        diagnostics = DiagnosticsReporter(backend, grid)

        # TwoPhaseSimulation のファクトリメソッドで組み立て
        return TwoPhaseSimulation._from_components(
            SimulationComponents(
                config=config,
                backend=backend,
                grid=grid,
                eps=eps,
                ccd=ccd,
                ls_advect=ls_advect,
                ls_reinit=ls_reinit,
                curvature_calc=curvature_calc,
                predictor=predictor,
                ppe_solver=ppe_solver,
                rhie_chow=rhie_chow,
                vel_corrector=vel_corrector,
                cfl_calc=cfl_calc,
                bc_handler=bc_handler,
                diagnostics=diagnostics,
            )
        )
