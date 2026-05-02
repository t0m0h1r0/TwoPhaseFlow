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
    # 軸ごとの界面適合強度 α_a; None なら alpha_grid を active 軸へ適用
    fitting_alpha_grid: Optional[Tuple[float, ...]] = None
    # セル幅の下限（CCD条件数を防ぐためのフロア値）
    dx_min_floor: float = 1e-6
    # 軸ごとのセル幅下限; None なら dx_min_floor を全軸へ適用
    fitting_dx_min_floor: Optional[Tuple[float, ...]] = None
    # ガウス型グリッド密度関数の幅: ε_g = eps_g_factor × ε（§6 eq:grid_delta）; 推奨 2–4
    eps_g_factor: float = 2.0
    # 軸ごとの ε_g factor; None なら eps_g_factor を全軸へ適用
    fitting_eps_g_factor: Optional[Tuple[float, ...]] = None
    # ξ空間セル数で格子密度幅を指定: ε_g = eps_g_cells × (L/N).
    # 設定時は eps_g_factor を上書き. CCD解像に ≥ 4 が必要 (WIKI-T-039).
    eps_g_cells: Optional[float] = None
    # 軸ごとの eps_g_cells; None 要素は fitting_eps_g_factor 経路を使う
    fitting_eps_g_cells: Optional[Tuple[Optional[float], ...]] = None
    # 非周期物理壁近傍の独立 monitor を適用する軸マスク
    wall_refinement_axes: Optional[Tuple[bool, ...]] = None
    # 軸ごとの壁 monitor 密度倍率 α_W,a; 1.0 = legacy/no wall term
    wall_alpha_grid: Optional[Tuple[float, ...]] = None
    # 壁 monitor 幅: ε_W = wall_eps_g_factor × ε
    wall_eps_g_factor: float = 2.0
    # 軸ごとの壁 monitor 幅 factor
    wall_eps_g_factor_axes: Optional[Tuple[float, ...]] = None
    # 壁 monitor 幅: ε_W = wall_eps_g_cells × (L/N)
    wall_eps_g_cells: Optional[Tuple[Optional[float], ...]] = None
    # 軸ごとの対象壁面; 各要素は ("lower",), ("upper",), ("lower","upper") など
    wall_sides: Optional[Tuple[Tuple[str, ...], ...]] = None

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
        if self.fitting_alpha_grid is None:
            self.fitting_alpha_grid = tuple(
                float(self.alpha_grid) if enabled else 1.0
                for enabled in self.fitting_axes
            )
        self.fitting_alpha_grid = self._float_tuple(
            self.fitting_alpha_grid,
            "fitting_alpha_grid",
        )
        if self.fitting_dx_min_floor is None:
            self.fitting_dx_min_floor = tuple(
                float(self.dx_min_floor) for _axis in range(self.ndim)
            )
        self.fitting_dx_min_floor = self._float_tuple(
            self.fitting_dx_min_floor,
            "fitting_dx_min_floor",
        )
        if self.fitting_eps_g_factor is None:
            self.fitting_eps_g_factor = tuple(
                float(self.eps_g_factor) for _axis in range(self.ndim)
            )
        self.fitting_eps_g_factor = self._float_tuple(
            self.fitting_eps_g_factor,
            "fitting_eps_g_factor",
        )
        if self.fitting_eps_g_cells is None:
            self.fitting_eps_g_cells = tuple(
                self.eps_g_cells for _axis in range(self.ndim)
            )
        assert len(self.fitting_eps_g_cells) == self.ndim, (
            f"len(fitting_eps_g_cells)={len(self.fitting_eps_g_cells)} は "
            f"ndim={self.ndim} と一致しなければならない"
        )
        self.fitting_eps_g_cells = tuple(
            None if cells is None else float(cells)
            for cells in self.fitting_eps_g_cells
        )
        if self.wall_refinement_axes is None:
            self.wall_refinement_axes = tuple(False for _axis in range(self.ndim))
        assert len(self.wall_refinement_axes) == self.ndim, (
            f"len(wall_refinement_axes)={len(self.wall_refinement_axes)} は "
            f"ndim={self.ndim} と一致しなければならない"
        )
        self.wall_refinement_axes = tuple(bool(enabled) for enabled in self.wall_refinement_axes)
        if self.wall_alpha_grid is None:
            self.wall_alpha_grid = tuple(
                1.0 for _axis in range(self.ndim)
            )
        self.wall_alpha_grid = self._float_tuple(
            self.wall_alpha_grid,
            "wall_alpha_grid",
        )
        if self.wall_eps_g_factor_axes is None:
            self.wall_eps_g_factor_axes = tuple(
                float(self.wall_eps_g_factor) for _axis in range(self.ndim)
            )
        self.wall_eps_g_factor_axes = self._float_tuple(
            self.wall_eps_g_factor_axes,
            "wall_eps_g_factor_axes",
        )
        if self.wall_eps_g_cells is None:
            self.wall_eps_g_cells = tuple(None for _axis in range(self.ndim))
        assert len(self.wall_eps_g_cells) == self.ndim, (
            f"len(wall_eps_g_cells)={len(self.wall_eps_g_cells)} は "
            f"ndim={self.ndim} と一致しなければならない"
        )
        self.wall_eps_g_cells = tuple(
            None if cells is None else float(cells)
            for cells in self.wall_eps_g_cells
        )
        if self.wall_sides is None:
            self.wall_sides = tuple(("lower", "upper") for _axis in range(self.ndim))
        assert len(self.wall_sides) == self.ndim, (
            f"len(wall_sides)={len(self.wall_sides)} は ndim={self.ndim} と一致しなければならない"
        )
        self.wall_sides = tuple(
            tuple(str(side).strip().lower() for side in sides)
            for sides in self.wall_sides
        )
        self.alpha_grid = max((*self.fitting_alpha_grid, *(
            alpha if enabled else 1.0
            for enabled, alpha in zip(self.wall_refinement_axes, self.wall_alpha_grid)
        )))
        if self.alpha_grid > 1.0:
            assert any(self.fitting_axes) or any(self.wall_refinement_axes), (
                "alpha_grid > 1.0 では少なくとも 1 軸の fitting_axes または "
                "wall_refinement_axes が必要"
            )
        for eps_g_cells in self.fitting_eps_g_cells:
            assert eps_g_cells is None or eps_g_cells >= 4.0, (
                f"eps_g_cells={eps_g_cells} は CCD 解像に 4 以上が必要"
            )
        for eps_g_cells in self.wall_eps_g_cells:
            assert eps_g_cells is None or eps_g_cells >= 4.0, (
                f"wall_eps_g_cells={eps_g_cells} は CCD 解像に 4 以上が必要"
            )
        for sides in self.wall_sides:
            assert all(side in {"lower", "upper"} for side in sides), (
                f"wall_sides={sides} は lower/upper のみ指定可能"
            )

    def _float_tuple(self, values: Tuple[float, ...], name: str) -> Tuple[float, ...]:
        assert len(values) == self.ndim, (
            f"len({name})={len(values)} は ndim={self.ndim} と一致しなければならない"
        )
        return tuple(float(value) for value in values)


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
    #   'fccd_flux' (デフォルト, §6) | 'dissipative_ccd' | 'weno5' | 'fccd'
    # FCCD は CHK-158 / SP-D — 4次精度 face-centered compact scheme.
    advection_scheme: str = "fccd_flux"
    # 運動量対流スキーム: 'uccd6' (デフォルト, §6) | 'ccd' | 'fccd'
    # FCCD 変種は face-centered compact (SP-D §6/§7); UCCD6 は 6 次 upwind CCD +
    # 選択的超粘性 (WIKI-T-062, WIKI-X-023). いずれも ConvectionTerm と完全互換
    # の AB2 バッファ形状を保つ.
    convection_scheme: str = "uccd6"
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

    # Solver type: "fd_direct" / "fd_iterative" / "fvm_iterative" (default) / "fvm_direct" / "iim" / "iterative";
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
            "fd": "fd_direct",
            "fd_matrixfree": "fd_iterative",
            "fd_cg": "fd_iterative",
            "fvm_matrixfree": "fvm_iterative",
            "fvm_spsolve": "fvm_direct",
        }
        self.ppe_solver_type = _aliases.get(self.ppe_solver_type, self.ppe_solver_type)
        _valid_types = (
            "fd_direct", "fd_iterative", "fvm_iterative", "fvm_direct",
            "iim", "iterative", "ccd_lu",
        )
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
