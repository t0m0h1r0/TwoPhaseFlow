"""
チェックポイントの形式別 I/O シリアライザ。

単一責務の原則 (SRP) に従い、HDF5 形式と NPZ 形式の
具体的なファイル I/O 処理を CheckpointManager から分離した。

各シリアライザは state 辞書の保存・読み込みのみを担当する。
チェックポイントの管理ロジック（ディレクトリ作成、ファイル命名、
シミュレーション状態の収集・復元）は CheckpointManager が担当する。

state 辞書のスキーマ:
    step        : int   — タイムステップ番号
    time        : float — 物理時刻
    ndim        : int   — 空間次元数
    N           : list  — グリッド点数
    L           : list  — ドメイン長さ
    psi         : array — レベルセット場
    pressure    : array — 圧力場
    velocity_0  : array — 速度成分 0
    velocity_1  : array — 速度成分 1
    velocity_2  : array — 速度成分 2（3次元の場合のみ）
    config_json : str   — SimulationConfig の JSON シリアライズ
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Any


class HDF5Serializer:
    """HDF5 形式でチェックポイントを保存・読み込みする。

    h5py が必要。保存時に gzip 圧縮 (level 4) を適用する。
    """

    @staticmethod
    def save(path: str, state: Dict[str, Any]) -> None:
        """HDF5 形式で state 辞書を保存する。

        Parameters
        ----------
        path  : 保存先ファイルパス（拡張子 .h5）
        state : 保存するデータ辞書
        """
        import h5py
        with h5py.File(path, "w") as f:
            # スカラー値とメタデータは属性として保存
            f.attrs["step"] = state["step"]
            f.attrs["time"] = state["time"]
            f.attrs["ndim"] = state["ndim"]
            if "config_json" in state:
                f.attrs["config_json"] = state["config_json"]

            f.create_dataset("N", data=np.array(state["N"]))
            f.create_dataset("L", data=np.array(state["L"]))

            # フィールドデータは gzip 圧縮付きデータセットとして保存
            for key in ("psi", "pressure"):
                f.create_dataset(
                    key, data=state[key],
                    compression="gzip", compression_opts=4,
                )

            ndim = state["ndim"]
            vel_grp = f.create_group("velocity")
            for ax in range(ndim):
                vel_grp.create_dataset(
                    str(ax), data=state[f"velocity_{ax}"],
                    compression="gzip", compression_opts=4,
                )

    @staticmethod
    def load(path: str) -> Dict[str, Any]:
        """HDF5 ファイルから state 辞書を読み込む。

        Parameters
        ----------
        path : 読み込むファイルパス（拡張子 .h5）

        Returns
        -------
        state : 復元されたデータ辞書
        """
        import h5py
        state: Dict[str, Any] = {}
        with h5py.File(path, "r") as f:
            state["step"] = int(f.attrs["step"])
            state["time"] = float(f.attrs["time"])
            state["ndim"] = int(f.attrs["ndim"])
            if "config_json" in f.attrs:
                state["config_json"] = str(f.attrs["config_json"])

            state["N"] = list(f["N"][:])
            state["L"] = list(f["L"][:])
            state["psi"]      = f["psi"][:]
            state["pressure"] = f["pressure"][:]

            for ax in range(state["ndim"]):
                state[f"velocity_{ax}"] = f["velocity"][str(ax)][:]

        return state


class NpzSerializer:
    """NumPy npz 形式でチェックポイントを保存・読み込みする。

    h5py が不要なフォールバック実装。savez_compressed で圧縮して保存する。
    """

    @staticmethod
    def save(path: str, state: Dict[str, Any]) -> None:
        """NumPy npz 形式で state 辞書を保存する。

        Parameters
        ----------
        path  : 保存先ファイルパス（拡張子 .npz）
        state : 保存するデータ辞書
        """
        # ndarray 以外の値を numpy 型に変換
        arrays: Dict[str, np.ndarray] = {}
        for key, val in state.items():
            if isinstance(val, np.ndarray):
                arrays[key] = val
            elif isinstance(val, (int, float)):
                arrays[key] = np.array(val)
            elif isinstance(val, list):
                arrays[key] = np.array(val)
            elif isinstance(val, str):
                arrays[key] = np.array(val)
        np.savez_compressed(path, **arrays)

    @staticmethod
    def load(path: str) -> Dict[str, Any]:
        """NumPy npz ファイルから state 辞書を読み込む。

        Parameters
        ----------
        path : 読み込むファイルパス（拡張子 .npz）

        Returns
        -------
        state : 復元されたデータ辞書
        """
        raw = np.load(path, allow_pickle=False)
        state: Dict[str, Any] = {}
        for key in raw.files:
            arr = raw[key]
            if arr.ndim == 0:
                # スカラーは Python ネイティブ型に変換
                val = arr.item()
                if key in ("step", "ndim"):
                    val = int(val)
                elif key == "time":
                    val = float(val)
                state[key] = val
            else:
                state[key] = arr

        # リスト型に変換
        if "N" in state:
            state["N"] = list(state["N"].astype(int))
        if "L" in state:
            state["L"] = list(state["L"].astype(float))

        return state
