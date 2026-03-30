"""
10_EVALUATE.md — 数値コンポーネント収束検証スクリプト（修正版）

各計算コンポーネントを解析解と比較し、収束次数を確認する。

修正履歴:
  - WENO5: 初期条件を [0,1] 内に収まる 0.5+0.4sin(2πx) に変更
            （advance() が ψ∈[0,1] へクランプするため）
  - PPE MMS: 製造解を cos(2πx)cos(2πy) に変更
             （Neumann BC ∂p/∂n=0 を満たすため）
  - 曲率: |κ| と 1/R を比較するよう修正
           （φ=r-R 規約では κ=-1/R が正しい符号）
"""

import sys, os
import numpy as np
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver

be = Backend(use_gpu=False)
xp = be.xp

SEP = "=" * 72


def errors(numeric, exact):
    """L1, L2, L∞ ノルム誤差を返す"""
    diff = np.abs(numeric - exact)
    return diff.mean(), np.sqrt((diff**2).mean()), diff.max()


def conv_order(e1, e2, r=2.0):
    """細かいグリッドへの洗練率 r での収束次数"""
    if e1 == 0.0 or e2 == 0.0:
        return float('inf')
    return math.log(e1 / e2) / math.log(r)


# ──────────────────────────────────────────────────────────────────────────────
# 1. CCD 微分演算子（1階・2階）
# ──────────────────────────────────────────────────────────────────────────────

def test_ccd_convergence():
    """
    解析解: u(x, y) = sin(2π x) cos(2π y)
    理論値:
      du/dx = 2π cos(2π x) cos(2π y)   [CCD 1階]
      d²u/dx² = −(2π)² sin(2π x) cos(2π y)  [CCD 2階]
    期待収束次数: 6次（CCD 内部スキーム）
    """
    print(SEP)
    print("【コンポーネント 1】CCD 微分演算子 — 収束試験")
    print("  解析解: u = sin(2πx)cos(2πy)")
    print(SEP)

    Ns = [16, 32, 64, 128]
    results_d1 = []
    results_d2 = []

    for N in Ns:
        cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
        grid = Grid(cfg.grid, be)
        ccd = CCDSolver(grid, be)

        X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1), indexing='ij')
        u = np.sin(2*np.pi*X) * np.cos(2*np.pi*Y)
        d1_exact = 2*np.pi * np.cos(2*np.pi*X) * np.cos(2*np.pi*Y)
        d2_exact = -(2*np.pi)**2 * np.sin(2*np.pi*X) * np.cos(2*np.pi*Y)

        d1_num, d2_num = ccd.differentiate(u, axis=0)

        sl = np.s_[2:-2, 2:-2]
        _, _, einf_d1 = errors(d1_num[sl], d1_exact[sl])
        _, _, einf_d2 = errors(d2_num[sl], d2_exact[sl])
        results_d1.append(einf_d1)
        results_d2.append(einf_d2)

    print(f"  {'N':>6}  {'L∞ (d1)':>12}  {'次数':>8}  {'L∞ (d2)':>12}  {'次数':>8}")
    print(f"  {'-'*56}")
    for i, N in enumerate(Ns):
        od1 = f"{conv_order(results_d1[i-1], results_d1[i]):.2f}" if i > 0 else "—"
        od2 = f"{conv_order(results_d2[i-1], results_d2[i]):.2f}" if i > 0 else "—"
        print(f"  {N:>6}  {results_d1[i]:>12.3e}  {od1:>8}  {results_d2[i]:>12.3e}  {od2:>8}")

    ord_d1 = conv_order(results_d1[-2], results_d1[-1])
    ord_d2 = conv_order(results_d2[-2], results_d2[-1])
    print(f"\n  判定: 1階 次数={ord_d1:.2f} (>4.5) {'✅ PASS' if ord_d1>4.5 else '❌ FAIL'}")
    print(f"  判定: 2階 次数={ord_d2:.2f} (>4.5) {'✅ PASS' if ord_d2>4.5 else '❌ FAIL'}")
    return ord_d1, ord_d2


# ──────────────────────────────────────────────────────────────────────────────
# 2. WENO5 移流スキーム
# ──────────────────────────────────────────────────────────────────────────────

