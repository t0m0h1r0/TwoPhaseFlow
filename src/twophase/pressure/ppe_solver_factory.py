"""
PPE solver factory (OCP + DIP).

Creates IPPESolver instances based on SimulationConfig.ppe_solver_type.

Active solvers:
    - "ccd_lu"    : CCD Kronecker + direct LU (production, PR-6 compliant)
    - "iim"       : CCD Kronecker + IIM interface correction
    - "iterative" : configurable research toolkit ({ccd,3pt}×{explicit,gs,adi})

Legacy solvers (C2 retained):
    - "pseudotime": CCD + LGMRES (violates PR-6)
    - "sweep"     : CCD residual + FD Thomas ADI (O(h⁴)/iter, impractical N>=32)
    - "dc_omega"  : sweep + under-relaxation (same ADI limitation)

To add a new solver: implement IPPESolver, add branch here, add type to config.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..core.boundary import BoundarySpec
    from ..interfaces.ppe_solver import IPPESolver


def create_ppe_solver(
    config: "SimulationConfig",
    backend: "Backend",
    grid: "Grid",
    ccd=None,
    bc_spec: "BoundarySpec | None" = None,
) -> "IPPESolver":
    """SimulationConfig の設定に基づいて PPE ソルバーを生成する。

    Parameters
    ----------
    config  : SimulationConfig — ppe_solver_type を参照
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver（オプション）— "pseudotime" ソルバーに注入される
    bc_spec : BoundarySpec（オプション）— 境界条件仕様；None なら config+grid から自動生成

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
    from .ppe_solver_dc_omega import PPESolverDCOmega
    from .ppe_solver_iim import PPESolverIIM
    from .ppe_solver_iterative import PPESolverIterative

    # BoundarySpec の自動生成（未指定時）
    if bc_spec is None:
        from ..core.boundary import BoundarySpec
        bc_spec = BoundarySpec(
            bc_type=config.numerics.bc_type,
            shape=tuple(n + 1 for n in config.grid.N),
            N=config.grid.N,
        )

    solver_type = config.solver.ppe_solver_type

    if solver_type == "pseudotime":
        return PPESolverPseudoTime(backend, config, grid, ccd=ccd, bc_spec=bc_spec)
    elif solver_type == "ccd_lu":
        # CCD Kronecker 積演算子 + 常時 spsolve（SuperLU）— balanced-force 保証
        return PPESolverCCDLU(backend, config, grid, ccd=ccd, bc_spec=bc_spec)
    elif solver_type == "sweep":
        # 行列不要・仮想時間スウィープ（§8d）— LTS + 欠陥補正
        return PPESolverSweep(backend, config, grid, ccd=ccd, bc_spec=bc_spec)
    elif solver_type == "dc_omega":
        # Under-relaxed DC sweep: omega < 0.81 for convergence (exp10_18)
        omega = getattr(config.solver, "pseudo_omega", 0.5)
        return PPESolverDCOmega(backend, config, grid, omega=omega, ccd=ccd, bc_spec=bc_spec)
    elif solver_type == "iim":
        # IIM-CCD: CCD Kronecker + IIM 界面補正 (docs/notes/iim_ccd_note.tex)
        return PPESolverIIM(backend, config, grid, ccd=ccd, bc_spec=bc_spec)
    elif solver_type == "iterative":
        # 研究用: 離散化×反復法の組合せ（config で選択）
        return PPESolverIterative(backend, config, grid, ccd=ccd, bc_spec=bc_spec)
    else:
        raise ValueError(
            f"未知の ppe_solver_type: '{solver_type}'。"
            " 'pseudotime', 'ccd_lu', 'sweep', 'iim', または 'iterative' を指定してください。"
        )
