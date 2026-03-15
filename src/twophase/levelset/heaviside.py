"""
Regularised Heaviside, delta function, and material-property update.

Implements Section 3 (§3.2–§3.3) of the paper.

The Conservative Level Set variable ψ is defined as:

    ψ = H_ε(φ) = 1 / (1 + exp(−φ/ε))                  (§3.2 Eq.33)

where φ is the signed-distance function and ε ≈ 1.5 Δx_min controls
the interface thickness.

The regularised delta function (interface indicator) is:

    δ_ε(φ) = dH_ε/dφ = (1/ε) H_ε(φ)(1 − H_ε(φ))      (§3.2 Eq.33′)

Material properties are linearly interpolated across the interface:

    ρ̃(ψ) = ρ_g + (ρ_l − ρ_g) · ψ                       (§2.4 Eq.6)
    μ̃(ψ) = μ_g + (μ_l − μ_g) · ψ                       (§2.4 Eq.7)

The Newton-inversion of H_ε (needed for curvature computation) is:

    φ = H_ε^{-1}(ψ) = ε · ln(ψ / (1 − ψ))              (§3.6 exact inverse)

with a clipping step to keep ψ ∈ (δ, 1−δ) before inversion.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Small clipping value to avoid log(0) in Newton inversion
_PSI_CLIP = 1e-10


def heaviside(xp, phi, eps: float):
    """Regularised Heaviside H_ε(φ).

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
    """Exact inverse of H_ε: φ = ε · ln(ψ / (1 − ψ)).

    Parameters
    ----------
    xp  : array namespace
    psi : array of ψ values (clipped to (_PSI_CLIP, 1-_PSI_CLIP))
    eps : interface thickness ε

    Returns
    -------
    phi : signed-distance estimate
    """
    psi_safe = xp.clip(psi, _PSI_CLIP, 1.0 - _PSI_CLIP)
    return eps * xp.log(psi_safe / (1.0 - psi_safe))


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
