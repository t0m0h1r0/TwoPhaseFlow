"""
Rayleigh-Taylor 不安定性ベンチマーク。

論文 Section 10.3.3 に対応。

重い流体（上）と軽い流体（下）の界面における重力駆動不安定性。
界面変形・スパイク・バブル成長の精度を検証する。

検証指標:
    - スパイク先端位置の時間変化
    - バブル先端位置の時間変化
    - 体積保存誤差

参考文献:
    Guermond & Quartapelle (2000), Tryggvason (1988)

使用例::

    from twophase.benchmarks import RayleighTaylorBenchmark

    bench = RayleighTaylorBenchmark(N=64)
    results = bench.run(verbose=True)
    bench.plot(results, save_dir="results/rayleigh_taylor/")
    bench.print_metrics(results)
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Optional, Any


class RayleighTaylorBenchmark:
    """Rayleigh-Taylor 不安定性ベンチマーク。

    ドメイン: [0, 0.5] × [0, 2]
    初期界面: y = 1 + 0.1 * cos(2π x / 0.5)
    重い流体（ρ₂）が上、軽い流体（ρ₁）が下

    Parameters
    ----------
    N     : x 方向の格子点数（y 方向は 4N）
    t_end : シミュレーション終了時刻
    Re    : レイノルズ数
    """

    def __init__(self, N: int = 32, t_end: float = 3.0, Re: float = 3000.0):
        self.N = N
        self.t_end = t_end
        self.Re = Re

    def _make_config(self):
        from ..config import SimulationConfig
        return SimulationConfig(
            ndim=2,
            N=(self.N, 4 * self.N),
            L=(0.5, 2.0),
            Re=self.Re,
            Fr=1.0,
            We=1e6,           # 表面張力無視
            rho_ratio=0.2,    # ρ₁/ρ₂ = 0.2（密度比 5:1）
            mu_ratio=0.2,
            epsilon_factor=1.5,
            reinit_steps=4,
            cfl_number=0.25,
            t_end=self.t_end,
            ppe_solver_type="bicgstab",
            bicgstab_tol=1e-10,
            bicgstab_maxiter=2000,
            bc_type="wall",
            use_gpu=False,
        )

    def run(self, verbose: bool = True) -> Dict[str, Any]:
        """ベンチマークを実行する。

        Returns
        -------
        results : スパイク/バブル先端位置の時系列と最終フィールドを含む辞書
        """
        from ..simulation import TwoPhaseSimulation

        cfg = self._make_config()
        sim = TwoPhaseSimulation(cfg)
        X, Y = sim.grid.meshgrid()
        eps = sim.eps

        # 初期界面: y = 1 + 0.1 * cos(2π x / Lx)
        Lx = cfg.L[0]
        y_interface = 1.0 + 0.1 * np.cos(2.0 * np.pi * X / Lx)
        # ψ = 1（重い流体=上）, ψ = 0（軽い流体=下）
        dist = Y - y_interface
        psi0 = 1.0 / (1.0 + np.exp(dist / eps))
        sim.psi.data = sim.backend.to_device(psi0.copy())

        # 計測用時系列データ
        times, spike_tips, bubble_tips = [], [], []
        dV = sim.grid.cell_volume()
        initial_volume = float(np.sum(psi0)) * dV

        def record(s):
            xp = s.backend.xp
            psi = np.asarray(s.backend.to_host(s.psi.data))
            _, Y_g = s.grid.meshgrid()

            # 界面位置（列ごとの ψ=0.5 crossing）を近似
            # スパイク: 重流体（ψ > 0.5）の最小 y 値
            # バブル:  軽流体（ψ < 0.5）の最大 y 値
            heavy = psi > 0.5
            if heavy.any():
                spike_y = float(Y_g[heavy].min())
            else:
                spike_y = float(Y_g.min())

            light = psi < 0.5
            if light.any():
                bubble_y = float(Y_g[light].max())
            else:
                bubble_y = float(Y_g.max())

            times.append(s.time)
            spike_tips.append(spike_y)
            bubble_tips.append(bubble_y)

        record(sim)  # 初期値を記録

        output_interval = max(1, int(self.t_end / 0.1 / 10))
        sim.run(
            t_end=self.t_end,
            output_interval=output_interval,
            verbose=verbose,
            callback=record,
        )

        psi_final = np.asarray(sim.backend.to_host(sim.psi.data))
        final_volume = float(np.sum(psi_final)) * dV
        volume_error = abs(final_volume - initial_volume) / max(initial_volume, 1e-14)

        results = {
            "times":        np.array(times),
            "spike_tips":   np.array(spike_tips),
            "bubble_tips":  np.array(bubble_tips),
            "volume_error": volume_error,
            "psi_final":    psi_final,
            "sim":          sim,
        }
        return results

    def print_metrics(self, results: Dict[str, Any]) -> None:
        """計測結果を表示する。"""
        print("\n=== Rayleigh-Taylor 不安定性 結果 ===")
        print(f"  スパイク先端最終 y : {results['spike_tips'][-1]:.4f}")
        print(f"  バブル先端最終 y   : {results['bubble_tips'][-1]:.4f}")
        print(f"  体積保存誤差       : {results['volume_error']:.2e}")
        print("=====================================\n")

    def plot(
        self,
        results: Dict[str, Any],
        save_dir: Optional[str] = None,
    ) -> None:
        """ベンチマーク結果をプロットする。

        Parameters
        ----------
        results  : run() の戻り値
        save_dir : 保存先ディレクトリ
        """
        import matplotlib.pyplot as plt
        import os

        if save_dir is not None:
            os.makedirs(save_dir, exist_ok=True)

        t = results["times"]

        # ── 1. スパイク・バブル先端位置の時間変化 ──────────────────────
        fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
        ax.plot(t, results["spike_tips"],  "r-",  label="スパイク先端（重流体最小 y）")
        ax.plot(t, results["bubble_tips"], "b--", label="バブル先端（軽流体最大 y）")
        ax.set_xlabel("時刻 t")
        ax.set_ylabel("y 座標")
        ax.set_title("Rayleigh-Taylor 不安定性: 先端位置")
        ax.legend()
        ax.grid(True, alpha=0.4)
        if save_dir:
            fig.savefig(os.path.join(save_dir, "tip_positions.png"),
                        bbox_inches="tight")
        plt.show()

        # ── 2. 最終 ψ フィールド ───────────────────────────────────────
        sim = results.get("sim")
        if sim is not None:
            from ..visualization.plot_scalar import plot_level_set
            fig = plot_level_set(
                results["psi_final"],
                sim.grid,
                title=f"Rayleigh-Taylor  t={sim.time:.3f}: ψ",
            )
            if save_dir:
                fig.savefig(os.path.join(save_dir, "final_psi.png"),
                            bbox_inches="tight")
            plt.show()
