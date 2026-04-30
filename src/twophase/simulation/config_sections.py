"""Grid and physics parsing helpers for experiment configs."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .config_models import GridCfg, PhysicsCfg


@dataclass(frozen=True)
class GridAxisDistribution:
    """Axis-local interface-fitting settings parsed from ``grid.distribution``."""

    enabled: bool
    method: str
    alpha_grid: float
    fitting_axes: tuple[bool, ...]
    fitting_alpha_grid: tuple[float, ...]
    eps_g_factor: float
    fitting_eps_g_factor: tuple[float, ...]
    eps_g_cells: float | None
    fitting_eps_g_cells: tuple[float | None, ...]
    dx_min_floor: float
    fitting_dx_min_floor: tuple[float, ...]


def parse_grid(d: dict, interface: dict) -> GridCfg:
    """Parse the grid section from experiment YAML."""
    cells = d["cells"]
    NX, NY = int(cells[0]), int(cells[1])
    domain = d["domain"]
    size = domain["size"]
    LX, LY = float(size[0]), float(size[1])
    distribution = d["distribution"]
    width = interface["thickness"]
    axis_distribution = parse_grid_axis_distribution(
        distribution,
        ndim=2,
        grid_dx_min_floor=float(d.get("dx_min_floor", 1e-6)),
    )
    eps_factor = float(width.get("base_factor", 1.5))
    eps_xi_cells = opt_float(width.get("xi_cells"))
    use_local_eps = parse_interface_width_mode(width, eps_xi_cells)
    return GridCfg(
        NX=NX,
        NY=NY,
        LX=LX,
        LY=LY,
        bc_type=str(domain["boundary"]),
        alpha_grid=axis_distribution.alpha_grid,
        fitting_axes=axis_distribution.fitting_axes,
        fitting_alpha_grid=axis_distribution.fitting_alpha_grid,
        eps_factor=eps_factor,
        eps_g_factor=axis_distribution.eps_g_factor,
        fitting_eps_g_factor=axis_distribution.fitting_eps_g_factor,
        eps_g_cells=axis_distribution.eps_g_cells,
        fitting_eps_g_cells=axis_distribution.fitting_eps_g_cells,
        dx_min_floor=axis_distribution.dx_min_floor,
        fitting_dx_min_floor=axis_distribution.fitting_dx_min_floor,
        use_local_eps=use_local_eps,
        eps_xi_cells=eps_xi_cells,
        grid_rebuild_freq=parse_grid_rebuild(distribution.get("schedule", "static")),
        interface_fitting_enabled=axis_distribution.enabled,
        interface_fitting_method=axis_distribution.method,
    )


def parse_physics(d: dict) -> PhysicsCfg:
    """Parse the physics section, resolving derived parameters."""
    phases = d["phases"]
    liquid = phases["liquid"]
    gas = phases["gas"]
    rho_l = float(liquid["rho"])
    rho_g = float(gas["rho"])
    g_acc = float(d.get("gravity", 0.0))
    rho_ref = opt_float(d.get("rho_ref"))
    d_ref = opt_float(d.get("d_ref"))

    mu_raw, mu_l_raw, mu_g_raw = resolve_viscosity(d, rho_l, g_acc, d_ref)
    sigma_raw = resolve_surface_tension(d, rho_l, rho_g, g_acc, d_ref, mu_g_raw)

    return PhysicsCfg(
        rho_l=rho_l,
        rho_g=rho_g,
        sigma=sigma_raw,
        mu=mu_raw,
        mu_l=mu_l_raw,
        mu_g=mu_g_raw,
        g_acc=g_acc,
        rho_ref=rho_ref,
    )


def resolve_viscosity(
    d: dict,
    rho_l: float,
    g_acc: float,
    d_ref: float | None,
) -> tuple[float, float | None, float | None]:
    """Resolve uniform and phase viscosities from direct or derived inputs."""
    phases = d["phases"]
    liquid = phases["liquid"]
    gas = phases["gas"]
    mu_g = opt_float(gas["mu"])
    mu_l = opt_float(liquid["mu"])
    mu = opt_float(d.get("mu"))

    lambda_mu = opt_float(d.get("lambda_mu"))
    if lambda_mu is not None and mu_g is not None:
        mu_l = lambda_mu * mu_g

    re_num = opt_float(d.get("Re"))
    if re_num is not None and d_ref is not None and g_acc > 0.0:
        mu_derived = rho_l * math.sqrt(g_acc * d_ref) * d_ref / re_num
        if mu is None:
            mu = mu_derived
        if mu_g is None:
            mu_g = mu_derived
        if mu_l is None:
            mu_l = mu_derived

    if mu is None:
        if mu_g is not None:
            mu = mu_g
        elif mu_l is not None:
            mu = mu_l
        else:
            mu = 0.01

    if mu_g is None and mu_l is None:
        return mu, mu, mu
    if mu_g is None:
        mu_g = mu
    if mu_l is None:
        mu_l = mu
    return mu, mu_l, mu_g


def resolve_surface_tension(
    d: dict,
    rho_l: float,
    rho_g: float,
    g_acc: float,
    d_ref: float | None,
    mu_g: float | None,
) -> float:
    """Resolve surface tension from direct sigma, Eotvos number, or Ca."""
    sigma = opt_float(d.get("surface_tension"))

    eo_num = opt_float(d.get("Eo"))
    if eo_num is not None and d_ref is not None and g_acc > 0.0:
        sigma = g_acc * (rho_l - rho_g) * d_ref ** 2 / eo_num

    ca_num = opt_float(d.get("Ca"))
    r_ref = opt_float(d.get("R_ref")) or (d_ref / 2.0 if d_ref else None)
    gamma_dot = opt_float(d.get("gamma_dot"))
    if (
        ca_num is not None
        and mu_g is not None
        and gamma_dot is not None
        and r_ref is not None
    ):
        sigma = mu_g * gamma_dot * r_ref / ca_num

    return 0.0 if sigma is None else sigma


def opt_float(val: Any) -> float | None:
    if val is None:
        return None
    return float(val)


def validate_choice(raw: Any, choices: tuple[str, ...], path: str) -> str:
    value = str(raw).strip().lower()
    if value not in choices:
        raise ValueError(f"{path} must be one of {choices}, got {value!r}")
    return value


def parse_interface_width_mode(
    width: dict,
    eps_xi_cells: float | None,
) -> bool:
    """Resolve canonical interface-width mode to the internal local-eps boolean."""
    mode = str(width["mode"]).strip().lower()
    if mode == "nominal":
        return False
    if mode == "local":
        return True
    if mode == "xi_cells":
        if eps_xi_cells is None:
            raise ValueError("interface.thickness.mode='xi_cells' requires xi_cells")
        return True
    raise ValueError(
        "interface.thickness.mode must be nominal|local|xi_cells, "
        f"got {mode!r}"
    )


def parse_grid_rebuild(raw: Any) -> int:
    """Resolve interface-fitting rebuild schedule to the internal frequency."""
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in {"static", "initial", "initial_only", "never", "off"}:
            return 0
        if value in {"every_step", "dynamic", "each_step"}:
            return 1
        if value.startswith("every_"):
            return int(value.removeprefix("every_"))
    freq = int(raw)
    if freq < 0:
        raise ValueError(f"grid.distribution.schedule must be >= 0, got {freq}")
    return freq


_AXIS_ALIASES = {
    "x": 0,
    "xi": 0,
    "0": 0,
    0: 0,
    "y": 1,
    "eta": 1,
    "1": 1,
    1: 1,
    "z": 2,
    "zeta": 2,
    "2": 2,
    2: 2,
}


def parse_grid_axis_distribution(
    distribution: dict,
    *,
    ndim: int,
    grid_dx_min_floor: float,
) -> GridAxisDistribution:
    """Parse global or axis-local interface-fitted grid settings."""
    axes_raw = distribution.get("axes")
    has_axis_map = isinstance(axes_raw, dict)
    distribution_type = validate_choice(
        distribution.get("type", "axis_mixed" if has_axis_map else "uniform"),
        ("uniform", "interface_fitted", "axis_mixed"),
        "grid.distribution.type",
    )
    default_enabled = distribution_type in {"interface_fitted", "axis_mixed"}
    default_method = normalize_interface_fitting_method(
        distribution.get(
            "method",
            "gaussian_levelset" if default_enabled else "none",
        )
    )
    if default_method == "none":
        default_enabled = False
    default_alpha = float(distribution.get("alpha", 1.0))
    default_eps_factor = float(distribution.get("eps_g_factor", 2.0))
    default_eps_cells = opt_float(distribution.get("eps_g_cells"))
    default_dx_floor = float(distribution.get("dx_min_floor", grid_dx_min_floor))

    if has_axis_map:
        parsed = parse_axis_map_distribution(
            axes_raw,
            ndim=ndim,
            default_enabled=default_enabled,
            default_method=default_method,
            default_alpha=default_alpha,
            default_eps_factor=default_eps_factor,
            default_eps_cells=default_eps_cells,
            default_dx_floor=default_dx_floor,
        )
    else:
        fitting_axes = parse_grid_fitting_axes(
            axes_raw,
            fitting_enabled=default_enabled,
            ndim=ndim,
        )
        parsed = {
            "fitting_axes": fitting_axes,
            "methods": tuple(
                default_method if enabled else "none" for enabled in fitting_axes
            ),
            "fitting_alpha_grid": tuple(
                default_alpha if enabled else 1.0 for enabled in fitting_axes
            ),
            "fitting_eps_g_factor": tuple(
                default_eps_factor for _axis in range(ndim)
            ),
            "fitting_eps_g_cells": tuple(default_eps_cells for _axis in range(ndim)),
            "fitting_dx_min_floor": tuple(default_dx_floor for _axis in range(ndim)),
        }

    active_methods = {
        method
        for enabled, method in zip(parsed["fitting_axes"], parsed["methods"])
        if enabled
    }
    enabled = any(parsed["fitting_axes"])
    method = "none" if not enabled else (
        next(iter(active_methods)) if len(active_methods) == 1 else "axis_mixed"
    )
    alpha_grid = max(parsed["fitting_alpha_grid"]) if enabled else 1.0
    eps_g_cells_values = {
        value for value in parsed["fitting_eps_g_cells"] if value is not None
    }
    eps_g_cells = (
        next(iter(eps_g_cells_values)) if len(eps_g_cells_values) == 1 else None
    )
    return GridAxisDistribution(
        enabled=enabled,
        method=method,
        alpha_grid=alpha_grid,
        fitting_axes=parsed["fitting_axes"],
        fitting_alpha_grid=parsed["fitting_alpha_grid"],
        eps_g_factor=default_eps_factor,
        fitting_eps_g_factor=parsed["fitting_eps_g_factor"],
        eps_g_cells=eps_g_cells,
        fitting_eps_g_cells=parsed["fitting_eps_g_cells"],
        dx_min_floor=default_dx_floor,
        fitting_dx_min_floor=parsed["fitting_dx_min_floor"],
    )


def parse_axis_map_distribution(
    axes_raw: dict,
    *,
    ndim: int,
    default_enabled: bool,
    default_method: str,
    default_alpha: float,
    default_eps_factor: float,
    default_eps_cells: float | None,
    default_dx_floor: float,
) -> dict:
    """Parse ``grid.distribution.axes`` when it is an axis-name mapping."""
    fitting_axes = [False] * ndim
    methods = ["none"] * ndim
    fitting_alpha = [1.0] * ndim
    fitting_eps_factor = [default_eps_factor] * ndim
    fitting_eps_cells = [default_eps_cells] * ndim
    fitting_dx_floor = [default_dx_floor] * ndim
    for raw_axis, raw_spec in axes_raw.items():
        axis = parse_grid_axis_key(raw_axis, ndim, "grid.distribution.axes")
        spec = normalize_axis_distribution_spec(raw_spec)
        axis_type = validate_choice(
            spec.get("type", "interface_fitted" if default_enabled else "uniform"),
            ("uniform", "interface_fitted"),
            f"grid.distribution.axes.{raw_axis}.type",
        )
        method = normalize_interface_fitting_method(
            spec.get(
                "method",
                default_method if axis_type == "interface_fitted" else "none",
            )
        )
        if axis_type == "interface_fitted" and method != "none":
            fitting_axes[axis] = True
            methods[axis] = method
            fitting_alpha[axis] = float(spec.get("alpha", default_alpha))
            fitting_eps_factor[axis] = float(
                spec.get("eps_g_factor", default_eps_factor)
            )
            fitting_eps_cells[axis] = opt_float(
                spec.get("eps_g_cells", default_eps_cells)
            )
            fitting_dx_floor[axis] = float(
                spec.get("dx_min_floor", default_dx_floor)
            )
    return {
        "fitting_axes": tuple(fitting_axes),
        "methods": tuple(methods),
        "fitting_alpha_grid": tuple(fitting_alpha),
        "fitting_eps_g_factor": tuple(fitting_eps_factor),
        "fitting_eps_g_cells": tuple(fitting_eps_cells),
        "fitting_dx_min_floor": tuple(fitting_dx_floor),
    }


def normalize_axis_distribution_spec(raw: Any) -> dict:
    """Normalize one axis entry under ``grid.distribution.axes``."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        return {"type": raw}
    if not isinstance(raw, dict):
        raise ValueError(
            "grid.distribution.axes entries must be mappings or uniform/interface_fitted"
        )
    return raw


