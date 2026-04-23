"""
IIM stencil correction for CCD-based PPE.

Computes the RHS correction Δq that accounts for pressure jumps [p]=σκ
at interface crossings, enabling the CCD operator to maintain high-order
accuracy across the sharp interface.

Theory (docs/memo/IIM_CCD_PPE_ShortPaper.md §4):
    For an interface crossing between x_i and x_{i+1} at x* = x_i + α·h:
    The CCD Hermite system (p, p', p'') requires corrections from
    C_0=[p], C_1=[p'], C_2=[p''] at all three equation levels.

    RHS^{IIM} = RHS^{std} - W(α) · C

    where W(α) is a weight vector depending on the fractional crossing
    position α ∈ (0,1), and C = [C_0,...,C_5]^T are the jump conditions.

Architecture:
    IIMStencilCorrector: receives the CCD sparse operator L, level-set φ,
    curvature κ, and jump conditions. Produces the flat correction vector Δq.
    Stateless — all grid/operator info passed per call.

Two modes:
    1. "nearest" (zeroth-order): Only C_0=[p]=σκ correction.
       Simple, robust, O(h^2) near interface.
    2. "hermite" (high-order): C_0,C_1,C_2 corrections on all three
       CCD equation types. O(h^6) near interface (if curvature is accurate).
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.grid import Grid

from .jump_conditions import JumpConditionCalculator
from .stencil_corrector_hermite import compute_hermite_stencil_correction
from .stencil_corrector_nearest import compute_nearest_stencil_correction
from .stencil_corrector_utils import find_interface_crossings, sparse_element


class IIMStencilCorrector:
    """Compute IIM RHS correction for the CCD PPE operator.

    Parameters
    ----------
    grid : Grid
    mode : str
        "nearest" — zeroth-order jump only (C_0).
        "hermite" — high-order jumps (C_0, C_1, C_2) with Hermite weighting.
    """

    def __init__(self, grid: "Grid", mode: str = "hermite") -> None:
        self.grid = grid
        self.mode = mode
        self._jump_calc = JumpConditionCalculator(
            max_order=2 if mode == "hermite" else 0
        )

    def compute_correction(
        self,
        L_sparse,
        phi: np.ndarray,
        kappa: np.ndarray,
        sigma: float,
        rho: np.ndarray,
        rhs: np.ndarray,
        dp_dx: np.ndarray | None = None,
        dp_dy: np.ndarray | None = None,
    ) -> np.ndarray:
        """Compute the IIM RHS correction vector Δq.

        Parameters
        ----------
        L_sparse : scipy.sparse matrix (n, n) — CCD operator (before pin)
        phi      : (Nx, Ny) — level-set signed distance (φ<0 = liquid)
        kappa    : (Nx, Ny) — interface curvature
        sigma    : surface tension coefficient
        rho      : (Nx, Ny) — density field
        rhs      : (Nx, Ny) — PPE RHS
        dp_dx    : (Nx, Ny) or None — pressure x-gradient (for hermite mode)
        dp_dy    : (Nx, Ny) or None — pressure y-gradient (for hermite mode)

        Returns
        -------
        delta_q : np.ndarray, shape (n,) — RHS correction (add to RHS)
        """
        if self.mode == "nearest":
            return self._correction_nearest(L_sparse, phi, kappa, sigma)
        else:
            return self._correction_hermite(
                L_sparse, phi, kappa, sigma, rho, rhs,
                dp_dx, dp_dy,
            )

    def _correction_nearest(
        self,
        L_sparse,
        phi: np.ndarray,
        kappa: np.ndarray,
        sigma: float,
    ) -> np.ndarray:
        """Vectorized zeroth-order IIM correction using only [p] = σκ.

        For each interface-crossing face, applies:
            Δq_L += L[L,R] · σκ   (liquid row)
            Δq_R -= L[R,L] · σκ   (gas row)

        Crossing detection and coefficient gathering are fully vectorized.
        Only the sparse element extraction uses a loop over O(N_Γ)
        crossing faces (typically N_Γ << N²).
        """
        return compute_nearest_stencil_correction(
            self.grid,
            L_sparse,
            phi,
            kappa,
            sigma,
        )

    def _correction_hermite(
        self,
        L_sparse,
        phi: np.ndarray,
        kappa: np.ndarray,
        sigma: float,
        rho: np.ndarray,
        rhs: np.ndarray,
        dp_dx: np.ndarray | None,
        dp_dy: np.ndarray | None,
    ) -> np.ndarray:
        """High-order IIM correction using C_0, C_1, C_2.

        For each interface crossing, computes the full jump condition
        vector and applies Hermite-weighted corrections that account
        for [p], [p'], and [p''] simultaneously.

        The correction at each crossing face uses the fractional
        position α = |φ_a|/(|φ_a|+|φ_b|) to weight the contributions.
        """
        return compute_hermite_stencil_correction(
            self.grid,
            self._jump_calc,
            L_sparse,
            phi,
            kappa,
            sigma,
            rho,
            rhs,
            dp_dx,
            dp_dy,
        )

    def find_interface_crossings(
        self,
        phi: np.ndarray,
    ) -> list[dict]:
        """Identify all grid faces where the interface crosses.

        Returns a list of crossing descriptors for diagnostics/testing.

        Parameters
        ----------
        phi : (Nx, Ny) level-set field

        Returns
        -------
        crossings : list of dict with keys:
            axis, idx_a, idx_b, alpha, phi_a, phi_b
        """
        return find_interface_crossings(phi)


_sparse_element = sparse_element
