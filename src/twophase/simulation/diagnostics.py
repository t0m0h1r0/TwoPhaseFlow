"""
診断レポータ。

単一責務の原則 (SRP) に従い、診断情報の出力ロジックを
TwoPhaseSimulation から分離した独立モジュール。

報告する診断値:
    - 現在時刻 t、タイムステップ幅 Δt
    - 速度の発散 |∇·u|_∞（非圧縮性の残差）
    - レベルセット体積 ∫ψ dV（体積保存誤差の指標）
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


class DiagnosticsReporter:
    """シミュレーション診断情報をコンソールに出力するクラス。

    Parameters
    ----------
    backend : Backend — xp (numpy/cupy) アクセス用
    grid    : Grid — 格子形状と格子体積用
    """

    def __init__(self, backend: "Backend", grid: "Grid") -> None:
        self.backend = backend
        self.grid = grid

    def report(self, sim, dt: float) -> None:
        """Compute and print diagnostics.

        Parameters
        ----------
        sim : TwoPhaseSimulation
        dt  : float — current time step size
        """
        xp = self.backend.xp

        # Velocity divergence (incompressibility residual)
        div = xp.zeros(self.grid.shape)
        for ax in range(self.grid.ndim):
            d1, _ = sim.ccd.differentiate(sim.velocity[ax], ax)
            div += d1
        div_max = float(xp.max(xp.abs(div)))

        # Level-set volume (integral of psi)
        dV = self.grid.cell_volume()
        vol = float(xp.sum(sim.psi.data)) * dV

        # Effective interface thickness diagnostic (section 3b eq. epsilon_eff)
        eps_eff_str = ""
        if hasattr(sim, 'eps') and sim.eps > 0:
            eps_eff_ratio = self._compute_eps_eff_ratio(xp, sim)
            if eps_eff_ratio is not None:
                eps_eff_str = f"  ε_eff/ε={eps_eff_ratio:.3f}"

        print(
            f"  t={sim.time:.5f}  dt={dt:.3e}  "
            f"|∇·u|_∞={div_max:.3e}  vol(ψ)={vol:.6f}{eps_eff_str}"
        )

    def _compute_eps_eff_ratio(self, xp, sim) -> float | None:
        """Compute mean eps_eff / eps near the interface (section 3b eq. epsilon_eff).

        Uses MEAN over band psi(1-psi) > 0.1, returns RATIO to nominal eps.
        Designed for real-time CLI output during simulation.

        For offline analysis with median-based robustness, use instead:
            diagnostics.interface_diagnostics.measure_eps_eff()
        which returns the absolute eps_eff (not ratio) using median over
        the 0.05 < psi < 0.95 band.

        Returns
        -------
        float or None : mean eps_eff / eps near interface, or None if
                        insufficient interface points.
        """
        psi = sim.psi.data

        # Gradient magnitude
        grad_sq = xp.zeros_like(psi)
        for ax in range(self.grid.ndim):
            d1, _ = sim.ccd.differentiate(psi, ax)
            grad_sq += d1 ** 2
        grad_mag = xp.sqrt(grad_sq)

        # Near-interface mask: psi(1-psi) > 0.1 (within ~2 interface widths)
        psi_1mpsi = psi * (1.0 - psi)
        near_iface = psi_1mpsi > 0.1

        if xp.sum(near_iface) < 4:
            return None

        eps_eff = psi_1mpsi[near_iface] / xp.maximum(grad_mag[near_iface], 1e-30)
        return float(xp.mean(eps_eff)) / sim.eps
