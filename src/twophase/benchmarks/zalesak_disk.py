"""
Zalesak のスロット付き円盤ベンチマーク（Zalesak Disk Benchmark）。

論文 Section 10.3.2 に対応。

スロット付き円盤を一様回転速度場で 1 回転させ、
初期形状への回帰精度を測定する純移流テスト。
数値拡散・界面変形の定量評価に広く使われる標準ベンチマーク。

検証指標:
    - 1 回転後の L1 形状誤差
    - 体積保存誤差
    - 界面の形状精度

参考文献:
    Zalesak, S. T. (1979). Fully multidimensional flux-corrected
    transport algorithms for fluids. J. Comput. Phys., 31(3), 335-362.

使用例::

    from twophase.benchmarks import ZalesakDiskBenchmark

    bench = ZalesakDiskBenchmark(N=64)
    results = bench.run(verbose=True)
    bench.plot(results, save_dir="results/zalesak/")
    bench.print_metrics(results)
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Optional, Any

from ..initial_conditions import RigidRotation


class ZalesakDiskBenchmark:
    """Zalesak スロット付き円盤ベンチマーク。

    Parameters
    ----------
    N     : 格子点数（一辺）
    n_rev : 回転数（デフォルト = 1）
    """

    def __init__(self, N: int = 64, n_rev: float = 1.0):
        self.N = N
        self.n_rev = n_rev

    @staticmethod
    def _make_slotted_disk(X: np.ndarray, Y: np.ndarray, eps: float) -> np.ndarray:
        """スロット付き円盤の Conservative Level Set ψ を構築する。

        円: 中心 (0.5, 0.75)、半径 0.15
        スロット: 幅 0.05、高さ 0.25（円下部に切れ込み）
        """
        cx, cy, r0 = 0.5, 0.75, 0.15
        slot_width = 0.025
        slot_bottom = 0.6

        # 円の signed distance
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - r0

        # スロット内部のマスク
        in_slot = (
            (np.abs(X - cx) <= slot_width) &
            (Y >= slot_bottom) &
            (Y <= cy + r0)
        )

        # スロット部分は外部（dist > 0）として扱う
        dist[in_slot] = np.abs(dist[in_slot]) + 1e-6

        # CLS 変換: ψ = 1/(1 + exp(dist/ε))
        psi = 1.0 / (1.0 + np.exp(dist / eps))
        return psi

    def run(self, verbose: bool = True) -> Dict[str, Any]:
        """ベンチマークを実行する。

        Parameters
        ----------
        verbose : 進捗表示フラグ

        Returns
        -------
        results : L1 誤差・体積誤差・フィールドスナップショットを含む辞書
        """
        from ..config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig
        from ..simulation.builder import SimulationBuilder

        # 1 回転の周期
        T = 1.0 / self.n_rev

        cfg = SimulationConfig(
            grid=GridConfig(ndim=2, N=(self.N, self.N), L=(1.0, 1.0)),
            fluid=FluidConfig(Re=1e6, Fr=1e6, We=1e6, rho_ratio=1.0, mu_ratio=1.0),
            numerics=NumericsConfig(
                epsilon_factor=1.5, reinit_steps=2, cfl_number=0.3, t_end=T, bc_type="wall",
            ),
            solver=SolverConfig(
                ppe_solver_type="pseudotime", pseudo_tol=1e-8, pseudo_maxiter=500,
            ),
        )

        sim = SimulationBuilder(cfg).build()
        X, Y = sim.grid.meshgrid()
        eps = sim.eps

        # 初期条件
        psi0 = self._make_slotted_disk(X, Y, eps)
        sim.psi.data = sim.backend.to_device(psi0.copy())

        # 速度場を固定（predictor を使わず直接設定）
        u_rot, v_rot = RigidRotation(center=(0.5, 0.5), period=T).compute(X, Y)
        sim.velocity[0] = sim.backend.to_device(u_rot)
        sim.velocity[1] = sim.backend.to_device(v_rot)

        # --- NOTE: Zalesak テストでは速度場を外部から固定するため、
        #     各タイムステップ後にコールバックで速度を再設定する ---
        def fix_velocity(s):
            s.velocity[0] = s.backend.to_device(u_rot)
            s.velocity[1] = s.backend.to_device(v_rot)

        dV = sim.grid.cell_volume()
        initial_volume = float(np.sum(psi0)) * dV

        output_interval = max(1, self.N // 4)
        sim.run(
            t_end=T,
            output_interval=output_interval,
            verbose=verbose,
            callback=fix_velocity,
        )

        # 1 回転後の ψ
        psi_final = np.asarray(sim.backend.to_host(sim.psi.data))

        # L1 誤差（正規化）
        l1_error = float(np.sum(np.abs(psi_final - psi0))) * dV

        # 体積誤差
        final_volume = float(np.sum(psi_final)) * dV
        volume_error = abs(final_volume - initial_volume) / max(initial_volume, 1e-14)

        results = {
            "psi_initial":   psi0,
            "psi_final":     psi_final,
            "l1_error":      l1_error,
            "volume_error":  volume_error,
            "initial_volume": initial_volume,
            "final_volume":  final_volume,
            "sim":           sim,
        }
        return results

    def print_metrics(self, results: Dict[str, Any]) -> None:
        """計測結果を表示する。"""
        print("\n=== Zalesak 円盤ベンチマーク 結果 ===")
        print(f"  L1 形状誤差   : {results['l1_error']:.4e}")
        print(f"  体積保存誤差  : {results['volume_error']:.2e}")
        print(f"  初期体積      : {results['initial_volume']:.6f}")
        print(f"  最終体積      : {results['final_volume']:.6f}")
        print("=====================================\n")

    def plot(
        self,
        results: Dict[str, Any],
        save_dir: Optional[str] = None,
    ) -> None:
        """初期・最終の ψ を並べてプロットする。

        Parameters
        ----------
        results  : run() の戻り値
        save_dir : 保存先ディレクトリ
        """
        import matplotlib.pyplot as plt
        import os

        if save_dir is not None:
            os.makedirs(save_dir, exist_ok=True)

        sim = results["sim"]
        grid = sim.grid
        X, Y = grid.meshgrid()

        fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=100)

        for ax, (psi, title) in zip(
            axes,
            [(results["psi_initial"], "初期 ψ（t=0）"),
             (results["psi_final"],   f"最終 ψ（{self.n_rev}回転後）")]
        ):
            im = ax.pcolormesh(X, Y, psi, cmap="bwr",
                               vmin=0.0, vmax=1.0, shading="auto")
            ax.contour(X, Y, psi, levels=[0.5],
                       colors="white", linewidths=1.5, linestyles="--")
            fig.colorbar(im, ax=ax, label="ψ")
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_aspect("equal")
            ax.set_title(title)

        fig.suptitle(
            f"Zalesak 円盤  N={self.N}  "
            f"L1誤差={results['l1_error']:.3e}  "
            f"体積誤差={results['volume_error']:.2e}",
            fontsize=11,
        )
        fig.tight_layout()
        if save_dir:
            fig.savefig(os.path.join(save_dir, "zalesak_comparison.png"),
                        bbox_inches="tight")
        plt.show()
