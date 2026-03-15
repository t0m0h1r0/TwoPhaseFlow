"""
Velocity predictor step (u* computation).

Implements Step 5 of the full algorithm (§9.1 Eq. 85–92).

The predictor solves:

    ρ̃^{n+1} (u* − uⁿ) / Δt = R^{n+1}

where the RHS collects:

    R = −ρ̃ (u·∇)u                    (convection, explicit)
      + (1/Re) ∇·[μ̃ (∇u+∇uᵀ)]        (viscous, CN or explicit)
      − ρ̃ ẑ / Fr²                     (gravity, explicit)
      + κ ∇ψ / We                     (surface tension, at t^{n+1})

The predictor does NOT enforce ∇·u* = 0; that is handled by the pressure
Poisson equation and the corrector step.

When ``cn_viscous=True`` the viscous term uses the Crank-Nicolson scheme
(§9), which performs one fixed-point iteration:
  1. Compute explicit u* with V(uⁿ).
  2. Evaluate V(u*) and recompute with the average ½[V(uⁿ)+V(u*)].

DIP 改善（2026-03-15）:
    - ConvectionTerm, ViscousTerm, GravityTerm, SurfaceTensionTerm を
      コンストラクタで注入可能にした（デフォルト値で後方互換を維持）。
    - Predictor 自体は具象クラスを知らなくてよくなった。
    - SimulationBuilder がデフォルト依存関係を組み立てる責務を担う。

ISP 改善（2026-03-15 3rd pass）:
    - ccd をコンストラクタ注入に変更。
    - compute() のシグネチャから ccd を除去し、他の演算子と統一した。
"""

from __future__ import annotations
import numpy as np
from typing import List, Optional, TYPE_CHECKING

from .convection import ConvectionTerm
from .viscous import ViscousTerm
from .gravity import GravityTerm
from .surface_tension import SurfaceTensionTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..interfaces.ns_terms import INSTerm


class Predictor:
    """Assemble all NS RHS terms and advance u → u*.

    Parameters
    ----------
    backend        : Backend
    config         : SimulationConfig
    ccd            : CCDSolver — コンストラクタ注入（毎呼び出しでの引き渡し不要）
    convection     : ConvectionTerm インスタンス（省略時はデフォルト生成）
    viscous        : ViscousTerm インスタンス（省略時はデフォルト生成）
    gravity        : GravityTerm インスタンス（省略時はデフォルト生成）
    surface_tension: SurfaceTensionTerm インスタンス（省略時はデフォルト生成）

    注: 各項を外部から注入することで、テスト・差し替えが容易になる（DIP）。
        引数を省略した場合は config の値から自動生成し、後方互換を保つ。
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        ccd: "CCDSolver",
        convection: Optional["INSTerm"] = None,
        viscous: Optional["INSTerm"] = None,
        gravity: Optional["INSTerm"] = None,
        surface_tension: Optional["INSTerm"] = None,
    ):
        self.xp = backend.xp
        self.config = config
        self.ccd = ccd   # コンストラクタ注入

        # 注入された依存関係を使用。省略時はデフォルト生成
        self.convection   = convection    or ConvectionTerm(backend)
        self.viscous      = viscous       or ViscousTerm(backend, config.fluid.Re, config.numerics.cn_viscous)
        self.gravity      = gravity       or GravityTerm(backend, config.fluid.Fr, config.grid.ndim)
        self.surface_tens = surface_tension or SurfaceTensionTerm(backend, config.fluid.We)

    def compute(
        self,
        vel_n: List,
        rho: "array",
        mu: "array",
        kappa: "array",
        psi: "array",
        dt: float,
    ) -> List:
        """Compute u* = uⁿ + Δt * R / ρ̃.

        Parameters
        ----------
        vel_n  : velocity components [u, v[, w]] at time n
        rho    : density at time n+1
        mu     : viscosity at time n+1
        kappa  : curvature at time n+1
        psi    : CLS field at time n+1
        dt     : time step

        Returns
        -------
        vel_star : list of u* arrays
        """
        xp = self.xp
        ccd = self.ccd   # コンストラクタ注入済みの ccd を使用

        # ── Explicit terms ────────────────────────────────────────────────
        conv = self.convection.compute(vel_n, ccd)           # −(u·∇)u  (ρ-weighted later)
        grav = self.gravity.compute(rho, vel_n[0].shape)     # −ρ̃ ẑ/Fr²
        st   = self.surface_tens.compute(kappa, psi, ccd)    # κ ∇ψ/We

        # ── Combine explicit terms (per component) ────────────────────────
        # Multiply convection by ρ̃ (because it enters as ρ̃ a_conv = −ρ̃(u·∇)u)
        explicit_rhs = [
            rho * conv[c] + grav[c] + st[c]
            for c in range(self.config.grid.ndim)
        ]

        # ── Viscous term (CN or explicit) ─────────────────────────────────
        if self.config.numerics.cn_viscous:
            vel_star = self.viscous.apply_cn_predictor(
                vel_n, None, explicit_rhs, mu, rho, ccd, dt
            )
        else:
            visc = self.viscous.compute_explicit(vel_n, mu, rho, ccd)
            vel_star = [
                vel_n[c] + dt * (explicit_rhs[c] + rho * visc[c]) / rho
                for c in range(self.config.grid.ndim)
            ]

        return vel_star
