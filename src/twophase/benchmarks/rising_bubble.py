"""
上昇気泡ベンチマーク（Rising Bubble Benchmark）。

論文 Section 10.3.1 に対応。

浮力によって上昇する単一気泡の 2 次元シミュレーション。
Hysing et al. (2009) のテストケース 1 を基にした検証問題。

検証指標:
    - 気泡重心の時間変化
    - 気泡上昇速度の時間変化
    - 気泡体積保存誤差
    - 界面長さの変化

使用例::

    from twophase.benchmarks import RisingBubbleBenchmark

    bench = RisingBubbleBenchmark(N=64, t_end=3.0)
    results = bench.run(verbose=True)
    bench.plot(results, save_dir="results/rising_bubble/")
    bench.print_metrics(results)
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Optional, Any
from ..initial_conditions import InitialConditionBuilder, Circle


class RisingBubbleBenchmark:
    """上昇気泡ベンチマーク。

    パラメータは Hysing et al. (2009) テストケース 1 に準拠:
        Re = 35, We = 10, Fr = 1, ρ_ratio = 0.1, μ_ratio = 0.1

    Parameters
    ----------
    N       : 格子点数（一辺）
    t_end   : シミュレーション終了時刻
    verbose : 進捗を表示するかどうか
    """

    # Hysing et al. テストケース 1 のリファレンス値
    REFERENCE = {
        "centroid_y_at_t3": 1.0813,   # t=3 における気泡重心 y 座標
        "rise_velocity_max": 0.2417,   # 最大上昇速度
    }

    def __init__(
        self,
        N: int = 64,
        t_end: float = 3.0,
        verbose: bool = True,
    ):
        self.N = N
        self.t_end = t_end
        self.verbose = verbose

    def _make_config(self):
        """シミュレーション設定を構築する。"""
        from ..config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig
        return SimulationConfig(
            grid=GridConfig(ndim=2, N=(self.N, 2 * self.N), L=(1.0, 2.0)),
            fluid=FluidConfig(Re=35.0, Fr=1.0, We=10.0, rho_ratio=0.1, mu_ratio=0.1),
            numerics=NumericsConfig(
                epsilon_factor=1.5, reinit_steps=4, cfl_number=0.25,
                t_end=self.t_end, bc_type="wall",
            ),
            solver=SolverConfig(
                ppe_solver_type="ccd_lu",
            ),
        )

    def run(self, save_checkpoints: bool = False,
            checkpoint_dir: str = "checkpoints/rising_bubble") -> Dict[str, Any]:
        """ベンチマークを実行し、計測結果を返す。

        Parameters
        ----------
        save_checkpoints : チェックポイントを保存するかどうか
        checkpoint_dir   : チェックポイント保存ディレクトリ

        Returns
        -------
        results : 時系列データと最終指標を含む辞書
        """
        from ..simulation.builder import SimulationBuilder
        from ..io.checkpoint import CheckpointManager

        cfg = self._make_config()
        sim = SimulationBuilder(cfg).build()

        # 初期条件: 中心 (0.5, 0.5) 半径 0.25 の円形気泡
        psi0 = (
            InitialConditionBuilder(background_phase="gas")
            .add(Circle(center=(0.5, 0.5), radius=0.25))
            .build(sim.grid, sim.eps)
        )
        sim.psi.data = sim.backend.to_device(psi0)

        # 計測用時系列データ
        times, centroid_y, rise_velocity, volume = [], [], [], []
        dV = sim.grid.cell_volume()

        def record(s):
            """各ステップの指標を記録するコールバック。"""
            xp = s.backend.xp
            psi = s.psi.data
            _, Y_g = s.grid.meshgrid()
            Y_dev = s.backend.to_device(Y_g)

            # 体積（ψ の積分）
            vol = float(xp.sum(psi)) * dV
            # 重心 y 座標
            cy = float(xp.sum(psi * Y_dev) * dV / max(vol, 1e-14))
            # 上昇速度（重心の y 成分速度で近似）
            v_mean = float(xp.sum(psi * s.velocity[1]) * dV / max(vol, 1e-14))

            times.append(s.time)
            centroid_y.append(cy)
            rise_velocity.append(v_mean)
            volume.append(vol)

        # チェックポイント設定
        callbacks = [record]
        if save_checkpoints:
            mgr = CheckpointManager(checkpoint_dir)
            callbacks.append(mgr.make_callback(interval=1))

        def combined_callback(s):
            for cb in callbacks:
                cb(s)

        record(sim)  # 初期値を記録

        output_interval = max(1, int(self.t_end / 0.05 / 10))
        sim.run(
            t_end=self.t_end,
            output_interval=output_interval,
            verbose=self.verbose,
            callback=combined_callback,
        )

        initial_volume = volume[0] if volume else 1.0
        vol_error = abs(volume[-1] - initial_volume) / initial_volume if volume else 0.0

        results = {
            "times":         np.array(times),
            "centroid_y":    np.array(centroid_y),
            "rise_velocity": np.array(rise_velocity),
            "volume":        np.array(volume),
            "volume_error":  vol_error,
            "final_centroid_y": centroid_y[-1] if centroid_y else 0.0,
            "max_rise_velocity": max(rise_velocity) if rise_velocity else 0.0,
            "sim": sim,
        }
        return results

    def print_metrics(self, results: Dict[str, Any]) -> None:
        """計測結果を表示する。"""
        cy = results["final_centroid_y"]
        vmax = results["max_rise_velocity"]
        vol_err = results["volume_error"]
        ref_cy = self.REFERENCE["centroid_y_at_t3"]
        ref_v  = self.REFERENCE["rise_velocity_max"]

        print("\n=== 上昇気泡ベンチマーク 結果 ===")
        print(f"  最終重心 y 座標  : {cy:.4f}  (参照値: {ref_cy:.4f}, "
              f"誤差: {abs(cy - ref_cy):.4f})")
        print(f"  最大上昇速度     : {vmax:.4f}  (参照値: {ref_v:.4f}, "
              f"誤差: {abs(vmax - ref_v):.4f})")
        print(f"  体積保存誤差     : {vol_err:.2e}")
        print("================================\n")

    def plot(
        self,
        results: Dict[str, Any],
        save_dir: Optional[str] = None,
    ) -> None:
        """ベンチマーク結果をプロットする。

        Parameters
        ----------
        results  : run() の戻り値
        save_dir : 非 None の場合、図を PNG として保存するディレクトリ
        """
        import matplotlib.pyplot as plt
        import os

        if save_dir is not None:
            os.makedirs(save_dir, exist_ok=True)

        t = results["times"]

        # ── 1. 重心の時間変化 ──────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(7, 4), dpi=100)
        ax.plot(t, results["centroid_y"], "b-", label="シミュレーション")
        ax.axhline(self.REFERENCE["centroid_y_at_t3"], color="r",
                   linestyle="--", label=f"参照値 (t=3): {self.REFERENCE['centroid_y_at_t3']:.4f}")
        ax.set_xlabel("時刻 t")
        ax.set_ylabel("重心 y 座標")
        ax.set_title("上昇気泡: 重心の時間変化")
        ax.legend()
        ax.grid(True, alpha=0.4)
        if save_dir:
            fig.savefig(os.path.join(save_dir, "centroid_y.png"),
                        bbox_inches="tight")
        plt.show()

        # ── 2. 上昇速度の時間変化 ───────────────────────────────────────
        fig, ax = plt.subplots(figsize=(7, 4), dpi=100)
        ax.plot(t, results["rise_velocity"], "g-", label="シミュレーション")
        ax.axhline(self.REFERENCE["rise_velocity_max"], color="r",
                   linestyle="--", label=f"参照最大値: {self.REFERENCE['rise_velocity_max']:.4f}")
        ax.set_xlabel("時刻 t")
        ax.set_ylabel("重心上昇速度")
        ax.set_title("上昇気泡: 上昇速度の時間変化")
        ax.legend()
        ax.grid(True, alpha=0.4)
        if save_dir:
            fig.savefig(os.path.join(save_dir, "rise_velocity.png"),
                        bbox_inches="tight")
        plt.show()

        # ── 3. 体積保存誤差 ───────────────────────────────────────────────
        vol0 = results["volume"][0] if len(results["volume"]) > 0 else 1.0
        vol_err_ts = np.abs(results["volume"] - vol0) / max(vol0, 1e-14)
        fig, ax = plt.subplots(figsize=(7, 4), dpi=100)
        ax.semilogy(t, vol_err_ts + 1e-16, "m-", label="体積誤差")
        ax.set_xlabel("時刻 t")
        ax.set_ylabel("|V(t) − V(0)| / V(0)")
        ax.set_title("上昇気泡: 体積保存誤差")
        ax.legend()
        ax.grid(True, alpha=0.4)
        if save_dir:
            fig.savefig(os.path.join(save_dir, "volume_error.png"),
                        bbox_inches="tight")
        plt.show()

        # ── 4. 最終フィールド（レベルセット） ──────────────────────────────
        sim = results.get("sim")
        if sim is not None:
            from ..visualization.plot_scalar import plot_level_set
            fig = plot_level_set(
                np.asarray(sim.backend.to_host(sim.psi.data)),
                sim.grid,
                title=f"上昇気泡 t={sim.time:.3f}: ψ",
            )
            if save_dir:
                fig.savefig(os.path.join(save_dir, "final_psi.png"),
                            bbox_inches="tight")
            plt.show()
