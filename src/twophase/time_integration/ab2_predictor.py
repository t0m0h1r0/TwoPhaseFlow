"""
Velocity predictor step (u* computation) — AB2 + IPC formulation.

Implements Step 5 of the full algorithm (§9.1 Eq. 85–92).

The predictor solves (AB2 + IPC formulation, §4 Eq. eq:predictor_ab2_ipc):

    ρ̃^{n+1} (u* − uⁿ) / Δt = R^{n+1}

where the RHS collects:

    R = −ρ̃ [3/2 C(uⁿ) − 1/2 C(uⁿ⁻¹)]  (convection, AB2 explicit; n=0: Euler)
      + 1/2 (1/Re) ∇·[μ̃ (∇u*+∇u*ᵀ)]
        + 1/2 (1/Re) ∇·[μ̃ (∇uⁿ+∇uⁿᵀ)]   (viscous, Crank-Nicolson or explicit)
      − ∇pⁿ                               (IPC: explicit old pressure, §4 §ipc_derivation)
      − ρ̃ ẑ / Fr²                         (gravity, explicit)
      + κ ∇ψ / We                         (surface tension, CSF only; zeroed in GFM mode §8e)

where C(u) = (u·∇)u is the convection operator.

The predictor does NOT enforce ∇·u* = 0; that is handled by the pressure
Poisson equation (solved for δp = p^{n+1}−pⁿ) and the corrector step.

AB2 startup (§4 warn:tvd_rk3_scope):
    n=0 (first step): forward Euler, C^{−1} unavailable.
    n≥1: AB2 with coefficients (3/2, −1/2).
    After each step the convection term C^n is buffered for the next step.

IPC (Incremental Pressure Correction, §4 sec:ipc_derivation):
    Explicitly adds −∇pⁿ to the predictor RHS so that the PPE only needs
    to solve for the pressure increment δp, reducing splitting errors from
    O(Δt) (Chorin) to O(Δt²) (van Kan 1986).

Note: Moved from ns_terms/predictor.py to time_integration/ to align with the
time-integration module structure.  ``twophase.ns_terms.predictor.Predictor``
remains valid as a C2 backward-compatible re-export.
"""

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

from ..ns_terms.convection import ConvectionTerm
from ..ns_terms.viscous import ViscousTerm
from ..ns_terms.gravity import GravityTerm
from ..ns_terms.surface_tension import SurfaceTensionTerm
from ..ns_terms.context import NSComputeContext
from ..core.flow_state import FlowState
from ..coupling.velocity_corrector import ccd_pressure_gradient

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..ns_terms.interfaces import INSTerm


