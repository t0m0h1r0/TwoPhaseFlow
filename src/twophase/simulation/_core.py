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

from ..backend import Backend
from ..config import SimulationConfig
from ..core.field import ScalarField, VectorField
from ..core.components import SimulationComponents
from ..core.flow_state import FlowState
from ..levelset.heaviside import update_properties, invert_heaviside
from ..levelset.field_extender import NullFieldExtender
from .legacy_simulation_state import (
    restore_legacy_simulation,
    snapshot_legacy_simulation,
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
        obj.phi      = ScalarField(c.grid, c.backend)   # cached φ = H_ε⁻¹(ψ) from Step 4
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
        obj._ppe_rhs_gfm   = c.ppe_rhs_gfm  # None when CSF mode
        obj._field_ext     = c.field_extender  # NullFieldExtender when disabled
        obj._needs_phi     = (c.field_extender is not None
                              and not c.field_extender.is_null_extender
                              ) or (c.ppe_rhs_gfm is not None)

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
            dt_nominal = self.cfl_calc.compute(
                [self.velocity[ax] for ax in range(self.config.grid.ndim)],
                self.mu.data,
                self.rho.data,
            )
            dt_nominal = min(dt_nominal, t_end - self.time)

            # Adaptive safety fallback:
            # If a step produces non-finite state (or raises), rollback and retry
            # with dt halved. This keeps long runs from hard-failing at the first
            # unstable CFL estimate.
            dt = self._step_with_retry(dt_nominal, verbose=verbose)

            if verbose and self.step % output_interval == 0:
                self._diagnostics.report(self, dt)
            if callback is not None and self.step % output_interval == 0:
                callback(self)

        if verbose:
            print(f"シミュレーション終了 t={self.time:.6f}, step={self.step}")

    def _step_with_retry(self, dt_nominal: float, verbose: bool = False) -> float:
        """Advance one step with rollback + dt-halving retries.

        Returns
        -------
        float
            Accepted dt used for this step.
        """
        max_retries = 12
        dt_try = float(dt_nominal)

        snapshot = snapshot_legacy_simulation(self)

        for retry in range(max_retries + 1):
            try:
                self.step_forward(dt_try)
                if self._has_nonfinite_state():
                    raise FloatingPointError("non-finite state after step")
                return dt_try
            except Exception:
                # Roll back all mutable fields + counters before retry.
                restore_legacy_simulation(self, snapshot)

                if retry >= max_retries:
                    raise
                dt_try *= 0.5
                if verbose:
                    print(
                        f"[run] step retry {retry + 1}/{max_retries}: "
                        f"reducing dt to {dt_try:.3e}"
                    )

        return dt_try

    def _has_nonfinite_state(self) -> bool:
        """True when any primary field contains NaN/Inf."""
        xp = self.backend.xp
        fields = [
            self.psi.data,
            self.rho.data,
            self.mu.data,
            self.kappa.data,
            self.phi.data,
            self.pressure.data,
        ]
        fields.extend(self.velocity[ax] for ax in range(self.config.grid.ndim))
        fields.extend(self.vel_star[ax] for ax in range(self.config.grid.ndim))
        return any(bool(xp.any(~xp.isfinite(arr))) for arr in fields)

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
        ndim = self.config.grid.ndim
        return FlowState(
            velocity=[self.velocity[ax] for ax in range(ndim)],
            psi=self.psi.data,
            rho=self.rho.data,
            mu=self.mu.data,
            kappa=self.kappa.data,
            pressure=pressure,
        )

    def _step_advect_reinit(self, dt: float) -> None:  # modifies self.psi in-place
        """Step 1–2: CLS 移流（WENO5+TVD-RK3）→ 再初期化（疑似時間 PDE）。"""
        ndim = self.config.grid.ndim
        vel_components = [self.velocity[ax] for ax in range(ndim)]
        psi_adv = self.ls_advect.advance(self.psi.data, vel_components, dt)
        self.psi.data = self.ls_reinit.reinitialize(psi_adv)

    def _step_predictor(self, state: FlowState, dt: float) -> List:
        """Step 5: 予測速度 u* を計算し vel_star フィールドに格納する。

        Returns
        -------
        vel_star : list of arrays  (u* の各速度成分)
        """
        ndim = self.config.grid.ndim
        vel_star_list = self.predictor.compute(state, dt)
        for ax in range(ndim):
            self.vel_star[ax] = vel_star_list[ax]
        return [self.vel_star[ax] for ax in range(ndim)]

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
        if self._ppe_rhs_gfm is not None:
            # GFM path (§8e Eq. gfm_ccd_div):
            # q_h = (1/dt) div(u_tilde*) + b^GFM
            # phi cached in _update_curvature (Step 4) to avoid redundant inversion
            rhs = self._ppe_rhs_gfm.build_rhs(
                vel_star, self.phi.data, self.kappa.data, self.rho.data, dt,
            )
        else:
            # CSF/Rhie-Chow path (legacy):
            # Rhie-Chow 補正発散: self.pressure.data = p^n
            div_rc = self.rhie_chow.face_velocity_divergence(
                vel_star, self.pressure.data, self.rho.data, dt,
            )
            rhs = div_rc / dt

        # δp を解く（IPC: 初期値 0）
        delta_p = self.ppe_solver.solve(
            rhs, self.rho.data, dt, p_init=None,
        )
        # p^{n+1} = p^n + δp（§9 Step 7 の圧力更新）
        self.pressure.data = self.pressure.data + delta_p
        return delta_p   # 速度 Corrector は ∇(δp) を適用する

    def _step_correct_velocity(self, vel_star: List, delta_p: object, dt: float) -> None:  # modifies self.velocity in-place
        """Step 7: u* − (Δt/ρ̃)∇(δp) → u^{n+1} を velocity フィールドに書き込む。

        IPC 増分法: 速度補正には圧力増分 δp の勾配を使用する（§9 Step 7）．
        絶対圧力 p^{n+1} の勾配ではなく δp の勾配である点に注意．

        Extension PDE (Aslam 2004): δp を界面越しに滑らかに延長してから
        CCD ∇(δp) を計算する（NullFieldExtender の場合は δp をそのまま返す）．
        """
        ndim = self.config.grid.ndim
        n_hat = self._field_ext.compute_normal(self.phi.data)
        delta_p = self._field_ext.extend(delta_p, self.phi.data, n_hat)
        vel_new = self.vel_corrector.correct(vel_star, delta_p, self.rho.data, dt)
        for ax in range(ndim):
            self.velocity[ax] = vel_new[ax]

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
        # Cache φ = H_ε⁻¹(ψ) for GFM PPE RHS (Step 6).
        # Only computed when GFM is active; CurvatureCalculator also inverts
        # ψ→φ internally, so this is a second inversion.  Eliminating it
        # would require passing pre-computed φ through ICurvatureCalculator,
        # which is too invasive for this change.
        if self._needs_phi:
            self.phi.data = invert_heaviside(self.backend.xp, self.psi.data, self.eps)


# DO NOT DELETE — legacy split-step simulation core retained per C2.
TwoPhaseSimulationLegacy = TwoPhaseSimulation
