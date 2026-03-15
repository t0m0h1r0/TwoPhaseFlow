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

使用例::

    from twophase.simulation.builder import SimulationBuilder
    from twophase.config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0)),
        fluid=FluidConfig(Re=100., Fr=1., We=10.),
        numerics=NumericsConfig(t_end=1.0),
    )
    sim = SimulationBuilder(cfg).build()

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
from ..core.field import ScalarField, VectorField
from ..core.components import SimulationComponents
from ..levelset.heaviside import update_properties


class TwoPhaseSimulation:
    """二相流ソルバー。

    このクラスは直接インスタンス化しないこと。
    SimulationBuilder を通じて構築すること::

        from twophase.simulation.builder import SimulationBuilder
        sim = SimulationBuilder(config).build()
    """

    # ── Builder 用ファクトリメソッド ─────────────────────────────────────

    @classmethod
    def _from_components(
        cls,
        components: SimulationComponents,
    ) -> "TwoPhaseSimulation":
        """SimulationBuilder が生成したコンポーネントから TwoPhaseSimulation を組み立てる。

        このメソッドは SimulationBuilder のみが呼び出すことを意図している。
        外部からは SimulationBuilder を使用すること。
        """
        obj = cls.__new__(cls)
        c = components
        obj.config  = c.config
        obj.backend = c.backend
        obj.grid    = c.grid
        obj.eps     = c.eps
        obj.ccd     = c.ccd

        # フィールドの初期化
        obj.psi      = ScalarField(c.grid, c.backend)
        obj.rho      = ScalarField(c.grid, c.backend)
        obj.mu       = ScalarField(c.grid, c.backend)
        obj.kappa    = ScalarField(c.grid, c.backend)
        obj.pressure = ScalarField(c.grid, c.backend)
        obj.velocity = VectorField(c.grid, c.backend)
        obj.vel_star = VectorField(c.grid, c.backend)

        # サブモジュールの設定
        obj.ls_advect      = c.ls_advect
        obj.ls_reinit      = c.ls_reinit
        obj.curvature_calc = c.curvature_calc
        obj.predictor      = c.predictor
        obj.ppe_solver     = c.ppe_solver
        obj.rhie_chow      = c.rhie_chow
        obj.vel_corrector  = c.vel_corrector
        obj.cfl_calc       = c.cfl_calc
        obj._bc_handler    = c.bc_handler
        obj._diagnostics   = c.diagnostics

        # 状態変数
        obj.time = 0.0
        obj.step = 0

        # 無次元流体物性
        obj._rho_l = 1.0
        obj._rho_g = c.config.fluid.rho_ratio
        obj._mu_l  = 1.0
        obj._mu_g  = c.config.fluid.mu_ratio

        return obj

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
        t_end           : 終了時刻（デフォルト: config.numerics.t_end）
        output_interval : N ステップごとに診断を出力
        verbose         : True の場合、ステップごとに情報を出力
        callback        : f(sim) — output_interval ステップごとに呼ばれる
        """
        if t_end is None:
            t_end = self.config.numerics.t_end

        # 初期 ψ から物性を初期化
        self._update_properties()
        self._update_curvature()

        while self.time < t_end:
            dt = self.cfl_calc.compute(
                [self.velocity[ax] for ax in range(self.config.grid.ndim)],
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
        ndim = self.config.grid.ndim

        # Step 1: CLS 移流 ──────────────────────────────────────────────
        vel_components = [self.velocity[ax] for ax in range(ndim)]
        psi_adv = self.ls_advect.advance(self.psi.data, vel_components, dt)

        # Step 2: 再初期化 ────────────────────────────────────────────────
        psi_new = self.ls_reinit.reinitialize(psi_adv)
        self.psi.data = psi_new

        # Step 3: 物性更新 ────────────────────────────────────────────────
        self._update_properties()

        # Step 4: 曲率更新 ────────────────────────────────────────────────
        self._update_curvature()

        # Step 5: 予測速度 u* ─────────────────────────────────────────────
        vel_n = [self.velocity[ax] for ax in range(ndim)]
        vel_star_list = self.predictor.compute(
            vel_n,
            self.rho.data,
            self.mu.data,
            self.kappa.data,
            self.psi.data,
            dt,
        )
        for ax in range(ndim):
            self.vel_star[ax] = vel_star_list[ax]

        # Step 6: PPE 求解 ─────────────────────────────────────────────────
        div_rc = self.rhie_chow.face_velocity_divergence(
            [self.vel_star[ax] for ax in range(ndim)],
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
            [self.vel_star[ax] for ax in range(ndim)],
            self.pressure.data,
            self.rho.data,
            dt,
        )
        for ax in range(ndim):
            self.velocity[ax] = vel_new[ax]

        # 境界条件の適用
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
