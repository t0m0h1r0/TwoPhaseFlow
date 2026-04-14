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


def ccd_pressure_gradient(ccd: "CCDSolver", p, ndim: int) -> List:
    """Return [∂p/∂x₀, ∂p/∂x₁, ...] via CCD with wall-Neumann zeroing.

    Used by both VelocityCorrector (§9 Step 7) and Predictor IPC term (§4).
    Wall-normal gradient components are zeroed to prevent IPC accumulation.
    """
    grad = []
    for ax in range(ndim):
        dp_dax, _ = ccd.differentiate(p, ax)
        ccd.enforce_wall_neumann(dp_dax, ax)
        grad.append(dp_dax)
    return grad


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
        grad_p = ccd_pressure_gradient(self.ccd, p, len(vel_star))
        return [vel_star[ax] - (dt / rho) * grad_p[ax] for ax in range(len(vel_star))]
