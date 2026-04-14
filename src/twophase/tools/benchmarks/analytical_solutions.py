"""
Analytical solutions for benchmark validation.

Exact solutions used across experiment scripts for convergence testing
and MMS verification. Centralised here to eliminate duplication.
"""

from __future__ import annotations
import numpy as np

__all__ = [
    "tgv_velocity", "tgv_pressure", "tgv_kinetic_energy",
    "kovasznay_lambda", "kovasznay_velocity", "kovasznay_pressure",
    "hydrostatic_pressure",
    "mms_sine_pressure", "mms_sine_laplacian",
]


# ── Taylor-Green Vortex (2-D, periodic) ──────────────────────────────────────

def tgv_velocity(X, Y, t: float, nu: float):
    """Exact Taylor-Green vortex velocity at time t.

    u(x,y,t) =  sin(x) cos(y) exp(-2 nu t)
    v(x,y,t) = -cos(x) sin(y) exp(-2 nu t)

    Domain: [0, 2*pi]^2, periodic BC.

    Parameters
    ----------
    X, Y : arrays — meshgrid coordinate arrays
    t    : float — time
    nu   : float — kinematic viscosity (1/Re)

    Returns
    -------
    u, v : arrays — velocity components
    """
    decay = np.exp(-2.0 * nu * t)
    u = np.sin(X) * np.cos(Y) * decay
    v = -np.cos(X) * np.sin(Y) * decay
    return u, v


def tgv_pressure(X, Y, t: float, nu: float):
    """Exact TGV pressure: p = -(1/4)(cos(2x) + cos(2y)) exp(-4 nu t)."""
    return -0.25 * (np.cos(2.0 * X) + np.cos(2.0 * Y)) * np.exp(-4.0 * nu * t)


def tgv_kinetic_energy(t: float, nu: float, L: float = 2.0 * np.pi):
    """Exact TGV kinetic energy: E_k(t) = (pi^2) exp(-4 nu t) for [0,2pi]^2."""
    return np.pi ** 2 * np.exp(-4.0 * nu * t)


# ── Kovasznay Flow (steady, Re-dependent) ────────────────────────────────────

def kovasznay_lambda(Re: float) -> float:
    """Kovasznay eigenvalue: lambda = Re/2 - sqrt(Re^2/4 + 4*pi^2)."""
    return Re / 2.0 - np.sqrt(Re ** 2 / 4.0 + 4.0 * np.pi ** 2)


def kovasznay_velocity(X, Y, Re: float):
    """Exact Kovasznay flow velocity (steady).

    u = 1 - exp(lambda*x) cos(2*pi*y)
    v = (lambda / 2*pi) exp(lambda*x) sin(2*pi*y)

    Parameters
    ----------
    X, Y : arrays — meshgrid
    Re   : float — Reynolds number

    Returns
    -------
    u, v : arrays
    """
    lam = kovasznay_lambda(Re)
    u = 1.0 - np.exp(lam * X) * np.cos(2.0 * np.pi * Y)
    v = lam / (2.0 * np.pi) * np.exp(lam * X) * np.sin(2.0 * np.pi * Y)
    return u, v


def kovasznay_pressure(X, Y, Re: float):
    """Exact Kovasznay pressure: p = -0.5 exp(2*lambda*x)."""
    lam = kovasznay_lambda(Re)
    return -0.5 * np.exp(2.0 * lam * X)


# ── Hydrostatic Pressure ─────────────────────────────────────────────────────

def hydrostatic_pressure(Y, rho: float, g: float, y_top: float):
    """Exact hydrostatic pressure: p = rho * |g| * (y_top - y).

    Parameters
    ----------
    Y     : array — vertical coordinate
    rho   : float — density
    g     : float — gravity magnitude (positive downward)
    y_top : float — top of domain (zero-pressure reference)
    """
    return rho * abs(g) * (y_top - Y)


# ── MMS: Manufactured Pressure ───────────────────────────────────────────────

def mms_sine_pressure(X, Y):
    """Manufactured pressure: p* = sin(pi*x) sin(pi*y).

    Standard MMS for PPE verification. Exact Laplacian:
        nabla^2 p* = -2 pi^2 sin(pi*x) sin(pi*y)
    """
    return np.sin(np.pi * X) * np.sin(np.pi * Y)


def mms_sine_laplacian(X, Y):
    """Exact Laplacian of mms_sine_pressure."""
    return -2.0 * np.pi ** 2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
