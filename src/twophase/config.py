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
from typing import Optional, Tuple

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
    # 界面適合を適用する軸マスク (x, y[, z]); False の軸は一様格子を保持
    fitting_axes: Optional[Tuple[bool, ...]] = None
    # セル幅の下限（CCD条件数を防ぐためのフロア値）
    dx_min_floor: float = 1e-6
    # ガウス型グリッド密度関数の幅: ε_g = eps_g_factor × ε（§6 eq:grid_delta）; 推奨 2–4
    eps_g_factor: float = 2.0
    # ξ空間セル数で格子密度幅を指定: ε_g = eps_g_cells × (L/N).
    # 設定時は eps_g_factor を上書き. CCD解像に ≥ 4 が必要 (WIKI-T-039).
    eps_g_cells: Optional[float] = None

    def __post_init__(self) -> None:
        assert self.ndim in (2, 3), f"ndim は 2 か 3 でなければならない: {self.ndim}"
        assert len(self.N) == self.ndim, (
            f"len(N)={len(self.N)} は ndim={self.ndim} と一致しなければならない"
        )
        assert len(self.L) == self.ndim, (
            f"len(L)={len(self.L)} は ndim={self.ndim} と一致しなければならない"
        )
        if self.fitting_axes is None:
            self.fitting_axes = tuple(True for _axis in range(self.ndim))
        assert len(self.fitting_axes) == self.ndim, (
            f"len(fitting_axes)={len(self.fitting_axes)} は ndim={self.ndim} と一致しなければならない"
        )
        self.fitting_axes = tuple(bool(enabled) for enabled in self.fitting_axes)
        if self.alpha_grid > 1.0:
            assert any(self.fitting_axes), (
                "alpha_grid > 1.0 では少なくとも 1 軸の fitting_axes が必要"
            )
        if self.eps_g_cells is not None:
            assert self.eps_g_cells >= 4.0, (
                f"eps_g_cells={self.eps_g_cells} は CCD 解像に 4 以上が必要"
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
    # 再初期化法: 'split'|'unified'|'dgr'|'hybrid'|'eikonal'|'eikonal_xi'
    #          | 'eikonal_fmm' | 'ridge_eikonal'  (CHK-159, SP-E)
    # Default 'split' preserves existing behaviour bit-exactly.
    reinit_method: str = "split"
    # σ_0 for Ridge-Eikonal (D1, WIKI-T-057) in h_ref units; ignored otherwise.
    ridge_sigma_0: float = 3.0
    # CFL 数（対流安定性条件）
    cfl_number: float = 0.3
    # 終了時刻
    t_end: float = 1.0
    # 粘性項に Crank-Nicolson（半陰的）スキームを使用（§9）
    cn_viscous: bool = True
    # CN viscous advance strategy (Strategy pattern, see
    # src/twophase/ns_terms/cn_advance/ and
    # docs/memo/extended_cn_impl_design.md).
    # 'picard' — default, 1-step Picard on CN (Heun). Current production
    # behaviour, bit-exact with pre-Phase-1 implementation.
    # Richardson / Implicit / Pade22 variants will be added in later phases.
    cn_mode: str = "picard"
    # 境界条件の種類: BCType.WALL または BCType.PERIODIC
    bc_type: BCType = BCType.WALL
    # CLS 移流スキーム:
    #   'dissipative_ccd' (デフォルト, §5) | 'weno5' | 'fccd'
    # FCCD は CHK-158 / SP-D — 4次精度 face-centered compact scheme.
    advection_scheme: str = "dissipative_ccd"
    # 運動量対流スキーム: 'ccd' (デフォルト) | 'fccd' | 'uccd6'
    # FCCD 変種は face-centered compact (SP-D §6/§7); UCCD6 は 6 次 upwind CCD +
    # 選択的超粘性 (WIKI-T-062, WIKI-X-023). いずれも ConvectionTerm と完全互換
    # の AB2 バッファ形状を保つ.
    convection_scheme: str = "ccd"
    # UCCD6 超粘性係数 σ (convection_scheme='uccd6' 時のみ). TVD-RK3 安定条件
    # σ ≲ √3 h / (8500 max|u|). 典型値 1e-3 (CFL ~0.1, N=128).
    uccd6_sigma: float = 1.0e-3
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
        if self.advection_scheme == "fccd":
            object.__setattr__(self, 'advection_scheme', "fccd_flux")
        if self.convection_scheme == "fccd":
            object.__setattr__(self, 'convection_scheme', "fccd_flux")
        assert isinstance(self.bc_type, BCType), (
            f"bc_type は BCType でなければならない: '{self.bc_type}'"
        )
        assert self.advection_scheme in (
            "dissipative_ccd", "weno5", "fccd_nodal", "fccd_flux",
        ), (
            f"advection_scheme は 'dissipative_ccd', 'weno5', 'fccd' "
            f"のいずれか: '{self.advection_scheme}'"
        )
        assert self.convection_scheme in (
            "ccd", "fccd_nodal", "fccd_flux", "uccd6",
        ), (
            f"convection_scheme は 'ccd', 'fccd', 'uccd6' "
            f"のいずれか: '{self.convection_scheme}'"
        )
        if self.convection_scheme == "uccd6":
            assert self.uccd6_sigma > 0.0, (
                f"uccd6_sigma > 0 でなければならない: {self.uccd6_sigma}"
            )
        assert self.surface_tension_model in ("gfm", "csf"), (
            f"surface_tension_model は 'gfm' または 'csf' でなければならない: "
            f"'{self.surface_tension_model}'"
        )
        assert self.extension_method in ("hermite", "upwind", "none"), (
            f"extension_method は 'hermite', 'upwind', または 'none' でなければならない: "
            f"'{self.extension_method}'"
        )
        _valid_reinit = (
            "split", "unified", "dgr", "hybrid",
            "eikonal", "eikonal_xi", "eikonal_fmm", "ridge_eikonal",
        )
        assert self.reinit_method in _valid_reinit, (
            f"reinit_method は {_valid_reinit} のいずれかでなければならない: "
            f"'{self.reinit_method}'"
        )
        assert self.ridge_sigma_0 > 0.0, (
            f"ridge_sigma_0 > 0 でなければならない: {self.ridge_sigma_0}"
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

    # Solver type: "fvm_iterative" (default) / "fvm_direct" / "iim" / "iterative";
    # "ccd_lu" is restricted to explicit component/reference use.
    ppe_solver_type: str = "fvm_iterative"
    allow_kronecker_lu: bool = False
    # Solver tolerances (used by iterative FVM, iim, iterative)
    pseudo_tol: float = 1e-8
    pseudo_maxiter: int = 500
    pseudo_c_tau: float = 2.0

    # ppe_solver_type="iterative" 用: 離散化 × 反復法の組合せ
    ppe_discretization: str = "ccd"        # "ccd" (O(h⁶)) or "3pt" (O(h²))
    ppe_iteration_method: str = "adi"      # "explicit", "gauss_seidel", "adi"

    # ppe_solver_type="iim" 用: IIM correction mode + solve backend
    iim_mode: str = "hermite"    # "nearest" (C_0 only) or "hermite" (C_0,C_1,C_2)
    iim_backend: str = "decomp"  # "decomp" (jump decomposition) / "lu" / "dc"

    def __post_init__(self) -> None:
        _aliases = {
            "fvm_matrixfree": "fvm_iterative",
            "fvm_spsolve": "fvm_direct",
        }
        self.ppe_solver_type = _aliases.get(self.ppe_solver_type, self.ppe_solver_type)
        _valid_types = ("fvm_iterative", "fvm_direct", "iim", "iterative", "ccd_lu")
        assert self.ppe_solver_type in _valid_types, (
            f"ppe_solver_type must be one of {_valid_types}: "
            f"'{self.ppe_solver_type}'"
        )
        if self.ppe_solver_type == "ccd_lu":
            assert self.allow_kronecker_lu, (
                "ppe_solver_type='ccd_lu' is restricted to explicit "
                "Kronecker-LU reference/component use. Set "
                "allow_kronecker_lu=True only when that is intentional."
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
            solver=SolverConfig(ppe_solver_type="fvm_iterative"),
        )
    """

    grid: GridConfig = field(default_factory=GridConfig)
    fluid: FluidConfig = field(default_factory=FluidConfig)
    numerics: NumericsConfig = field(default_factory=NumericsConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    use_gpu: bool = False