class Predictor:
    """Assemble all NS RHS terms and advance u → u* via AB2 + IPC.

    Parameters
    ----------
    backend        : Backend
    config         : SimulationConfig
    ccd            : CCDSolver — コンストラクタ注入（毎呼び出しでの引き渡し不要）
    convection     : ConvectionTerm インスタンス（省略時はデフォルト生成）
    viscous        : ViscousTerm インスタンス（省略時はデフォルト生成）
    gravity        : GravityTerm インスタンス（省略時はデフォルト生成）
    surface_tension: SurfaceTensionTerm インスタンス（省略時はデフォルト生成）

    注: 各項を外部から注入することで、テスト・差し替えが容易になる（DIP）。
        引数を省略した場合は config の値から自動生成し、後方互換を保つ。
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        ccd: "CCDSolver",
        convection: Optional["INSTerm"] = None,
        viscous: Optional["INSTerm"] = None,
        gravity: Optional["INSTerm"] = None,
        surface_tension: Optional["INSTerm"] = None,
        use_gfm: bool = False,
    ):
        self.xp = backend.xp
        self.config = config
        self.ccd = ccd   # コンストラクタ注入
        # GFM mode (§8e): when True, surface tension is handled in PPE RHS
        # via GFMCorrector, NOT as a volume force in the predictor.
        self.use_gfm = use_gfm

        # 注入された依存関係を使用。省略時はデフォルト生成
        self.convection   = convection    or ConvectionTerm(backend)
        if viscous is None:
            from .cn_advance import make_cn_advance
            viscous = ViscousTerm(
                backend, config.fluid.Re, config.numerics.cn_viscous,
                cn_advance=make_cn_advance(backend, config.numerics.cn_mode),
            )
        self.viscous      = viscous
        self.gravity      = gravity       or GravityTerm(backend, config.fluid.Fr, config.grid.ndim)
        self.surface_tens = surface_tension or SurfaceTensionTerm(backend, config.fluid.We)

        # AB2 スタートアップ用バッファ（§4 warn:tvd_rk3_scope）
        # _conv_prev: 前ステップの対流項 C^{n-1}（各速度成分のリスト）
        # _ab2_ready: True のとき AB2 係数を使用；False のとき前進 Euler
        self._conv_prev: Optional[List] = None
        self._ab2_ready: bool = False

    def compute(self, state: FlowState, dt: float) -> List:
        """Compute u* using AB2 convection + IPC + CN/explicit viscous.

        Implements §9 Step 5 (Eq. eq:predictor_ab2_ipc):

            ρ(u*−uⁿ)/Δt = −ρ[3/2 C^n − 1/2 C^{n−1}] + viscous − ∇p^n + gravity + ST

        AB2 startup: first call uses forward Euler (C^{−1} unavailable).

        Parameters
        ----------
        state : FlowState
            現タイムステップの流体場（velocity, psi, rho, mu, kappa, pressure）。
        dt    : float
            タイムステップ幅。

        Returns
        -------
        vel_star : list of u* arrays  (ndim 個)
        """
        ccd  = self.ccd
        ndim = self.config.grid.ndim
        vel_n = state.velocity
        rho   = state.rho
        mu    = state.mu
        kappa = state.kappa
        psi   = state.psi

        # Build context for all NS terms
        ctx = NSComputeContext(
            velocity=vel_n,
            ccd=ccd,
            rho=rho,
            mu=mu,
            kappa=kappa,
            psi=psi,
        )

        # ── 対流項 C^n = −(u·∇)u （負符号を含む） ──────────────────────────
        conv_n = self.convection.compute(ctx)   # C^n = −(u·∇)u

        # ── AB2 外挿（§4 eq:predictor_ab2_ipc） ──────────────────────────
        # n=0（スタートアップ）: 前進 Euler → ab2_conv = conv_n
        # n≥1: AB2 → ab2_conv = 3/2 * conv_n − 1/2 * conv_prev
        if self._ab2_ready and self._conv_prev is not None:
            ab2_conv = [
                1.5 * conv_n[c] - 0.5 * self._conv_prev[c]
                for c in range(ndim)
            ]
        else:
            ab2_conv = conv_n   # 前進 Euler（n=0）

        # ── 重力・表面張力（陽的，t^{n+1}） ─────────────────────────────
        grav = self.gravity.compute(ctx)   # −ρ̃/Fr² ẑ
        # GFM mode (§8e sec:gfm): surface tension is handled in PPE RHS
        # via GFMCorrector; predictor does NOT include CSF volume force.
        if self.use_gfm:
            st = [self.xp.zeros_like(vel_n[c]) for c in range(ndim)]
        else:
            st = self.surface_tens.compute(ctx)  # κ ∇ψ/We (CSF)

        # ── IPC 項 −∇p^n（§4 sec:ipc_derivation） ────────────────────────
        # van Kan (1986) の増分圧力補正：前時刻圧力 p^n を陽的に加える
        # これにより PPE は圧力増分 δp = p^{n+1}−p^n を解くだけでよくなり
        # スプリッティング誤差が O(Δt) → O(Δt²) に改善する
        # CCD D^{(1)} を使用することで balanced-force 条件を満たす（§7 warnbox）:
        # 表面張力 κ D^{(1)} ψ/We と同一演算子により寄生流れが O(h⁶) まで低減する
        grad_pn = ccd_pressure_gradient(ccd, state.pressure, ndim)
        ipc = [-g for g in grad_pn]

        # ── 陽的 RHS の組み立て ────────────────────────────────────────
        # ρ × ab2_conv = −ρ[3/2 C^n − 1/2 C^{n-1}]（対流項）
        # grav = −ρ̃/Fr² ẑ（重力項，ρ 因子あり）
        # st   = κ∇ψ/We（表面張力，ρ 因子なし）
        # ipc  = −∇p^n（IPC 圧力項）
        explicit_rhs = [
            rho * ab2_conv[c] + grav[c] + st[c] + ipc[c]
            for c in range(ndim)
        ]

        # ── 粘性項（CN または陽的） ────────────────────────────────────
        if self.config.numerics.cn_viscous:
            vel_star = self.viscous.apply_cn_predictor(
                vel_n, explicit_rhs, mu, rho, ccd, dt
            )
        else:
            visc = self.viscous.compute_explicit(vel_n, mu, rho, ccd)
            vel_star = [
                vel_n[c] + dt * (explicit_rhs[c] + rho * visc[c]) / rho
                for c in range(ndim)
            ]

        # ── AB2 バッファ更新 ──────────────────────────────────────────
        # conv_n を保存して次ステップの AB2 の「前ステップ項」として使用する
        # コピーが必要（conv_n は ccd から返る配列で次ステップで上書きされる）
        xp = self.xp
        self._conv_prev = [xp.copy(conv_n[c]) for c in range(ndim)]
        self._ab2_ready = True

        return vel_star
