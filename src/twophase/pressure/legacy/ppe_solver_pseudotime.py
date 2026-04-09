"""
CCD sparse PPE solver — LGMRES iterative variant.

# DO NOT DELETE — passed tests 2026-03-27
# Superseded by: PPESolverCCDLU in ppe_solver_ccd_lu.py
# Retained for: cross-validation baseline; warm-start research
# Violation: PR-6 (uses LGMRES, prohibited for PPE)
# Registered: docs/01_PROJECT_MAP.md §8
"""

from __future__ import annotations
import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Backward-compat re-export (A7): _CCDPPEBase moved to ccd_ppe_base.py
from ..ccd_ppe_base import _CCDPPEBase  # noqa: F401


class PPESolverPseudoTime(_CCDPPEBase):
    """CCD variable-density PPE solver — LGMRES iterative (O(h^6)).

    Legacy: violates PR-6 (LGMRES prohibited for PPE).
    Use PPESolverCCDLU for production.
    """

    def _solve_linear_system(
        self,
        L_pinned,
        rhs_np: np.ndarray,
        p0: np.ndarray,
    ) -> np.ndarray:
        import scipy.sparse.linalg as spla

        atol = max(1e-14, self.tol * float(np.linalg.norm(rhs_np)))
        p_flat, info = spla.lgmres(
            L_pinned, rhs_np,
            x0=p0,
            rtol=self.tol,
            maxiter=self.maxiter,
            atol=atol,
        )

        if info != 0:
            warnings.warn(
                f"CCD-PPE LGMRES did not converge (info={info}, "
                f"maxiter={self.maxiter}, tol={self.tol}). "
                "Returning best iterate.",
                RuntimeWarning,
                stacklevel=2,
            )

        return p_flat
