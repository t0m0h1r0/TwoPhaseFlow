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
    viscous_time_scheme: str = "forward_euler"
    h_axes: tuple[float, ...] | None = None


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
    """Estimate the stable timestep from advective, viscous, and capillary limits.

    The advective bound uses the multidimensional Courant sum
    ``Σ_i max|u_i| / h_i`` rather than ``max_i |u_i| / h_min``.  The capillary
    bound uses the Denner--van Wachem wave-resolution scale with the same
    dimensionless user coefficient ``cfl`` interpreted as ``C_wave``.  For
    non-uniform grids these are necessary timestep scales, not a proof of
    stability for the full non-normal compact operator.
    """
    h_axes = context.h_axes
    if h_axes is None:
        h = context.h_min if context.alpha_grid > 1.0 else context.h
        h_axes = (h, h)
    h_min = min(h_axes)
    mu_max = max(filter(None, [physics.mu, physics.mu_l, physics.mu_g]))
    rho_min = physics.rho_g

    xp = context.backend.xp
    axis_speeds = np.asarray(
        context.backend.to_host(
            xp.stack([xp.max(xp.abs(xp.asarray(u))), xp.max(xp.abs(xp.asarray(v)))])
        )
    )
    advective_rate = sum(
        float(speed) / float(h_axis)
        for speed, h_axis in zip(axis_speeds, h_axes)
    )
    dt_cfl = float("inf") if advective_rate <= 1e-14 else cfl / advective_rate

    nu_max = mu_max / rho_min
    inv_h2_sum = sum(1.0 / (float(h_axis) ** 2) for h_axis in h_axes)
    explicit_visc_dt = 1.0 / (2.0 * nu_max * inv_h2_sum)
    if context.viscous_time_scheme == "implicit_bdf2":
        dt_visc = float("inf")
    else:
        dt_visc = (2.0 if context.cn_viscous else 1.0) * explicit_visc_dt

    if physics.sigma > 0.0:
        rho_sum = physics.rho_l + physics.rho_g
        dt_cap = cfl * np.sqrt(
            rho_sum * h_min ** 3 / (2.0 * np.pi * physics.sigma)
        )
        return min(dt_cfl, dt_visc, dt_cap)
    return min(dt_cfl, dt_visc)
