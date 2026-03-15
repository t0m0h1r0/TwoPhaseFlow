"""
MINRES PPE ソルバー（ウォームスタート付き疑似時間 Krylov 法）。

∇·(1/ρ ∇p) = q_h, q_h = (1/Δt) ∇·u*_RC

を PPESolver と同じ FVM スパース行列で解くが、以下の点が異なる:

  * 対称 Dirichlet ピン（行 0 と列 0 を同時にゼロ化）により
    行列の対称性を保ち、BiCGSTAB の代わりに MINRES を使用。
  * p^n からウォームスタートし、解がゆっくり変化する場合の
    反復回数を大幅に削減。

リファクタリング時の変更:
    - IPPESolver を実装し、統一シグネチャ solve(rhs, rho, dt, p_init=None) を採用。
    - 旧シグネチャ solve(p_init, q_h, rho, ccd) を廃止した。
    - これにより TwoPhaseSimulation の isinstance チェックが不要になった（LSP修正）。
"""

from __future__ import annotations
import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid

from ..interfaces.ppe_solver import IPPESolver


class PPESolverPseudoTime(IPPESolver):
    """MINRES によるウォームスタート付き変密度 PPE ソルバー。

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig（pseudo_tol, pseudo_maxiter を参照）
    grid    : Grid
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
    ) -> None:
        self.xp = backend.xp
        self.backend = backend
        self.ndim = grid.ndim
        self.grid = grid
        self.tol = config.pseudo_tol
        self.maxiter = config.pseudo_maxiter

        # 静的な面インデックス配列を事前計算
        self._face_indices: dict = {}
        self._build_index_arrays()

    # ── IPPESolver 実装 ──────────────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """IPPESolver インターフェースの実装。

        MINRES + ウォームスタートで PPE を解く。

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — 右辺 (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — 密度フィールド
        dt     : float — タイムステップ幅（本ソルバーでは未使用）
        p_init : optional array, shape ``grid.shape`` — ウォームスタート p^n

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla

        rho_h = np.asarray(self.backend.to_host(rho), dtype=float)
        q_h_host = np.asarray(self.backend.to_host(rhs), dtype=float).ravel()

        # ウォームスタート初期値
        if p_init is not None:
            p0_host = np.asarray(self.backend.to_host(p_init), dtype=float).ravel()
        else:
            p0_host = np.zeros(int(np.prod(self.grid.shape)))

        # 対称ピン付き FVM 行列を組み立て
        (data, rows, cols), A_shape = self._build_sym(rho_h)
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        # ピン点の右辺を 0 に設定（p[0] = 0）
        q_h_host[0] = 0.0

        p_flat, info = spla.minres(
            A,
            q_h_host,
            x0=p0_host,
            rtol=self.tol,
            maxiter=self.maxiter,
        )

        if info != 0:
            warnings.warn(
                f"PPE MINRES が収束しませんでした (info={info})。"
                " pseudo_maxiter を増やすか pseudo_tol を緩めてください。",
                RuntimeWarning,
                stacklevel=2,
            )

        p_arr = p_flat.reshape(self.grid.shape)
        return self.backend.to_device(p_arr)

    # ── 行列組立 ─────────────────────────────────────────────────────────

    def _build_sym(self, rho: np.ndarray):
        """対称ピン付き FVM PPE 行列を組み立てる。

        対称ピン: A[0, :] = A[:, 0] = e_0（行と列の両方を単位ベクトルに）。
        これにより行列の対称性が保たれ、MINRES が使用可能になる。
        """
        n = int(np.prod(self.grid.shape))
        data_list, row_list, col_list = [], [], []

        for ax in range(self.ndim):
            h = float(self.grid.L[ax] / self.grid.N[ax])
            h2 = h * h
            idx_L, idx_R = self._face_indices[ax]

            rho_L = rho.ravel()[idx_L]
            rho_R = rho.ravel()[idx_R]
            a_f = 2.0 / (rho_L + rho_R)
            coeff = a_f / h2

            # 非対角: L↔R（対称性あり）
            for (src, dst) in [(idx_L, idx_R), (idx_R, idx_L)]:
                data_list.append(coeff)
                row_list.append(src)
                col_list.append(dst)

            # 対角: 両端で coeff を引く
            for idx in [idx_L, idx_R]:
                data_list.append(-coeff)
                row_list.append(idx)
                col_list.append(idx)

        data = np.concatenate(data_list)
        rows = np.concatenate(row_list)
        cols = np.concatenate(col_list)

        # 対称ピン: 行 0 と列 0 をすべて除去してから A[0,0] = 1 を追加
        mask = (rows != 0) & (cols != 0)
        data = data[mask]
        rows = rows[mask]
        cols = cols[mask]

        data = np.append(data, 1.0)
        rows = np.append(rows, 0)
        cols = np.append(cols, 0)

        return (data, rows, cols), (n, n)

    # ── インデックス配列の事前計算 ────────────────────────────────────────

    def _build_index_arrays(self) -> None:
        """内部面の平坦ノードインデックスを事前計算する（PPEBuilder と同じロジック）。"""
        shape = self.grid.shape

        for ax in range(self.ndim):
            ranges = [np.arange(s) for s in shape]
            N_ax = self.grid.N[ax]

            ranges_L = [r.copy() for r in ranges]
            ranges_L[ax] = np.arange(0, N_ax)

            ranges_R = [r.copy() for r in ranges]
            ranges_R[ax] = np.arange(1, N_ax + 1)

            grid_L = np.meshgrid(*ranges_L, indexing='ij')
            grid_R = np.meshgrid(*ranges_R, indexing='ij')

            idx_L = np.ravel_multi_index([g.ravel() for g in grid_L], shape)
            idx_R = np.ravel_multi_index([g.ravel() for g in grid_R], shape)
            self._face_indices[ax] = (idx_L, idx_R)