def test_weno5_convergence():
    """
    WENO5 空間切断誤差の直接評価（_rhs() 直接呼び出し法）。

    問題: u_t + u_x = 0, ψ = 0.5 + 0.4·sin(2πx) ∈ [0.1, 0.9]
    数値 RHS = adv._rhs(ψ, vel)  ← TVD-RK3 なし、WENO5 空間評価のみ
    厳密 RHS = −∂ψ/∂x = −0.4 · 2π · cos(2πx)

    修正理由:
    (1) dt∝h² は LF 拡散累積 ∝ 1/h で発散（前回修正）。
    (2) advance() の TVD-RK3 は中間ステージの WENO5 評価に O(dt) 誤差を導入し、
        N=128 で WENO5 5次空間誤差と同等のフロア (O(dt)~O(h^5)) を形成する。
    _rhs() 直接呼び出しでは WENO5 空間精度のみを純粋に評価できる。
    期待収束次数: 5次（WENO5）
    """
    print()
    print(SEP)
    print("【コンポーネント 2】WENO5 移流スキーム — 空間切断誤差（_rhs 直接評価）")
    print("  RHS 誤差 = |adv._rhs(ψ, vel) − (−∂ψ/∂x)|")
    print("  修正: advance()のRK3中間ステージがO(dt)誤差フロア → _rhs()直接評価")
    print(SEP)

    from twophase.levelset.advection import LevelSetAdvection

    Ns = [16, 32, 64, 128]
    results = []

    for N in Ns:
        cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
        grid = Grid(cfg.grid, be)
        adv = LevelSetAdvection(be, grid)

        X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1), indexing='ij')
        psi0 = 0.5 + 0.4 * np.sin(2*np.pi*X)   # ∈ [0.1, 0.9]
        u_vel = np.ones((N+1, N+1))
        v_vel = np.zeros((N+1, N+1))

        # WENO5 RHS を TVD-RK3 なしで直接計算
        rhs_num = adv._rhs(psi0, [u_vel, v_vel])

        # 厳密 RHS: −u · ∂ψ/∂x = −0.4 · 2π · cos(2πx)
        rhs_exact = -0.4 * 2*np.pi * np.cos(2*np.pi*X)

        # WENO5 のゴースト領域（各辺 3 点）を除いた内部格子点で評価
        sl = np.s_[3:-3, 3:-3]
        _, _, einf = errors(rhs_num[sl], rhs_exact[sl])
        results.append(einf)

    print(f"  {'N':>6}  {'L∞ (RHS誤差)':>16}  {'次数':>10}")
    print(f"  {'-'*38}")
    for i, N in enumerate(Ns):
        order = f"{conv_order(results[i-1], results[i]):.2f}" if i > 0 else "—"
        print(f"  {N:>6}  {results[i]:>16.3e}  {order:>10}")

    ord_weno = conv_order(results[-2], results[-1])
    status = "✅ PASS" if ord_weno > 3.5 else "❌ FAIL"
    print(f"\n  判定: WENO5 次数={ord_weno:.2f} (>3.5 期待) {status}")
    return ord_weno


def _weno5_divergence_only(adv, psi0, u_vel, v_vel):
    """TVD-RK3 なしで WENO5 の RHS だけを返す（プライベートメソッドを直接呼ぶ）。"""
    return adv._rhs(psi0, [u_vel, v_vel])


# ──────────────────────────────────────────────────────────────────────────────
# 3. 粘性項（Laplacian、一定粘性・密度）
# ──────────────────────────────────────────────────────────────────────────────

def test_viscous_convergence():
    """
    解析解: u = sin(2πx), μ = 1, ρ = 1, Re = 1
    対称歪み速度テンソル x 成分: V_x = (2/Re) d²u/dx² = 2·(−(2π)²)·sin(2πx)
    期待収束次数: ~5次（CCD 2段階適用）
    """
    print()
    print(SEP)
    print("【コンポーネント 3】粘性項（対称歪み速度テンソル) — 収束試験")
    print("  解析解: u = sin(2πx), V_x = 2Δu/Re (Re=1, μ=ρ=1)")
    print(SEP)

    from twophase.ns_terms.viscous import ViscousTerm

    Ns = [16, 32, 64, 128]
    results = []

    for N in Ns:
        cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
        grid = Grid(cfg.grid, be)
        ccd = CCDSolver(grid, be)
        visc = ViscousTerm(be, Re=1.0, cn_viscous=False)

        X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1), indexing='ij')
        u = np.sin(2*np.pi*X)
        v = np.zeros_like(u)
        mu = np.ones_like(u)
        rho = np.ones_like(u)

        result = visc.compute_explicit([u, v], mu, rho, ccd)
        expected = 2.0 * (-(2*np.pi)**2) * np.sin(2*np.pi*X)

        sl = np.s_[2:-2, 2:-2]
        _, _, einf = errors(result[0][sl], expected[sl])
        results.append(einf)

    print(f"  {'N':>6}  {'L∞':>14}  {'次数':>10}")
    print(f"  {'-'*35}")
    for i, N in enumerate(Ns):
        order = f"{conv_order(results[i-1], results[i]):.2f}" if i > 0 else "—"
        print(f"  {N:>6}  {results[i]:>14.3e}  {order:>10}")

    ord_visc = conv_order(results[-2], results[-1])
    status = "✅ PASS" if ord_visc > 3.5 else "❌ FAIL"
    print(f"\n  判定: 粘性項次数={ord_visc:.2f} (>3.5 期待) {status}")
    return ord_visc


