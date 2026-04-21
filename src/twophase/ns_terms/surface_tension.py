"""
Continuum Surface Force (CSF) model: κ ∇ψ / We.

Implements §2.3 (Eq. 21) and §9 of the paper.

The surface tension force in the balanced-force form is:

    f_σ = (1/We) κ ∇ψ                             (§2.3 Eq. 21)

where:
  κ = interface curvature (pre-computed by CurvatureCalculator)
  ψ = Conservative Level Set field (ψ ∈ [0, 1])
  We = Weber number = ρ_l U² L / σ

∇ψ acts as a regularised delta function (interface indicator).
The gradient is computed via CCD for O(h⁶) accuracy, consistent with
the curvature computation, which is critical for reducing parasitic currents
(§1, failure mode 1).

Note: this implementation returns the volume force density f_σ.
The predictor step then adds (Δt / ρ̃) * f_σ to the velocity.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .interfaces import INSTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from .context import NSComputeContext


class SurfaceTensionTerm(INSTerm):
    """CSF surface tension force κ ∇ψ / We.

    Parameters
    ----------
    backend : Backend
    We      : Weber number
    """

    def __init__(self, backend: "Backend", We: float):
        self.xp = backend.xp
        self.We = We

    def compute(self, ctx_or_kappa, psi=None, sigma=None, ccd=None, grad_op=None) -> List:
        """Compute f_σ = κ ∇ψ / We.

        Supports both new (ctx) and legacy (kappa, psi, sigma, ccd) signatures.
        R-1.5: grad_op parameter allows FVM-consistent ∇ψ on non-uniform grids.

        Parameters
        ----------
        ctx_or_kappa : NSComputeContext or ndarray
            Either NSComputeContext (new) or kappa field (legacy)
        psi : ndarray, optional
            Only used with legacy signature
        sigma : float, optional
            Surface tension coefficient (legacy signature, for compatibility)
        ccd : CCDSolver, optional
            Only used with legacy signature
        grad_op : IGradientOperator, optional
            Gradient operator for computing ∇ψ (R-1.5). If provided on
            non-uniform grid, uses FVM-consistent gradient instead of CCD.

        Returns
        -------
        f_sigma : list of arrays, one per spatial dimension
        """
        # Dispatch based on argument type
        if psi is not None and ccd is not None:
            # Legacy signature: compute(kappa, psi, sigma, ccd, grad_op=None)
            kappa = ctx_or_kappa
        else:
            # New signature: compute(ctx)
            ctx = ctx_or_kappa
            kappa = ctx.kappa
            psi = ctx.psi
            ccd = ctx.ccd

        xp = self.xp
        We = self.We
        ndim = ccd.ndim
        result = []

        for ax in range(ndim):
            # R-1.5: Use grad_op (FVM) if available, else CCD (legacy)
            if grad_op is not None:
                dpsi_dax = grad_op.gradient(psi, ax)
            else:
                dpsi_dax, _ = ccd.differentiate(psi, ax)
            result.append(kappa * dpsi_dax / We)

        return result
