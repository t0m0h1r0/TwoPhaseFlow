"""
チェックポイント保存・リスタートモジュール。

HDF5 形式（h5py が利用可能な場合）または NumPy npz 形式で
シミュレーション状態を保存・復元する。

SOLID リファクタリング後の変更点:
    - HDF5/NPZ の具体的な I/O 処理を HDF5Serializer / NpzSerializer に委譲（SRP修正）。
    - CheckpointManager はコーディネータとして、ファイル管理と状態の収集・復元に専念する。

保存データ:
    - タイムステップ番号・物理時刻
    - 速度場（全成分）
    - 圧力場
    - レベルセット ψ
    - 格子情報（N, L, ndim）
    - SimulationConfig のシリアライズ

使用例::

    from twophase.io import CheckpointManager

    mgr = CheckpointManager("checkpoints/")

    # コールバックとして登録（100ステップごとに保存）
    sim.run(output_interval=100, callback=mgr.make_callback(interval=100))

    # リスタート
    mgr.restore(sim, "checkpoints/step_000200.h5")
"""

from __future__ import annotations
import os
import json
import dataclasses
import numpy as np
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..simulation import TwoPhaseSimulation

from .serializers import HDF5Serializer, NpzSerializer


def _h5py_available() -> bool:
    """h5py がインストールされているか確認する。"""
    try:
        import h5py  # noqa: F401
        return True
    except ImportError:
        return False


class CheckpointManager:
    """チェックポイントの保存・ロードを管理するコーディネータクラス。

    形式別 I/O の詳細は HDF5Serializer または NpzSerializer に委譲する（SRP修正）。

    Parameters
    ----------
    directory : チェックポイントを保存するディレクトリ
    use_hdf5  : True の場合 HDF5、False の場合 npz 形式を使用。
                デフォルトは h5py の有無で自動選択。
    """

    def __init__(
        self,
        directory: str = "checkpoints",
        use_hdf5: Optional[bool] = None,
    ):
        self.directory = directory
        if use_hdf5 is None:
            self.use_hdf5 = _h5py_available()
        else:
            self.use_hdf5 = use_hdf5
            if use_hdf5 and not _h5py_available():
                raise ImportError(
                    "h5py が見つかりません。pip install h5py でインストールしてください。"
                )

        self._ext = ".h5" if self.use_hdf5 else ".npz"
        # シリアライザを注入（DIP: 具体的な形式に直接依存しない）
        self._serializer = HDF5Serializer() if self.use_hdf5 else NpzSerializer()

    # ── 保存 ─────────────────────────────────────────────────────────────

    def save(self, sim: "TwoPhaseSimulation", step: Optional[int] = None) -> str:
        """シミュレーション状態をファイルに保存する。

        Parameters
        ----------
        sim  : TwoPhaseSimulation — 保存するシミュレーション
        step : ファイル名に使うステップ番号（None の場合は sim.step を使用）

        Returns
        -------
        path : 保存されたファイルのパス
        """
        os.makedirs(self.directory, exist_ok=True)
        s = step if step is not None else sim.step
        fname = f"step_{s:08d}{self._ext}"
        path = os.path.join(self.directory, fname)

        state = self._collect_state(sim)
        self._serializer.save(path, state)

        return path

    def make_callback(self, interval: int = 100):
        """``sim.run()`` に渡せるコールバック関数を返す。

        Parameters
        ----------
        interval : 何ステップごとに保存するか（run の output_interval と組み合わせて使う）

        Returns
        -------
        callback : f(sim) → None
        """
        counter = {"n": 0}

        def callback(sim: "TwoPhaseSimulation") -> None:
            counter["n"] += 1
            if counter["n"] % interval == 0:
                path = self.save(sim)
                print(f"  [checkpoint] saved → {path}")

        return callback

    # ── ロード ────────────────────────────────────────────────────────────

    def restore(self, sim: "TwoPhaseSimulation", path: str) -> None:
        """チェックポイントファイルからシミュレーション状態を復元する。

        Parameters
        ----------
        sim  : TwoPhaseSimulation — 復元先のシミュレーション
        path : チェックポイントファイルのパス
        """
        # ファイル拡張子で読み込む形式を自動判定
        if path.endswith(".h5"):
            state = HDF5Serializer.load(path)
        else:
            state = NpzSerializer.load(path)

        self._restore_state(sim, state)

    @staticmethod
    def list_checkpoints(directory: str) -> list:
        """指定ディレクトリ内のチェックポイントファイル一覧を返す（昇順）。"""
        if not os.path.isdir(directory):
            return []
        files = [
            os.path.join(directory, f)
            for f in sorted(os.listdir(directory))
            if f.startswith("step_") and (f.endswith(".h5") or f.endswith(".npz"))
        ]
        return files

    @staticmethod
    def latest_checkpoint(directory: str) -> Optional[str]:
        """最新チェックポイントファイルのパスを返す（存在しない場合は None）。"""
        files = CheckpointManager.list_checkpoints(directory)
        return files[-1] if files else None

    # ── 内部: 状態の収集・復元 ─────────────────────────────────────────────

    @staticmethod
    def _collect_state(sim: "TwoPhaseSimulation") -> dict:
        """シミュレーションから保存すべき状態を辞書として収集する。"""
        be = sim.backend

        state: dict = {
            "step": sim.step,
            "time": sim.time,
            "ndim": sim.config.grid.ndim,
            "N":    list(sim.config.grid.N),
            "L":    list(sim.config.grid.L),
            "psi":      np.asarray(be.to_host(sim.psi.data)),
            "pressure": np.asarray(be.to_host(sim.pressure.data)),
        }

        for ax in range(sim.config.grid.ndim):
            state[f"velocity_{ax}"] = np.asarray(be.to_host(sim.velocity[ax]))

        try:
            cfg_dict = dataclasses.asdict(sim.config)
            state["config_json"] = json.dumps(cfg_dict)
        except Exception:
            pass  # config のシリアライズに失敗しても保存を継続

        return state

    @staticmethod
    def _restore_state(sim: "TwoPhaseSimulation", state: dict) -> None:
        """辞書からシミュレーション状態を復元する。"""
        be = sim.backend

        sim.step = int(state["step"])
        sim.time = float(state["time"])

        sim.psi.data      = be.to_device(state["psi"])
        sim.pressure.data = be.to_device(state["pressure"])

        for ax in range(sim.config.grid.ndim):
            sim.velocity[ax] = be.to_device(state[f"velocity_{ax}"])

        # 復元後に材料特性と曲率を再計算
        sim._update_properties()
        sim._update_curvature()
