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
from typing import Optional, TYPE_CHECKING

from .heaviside import invert_heaviside
from .interfaces import ICurvatureCalculator
from ..backend import fuse as _fuse
from ..core.boundary import is_periodic_axis

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from .normal_filter import NormalVectorFilter
    from .curvature_filter import InterfaceLimitedFilter


_EPS_NORM = 1e-3   # regularisation floor for |∇φ| (paper §3.5 recommended value)
_DCCD_EPS_D = 0.05  # DCCD filter strength for curvature derivatives (§10.1.3)


@_fuse
def _kappa_2d_formula(phi_x, phi_y, phi_xx, phi_yy, phi_xy, grad_cube):
    """κ = −[φ_y² φ_xx − 2 φ_x φ_y φ_xy + φ_x² φ_yy] / |∇φ|³

    Fused into a single CUDA kernel on GPU via ``@_fuse``.
    """
    num = phi_y * phi_y * phi_xx - 2.0 * phi_x * phi_y * phi_xy + phi_x * phi_x * phi_yy
    return -num / grad_cube


def _coefficient_slice(coeff, sl):
    return coeff[tuple(sl)] if hasattr(coeff, "ndim") and coeff.ndim > 0 else coeff


def _dccd_filter_1d(
    xp,
    f,
    ax: int,
    ndim: int,
    N_ax: int,
    eps_d,
    *,
    periodic: bool = False,
):
    """Apply the 3-point DCCD dissipative filter along axis ``ax``.

    A3 chain: DCCD transfer function (§10.1.3) → boundary topology closure
    → periodic axes must satisfy ``f[N] = f[0]`` after filtering.
    """
    result = xp.copy(f)
    if periodic:
        unique_sl = [slice(None)] * ndim
        unique_sl[ax] = slice(0, N_ax)
        unique = f[tuple(unique_sl)]
        eps_unique = _coefficient_slice(eps_d, unique_sl)
        filtered = unique + eps_unique * (
            xp.roll(unique, -1, axis=ax) - 2.0 * unique + xp.roll(unique, 1, axis=ax)
        )
        result[tuple(unique_sl)] = filtered
        image_sl = [slice(None)] * ndim
        source_sl = [slice(None)] * ndim
        image_sl[ax] = N_ax
        source_sl[ax] = 0
        result[tuple(image_sl)] = result[tuple(source_sl)]
        return result

    sl_c = [slice(None)] * ndim
    sl_m = [slice(None)] * ndim
    sl_p = [slice(None)] * ndim
    sl_c[ax] = slice(1, N_ax)
    sl_m[ax] = slice(0, N_ax - 1)
    sl_p[ax] = slice(2, N_ax + 1)
    eps_c = _coefficient_slice(eps_d, sl_c)
    result[tuple(sl_c)] = f[tuple(sl_c)] + eps_c * (
        f[tuple(sl_p)] - 2.0 * f[tuple(sl_c)] + f[tuple(sl_m)]
    )
    return result


def _dccd_filter_nd(xp, f, grid, eps_d: float, *, bc_type: str = "wall", switch=None):
    """Apply DCCD filter along all spatial axes with boundary topology."""
    result = f
    coeff = eps_d if switch is None else eps_d * switch
    for ax in range(grid.ndim):
        result = _dccd_filter_1d(
            xp,
            result,
            ax,
            grid.ndim,
            grid.N[ax],
            coeff,
            periodic=is_periodic_axis(bc_type, ax, grid.ndim),
        )
    for ax in range(grid.ndim):
        if is_periodic_axis(bc_type, ax, grid.ndim):
            continue
        left = [slice(None)] * grid.ndim
        right = [slice(None)] * grid.ndim
        left[ax] = 0
        right[ax] = grid.N[ax]
        result[tuple(left)] = f[tuple(left)]
        result[tuple(right)] = f[tuple(right)]
    return result


