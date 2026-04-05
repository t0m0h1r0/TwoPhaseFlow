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

        from .ccd_ppe_utils import (
            precompute_density_gradients, compute_ccd_laplacian,
            compute_lts_dtau, check_convergence,
        )
        from .thomas_sweep import thomas_sweep_1d

        dtau = compute_lts_dtau(rho_np, self.c_tau, self._h_min)

        # 初期値（IPC 増分法: δp⁰ = 0）
        p = (
            np.zeros(shape, dtype=float)
            if p_init is None
            else np.asarray(self.backend.to_host(p_init), dtype=float)
        )

        drho = precompute_density_gradients(rho_np, self.ccd, self.backend)
        pin_dof = self._bc_spec.pin_dof

        converged = False
        for _ in range(self.maxiter):
            Lp = compute_ccd_laplacian(p, rho_np, drho, self.ccd, self.backend)
            R = rhs_np - Lp

            residual, converged = check_convergence(R, pin_dof, self.tol)
            if converged:
                break

            q = thomas_sweep_1d(R, rho_np, drho[0], dtau, axis=0, grid=self.grid)
            q.ravel()[pin_dof] = 0.0

            dp = thomas_sweep_1d(q, rho_np, drho[1], dtau, axis=1, grid=self.grid)
            dp.ravel()[pin_dof] = 0.0

            # Pseudo-time: ∂p/∂τ = Lp − q (steady state → Lp = q).
            # Implicit step: (1/Δτ − L_FD) dp = Lp − q = −R  → dp = −(1/Δτ−L_FD)⁻¹ R
            # Thomas sweep solves (1/Δτ−L_FD) dp = R, so the physical correction is −dp.
            p = p - dp
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

    # _sweep_1d は thomas_sweep.thomas_sweep_1d に統合済み
