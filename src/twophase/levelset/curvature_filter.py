"""
Interface-limited curvature filters.

Provides two complementary filters:

1. InterfaceLimitedFilter  (Laplacian / HFE):
       q* = q + C h² w(ψ) ∇²q          (+ = diffusion, C < 0.125 in 2D)

2. CurvatureBiharmonicFilter  (κ direct / biharmonic):
       κ* = κ − β h⁴ w(ψ) ∇⁴κ          (− = hyper-diffusion, β < 0.016 in 2D)

Both use w(ψ) = 4ψ(1−ψ) as the interface weight (O(1), mesh-independent).

A3 traceability
───────────────
  Laplacian form  →  Lele (1992) §4; Fedkiw et al. (2002) spurious-current
  Biharmonic form →  Gottlieb & Hesthaven (2001) stabilisation; Jamet (2002)
                     §4 curvature-smoothing via ∇⁴
  Discrete ∇²q    →  Σ_ax ∂²q/∂x_ax² via CCD (d2 from differentiate())
  Discrete ∇⁴q    →  ∇²(∇²q): 2×ndim CCD calls
  Code            →  InterfaceLimitedFilter.apply(), CurvatureBiharmonicFilter.apply()

§ Why 4ψ(1−ψ) instead of δ_ε(φ)?
──────────────────────────────────
  δ_ε ~ O(1/h).  h² · δ_ε · ∇²q ~ q/h  → NOT mesh-independent.
  4ψ(1−ψ) = O(1).  h² · 4ψ(1−ψ) · ∇²q ~ O(q)  ✓

§ Stability (2D, w ≤ 1)
──────────────────────────
  Laplacian:    ∇² eigenvalue −8/h²  → factor (1−8Cw);  C < 1/8 = 0.125
  Biharmonic:   ∇⁴ eigenvalue 64/h⁴ → factor (1−64βw); β < 1/64 ≈ 0.0156
"""

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


# ── Module-level helpers ──────────────────────────────────────────────────────

def _ccd_laplacian(xp, ccd, field):
    """∇²field = Σ_ax ∂²field/∂x_ax² via CCD (ndim tridiagonal solves)."""
    lap = xp.zeros_like(field)
    for ax in range(ccd.ndim):
        lap += ccd.second_derivative(field, ax)
    return lap


def _interface_weight(xp, psi):
    """w(ψ) = 4ψ(1−ψ) — O(1) mesh-independent interface weight."""
    psi_arr = xp.asarray(psi)
    return 4.0 * psi_arr * (1.0 - psi_arr)


class InterfaceLimitedFilter:
    """High-frequency extraction filter restricted to the interface band.

    Equation:

        q* = q − C h² w(ψ) ∇²q

    where:
        w(ψ) = 4ψ(1−ψ)    — mesh-independent interface weight, O(1) at ψ=0.5
        ∇²q               — CCD Laplacian (ndim calls, d2 output)
        h²                — min-grid-spacing squared (CCD normalisation)
        C                 — dimensionless strength in (0, 0.125)

    Parameters
    ----------
    backend : Backend
    ccd     : CCDSolver
    C       : float — filter strength (default 0.05; stable for C < 0.125 in 2D)
    """

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        C: float = 0.05,
    ):
        self.xp = backend.xp
        self.ccd = ccd
        self.C = C

        # _h_sq is read from grid.h at use-time via property, so it picks
        # up updated spacings after non-uniform grid rebuild.

    @property
    def _h_sq(self) -> float:
        """Minimum cell spacing squared, recomputed from live grid state."""
        import numpy as _np
        grid = self.ccd.grid
        return min(float(_np.min(grid.h[ax])) for ax in range(grid.ndim)) ** 2

    # ── Public API ────────────────────────────────────────────────────────

    def apply(self, q, psi, d2_list: Optional[List] = None):
        """Apply HFE filter to scalar field q.

        Parameters
        ----------
        q        : array — scalar field to filter (e.g. κ, n_i)
        psi      : array — CLS field ψ ∈ (0,1), used for interface weight
        d2_list  : list of ndim arrays (optional) — pre-computed ∂²q/∂x_ax²
                   for each axis; if provided, no CCD calls are made.
                   Pass the d2 output from the curvature pipeline for zero
                   extra CCD cost.

        Returns
        -------
        q* : array — filtered field

        CCD cost: ndim calls if d2_list is None, else 0.

        Discretization (A3):
          1. w = 4ψ(1−ψ)
          2. ∇²q = Σ_ax d2_ax  (from CCD or d2_list)
          3. q* = q − C h² w ∇²q
        """
        xp = self.xp
        ccd = self.ccd

        # ── Interface weight w(ψ) = 4ψ(1−ψ) — O(1), mesh-independent ─────
        w = _interface_weight(xp, psi)

        # ── Laplacian ∇²q = Σ_ax ∂²q/∂x_ax² ─────────────────────────────
        if d2_list is not None:
            # Zero extra CCD cost: caller supplies d2 from an existing pipeline
            lap_q = sum(xp.asarray(d2) for d2 in d2_list)
        else:
            lap_q = _ccd_laplacian(xp, ccd, q)

        # ── Filter: q* = q + C h² w ∇²q ──────────────────────────────────
        # PLUS = diffusion. Fourier factor at highest 2D mode: (1 − 8C·w).
        # Stable for C < 1/8; C=0.05 → 40% damping per step.
        # MINUS would be anti-diffusion (amplifies noise) — never use.
        return q + self.C * self._h_sq * w * lap_q


