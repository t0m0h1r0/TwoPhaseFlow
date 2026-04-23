"""
legacy トップレベル タイムステップ ループ。

§9.1 の完全な 7 ステップアルゴリズム (Eq. 85–94) を実装する。

各タイムステップの処理:

  Step 1 — CLS 移流（WENO5 + TVD-RK3）
  Step 2 — 再初期化（疑似時間 PDE）
  Step 3 — 物性更新（ρ̃, μ̃）
  Step 4 — 曲率（φ ← H_ε^{-1}(ψ), κ ← CCD）
  Step 5 — 予測速度 u*（AB2 対流 + CN 粘性 + 重力 [+ 表面張力 if CSF] − ∇p^n [IPC]）
  Step 6 — PPE 求解（GFM: DCCD-filtered div + GFM corr / CSF: Rhie-Chow div）→ δp
  Step 7 — 速度・圧力補正 u^{n+1} = u* − (Δt/ρ̃) ∇(δp);  p^{n+1} = p^n + δp

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
from typing import Optional, Callable, List

from ..core.components import SimulationComponents
from ..core.flow_state import FlowState
from .legacy_component_binding import bind_legacy_simulation_components
from .legacy_flow_helpers import (
    advance_legacy_levelset,
    build_legacy_flow_state,
    correct_legacy_velocity,
    predict_legacy_velocity,
    solve_legacy_ppe,
    update_legacy_curvature,
    update_legacy_properties,
)
from .legacy_run_loop import (
    advance_legacy_step_with_retry,
    has_nonfinite_legacy_state,
    run_legacy_simulation,
)


class TwoPhaseSimulation:
    """Legacy 二相流ソルバー。

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
        bind_legacy_simulation_components(obj, components)
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
        run_legacy_simulation(
            self,
            t_end=t_end,
            output_interval=output_interval,
            verbose=verbose,
            callback=callback,
        )

    def _step_with_retry(self, dt_nominal: float, verbose: bool = False) -> float:
        """Advance one step with rollback + dt-halving retries.

        Returns
        -------
        float
            Accepted dt used for this step.
        """
        return advance_legacy_step_with_retry(self, dt_nominal, verbose=verbose)

    def _has_nonfinite_state(self) -> bool:
        """True when any primary field contains NaN/Inf."""
        return has_nonfinite_legacy_state(self)

    def step_forward(self, dt: float) -> None:
        """タイムステップ dt で 1 ステップ進める（§9.1 の 7 ステップアルゴリズム）。

        各物理ステップはプライベートメソッドに委譲する。
        このメソッドはオーケストレーションのみを担う（SRP）。
        """
        # Steps 1–2: CLS 移流 + 再初期化
        self._step_advect_reinit(dt)

        # Step 3: 物性更新（ρ̃, μ̃）
        self._update_properties()

        # Step 4: 曲率更新（κ）
        self._update_curvature()

        # Step 5: 予測速度 u*（AB2+IPC: state.pressure = p^n を使用）
        # Extension PDE: p^n を界面越しに延長してから IPC ∇p^n を CCD で計算
        # （NullFieldExtender の場合は p^n をそのまま返す）
        n_hat = self._field_ext.compute_normal(self.phi.data)
        p_ext = self._field_ext.extend(
            self.pressure.data, self.phi.data, n_hat,
        )
        state = self._build_flow_state_with_pressure(p_ext)
        vel_star = self._step_predictor(state, dt)

        # Step 5b: 壁面 BC を u* に適用（wall BC のみ）
        # PPE RHS 構築（Rhie-Chow or DCCD フィルタ）が u* を参照する前に
        # ノースリップ条件を強制する．これを省略すると IPC 圧力勾配の
        # コーナー非対称性（pin ノード p=0 に起因）が u* 壁面成分を
        # 非ゼロにし，PPE RHS に誤差を与えて発散を招く．
        self._bc_handler.apply(self.vel_star)

        # Step 6: PPE 求解 → δp（IPC 増分法; p^{n+1} = p^n + δp を内部で更新）
        delta_p = self._step_ppe(vel_star, dt)

        # Step 7: 速度補正 u^{n+1} = u* − (Δt/ρ̃) ∇(δp)
        self._step_correct_velocity(vel_star, delta_p, dt)

        self._bc_handler.apply(self.velocity)
        self.time += dt
        self.step += 1

    # ── ステップ別プライベートメソッド ────────────────────────────────────────

    def _build_flow_state_with_pressure(self, pressure) -> FlowState:
        """延長済み圧力を使った FlowState を構築する（Extension PDE 用）。"""
        return build_legacy_flow_state(self, pressure)

    def _step_advect_reinit(self, dt: float) -> None:  # modifies self.psi in-place
        """Step 1–2: CLS 移流（WENO5+TVD-RK3）→ 再初期化（疑似時間 PDE）。"""
        advance_legacy_levelset(self, dt)

    def _step_predictor(self, state: FlowState, dt: float) -> List:
        """Step 5: 予測速度 u* を計算し vel_star フィールドに格納する。

        Returns
        -------
        vel_star : list of arrays  (u* の各速度成分)
        """
        return predict_legacy_velocity(self, state, dt)

    def _step_ppe(self, vel_star: List, dt: float) -> object:
        """Step 6: PPE RHS 構築 → PPE 求解（IPC 増分法） → δp を返す。

        Two paths depending on surface_tension_model config:
          - GFM (§8e + §7 sec:dccd_decoupling):
              RHS = DCCD-filtered CCD divergence + GFM correction
          - CSF (legacy, §2b):
              RHS = Rhie-Chow face-velocity divergence

        IPC 増分法（§4 sec:ipc_derivation, §9 Step 6）:
            PPE は圧力増分 δp ≡ p^{n+1}−p^n を求解対象とする
            求解後 p^{n+1} = p^n + δp で圧力場を更新する．

        Returns
        -------
        delta_p : 圧力増分 δp（速度 Corrector に渡す）
        """
        return solve_legacy_ppe(self, vel_star, dt)

    def _step_correct_velocity(self, vel_star: List, delta_p: object, dt: float) -> None:  # modifies self.velocity in-place
        """Step 7: u* − (Δt/ρ̃)∇(δp) → u^{n+1} を velocity フィールドに書き込む。

        IPC 増分法: 速度補正には圧力増分 δp の勾配を使用する（§9 Step 7）．
        絶対圧力 p^{n+1} の勾配ではなく δp の勾配である点に注意．

        Extension PDE (Aslam 2004): δp を界面越しに滑らかに延長してから
        CCD ∇(δp) を計算する（NullFieldExtender の場合は δp をそのまま返す）．
        """
        correct_legacy_velocity(self, vel_star, delta_p, dt)

    # ── プライベートヘルパー ───────────────────────────────────────────────

    def _update_properties(self) -> None:
        update_legacy_properties(self)

    def _update_curvature(self) -> None:
        update_legacy_curvature(self)


# DO NOT DELETE — legacy split-step simulation core retained per C2.
TwoPhaseSimulationLegacy = TwoPhaseSimulation
