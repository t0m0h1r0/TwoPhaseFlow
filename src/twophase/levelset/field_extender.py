"""
Field extension across the interface via Extension PDE.

Implements the Aslam (2004) constant-normal extrapolation:

    ∂q/∂τ + S(φ) n̂·∇q = 0                     (ext-pde)

where S(φ) = sign(φ), n̂ = ∇φ/|∇φ|, and τ is pseudo-time.

At convergence, q is extended from one phase into the other along
interface normals, producing a globally smooth field suitable for
CCD differentiation without Gibbs oscillations.

Spatial discretisation: first-order upwind FD for the advection of q
(discontinuous field → upwind is essential for stability; CCD and DCCD
cannot stably differentiate across discontinuities).

Normal computation: CCD D^(1) on φ (φ is always smooth after
reinitialisation → CCD gives O(h⁶) normals).

CFL condition: Δτ ≤ C_CFL · h_min,  characteristic speed |S n̂| ≤ 1.

Usage in the simulation loop (§09 full algorithm):
  - After PPE solve: extend δp before CCD velocity correction
  - Before predictor IPC: extend p^n before CCD gradient

Symbol mapping (paper → Python):
    q         → q           field to extend
    φ         → phi         signed distance
    n̂         → n_hat       interface normal (CCD-computed)
    S(φ)      → sign_phi    propagation sign
    Δτ        → dtau        pseudo-time step
    n_ext     → n_iter      pseudo-time iterations

Reference: Aslam, T.D. (2004). J. Comput. Phys. 193(1), 349–355.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver


class FieldExtender:
    """Extend fields smoothly across the interface via Extension PDE.

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver — used for normal computation on φ (smooth)
    n_iter  : int — pseudo-time iterations (default 5; covers ~2.5 cells)
    cfl     : float — CFL safety factor (default 0.5)
    """

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        ccd: "CCDSolver",
        n_iter: int = 5,
        cfl: float = 0.5,
    ):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.ndim = grid.ndim
        self.n_iter = n_iter
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]
        self._dtau = cfl * min(self._h)

    def compute_normal(self, phi) -> List:
        """Compute interface normal n̂ = ∇φ/|∇φ| via CCD.

        φ is smooth (post-reinitialisation) → CCD gives O(h⁶) normals.
        """
        dphi = []
        for ax in range(self.ndim):
            d1, _ = self.ccd.differentiate(phi, ax)
            dphi.append(d1)
        grad_sq = sum(g * g for g in dphi)
        grad_norm = np.maximum(np.sqrt(np.maximum(grad_sq, 1e-28)), 1e-14)
        return [g / grad_norm for g in dphi]

    def extend(self, q, phi, n_hat=None):
        """Extend q from φ<0 (liquid) into φ≥0 (gas) region.

        After extension, q is smooth across Γ — safe for CCD differentiation.

        Parameters
        ----------
        q     : array — field to extend (may be discontinuous at Γ)
        phi   : array — signed distance (liquid > 0 or < 0 depending on convention)
        n_hat : list of arrays or None — pre-computed normals (saves CCD calls)

        Returns
        -------
        q_ext : array — extended field (smooth, CCD-ready)
        """
        if n_hat is None:
            n_hat = self.compute_normal(phi)

        ndim = self.ndim
        h = self._h
        dtau = self._dtau

        # sign(φ): +1 in target (φ≥0), -1 in source (φ<0)
        # φ=0 nodes assigned to target to enable interface seeding
        sign_phi = np.where(phi >= 0, 1.0, -1.0)
        freeze = (phi < 0)  # source phase: don't modify

        # Advection velocity per axis
        a = [sign_phi * n_hat[ax] for ax in range(ndim)]

        q_ext = np.copy(q)

        for _ in range(self.n_iter):
            rhs = np.zeros_like(q_ext)
            for ax in range(ndim):
                h_ax = h[ax]
                N_ax = self.grid.N[ax]

                # D⁺ (forward) and D⁻ (backward) first-order differences
                dq_fwd = np.zeros_like(q_ext)
                dq_bwd = np.zeros_like(q_ext)

                sl_c = [slice(None)] * ndim
                sl_p = [slice(None)] * ndim
                sl_m = [slice(None)] * ndim
                sl_c[ax] = slice(1, N_ax)
                sl_p[ax] = slice(2, N_ax + 1)
                sl_m[ax] = slice(0, N_ax - 1)
                dq_fwd[tuple(sl_c)] = (q_ext[tuple(sl_p)] - q_ext[tuple(sl_c)]) / h_ax
                dq_bwd[tuple(sl_c)] = (q_ext[tuple(sl_c)] - q_ext[tuple(sl_m)]) / h_ax

                # Boundary: Neumann ∂q/∂n = 0
                sl_0 = [slice(None)] * ndim; sl_0[ax] = 0
                sl_1 = [slice(None)] * ndim; sl_1[ax] = 1
                sl_N = [slice(None)] * ndim; sl_N[ax] = N_ax
                sl_Nm1 = [slice(None)] * ndim; sl_Nm1[ax] = N_ax - 1
                dq_fwd[tuple(sl_0)] = (q_ext[tuple(sl_1)] - q_ext[tuple(sl_0)]) / h_ax
                dq_bwd[tuple(sl_N)] = (q_ext[tuple(sl_N)] - q_ext[tuple(sl_Nm1)]) / h_ax

                # Upwind: a > 0 → D⁻, a < 0 → D⁺
                rhs += a[ax] * np.where(a[ax] > 0, dq_bwd, dq_fwd)

            q_new = q_ext - dtau * rhs
            q_new[freeze] = q[freeze]
            q_ext = q_new

        return q_ext

    def extend_both(self, q, phi, n_hat=None):
        """Extend q bidirectionally: each phase's values propagate outward.

        Equivalent to calling extend() twice with opposite φ conventions,
        then blending. Used when the full domain needs smooth values
        (e.g., for PPE operator evaluation).

        Parameters
        ----------
        q     : array — field to extend
        phi   : array — signed distance
        n_hat : list or None — pre-computed normals

        Returns
        -------
        q_ext : array — bidirectionally extended field
        """
        if n_hat is None:
            n_hat = self.compute_normal(phi)

        # Extend liquid into gas
        q_liq = self.extend(q, phi, n_hat)
        # Extend gas into liquid (flip φ sign)
        q_gas = self.extend(q, -phi, [(-n) for n in n_hat])

        # Blend: use original phase's value where available
        q_ext = np.where(phi < 0, q_gas, q_liq)
        return q_ext
