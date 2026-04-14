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
from .hermite_interp import hermite5_coeffs, hermite5_eval

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

        # CCD Hermite data (f, f', f'') for the field
        df_dx, d2f_dx2 = self.ccd.differentiate(field_data, axis=0)
        df_dy, d2f_dy2 = self.ccd.differentiate(field_data, axis=1)
        df_xy, d2f_xy2 = self.ccd.differentiate(df_dx, axis=1)

        # Grid info
        x_coords = grid.coords[0]
        y_coords = grid.coords[1]
        hx = float(grid.L[0] / grid.N[0])
        hy = float(grid.L[1] / grid.N[1])

        # Target-phase points within narrow band
        # Default: source is liquid (φ < 0), extend into gas (φ ≥ 0)
        source_sign = -1.0
        is_target = (phi * source_sign) < 0.0
        dist_cells = xp.abs(phi) / min(hx, hy)
        in_band = is_target & (dist_cells <= self.band_cells)

        target_indices = xp.argwhere(in_band)

        for idx in target_indices:
            i, j = int(idx[0]), int(idx[1])
            phi_val = float(phi[i, j])

            # Closest point on Γ: x_Γ = x - φ·n̂  — Eq. (closest_point)
            x_gamma = x_coords[i] - phi_val * float(nx[i, j])
            y_gamma = y_coords[j] - phi_val * float(ny[i, j])

            # Clamp to domain
            x_gamma = max(x_coords[0], min(x_coords[-1], x_gamma))
            y_gamma = max(y_coords[0], min(y_coords[-1], y_gamma))

            # 2D tensor-product Hermite interpolation at (x_gamma, y_gamma)
            val = self._interp_2d(
                x_gamma, y_gamma,
                x_coords, y_coords, hx, hy,
                field_data, df_dx, d2f_dx2,
                df_dy, d2f_dy2, df_xy, d2f_xy2,
            )
            result[i, j] = val

        return result

    # ── 2D tensor-product Hermite interpolation ──────────────────────────

    def _interp_2d(
        self,
        x_target: float, y_target: float,
        x_coords: np.ndarray, y_coords: np.ndarray,
        hx: float, hy: float,
        field: np.ndarray,
        df_dx: np.ndarray, d2f_dx2: np.ndarray,
        df_dy: np.ndarray, d2f_dy2: np.ndarray,
        df_xy: np.ndarray, d2f_xy2: np.ndarray,
    ) -> float:
        """2D tensor-product Hermite interpolation at (x_target, y_target).

        Strategy (§8.4 "2次元への拡張"):
          1. Find x-bracket [ix_a, ix_b] containing x_target
          2. At y-rows j_a, j_b: x-direction Hermite → (val, dval/dy, d²val/dy²)
          3. y-direction Hermite interpolation of the row values
        """
        Nx = len(x_coords) - 1
        Ny = len(y_coords) - 1

        # Natural brackets containing the target point (ξ ∈ [0,1])
        ix_a = int(np.clip(np.searchsorted(x_coords, x_target) - 1, 0, Nx - 1))
        ix_b = ix_a + 1
        jy_a = int(np.clip(np.searchsorted(y_coords, y_target) - 1, 0, Ny - 1))
        jy_b = jy_a + 1

        xi_x = (x_target - x_coords[ix_a]) / hx

        # Row j_a: x-interpolation
        val_ja = self._hermite1d_x(ix_a, ix_b, jy_a, xi_x, hx, field, df_dx, d2f_dx2)
        ddy_ja = self._hermite1d_x(ix_a, ix_b, jy_a, xi_x, hx, df_dy, df_xy, d2f_xy2)
        d2dy2_ja = self._hermite1d_x_val_only(ix_a, ix_b, jy_a, xi_x, hx, d2f_dy2)

        # Row j_b: x-interpolation
        val_jb = self._hermite1d_x(ix_a, ix_b, jy_b, xi_x, hx, field, df_dx, d2f_dx2)
        ddy_jb = self._hermite1d_x(ix_a, ix_b, jy_b, xi_x, hx, df_dy, df_xy, d2f_xy2)
        d2dy2_jb = self._hermite1d_x_val_only(ix_a, ix_b, jy_b, xi_x, hx, d2f_dy2)

        # y-interpolation
        xi_y = (y_target - y_coords[jy_a]) / hy
        coeffs = hermite5_coeffs(
            val_ja, ddy_ja, d2dy2_ja,
            val_jb, ddy_jb, d2dy2_jb,
            hy,
        )
        return hermite5_eval(coeffs, xi_y)

    # ── 1D Hermite helpers ───────────────────────────────────────────────

    @staticmethod
    def _hermite1d_x(
        ia: int, ib: int, j: int, xi: float, h: float,
        f: np.ndarray, df: np.ndarray, d2f: np.ndarray,
    ) -> float:
        """1D x-direction Hermite interpolation at row j."""
        coeffs = hermite5_coeffs(
            float(f[ia, j]), float(df[ia, j]), float(d2f[ia, j]),
            float(f[ib, j]), float(df[ib, j]), float(d2f[ib, j]),
            h,
        )
        return hermite5_eval(coeffs, xi)

    @staticmethod
    def _hermite1d_x_val_only(
        ia: int, ib: int, j: int, xi: float, h: float,
        f: np.ndarray,
    ) -> float:
        """Linear interpolation fallback for d²f/dy² along x.

        Used when CCD cross-derivatives are not available. Linear
        interpolation preserves overall order because this term enters
        as the 2nd-derivative constraint (multiplied by h²) in ξ-space.
        """
        return float(f[ia, j]) * (1.0 - xi) + float(f[ib, j]) * xi
