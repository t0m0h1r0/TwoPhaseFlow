"""Convenience runtime services for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .runtime_setup import (
    build_initial_condition,
    build_initial_velocity,
    make_boundary_condition_hook,
)


@dataclass(frozen=True)
class NSRuntimeSetupContext:
    backend: object
    grid: object
    eps: float
    X: object
    Y: object
    LY: float
    bc_type: str
    reconstruct_base: object


@dataclass(frozen=True)
class NSTimestepEstimateContext:
    backend: object
    h: float
    h_min: float
    alpha_grid: float
    cn_viscous: bool


def psi_from_phi(context: NSRuntimeSetupContext, phi: np.ndarray) -> np.ndarray:
    """Return the smooth Heaviside field reconstructed from ``phi``."""
    return np.asarray(context.backend.to_host(context.reconstruct_base.psi_from_phi(phi)))


def build_runtime_initial_condition(
    context: NSRuntimeSetupContext,
    initial_condition: dict,
) -> np.ndarray:
    """Build the initial conservative level-set field on the host."""
    return build_initial_condition(context.grid, context.eps, initial_condition)


def build_runtime_initial_velocity(
    context: NSRuntimeSetupContext,
    initial_velocity: dict | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the initial velocity field on the host."""
    return build_initial_velocity(
        context.X,
        context.Y,
        initial_velocity,
        context.backend.to_host,
    )


def make_runtime_boundary_condition_hook(
    context: NSRuntimeSetupContext,
    boundary_condition: dict | None,
):
    """Return a ``bc_hook(u, v)`` callable from config-like input."""
    return make_boundary_condition_hook(
        boundary_condition,
        context.bc_type,
        context.LY,
    )


def compute_runtime_dt_max(
    context: NSTimestepEstimateContext,
    u: np.ndarray,
    v: np.ndarray,
    physics,
    *,
    cfl: float = 0.15,
) -> float:
    """Estimate the stable timestep from CFL, viscous, and capillary limits."""
    h = context.h_min if context.alpha_grid > 1.0 else context.h
    mu_max = max(filter(None, [physics.mu, physics.mu_l, physics.mu_g]))
    rho_min = physics.rho_g

    xp = context.backend.xp
    uv_max = np.asarray(
        context.backend.to_host(
            xp.stack([xp.max(xp.abs(xp.asarray(u))), xp.max(xp.abs(xp.asarray(v)))])
        )
    )
    u_max = max(float(uv_max[0]), float(uv_max[1]), 1e-10)
    dt_cfl = cfl * h / u_max
    visc_safety = 0.5 if context.cn_viscous else 0.25
    dt_visc = visc_safety * h ** 2 / (mu_max / rho_min)

    if physics.sigma > 0.0:
        rho_sum = physics.rho_l + physics.rho_g
        dt_cap = 0.25 * np.sqrt(
            rho_sum * h ** 3 / (2.0 * np.pi * physics.sigma)
        )
        return min(dt_cfl, dt_visc, dt_cap)
    return min(dt_cfl, dt_visc)
