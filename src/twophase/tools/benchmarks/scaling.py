"""Common dimensional-to-nondimensional conversion helpers for benchmarks."""

from __future__ import annotations

import numpy as np


def mu_from_re(rho_l: float, g_acc: float, d_ref: float, re_num: float) -> float:
    """Compute dynamic viscosity from Reynolds number."""
    return float(rho_l * np.sqrt(g_acc * d_ref) * d_ref / re_num)


def sigma_from_eo(rho_l: float, rho_g: float, g_acc: float, d_ref: float, eo_num: float) -> float:
    """Compute surface tension from Eotvos number."""
    return float(g_acc * (rho_l - rho_g) * d_ref ** 2 / eo_num)


def mu_sigma_from_re_eo(
    rho_l: float,
    rho_g: float,
    g_acc: float,
    d_ref: float,
    re_num: float,
    eo_num: float,
) -> tuple[float, float]:
    """Return (mu, sigma) derived from (Re, Eo)."""
    mu = mu_from_re(rho_l, g_acc, d_ref, re_num)
    sigma = sigma_from_eo(rho_l, rho_g, g_acc, d_ref, eo_num)
    return mu, sigma

