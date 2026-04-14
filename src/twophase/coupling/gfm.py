"""
Ghost Fluid Method (GFM) corrector for the PPE right-hand side.

Implements section 8.5 (sec:gfm) of the paper.

The GFM (Fedkiw 1999) treats the interface Gamma as a mathematical
discontinuity and embeds the Young-Laplace jump condition [p]_Gamma = kappa/We
directly into the PPE RHS vector, eliminating the CSF model error O(epsilon^2).

Ghost pressure substitution (Eq. gfm_ghost_p):

    p_tilde_{i+1}^ghost = p_{i+1} + kappa_f / We

PPE RHS correction (Eq. gfm_rhs_correction):

    b_i^GFM = b_i - (1/rho)_{i+1/2}^harm * kappa_f / (We * h^2)

where (1/rho)^harm = 2 / (rho_i + rho_{i+1}) is the harmonic-mean inverse
density at the interface face, and the sign follows the interface orientation
(phi_i > 0 vs phi_i < 0).  Applied independently per axis direction.

Symbol mapping (paper -> Python):
    phi      -> phi        signed-distance field
    kappa    -> kappa      curvature field
    rho      -> rho        density field
    We       -> We         Weber number
    h        -> h          grid spacing per axis
    kappa_f  -> kappa_f    face-interpolated curvature at interface
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


class GFMCorrector:
    """Compute GFM pressure-jump correction for the PPE RHS.

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    We      : float  — Weber number (We = rho_l U^2 L / sigma)

    Limitation: periodic BC wrap-around faces are not handled.  If the
    interface crosses the periodic domain boundary, the GFM correction at
    that face is missed.  This is acceptable for typical two-phase setups
    where the interface is fully contained within the domain.
    """

    def __init__(self, backend: "Backend", grid: "Grid", We: float):
        self.xp = backend.xp
        self.grid = grid
        self.ndim = grid.ndim
        self.We = We

    def compute_rhs_correction(
        self,
        phi: "array",
        kappa: "array",
        rho: "array",
    ) -> "array":
        """Compute the GFM correction term b^GFM for the PPE RHS.

        For each axis, detects interface-crossing faces (sign change in phi)
        and adds the pressure-jump correction (Eq. gfm_rhs_correction).

        Parameters
        ----------
        phi   : signed-distance field, shape ``grid.shape``
        kappa : curvature field, shape ``grid.shape``
        rho   : density field, shape ``grid.shape``

        Returns
        -------
        b_gfm : array, shape ``grid.shape`` — additive correction to PPE RHS
        """
        xp = self.xp
        We = self.We
        b_gfm = xp.zeros_like(phi)

        for ax in range(self.ndim):
            h = float(self.grid.L[ax] / self.grid.N[ax])
            h2 = h * h

            # Build slices for left (i) and right (i+1) nodes along axis ax
            # Interior faces: indices 0..N-1 paired with 1..N
            N_ax = self.grid.N[ax]
            sl_L = [slice(None)] * self.ndim
            sl_R = [slice(None)] * self.ndim
            sl_L[ax] = slice(0, N_ax)
            sl_R[ax] = slice(1, N_ax + 1)
            sl_L = tuple(sl_L)
            sl_R = tuple(sl_R)

            phi_L = phi[sl_L]
            phi_R = phi[sl_R]

            # Detect interface-crossing faces: sign(phi_L) != sign(phi_R)
            # Use strict inequality (< 0); phi = 0 exactly on a node is
            # measure-zero in floating-point and handled by the level-set
            # reinitialization which keeps the zero-crossing between nodes.
            crosses = (phi_L * phi_R) < 0.0

            if not xp.any(crosses):
                continue

            # Face-interpolated curvature: arithmetic mean (Eq. gfm_ghost_p)
            kappa_f = 0.5 * (kappa[sl_L] + kappa[sl_R])

            # Harmonic-mean inverse density at face (PPE operator consistency)
            # (1/rho)^harm = 2 / (rho_L + rho_R)
            rho_L = rho[sl_L]
            rho_R = rho[sl_R]
            inv_rho_f = 2.0 / (rho_L + rho_R)

            # Correction magnitude: (1/rho)^harm * kappa_f / (We * h^2)
            correction = inv_rho_f * kappa_f / (We * h2)

            # Sign convention (Eq. gfm_rhs_correction):
            #   Cell i (phi_i > 0, phase 1): b_i -= correction
            #   Cell i+1 (phi_{i+1} > 0, phase 1): b_{i+1} -= correction
            # The sign depends on which side is phase 1 (phi > 0).
            # For cell i where phi_L > 0: interface is to the right -> subtract
            # For cell i where phi_L < 0: interface is to the right -> add
            # This is equivalent to: sign = -sign(phi_L) applied to cell i,
            #                         sign = +sign(phi_L) applied to cell i+1
            sign_L = xp.where(phi_L > 0, -1.0, 1.0)

            # Apply correction to left cell (i)
            corr_L = xp.where(crosses, sign_L * correction, 0.0)
            # Apply correction to right cell (i+1) with opposite sign
            corr_R = xp.where(crosses, -sign_L * correction, 0.0)

            # Accumulate into b_gfm
            # Use slice-based accumulation (no scatter needed for structured grid)
            b_gfm[sl_L] = b_gfm[sl_L] + corr_L
            b_gfm[sl_R] = b_gfm[sl_R] + corr_R

        return b_gfm
