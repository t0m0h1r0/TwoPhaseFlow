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
        self._convection: Optional[ConvectionTerm] = None
        self._viscous: Optional[ViscousTerm] = None
        self._gravity: Optional[GravityTerm] = None
        self._surface_tension: Optional[SurfaceTensionTerm] = None

    # ── カスタムコンポーネントの注入メソッド ─────────────────────────────

    def with_ppe_solver(self, solver: "IPPESolver") -> "SimulationBuilder":
        """カスタム PPE ソルバーを注入する。

        Parameters
        ----------
        solver : IPPESolver を実装した任意のソルバー
        """
        self._ppe_solver = solver
        return self

    def with_convection(self, term: ConvectionTerm) -> "SimulationBuilder":
        """カスタム対流項を注入する。"""
        self._convection = term
        return self

    def with_viscous(self, term: ViscousTerm) -> "SimulationBuilder":
        """カスタム粘性項を注入する。"""
        self._viscous = term
        return self

    def with_gravity(self, term: GravityTerm) -> "SimulationBuilder":
        """カスタム重力項を注入する。"""
        self._gravity = term
        return self

    def with_surface_tension(self, term: SurfaceTensionTerm) -> "SimulationBuilder":
        """カスタム表面張力項を注入する。"""
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

        grid = Grid(config, backend)
        dx_min = min(config.L[ax] / config.N[ax] for ax in range(config.ndim))
        eps = config.epsilon_factor * dx_min
        ccd = CCDSolver(grid, backend)

        # レベルセット演算子
        ls_advect = LevelSetAdvection(backend)
        ls_advect.set_grid(grid)
        ls_reinit = Reinitializer(backend, grid, ccd, eps, config.reinit_steps)
        curvature_calc = CurvatureCalculator(backend, ccd, eps)

        # NS 各項（注入または自動生成）
        predictor = Predictor(
            backend, config,
            convection=self._convection,
            viscous=self._viscous,
            gravity=self._gravity,
            surface_tension=self._surface_tension,
        )

        # 圧力ソルバー（注入または factory 経由）
        ppe_solver = self._ppe_solver or create_ppe_solver(config, backend, grid)

        # 補助演算子
        rhie_chow = RhieChowInterpolator(backend, grid, ccd)
        vel_corrector = VelocityCorrector(backend, ccd)
        cfl_calc = CFLCalculator(backend, grid, config.cfl_number)

        # 境界条件・診断
        bc_handler = BoundaryConditionHandler(config)
        diagnostics = DiagnosticsReporter(backend, grid)

        # TwoPhaseSimulation のファクトリメソッドで組み立て
        return TwoPhaseSimulation._from_components(
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
