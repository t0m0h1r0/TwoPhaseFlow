"""
PPE 直接法ソルバー（FVM + スパース LU / spsolve）。

変密度 PPE を FVM スパース行列で組み立て、直接法 (SuperLU) で解く:

    A p = rhs,  A = PPEBuilder.build(rho)

収束判定が不要なため高密度比・高条件数のケースで確実に動作する。
メモリは O(n^1.5)（LU fill-in）。

用途:
    - 反復法が収束しない高密度比ケースのデバッグ・テスト
    - 全体の物理動作確認（反復法の収束チューニング前の足場）

反復法への移行:
    ppe_solver_type を "bicgstab" または "pseudotime" に切り替えること。
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid

from ..interfaces.ppe_solver import IPPESolver
from .ppe_builder import PPEBuilder


class PPESolverLU(IPPESolver):
    """FVM PPE を直接 LU 法（spsolve / SuperLU）で解くソルバー。

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig（本ソルバーでは未参照）
    grid    : Grid
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
    ) -> None:
        self.backend = backend
        self._builder = PPEBuilder(backend, grid, bc_type=config.numerics.bc_type)

    # ── IPPESolver 実装 ──────────────────────────────────────────────────

    def solve(self, rhs, rho, dt: float, p_init=None):
        """FVM スパース行列を組み立て、spsolve（直接 LU）で解く。

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
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla
        import numpy as np_host

        triplet, A_shape = self._builder.build(rho)
        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        rhs_host = self.backend.to_host(rhs).ravel().astype(float)
        rhs_host[self._builder._pin_dof] = 0.0  # Dirichlet 固定点（中央ノード）
        if self._builder._periodic_image_dofs is not None:
            rhs_host[self._builder._periodic_image_dofs] = 0.0

        # 対角スケーリング: 密度比が大きい場合の条件数を低減する。
        # 各行を対角絶対値で割る（Jacobi スケーリング）。
        # pin 行（row 0, diag=1）は変化しない。
        diag = np_host.abs(A.diagonal())
        diag = np_host.maximum(diag, 1e-30)   # ゼロ除算を防ぐ
        D_inv = sp.diags(1.0 / diag)
        A_scaled = D_inv @ A
        rhs_scaled = D_inv.diagonal() * rhs_host

        # permc_spec='NATURAL': 列置換なし → pin ノード 0 がピボット位置を保持する
        p_flat = spla.spsolve(A_scaled, rhs_scaled, permc_spec='NATURAL')

        field_shape = self._builder.shape_field
        return self.backend.to_device(p_flat.reshape(field_shape))
