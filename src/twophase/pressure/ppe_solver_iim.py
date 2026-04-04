"""
IIM-CCD PPE solver — Immersed Interface Method correction for CCD operator.

Motivation
----------
The standard CCD PPE operator (L^ρ p = q) assumes p is smooth everywhere.
When pressure jumps at the interface (GFM: [p] = σκ ≠ 0), near-interface
stencils mix Phase-1 and Phase-2 pressure values, producing an O([p]/h²)
discretisation error that dominates and causes time-marching instability.

Key idea (IIM, LeVeque & Li 1994 applied to the CCD operator)
------------------------------------------------------------
For a Phase-1 cell (φ < 0) whose stencil touches Phase-2 cells (φ_k > 0):
the CCD equation uses p_k^+ (gas pressure), but the Phase-1 equation should
use p_k^- = p_k^+ − [p] = p_k^+ − σκ.  Moving the discrepancy to the RHS:

    L^ρ p = q + Δq,

    Δq_i = +σκ_i · Σ_{k: φ_k > 0} L^ρ_{i,k}     (Phase-1 rows)
    Δq_i = −σκ_i · Σ_{k: φ_k < 0} L^ρ_{i,k}     (Phase-2 rows)

In matrix-vector form (eq. 6 of iim_ccd_note.tex):

    Δq = σκ ⊙ [m⁻ ⊙ (L^ρ m⁺) − m⁺ ⊙ (L^ρ m⁻)]

where m⁺ = (φ > 0), m⁻ = (φ < 0) as float vectors.

This correction requires only one sparse matrix-vector product and no
modification of L^ρ itself.  Only the zeroth-order jump [p] = σκ is used
(first-order [p'_n] correction deferred to future work).

Architecture
------------
PPESolverIIM(_CCDPPEBase):
    Inherits Kronecker-product operator assembly from _CCDPPEBase (OCP).
    Overrides solve() to accept phi, kappa, sigma as optional kwargs.
    Falls back to standard CCD-LU when phi is None (sigma=0 or no interface).
    solve strategy: always-direct sparse LU (same as PPESolverCCDLU).

Usage
-----
    solver = PPESolverIIM(backend, config, grid, ccd=ccd)
    p = solver.solve(rhs, rho, dt, phi=phi, kappa=kappa, sigma=sigma)

    # Without correction (behaves identically to PPESolverCCDLU):
    p = solver.solve(rhs, rho, dt)
"""

from __future__ import annotations
import warnings
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver

from .ppe_solver_pseudotime import _CCDPPEBase


