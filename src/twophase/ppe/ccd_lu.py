"""
CCD PPE solver — always-direct sparse LU (spsolve / SuperLU).

Shares the CCD Kronecker-product operator (L_CCD^ρ) with
PPESolverPseudoTime via the common base class _CCDPPEBase, but skips
the iterative phase and solves directly every step.

Uses:
    - Debugging / reference solutions (force direct LU, ppe_solver_type="ccd_lu")
    - Verifying balanced-force compliance (CCD PPE + CCD corrector consistency)
    - Cases where a guaranteed-accurate baseline is preferred over speed

Operator (identical to PPESolverPseudoTime):
    (L_CCD^ρ p)_{i,j}
        = (1/ρ)(D_x^{(2)}p + D_y^{(2)}p)
          − (D_x^{(1)}ρ / ρ²) D_x^{(1)}p
          − (D_y^{(1)}ρ / ρ²) D_y^{(1)}p

Architecture:
    Inherits _CCDPPEBase — only _solve_linear_system is overridden (OCP).
    No code is duplicated from PPESolverPseudoTime.
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver

from .ccd_ppe_base import _CCDPPEBase


class PPESolverCCDLU(_CCDPPEBase):
    """CCD Kronecker-product operator + always-direct LU (SuperLU).

    NS role
    -------
    Solves the variable-density PPE at Step 6 (§9.1 algorithm):

        ∇·[(1/ρ̃) ∇p] = (1/Δt) ∇·u*

    so that Step 7 corrector recovers divergence-free velocity:

        u^{n+1} = u* − (Δt/ρ̃) ∇p^{n+1}

    Discretisation: CCD Kronecker O(h⁶) + sparse direct LU.
    Use: ch11 smooth-RHS tests (PR-2).

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig
    grid    : Grid
    ccd     : CCDSolver (constructor injection; auto-built if None)
    """

    def _solve_linear_system(
        self,
        L_pinned,
        rhs_np: np.ndarray,
        p0: np.ndarray,
    ) -> np.ndarray:
        """Solve via sparse direct LU (spsolve).

        ``p0`` (warm-start guess) is accepted for interface compatibility
        but ignored — direct solvers do not use an initial guess.

        Runs on the active device via :meth:`_CCDPPEBase._spsolve`:
        scipy on CPU, cupyx.scipy on GPU.
        """
        return self._spsolve(L_pinned, rhs_np)
