"""
トップレベル タイムステップ ループ。

§9.1 の完全な 7 ステップアルゴリズム (Eq. 85–94) を実装する。

各タイムステップの処理:

  Step 1 — CLS 移流（WENO5 + TVD-RK3）
  Step 2 — 再初期化（疑似時間 PDE）
  Step 3 — 物性更新（ρ̃, μ̃）
  Step 4 — 曲率（φ ← H_ε^{-1}(ψ), κ ← CCD）
  Step 5 — 予測速度 u*（対流 + 粘性 + 重力 + 表面張力）
  Step 6 — PPE 求解（Rhie-Chow div + IPPESolver）
  Step 7 — 速度修正 u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}

SOLID リファクタリング後の変更点:
    - ``ppe_builder`` の直接管理を廃止。PPEBuilder は PPESolver 内部に移動。
    - ``isinstance(ppe_solver, PPESolverPseudoTime)`` チェックを廃止（LSP修正）。
    - ``_apply_wall_bc()`` を BoundaryConditionHandler に委譲（SRP修正）。
    - ``_print_diagnostics()`` を DiagnosticsReporter に委譲（SRP修正）。
    - ``create_ppe_solver()`` ファクトリ経由でソルバーを取得（DIP修正）。

使用例::

    from twophase import SimulationConfig, TwoPhaseSimulation
    import numpy as np

    cfg = SimulationConfig(ndim=2, N=(64, 64), L=(1.0, 1.0),
                           Re=100., Fr=1., We=10.,
                           rho_ratio=0.1, mu_ratio=0.1, t_end=1.0)
    sim = TwoPhaseSimulation(cfg)

    X, Y = sim.grid.meshgrid()
    sim.psi.data[:] = 1.0 / (1.0 + np.exp(
        -(np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.2) / (1.5 / 64)
    ))
    sim.run(output_interval=20, verbose=True)
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Callable, TYPE_CHECKING

from ..backend import Backend
from ..config import SimulationConfig
from ..core.grid import Grid
from ..core.field import ScalarField, VectorField
from ..ccd.ccd_solver import CCDSolver
from ..levelset.heaviside import heaviside, update_properties, invert_heaviside
from ..levelset.curvature import CurvatureCalculator
from ..levelset.advection import LevelSetAdvection
from ..levelset.reinitialize import Reinitializer
from ..ns_terms.predictor import Predictor
from ..pressure.rhie_chow import RhieChowInterpolator
from ..pressure.ppe_solver_factory import create_ppe_solver
from ..pressure.velocity_corrector import VelocityCorrector
from ..time_integration.cfl import CFLCalculator
from .boundary_condition import BoundaryConditionHandler
from .diagnostics import DiagnosticsReporter


class TwoPhaseSimulation:
    """二相流ソルバー。

    Parameters
    ----------
    config : SimulationConfig

    注: 推奨される構築方法は SimulationBuilder を使用すること。
        直接コンストラクタ呼び出し（後方互換）も引き続き動作する。

    例（後方互換）::

        sim = TwoPhaseSimulation(config)

    例（Builder 経由）::

        from twophase.simulation.builder import SimulationBuilder
        sim = SimulationBuilder(config).build()
        # または カスタムソルバーを注入:
        sim = SimulationBuilder(config).with_ppe_solver(my_solver).build()
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.backend = Backend(use_gpu=config.use_gpu)
        xp = self.backend.xp

        # ── グリッド ──────────────────────────────────────────────────────
        self.grid = Grid(config, self.backend)

        # ── 界面厚さ ε ────────────────────────────────────────────────────
        dx_min = min(config.L[ax] / config.N[ax] for ax in range(config.ndim))
        self.eps = config.epsilon_factor * dx_min

        # ── CCD ソルバー ──────────────────────────────────────────────────
        self.ccd = CCDSolver(self.grid, self.backend)

        # ── フィールド ────────────────────────────────────────────────────
        # レベルセット ψ（Conservative Level Set, ψ ∈ [0,1]）
        self.psi = ScalarField(self.grid, self.backend)

        # 派生フィールド
        self.rho = ScalarField(self.grid, self.backend)
        self.mu  = ScalarField(self.grid, self.backend)
        self.kappa = ScalarField(self.grid, self.backend)
        self.pressure = ScalarField(self.grid, self.backend)

        # 速度場（VectorField として保持）
        self.velocity = VectorField(self.grid, self.backend)
        self.vel_star = VectorField(self.grid, self.backend)

        # ── サブモジュール ────────────────────────────────────────────────
        self.ls_advect = LevelSetAdvection(self.backend)
        self.ls_advect.set_grid(self.grid)

        self.ls_reinit = Reinitializer(
            self.backend, self.grid, self.ccd, self.eps, config.reinit_steps
        )

        self.curvature_calc = CurvatureCalculator(self.backend, self.ccd, self.eps)
        self.predictor = Predictor(self.backend, config)
        self.rhie_chow = RhieChowInterpolator(self.backend, self.grid, self.ccd)

        # ファクトリ経由で IPPESolver を取得（DIP: 具体クラスに依存しない）
        self.ppe_solver = create_ppe_solver(config, self.backend, self.grid)

        self.vel_corrector = VelocityCorrector(self.backend, self.ccd)
        self.cfl_calc = CFLCalculator(self.backend, self.grid, config.cfl_number)

        # 境界条件と診断を独立クラスに委譲（SRP修正）
        self._bc_handler = BoundaryConditionHandler(config)
        self._diagnostics = DiagnosticsReporter(self.backend, self.grid)

        # ── シミュレーション時刻 ──────────────────────────────────────────
        self.time: float = 0.0
        self.step: int = 0

        # ── 無次元流体物性 ────────────────────────────────────────────────
        # 論文の無次元化: ρ_l = 1, ρ_g = rho_ratio
        self._rho_l: float = 1.0
        self._rho_g: float = config.rho_ratio
        self._mu_l: float = 1.0
        self._mu_g: float = config.mu_ratio

    # ── 公開 API ──────────────────────────────────────────────────────────

    def run(
        self,
        t_end: Optional[float] = None,
        output_interval: int = 10,
        verbose: bool = True,
        callback: Optional[Callable] = None,
    ) -> None:
        """``self.time`` から ``t_end`` まで時間積分する。

        Parameters
        ----------
        t_end           : 終了時刻（デフォルト: config.t_end）
        output_interval : N ステップごとに診断を出力
        verbose         : True の場合、ステップごとに情報を出力
        callback        : f(sim) — output_interval ステップごとに呼ばれる
        """
        if t_end is None:
            t_end = self.config.t_end

        # 初期 ψ から物性を初期化
        self._update_properties()
        self._update_curvature()

        while self.time < t_end:
            dt = self.cfl_calc.compute(
                [self.velocity[ax] for ax in range(self.config.ndim)],
                self.mu.data,
                self.rho.data,
            )
            dt = min(dt, t_end - self.time)

            self.step_forward(dt)

            if verbose and self.step % output_interval == 0:
                self._diagnostics.report(self, dt)
            if callback is not None and self.step % output_interval == 0:
                callback(self)

        if verbose:
            print(f"シミュレーション終了 t={self.time:.6f}, step={self.step}")

    def step_forward(self, dt: float) -> None:
        """タイムステップ dt で 1 ステップ進める。"""
        xp = self.backend.xp

        # Step 1: CLS 移流 ──────────────────────────────────────────────
        vel_components = [self.velocity[ax] for ax in range(self.config.ndim)]
        psi_adv = self.ls_advect.advance(self.psi.data, vel_components, dt)

        # Step 2: 再初期化 ────────────────────────────────────────────────
        psi_new = self.ls_reinit.reinitialize(psi_adv)
        self.psi.data = psi_new

        # Step 3: 物性更新 ────────────────────────────────────────────────
        self._update_properties()

        # Step 4: 曲率更新 ────────────────────────────────────────────────
        self._update_curvature()

        # Step 5: 予測速度 u* ─────────────────────────────────────────────
        vel_n = [self.velocity[ax] for ax in range(self.config.ndim)]
        vel_star_list = self.predictor.compute(
            vel_n,
            self.rho.data,
            self.mu.data,
            self.kappa.data,
            self.psi.data,
            self.ccd,
            dt,
        )
        for ax in range(self.config.ndim):
            self.vel_star[ax] = vel_star_list[ax]

        # Step 6: PPE 求解 ─────────────────────────────────────────────────
        # isinstance チェックが不要（LSP修正: 統一インターフェース IPPESolver）
        div_rc = self.rhie_chow.face_velocity_divergence(
            [self.vel_star[ax] for ax in range(self.config.ndim)],
            self.pressure.data,
            self.rho.data,
            dt,
        )
        rhs_ppe = div_rc / dt

        p_new = self.ppe_solver.solve(
            rhs_ppe,
            self.rho.data,
            dt,
            p_init=self.pressure.data,
        )
        self.pressure.data = p_new

        # Step 7: 速度修正 ────────────────────────────────────────────────
        vel_new = self.vel_corrector.correct(
            [self.vel_star[ax] for ax in range(self.config.ndim)],
            self.pressure.data,
            self.rho.data,
            dt,
        )
        for ax in range(self.config.ndim):
            self.velocity[ax] = vel_new[ax]

        # 境界条件の適用（BoundaryConditionHandler に委譲: SRP修正）
        self._bc_handler.apply(self.velocity)

        self.time += dt
        self.step += 1

    # ── プライベートヘルパー ───────────────────────────────────────────────

    def _update_properties(self) -> None:
        rho, mu = update_properties(
            self.backend.xp,
            self.psi.data,
            self._rho_l, self._rho_g,
            self._mu_l, self._mu_g,
        )
        self.rho.data = rho
        self.mu.data  = mu

    def _update_curvature(self) -> None:
        self.kappa.data = self.curvature_calc.compute(self.psi.data)

    # ── Builder 用ファクトリメソッド ─────────────────────────────────────

    @classmethod
    def _from_components(
        cls,
        config: SimulationConfig,
        backend,
        grid,
        eps: float,
        ccd,
        ls_advect,
        ls_reinit,
        curvature_calc,
        predictor,
        ppe_solver,
        rhie_chow,
        vel_corrector,
        cfl_calc,
        bc_handler,
        diagnostics,
    ) -> "TwoPhaseSimulation":
        """SimulationBuilder が生成したコンポーネントから TwoPhaseSimulation を組み立てる。

        このメソッドは SimulationBuilder のみが呼び出すことを意図している。
        外部から直接呼び出す場合は SimulationBuilder を使用すること。
        """
        obj = cls.__new__(cls)
        obj.config = config
        obj.backend = backend
        obj.grid = grid
        obj.eps = eps
        obj.ccd = ccd

        # フィールドの初期化
        obj.psi      = ScalarField(grid, backend)
        obj.rho      = ScalarField(grid, backend)
        obj.mu       = ScalarField(grid, backend)
        obj.kappa    = ScalarField(grid, backend)
        obj.pressure = ScalarField(grid, backend)
        obj.velocity = VectorField(grid, backend)
        obj.vel_star = VectorField(grid, backend)

        # サブモジュールの設定
        obj.ls_advect      = ls_advect
        obj.ls_reinit      = ls_reinit
        obj.curvature_calc = curvature_calc
        obj.predictor      = predictor
        obj.ppe_solver     = ppe_solver
        obj.rhie_chow      = rhie_chow
        obj.vel_corrector  = vel_corrector
        obj.cfl_calc       = cfl_calc
        obj._bc_handler    = bc_handler
        obj._diagnostics   = diagnostics

        # 状態変数
        obj.time = 0.0
        obj.step = 0

        # 無次元流体物性
        obj._rho_l = 1.0
        obj._rho_g = config.rho_ratio
        obj._mu_l  = 1.0
        obj._mu_g  = config.mu_ratio

        return obj
