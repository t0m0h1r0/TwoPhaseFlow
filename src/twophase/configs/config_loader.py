"""
YAML 設定ファイルローダー。

YAML ファイルから SimulationConfig を構築する。
グリッド、物理パラメータ、ソルバー設定、出力設定など
すべてのパラメータを YAML から読み込める。

YAML ファイル形式::

    # グリッド
    ndim: 2
    N: [64, 64]
    L: [1.0, 1.0]

    # 無次元数
    Re: 100.0
    Fr: 1.0
    We: 10.0

    # 流体特性（比率 気体/液体）
    rho_ratio: 0.001
    mu_ratio: 0.01

    # 界面
    epsilon_factor: 1.5
    reinit_steps: 4

    # 時間積分
    cfl_number: 0.3
    t_end: 1.0

    # 圧力ソルバー
    ppe_solver_type: bicgstab
    bicgstab_tol: 1.0e-10
    bicgstab_maxiter: 1000

    # 境界条件
    bc_type: wall

    # ハードウェア
    use_gpu: false

    # 出力設定（main.py が使用）
    output:
      checkpoint_dir: checkpoints
      checkpoint_interval: 100
      visualization_interval: 50
      output_dir: results
      save_figures: true

使用例::

    from twophase.configs import load_config
    cfg, output_cfg = load_config("config.yaml")
"""

from __future__ import annotations
import os
from typing import Any, Dict, Optional, Tuple


def _require_pyyaml() -> Any:
    """PyYAML をインポートする。未インストールの場合は分かりやすいエラーを返す。"""
    try:
        import yaml
        return yaml
    except ImportError:
        raise ImportError(
            "PyYAML が見つかりません。pip install pyyaml でインストールしてください。"
        )


def load_config_dict(path: str) -> Dict[str, Any]:
    """YAML ファイルを辞書として読み込む。

    Parameters
    ----------
    path : YAML ファイルのパス

    Returns
    -------
    d : 読み込んだ辞書
    """
    yaml = _require_pyyaml()
    with open(path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    if d is None:
        d = {}
    return d


def load_config(
    path: str,
) -> Tuple["SimulationConfig", Dict[str, Any]]:
    """YAML ファイルから SimulationConfig と出力設定を読み込む。

    SimulationConfig のフィールドに対応するキーは直接 config に渡される。
    ``output`` キーは出力設定として別途返される。

    Parameters
    ----------
    path : YAML ファイルのパス

    Returns
    -------
    config     : SimulationConfig
    output_cfg : 出力設定辞書（キー: checkpoint_dir, checkpoint_interval,
                  visualization_interval, output_dir, save_figures）
    """
    from ..config import SimulationConfig
    import dataclasses

    raw = load_config_dict(path)

    # 出力設定を分離
    output_cfg = _default_output_config()
    if "output" in raw:
        output_cfg.update(raw.pop("output"))

    # SimulationConfig のフィールド名を取得
    valid_fields = {f.name for f in dataclasses.fields(SimulationConfig)}

    # タプル変換が必要なフィールド
    tuple_fields = {"N", "L"}

    kwargs: Dict[str, Any] = {}
    for key, val in raw.items():
        if key not in valid_fields:
            import warnings
            warnings.warn(
                f"YAML に未知のキー '{key}' があります（無視します）。",
                UserWarning,
                stacklevel=2,
            )
            continue

        if key in tuple_fields and isinstance(val, list):
            val = tuple(val)

        kwargs[key] = val

    config = SimulationConfig(**kwargs)
    return config, output_cfg


def _default_output_config() -> Dict[str, Any]:
    """デフォルトの出力設定辞書を返す。"""
    return {
        "checkpoint_dir":         "checkpoints",
        "checkpoint_interval":    100,
        "visualization_interval": 50,
        "output_dir":             "results",
        "save_figures":           True,
    }


def config_to_yaml(config: "SimulationConfig", path: str) -> None:
    """SimulationConfig を YAML ファイルに保存する（設定のエクスポート用）。

    Parameters
    ----------
    config : SimulationConfig
    path   : 保存先 YAML ファイルのパス
    """
    import dataclasses
    yaml = _require_pyyaml()

    d = dataclasses.asdict(config)
    # tuple を list に変換（YAML 的に自然な形式）
    for key in ("N", "L"):
        if key in d and isinstance(d[key], tuple):
            d[key] = list(d[key])

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(d, f, default_flow_style=False, allow_unicode=True)
