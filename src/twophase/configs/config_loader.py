"""
YAML 設定ファイルローダー。

YAML ファイルから SimulationConfig を構築する。
YAML は従来のフラット形式（後方互換）とネスト形式の両方に対応する。

フラット YAML 形式（推奨）::

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
from typing import Any, Dict, Tuple


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

    フラット YAML キーを適切なサブ設定（GridConfig, FluidConfig,
    NumericsConfig, SolverConfig）に振り分ける。

    Parameters
    ----------
    path : YAML ファイルのパス

    Returns
    -------
    config     : SimulationConfig
    output_cfg : 出力設定辞書
    """
    from ..config import (
        SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
    )

    raw = load_config_dict(path)

    # 出力設定を分離
    output_cfg = _default_output_config()
    if "output" in raw:
        output_cfg.update(raw.pop("output"))

    # タプル変換
    for key in ("N", "L"):
        if key in raw and isinstance(raw[key], list):
            raw[key] = tuple(raw[key])

    def _get(key, default):
        return raw.get(key, default)

    grid = GridConfig(
        ndim=_get("ndim", 2),
        N=_get("N", (64, 64)),
        L=_get("L", (1.0, 1.0)),
        alpha_grid=_get("alpha_grid", 1.0),
        dx_min_floor=_get("dx_min_floor", 1e-6),
        eps_g_factor=_get("eps_g_factor", 2.0),
    )
    fluid = FluidConfig(
        Re=_get("Re", 100.0),
        Fr=_get("Fr", 1.0),
        We=_get("We", 10.0),
        rho_ratio=_get("rho_ratio", 0.001),
        mu_ratio=_get("mu_ratio", 0.01),
    )
    numerics = NumericsConfig(
        epsilon_factor=_get("epsilon_factor", 1.5),
        reinit_steps=_get("reinit_steps", 4),
        cfl_number=_get("cfl_number", 0.3),
        t_end=_get("t_end", 1.0),
        cn_viscous=_get("cn_viscous", True),
        bc_type=_get("bc_type", "wall"),
        advection_scheme=_get("advection_scheme", "dissipative_ccd"),
    )
    solver = SolverConfig(
        ppe_solver_type=_get("ppe_solver_type", "bicgstab"),
        bicgstab_tol=_get("bicgstab_tol", 1e-10),
        bicgstab_maxiter=_get("bicgstab_maxiter", 1000),
        pseudo_tol=_get("pseudo_tol", 1e-8),
        pseudo_maxiter=_get("pseudo_maxiter", 500),
        pseudo_c_tau=_get("pseudo_c_tau", 2.0),
    )

    # 未知キーの警告
    _known = {
        "ndim", "N", "L", "alpha_grid", "dx_min_floor", "eps_g_factor",
        "Re", "Fr", "We", "rho_ratio", "mu_ratio",
        "epsilon_factor", "reinit_steps", "cfl_number", "t_end", "cn_viscous", "bc_type",
        "advection_scheme",
        "ppe_solver_type", "bicgstab_tol", "bicgstab_maxiter", "pseudo_tol", "pseudo_maxiter",
        "pseudo_c_tau",
        "use_gpu",
    }
    for key in raw:
        if key not in _known:
            import warnings
            warnings.warn(
                f"YAML に未知のキー '{key}' があります（無視します）。",
                UserWarning,
                stacklevel=2,
            )

    config = SimulationConfig(
        grid=grid,
        fluid=fluid,
        numerics=numerics,
        solver=solver,
        use_gpu=_get("use_gpu", False),
    )
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

    サブ設定のフィールドをフラット形式で出力し、load_config() と往復可能にする。

    Parameters
    ----------
    config : SimulationConfig
    path   : 保存先 YAML ファイルのパス
    """
    yaml = _require_pyyaml()

    d: Dict[str, Any] = {
        # GridConfig
        "ndim":         config.grid.ndim,
        "N":            list(config.grid.N),
        "L":            list(config.grid.L),
        "alpha_grid":   config.grid.alpha_grid,
        "dx_min_floor": config.grid.dx_min_floor,
        "eps_g_factor": config.grid.eps_g_factor,
        # FluidConfig
        "Re":        config.fluid.Re,
        "Fr":        config.fluid.Fr,
        "We":        config.fluid.We,
        "rho_ratio": config.fluid.rho_ratio,
        "mu_ratio":  config.fluid.mu_ratio,
        # NumericsConfig
        "epsilon_factor": config.numerics.epsilon_factor,
        "reinit_steps":   config.numerics.reinit_steps,
        "cfl_number":     config.numerics.cfl_number,
        "t_end":          config.numerics.t_end,
        "cn_viscous":       config.numerics.cn_viscous,
        "bc_type":          config.numerics.bc_type,
        "advection_scheme": config.numerics.advection_scheme,
        # SolverConfig
        "ppe_solver_type":  config.solver.ppe_solver_type,
        "bicgstab_tol":     config.solver.bicgstab_tol,
        "bicgstab_maxiter": config.solver.bicgstab_maxiter,
        "pseudo_tol":       config.solver.pseudo_tol,
        "pseudo_maxiter":   config.solver.pseudo_maxiter,
        "pseudo_c_tau":     config.solver.pseudo_c_tau,
        # ハードウェア
        "use_gpu": config.use_gpu,
    }

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(d, f, default_flow_style=False, allow_unicode=True)
