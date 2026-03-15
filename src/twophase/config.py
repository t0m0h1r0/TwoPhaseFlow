"""
シミュレーション設定 dataclass 群。

§2.4 の無次元化に従う:

    Re = ρ_l U L / μ_l         (Reynolds数)
    Fr = U / sqrt(g L)          (Froude数)
    We = ρ_l U² L / σ           (Weber数)

設計方針（2026-03-15 SRP改善）:
    - SimulationConfig を 4 つのサブ設定に分割。
    - 後方互換性のため SimulationConfig は全フィールドを直接保持し続ける。
    - サブ設定は独立 dataclass として利用可能（個別テストや部分注入に使用）。
    - SimulationConfig.from_sub_configs() で組み立て可能。

サブ設定クラス:
    GridConfig      — グリッドジオメトリ・解像度
    FluidConfig     — 流体物性（Re, Fr, We, 密度比, 粘性比）
    NumericsConfig  — 数値スキーム（CFL, ε係数, 再初期化, CN粘性）
    SolverConfig    — PPEソルバー選択とパラメータ
"""

from __future__ import annotations
from dataclasses import dataclass, field, fields
from typing import Tuple


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
    # 界面適合グリッドの伸縮係数（§5）; 1.0 = 一様格子
    alpha_grid: float = 1.0
    # セル幅の下限（CCD条件数を防ぐためのフロア値）
    dx_min_floor: float = 1e-6

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
    # 境界条件の種類: 'wall' または 'periodic'
    bc_type: str = "wall"

    def __post_init__(self) -> None:
        assert self.bc_type in ("wall", "periodic"), (
            f"bc_type は 'wall' または 'periodic' でなければならない: '{self.bc_type}'"
        )


@dataclass
class SolverConfig:
    """PPEソルバーのパラメータ。"""

    # ソルバー種別: "bicgstab"（FVM, O(h²)）または "pseudotime"（CCD, O(h⁶)）
    ppe_solver_type: str = "bicgstab"
    # BiCGSTAB パラメータ（ppe_solver_type="bicgstab" 時に使用）
    bicgstab_tol: float = 1e-10
    bicgstab_maxiter: int = 1000
    # 疑似時間パラメータ（ppe_solver_type="pseudotime" 時に使用）
    pseudo_tol: float = 1e-8
    pseudo_maxiter: int = 500

    def __post_init__(self) -> None:
        assert self.ppe_solver_type in ("bicgstab", "pseudotime"), (
            f"ppe_solver_type は 'bicgstab' または 'pseudotime' でなければならない: "
            f"'{self.ppe_solver_type}'"
        )


# ── メイン設定クラス（後方互換集約）────────────────────────────────────────