class PPESolverIIM(_CCDPPEBase):
    """CCD Kronecker-product PPE solver with IIM interface correction.

    Extends the standard CCD-LU solver by adding the zeroth-order IIM
    correction Δq = σκ ⊙ [m⁻ ⊙ (L m⁺) − m⁺ ⊙ (L m⁻)] to the RHS
    before solving, so that the pressure jump [p] = σκ is correctly
    accounted for without modifying the operator or falling back to FD.

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig
    grid    : Grid
    ccd     : CCDSolver (constructor injection; auto-built if None)
    """

    # ── IPPESolver interface ──────────────────────────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
        *,
        phi=None,
        kappa=None,
        sigma: float = 0.0,
    ):
        """Solve PPE with optional IIM correction.

        Parameters
        ----------
        rhs    : array, shape grid.shape — RHS (1/Δt) ∇·u*_RC
        rho    : array, shape grid.shape — density field
        dt     : float — time step (passed through for LSP; unused by direct LU)
        p_init : optional warm-start (ignored by direct LU; accepted for LSP)
        phi    : optional array, shape grid.shape — level-set φ (signed distance)
                 Required for IIM correction; if None the correction is skipped.
        kappa  : optional array, shape grid.shape — interface curvature κ
                 Required for IIM correction; if None the correction is skipped.
        sigma  : float — surface tension coefficient σ (dimensional)
                 If 0.0 the correction is skipped even when phi/kappa are given.

        Returns
        -------
        p : array, shape grid.shape
        """
        shape = self.grid.shape
        n = int(np.prod(shape))

        # Step 1: build variable-density CCD operator L^ρ (before pin)
        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        xp = self.xp
        drho_np = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(xp.asarray(rho_np), ax)
            drho_np.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))
        L_sparse = self._build_sparse_operator(rho_np, drho_np)

        # Step 2: base RHS
        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float).ravel()

        # Step 3: IIM correction Δq
        if phi is not None and kappa is not None and sigma > 0.0:
            delta_q = self._compute_iim_correction(phi, kappa, sigma, L_sparse)
            rhs_np = rhs_np + delta_q

        # Step 4: pin centre node (gauge fix)
        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, self.grid.shape))
        import scipy.sparse as sp
        L_lil = L_sparse.tolil()
        L_lil[pin_dof, :] = 0.0
        L_lil[pin_dof, pin_dof] = 1.0
        L_pinned = L_lil.tocsr()
        rhs_np[pin_dof] = 0.0

        # Step 5: direct LU solve
        p0 = (
            np.asarray(self.backend.to_host(p_init), dtype=float).ravel()
            if p_init is not None
            else np.zeros(n)
        )
        p_flat = self._solve_linear_system(L_pinned, rhs_np, p0)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                f"{type(self).__name__}: solver returned non-finite values.",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.backend.to_device(p_flat.reshape(shape))

    # ── Abstract method implementation (direct LU) ────────────────────

    def _solve_linear_system(
        self,
        L_pinned,
        rhs_np: np.ndarray,
        p0: np.ndarray,
    ) -> np.ndarray:
        """Direct LU solve (spsolve / SuperLU).

        p0 is accepted for LSP compliance but ignored by direct solvers.
        """
        import scipy.sparse.linalg as spla
        return spla.spsolve(L_pinned, rhs_np)

    # ── IIM correction ────────────────────────────────────────────────

    def _compute_iim_correction(
        self,
        phi,
        kappa,
        sigma: float,
        L_sparse,
    ) -> np.ndarray:
        """Compute IIM RHS correction using direct (nearest-neighbour) stencil.

        Derivation (iim_ccd_note.tex §2):
          For a Phase-1 cell (i,j) whose immediate neighbour (i±1,j) or (i,j±1)
          is in Phase 2, the CCD D2 stencil term L[(i,j),(i±1,j)] * p_(i±1,j)
          uses Phase-2 pressure but should use Phase-1.
          Correction: add L[(i,j),(nbr)] * [p] to RHS at (i,j), where [p] = σκ.

        Only immediate face-neighbours are corrected (nearest-neighbour IIM).
        This avoids the non-local artefacts that arise when using L @ mask_phase,
        since the CCD D2 matrix is effectively dense (block-tridiagonal solve).

        Parameters
        ----------
        phi      : array, shape grid.shape — level-set (φ > 0 = gas)
        kappa    : array, shape grid.shape — curvature (κ > 0 inside bubble)
        sigma    : float — surface tension coefficient
        L_sparse : scipy sparse (n×n) — assembled L^ρ before pin

        Returns
        -------
        delta_q : np.ndarray, shape (n,) — RHS correction
        """
        import scipy.sparse as sp

        phi_np  = np.asarray(self.backend.to_host(phi),   dtype=float)
        kap_np  = np.asarray(self.backend.to_host(kappa), dtype=float)
        shape   = self.grid.shape       # (Nx, Ny)
        Nx, Ny  = shape
        n       = Nx * Ny

        phi_flat = phi_np.ravel()
        kap_flat = kap_np.ravel()
        delta_q  = np.zeros(n)

        # Convert L to LIL for O(1) row access
        L_lil = L_sparse.tolil()

        # ── x-direction crossings ────────────────────────────────────────────
        # Face between (i,j) and (i+1,j): crossing when sign(φ) differs
        for i in range(Nx - 1):
            for j in range(Ny):
                idx_L = i * Ny + j        # flat index of left cell  (i,  j)
                idx_R = (i + 1) * Ny + j  # flat index of right cell (i+1,j)
                phi_L = phi_flat[idx_L]
                phi_R = phi_flat[idx_R]
                if phi_L * phi_R >= 0.0:
                    continue              # same phase — no crossing

                # Average curvature at the interface crossing
                # (use harmonic mean so kappa at exact zero-crossing is smooth)
                abs_L = abs(phi_L); abs_R = abs(phi_R)
                kap_iface = (abs_R * kap_flat[idx_L] + abs_L * kap_flat[idx_R]) / (abs_L + abs_R + 1e-30)
                jump = sigma * kap_iface   # [p] = σκ

                # Determine which cell is Phase 1 (liquid, φ<0) and Phase 2 (gas, φ>0)
                # Phase-1 cell's equation uses Phase-2 neighbour → +jump correction
                # Phase-2 cell's equation uses Phase-1 neighbour → -jump correction
                if phi_L < 0.0:
                    # Left = liquid (Ph1), Right = gas (Ph2)
                    L_coeff = float(L_lil[idx_L, idx_R])   # L[(i,j),(i+1,j)]
                    R_coeff = float(L_lil[idx_R, idx_L])   # L[(i+1,j),(i,j)]
                    delta_q[idx_L] += + L_coeff * jump
                    delta_q[idx_R] += - R_coeff * jump
                else:
                    # Left = gas (Ph2), Right = liquid (Ph1)
                    L_coeff = float(L_lil[idx_L, idx_R])
                    R_coeff = float(L_lil[idx_R, idx_L])
                    delta_q[idx_L] += - L_coeff * jump
                    delta_q[idx_R] += + R_coeff * jump

        # ── y-direction crossings ────────────────────────────────────────────
        for i in range(Nx):
            for j in range(Ny - 1):
                idx_B = i * Ny + j        # flat index of bottom cell (i, j  )
                idx_T = i * Ny + (j + 1)  # flat index of top cell    (i, j+1)
                phi_B = phi_flat[idx_B]
                phi_T = phi_flat[idx_T]
                if phi_B * phi_T >= 0.0:
                    continue

                abs_B = abs(phi_B); abs_T = abs(phi_T)
                kap_iface = (abs_T * kap_flat[idx_B] + abs_B * kap_flat[idx_T]) / (abs_B + abs_T + 1e-30)
                jump = sigma * kap_iface

                if phi_B < 0.0:
                    B_coeff = float(L_lil[idx_B, idx_T])
                    T_coeff = float(L_lil[idx_T, idx_B])
                    delta_q[idx_B] += + B_coeff * jump
                    delta_q[idx_T] += - T_coeff * jump
                else:
                    B_coeff = float(L_lil[idx_B, idx_T])
                    T_coeff = float(L_lil[idx_T, idx_B])
                    delta_q[idx_B] += - B_coeff * jump
                    delta_q[idx_T] += + T_coeff * jump

        return delta_q
