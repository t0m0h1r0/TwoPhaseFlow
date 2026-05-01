"""Grid and physics parsing helpers for experiment configs."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..core.boundary import canonical_bc_type
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
    wall_refinement_enabled: bool
    wall_refinement_axes: tuple[bool, ...]
    wall_alpha_grid: tuple[float, ...]
    wall_eps_g_factor: float
    wall_eps_g_factor_axes: tuple[float, ...]
    wall_eps_g_cells: tuple[float | None, ...]
    wall_sides: tuple[tuple[str, ...], ...]
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
    bc_type, boundary_sides = parse_grid_boundary(domain["boundary"], ndim=2)
    width = interface["thickness"]
    axis_distribution = parse_grid_axis_distribution(
        distribution,
        ndim=2,
        grid_dx_min_floor=float(d.get("dx_min_floor", 1e-6)),
        bc_type=bc_type,
        boundary_sides=boundary_sides,
    )
    eps_factor = float(width.get("base_factor", 1.5))
    eps_xi_cells = opt_float(width.get("xi_cells"))
    use_local_eps = parse_interface_width_mode(width, eps_xi_cells)
    return GridCfg(
        NX=NX,
        NY=NY,
        LX=LX,
        LY=LY,
        bc_type=bc_type,
        alpha_grid=axis_distribution.alpha_grid,
        fitting_axes=axis_distribution.fitting_axes,
        fitting_alpha_grid=axis_distribution.fitting_alpha_grid,
        eps_factor=eps_factor,
        eps_g_factor=axis_distribution.eps_g_factor,
        fitting_eps_g_factor=axis_distribution.fitting_eps_g_factor,
        eps_g_cells=axis_distribution.eps_g_cells,
        fitting_eps_g_cells=axis_distribution.fitting_eps_g_cells,
        wall_refinement_axes=axis_distribution.wall_refinement_axes,
        wall_alpha_grid=axis_distribution.wall_alpha_grid,
        wall_eps_g_factor=axis_distribution.wall_eps_g_factor,
        wall_eps_g_factor_axes=axis_distribution.wall_eps_g_factor_axes,
        wall_eps_g_cells=axis_distribution.wall_eps_g_cells,
        wall_sides=axis_distribution.wall_sides,
        dx_min_floor=axis_distribution.dx_min_floor,
        fitting_dx_min_floor=axis_distribution.fitting_dx_min_floor,
        use_local_eps=use_local_eps,
        eps_xi_cells=eps_xi_cells,
        grid_rebuild_freq=parse_grid_rebuild(distribution.get("schedule", 0)),
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
    """Resolve grid rebuild schedule to an interval.

    ``0`` means initial construction only; positive integers mean rebuild every
    N physical steps. Legacy string aliases are retained for old YAMLs.
    """
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


def parse_grid_boundary(raw: Any, *, ndim: int) -> tuple[str, tuple[tuple[str, ...], ...]]:
    """Parse global or axis-local domain boundary declarations."""
    if isinstance(raw, str):
        value = validate_choice(
            raw,
            ("wall", "periodic"),
            "grid.domain.boundary",
        )
        axes = tuple(value for _axis in range(ndim))
        sides = tuple(
            ("lower", "upper") if value == "wall" else ()
            for _axis in range(ndim)
        )
        return canonical_bc_type(axes), sides
    if not isinstance(raw, dict):
        raise ValueError("grid.domain.boundary must be wall|periodic or an axis map")

    axis_values: list[str | None] = [None] * ndim
    side_values: list[tuple[str, ...] | None] = [None] * ndim
    for raw_axis, raw_spec in raw.items():
        axis = parse_grid_axis_key(raw_axis, ndim, "grid.domain.boundary")
        if axis_values[axis] is not None:
            raise ValueError(
                f"grid.domain.boundary has duplicate declarations for axis {raw_axis!r}"
            )
        axis_type, sides = parse_grid_axis_boundary_spec(
            raw_spec,
            context=f"grid.domain.boundary.{raw_axis}",
        )
        axis_values[axis] = axis_type
        side_values[axis] = sides
    missing = [
        axis_name
        for axis_name, value in zip(("x", "y", "z"), axis_values)
        if value is None
    ]
    if missing:
        raise ValueError(f"grid.domain.boundary axis map must define {missing!r}")
    axes = tuple(str(value) for value in axis_values)
    return canonical_bc_type(axes), tuple(tuple(sides or ()) for sides in side_values)


def parse_grid_axis_boundary_spec(raw: Any, *, context: str) -> tuple[str, tuple[str, ...]]:
    """Parse one axis boundary declaration."""
    if isinstance(raw, str):
        value = validate_choice(raw, ("wall", "periodic"), context)
        return value, ("lower", "upper") if value == "wall" else ()
    if not isinstance(raw, dict):
        raise ValueError(f"{context} must be wall|periodic or lower/upper map")
    unexpected = sorted(set(raw) - {"lower", "upper"})
    if unexpected:
        raise ValueError(f"{context} supports only lower and upper, got {unexpected!r}")
    if set(raw) != {"lower", "upper"}:
        raise ValueError(f"{context} must define both lower and upper")
    lower = validate_choice(raw["lower"], ("wall", "periodic"), f"{context}.lower")
    upper = validate_choice(raw["upper"], ("wall", "periodic"), f"{context}.upper")
    if lower != upper:
        raise ValueError(
            f"{context} lower/upper mixed boundary is not supported; got {lower}/{upper}"
        )
    return lower, ("lower", "upper") if lower == "wall" else ()


def parse_grid_axis_distribution(
    distribution: dict,
    *,
    ndim: int,
    grid_dx_min_floor: float,
    bc_type: str,
    boundary_sides: tuple[tuple[str, ...], ...] | None = None,
) -> GridAxisDistribution:
    """Parse global or axis-local interface-fitted grid settings."""
    axes_raw = distribution.get("axes")
    has_axis_map = isinstance(axes_raw, dict)
    if has_axis_map:
        unexpected = sorted(set(distribution) - {"axes", "schedule"})
        if unexpected:
            raise ValueError(
                "grid.distribution with axis maps accepts only axes and schedule; "
                f"move {unexpected!r} under grid.distribution.axes.<axis>.monitors"
            )
        parsed = parse_axis_monitor_distribution(
            axes_raw,
            ndim=ndim,
            default_eps_factor=2.0,
            default_dx_floor=grid_dx_min_floor,
            bc_type=bc_type,
            boundary_sides=boundary_sides,
        )
        default_eps_factor = 2.0
        default_dx_floor = grid_dx_min_floor
        wall_defaults = {"eps_g_factor": 2.0}
    else:
        if "monitors" in distribution:
            raise ValueError(
                "grid.distribution.monitors is axis-local; use "
                "grid.distribution.axes.<axis>.monitors"
            )
        if "wall" in distribution:
            raise ValueError(
                "grid.distribution.wall is not supported; wall refinement belongs "
                "to grid.distribution.axes.<axis>.monitors.wall and is validated "
                "against grid.domain.boundary"
            )
        distribution_type = validate_choice(
            distribution.get("type", "uniform"),
            ("uniform", "interface_fitted"),
            "grid.distribution.type",
        )
        default_enabled = distribution_type == "interface_fitted"
        default_method = normalize_interface_fitting_method(
            distribution.get(
                "method",
                "gaussian_levelset" if default_enabled else "none",
            ),
            path="grid.distribution.method",
        )
        if default_method == "none":
            default_enabled = False
        default_alpha = float(distribution.get("alpha", 1.0))
        default_eps_factor = float(distribution.get("eps_g_factor", 2.0))
        default_eps_cells = opt_float(distribution.get("eps_g_cells"))
        default_dx_floor = float(distribution.get("dx_min_floor", grid_dx_min_floor))
        wall_defaults = parse_wall_refinement_defaults(
            None,
            ndim=ndim,
            bc_type=bc_type,
            default_eps_factor=default_eps_factor,
            nonuniform_enabled=default_enabled,
        )
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
            "wall_refinement_axes": tuple(False for _axis in range(ndim)),
            "wall_alpha_grid": tuple(1.0 for _axis in range(ndim)),
            "wall_eps_g_factor_axes": tuple(default_eps_factor for _axis in range(ndim)),
            "wall_eps_g_cells": tuple(None for _axis in range(ndim)),
            "wall_sides": tuple(("lower", "upper") for _axis in range(ndim)),
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
    wall_enabled = any(parsed["wall_refinement_axes"])
    alpha_grid = max(
        alpha_grid,
        max(
            (
                alpha if wall_axis else 1.0
                for wall_axis, alpha in zip(
                    parsed["wall_refinement_axes"],
                    parsed["wall_alpha_grid"],
                )
            ),
            default=1.0,
        ),
    )
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
        wall_refinement_enabled=wall_enabled,
        wall_refinement_axes=parsed["wall_refinement_axes"],
        wall_alpha_grid=parsed["wall_alpha_grid"],
        wall_eps_g_factor=wall_defaults["eps_g_factor"],
        wall_eps_g_factor_axes=parsed["wall_eps_g_factor_axes"],
        wall_eps_g_cells=parsed["wall_eps_g_cells"],
        wall_sides=parsed["wall_sides"],
        dx_min_floor=default_dx_floor,
        fitting_dx_min_floor=parsed["fitting_dx_min_floor"],
    )


def parse_axis_monitor_distribution(
    axes_raw: dict,
    *,
    ndim: int,
    default_eps_factor: float,
    default_dx_floor: float,
    bc_type: str,
    boundary_sides: tuple[tuple[str, ...], ...] | None = None,
) -> dict:
    """Parse the canonical monitor-based ``grid.distribution.axes`` schema."""
    fitting_axes = [False] * ndim
    methods = ["none"] * ndim
    fitting_alpha = [1.0] * ndim
    fitting_eps_factor = [default_eps_factor] * ndim
    fitting_eps_cells = [None] * ndim
    fitting_dx_floor = [default_dx_floor] * ndim
    wall_axes = [False] * ndim
    wall_alpha = [1.0] * ndim
    wall_eps_factor = [default_eps_factor] * ndim
    wall_eps_cells = [None] * ndim
    wall_sides = [("lower", "upper")] * ndim
    wall_sides_by_axis = (
        boundary_sides
        if boundary_sides is not None
        else tuple(
            ("lower", "upper")
            if str(bc_type).strip().lower() == "wall"
            else ()
            for _axis in range(ndim)
        )
    )

    for raw_axis, raw_spec in axes_raw.items():
        axis = parse_grid_axis_key(raw_axis, ndim, "grid.distribution.axes")
        context = f"grid.distribution.axes.{raw_axis}"
        spec = normalize_axis_monitor_distribution_spec(raw_spec, context=context)
        unexpected = sorted(set(spec) - {"type", "monitors", "dx_min_floor"})
        if unexpected:
            raise ValueError(
                f"{context} accepts only type, monitors, and dx_min_floor; "
                f"got {unexpected!r}"
            )
        axis_type = validate_choice(
            spec.get("type", "nonuniform" if "monitors" in spec else "uniform"),
            ("uniform", "nonuniform"),
            f"{context}.type",
        )
        if axis_type == "uniform":
            if "monitors" in spec:
                raise ValueError(f"{context}.monitors is invalid for type=uniform")
            if "dx_min_floor" in spec:
                raise ValueError(f"{context}.dx_min_floor is invalid for type=uniform")
            continue

        monitors = spec.get("monitors")
        if not isinstance(monitors, dict) or not monitors:
            raise ValueError(
                f"{context}.monitors must declare interface and/or wall for type=nonuniform"
            )
        unexpected_monitors = sorted(set(monitors) - {"interface", "wall"})
        if unexpected_monitors:
            raise ValueError(
                f"{context}.monitors supports only interface and wall; "
                f"got {unexpected_monitors!r}"
            )
        fitting_dx_floor[axis] = float(spec.get("dx_min_floor", default_dx_floor))

        if "interface" in monitors:
            interface_spec = normalize_monitor_spec(
                monitors["interface"],
                context=f"{context}.monitors.interface",
            )
            unexpected_interface = sorted(
                set(interface_spec) - {"alpha", "method", "eps_g_factor", "eps_g_cells"}
            )
            if unexpected_interface:
                raise ValueError(
                    f"{context}.monitors.interface accepts only alpha, method, "
                    f"eps_g_factor, and eps_g_cells; got {unexpected_interface!r}"
                )
            method = normalize_interface_fitting_method(
                interface_spec.get("method", "gaussian_levelset"),
                path=f"{context}.monitors.interface.method",
            )
            if method == "none":
                raise ValueError(f"{context}.monitors.interface.method must not be none")
            fitting_axes[axis] = True
            methods[axis] = method
            fitting_alpha[axis] = parse_monitor_alpha(
                interface_spec,
                context=f"{context}.monitors.interface",
            )
            fitting_eps_factor[axis] = float(
                interface_spec.get("eps_g_factor", default_eps_factor)
            )
            fitting_eps_cells[axis] = opt_float(interface_spec.get("eps_g_cells"))

        if "wall" in monitors:
            wall_spec = normalize_monitor_spec(
                monitors["wall"],
                context=f"{context}.monitors.wall",
            )
            unexpected_wall = sorted(
                set(wall_spec) - {"alpha", "eps_g_factor", "eps_g_cells", "apply_to"}
            )
            if unexpected_wall:
                raise ValueError(
                    f"{context}.monitors.wall accepts only alpha, eps_g_factor, "
                    f"eps_g_cells, and apply_to; got {unexpected_wall!r}"
                )
            if not wall_sides_by_axis[axis]:
                raise ValueError(
                    f"{context}.monitors.wall requires wall boundary on axis {raw_axis}"
                )
            wall_axes[axis] = True
            wall_alpha[axis] = parse_monitor_alpha(
                wall_spec,
                context=f"{context}.monitors.wall",
            )
            wall_eps_factor[axis] = float(
                wall_spec.get("eps_g_factor", default_eps_factor)
            )
            wall_eps_cells[axis] = opt_float(wall_spec.get("eps_g_cells"))
            wall_sides[axis] = parse_wall_monitor_apply_to(
                wall_spec.get("apply_to"),
                allowed=wall_sides_by_axis[axis],
                context=f"{context}.monitors.wall",
            )

        if not fitting_axes[axis] and not wall_axes[axis]:
            raise ValueError(
                f"{context} type=nonuniform must activate at least one monitor"
            )

    return {
        "fitting_axes": tuple(fitting_axes),
        "methods": tuple(methods),
        "fitting_alpha_grid": tuple(fitting_alpha),
        "fitting_eps_g_factor": tuple(fitting_eps_factor),
        "fitting_eps_g_cells": tuple(fitting_eps_cells),
        "fitting_dx_min_floor": tuple(fitting_dx_floor),
        "wall_refinement_axes": tuple(wall_axes),
        "wall_alpha_grid": tuple(wall_alpha),
        "wall_eps_g_factor_axes": tuple(wall_eps_factor),
        "wall_eps_g_cells": tuple(wall_eps_cells),
        "wall_sides": tuple(wall_sides),
    }


def normalize_axis_monitor_distribution_spec(raw: Any, *, context: str) -> dict:
    """Normalize one canonical axis-distribution entry."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        return {"type": raw}
    if not isinstance(raw, dict):
        raise ValueError(f"{context} must be a mapping or uniform/nonuniform")
    return raw


