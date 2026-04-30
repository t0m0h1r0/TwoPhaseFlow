"""
HermiteFieldExtension — O(h^6) field extension across interface Γ.

Paper reference: §8.4 (Hermite Field Extension)

Extends a scalar field q from the source phase into the target phase by:
  1. Computing closest interface point x_Γ = x - φ(x)·n̂(x)    — Eq. (closest_point)
  2. Evaluating q(x_Γ) via CCD Hermite 5th-order interpolation — Eq. (hermite5)

The extension satisfies ∇q·n̂ = 0 (Extension PDE steady state, Eq. extension_pde_main)
to O(h^6) accuracy, matching CCD differentiation order.

2D extension uses tensor-product sequential interpolation:
  - x-direction Hermite interpolation at each row
  - y-direction Hermite interpolation of the intermediate results
  - full mixed-derivative data for q_y and q_yy in the x-interpolation

Symbol mapping (paper → code):
    q               → field_data
    q_ext           → result (return value)
    φ               → phi
    n̂ = ∇φ/|∇φ|    → normal (computed via CCD D^(1))
    x_Γ             → closest_pt
    (f, f', f'')    → (val, d1, d2) from CCD

Sign convention:
    Source is liquid (φ < 0), target is gas (φ ≥ 0).
    Extension overwrites target-phase values within narrow band.

Caller contract:
    The input field_data must be smooth (C^6) in the neighborhood of the
    interface for CCD derivatives to be accurate. In the simulation time loop,
    this is satisfied because the field is the full-domain pressure field
    from the previous timestep.
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

from .interfaces import IFieldExtension

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..core.grid import Grid
    from ..backend import Backend


_DEFAULT_BAND_CELLS = 6


class HermiteFieldExtension(IFieldExtension):
    """O(h^6) Hermite field extension using CCD data.

    Parameters
    ----------
    grid : Grid
        Computational grid (2-D, uniform).
    ccd : CCDSolver
        CCD differentiator for computing (f, f', f'').
    backend : Backend
        Array namespace provider.
    band_cells : int
        Narrow-band half-width in cells. Target-phase points beyond
        this distance from Γ are not extended (retain original value).
    """

    def __init__(
        self,
        grid: "Grid",
        ccd: "CCDSolver",
        backend: "Backend",
        band_cells: int = _DEFAULT_BAND_CELLS,
    ):
        if not grid.uniform:
            raise NotImplementedError(
                "HermiteFieldExtension currently supports uniform grids only; "
                "non-uniform grids require a metric-aware HFE implementation."
            )
        self.grid = grid
        self.ccd = ccd
        self.backend = backend
        self.xp = backend.xp
        self.band_cells = band_cells

    # ── IFieldExtension implementation ───────────────────────────────────

    def extend(
        self,
        field_data: np.ndarray,
        phi: np.ndarray,
        n_hat=None,
    ) -> np.ndarray:
        """Extend field_data from source phase across Γ.

        See IFieldExtension.extend for full docstring.

        Parameters
        ----------
        field_data : array — scalar field to extend
        phi        : array — signed-distance function
        n_hat      : ignored (normals are computed internally via CCD)

        The input field_data should be smooth near the interface for
        accurate CCD derivatives. Source-phase values are preserved
        exactly; only target-phase points in the narrow band are
        overwritten with the Hermite-interpolated extension.
        """
        xp = self.xp
        grid = self.grid

        if grid.ndim != 2:
            raise NotImplementedError("HFE currently supports 2-D grids only")

        result = xp.copy(field_data)

        # Interface normal n̂ = ∇φ / |∇φ| via CCD — §8.4 Eq. (closest_point)
        dphi_dx, _ = self.ccd.differentiate(phi, axis=0)
        dphi_dy, _ = self.ccd.differentiate(phi, axis=1)
        grad_mag = xp.sqrt(dphi_dx**2 + dphi_dy**2)
        grad_mag = xp.maximum(grad_mag, 1e-14)
        nx = dphi_dx / grad_mag
        ny = dphi_dy / grad_mag

        # CCD Hermite data for the full tensor-product extension.
        df_dx, d2f_dx2 = self.ccd.differentiate(field_data, axis=0)
        df_dy, d2f_dy2 = self.ccd.differentiate(field_data, axis=1)
        df_xy, d2f_xyy = self.ccd.differentiate(df_dx, axis=1)
        df_xxy, d2f_xxyy = self.ccd.differentiate(d2f_dx2, axis=1)

        # Grid info (uniform grids only — HFE library constraint)
        x_coords = xp.asarray(grid.coords[0])
        y_coords = xp.asarray(grid.coords[1])
        hx = float(grid.L[0] / grid.N[0])
        hy = float(grid.L[1] / grid.N[1])
        Nx = int(grid.N[0])
        Ny = int(grid.N[1])

        # Target-phase points within narrow band
        # Default: source is liquid (φ < 0), extend into gas (φ ≥ 0)
        source_sign = -1.0
        is_target = (phi * source_sign) < 0.0
        dist_cells = xp.abs(phi) / min(hx, hy)
        in_band = is_target & (dist_cells <= self.band_cells)

        # Per-cell closest-point on Γ (vectorised): x_Γ = x - φ·n̂
        X2, Y2 = xp.meshgrid(x_coords, y_coords, indexing="ij")
        x_gamma_full = X2 - phi * nx
        y_gamma_full = Y2 - phi * ny

        # Clamp to domain
        x_gamma_full = xp.clip(x_gamma_full, float(x_coords[0]), float(x_coords[-1]))
        y_gamma_full = xp.clip(y_gamma_full, float(y_coords[0]), float(y_coords[-1]))

        # Bracket indices via uniform-grid division (no searchsorted needed)
        x0 = float(x_coords[0])
        y0 = float(y_coords[0])
        ix_a = xp.clip(
            ((x_gamma_full - x0) / hx).astype(xp.int64), 0, Nx - 2
        )
        jy_a = xp.clip(
            ((y_gamma_full - y0) / hy).astype(xp.int64), 0, Ny - 2
        )
        ix_b = ix_a + 1
        jy_b = jy_a + 1

        # Local ξ coordinates in [0, 1]
        xi_x = (x_gamma_full - x_coords[ix_a]) / hx
        xi_y = (y_gamma_full - y_coords[jy_a]) / hy

        # Gather 2×2 stencil for every Hermite primitive at
        # (ix_a|ix_b, jy_a|jy_b).
        def _g(arr):
            return (
                arr[ix_a, jy_a], arr[ix_b, jy_a],
                arr[ix_a, jy_b], arr[ix_b, jy_b],
            )
        f_aa, f_ba, f_ab, f_bb = _g(field_data)
        fx_aa, fx_ba, fx_ab, fx_bb = _g(df_dx)
        fxx_aa, fxx_ba, fxx_ab, fxx_bb = _g(d2f_dx2)
        fy_aa, fy_ba, fy_ab, fy_bb = _g(df_dy)
        fxy_aa, fxy_ba, fxy_ab, fxy_bb = _g(df_xy)
        fxyy_aa, fxyy_ba, fxyy_ab, fxyy_bb = _g(d2f_xyy)
        fxxy_aa, fxxy_ba, fxxy_ab, fxxy_bb = _g(df_xxy)
        fxxyy_aa, fxxyy_ba, fxxyy_ab, fxxyy_bb = _g(d2f_xxyy)
        fyy_aa, fyy_ba, fyy_ab, fyy_bb = _g(d2f_dy2)

        # Row j_a: x-interpolation of (val, ∂y, ∂yy)
        val_ja = _hermite5_xp(
            xp, f_aa, fx_aa, fxx_aa, f_ba, fx_ba, fxx_ba, hx, xi_x
        )
        ddy_ja = _hermite5_xp(
            xp, fy_aa, fxy_aa, fxxy_aa, fy_ba, fxy_ba, fxxy_ba, hx, xi_x
        )
        d2dy2_ja = _hermite5_xp(
            xp, fyy_aa, fxyy_aa, fxxyy_aa, fyy_ba, fxyy_ba, fxxyy_ba, hx, xi_x
        )

        # Row j_b: x-interpolation
        val_jb = _hermite5_xp(
            xp, f_ab, fx_ab, fxx_ab, f_bb, fx_bb, fxx_bb, hx, xi_x
        )
        ddy_jb = _hermite5_xp(
            xp, fy_ab, fxy_ab, fxxy_ab, fy_bb, fxy_bb, fxxy_bb, hx, xi_x
        )
        d2dy2_jb = _hermite5_xp(
            xp, fyy_ab, fxyy_ab, fxxyy_ab, fyy_bb, fxyy_bb, fxxyy_bb, hx, xi_x
        )

        # y-direction Hermite interpolation of the intermediate rows
        val_full = _hermite5_xp(
            xp, val_ja, ddy_ja, d2dy2_ja, val_jb, ddy_jb, d2dy2_jb, hy, xi_y
        )

        # Masked scatter: only overwrite in-band target cells
        return xp.where(in_band, val_full, result)

def _hermite5_xp(xp, fa, dfa, d2fa, fb, dfb, d2fb, h: float, xi):
    """Array-valued 5th-order Hermite interpolation in ξ-space.

    Closed-form solve of the 6×6 Vandermonde-like system (identical maths
    to :func:`hermite5_coeffs`) applied elementwise on ``backend.xp``
    arrays, followed by Horner evaluation at ``xi``.
    """
    F0 = fa
    F1 = h * dfa
    F2 = h * h * d2fa
    G0 = fb
    G1 = h * dfb
    G2 = h * h * d2fb

    c0 = F0
    c1 = F1
    c2 = 0.5 * F2

    A = G0 - c0 - c1 - c2
    B = G1 - c1 - 2.0 * c2
    C = G2 - 2.0 * c2

    c3 = (20.0 * A - 8.0 * B + C) / 2.0
    c4 = (-30.0 * A + 14.0 * B - 2.0 * C) / 2.0
    c5 = (12.0 * A - 6.0 * B + C) / 2.0

    return c0 + xi * (c1 + xi * (c2 + xi * (c3 + xi * (c4 + xi * c5))))
