"""
PPE 線形ソルバー（BiCGSTAB）。

論文の §7.4 を実装。

    A p = rhs

を BiCGSTAB で解く。:class:`~twophase.pressure.ppe_builder.PPEBuilder` で
組み立てたスパース行列を内部で生成する。

リファクタリング時の変更:
    - IPPESolver を実装し、統一シグネチャ solve(rhs, rho, dt, p_init=None) を採用。
    - PPEBuilder を内部に保持し、呼び出し側が triplet を直接渡す必要をなくした。
    - これにより TwoPhaseSimulation の isinstance チェックが不要になった（LSP修正）。
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid

from ..interfaces.ppe_solver import IPPESolver
from .ppe_builder import PPEBuilder

# ILU fill_factor: periodic BC mixes identity-minus rows with FVM rows,
# requiring higher fill for convergence (§8 preconditioner note).
_FILL_PERIODIC = 10
_FILL_WALL     = 1


class PPESolver(IPPESolver):
    """BiCGSTAB による PPE スパース系ソルバー。

    PPEBuilder を内部に保持し、各ステップで行列を組み立てて BiCGSTAB で解く。

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig（tol, maxiter を参照）
    grid    : Grid（PPEBuilder の構築に使用）
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
    ):
        self.backend = backend
        self.xp = backend.xp
        self.tol = config.solver.bicgstab_tol
        self.maxiter = config.solver.bicgstab_maxiter
        bc_type = config.numerics.bc_type
        self._builder = PPEBuilder(backend, grid, bc_type=bc_type)

    # ── IPPESolver 実装 ──────────────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """IPPESolver インターフェースの実装。

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — 右辺 (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — 密度フィールド
        dt     : float — タイムステップ幅（本ソルバーでは未使用）
        p_init : optional array — ウォームスタート初期値 p^n

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla
        import numpy as np_host

        # 行列を組み立て
        triplet, A_shape = self._builder.build(rho)
        n_dof = self._builder.n_dof
        field_shape = self._builder.shape_field

        data, rows, cols = triplet
        A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)

        rhs_host = self.backend.to_host(rhs).ravel().astype(float)
        # Dirichlet 固定点（中央ノード）の右辺を 0 に設定
        rhs_host[self._builder._pin_dof] = 0.0
        # 周期 BC: 周期像ノードの方程式は p[ghost]=p[src] → RHS = 0
        if self._builder._periodic_image_dofs is not None:
            rhs_host[self._builder._periodic_image_dofs] = 0.0

        # ウォームスタート初期値の設定
        x0 = None
        if p_init is not None:
            x0 = self.backend.to_host(p_init).ravel().astype(float)

        # 前処理: 周期 BC では ILU が収束しない（identity-minus 行と FVM 行の混在が原因）
        # → Jacobi（対角スケーリング）で代替する。壁面 BC では ILU(0) を使用。
        # 前処理: 周期 BC では identity-minus 行と FVM 行が混在するため ILU(0) が
        # 収束しにくい。fill_factor=10 で完全な充填を許してより良い前処理を得る。
        # 壁面 BC では fill_factor=1 で十分。
        fill = _FILL_PERIODIC if self._builder.bc_type == 'periodic' else _FILL_WALL
        try:
            ilu = spla.spilu(A.tocsc(), fill_factor=fill)
            M = spla.LinearOperator(A_shape, ilu.solve)
        except Exception:
            M = None

        p_flat, info = spla.bicgstab(
            A, rhs_host,
            x0=x0,
            M=M,
            rtol=self.tol,
            maxiter=self.maxiter,
        )

        if info != 0:
            import warnings
            warnings.warn(
                f"PPE BiCGSTAB が収束しませんでした (info={info})。"
                " bicgstab_maxiter を増やすか tol を緩めてください。",
                RuntimeWarning,
                stacklevel=2,
            )

        p_arr = np_host.reshape(p_flat, field_shape)
        return self.backend.to_device(p_arr)
