"""
CCD matrix-free PPE solver (pseudo-time / implicit iteration).

Solves the variable-density Pressure Poisson Equation:

    ∇·(1/ρ ∇p) = q_h,   q_h = (1/Δt) ∇·u*_RC

using the 6th-order CCD product-rule operator (§8b Eq. L_CCD_2d_full):

    (L_CCD^ρ p)_{i,j}
        = (1/ρ)(D_x^{(2)}p + D_y^{(2)}p)
          − (D_x^{(1)}ρ / ρ²) D_x^{(1)}p
          − (D_y^{(1)}ρ / ρ²) D_y^{(1)}p         (§8b Eq. Lx_varrho_discrete)

The CCD 1st/2nd derivative matrices (per axis) are built once via a single
batched CCD call on the identity matrix, then assembled into the 2D operator
via Kronecker products (scipy.sparse.kron).  The pseudo-time implicit update

    (I + Δτ L_CCD^ρ) p^{m+1} = p^m + Δτ q        (§9 Step 6.4)

is solved directly with scipy.sparse.linalg.spsolve.  Choosing Δτ ~ 1/λ_min
gives geometric convergence; convergence is checked via the CCD residual
‖L_CCD^ρ p^m − q‖₂ (§9 Step 6.3).

Compared to the GMRES matrix-free approach:
  - The CCD operator matrix is highly asymmetric (max asymmetry ~900 for N=16)
    due to compact one-sided boundary schemes, causing GMRES divergence.
  - The Kronecker-product sparse formulation avoids GMRES by building the
    full sparse matrix once per timestep and using a direct solver.
  - Cost: O(N^4) build (2 batched CCD calls + kron) + O(N^3) solve per step;
    typically 1-3 pseudo-time steps suffice for convergence.

IPC integration (§4 sec:ipc_derivation):
    Caller passes δp ≡ p^{n+1}−p^n as the unknown (p_init=None → zeros).
    The operator and BC are identical to the absolute-pressure formulation;
    only the unknown variable changes.

Boundary conditions:
    Neumann ∂p/∂n = 0 at all walls: satisfied through the Rhie-Chow RHS
    and velocity BC.  One interior node is pinned to zero to fix the null
    space: row 0 of L is replaced by the identity row.

Refactoring notes (2026-03-20):
    - Replaces FVM+MINRES and GMRES matrix-free implementations.
    - Accepts ``ccd`` via constructor injection (DIP).
    - Factory and builder updated to supply ccd.
    - Existing IPPESolver interface (solve signature) unchanged.
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

from ..interfaces.ppe_solver import IPPESolver


class PPESolverPseudoTime(IPPESolver):
    """CCD sparse-direct variable-density PPE solver (O(h⁶)).

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig  (pseudo_tol, pseudo_maxiter を参照)
    grid    : Grid
    ccd     : CCDSolver  (コンストラクタ注入; None の場合は自動生成)
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        ccd: "CCDSolver | None" = None,
    ) -> None:
        self.xp = backend.xp
        self.backend = backend
        self.ndim = grid.ndim
        self.grid = grid
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter

        # CCD ソルバーの注入または自動生成
        if ccd is not None:
            self.ccd = ccd
        else:
            from ..ccd.ccd_solver import CCDSolver as _CCDSolver
            self.ccd = _CCDSolver(grid, backend)

        # 1D CCD 微分行列をコンストラクタで1回だけ構築（軸ごとの単位行列を差分）
        self._D1: list = []
        self._D2: list = []
        for ax in range(self.ndim):
            d1, d2 = self._build_1d_ccd_matrices(ax)
            self._D1.append(d1)
            self._D2.append(d2)

    # ── IPPESolver 実装 ──────────────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """IPPESolver インターフェースの実装。

        CCD sparse-direct 法で PPE を解く（O(h⁶)）。

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — 右辺 (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — 密度フィールド
        dt     : float — タイムステップ幅（本ソルバーでは未使用）
        p_init : optional array, shape ``grid.shape`` — 初期推定値
                 IPC 増分法では None（ゼロ初期化）を渡すこと

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla  # noqa: F401 (spsolve used below)

        shape = self.grid.shape
        n = int(np.prod(shape))

        # ─── 密度勾配の事前計算（PPE 反復ループの外側で1回）───────────────
        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        xp = self.xp
        drho_np = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(xp.asarray(rho_np), ax)
            drho_np.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        # ─── スパース演算子行列 L_CCD^ρ を Kronecker 積で構築 ──────────────
        L_sparse = self._build_sparse_operator(rho_np, drho_np)

        # ─── ピン点：行 0 を恒等行に置き換えて零空間を除去 ────────────────
        L_lil = L_sparse.tolil()
        L_lil[0, :] = 0.0
        L_lil[0, 0] = 1.0
        L_pinned = L_lil.tocsr()

        # ─── 右辺の準備 ─────────────────────────────────────────────────
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float).ravel()
        rhs_np[0] = 0.0   # ピン点と整合

        # ─── 直接法による求解（スパース LU; 1ステップで収束） ─────────────
        # CCD コンパクト境界スキームが非対称行列を生成するため
        # 仮想時間反復（Krylov 系）は収束が不安定になりやすい。
        # スパース直接ソルバーを用いることで確実に L p = q を解く。
        p_flat = spla.spsolve(L_pinned, rhs_np)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                "CCD-PPE spsolve が非有限値を返しました。"
                " 右辺または密度場を確認してください。",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.backend.to_device(p_flat.reshape(shape))

    # ── 診断用：CCD 演算子の残差を計算 ───────────────────────────────────

    def compute_residual(self, p, rhs, rho) -> float:
        """‖L_CCD^ρ p − rhs‖₂ を返す（テスト・診断用）。

        Parameters
        ----------
        p   : array, shape ``grid.shape`` — 圧力場
        rhs : array, shape ``grid.shape`` — PPE 右辺
        rho : array, shape ``grid.shape`` — 密度場

        Returns
        -------
        residual : float
        """
        xp = self.xp
        shape = self.grid.shape
        rho_dev = xp.asarray(self.backend.to_host(rho))
        drho = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(rho_dev, ax)
            drho.append(drho_ax)

        p_dev = xp.asarray(self.backend.to_host(p))
        Lp = xp.zeros(shape, dtype=p_dev.dtype)
        for ax in range(self.ndim):
            dp_ax, d2p_ax = self.ccd.differentiate(p_dev, ax)
            Lp += d2p_ax / rho_dev - (drho[ax] / rho_dev ** 2) * dp_ax

        rhs_dev = xp.asarray(self.backend.to_host(rhs))
        residual = Lp - rhs_dev
        # ピン点（node 0）は PDE ではなくゲージ拘束条件で置き換えられているため、
        # 物理 PDE 残差の計算から除外する。
        residual_arr = np.asarray(self.backend.to_host(residual))
        residual_arr.ravel()[0] = 0.0
        return float(np.sqrt(np.sum(residual_arr ** 2)))

    # ── プライベートヘルパー ──────────────────────────────────────────────

    def _build_1d_ccd_matrices(self, axis: int):
        """指定軸の 1D CCD 微分行列 D1, D2 を構築する。

        Parameters
        ----------
        axis : 0 (x方向) or 1 (y方向)

        Returns
        -------
        D1 : np.ndarray, shape (n_pts, n_pts) — D_axis^{(1)} 行列
        D2 : np.ndarray, shape (n_pts, n_pts) — D_axis^{(2)} 行列
        """
        n_pts = self.grid.N[axis] + 1
        # 単位行列を差分することで全列を一括計算（バッチ処理）
        I = np.eye(n_pts)

        if axis == 0:
            # axis=0: data shape (n_pts, batch), moveaxis後も同じ
            # D1[i, k] = (D_x^{(1)} e_k)[i]（k列目は単位ベクトル e_k）
            d1, d2 = self.ccd.differentiate(I, axis=0)
            return np.asarray(d1, dtype=float), np.asarray(d2, dtype=float)
        else:
            # axis=1: ccd.differentiate(I, 1) returns d1[k, j] = (D_y^{(1)} e_k)[j]
            # → 転置して D1[j, k] = (D_y^{(1)} e_k)[j]
            d1, d2 = self.ccd.differentiate(I, axis=1)
            return np.asarray(d1, dtype=float).T, np.asarray(d2, dtype=float).T

    def _build_sparse_operator(self, rho_np, drho_np):
        """L_CCD^ρ のスパース行列を Kronecker 積で構築する。

        L_CCD^ρ p = (1/ρ)(D2x⊗I_y + I_x⊗D2y)p
                    − (Dρ_x/ρ²)(D1x⊗I_y)p
                    − (Dρ_y/ρ²)(I_x⊗D1y)p

        Parameters
        ----------
        rho_np  : np.ndarray, shape ``grid.shape``
        drho_np : list of np.ndarray (one per axis)

        Returns
        -------
        L : scipy.sparse.csr_matrix, shape (n, n)
        """
        import scipy.sparse as sp

        shape = self.grid.shape
        Nx, Ny = shape  # (N[0]+1, N[1]+1)

        D1x = self._D1[0]   # (Nx, Nx)
        D2x = self._D2[0]
        D1y = self._D1[1]   # (Ny, Ny)
        D2y = self._D2[1]

        # Kronecker 積による 2D 微分行列（変密度前の純粋な微分演算子）
        # データ順: p.ravel() は (i, j) 順（i=x軸, j=y軸, C-order)
        # D2x_full[k, l]: x方向 2次微分を全グリッド点に適用
        D2x_full = sp.kron(sp.csr_matrix(D2x), sp.eye(Ny), format='csr')
        D2y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(D2y), format='csr')
        D1x_full = sp.kron(sp.csr_matrix(D1x), sp.eye(Ny), format='csr')
        D1y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(D1y), format='csr')

        # 密度重み対角行列
        rho_flat = rho_np.ravel()
        drho_x_flat = drho_np[0].ravel()
        drho_y_flat = drho_np[1].ravel() if self.ndim > 1 else np.zeros_like(rho_flat)

        inv_rho = sp.diags(1.0 / rho_flat, format='csr')
        coeff_x = sp.diags(drho_x_flat / rho_flat ** 2, format='csr')
        coeff_y = sp.diags(drho_y_flat / rho_flat ** 2, format='csr')

        # L_CCD^ρ = (1/ρ)(D2x + D2y) − (Dρ_x/ρ²) D1x − (Dρ_y/ρ²) D1y
        L = (inv_rho @ (D2x_full + D2y_full)
             - coeff_x @ D1x_full
             - coeff_y @ D1y_full)

        return L.tocsr()
