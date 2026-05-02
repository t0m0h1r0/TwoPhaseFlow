"""
Regularised Heaviside, delta function, and material-property update.

Implements Section 3 (§3.2–§3.3) of the paper.

This module provides the increasing logistic helper:

    H_ε(s) = 1 / (1 + exp(−s/ε))

The paper/runtime CLS convention for a liquid-inside signed distance
``φ_lg`` is ``ψ = H_ε(-φ_lg)``.  Therefore callers that hold the paper
signed distance must pass ``-φ_lg`` to :func:`heaviside`, or use the
initial-condition builder which applies that sign convention directly.

The regularised delta function (interface indicator) is:

    δ_ε(φ) = dH_ε/dφ = (1/ε) H_ε(φ)(1 − H_ε(φ))      (§3.2 Eq.33′)

Material properties are linearly interpolated across the interface:

    ρ̃(ψ) = ρ_g + (ρ_l − ρ_g) · ψ                       (§2.4 Eq.6)
    μ̃(ψ) = μ_g + (μ_l − μ_g) · ψ                       (§2.4 Eq.7)

The inverse of this increasing helper is:

    s = H_ε^{-1}(ψ) = ε · ln(ψ / (1 − ψ))

For the paper signed distance, ``φ_lg = -s``.

with a clipping step to keep ψ ∈ (δ, 1−δ) before inversion.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Saturation clamp (section 3b algbox step 1): delta_clamp = 1e-6
# phi_max = eps * ln((1 - delta_clamp) / delta_clamp) ~ 13.8 * eps
_DELTA_CLAMP = 1e-6

# Legacy clip value retained for backward compatibility
_PSI_CLIP = 1e-10


def heaviside(xp, phi, eps: float):
    """Increasing regularised Heaviside helper ``H_ε(phi)``.

    For the paper CLS convention ``ψ=H_ε(-φ_lg)``, pass ``-φ_lg``.

    Parameters
    ----------
    xp  : array namespace
    phi : array (signed-distance values)
    eps : interface thickness ε

    Returns
    -------
    psi : array in (0, 1)
    """
    return 1.0 / (1.0 + xp.exp(-phi / eps))


def delta(xp, phi, eps: float):
    """Regularised delta function δ_ε(φ) = dH_ε/dφ.

    Parameters
    ----------
    xp  : array namespace
    phi : array (signed-distance values)
    eps : interface thickness ε

    Returns
    -------
    delta_eps : array ≥ 0, peaked at φ = 0
    """
    H = heaviside(xp, phi, eps)
    return (1.0 / eps) * H * (1.0 - H)


def invert_heaviside(xp, psi, eps: float):
    """Exact inverse of the increasing ``H_ε`` helper with saturation handling.

    Algorithm (section 3b):
      1. Saturation test: psi < delta_clamp or psi > 1 - delta_clamp
      2. Saturated points: phi = +/- phi_max
      3. Standard region: s = eps * ln(psi / (1 - psi))

    No iterative alternative is applied: saturation is the analytic logit after
    clipping ψ into [delta_clamp, 1-delta_clamp].

    Parameters
    ----------
    xp  : array namespace
    psi : array of psi values in [0, 1]
    eps : interface thickness epsilon

    Returns
    -------
    phi : increasing-helper coordinate ``s``; paper ``φ_lg`` is ``-s``
    """
    import math

    # Saturation handling is equivalent to clipping ψ into
    # [delta_clamp, 1-delta_clamp] before the analytic logit inversion:
    #
    #   phi = eps * log(psi / (1 - psi))
    #
    # For ψ outside that interval, clipping yields exactly +/- phi_max.
    # This keeps the section-3b semantics while avoiding mask-heavy scatter
    # updates on the GPU hot path used by interface-fitted regridding.
    eps_arr = xp.asarray(eps)
    psi_clip = xp.clip(xp.asarray(psi), _DELTA_CLAMP, 1.0 - _DELTA_CLAMP)
    return eps_arr * xp.log(psi_clip / (1.0 - psi_clip))


def apply_mass_correction(xp, q, dV, M_target):
    """Interface-weighted mass correction (WIKI-T-027).

    Adjusts q so that ∫q dV = M_target, distributing the correction
    proportionally to w = 4q(1−q) (peaked at the interface).

    M_target accepts float, numpy scalar, or 0-d array — kept device-side
    throughout to avoid host sync on the GPU backend.

    Parameters
    ----------
    xp       : array namespace
    q        : array — CLS field ψ ∈ [0, 1]
    dV       : array or scalar — cell volumes
    M_target : float | 0-d array — target mass ∫ψ dV

    Returns
    -------
    q_corrected : array — mass-corrected and clipped to [0, 1]
    """
    M_new = xp.sum(q * dV)                           # 0-d
    w = 4.0 * q * (1.0 - q)
    W = xp.sum(w * dV)                               # 0-d
    # Preserve legacy division order for bit-exactness: (M - M_new) / W,
    # NOT (M - M_new) * (1/W) — the latter introduces an extra rounding
    # per call that compounds over long runs. W_safe avoids 0/0 in the
    # unused branch; gate zeroes the correction when W <= 1e-12.
    W_safe = xp.where(W > 1e-12, W, 1.0)
    ratio = (xp.asarray(M_target) - M_new) / W_safe
    gate = xp.where(W > 1e-12, 1.0, 0.0)
    q_new = q + (gate * ratio) * w
    return xp.clip(q_new, 0.0, 1.0)


def apply_mass_correction_legacy(xp, q, dV, M_target: float):
    """Legacy float-gated implementation (pre-CuPy sync removal).

    DO NOT DELETE — reference implementation. Reinstate if any bit-exact
    regression appears on the NumPy path.
    """
    M_new = float(xp.sum(q * dV))
    w = 4.0 * q * (1.0 - q)
    W = float(xp.sum(w * dV))
    if W > 1e-12:
        q = q + ((M_target - M_new) / W) * w
        q = xp.clip(q, 0.0, 1.0)
    return q


def update_properties(xp, psi, rho_l: float, rho_g: float,
                      mu_l: float, mu_g: float):
    """Compute density and viscosity fields from ψ.

    Parameters
    ----------
    xp    : array namespace
    psi   : Conservative Level Set field ψ ∈ [0, 1]
    rho_l : liquid density (dimensionless = 1.0 in the paper's scaling)
    rho_g : gas density = rho_ratio * rho_l
    mu_l  : liquid viscosity (dimensionless = 1.0)
    mu_g  : gas viscosity = mu_ratio * mu_l

    Returns
    -------
    rho : density array, shape like psi
    mu  : dynamic viscosity array, shape like psi
    """
    rho = rho_g + (rho_l - rho_g) * psi   # §2.4 Eq.6
    mu  = mu_g  + (mu_l  - mu_g)  * psi   # §2.4 Eq.7
    return rho, mu