class CurvatureBiharmonicFilter:
    """Biharmonic (∇⁴) curvature filter restricted to the interface band.

    Equation (A3: Gottlieb & Hesthaven 2001; Jamet 2002 §4):

        κ* = κ − β h⁴ w(ψ) ∇⁴κ

    where:
        ∇⁴κ = ∇²(∇²κ)        — computed by two sequential CCD Laplacians
        w(ψ) = 4ψ(1−ψ)        — O(1) mesh-independent interface weight
        h⁴                    — (min grid spacing)⁴ (CCD normalisation)
        β                     — dimensionless strength in (0, 1/64 ≈ 0.0156)

    Why biharmonic?
        ∇²q is a second-order dissipation — it spreads information over O(h).
        ∇⁴q is a fourth-order hyper-dissipation — it targets only the highest
        wavenumbers while leaving low wavenumbers nearly untouched.
        Net effect: sharper spectral selectivity than the Laplacian filter.

    Stability (2D, w ≤ 1):
        ∇⁴ eigenvalue at highest mode: +64/h⁴
        Update factor: 1 − 64 β w_max
        Stable for β < 1/64 ≈ 0.0156.
        Recommended: β = 0.005–0.01.

    Parameters
    ----------
    backend : Backend
    ccd     : CCDSolver
    beta    : float — filter strength (default 0.01; stable for β < 0.0156 in 2D)
    """

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        beta: float = 0.01,
    ):
        self.xp = backend.xp
        self.ccd = ccd
        self.beta = beta

        grid = ccd.grid
        h = min(float(grid.L[ax]) / grid.N[ax] for ax in range(grid.ndim))
        self._h4 = h ** 4

    def apply(self, q, psi):
        """Apply biharmonic filter to scalar field q.

        Parameters
        ----------
        q   : array — scalar field to filter (κ)
        psi : array — CLS field ψ ∈ (0,1)

        Returns
        -------
        κ* : array — filtered field

        CCD cost: 2·ndim calls (∇²κ then ∇²(∇²κ)).

        Discretization (A3):
          Step 1. lap_q  = Σ_ax d2(q, ax)       — ∇²κ
          Step 2. bilap_q = Σ_ax d2(lap_q, ax)  — ∇⁴κ = ∇²(∇²κ)
          Step 3. w = 4ψ(1−ψ)
          Step 4. κ* = κ − β h⁴ w ∇⁴κ
        """
        xp = self.xp
        ccd = self.ccd

        lap_q   = _ccd_laplacian(xp, ccd, q)        # ∇²κ
        bilap_q = _ccd_laplacian(xp, ccd, lap_q)    # ∇⁴κ = ∇²(∇²κ)
        w       = _interface_weight(xp, psi)

        # MINUS = hyper-diffusion (∇⁴ eigenvalue is positive → subtract to damp).
        # Stability: factor (1 − 64βw) > 0 iff β < 1/64 ≈ 0.0156 for w ≤ 1.
        return q - self.beta * self._h4 * w * bilap_q
