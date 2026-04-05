"""
シミュレーション設定 dataclass 群。

§2.4 の無次元化に従う:

    Re = ρ_l U L / μ_l         (Reynolds数)
    Fr = U / sqrt(g L)          (Froude数)
    We = ρ_l U² L / σ           (Weber数)

設計方針:
    - SimulationConfig は 4 つのサブ設定の合成のみを保持する（SRP）。
    - フラットフィールドおよび変換メソッドは廃止。

サブ設定クラス:
    GridConfig      — グリッドジオメトリ・解像度
    FluidConfig     — 流体物性（Re, Fr, We, 密度比, 粘性比）
    NumericsConfig  — 数値スキーム（CFL, ε係数, 再初期化, CN粘性）
    SolverConfig    — PPEソルバー選択とパラメータ
"""

from __future__ import annotations
import warnings
from dataclasses import dataclass, field
from typing import Tuple

from .core.boundary import BCType


# ── サブ設定クラス群 ─────────────────────────────────────────────────────────

@dataclass
class GridConfig:
    """グリッドジオメトリと解像度設定。"""

    # 空間次元 (2 または 3)
    ndim: int = 2
    # 各軸のセル数
    N: Tuple[int, ...] = (64, 64)
    # 物理領域の各軸の長さ
    L: Tuple[float, ...] = (1.0, 1.0)
    # 界面適合グリッドの伸縮係数（§6）; 1.0 = 一様格子
    alpha_grid: float = 1.0
    # セル幅の下限（CCD条件数を防ぐためのフロア値）
    dx_min_floor: float = 1e-6
    # ガウス型グリッド密度関数の幅: ε_g = eps_g_factor × ε（§6 eq:grid_delta）; 推奨 2–4
    eps_g_factor: float = 2.0

    def __post_init__(self) -> None:
        assert self.ndim in (2, 3), f"ndim は 2 か 3 でなければならない: {self.ndim}"
        assert len(self.N) == self.ndim, (
            f"len(N)={len(self.N)} は ndim={self.ndim} と一致しなければならない"
        )
        assert len(self.L) == self.ndim, (
            f"len(L)={len(self.L)} は ndim={self.ndim} と一致しなければならない"
        )


@dataclass
class FluidConfig:
    """流体物性（無次元数および密度・粘性比）。"""

    # Reynolds数: Re = ρ_l U L / μ_l
    Re: float = 100.0
    # Froude数: Fr = U / sqrt(g L)
    Fr: float = 1.0
    # Weber数: We = ρ_l U² L / σ
    We: float = 10.0
    # 密度比 ρ_g / ρ_l（気体 / 液体）
    rho_ratio: float = 0.001
    # 粘性比 μ_g / μ_l
    mu_ratio: float = 0.01


@dataclass
class NumericsConfig:
    """数値スキームのパラメータ。"""

    # ε = epsilon_factor * min(Δx)  — 界面厚さ（§3.3）
    epsilon_factor: float = 1.5
    # 移流ステップあたりの再初期化疑似時間ステップ数
    reinit_steps: int = 4
    # CFL 数（対流安定性条件）
    cfl_number: float = 0.3
    # 終了時刻
    t_end: float = 1.0
    # 粘性項に Crank-Nicolson（半陰的）スキームを使用（§9）
    cn_viscous: bool = True
    # 境界条件の種類: BCType.WALL または BCType.PERIODIC
    bc_type: BCType = BCType.WALL
    # CLS 移流スキーム: 'dissipative_ccd'（デフォルト, §5）または 'weno5'（参考スキーム）
    advection_scheme: str = "dissipative_ccd"
    # 表面張力モデル: 'gfm'（GFM, §8e — 生産用）または 'csf'（CSF, §2b — レガシー）
    # Default: 'csf' for backward compatibility; 'gfm' is production (§8e)
    surface_tension_model: str = "csf"
    # Field extension across Γ: smooth δp and p^n before CCD gradient.
    # extension_method = 'hermite'  : ClosestPointExtender, O(h^6) [default]
    # extension_method = 'upwind'   : FieldExtender (Aslam 2004), O(h^1) [legacy]
    # extension_method = 'none'     : disabled
    # n_extend: pseudo-time iterations used only when method='upwind'.
    extension_method: str = "hermite"
    n_extend: int = 5

    def __post_init__(self) -> None:
        # 文字列からの自動変換（YAML 後方互換）
        if isinstance(self.bc_type, str):
            object.__setattr__(self, 'bc_type', BCType(self.bc_type))
        assert isinstance(self.bc_type, BCType), (
            f"bc_type は BCType でなければならない: '{self.bc_type}'"
        )
        assert self.advection_scheme in ("dissipative_ccd", "weno5"), (
            f"advection_scheme は 'dissipative_ccd' または 'weno5' でなければならない: "
            f"'{self.advection_scheme}'"
        )
        assert self.surface_tension_model in ("gfm", "csf"), (
            f"surface_tension_model は 'gfm' または 'csf' でなければならない: "
            f"'{self.surface_tension_model}'"
        )
        assert self.extension_method in ("hermite", "upwind", "none"), (
            f"extension_method は 'hermite', 'upwind', または 'none' でなければならない: "
            f"'{self.extension_method}'"
        )
        if self.advection_scheme == "dissipative_ccd" and self.epsilon_factor < 1.2:
            warnings.warn(
                f"epsilon_factor={self.epsilon_factor} < 1.2 with advection_scheme="
                "'dissipative_ccd' risks instability for nonlinear flows "
                "(We > 100, density ratio > 100). "
                "Consider epsilon_factor >= 1.5 or advection_scheme='weno5'. "
                "(§5 warn:adv_risks)",
                UserWarning,
                stacklevel=2,
            )


