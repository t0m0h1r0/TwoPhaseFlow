"""
Interface-limited high-frequency extraction (HFE) filter.

Implements:

    q* = q - C h² w(ψ) ∇²q

where the CCD-computed Laplacian ∇²q extracts high-frequency content and the
interface weight w(ψ) = 4ψ(1−ψ) confines the filter to the interface band.

A3 traceability
───────────────
  Equation  →  Compact filter: Lele (1992) §4; interface-limited form:
               Fedkiw et al. (2002) spurious-current reduction.
  Discrete  →  ∇²q = Σ_ax ∂²q/∂x_ax²  via CCD (d2 output of differentiate())
               w(ψ) = 4ψ(1−ψ)  — O(1) mesh-independent weight (see §Why below)
  Code      →  InterfaceLimitedFilter.apply()

§ Why 4ψ(1−ψ) instead of δ_ε(φ)?
──────────────────────────────────
  δ_ε(φ) = (1/ε)·H(1−H) scales as O(1/h) since ε ~ h.
  When multiplied by h² ∇²q ~ h² · q/h² = q, the product δ_ε · h² · ∇²q
  scales as (1/h)·q, which grows with grid refinement → NOT mesh-independent.

  4ψ(1−ψ) = 4H(1−H) = 4ε·δ_ε ~ 4·h·δ_ε = O(1).
  Then h² · 4ψ(1−ψ) · ∇²q ~ h² · O(1) · q/h² = O(q) → mesh-independent. ✓

§ CCD advantage (zero-overhead path)
──────────────────────────────────────
  ccd.differentiate(q, ax) returns (∂q/∂x_ax, ∂²q/∂x_ax²) simultaneously.
  ∇²q = Σ_ax d2[ax] costs exactly ndim CCD calls (same as computing ∇q).
  When the caller already has d2 from the curvature pipeline, these can be
  passed in directly (pass_d2 argument) at zero extra CCD cost.

§ Stability
──────────────
  ∇²q eigenvalue for highest mode (2D): λ_max = −8/h²
  Update factor:  1 − C·h²·w·8/h² = 1 − 8Cw
  For w ≤ 1 and C < 0.125:  factor ∈ (0, 1)  → stable and damping.
  Recommended C: 0.1–0.5  (keeps 1−8C·w_max > 0 for w_max ≤ 1).

Integration point:
  After κ is computed: κ* = curvature_filter.apply(κ, ψ)
  Before CSF force evaluation.
"""

from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


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

        grid = ccd.grid
        self._h_sq = min(float(grid.L[ax]) / grid.N[ax] for ax in range(grid.ndim)) ** 2

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
        ndim = ccd.ndim

        # ── Interface weight w(ψ) = 4ψ(1−ψ) — O(1), mesh-independent ─────
        psi_arr = xp.asarray(psi)
        w = 4.0 * psi_arr * (1.0 - psi_arr)   # peak = 1 at ψ = 0.5

        # ── Laplacian ∇²q = Σ_ax ∂²q/∂x_ax² ─────────────────────────────
        if d2_list is not None:
            # Zero extra CCD cost: caller supplies d2 from an existing pipeline
            lap_q = sum(xp.asarray(d2) for d2 in d2_list)
        else:
            # Compute d2 via CCD (ndim calls)
            lap_q = xp.zeros_like(q)
            for ax in range(ndim):
                _, q_xx = ccd.differentiate(q, ax)
                lap_q = lap_q + q_xx

        # ── Filter: q* = q + C h² w ∇²q ──────────────────────────────────
        # PLUS = diffusion. Fourier factor at highest 2D mode: (1 − 8C·w).
        # Stable for C < 1/8; C=0.05 → 40% damping per step.
        # MINUS would be anti-diffusion (amplifies noise) — never use.
        return q + self.C * self._h_sq * w * lap_q
