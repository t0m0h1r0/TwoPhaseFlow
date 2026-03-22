"""
PPE CCD ソルバー — 常にスパース LU（spsolve）で解く。

PPESolverPseudoTime と同じ CCD Kronecker 積演算子 L_CCD^ρ を使用するが，
LGMRES を試みずに spsolve（SuperLU）で直接解く。

用途:
    - 直接 LU を強制したいテスト・デバッグ用（ppe_solver_type="ccd_lu"）
    - 密度比 1:1 など反復法が収束する条件でも確実な基準解を得たい場合
    - balanced-force 検証（CCD PPE + CCD 補正子の一貫性確認）

演算子:
    (L_CCD^ρ p)_{i,j}
        = (1/ρ)(D_x^{(2)}p + D_y^{(2)}p)
          − (D_x^{(1)}ρ / ρ²) D_x^{(1)}p
          − (D_y^{(1)}ρ / ρ²) D_y^{(1)}p

PPESolverPseudoTime との違い:
    LGMRES を省略し，常に spsolve を使用する（O(n^1.5) メモリ）。
    演算子構築・ピン設定は完全に同一。
"""

from __future__ import annotations
import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver

from .ppe_solver_pseudotime import PPESolverPseudoTime


class PPESolverCCDLU(PPESolverPseudoTime):
    """CCD Kronecker 積演算子 + 常時 spsolve（SuperLU）による PPE ソルバー。

    PPESolverPseudoTime と同じ L_CCD^ρ 演算子を使用し，
    LGMRES を省略してスパース直接法（SuperLU）で解く。

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig
    grid    : Grid
    ccd     : CCDSolver（コンストラクタ注入; None の場合は自動生成）
    """

    def solve(self, rhs, rho, dt: float, p_init=None):
        """CCD L_CCD^ρ 演算子を Kronecker 積で組み立て，spsolve で解く。

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — 右辺 (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — 密度フィールド
        dt     : float — 未使用（インターフェース互換のため保持）
        p_init : optional — 未使用（直接法はウォームスタート不要）

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        import scipy.sparse.linalg as spla

        shape = self.grid.shape

        # 密度勾配の事前計算
        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        xp = self.xp
        drho_np = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(xp.asarray(rho_np), ax)
            drho_np.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        # スパース演算子行列 L_CCD^ρ を Kronecker 積で構築
        L_sparse = self._build_sparse_operator(rho_np, drho_np)

        # ピン点：中央ノードを恒等行に置き換えて零空間を除去
        pin_idx = tuple(n // 2 for n in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, self.grid.shape))
        L_lil = L_sparse.tolil()
        L_lil[pin_dof, :] = 0.0
        L_lil[pin_dof, pin_dof] = 1.0
        L_pinned = L_lil.tocsr()

        # 右辺の準備
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float).ravel()
        rhs_np[pin_dof] = 0.0

        # 常に直接 LU（spsolve / SuperLU）
        p_flat = spla.spsolve(L_pinned, rhs_np)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                "PPESolverCCDLU: spsolve が非有限値を返しました。"
                " 右辺または密度場を確認してください。",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.backend.to_device(p_flat.reshape(shape))
