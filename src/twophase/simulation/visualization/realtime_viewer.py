"""
リアルタイム可視化モジュール。

シミュレーション実行中にフィールドをインタラクティブに表示する。
``TwoPhaseSimulation.run()`` の ``callback`` 引数に渡して使用する。

使用例::

    from twophase.simulation.visualization import RealtimeViewer
    viewer = RealtimeViewer(sim, fields=["psi", "pressure", "velocity"])
    sim.run(output_interval=10, verbose=True, callback=viewer)
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..simulation import TwoPhaseSimulation


class RealtimeViewer:
    """シミュレーション実行中にフィールドをリアルタイム表示するビューワー。

    ``TwoPhaseSimulation.run()`` の ``callback`` 引数として渡すことで、
    指定した出力間隔ごとにプロットが更新される。

    Parameters
    ----------
    sim : TwoPhaseSimulation  — 初期化済みのシミュレーションオブジェクト
    fields : 表示するフィールド名のリスト。
             選択肢: ``"psi"``, ``"pressure"``, ``"velocity"``,
                     ``"vorticity"``, ``"density"``
    figsize : 図のサイズ（None の場合は自動）
    save_dir : 非 None の場合、各フレームを PNG として保存するディレクトリ
    dpi : 解像度
    """

    # 各フィールドの (カラーマップ, タイトル, ラベル) 設定
    _FIELD_CONFIGS = {
        "psi":      ("bwr",     "レベルセット ψ",   "ψ",    (0.0, 1.0)),
        "pressure": ("RdBu_r",  "圧力 p",          "p",    (None, None)),
        "density":  ("Blues",   "密度 ρ",           "ρ",    (None, None)),
        "vorticity":("seismic", "渦度 ω",           "ω",    (None, None)),
        "velocity": ("viridis", "速度 |u|",         "|u|",  (None, None)),
    }

    def __init__(
        self,
        sim: "TwoPhaseSimulation",
        fields: List[str] = None,
        figsize: Optional[tuple] = None,
        save_dir: Optional[str] = None,
        dpi: int = 100,
    ):
        if fields is None:
            fields = ["psi", "pressure", "velocity"]

        for f in fields:
            if f not in self._FIELD_CONFIGS:
                raise ValueError(
                    f"未知のフィールド名: '{f}'. "
                    f"選択肢: {list(self._FIELD_CONFIGS.keys())}"
                )

        self.sim = sim
        self.fields = fields
        self.save_dir = save_dir
        self.dpi = dpi
        self._frame = 0

        n = len(fields)
        if figsize is None:
            figsize = (5 * n, 4.5)

        # インタラクティブモードを有効化
        plt.ion()
        self.fig, self._axes = plt.subplots(1, n, figsize=figsize, dpi=dpi)
        if n == 1:
            self._axes = [self._axes]

        self._images = {}
        self._init_plots()

    # ── コールバックインターフェース ──────────────────────────────────────

    def __call__(self, sim: "TwoPhaseSimulation") -> None:
        """シミュレーションから呼ばれるコールバック。フィールドを更新する。"""
        self._update_plots()
        self._frame += 1

        if self.save_dir is not None:
            import os
            os.makedirs(self.save_dir, exist_ok=True)
            path = os.path.join(
                self.save_dir, f"frame_{self._frame:06d}.png"
            )
            self.fig.savefig(path, bbox_inches="tight", dpi=self.dpi)

    def close(self) -> None:
        """ウィンドウを閉じる。"""
        plt.ioff()
        plt.close(self.fig)

    # ── 内部メソッド ─────────────────────────────────────────────────────

    def _get_field_data(self, name: str) -> np.ndarray:
        """フィールド名から numpy 配列を取得する。"""
        sim = self.sim
        be = sim.backend

        if name == "psi":
            return np.asarray(be.to_host(sim.psi.data))
        elif name == "pressure":
            return np.asarray(be.to_host(sim.pressure.data))
        elif name == "density":
            return np.asarray(be.to_host(sim.rho.data))
        elif name == "vorticity":
            from .plot_vector import compute_vorticity_2d
            u = np.asarray(be.to_host(sim.velocity[0]))
            v = np.asarray(be.to_host(sim.velocity[1]))
            return np.asarray(be.to_host(
                compute_vorticity_2d(u, v, sim.ccd)
            ))
        elif name == "velocity":
            u = np.asarray(be.to_host(sim.velocity[0]))
            v = np.asarray(be.to_host(sim.velocity[1]))
            return np.sqrt(u ** 2 + v ** 2)
        else:
            raise ValueError(f"未知のフィールド: {name}")

    def _init_plots(self) -> None:
        """初期プロットを作成する。"""
        X, Y = self.sim.grid.meshgrid()
        psi_np = np.asarray(self.sim.backend.to_host(self.sim.psi.data))

        for ax, name in zip(self._axes, self.fields):
            cmap, title, label, (vmin, vmax) = self._FIELD_CONFIGS[name]
            data = self._get_field_data(name)

            im = ax.pcolormesh(X, Y, data, cmap=cmap,
                               vmin=vmin, vmax=vmax, shading="auto")
            self.fig.colorbar(im, ax=ax, label=label)
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_aspect("equal")
            ax.set_title(f"t=0.000  {title}")
            self._images[name] = im

            # 界面等値線（ψ系フィールド以外でも常時表示）
            ax.contour(X, Y, psi_np, levels=[0.5],
                       colors="white", linewidths=1.0, linestyles="--",
                       alpha=0.8)

        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def _update_plots(self) -> None:
        """プロットデータを最新フィールドで更新する。"""
        X, Y = self.sim.grid.meshgrid()
        psi_np = np.asarray(self.sim.backend.to_host(self.sim.psi.data))
        t = self.sim.time

        for ax, name in zip(self._axes, self.fields):
            cmap, title, label, (vmin, vmax) = self._FIELD_CONFIGS[name]
            data = self._get_field_data(name)

            # pcolormesh を再描画（等値線は毎回クリア）
            ax.cla()
            im = ax.pcolormesh(X, Y, data, cmap=cmap,
                               vmin=vmin, vmax=vmax, shading="auto")
            ax.contour(X, Y, psi_np, levels=[0.5],
                       colors="white", linewidths=1.0, linestyles="--",
                       alpha=0.8)
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            ax.set_aspect("equal")
            ax.set_title(f"t={t:.4f}  {title}")
            self._images[name] = im

        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
