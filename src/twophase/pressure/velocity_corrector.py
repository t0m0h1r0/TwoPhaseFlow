"""
Velocity corrector: u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}.

Implements Step 7 of the full algorithm (§9.1 Eq. 93) of the paper.

After solving the PPE for p^{n+1}, the divergence-free velocity is
recovered by subtracting the pressure gradient:

    u^{n+1} = u* − (Δt / ρ̃^{n+1}) (D^{(1)} δp)^{n+1}    (§9.1 Eq. 93)

Spatial gradients are computed via CCD D^{(1)} (O(h⁶)) in the interior,
consistent with the surface-tension term (κ D^{(1)} ψ / We) in the
predictor.  Using the same CCD operator for ∇(δp) and ∇ψ satisfies the
balanced-force condition (§7 warnbox), reducing parasitic currents from
O(h²) to O(h⁶) in the interior.

Boundary (wall) treatment:
    The PPE Neumann condition ∂p/∂n = 0 is enforced explicitly at wall
    nodes: after computing the CCD gradient, the wall-normal component at
    boundary planes is set to zero.  This prevents a positive-feedback loop
    where each IPC step accumulates a nonzero wall pressure gradient (the
    CCD one-sided boundary stencil gives ∂p/∂n ≠ 0 when the FVM PPE does
    not enforce Neumann BC in the CCD sense).  The interior gradient is
    unaffected and remains O(h⁶) accurate.

    For periodic BC the CCD periodic solver handles the gradient correctly
    and no explicit zeroing is needed.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver


class VelocityCorrector:
    """Apply pressure-gradient correction to u*.

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver — CCD D^{(1)} operator for ∇(δp) (balanced-force)
    """

    def __init__(self, backend: "Backend", grid: "Grid", ccd: "CCDSolver"):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd

    def correct(
        self,
        vel_star: List,
        p: "array",
        rho: "array",
        dt: float,
    ) -> List:
        """Return u^{n+1} = u* − (Δt/ρ̃) D^{(1)} p.

        Parameters
        ----------
        vel_star : list of u* arrays
        p        : pressure field p^{n+1} (or δp for IPC)
        rho      : density field ρ̃^{n+1}
        dt       : time step

        Returns
        -------
        vel_new : corrected velocity list
        """
        ndim = len(vel_star)
        vel_new = []
        for ax in range(ndim):
            dp_dax, _ = self.ccd.differentiate(p, ax)
            if self.ccd.bc_type == "wall":
                self._enforce_neumann(dp_dax, ax)
            vel_new.append(vel_star[ax] - (dt / rho) * dp_dax)
        return vel_new

    # ── private ───────────────────────────────────────────────────────────

    def _enforce_neumann(self, grad, ax: int) -> None:
        """Zero CCD gradient at wall boundaries (Neumann BC: ∂p/∂n = 0).

        The FVM PPE enforces Neumann BC via zero wall-face flux, but the
        CCD one-sided boundary stencil gives a nonzero wall gradient.
        Explicitly zeroing it is consistent with the physical BC and
        prevents a growing feedback loop through the IPC pressure term.
        """
        sl_lo = [slice(None)] * grad.ndim
        sl_hi = [slice(None)] * grad.ndim
        sl_lo[ax] = 0
        sl_hi[ax] = -1
        grad[tuple(sl_lo)] = 0.0
        grad[tuple(sl_hi)] = 0.0
