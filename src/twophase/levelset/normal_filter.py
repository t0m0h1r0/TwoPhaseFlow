"""
Normal-vector diffusion filter for interface stabilization.

Implements:

    n* = n + α ∇·(w ∇n)           (componentwise)

followed by re-normalization:

    n* ← n* / |n*|

The weight w = δ_ε(φ) (smoothed delta function) restricts diffusion to the
interface band, preserving bulk-fluid accuracy.

A3 traceability
───────────────
  Equation    →  Herrmann (2008) "A balanced-force refined level set...", Eq.14
                 Sussman & Fatemi (1999): normal-diffusion stabilization
  Discrete    →  ∂_ax(w ∂_ax n_i): two sequential CCD calls per (axis, component)
  Code        →  NormalVectorFilter.apply()  +  kappa_from_normals()

Integration point in pipeline:
  φ → ∇φ (CCD) → n → [this filter] → n* → κ = -∇·n* (CCD) → CSF
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend

# Gradient regularisation floor (shared with curvature.py)
_EPS_NORM = 1e-3


class NormalVectorFilter:
    """Diffusion filter applied to the interface normal n = ∇φ/|∇φ|.

    Equation (A3: Herrmann 2008 Eq. 14):

        n*_i = n_i + α h² ∇·(w ∇n_i)       per component i
        n*   ← n* / |n*|                     re-normalisation

    where h = min grid spacing.  The h² factor makes α mesh-independent
    (dimensionless Fourier damping factor) — stable for α < 1/(2·ndim).

    Diffusion weight choice:
        w = |∇φ|  (grad_norm, ≈ 1 near interface for a good SDF)

    This keeps w = O(1) and avoids the 1/h scaling of δ_ε, which would
    require α ∝ h and collapse to a mesh-parameter rather than a
    physics parameter.

    Interface restriction:
        mask = δ_ε(φ) > w_threshold_frac · max(δ_ε)
    Only masked points receive the filter update; the rest keep n_i.

    Parameters
    ----------
    backend          : Backend  — carries the array namespace xp
    ccd              : CCDSolver — pre-factored CCD differentiator
    eps              : float  — interface thickness ε (used for mask only)
    alpha            : float  — dimensionless filter strength in (0, 0.125)
                                Fourier attenuation at highest frequency:
                                  2D: (1 − 8α),  3D: (1 − 12α)
                                Recommended: 0.03–0.10; stable for C < 0.125 (2D)
                                (default 0.05 → 40% damping of highest-freq mode)
    w_threshold_frac : float  — interface mask threshold as fraction of
                                max(δ_ε) (default 0.10)
    """

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        eps: float,
        alpha: float = 0.05,
        w_threshold_frac: float = 0.10,
    ):
        self.xp = backend.xp
        self.ccd = ccd
        self.eps = eps
        self.alpha = alpha
        self.w_threshold_frac = w_threshold_frac

        # Pre-compute h² (mesh-normalisation for CCD physical derivatives)
        grid = ccd.grid
        self._h_sq = min(float(grid.L[ax]) / grid.N[ax] for ax in range(grid.ndim)) ** 2

    # ── Public API ────────────────────────────────────────────────────────

    def apply(self, d1_list: List, phi) -> List:
        """Filter normal vector components; return filtered list.

        Parameters
        ----------
        d1_list : list of ndim arrays — [∂φ/∂x, ∂φ/∂y[, ∂φ/∂z]]
                  CCD first-derivatives of the SDF φ
        phi     : array — signed-distance field φ (same grid as d1_list)

        Returns
        -------
        n_filtered : list of ndim arrays — re-normalized filtered normal
                     components [n*_x, n*_y[, n*_z]]

        Discretization (A3):
          n*_i = n_i + α h² ∇·(|∇φ| ∇n_i)

          Per axis ax:
            Step 1. ∂n_i/∂x_ax  = ccd.differentiate(n_i, ax)[0]
            Step 2. flux_ax     = |∇φ| · ∂n_i/∂x_ax
            Step 3. ∂flux/∂x_ax = ccd.differentiate(flux_ax, ax)[0]
            Step 4. sum axes → ∇·(|∇φ| ∇n_i)

        CCD cost: 2·ndim² calls (8 in 2D, 18 in 3D)
        """
        xp = self.xp
        ccd = self.ccd
        ndim = ccd.ndim
        h_sq = self._h_sq

        # ── |∇φ| — diffusion weight (O(1) near interface) ─────────────────
        grad_sq = sum(g * g for g in d1_list)
        grad_norm = xp.sqrt(xp.maximum(grad_sq, _EPS_NORM ** 2))
        w = grad_norm   # w = |∇φ| ≈ 1 for a good SDF

        # ── Interface mask via δ_ε(φ) ─────────────────────────────────────
        w_delta = _delta_eps(xp, phi, self.eps)
        w_delta_max = float(xp.max(w_delta))
        if w_delta_max < 1e-30:
            # No interface — return unmodified normals
            return [g / grad_norm for g in d1_list]
        mask = w_delta > self.w_threshold_frac * w_delta_max

        # ── n = ∇φ / |∇φ| ─────────────────────────────────────────────────
        n_components = [g / grad_norm for g in d1_list]

        # ── Diffusion filter per component ─────────────────────────────────
        # n*_i = n_i + α h² ∇·(|∇φ| ∇n_i)
        # h² normalises CCD physical derivatives → α is mesh-independent.
        # Stability (explicit diffusion with w ≤ 1): α < 1/(2·ndim).

        n_filtered = []
        for n_i in n_components:
            div_term = xp.zeros_like(n_i)
            for ax in range(ndim):
                dni_ax, _ = ccd.differentiate(n_i, ax)    # ∂n_i/∂x_ax
                flux = w * dni_ax                          # |∇φ| ∂n_i/∂x_ax
                dflux_ax, _ = ccd.differentiate(flux, ax) # ∂(|∇φ| ∂n_i/∂x_ax)/∂x_ax
                div_term = div_term + dflux_ax

            n_i_new = n_i + self.alpha * h_sq * div_term
            # Apply only in interface band
            n_filtered.append(xp.where(mask, n_i_new, n_i))

        # ── Re-normalization ───────────────────────────────────────────────
        norm_sq = sum(ni ** 2 for ni in n_filtered)
        norm = xp.sqrt(xp.maximum(norm_sq, _EPS_NORM ** 2))
        return [ni / norm for ni in n_filtered]


# ── Module-level helper — used by CurvatureCalculator after filtering ─────

def kappa_from_normals(xp, ccd: "CCDSolver", n_filtered: List):
    """Compute κ = -∇·n* from filtered normal components via CCD.

    Parameters
    ----------
    xp         : array namespace
    ccd        : CCDSolver
    n_filtered : list of ndim arrays — [n*_x, n*_y[, n*_z]]

    Returns
    -------
    kappa : array — interface curvature field

    CCD cost: ndim CCD calls.
    """
    div_n = xp.zeros_like(n_filtered[0])
    for ax, n_ax in enumerate(n_filtered):
        dn_ax, _ = ccd.differentiate(n_ax, ax)
        div_n = div_n + dn_ax
    return -div_n


# ── Private utility ───────────────────────────────────────────────────────

def _delta_eps(xp, phi, eps: float):
    """Smoothed delta function δ_ε(φ) = (1/ε) H(1-H).

    Inline copy to avoid circular import with heaviside.py.
    Identical to levelset.heaviside.delta().
    """
    H = 1.0 / (1.0 + xp.exp(-phi / eps))
    return (1.0 / eps) * H * (1.0 - H)
