"""
CCD sparse PPE solver — base class + LGMRES iterative variant.

Solves the variable-density Pressure Poisson Equation:

    ∇·(1/ρ ∇p) = q_h,   q_h = (1/Δt) ∇·u*_RC

using the 6th-order CCD product-rule operator (§8b Eq. L_CCD_2d_full):

    (L_CCD^ρ p)_{i,j}
        = (1/ρ)(D_x^{(2)}p + D_y^{(2)}p)
          − (D_x^{(1)}ρ / ρ²) D_x^{(1)}p
          − (D_y^{(1)}ρ / ρ²) D_y^{(1)}p         (§8b Eq. Lx_varrho_discrete)

The CCD 1st/2nd derivative matrices (per axis) are built once via a single
batched CCD call on the identity matrix, then assembled into the 2D operator
via Kronecker products (scipy.sparse.kron) — see app:ccd_kronecker.

Architecture (Template Method pattern, OCP + SRP):
  _CCDPPEBase(IPPESolver) — shared matrix assembly + solve template:
      • _build_1d_ccd_matrices()  — precomputed once in __init__
      • _build_sparse_operator()  — Kronecker product L_CCD^ρ
      • _assemble_pinned_system() — operator + pin + RHS preparation
      • solve()                   — template: assemble → _solve_linear_system
      • compute_residual()        — diagnostic
      • _solve_linear_system()    — abstract; subclasses provide solve strategy

  PPESolverPseudoTime(_CCDPPEBase):
      LGMRES iterative solver (O(n·k) memory, warm start).  Returns
      the best iterate when LGMRES does not converge (no LU fallback).

  PPESolverCCDLU(_CCDPPEBase)  [ppe_solver_ccd_lu.py]:
      Always-direct sparse LU (spsolve / SuperLU); no iterative phase.

Adding a new solve strategy requires only implementing _solve_linear_system
in a new subclass — no changes to base or factory (OCP).

IPC integration (§4 sec:ipc_derivation):
    Caller passes δp ≡ p^{n+1}−p^n as the unknown (p_init=None → zeros).
    The operator and BC are identical to the absolute-pressure formulation;
    only the unknown variable changes.

Boundary conditions:
    Neumann ∂p/∂n = 0 at all walls: satisfied through the Rhie-Chow RHS
    and velocity BC.  One interior node is pinned to zero to fix the null
    space: the center node (N//2, N//2) is pinned — invariant under all
    square-domain symmetry operations (x-flip, y-flip, diagonal swap).

Refactoring notes:
    2026-03-20: Replaces FVM+MINRES and GMRES matrix-free implementations.
                Accepts ``ccd`` via constructor injection (DIP).
    2026-03-21: Added Kronecker product matrix assembly (app:ccd_kronecker).
                Switched from LU-only to LGMRES-primary / LU-fallback.
    2026-04-01: Removed LU fallback — LGMRES returns best iterate on
                non-convergence.  Paper alignment (§app:ccd_lu_direct).
    2026-03-22: Pin moved from corner (0,0) to center (N//2,N//2) to
                avoid symmetry breaking.
    2026-03-22: Extracted _CCDPPEBase (Template Method); PPESolverCCDLU
                now inherits _CCDPPEBase directly (OCP, SRP, DRY).
"""

from __future__ import annotations
import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Backward-compat re-export (A7): _CCDPPEBase moved to ccd_ppe_base.py
from .ccd_ppe_base import _CCDPPEBase  # noqa: F401


# DO NOT DELETE — passed tests 2026-03-27
# Superseded by: PPESolverCCDLU in ppe_solver_ccd_lu.py
# Retained for: cross-validation baseline; warm-start research
# Violation: PR-6 (uses LGMRES, prohibited for PPE)
class PPESolverPseudoTime(_CCDPPEBase):
    """CCD variable-density PPE solver — LGMRES iterative (O(h⁶)).

    Legacy: violates PR-6 (LGMRES prohibited for PPE).
    Use PPESolverCCDLU for production.

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig  (pseudo_tol, pseudo_maxiter)
    grid    : Grid
    ccd     : CCDSolver  (constructor injection; auto-built if None)
    """

    def _solve_linear_system(
        self,
        L_pinned,
        rhs_np: np.ndarray,
        p0: np.ndarray,
    ) -> np.ndarray:
        """LGMRES iterative solve (O(n·k) memory), no LU fallback.

        The CCD operator is highly asymmetric (max asymmetry ~900 for N=16)
        due to compact one-sided boundary schemes; standard GMRES diverges on
        some grids.  LGMRES (augmented Krylov) is more robust.  When LGMRES
        does not converge within maxiter, the best iterate is returned with
        a warning — no direct-solver fallback.

        atol: fp64 floor prevents spurious non-convergence when ‖rhs‖ is tiny
        (e.g. immediately after initialisation).  See KL-09 (docs/LESSONS.md).
        """
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
                f"CCD-PPE LGMRES が収束しませんでした (info={info}, "
                f"maxiter={self.maxiter}, tol={self.tol})。"
                " 最良反復解を返します。",
                RuntimeWarning,
                stacklevel=2,
            )

        return p_flat
