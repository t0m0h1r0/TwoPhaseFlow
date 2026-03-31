"""
PPE RHS builder for the GFM + DCCD-decoupling pipeline.

Implements Eq. gfm_ccd_div (section 8.5) of the paper:

    q_h = (1/dt) * (D_x^(1) u_tilde* + D_y^(1) v_tilde*) + b^GFM

where:
  - u_tilde*, v_tilde* are DCCD-filtered predicted velocities
    (sec:dccd_decoupling, Eq. dccd_ppe_rhs)
  - b^GFM is the GFM interface pressure-jump correction
    (sec:gfm, Eq. gfm_rhs_correction)
  - D_x^(1), D_y^(1) are CCD 1st-derivative operators

This replaces the Rhie-Chow face-velocity divergence used in the CSF path.
Rhie-Chow interpolation is NOT needed when GFM + DCCD-decoupling is active,
because:
  1. CSF volume forces are removed from the predictor (sec:gfm)
  2. Checkerboard suppression is handled by the DCCD filter (eps_d=1/4)

Symbol mapping (paper -> Python):
    q_h       -> rhs          complete PPE RHS
    u_tilde*  -> vel_filtered  DCCD-filtered velocity
    b^GFM     -> b_gfm        GFM correction from GFMCorrector
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .gfm import GFMCorrector
    from .dccd_ppe_filter import DCCDPPEFilter


class PPERHSBuilderGFM:
    """Build PPE RHS using DCCD-filtered CCD divergence + GFM correction.

    Parameters
    ----------
    dccd_filter : DCCDPPEFilter — velocity filter + CCD divergence
    gfm         : GFMCorrector  — interface pressure-jump correction
    """

    def __init__(
        self,
        dccd_filter: "DCCDPPEFilter",
        gfm: "GFMCorrector",
    ):
        self.dccd_filter = dccd_filter
        self.gfm = gfm

    def build_rhs(
        self,
        vel_star: List,
        phi: "array",
        kappa: "array",
        rho: "array",
        dt: float,
    ) -> "array":
        """Compute the complete PPE RHS for the GFM pipeline.

        Implements Eq. gfm_ccd_div:
            q_h = (1/dt) * div(u_tilde*) + b^GFM

        Parameters
        ----------
        vel_star : list of predicted velocity arrays (u*, v*, ...)
        phi      : signed-distance field
        kappa    : curvature field
        rho      : density field
        dt       : time step

        Returns
        -------
        rhs : array, shape ``grid.shape`` — PPE RHS
        """
        # DCCD-filtered CCD divergence (Eq. dccd_ppe_rhs)
        div_filtered = self.dccd_filter.compute_filtered_divergence(vel_star)

        # GFM correction (Eq. gfm_rhs_correction)
        b_gfm = self.gfm.compute_rhs_correction(phi, kappa, rho)

        # Complete RHS (Eq. gfm_ccd_div)
        rhs = div_filtered / dt + b_gfm

        return rhs
