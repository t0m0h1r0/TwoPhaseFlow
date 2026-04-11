"""
Operator-split reinitialization: compression (FE) + diffusion (CN-ADI).

Implements the scheme from §5c (alg:cls_reinit_dccd).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple

from ..interfaces.levelset import IReinitializer
from .heaviside import apply_mass_correction
from .reinit_ops import (
    compute_dtau, dccd_compression_div, cn_diffusion_axis, build_cn_factors,
)

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class SplitReinitializer(IReinitializer):
    """Operator-split reinitialization: compression (FE) + diffusion (CN-ADI).

    Parameters
    ----------
    backend, grid, ccd, eps, n_steps, bc, eps_d_comp, mass_correction
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero',
                 eps_d_comp: float = 0.05,
                 mass_correction: bool = True):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.n_steps = n_steps
        self._bc = bc
        self._eps_d_comp = float(eps_d_comp)
        self._mass_correction = mass_correction
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]
        self.dtau = compute_dtau(grid, eps)

        self._cn_factors: List[Tuple] = []
        for ax in range(grid.ndim):
            self._cn_factors.append(
                build_cn_factors(grid, eps, self.dtau, ax, backend))

        self._dV = self.xp.asarray(grid.cell_volumes())

    def reinitialize(self, psi):
        xp = self.xp
        # Ensure psi is on the correct device (no-op on CPU).
        q = xp.asarray(psi).copy()
        dV = self._dV
        M_old = xp.sum(q * dV)

        for _ in range(self.n_steps):
            div_comp = dccd_compression_div(
                xp, q, self.ccd, self.grid, self._bc, self._eps_d_comp,
            )
            q_star = xp.clip(q - self.dtau * div_comp, 0.0, 1.0)

            q_new = q_star
            for ax in range(self.grid.ndim):
                q_new = cn_diffusion_axis(
                    xp, q_new, ax, self.eps, self.dtau,
                    self._h[ax], self._cn_factors[ax],
                )
            q = xp.clip(q_new, 0.0, 1.0)

        if self._mass_correction:
            q = apply_mass_correction(xp, q, dV, M_old)

        return q
