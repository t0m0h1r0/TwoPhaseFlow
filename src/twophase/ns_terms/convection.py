"""
Convection term: −(u·∇)u.

Implements the inertia contribution to the momentum equation (§9 Eq. 85).

In component form (e.g., x-momentum):

    [−(u·∇)u]_x = −u ∂u/∂x − v ∂u/∂y [− w ∂u/∂z]

Spatial derivatives are computed via CCD (6th-order).
The result is an array of shape ``grid.shape`` for each velocity component.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .interfaces import INSTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from .context import NSComputeContext


class ConvectionTerm(INSTerm):
    """Computes −(u·∇)u for all velocity components.

    Parameters
    ----------
    backend : Backend
    """

    def __init__(self, backend: "Backend"):
        self.xp = backend.xp

    def compute(self, ctx_or_velocity, ccd=None) -> List:
        """Compute convection term −(u·∇)u.

        Supports both new (ctx) and legacy (velocity, ccd) signatures.

        Parameters
        ----------
        ctx_or_velocity : NSComputeContext or list
            Either NSComputeContext (new) or velocity_components list (legacy)
        ccd : CCDSolver, optional
            Only used with legacy signature

        Returns
        -------
        List[ndarray]
            Convective acceleration per velocity component
        """
        # Dispatch based on argument type
        if ccd is not None:
            # Legacy signature: compute(velocity_components, ccd)
            velocity_components = ctx_or_velocity
        else:
            # New signature: compute(ctx)
            ctx = ctx_or_velocity
            velocity_components = ctx.velocity
            ccd = ctx.ccd

        xp = self.xp
        ndim = len(velocity_components)
        result = []

        for comp in range(ndim):
            u_comp = velocity_components[comp]
            acc = xp.zeros_like(u_comp)
            for ax in range(ndim):
                du_dax, _ = ccd.differentiate(u_comp, ax)
                acc -= velocity_components[ax] * du_dax
            result.append(acc)

        return result
