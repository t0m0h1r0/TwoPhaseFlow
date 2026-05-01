"""Setup helpers for config-driven two-phase simulations.

This module keeps initial-condition parsing and boundary-hook construction
separate from the main solver orchestration so ``ns_pipeline`` can focus on
time stepping and scheme wiring.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from ..core.boundary import boundary_axes, is_all_periodic

from .initial_conditions.builder import InitialConditionBuilder
from .initial_conditions.velocity_fields import velocity_field_from_dict


def _xp_of(array):
    if type(array).__module__.split(".", 1)[0] == "cupy":
        import cupy
        return cupy
    return np


def normalise_ic_dict(ic: dict) -> dict:
    """Convert shorthand IC dicts to ``InitialConditionBuilder`` format."""
    if "shapes" in ic and "type" not in ic:
        return ic

    ic_type = ic.get("type", "")

    if ic_type == "union":
        shapes = ic.get("shapes", [])
        background_phase = ic.get("background_phase") or infer_background(shapes)
        return {"background_phase": background_phase, "shapes": shapes}

    if ic_type:
        shape_dict = {k: v for k, v in ic.items() if k not in {"background_phase"}}
        background_phase = ic.get("background_phase") or infer_background([shape_dict])
        return {"background_phase": background_phase, "shapes": [shape_dict]}

    return ic


def infer_background(shapes: list[dict]) -> str:
    """Infer the complement phase used outside the configured shapes."""
    for shape in shapes:
        if shape.get("interior_phase", "liquid") == "gas":
            return "liquid"
    return "gas"


def build_initial_condition(
    grid,
    eps: float,
    initial_condition: dict,
    *,
    return_host: bool = True,
):
    """Build the initial conservative level-set field."""
    ic_norm = normalise_ic_dict(dict(initial_condition))
    builder = InitialConditionBuilder.from_dict(ic_norm)
    psi = builder.build(grid, eps, return_host=return_host)
    return np.asarray(psi) if return_host else psi


def build_initial_velocity(
    X,
    Y,
    initial_velocity: dict | None,
    to_host: Callable[[object], object],
    *,
    return_host: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the initial velocity field."""
    if initial_velocity is None:
        xp = np if return_host else _xp_of(X)
        return xp.zeros(X.shape), xp.zeros(Y.shape)

    spec = dict(initial_velocity)
    velocity_field = velocity_field_from_dict(spec)
    u, v = velocity_field.compute(X, Y)
    if return_host:
        return np.asarray(to_host(u)), np.asarray(to_host(v))
    return u, v


def wall_bc_hook(u: np.ndarray, v: np.ndarray, bc_type: str = "wall") -> None:
    """Apply no-slip / no-penetration walls on all boundaries."""
    axes = boundary_axes(bc_type, u.ndim)
    for arr in (u, v):
        if axes[0] == "wall":
            arr[0, :] = 0.0
            arr[-1, :] = 0.0
        if axes[1] == "wall":
            arr[:, 0] = 0.0
            arr[:, -1] = 0.0


def apply_velocity_bc(u, v, bc_hook, bc_type: str) -> None:
    """Apply the configured velocity boundary condition in-place."""
    if bc_hook is not None:
        bc_hook(u, v)
    elif not is_all_periodic(bc_type, u.ndim):
        wall_bc_hook(u, v, bc_type=bc_type)


def make_boundary_condition_hook(
    boundary_condition: dict | None,
    bc_type: str,
    LY: float,
):
    """Return a ``bc_hook(u, v)`` callable from config-like input."""
    if boundary_condition is None:
        if is_all_periodic(bc_type, 2):
            return None
        return lambda u, v: wall_bc_hook(u, v, bc_type=bc_type)

    hook_type = boundary_condition.get("type", "wall")
    if hook_type == "couette":
        gamma = float(boundary_condition.get("gamma_dot", 1.0))
        U = 0.5 * gamma * LY

        def _couette(u: np.ndarray, v: np.ndarray) -> None:
            u[:, 0] = -U
            u[:, -1] = +U
            v[:, 0] = 0.0
            v[:, -1] = 0.0
            u[0, :] = u[1, :]
            u[-1, :] = u[-2, :]

        return _couette

    return lambda u, v: wall_bc_hook(u, v, bc_type=bc_type)