# ──────────────────────────────────────────────────────────────────────────────
# 4. 圧力ポアソンソルバー（MMS）
# ──────────────────────────────────────────────────────────────────────────────

def test_ppe_convergence():
    """
    製造解法 (MMS):
      p(x,y) = cos(2πx) cos(2πy)
      ∂p/∂n = 0 at all walls  [Neumann BC 適合]
      Δp = −8π² cos(2πx)cos(2πy) → これを rhs とする

    修正理由: 旧テストの sin(2πx)sin(2πy) は ∂p/∂n ≠ 0 at x=0,1,y=0,1 であり
    ソルバーの Neumann BC と矛盾していたため収束しなかった。
    cos 型はすべての壁面で ∂/∂n = 0 を満たす。

    期待収束次数: 2次（FVM 2次中心差分）
    """
    print()
    print(SEP)
    print("【コンポーネント 4】圧力ポアソンソルバー — MMS 収束試験")
    print("  製造解: p = cos(2πx)cos(2πy) (∂p/∂n=0 at walls)")
    print("  修正: sin版は Neumann BC と矛盾 → cos版に変更")
    print(SEP)

    from twophase.pressure.ppe_solver import PPESolver

    Ns = [16, 32, 64, 128]
    results = []

    for N in Ns:
        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
            fluid=FluidConfig(Re=1.0),
            numerics=NumericsConfig(t_end=1.0),
        )
        grid = Grid(cfg.grid, be)

        X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1), indexing='ij')
        p_exact = np.cos(2*np.pi*X) * np.cos(2*np.pi*Y)
        rho = np.ones_like(p_exact)
        # Δ(cos·cos) = −4π²cos·cos − 4π²cos·cos = −8π²cos·cos
        rhs = -8.0 * np.pi**2 * np.cos(2*np.pi*X) * np.cos(2*np.pi*Y)

        solver = PPESolver(be, cfg, grid)
        p_num = solver.solve(rhs, rho, dt=1.0)

        # ソルバーは p[0,0]=0 にピン留め。解析解では p[0,0]=cos(0)cos(0)=1。
        # 定数シフトを解析的に補正する。
        p_num_corr = p_num + (p_exact.flat[0] - p_num.flat[0])

        sl = np.s_[1:-1, 1:-1]
        _, _, einf = errors(p_num_corr[sl], p_exact[sl])
        results.append(einf)

    print(f"  {'N':>6}  {'L∞':>14}  {'次数':>10}")
    print(f"  {'-'*35}")
    for i, N in enumerate(Ns):
        order = f"{conv_order(results[i-1], results[i]):.2f}" if i > 0 else "—"
        print(f"  {N:>6}  {results[i]:>14.3e}  {order:>10}")

    ord_ppe = conv_order(results[-2], results[-1])
    status = "✅ PASS" if ord_ppe > 1.5 else "❌ FAIL"
    print(f"\n  判定: PPE 次数={ord_ppe:.2f} (>1.5 期待) {status}")
    return ord_ppe


# ──────────────────────────────────────────────────────────────────────────────
# 5. 曲率計算（円形界面）
# ──────────────────────────────────────────────────────────────────────────────

def test_curvature_convergence():
    """
    2D 円形界面 R = 0.25:
      φ = r − R (外側正, 内側負)
      ψ = H_ε(φ) → 1 外側, 0 内側
      κ_code = −1/R = −4.0  [CLS 符号規約]

    修正理由: φ=r-R のとき κ は負の値になる（既存の test_curvature_circle も
    abs(κ) で比較している）。|κ| と 1/R を比較することで正しく評価できる。

    期待収束次数: 1次以上（ε∝h のスムージングが精度を制限）
    """
    print()
    print(SEP)
    print("【コンポーネント 5】曲率計算 — 円形界面収束試験")
    print("  解析解: |κ| = 1/R = 4.0 (R=0.25)")
    print("  修正: κ_code は符号が負 → |κ| と 1/R を比較")
    print(SEP)

    from twophase.levelset.curvature import CurvatureCalculator
    from twophase.levelset.heaviside import heaviside

    Ns = [16, 32, 64, 128]
    results = []

    for N in Ns:
        cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
        grid = Grid(cfg.grid, be)
        ccd = CCDSolver(grid, be)
        eps = 1.5 / N
        curv_calc = CurvatureCalculator(be, ccd, eps)

        X, Y = np.meshgrid(np.linspace(0, 1, N+1), np.linspace(0, 1, N+1), indexing='ij')
        R = 0.25
        phi = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - R
        psi = heaviside(xp, phi, eps)
        kappa = curv_calc.compute(psi)

        # 界面付近（|φ| < 2ε）での |κ| の誤差
        mask = np.abs(phi) < 2 * eps
        if mask.sum() < 4:
            results.append(float('nan'))
            continue

        kappa_exact = 1.0 / R   # = 4.0
        _, _, einf = errors(np.abs(kappa[mask]), np.full(mask.sum(), kappa_exact))
        results.append(einf)

    print(f"  {'N':>6}  {'L∞ |κ|−1/R':>16}  {'次数':>10}")
    print(f"  {'-'*42}")
    for i, N in enumerate(Ns):
        order_str = "—"
        if i > 0 and not math.isnan(results[i]) and not math.isnan(results[i-1]):
            order_str = f"{conv_order(results[i-1], results[i]):.2f}"
        val_str = f"{results[i]:.3e}" if not math.isnan(results[i]) else "NaN"
        print(f"  {N:>6}  {val_str:>16}  {order_str:>10}")

    ord_curv = conv_order(results[-2], results[-1]) if not math.isnan(results[-1]) else float('nan')
    status = "✅ PASS" if not math.isnan(ord_curv) and ord_curv > 0.8 else "❌ FAIL"
    print(f"\n  判定: 曲率次数={ord_curv:.2f} (>0.8 期待) {status}")
    return ord_curv


