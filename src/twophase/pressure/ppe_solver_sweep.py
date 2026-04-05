"""
仮想時間スウィープ PPE ソルバー（行列不要）。

論文 §8d のスウィープ型（sweep-type）を実装する。

アルゴリズム（各仮想時間反復 m）:
  1. CCD 残差 R = q_h − L_CCD(δp^m)  [O(h⁶)]
  2. ε = ‖R‖₂ < ε_tol なら収束終了
  3. x スウィープ: (1/Δτ − L_FD_x) q  = R  [各列 j に Thomas 法]
  4. y スウィープ: (1/Δτ − L_FD_y) Δp = q  [各行 i に Thomas 法]
  5. δp^{m+1} = δp^m + Δp；ゲージピンを 0 に固定

設計方針（欠陥補正, §8d sec:defect_correction）:
  - LHS: 2次精度有限差分 L_FD → 通常の3重対角 → Thomas 法 O(N)
  - RHS: CCD 演算子 L_CCD → O(h⁶) 精度残差
  - 収束後: L_CCD(δp) = q_h が ε_tol 精度で満たされる（空間精度は CCD による）

LTS（局所時間刻み, §8d eq:dtau_lts）:
  Δτᵢⱼ = C_τ · ρᵢⱼ · h² / 2
  ρ 依存性が打ち消されるため，気体・液体相で均等な収束速度が得られる
  （Δτᵢⱼ · (1/ρᵢⱼ) = C_τ h²/2 = 定数）。

収束基準（§8d eq:residual, result:etol_criterion）:
  ε_tol = config.solver.pseudo_tol（推奨: ε_tol ≤ Δt² × 10⁻²）

ゲージ固定:
  中央ノード (N//2, N//2) を 0 に固定（正方形領域の全対称操作に対して不変）。

現行 LGMRES 実装（PPESolverPseudoTime）との比較:
  本クラス（sweep）: 行列なし, O(N²/iter), LTS 収束加速
  PPESolverPseudoTime: N²×N² クロネッカー行列 + LGMRES, 分割誤差なし
  両者は収束後に同一解を与える（表 tab:ppe_methods, 3行目 vs 4行目）。
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
    from ..core.boundary import BoundarySpec

from ..interfaces.ppe_solver import IPPESolver


class PPESolverSweep(IPPESolver):
    """行列不要・仮想時間スウィープ PPE ソルバー（O(h⁶)，§8d）。

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig  (pseudo_tol, pseudo_maxiter, pseudo_c_tau)
    grid    : Grid
    ccd     : CCDSolver（コンストラクタ注入；None なら自動生成）
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        ccd: "CCDSolver | None" = None,
        bc_spec: "BoundarySpec | None" = None,
    ) -> None:
        self.xp = backend.xp
        self.backend = backend
        self.grid = grid
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter
        self.c_tau = config.solver.pseudo_c_tau

        if ccd is not None:
            self.ccd = ccd
        else:
            from ..ccd.ccd_solver import CCDSolver as _CCD
            self.ccd = _CCD(grid, backend)

        # 境界条件仕様
        if bc_spec is not None:
            self._bc_spec = bc_spec
        else:
            from ..core.boundary import BoundarySpec as _BS
            self._bc_spec = _BS(
                bc_type=config.numerics.bc_type,
                shape=grid.shape,
                N=grid.N,
            )

        # 最小格子幅 h（LTS の h² 基準値）
        self._h_min = min(
            grid.L[ax] / grid.N[ax] for ax in range(grid.ndim)
        )

    # ── IPPESolver ────────────────────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """仮想時間スウィープ法で PPE を解く。

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — 密度場
        dt     : float（未使用；LSP のために保持）
        p_init : optional array — ウォームスタート初期値；None → IPC 増分（ゼロ）

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        xp = self.xp
        shape = self.grid.shape

        rho_np  = np.asarray(self.backend.to_host(rho),  dtype=float)
        rhs_np  = np.asarray(self.backend.to_host(rhs),  dtype=float)

        # LTS: Δτᵢⱼ = C_τ · ρᵢⱼ · h_min² / 2  (§8d eq:dtau_lts)
        dtau = self.c_tau * rho_np * (self._h_min ** 2) / 2.0   # shape=grid.shape

        # 初期値（IPC 増分法: δp⁰ = 0）
        p = (
            np.zeros(shape, dtype=float)
            if p_init is None
            else np.asarray(self.backend.to_host(p_init), dtype=float)
        )

        # 密度勾配（CCD; 反復中は凍結）
        rho_dev = xp.asarray(rho_np)
        drho: list[np.ndarray] = []
        for ax in range(self.grid.ndim):
            drho_ax, _ = self.ccd.differentiate(rho_dev, ax)
            drho.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        # ゲージピン
        pin_dof = self._bc_spec.pin_dof

        converged = False
        for _ in range(self.maxiter):
            # ── CCD 残差 R = q_h − L_CCD(δp)  (O(h⁶)) ─────────────
            p_dev = xp.asarray(p)
            Lp = xp.zeros(shape, dtype=float)
            for ax in range(self.grid.ndim):
                dp_ax, d2p_ax = self.ccd.differentiate(p_dev, ax)
                drho_dev = xp.asarray(drho[ax])
                Lp += d2p_ax / rho_dev - (drho_dev / rho_dev ** 2) * dp_ax

            R = rhs_np - np.asarray(self.backend.to_host(Lp))

            # ピンノードを残差から除外して収束判定
            R_chk = R.ravel().copy()
            R_chk[pin_dof] = 0.0
            residual = float(np.sqrt(np.dot(R_chk, R_chk)))
            if residual < self.tol:
                converged = True
                break

            # ── x スウィープ: (1/Δτ − L_FD_x) q = R ────────────────
            q = self._sweep_1d(R, rho_np, drho[0], dtau, axis=0)
            q.ravel()[pin_dof] = 0.0

            # ── y スウィープ: (1/Δτ − L_FD_y) Δp = q ───────────────
            dp = self._sweep_1d(q, rho_np, drho[1], dtau, axis=1)
            dp.ravel()[pin_dof] = 0.0

            p = p + dp
            p.ravel()[pin_dof] = 0.0

        if not converged:
            warnings.warn(
                f"PPESolverSweep: 仮想時間反復が {self.maxiter} 回で収束しませんでした"
                f"（最終残差 {residual:.3e}，ε_tol={self.tol:.3e}）。"
                " pseudo_maxiter または pseudo_c_tau の調整を検討してください。",
                RuntimeWarning,
                stacklevel=2,
            )

        if not np.isfinite(p).all():
            warnings.warn(
                "PPESolverSweep: 非有限値が検出されました。密度場を確認してください。",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.backend.to_device(p)

    # ── Thomas スウィープ ─────────────────────────────────────────────────

    def _sweep_1d(
        self,
        rhs_2d: np.ndarray,
        rho: np.ndarray,
        drho: np.ndarray,
        dtau: np.ndarray,
        axis: int,
    ) -> np.ndarray:
        """(1/Δτ − L_FD_axis) q = rhs を axis 方向の Thomas 法で解く。

        全断面を同時に処理するベクトル化 Thomas 法。
        LHS 演算子（FD 2次精度）:
            (L_FD_axis q)[i] = (1/ρ[i])(q[i-1]−2q[i]+q[i+1])/h²
                               − (∂ρ/∂x[i]/ρ[i]²)(q[i+1]−q[i-1])/(2h)

        境界ノード (i=0, i=N): 恒等（Neumann BC — 壁面では増分ゼロ）。

        Parameters
        ----------
        rhs_2d : shape ``grid.shape`` — RHS
        rho    : shape ``grid.shape`` — 密度
        drho   : shape ``grid.shape`` — ρ の axis 方向微分（CCD）
        dtau   : shape ``grid.shape`` — LTS 仮想時間刻み Δτᵢⱼ
        axis   : int — Thomas を適用する軸（0=x, 1=y）

        Returns
        -------
        q : shape ``grid.shape``
        """
        N = self.grid.N[axis]
        h = self.grid.L[axis] / N
        h2 = h * h

        # 解く軸を先頭に移動: (N+1, batch)
        rhs_f  = np.moveaxis(rhs_2d, axis, 0)
        rho_f  = np.moveaxis(rho,    axis, 0)
        drho_f = np.moveaxis(drho,   axis, 0)
        dtau_f = np.moveaxis(dtau,   axis, 0)

        n = N + 1  # ノード数

        # 係数: (N+1, batch)
        inv_dtau = 1.0 / dtau_f                          # 1/Δτᵢⱼ
        inv_rho_h2 = 1.0 / (rho_f * h2)                 # 1/(ρ h²)
        drho_h = drho_f / (rho_f ** 2 * 2.0 * h)        # ∂ρ/∂x / (ρ² 2h)

        # 3重対角係数 (N+1, batch)
        a = np.empty_like(rhs_f)   # 下対角 (p[i-1])
        b = np.empty_like(rhs_f)   # 主対角 (p[i])
        c = np.empty_like(rhs_f)   # 上対角 (p[i+1])

        # 内部ノード 1..N-1
        a[1:-1] = -inv_rho_h2[1:-1] + drho_h[1:-1]        # − 1/(ρh²) + ρx/(2ρ²h)
        b[1:-1] =  inv_dtau[1:-1]   + 2.0 * inv_rho_h2[1:-1]  # 1/Δτ + 2/(ρh²)
        c[1:-1] = -inv_rho_h2[1:-1] - drho_h[1:-1]        # − 1/(ρh²) − ρx/(2ρ²h)

        # 境界ノード: 恒等（Δq 壁面 = 0）
        rhs_m = rhs_f.copy()
        from ..core.boundary import apply_thomas_neumann
        apply_thomas_neumann(a, b, c, rhs_m)

        # ── Thomas 前進消去 ────────────────────────────────────────
        c_p = np.zeros_like(rhs_f)    # 修正上対角
        r_p = np.zeros_like(rhs_f)    # 修正 RHS

        c_p[0] = c[0] / b[0]
        r_p[0] = rhs_m[0] / b[0]
        for i in range(1, n):
            denom   = b[i] - a[i] * c_p[i - 1]
            c_p[i]  = c[i] / denom
            r_p[i]  = (rhs_m[i] - a[i] * r_p[i - 1]) / denom

        # ── 後退代入 ───────────────────────────────────────────────
        q = np.empty_like(rhs_f)
        q[-1] = r_p[-1]
        for i in range(n - 2, -1, -1):
            q[i] = r_p[i] - c_p[i] * q[i + 1]

        return np.moveaxis(q, 0, axis)
