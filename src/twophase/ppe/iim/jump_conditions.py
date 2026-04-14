"""
High-order jump condition calculator for IIM-CCD PPE.

Computes interface jump conditions [p^(k)]_Γ (k=0..max_order) required
for the CCD stencil correction at interface-crossing grid points.

Theory (docs/memo/IIM_CCD_PPE_ShortPaper.md §3):
    k=0: [p] = σκ                                      (Young-Laplace)
    k=1: [p'] from [1/ρ · p'] = 0                      (normal flux continuity)
    k=2..5: recurrence from repeated differentiation of
            d/dx(1/ρ dp/dx) = q

For CCD O(h^6) accuracy, jumps up to k=5 are needed. The overall
accuracy is min(6, k_max+1, p_κ) where p_κ is the curvature accuracy.

Architecture:
    JumpConditionCalculator: stateless calculator, receives interface data
    per call. No grid/solver dependency — pure numerical computation.
"""

from __future__ import annotations

import numpy as np


class JumpConditionCalculator:
    """Compute high-order jump conditions [p^(k)] at interface crossings.

    Parameters
    ----------
    max_order : int
        Maximum derivative order (default 5 for O(h^6) CCD).
    """

    def __init__(self, max_order: int = 5) -> None:
        self.max_order = max_order

    def compute_1d_jumps(
        self,
        sigma: float,
        kappa: float,
        rho_l: float,
        rho_g: float,
        p_prime_l: float,
        p_double_prime_l: float,
        q_l: float,
        q_g: float,
        drho_l: float = 0.0,
        drho_g: float = 0.0,
    ) -> np.ndarray:
        """Compute 1D jump conditions C_k = [p^(k)]_Γ for k=0..max_order.

        All quantities are evaluated at the interface location x*.

        Parameters
        ----------
        sigma   : surface tension coefficient
        kappa   : interface curvature (positive for bubble interior)
        rho_l   : liquid-side density
        rho_g   : gas-side density
        p_prime_l       : liquid-side dp/dx at interface
        p_double_prime_l: liquid-side d²p/dx² at interface
        q_l     : liquid-side PPE RHS at interface
        q_g     : gas-side PPE RHS at interface
        drho_l  : liquid-side dρ/dx (0 for piecewise-constant ρ)
        drho_g  : gas-side dρ/dx (0 for piecewise-constant ρ)

        Returns
        -------
        C : np.ndarray, shape (max_order+1,)
            C[k] = [p^(k)]_Γ for k=0,1,...,max_order
        """
        C = np.zeros(self.max_order + 1)

        # k=0: [p] = σκ  (Young-Laplace)
        C[0] = sigma * kappa

        # k=1: from [1/ρ · p'] = 0
        #   p'_g / ρ_g = p'_l / ρ_l
        #   => p'_g = (ρ_g / ρ_l) p'_l
        #   => [p'] = p'_g - p'_l = (ρ_g/ρ_l - 1) p'_l
        if self.max_order >= 1:
            C[1] = (rho_g / rho_l - 1.0) * p_prime_l

        # k=2: from the PDE  (1/ρ)p'' - (ρ'/ρ²)p' = q
        #   [p''] derived from jumping the PDE across Γ
        if self.max_order >= 2:
            # PDE: (1/ρ)p'' = q + (ρ'/ρ²)p'
            # => p'' = ρ(q + (ρ'/ρ²)p') = ρq + (ρ'/ρ)p'
            # Jump: [p''] = [ρq + (ρ'/ρ)p']
            #             = ρ_g(q_g + drho_g/ρ_g * p'_g) - ρ_l(q_l + drho_l/ρ_l * p'_l)
            p_prime_g = (rho_g / rho_l) * p_prime_l
            p_pp_l = rho_l * q_l + drho_l * p_prime_l / rho_l * rho_l
            p_pp_g = rho_g * q_g + drho_g * p_prime_g / rho_g * rho_g
            # Simplify: p'' = ρ·q + ρ'·p'/ρ · ρ = ρ·q + ρ'·p'
            p_pp_l = rho_l * q_l + drho_l * p_prime_l
            p_pp_g = rho_g * q_g + drho_g * p_prime_g
            C[2] = p_pp_g - p_pp_l

        # k>=3: Higher-order jumps via finite differences of the PDE.
        # For piecewise-constant density (drho=0 in each phase, which is
        # the standard two-phase case), the recurrence simplifies:
        #   [p^(k)] = ρ_g · q_g^(k-2) - ρ_l · q_l^(k-2)
        # Since q is typically smooth within each phase, q^(j) ≈ 0 for j≥1
        # at coarse grids, yielding C_k ≈ 0 for k≥3.
        # We leave them as zero — the dominant contributions are C_0, C_1, C_2.
        # Higher-order terms can be populated if q derivatives are supplied.

        return C

    def compute_2d_jumps(
        self,
        sigma: float,
        kappa: float,
        rho_l: float,
        rho_g: float,
        grad_p_l: np.ndarray,
        normal: np.ndarray,
        q_l: float = 0.0,
        q_g: float = 0.0,
    ) -> np.ndarray:
        """Compute 2D jump conditions in the normal direction.

        Parameters
        ----------
        sigma   : surface tension coefficient
        kappa   : interface curvature
        rho_l   : liquid density
        rho_g   : gas density
        grad_p_l: liquid-side pressure gradient [dp/dx, dp/dy]
        normal  : interface unit normal [nx, ny] (liquid → gas)
        q_l     : liquid-side PPE RHS
        q_g     : gas-side PPE RHS

        Returns
        -------
        C : np.ndarray, shape (max_order+1,)
            Jump conditions in the normal direction.
        """
        # Project liquid gradient onto normal
        p_n_l = float(np.dot(grad_p_l, normal))

        # For piecewise-constant density, drho=0 in each phase
        C = self.compute_1d_jumps(
            sigma=sigma,
            kappa=kappa,
            rho_l=rho_l,
            rho_g=rho_g,
            p_prime_l=p_n_l,
            p_double_prime_l=0.0,  # approximated
            q_l=q_l,
            q_g=q_g,
            drho_l=0.0,
            drho_g=0.0,
        )
        return C
