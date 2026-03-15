"""
Velocity corrector: u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}.

Implements Step 7 of the full algorithm (§9.1 Eq. 93) of the paper.

After solving the PPE for p^{n+1}, the divergence-free velocity is
recovered by subtracting the pressure gradient:

    u^{n+1} = u* − (Δt / ρ̃^{n+1}) ∇p^{n+1}           (§9.1 Eq. 93)

Spatial gradients are computed via CCD (6th-order).
The result satisfies ∇·u^{n+1} = 0 to within the PPE solver tolerance.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class VelocityCorrector:
    """Apply pressure-gradient correction to u*.

    Parameters
    ----------
    backend : Backend
    """

    def __init__(self, backend: "Backend"):
        self.xp = backend.xp

    def correct(
        self,
        vel_star: List,
        p: "array",
        rho: "array",
        ccd: "CCDSolver",
        dt: float,
    ) -> List:
        """Return u^{n+1} = u* − (Δt/ρ̃) ∇p.

        Parameters
        ----------
        vel_star : list of u* arrays
        p        : pressure field p^{n+1}
        rho      : density field ρ̃^{n+1}
        ccd      : CCDSolver for ∇p
        dt       : time step

        Returns
        -------
        vel_new : corrected velocity list
        """
        ndim = len(vel_star)
        vel_new = []
        for ax in range(ndim):
            dp_dax, _ = ccd.differentiate(p, ax)
            vel_new.append(vel_star[ax] - (dt / rho) * dp_dax)
        return vel_new