# DO NOT DELETE — passed tests 2026-03-27
# Superseded by: CurvatureCalculatorPsi in curvature_psi.py
# Retained for: cross-validation and regression baseline
class CurvatureCalculator(ICurvatureCalculator):
    """Compute interface curvature κ from the CLS field ψ (via phi inversion).

    Legacy implementation: inverts ψ → φ via logit, then computes κ from φ.
    Superseded by CurvatureCalculatorPsi which computes κ directly from ψ.

    Parameters
    ----------
    backend  : Backend
    ccd      : CCDSolver — constructor injection
    eps      : interface thickness ε (used for H_ε inversion)
    dccd_eps : DCCD filter strength (0 = no filter, default 0.05)
    """

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        eps,
        dccd_eps: float = _DCCD_EPS_D,
        normal_filter: Optional["NormalVectorFilter"] = None,
        kappa_filter: Optional["InterfaceLimitedFilter"] = None,
    ):
        self.xp = backend.xp
        self.ccd = ccd
        self.eps = eps
        self.dccd_eps = dccd_eps
        self.normal_filter = normal_filter    # optional: NormalVectorFilter
        self.kappa_filter = kappa_filter      # optional: InterfaceLimitedFilter

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

        # Ensure psi is on the correct device (no-op on CPU).
        psi = xp.asarray(psi)
        dccd_switch = (2.0 * psi - 1.0) ** 2 if self.dccd_eps > 0 else None

        # Invert ψ → φ (§3.6)
        phi = invert_heaviside(xp, psi, eps)

        # First and second derivatives via CCD + optional DCCD filter
        d1 = []   # ∂φ/∂x_i
        d2 = []   # ∂²φ/∂x_i²
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(phi, ax)
            if self.dccd_eps > 0:
                g1 = _dccd_filter_nd(
                    xp, g1, ccd.grid, self.dccd_eps, bc_type=ccd.bc_type,
                    switch=dccd_switch,
                )
                g2 = _dccd_filter_nd(
                    xp, g2, ccd.grid, self.dccd_eps, bc_type=ccd.bc_type,
                    switch=dccd_switch,
                )
            d1.append(g1)
            d2.append(g2)

        # |∇φ|² and |∇φ|³
        grad_sq = sum(g * g for g in d1)
        grad_norm = xp.sqrt(xp.maximum(grad_sq, _EPS_NORM ** 2))
        grad_cube = grad_norm ** 3

        if self.normal_filter is not None:
            # Filter n = ∇φ/|∇φ|, then κ = -∇·n* via CCD divergence.
            # This path replaces the Hessian formula when filtering is active.
            from .normal_filter import kappa_from_normals
            n_filtered = self.normal_filter.apply(d1, phi)
            kappa = kappa_from_normals(xp, ccd, n_filtered)
        elif ndim == 2:
            kappa = self._kappa_2d(xp, d1, d2, ccd, phi, grad_cube, dccd_switch)
        else:
            kappa = self._kappa_3d(xp, d1, d2, ccd, phi, grad_sq, grad_cube)

        if self.kappa_filter is not None:
            # Interface-limited filter: κ* = κ − C h² 4ψ(1−ψ) ∇²κ
            from .curvature_filter import InterfaceLimitedFilter
            kappa = self.kappa_filter.apply(kappa, psi)

        return kappa

    # ── 2-D formula (Eq. 30) ──────────────────────────────────────────────

    def _kappa_2d(self, xp, d1, d2, ccd, phi, grad_cube, dccd_switch=None):
        """κ = −[φ_y² φ_xx − 2 φ_x φ_y φ_xy + φ_x² φ_yy] / |∇φ|³"""
        phi_x, phi_y = d1[0], d1[1]
        phi_xx       = d2[0]
        phi_yy       = d2[1]

        # Mixed derivative φ_xy via sequential CCD: differentiate d1[0] along y
        phi_xy, _ = ccd.differentiate(d1[0], 1)
        if self.dccd_eps > 0:
            phi_xy = _dccd_filter_nd(
                self.xp, phi_xy, ccd.grid, self.dccd_eps, bc_type=ccd.bc_type,
                switch=dccd_switch,
            )

        return _kappa_2d_formula(phi_x, phi_y, phi_xx, phi_yy, phi_xy, grad_cube)

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