def normalize_monitor_spec(raw: Any, *, context: str) -> dict:
    """Normalize one active monitor spec."""
    if not isinstance(raw, dict):
        raise ValueError(f"{context} must be a mapping with alpha")
    return raw


def parse_monitor_alpha(spec: dict, *, context: str) -> float:
    """Parse the density multiplier for one active monitor."""
    if "alpha" not in spec:
        raise ValueError(f"{context}.alpha is required")
    alpha = float(spec["alpha"])
    if alpha <= 1.0:
        raise ValueError(f"{context}.alpha must be > 1.0, got {alpha}")
    return alpha


def parse_wall_monitor_apply_to(
    raw: Any,
    *,
    allowed: tuple[str, ...],
    context: str,
) -> tuple[str, ...]:
    """Parse an optional wall-monitor side filter against physical wall sides."""
    selected = allowed if raw is None else parse_wall_sides(raw, context=context)
    if not selected:
        raise ValueError(f"{context}.apply_to must select at least one wall side")
    invalid = [side for side in selected if side not in allowed]
    if invalid:
        raise ValueError(
            f"{context}.apply_to must select existing wall sides {allowed!r}, "
            f"got {invalid!r}"
        )
    return selected


def parse_wall_refinement_defaults(
    raw: Any,
    *,
    ndim: int,
    bc_type: str,
    default_eps_factor: float,
    nonuniform_enabled: bool,
    context: str = "grid.distribution.wall",
) -> dict:
    """Parse a wall-refinement block into axis-default values."""
    if raw is None:
        return {
            "enabled": False,
            "alpha": 1.0,
            "eps_g_factor": default_eps_factor,
            "eps_g_cells": None,
            "sides": ("lower", "upper"),
        }
    if isinstance(raw, bool):
        spec = {"enabled": raw}
    elif isinstance(raw, str):
        spec = {"enabled": raw}
    elif isinstance(raw, dict):
        spec = raw
    else:
        raise ValueError(f"{context} must be a mapping, bool, or auto/enabled string")

    enabled = parse_wall_refinement_enabled(
        spec.get("enabled", "auto"),
        bc_type=bc_type,
        nonuniform_enabled=nonuniform_enabled,
        context=f"{context}.enabled",
    )
    combine = str(spec.get("combine", "additive")).strip().lower()
    if combine != "additive":
        raise ValueError(f"{context}.combine must be 'additive', got {combine!r}")
    sides = parse_wall_sides(spec.get("sides", ("lower", "upper")), context=context)
    if not sides:
        enabled = False
    return {
        "enabled": enabled,
        "alpha": float(spec.get("alpha", 1.0)) if enabled else 1.0,
        "eps_g_factor": float(spec.get("eps_g_factor", default_eps_factor)),
        "eps_g_cells": opt_float(spec.get("eps_g_cells")),
        "sides": sides,
    }