@dataclass
class SolverConfig:
    """PPEソルバーのパラメータ。"""

    # ソルバー種別: "pseudotime" / "ccd_lu" / "sweep" / "iim" / "iterative"
    ppe_solver_type: str = "pseudotime"
    # LGMRES パラメータ（ppe_solver_type="pseudotime" 時に使用）
    pseudo_tol: float = 1e-8
    pseudo_maxiter: int = 500

    # 仮想時間スウィープソルバーの密度係数: Δτᵢⱼ = C_τ·ρᵢⱼ·h²/2 (§8d eq:dtau_lts)
    pseudo_c_tau: float = 2.0

    # ppe_solver_type="iterative" 用: 離散化 × 反復法の組合せ
    ppe_discretization: str = "ccd"        # "ccd" (O(h⁶)) or "3pt" (O(h²))
    ppe_iteration_method: str = "adi"      # "explicit", "gauss_seidel", "adi"

    # ppe_solver_type="iim" 用: IIM correction mode + solve backend
    iim_mode: str = "hermite"    # "nearest" (C_0 only) or "hermite" (C_0,C_1,C_2)
    iim_backend: str = "decomp"  # "decomp" (jump decomposition) / "lu" / "dc"

    def __post_init__(self) -> None:
        _valid_types = ("pseudotime", "ccd_lu", "sweep", "iim", "iterative")
        assert self.ppe_solver_type in _valid_types, (
            f"ppe_solver_type must be one of {_valid_types}: "
            f"'{self.ppe_solver_type}'"
        )
        if self.ppe_solver_type == "iterative":
            assert self.ppe_discretization in ("ccd", "3pt"), (
                f"ppe_discretization must be 'ccd' or '3pt': "
                f"'{self.ppe_discretization}'"
            )
            assert self.ppe_iteration_method in ("explicit", "gauss_seidel", "adi"), (
                f"ppe_iteration_method must be 'explicit', 'gauss_seidel', or 'adi': "
                f"'{self.ppe_iteration_method}'"
            )
        if self.ppe_solver_type == "iim":
            assert self.iim_mode in ("nearest", "hermite"), (
                f"iim_mode must be 'nearest' or 'hermite': '{self.iim_mode}'"
            )
            assert self.iim_backend in ("decomp", "lu", "dc"), (
                f"iim_backend must be 'decomp', 'lu', or 'dc': '{self.iim_backend}'"
            )


# ── メイン設定クラス ─────────────────────────────────────────────────────────

@dataclass
class SimulationConfig:
    """全シミュレーションパラメータを保持する不変 dataclass。

    サブ設定クラスの合成として設計されている::

        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0)),
            fluid=FluidConfig(Re=100., Fr=1., We=10.),
            numerics=NumericsConfig(t_end=2.0, cfl_number=0.3),
            solver=SolverConfig(ppe_solver_type="pseudotime"),
        )
    """

    grid: GridConfig = field(default_factory=GridConfig)
    fluid: FluidConfig = field(default_factory=FluidConfig)
    numerics: NumericsConfig = field(default_factory=NumericsConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    use_gpu: bool = False
