"""
PPE ソルバーのファクトリ関数。

開放閉鎖の原則 (OCP) と依存性逆転の原則 (DIP) を実現するために、
SimulationConfig の設定に基づいて適切な IPPESolver 実装を生成する。

TwoPhaseSimulation はこのファクトリを通じて IPPESolver を取得することで、
具体的なソルバークラスへの依存を排除できる。

新しいソルバーを追加する場合は:
    1. IPPESolver を実装した新クラスを作成
    2. このファクトリに条件分岐を追加
    3. SimulationConfig に新しい solver_type を追加
    → TwoPhaseSimulation 自体の変更は不要（OCP 準拠）
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..interfaces.ppe_solver import IPPESolver


def create_ppe_solver(
    config: "SimulationConfig",
    backend: "Backend",
    grid: "Grid",
    ccd=None,
) -> "IPPESolver":
    """SimulationConfig の設定に基づいて PPE ソルバーを生成する。

    Parameters
    ----------
    config  : SimulationConfig — ppe_solver_type を参照
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver（オプション）— "pseudotime" ソルバーに注入される

    Returns
    -------
    solver : IPPESolver — 統一インターフェースを持つソルバーインスタンス

    Raises
    ------
    ValueError : 未知の ppe_solver_type が指定された場合
    """
    from .ppe_solver import PPESolver
    from .ppe_solver_pseudotime import PPESolverPseudoTime
    from .ppe_solver_lu import PPESolverLU
    from .ppe_solver_ccd_lu import PPESolverCCDLU

    solver_type = config.solver.ppe_solver_type

    if solver_type == "pseudotime":
        return PPESolverPseudoTime(backend, config, grid, ccd=ccd)
    elif solver_type == "ccd_lu":
        # CCD Kronecker 積演算子 + 常時 spsolve（SuperLU）— balanced-force 保証
        return PPESolverCCDLU(backend, config, grid, ccd=ccd)
    elif solver_type == "bicgstab":
        return PPESolver(backend, config, grid)
    elif solver_type == "lu":
        # 直接 LU 法（FVM + spsolve）— 反復収束問題を回避するデバッグ用
        return PPESolverLU(backend, config, grid)
    else:
        raise ValueError(
            f"未知の ppe_solver_type: '{solver_type}'。"
            " 'bicgstab', 'pseudotime', 'lu', または 'ccd_lu' を指定してください。"
        )