def parse_wall_refinement_enabled(
    raw: Any,
    *,
    bc_type: str,
    nonuniform_enabled: bool,
    context: str,
) -> bool:
    """Resolve wall-refinement enabled/auto with mandatory periodic exclusion."""
    if isinstance(raw, bool):
        requested = raw
    else:
        value = str(raw).strip().lower()
        if value == "auto":
            requested = True
        elif value in {"true", "yes", "on", "enabled"}:
            requested = True
        elif value in {"false", "no", "off", "disabled", "none"}:
            requested = False
        else:
            raise ValueError(f"{context} must be auto|true|false, got {raw!r}")
    return (
        requested
        and nonuniform_enabled
        and str(bc_type).strip().lower() == "wall"
    )


def parse_wall_sides(raw: Any, *, context: str) -> tuple[str, ...]:
    """Parse wall sides as a subset of lower/upper."""
    if raw is None:
        return ("lower", "upper")
    raw_items = [raw] if isinstance(raw, str) else list(raw)
    if any(str(item).strip().lower() == "all" for item in raw_items):
        return ("lower", "upper")
    sides = tuple(str(item).strip().lower() for item in raw_items)
    invalid = [side for side in sides if side not in {"lower", "upper"}]
    if invalid:
        raise ValueError(f"{context}.sides must contain lower|upper|all, got {invalid!r}")
    return sides


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
    wall_defaults: dict,
    bc_type: str,
) -> dict:
    """Parse ``grid.distribution.axes`` when it is an axis-name mapping."""
    fitting_axes = [False] * ndim
    methods = ["none"] * ndim
    fitting_alpha = [1.0] * ndim
    fitting_eps_factor = [default_eps_factor] * ndim
    fitting_eps_cells = [default_eps_cells] * ndim
    fitting_dx_floor = [default_dx_floor] * ndim
    wall_axes = [False] * ndim
    wall_alpha = [wall_defaults["alpha"]] * ndim
    wall_eps_factor = [wall_defaults["eps_g_factor"]] * ndim
    wall_eps_cells = [wall_defaults["eps_g_cells"]] * ndim
    wall_sides = [wall_defaults["sides"]] * ndim
    for raw_axis, raw_spec in axes_raw.items():
        axis = parse_grid_axis_key(raw_axis, ndim, "grid.distribution.axes")
        spec = normalize_axis_distribution_spec(raw_spec)
        axis_type = validate_choice(
            spec.get("type", "interface_fitted" if default_enabled else "uniform"),
            ("uniform", "interface_fitted"),
            f"grid.distribution.axes.{raw_axis}.type",
        )
        if "method" in spec:
            raise ValueError(
                "grid.distribution.method is global; axis-local method is not supported "
                f"(got grid.distribution.axes.{raw_axis}.method)"
            )
        method = default_method if axis_type == "interface_fitted" else "none"
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
            wall_axes[axis] = wall_defaults["enabled"]
        else:
            wall_axes[axis] = False
            wall_alpha[axis] = 1.0
        if "wall" in spec:
            wall_spec = parse_wall_refinement_defaults(
                spec.get("wall"),
                ndim=ndim,
                bc_type=bc_type,
                default_eps_factor=wall_defaults["eps_g_factor"],
                nonuniform_enabled=axis_type == "interface_fitted",
                context=f"grid.distribution.axes.{raw_axis}.wall",
            )
            wall_axes[axis] = wall_spec["enabled"]
            wall_alpha[axis] = wall_spec["alpha"]
            wall_eps_factor[axis] = wall_spec["eps_g_factor"]
            wall_eps_cells[axis] = wall_spec["eps_g_cells"]
            wall_sides[axis] = wall_spec["sides"]
    return {
        "fitting_axes": tuple(fitting_axes),
        "methods": tuple(methods),
        "fitting_alpha_grid": tuple(fitting_alpha),
        "fitting_eps_g_factor": tuple(fitting_eps_factor),
        "fitting_eps_g_cells": tuple(fitting_eps_cells),
        "fitting_dx_min_floor": tuple(fitting_dx_floor),
        "wall_refinement_axes": tuple(wall_axes),
        "wall_alpha_grid": tuple(wall_alpha),
        "wall_eps_g_factor_axes": tuple(wall_eps_factor),
        "wall_eps_g_cells": tuple(wall_eps_cells),
        "wall_sides": tuple(wall_sides),
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


def normalize_interface_fitting_method(
    raw: Any,
    *,
    path: str = "grid.distribution.method",
) -> str:
    """Validate the canonical interface-fitting method name."""
    method = str(raw).strip().lower()
    if method not in {"gaussian_levelset", "none"}:
        raise ValueError(
            f"{path} must be gaussian_levelset|none, got {method!r}"
        )
    return method
