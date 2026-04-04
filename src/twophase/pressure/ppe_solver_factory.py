"""
PPE ソルバーのファクトリ関数。

開放閉鎖の原則 (OCP) と依存性逆転の原則 (DIP) を実現するために、
SimulationConfig の設定に基づいて適切な IPPESolver 実装を生成する。

TwoPhaseSimulation はこのファクトリを通じて IPPESolver を取得することで、
具体的なソルバークラスへの依存を排除できる。

CCD ベースのソルバーのみをサポート（FVM は精度不足のため廃止）:
    - "pseudotime": CCD Kronecker + LGMRES 反復（デフォルト・本番用）
    - "ccd_lu":     CCD Kronecker + 常時直接 LU（デバッグ・検証用）
    - "sweep":      CCD 仮想時間スウィープ（行列不要・大規模用）
    - "iim":        IIM-CCD 界面補正（界面ジャンプ対応）
    - "iterative":  離散化×反復法の組合せ研究用（{ccd,3pt}×{explicit,gs,adi}）

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
    from .ppe_solver_pseudotime import PPESolverPseudoTime
    from .ppe_solver_ccd_lu import PPESolverCCDLU
    from .ppe_solver_sweep import PPESolverSweep
    from .ppe_solver_iim import PPESolverIIM
    from .ppe_solver_iterative import PPESolverIterative

    solver_type = config.solver.ppe_solver_type

    if solver_type == "pseudotime":
        return PPESolverPseudoTime(backend, config, grid, ccd=ccd)
    elif solver_type == "ccd_lu":
        # CCD Kronecker 積演算子 + 常時 spsolve（SuperLU）— balanced-force 保証
        return PPESolverCCDLU(backend, config, grid, ccd=ccd)
    elif solver_type == "sweep":
        # 行列不要・仮想時間スウィープ（§8d）— LTS + 欠陥補正
        return PPESolverSweep(backend, config, grid, ccd=ccd)
    elif solver_type == "iim":
        # IIM-CCD: CCD Kronecker + IIM 界面補正 (docs/notes/iim_ccd_note.tex)
        return PPESolverIIM(backend, config, grid, ccd=ccd)
    elif solver_type == "iterative":
        # 研究用: 離散化×反復法の組合せ（config で選択）
        return PPESolverIterative(backend, config, grid, ccd=ccd)
    else:
        raise ValueError(
            f"未知の ppe_solver_type: '{solver_type}'。"
            " 'pseudotime', 'ccd_lu', 'sweep', 'iim', または 'iterative' を指定してください。"
        )
