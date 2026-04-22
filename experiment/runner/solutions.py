"""Reference solution and test-function registry for experiment runner.

Spatial test functions return (f, (fx, fy), (fxx, fyy)).
Analytical solutions wrap twophase.tools.benchmarks.analytical_solutions.
"""

from __future__ import annotations

import numpy as np

from .registry import register_solution


# ── Spatial test functions ────────────────────────────────────────────────────

@register_solution("sin_2pi")
def _sin_2pi(X, Y, xp=None):
    """f = sin(2π x)·sin(2π y) — periodic, full O(h^6)."""
    xp = xp or np
    k = 2 * np.pi
    f = xp.sin(k * X) * xp.sin(k * Y)
    fx = k * xp.cos(k * X) * xp.sin(k * Y)
    fy = k * xp.sin(k * X) * xp.cos(k * Y)
    fxx = -(k**2) * f
    fyy = -(k**2) * f
    return f, (fx, fy), (fxx, fyy)


@register_solution("exp_sincos")
def _exp_sincos(X, Y, xp=None):
    """f = exp(sin(π x))·exp(cos(π y)) — wall BC, O(h^5) boundary-limited."""
    xp = xp or np
    sx, cx = xp.sin(np.pi * X), xp.cos(np.pi * X)
    sy, cy = xp.sin(np.pi * Y), xp.cos(np.pi * Y)
    ef = xp.exp(sx) * xp.exp(cy)
    f = ef
    fx = np.pi * cx * ef
    fxx = ef * np.pi**2 * (-sx + cx**2)
    fy = -np.pi * sy * ef
    fyy = ef * np.pi**2 * (-cy + sy**2)
    return f, (fx, fy), (fxx, fyy)


# ── Analytical solutions (library wrappers) ───────────────────────────────────

@register_solution("tgv_kinetic_energy")
def _tgv_ke(t, nu=0.01, **_):
    from twophase.tools.benchmarks.analytical_solutions import tgv_kinetic_energy
    return tgv_kinetic_energy(t, nu)


@register_solution("tgv_velocity")
def _tgv_vel(X, Y, t=0.0, nu=0.01, **_):
    from twophase.tools.benchmarks.analytical_solutions import tgv_velocity
    return tgv_velocity(X, Y, t, nu)


@register_solution("tgv_pressure")
def _tgv_pres(X, Y, t=0.0, nu=0.01, **_):
    from twophase.tools.benchmarks.analytical_solutions import tgv_pressure
    return tgv_pressure(X, Y, t, nu)


@register_solution("kovasznay_velocity")
def _kov_vel(X, Y, Re=40.0, **_):
    from twophase.tools.benchmarks.analytical_solutions import kovasznay_velocity
    return kovasznay_velocity(X, Y, Re)


@register_solution("kovasznay_pressure")
def _kov_pres(X, Y, Re=40.0, **_):
    from twophase.tools.benchmarks.analytical_solutions import kovasznay_pressure
    return kovasznay_pressure(X, Y, Re)


@register_solution("mms_sine_pressure")
def _mms_sine_p(X, Y, **_):
    from twophase.tools.benchmarks.analytical_solutions import mms_sine_pressure
    return mms_sine_pressure(X, Y)


@register_solution("mms_sine_laplacian")
def _mms_sine_lap(X, Y, **_):
    from twophase.tools.benchmarks.analytical_solutions import mms_sine_laplacian
    return mms_sine_laplacian(X, Y)


@register_solution("hydrostatic_pressure")
def _hydrostatic(X, Y, rho=1.0, g=1.0, **_):
    from twophase.tools.benchmarks.analytical_solutions import hydrostatic_pressure
    return hydrostatic_pressure(X, Y, rho, g)


@register_solution("ode_decay_exact")
def _ode_decay(T=1.0, **_):
    """q(T) = e^{-T} for dq/dt = -q."""
    return float(np.exp(-T))