@dataclass
class SimulationConfig:
    """全シミュレーションパラメータを保持する不変 dataclass。

    後方互換性のため全フィールドを直接保持する。
    サブ設定クラス（GridConfig, FluidConfig, NumericsConfig, SolverConfig）を
    組み合わせた構築には ``from_sub_configs()`` クラスメソッドを使用する。
    """

    # ── 空間次元 ────────────────────────────────────────────────────────
    ndim: int = 2

    # ── グリッド設定（GridConfig に対応） ─────────────────────────────
    N: Tuple[int, ...] = (64, 64)
    L: Tuple[float, ...] = (1.0, 1.0)
    alpha_grid: float = 1.0
    dx_min_floor: float = 1e-6

    # ── 流体物性（FluidConfig に対応） ────────────────────────────────
    Re: float = 100.0
    Fr: float = 1.0
    We: float = 10.0
    rho_ratio: float = 0.001   # ρ_g / ρ_l
    mu_ratio: float = 0.01     # μ_g / μ_l

    # ── 数値スキーム（NumericsConfig に対応） ─────────────────────────
    epsilon_factor: float = 1.5
    reinit_steps: int = 4
    cfl_number: float = 0.3
    t_end: float = 1.0
    cn_viscous: bool = True
    bc_type: str = "wall"

    # ── PPEソルバー（SolverConfig に対応） ────────────────────────────
    ppe_solver_type: str = "bicgstab"
    bicgstab_tol: float = 1e-10
    bicgstab_maxiter: int = 1000
    pseudo_tol: float = 1e-8
    pseudo_maxiter: int = 500

    # ── ハードウェア設定 ───────────────────────────────────────────────
    use_gpu: bool = False

    def __post_init__(self) -> None:
        assert self.ndim in (2, 3), f"ndim は 2 か 3 でなければならない: {self.ndim}"
        assert len(self.N) == self.ndim, (
            f"len(N)={len(self.N)} は ndim={self.ndim} と一致しなければならない"
        )
        assert len(self.L) == self.ndim, (
            f"len(L)={len(self.L)} は ndim={self.ndim} と一致しなければならない"
        )
        assert self.bc_type in ("wall", "periodic"), (
            f"bc_type は 'wall' または 'periodic' でなければならない: '{self.bc_type}'"
        )
        assert self.ppe_solver_type in ("bicgstab", "pseudotime"), (
            f"ppe_solver_type は 'bicgstab' または 'pseudotime' でなければならない: "
            f"'{self.ppe_solver_type}'"
        )

    # ── サブ設定への変換メソッド ──────────────────────────────────────

    def to_grid_config(self) -> GridConfig:
        """GridConfig サブ設定を返す。"""
        return GridConfig(
            ndim=self.ndim,
            N=self.N,
            L=self.L,
            alpha_grid=self.alpha_grid,
            dx_min_floor=self.dx_min_floor,
        )

    def to_fluid_config(self) -> FluidConfig:
        """FluidConfig サブ設定を返す。"""
        return FluidConfig(
            Re=self.Re,
            Fr=self.Fr,
            We=self.We,
            rho_ratio=self.rho_ratio,
            mu_ratio=self.mu_ratio,
        )

    def to_numerics_config(self) -> NumericsConfig:
        """NumericsConfig サブ設定を返す。"""
        return NumericsConfig(
            epsilon_factor=self.epsilon_factor,
            reinit_steps=self.reinit_steps,
            cfl_number=self.cfl_number,
            t_end=self.t_end,
            cn_viscous=self.cn_viscous,
            bc_type=self.bc_type,
        )

    def to_solver_config(self) -> SolverConfig:
        """SolverConfig サブ設定を返す。"""
        return SolverConfig(
            ppe_solver_type=self.ppe_solver_type,
            bicgstab_tol=self.bicgstab_tol,
            bicgstab_maxiter=self.bicgstab_maxiter,
            pseudo_tol=self.pseudo_tol,
            pseudo_maxiter=self.pseudo_maxiter,
        )

    @classmethod
    def from_sub_configs(
        cls,
        grid: GridConfig,
        fluid: FluidConfig,
        numerics: NumericsConfig,
        solver: SolverConfig,
        use_gpu: bool = False,
    ) -> "SimulationConfig":
        """サブ設定クラス群から SimulationConfig を組み立てる。

        Parameters
        ----------
        grid     : グリッド設定
        fluid    : 流体物性設定
        numerics : 数値スキーム設定
        solver   : PPEソルバー設定
        use_gpu  : GPU使用フラグ
        """
        return cls(
            # GridConfig から
            ndim=grid.ndim,
            N=grid.N,
            L=grid.L,
            alpha_grid=grid.alpha_grid,
            dx_min_floor=grid.dx_min_floor,
            # FluidConfig から
            Re=fluid.Re,
            Fr=fluid.Fr,
            We=fluid.We,
            rho_ratio=fluid.rho_ratio,
            mu_ratio=fluid.mu_ratio,
            # NumericsConfig から
            epsilon_factor=numerics.epsilon_factor,
            reinit_steps=numerics.reinit_steps,
            cfl_number=numerics.cfl_number,
            t_end=numerics.t_end,
            cn_viscous=numerics.cn_viscous,
            bc_type=numerics.bc_type,
            # SolverConfig から
            ppe_solver_type=solver.ppe_solver_type,
            bicgstab_tol=solver.bicgstab_tol,
            bicgstab_maxiter=solver.bicgstab_maxiter,
            pseudo_tol=solver.pseudo_tol,
            pseudo_maxiter=solver.pseudo_maxiter,
            # ハードウェア
            use_gpu=use_gpu,
        )