# ──────────────────────────────────────────────────────────────────────────────
# 6. TVD-RK3 時間積分
# ──────────────────────────────────────────────────────────────────────────────

def test_tvd_rk3_convergence():
    """
    ODE: dy/dt = −y, y(0) = 1, 厳密解: exp(−t)
    t_end = 1, dt を細かくして時間収束次数を確認。
    TVD-RK3 期待収束次数: 3次。
    """
    print()
    print(SEP)
    print("【コンポーネント 6】TVD-RK3 時間積分 — 時間収束試験")
    print("  ODE: dy/dt = −y, y(0) = 1, 厳密解: exp(−t)")
    print(SEP)

    from twophase.time_integration.tvd_rk3 import tvd_rk3

    dts = [0.1, 0.05, 0.025, 0.0125]
    t_end = 1.0
    results = []

    for dt in dts:
        y = np.array([1.0])
        t = 0.0
        while t < t_end - 1e-12:
            dt_step = min(dt, t_end - t)
            y = tvd_rk3(xp, y, dt_step, lambda q: -q)
            t += dt_step
        err = abs(y[0] - math.exp(-t_end))
        results.append(err)

    print(f"  {'dt':>10}  {'誤差':>14}  {'次数':>10}")
    print(f"  {'-'*38}")
    for i, dt in enumerate(dts):
        order = f"{conv_order(results[i-1], results[i]):.2f}" if i > 0 else "—"
        print(f"  {dt:>10.4f}  {results[i]:>14.3e}  {order:>10}")

    ord_rk3 = conv_order(results[-2], results[-1])
    status = "✅ PASS" if ord_rk3 > 2.5 else "❌ FAIL"
    print(f"\n  判定: TVD-RK3 次数={ord_rk3:.2f} (>2.5 期待) {status}")
    return ord_rk3


# ──────────────────────────────────────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("=" * 72)
    print("  10_EVALUATE.md — 数値コンポーネント収束検証（修正版）")
    print("=" * 72)

    ord_d1, ord_d2 = test_ccd_convergence()
    ord_weno       = test_weno5_convergence()
    ord_visc       = test_viscous_convergence()
    ord_ppe        = test_ppe_convergence()
    ord_curv       = test_curvature_convergence()
    ord_rk3        = test_tvd_rk3_convergence()

    print()
    print(SEP)
    print("【総合結果サマリー】")
    print(SEP)
    rows = [
        ("CCD 1階微分", ord_d1,   6,  4.5),
        ("CCD 2階微分", ord_d2,   6,  4.5),
        ("WENO5 移流",  ord_weno, 5,  3.5),
        ("粘性項",      ord_visc, 5,  3.5),
        ("PPE ソルバー",ord_ppe,  2,  1.5),
        ("曲率計算",    ord_curv, 2,  0.8),
        ("TVD-RK3",    ord_rk3,  3,  2.5),
    ]
    print(f"  {'コンポーネント':<18}  {'実測次数':>10}  {'理論次数':>10}  {'判定':>8}")
    print(f"  {'-'*55}")
    all_pass = True
    for name, ord_val, theory, threshold in rows:
        ok = not math.isnan(ord_val) and ord_val > threshold
        status = "✅ PASS" if ok else "❌ FAIL"
        if not ok:
            all_pass = False
        print(f"  {name:<18}  {ord_val:>10.2f}  {theory:>10}  {status:>8}")

    print()
    if all_pass:
        print("  ✅ 全コンポーネント 期待収束次数を達成")
    else:
        print("  ❌ 一部コンポーネントに問題あり")
    print()