def parse_grid_axis_key(raw: Any, ndim: int, context: str) -> int:
    """Parse one grid axis key into a zero-based axis index."""
    if isinstance(raw, bool):
        raise ValueError(f"{context} must not contain bool axis keys")
    key = raw if isinstance(raw, int) else str(raw).strip().lower()
    if key not in _AXIS_ALIASES or _AXIS_ALIASES[key] >= ndim:
        raise ValueError(
            f"{context} entries must be drawn from x|y|z|0|1|2|all, got {raw!r}"
        )
    return _AXIS_ALIASES[key]


def parse_grid_fitting_axes(
    raw: Any,
    *,
    fitting_enabled: bool,
    ndim: int,
) -> tuple[bool, ...]:
    """Parse ``grid.distribution.axes`` into an active-axis mask."""
    if not fitting_enabled:
        return tuple(False for _axis in range(ndim))
    if raw is None:
        return tuple(True for _axis in range(ndim))
    if isinstance(raw, bool):
        raise ValueError("grid.distribution.axes must be an axis name/list, not bool")
    raw_items = [raw] if isinstance(raw, (str, int)) else list(raw)
    if any(str(item).strip().lower() == "all" for item in raw_items):
        return tuple(True for _axis in range(ndim))
    active = [False] * ndim
    for item in raw_items:
        active[parse_grid_axis_key(item, ndim, "grid.distribution.axes")] = True
    if not any(active):
        raise ValueError("grid.distribution.axes must enable at least one axis")
    return tuple(active)


def normalize_interface_fitting_method(raw: Any) -> str:
    """Validate the canonical interface-fitting method name."""
    method = str(raw).strip().lower()
    if method not in {"gaussian_levelset", "none"}:
        raise ValueError(
            "grid.distribution.method must be gaussian_levelset|none, "
            f"got {method!r}"
        )
    return method
