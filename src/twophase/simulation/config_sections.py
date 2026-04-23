"""Grid and physics parsing helpers for experiment configs."""

from __future__ import annotations

import math
from typing import Any

from .config_models import GridCfg, PhysicsCfg


def parse_grid(d: dict, interface: dict) -> GridCfg:
    """Parse the grid section from experiment YAML."""
    cells = d["cells"]
    NX, NY = int(cells[0]), int(cells[1])
    domain = d["domain"]
    size = domain["size"]
    LX, LY = float(size[0]), float(size[1])
    distribution = d["distribution"]
    width = interface["thickness"]
    distribution_type = validate_choice(
        distribution["type"],
        ("uniform", "interface_fitted"),
        "grid.distribution.type",
    )
    fitting_enabled = distribution_type == "interface_fitted"
    fitting_method = normalize_interface_fitting_method(
        distribution.get("method", "gaussian_levelset" if fitting_enabled else "none")
    )
    if fitting_method == "none":
        fitting_enabled = False
    alpha_grid = float(distribution.get("alpha", 1.0))
    if not fitting_enabled:
        alpha_grid = 1.0
    eps_factor = float(width.get("base_factor", 1.5))
    eps_g_factor = float(distribution.get("eps_g_factor", 2.0))
    eps_g_cells = opt_float(distribution.get("eps_g_cells"))
    eps_xi_cells = opt_float(width.get("xi_cells"))
    use_local_eps = parse_interface_width_mode(width, eps_xi_cells)
    return GridCfg(
        NX=NX,
        NY=NY,
        LX=LX,
        LY=LY,
        bc_type=str(domain["boundary"]),
        alpha_grid=alpha_grid,
        eps_factor=eps_factor,
        eps_g_factor=eps_g_factor,
        eps_g_cells=eps_g_cells,
        dx_min_floor=float(d.get("dx_min_floor", 1e-6)),
        use_local_eps=use_local_eps,
        eps_xi_cells=eps_xi_cells,
        grid_rebuild_freq=parse_grid_rebuild(distribution.get("schedule", "static")),
        interface_fitting_enabled=fitting_enabled,
        interface_fitting_method=("none" if not fitting_enabled else fitting_method),
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


def normalize_interface_fitting_method(raw: Any) -> str:
    """Validate the canonical interface-fitting method name."""
    method = str(raw).strip().lower()
    if method not in {"gaussian_levelset", "none"}:
        raise ValueError(
            "grid.distribution.method must be gaussian_levelset|none, "
            f"got {method!r}"
        )
    return method
