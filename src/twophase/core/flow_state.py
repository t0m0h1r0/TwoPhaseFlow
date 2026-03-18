"""
FlowState — 単一タイムステップにおける流体場の集約データクラス。

設計方針:
    - `TwoPhaseSimulation.step_forward()` や `Predictor.compute()` が
      多数の引数をフラットに受け渡している問題を解消する（引数の構造化）。
    - 新しい物理場（温度場・濃度場等）を追加する際、呼び出しシグネチャを
      変更せず FlowState にフィールドを追加するだけで済む（OCP）。
    - 純粋なデータ保持オブジェクト（ロジックを持たない）。
      計算は各 NS 項クラス・Predictor・step_* メソッドが担う（SRP）。

使用例::

    from twophase.core.flow_state import FlowState

    state = FlowState(
        velocity=[u, v],
        psi=psi_array,
        rho=rho_array,
        mu=mu_array,
        kappa=kappa_array,
        pressure=p_array,
    )
    vel_star = predictor.compute(state, dt)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass
class FlowState:
    """単一タイムステップにおける流体場の集約。

    Attributes
    ----------
    velocity : list of array
        速度成分 [u, v[, w]]。各要素は形状 (N0+1, N1+1[, N2+1]) の配列。
    psi      : array
        Conservative Level Set 関数 ψ ∈ [0, 1]。
    rho      : array
        正則化密度場 ρ̃ = ρ_g + (ρ_l − ρ_g)ψ。
    mu       : array
        正則化粘性場 μ̃ = μ_g + (μ_l − μ_g)ψ。
    kappa    : array
        曲率場 κ（§2.6）。
    pressure : array
        圧力場 p^n（PPE の初期推定値にも使用）。
    """

    velocity: List   # [u, v[, w]] — ndim 個の配列
    psi: object      # ψ — CLS フィールド
    rho: object      # ρ̃ — 密度
    mu: object       # μ̃ — 粘性
    kappa: object    # κ  — 曲率
    pressure: object # p  — 圧力
