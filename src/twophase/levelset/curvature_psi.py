"""
Direct curvature computation from CLS field psi (no logit inversion).

Implements section 3b (eq. curvature_psi_2d) of the paper.

By Theorem curvature_invariance (section 2.6), curvature is invariant
under monotonic reparametrisation:

    kappa = - [psi_y^2 psi_xx - 2 psi_x psi_y psi_xy + psi_x^2 psi_yy]
              / (psi_x^2 + psi_y^2)^{3/2}

yields the same result as the phi-based formula.  This eliminates:
  1. Logit inversion (avoids log singularity in saturation regions)
  2. Dependence on Eikonal condition |nabla phi| = 1
  3. Extra CCD differentiation pass on phi

Hybrid strategy (section 3b):
  - Near interface (psi_min < psi < 1 - psi_min): apply eq. curvature_psi_2d
  - Far from interface: kappa = 0 (no surface-tension contribution)

Symbol mapping (paper -> Python):
    psi           -> psi
    psi_x, psi_y  -> d1[0], d1[1]
    psi_xx, psi_yy-> d2[0], d2[1]
    psi_xy        -> psi_xy (mixed partial via sequential CCD)
    psi_min       -> psi_min (threshold, default 0.01)
    kappa         -> kappa (output curvature field)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

from .interfaces import ICurvatureCalculator
from .curvature import _dccd_filter_nd, _DCCD_EPS_D

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class CurvatureCalculatorPsi(ICurvatureCalculator):
    """Compute interface curvature kappa directly from CLS field psi.

    This is the recommended path per section 3b checklist:
    no logit inversion, no Eikonal dependence.

    Parameters
    ----------
    backend  : Backend
    ccd      : CCDSolver -- constructor injection (A3 traceability: eq.curvature_psi_2d)
    psi_min  : float -- threshold for interface region (default 0.01, section 3b)
    gaussian_filter : bool -- apply 3x3 Gaussian smoothing on kappa (section 3b line 286)
    dccd_eps : float -- DCCD filter strength for derivatives (0 = no filter, default 0.05)
    """

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        psi_min: float = 0.01,
        gaussian_filter: bool = False,
        dccd_eps: float = _DCCD_EPS_D,
    ):
        self.xp = backend.xp
        self.ccd = ccd
        self.psi_min = psi_min
        self.gaussian_filter = gaussian_filter
        self.dccd_eps = dccd_eps

    def compute(self, psi) -> "array":
        """Compute curvature field kappa directly from psi.

        Parameters
        ----------
        psi : array, shape ``grid.shape``, values in (0, 1)

        Returns
        -------
        kappa : array, same shape as psi
        """
        xp = self.xp
        ccd = self.ccd
        ndim = ccd.ndim
        psi = xp.asarray(psi)
        dccd_switch = (2.0 * psi - 1.0) ** 2 if self.dccd_eps > 0 else None

        # CCD derivatives of psi (O(h^6) accuracy) + optional DCCD filter
        d1 = []  # d psi / d x_i
        d2 = []  # d^2 psi / d x_i^2
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(psi, ax)
            if self.dccd_eps > 0:
                g1 = _dccd_filter_nd(
                    xp, g1, ccd.grid, self.dccd_eps, bc_type=ccd.bc_type,
                    switch=dccd_switch,
                )
                g2 = _dccd_filter_nd(
                    xp, g2, ccd.grid, self.dccd_eps, bc_type=ccd.bc_type,
                    switch=dccd_switch,
                )
            d1.append(g1)
            d2.append(g2)

        # |nabla psi|^2 and |nabla psi|^3
        grad_sq = sum(g * g for g in d1)

        if ndim == 2:
            kappa = self._kappa_2d(xp, d1, d2, ccd, psi, grad_sq, dccd_switch)
        else:
            kappa = self._kappa_3d(xp, d1, d2, ccd, psi, grad_sq)

        # Hybrid strategy: zero kappa far from interface (section 3b)
        far_mask = (psi <= self.psi_min) | (psi >= 1.0 - self.psi_min)
        kappa[far_mask] = 0.0

        # Optional Gaussian smoothing (section 3b line 286-288, G-3)
        if self.gaussian_filter and ndim == 2:
            kappa = _gaussian_3x3(xp, kappa)

        return kappa

    # -- 2-D formula (eq. curvature_psi_2d) --------------------------------

    def _kappa_2d(self, xp, d1, d2, ccd, psi, grad_sq, dccd_switch=None):
        """kappa = -[psi_y^2 psi_xx - 2 psi_x psi_y psi_xy + psi_x^2 psi_yy]
                    / (psi_x^2 + psi_y^2)^{3/2}
        """
        psi_x, psi_y = d1[0], d1[1]
        psi_xx = d2[0]
        psi_yy = d2[1]

        # Mixed derivative psi_xy via sequential CCD
        psi_xy, _ = ccd.differentiate(d1[0], 1)
        if self.dccd_eps > 0:
            psi_xy = _dccd_filter_nd(
                self.xp, psi_xy, ccd.grid, self.dccd_eps, bc_type=ccd.bc_type,
                switch=dccd_switch,
            )

        numerator = (psi_y**2 * psi_xx
                     - 2.0 * psi_x * psi_y * psi_xy
                     + psi_x**2 * psi_yy)

        # Safe denominator: use large eps where grad is near zero
        # (these points are masked to 0 by the hybrid strategy anyway)
        _EPS_GRAD = 1e-30
        grad_cube = (grad_sq + _EPS_GRAD) ** 1.5

        return -numerator / grad_cube

    # -- 3-D formula -------------------------------------------------------

    def _kappa_3d(self, xp, d1, d2, ccd, psi, grad_sq):
        """kappa = -(laplacian - (nabla_psi . H . nabla_psi) / |nabla_psi|^2)
                    / |nabla_psi|
        """
        lap = sum(d2)

        contracted = sum(d1[i] ** 2 * d2[i] for i in range(3))

        for i in range(3):
            for j in range(i + 1, 3):
                psi_ij, _ = ccd.differentiate(d1[i], j)
                contracted = contracted + 2.0 * d1[i] * d1[j] * psi_ij

        _EPS_GRAD = 1e-30
        grad_sq_safe = grad_sq + _EPS_GRAD
        grad_norm = xp.sqrt(grad_sq_safe)
        kappa = -(lap - contracted / grad_sq_safe) / grad_norm
        return kappa


def _gaussian_3x3(xp, field):
    """Apply 3x3 Gaussian smoothing filter (section 3b line 286-288).

    Kernel:
        [1  2  1]
        [2  4  2]  / 16
        [1  2  1]

    Boundary: replicate padding (Neumann-like).
    Only for 2D fields.
    """
    # Pad with replicate boundary
    padded = xp.pad(field, 1, mode='edge')

    # Convolution via shifted sums
    result = (
        1.0 * padded[:-2, :-2] + 2.0 * padded[:-2, 1:-1] + 1.0 * padded[:-2, 2:]
      + 2.0 * padded[1:-1, :-2] + 4.0 * padded[1:-1, 1:-1] + 2.0 * padded[1:-1, 2:]
      + 1.0 * padded[2:, :-2] + 2.0 * padded[2:, 1:-1] + 1.0 * padded[2:, 2:]
    ) / 16.0

    return result
