"""Reference solution and test-function registry for experiment runner."""

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


@register_solution("ode_decay_exact")
def _ode_decay(T=1.0, **_):
    """q(T) = e^{-T} for dq/dt = -q."""
    return float(np.exp(-T))


@register_solution("zero")
def _zero(**_):
    """Exact solution = 0; use when the adapter computes error internally."""
    return 0.0
