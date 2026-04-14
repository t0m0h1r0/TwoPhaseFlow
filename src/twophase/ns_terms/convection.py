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


class ConvectionTerm(INSTerm):
    """Computes −(u·∇)u for all velocity components.

    Parameters
    ----------
    backend : Backend
    """

    def __init__(self, backend: "Backend"):
        self.xp = backend.xp

    def compute(self, velocity_components: List, ccd: "CCDSolver") -> List:
        """
        Parameters
        ----------
        velocity_components : list of arrays [u, v[, w]], shape ``grid.shape``
        ccd                 : CCDSolver

        Returns
        -------
        conv : list of arrays, same shapes — convective acceleration per component
        """
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
