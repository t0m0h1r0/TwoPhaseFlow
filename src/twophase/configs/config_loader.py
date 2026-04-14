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
    ppe_solver_type: pseudotime
    pseudo_tol: 1.0e-8
    pseudo_maxiter: 500

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

    # 初期条件（オプション）
    initial_condition:
      background_phase: gas
      shapes:
        - type: circle
          center: [0.5, 0.5]
          radius: 0.25
          interior_phase: liquid

使用例::

    from twophase.configs import load_config
    cfg, output_cfg = load_config("config.yaml")
    cfg, output_cfg, ic_cfg = load_config("config.yaml")  # ic_cfg は None または dict
"""

from __future__ import annotations
import os
import warnings
from dataclasses import fields as _dc_fields
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
) -> Tuple["SimulationConfig", Dict[str, Any], Any, Any]:
    """YAML ファイルから SimulationConfig と出力設定・初期条件設定・速度場設定を読み込む。

    フラット YAML キーを適切なサブ設定（GridConfig, FluidConfig,
    NumericsConfig, SolverConfig）に振り分ける。

    Parameters
    ----------
    path : YAML ファイルのパス

    Returns
    -------
    config     : SimulationConfig
    output_cfg : 出力設定辞書
    ic_cfg     : 初期条件設定辞書（initial_condition キーがなければ None）
                 InitialConditionBuilder.from_dict(ic_cfg) で変換できる。
    vf_cfg     : 速度場設定辞書（velocity_field キーがなければ None）
                 velocity_field_from_dict(vf_cfg) で VelocityField に変換できる。
    """
    from ..config import (
        SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig,
    )

    raw = load_config_dict(path)
    output_cfg, ic_cfg, vf_cfg = _pop_side_sections(raw)
    _coerce_tuple_keys(raw, ("N", "L"))

    grid = _build_grid_config(raw, GridConfig)
    fluid = _build_fluid_config(raw, FluidConfig)
    numerics = _build_numerics_config(raw, NumericsConfig)
    solver = _build_solver_config(raw, SolverConfig)
    _warn_unknown_keys(raw, (GridConfig, FluidConfig, NumericsConfig, SolverConfig))

    config = SimulationConfig(
        grid=grid,
        fluid=fluid,
        numerics=numerics,
        solver=solver,
        use_gpu=raw.get("use_gpu", False),
    )
    return config, output_cfg, ic_cfg, vf_cfg


def _pop_side_sections(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], Any, Any]:
    """Remove non-SimulationConfig sections from the raw YAML dict."""
    output_cfg = _default_output_config()
    if "output" in raw:
        output_cfg.update(raw.pop("output"))
    ic_cfg = raw.pop("initial_condition", None)
    vf_cfg = raw.pop("velocity_field", None)
    return output_cfg, ic_cfg, vf_cfg


def _coerce_tuple_keys(raw: Dict[str, Any], keys: Tuple[str, ...]) -> None:
    """Convert YAML lists that map to tuple-valued config fields."""
    for key in keys:
        if key in raw and isinstance(raw[key], list):
            raw[key] = tuple(raw[key])


def _get_float(raw: Dict[str, Any], key: str, default: float) -> float:
    """Read a float, accepting YAML loaders that parse scientific notation as str."""
    return float(raw.get(key, default))


def _get_int(raw: Dict[str, Any], key: str, default: int) -> int:
    """Read an integer config value."""
    return int(raw.get(key, default))


def _build_grid_config(raw: Dict[str, Any], GridConfig):
    return GridConfig(
        ndim=_get_int(raw, "ndim", 2),
        N=raw.get("N", (64, 64)),
        L=raw.get("L", (1.0, 1.0)),
        alpha_grid=_get_float(raw, "alpha_grid", 1.0),
        dx_min_floor=_get_float(raw, "dx_min_floor", 1e-6),
        eps_g_factor=_get_float(raw, "eps_g_factor", 2.0),
    )


def _build_fluid_config(raw: Dict[str, Any], FluidConfig):
    return FluidConfig(
        Re=_get_float(raw, "Re", 100.0),
        Fr=_get_float(raw, "Fr", 1.0),
        We=_get_float(raw, "We", 10.0),
        rho_ratio=_get_float(raw, "rho_ratio", 0.001),
        mu_ratio=_get_float(raw, "mu_ratio", 0.01),
    )


def _build_numerics_config(raw: Dict[str, Any], NumericsConfig):
    return NumericsConfig(
        epsilon_factor=_get_float(raw, "epsilon_factor", 1.5),
        reinit_steps=_get_int(raw, "reinit_steps", 4),
        cfl_number=_get_float(raw, "cfl_number", 0.3),
        t_end=_get_float(raw, "t_end", 1.0),
        cn_viscous=bool(raw.get("cn_viscous", True)),
        cn_mode=str(raw.get("cn_mode", "picard")),
        bc_type=str(raw.get("bc_type", "wall")),
        advection_scheme=str(raw.get("advection_scheme", "dissipative_ccd")),
        surface_tension_model=str(raw.get("surface_tension_model", "csf")),
        extension_method=str(raw.get("extension_method", "hermite")),
        n_extend=_get_int(raw, "n_extend", 5),
    )


def _build_solver_config(raw: Dict[str, Any], SolverConfig):
    return SolverConfig(
        ppe_solver_type=str(raw.get("ppe_solver_type", "pseudotime")),
        pseudo_tol=_get_float(raw, "pseudo_tol", 1e-8),
        pseudo_maxiter=_get_int(raw, "pseudo_maxiter", 500),
        pseudo_c_tau=_get_float(raw, "pseudo_c_tau", 2.0),
        ppe_discretization=str(raw.get("ppe_discretization", "ccd")),
        ppe_iteration_method=str(raw.get("ppe_iteration_method", "adi")),
        iim_mode=str(raw.get("iim_mode", "hermite")),
        iim_backend=str(raw.get("iim_backend", "decomp")),
    )


def _warn_unknown_keys(raw: Dict[str, Any], config_types: Tuple[type, ...]) -> None:
    """Warn for keys not owned by any config dataclass."""
    known = set()
    for config_type in config_types:
        known |= {f.name for f in _dc_fields(config_type)}
    known |= {"use_gpu", "bicgstab_tol", "bicgstab_maxiter"}  # legacy keys

    for key in raw:
        if key not in known:
            warnings.warn(
                f"YAML に未知のキー '{key}' があります（無視します）。",
                UserWarning,
                stacklevel=2,
            )


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
    d = _config_to_flat_dict(config)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(d, f, default_flow_style=False, allow_unicode=True)


def _config_to_flat_dict(config: "SimulationConfig") -> Dict[str, Any]:
    """Flatten SimulationConfig into the legacy YAML key layout."""
    return {
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
        "epsilon_factor":        config.numerics.epsilon_factor,
        "reinit_steps":          config.numerics.reinit_steps,
        "cfl_number":            config.numerics.cfl_number,
        "t_end":                 config.numerics.t_end,
        "cn_viscous":            config.numerics.cn_viscous,
        "cn_mode":               config.numerics.cn_mode,
        "bc_type":               config.numerics.bc_type.value,
        "advection_scheme":      config.numerics.advection_scheme,
        "surface_tension_model": config.numerics.surface_tension_model,
        "extension_method":      config.numerics.extension_method,
        "n_extend":              config.numerics.n_extend,
        # SolverConfig
        "ppe_solver_type":       config.solver.ppe_solver_type,
        "pseudo_tol":            config.solver.pseudo_tol,
        "pseudo_maxiter":        config.solver.pseudo_maxiter,
        "pseudo_c_tau":          config.solver.pseudo_c_tau,
        "ppe_discretization":    config.solver.ppe_discretization,
        "ppe_iteration_method":  config.solver.ppe_iteration_method,
        "iim_mode":              config.solver.iim_mode,
        "iim_backend":           config.solver.iim_backend,
        # ハードウェア
        "use_gpu": config.use_gpu,
    }


# save_config は config_to_yaml の別名（テスト互換性のため）
save_config = config_to_yaml
