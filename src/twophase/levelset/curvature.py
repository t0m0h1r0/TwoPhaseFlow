"""
Interface curvature κ = −∇·(∇φ / |∇φ|).

Implements §2.6 (Eq. 30) of the paper using CCD 6th-order derivatives.

In 2-D the explicit formula is (§2.6 Eq. 30):

    κ = − [φ_y² φ_xx − 2 φ_x φ_y φ_xy + φ_x² φ_yy]
          ─────────────────────────────────────────────
                  (φ_x² + φ_y²)^{3/2}

In 3-D (§2.6):

    κ = −∇·(∇φ / |∇φ|)
      = − [(|∇φ|² δ_ij − φ_i φ_j) φ_ij] / |∇φ|³

computed as −(Δφ − (∇φ·H∇φ)/|∇φ|²) / |∇φ| where H is the Hessian.

Before computing κ, the level-set value ψ is inverted to φ via
``invert_heaviside`` (§3.6) so that CCD operates on the smooth
signed-distance function.

A regularisation floor ``eps_norm`` prevents division by zero at
grid points far from the interface where |∇φ| ≈ 0.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .heaviside import invert_heaviside
from ..interfaces.levelset import ICurvatureCalculator

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


_EPS_NORM = 1e-8   # regularisation floor for |∇φ|


class CurvatureCalculator(ICurvatureCalculator):
    """Compute interface curvature κ from the CLS field ψ.

    Parameters
    ----------
    backend : Backend
    ccd     : CCDSolver — コンストラクタ注入（毎呼び出しでの引き渡し不要）
    eps     : interface thickness ε (used for H_ε inversion)
    """

    def __init__(self, backend: "Backend", ccd: "CCDSolver", eps: float):
        self.xp = backend.xp
        self.ccd = ccd
        self.eps = eps

    def compute(self, psi) -> "array":
        """Compute curvature field κ.

        Parameters
        ----------
        psi : array, shape ``grid.shape``, values ∈ (0, 1)

        Returns
        -------
        kappa : array, same shape as ``psi``
        """
        xp = self.xp
        ccd = self.ccd
        ndim = ccd.ndim
        eps = self.eps

        # Invert ψ → φ (§3.6)
        phi = invert_heaviside(xp, psi, eps)

        # First and second derivatives via CCD
        d1 = []   # ∂φ/∂x_i
        d2 = []   # ∂²φ/∂x_i²
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(phi, ax)
            d1.append(g1)
            d2.append(g2)

        # |∇φ|² and |∇φ|³
        grad_sq = sum(g * g for g in d1)
        grad_norm = xp.sqrt(xp.maximum(grad_sq, _EPS_NORM ** 2))
        grad_cube = grad_norm ** 3

        if ndim == 2:
            kappa = self._kappa_2d(xp, d1, d2, ccd, phi, grad_cube)
        else:
            kappa = self._kappa_3d(xp, d1, d2, ccd, phi, grad_sq, grad_cube)

        return kappa

    # ── 2-D formula (Eq. 30) ──────────────────────────────────────────────

    def _kappa_2d(self, xp, d1, d2, ccd, phi, grad_cube):
        """κ = −[φ_y² φ_xx − 2 φ_x φ_y φ_xy + φ_x² φ_yy] / |∇φ|³"""
        phi_x, phi_y  = d1[0], d1[1]
        phi_xx, _     = d2[0], None
        phi_yy, _     = d2[1], None
        phi_xx        = d2[0]
        phi_yy        = d2[1]

        # Mixed derivative φ_xy via sequential CCD: first along x, then along y
        phi_x_only, _ = ccd.differentiate(phi, 0)
        _, temp       = ccd.differentiate(phi, 0)   # (not needed here)
        phi_xy, _     = ccd.differentiate(phi_x_only, 1)

        numerator = (phi_y**2 * phi_xx
                     - 2.0 * phi_x * phi_y * phi_xy
                     + phi_x**2 * phi_yy)
        return -numerator / grad_cube

    # ── 3-D formula ───────────────────────────────────────────────────────

    def _kappa_3d(self, xp, d1, d2, ccd, phi, grad_sq, grad_cube):
        """κ = −(Δφ − (∇φ · H ∇φ) / |∇φ|²) / |∇φ|

        where H is the Hessian matrix (only diagonal needed here plus
        off-diagonal terms contracted with ∇φ).
        """
        # Laplacian
        lap = sum(d2)

        # ∇φ · H ∇φ = Σ_i Σ_j φ_i φ_ij φ_j
        # = Σ_i φ_i² φ_ii + 2 Σ_{i<j} φ_i φ_j φ_ij
        contracted = sum(d1[i] ** 2 * d2[i] for i in range(3))

        # Off-diagonal Hessian terms
        for i in range(3):
            for j in range(i + 1, 3):
                # φ_ij: differentiate d1[i] along axis j
                phi_ij, _ = ccd.differentiate(d1[i], j)
                contracted = contracted + 2.0 * d1[i] * d1[j] * phi_ij

        grad_sq_safe = xp.maximum(grad_sq, _EPS_NORM ** 2)
        kappa = -(lap - contracted / grad_sq_safe) / xp.sqrt(grad_sq_safe)
        return kappa
