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
from dataclasses import dataclass, field
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


# ── メイン設定クラス ─────────────────────────────────────────────────────────

@dataclass
class SimulationConfig:
    """全シミュレーションパラメータを保持する不変 dataclass。

    サブ設定クラスの合成として設計されている::

        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0)),
            fluid=FluidConfig(Re=100., Fr=1., We=10.),
            numerics=NumericsConfig(t_end=2.0, cfl_number=0.3),
            solver=SolverConfig(ppe_solver_type="bicgstab"),
        )
    """

    grid: GridConfig = field(default_factory=GridConfig)
    fluid: FluidConfig = field(default_factory=FluidConfig)
    numerics: NumericsConfig = field(default_factory=NumericsConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    use_gpu: bool = False
