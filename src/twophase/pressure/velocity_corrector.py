"""
Velocity corrector: u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}.

Implements Step 7 of the full algorithm (§9.1 Eq. 93) of the paper.

After solving the PPE for p^{n+1}, the divergence-free velocity is
recovered by subtracting the pressure gradient:

    u^{n+1} = u* − (Δt / ρ̃^{n+1}) ∇p^{n+1}           (§9.1 Eq. 93)

Spatial gradients are computed via O(h²) central FD, consistent with
the FVM PPE operator (PPESolverLU / PPEBuilder).  Using CCD here while
the PPE uses FVM breaks the balanced-force condition, driving parasitic
currents.  FD/FVM consistency keeps the mismatch at O(h²).

Boundary nodes: Neumann ∂p/∂n = 0 → gradient = 0.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid


class VelocityCorrector:
    """Apply pressure-gradient correction to u*.

    Parameters
    ----------
    backend : Backend
    grid    : Grid — needed for cell spacing h
    """

    def __init__(self, backend: "Backend", grid: "Grid"):
        self.xp = backend.xp
        self.grid = grid

    def correct(
        self,
        vel_star: List,
        p: "array",
        rho: "array",
        dt: float,
    ) -> List:
        """Return u^{n+1} = u* − (Δt/ρ̃) ∇p.

        Parameters
        ----------
        vel_star : list of u* arrays
        p        : pressure field p^{n+1}
        rho      : density field ρ̃^{n+1}
        dt       : time step

        Returns
        -------
        vel_new : corrected velocity list
        """
        ndim = len(vel_star)
        vel_new = []
        for ax in range(ndim):
            dp_dax = self._fd_gradient(p, ax)
            vel_new.append(vel_star[ax] - (dt / rho) * dp_dax)
        return vel_new

    # ── private ───────────────────────────────────────────────────────────

    def _fd_gradient(self, p, ax: int):
        """O(h²) central-difference gradient along ax.

        Interior nodes k = 1..N-1: (p[k+1] - p[k-1]) / (2h).
        Boundary nodes k = 0, N: zero (Neumann ∂p/∂n = 0).
        """
        xp = self.xp
        h = float(self.grid.L[ax] / self.grid.N[ax])
        grad = xp.zeros_like(p)
        sl_hi  = [slice(None)] * p.ndim
        sl_lo  = [slice(None)] * p.ndim
        sl_int = [slice(None)] * p.ndim
        sl_hi[ax]  = slice(2, None)
        sl_lo[ax]  = slice(0, -2)
        sl_int[ax] = slice(1, -1)
        grad[tuple(sl_int)] = (
            (p[tuple(sl_hi)] - p[tuple(sl_lo)]) / (2.0 * h)
        )
        return grad
