"""
Closest-Point Hermite Extension: O(h^6) interface field extension.

Replaces the Aslam (2004) upwind Extension PDE (O(h^1)) with direct
quintic Hermite interpolation using CCD's (f, f', f'') output.

The steady-state of the Extension PDE is the closest-point extension:

    q_ext(x) = q(x_Γ(x))

where x_Γ = x − φ(x) n̂(x) is the closest point on the interface.
This class computes that steady-state directly:

  1. Compute closest point x_Γ via CCD normals (O(h^6) location accuracy).
  2. Interpolate q at x_Γ using CCD Hermite data (O(h^6) interpolation error).

Total field-extension error: O(h^6) vs O(h^1) for upwind PDE.
Cost: 4 CCD calls (no pseudo-time iterations).

2-D Algorithm (§8.4 "最近接点 Hermite 補間による離散化"):

  Step 1  4 CCD calls → 8 derivative fields q_x, q_xx, q_y, q_yy,
          q_xy, q_xxy, q_xyy, q_xxyy.
  Step 2  Closest-point: xc = x − φ n̂_x, yc = y − φ n̂_y (O(h^6)).
  Step 3  x-bracket [x_a, x_b] in source phase for each target point;
          one-sided fallback if x_b is target-side.
  Step 4  Hermite5_x in q, q_y, q_yy at y-row iy → (val0, dval0, ddval0).
  Step 5  Same at y-row iy+1 → (val1, dval1, ddval1).
  Step 6  Hermite5_y → q_ext at (xc, yc).

Reference: Aslam (2004) J. Comput. Phys. 193, 349–355 (baseline comparison).
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver


# ── Quintic Hermite polynomial ──────────────────────────────────────────────

def _h5(t, Fa, Ga, Ha, Fb, Gb, Hb):
    """Evaluate quintic Hermite polynomial at normalized coordinate t.

    Constraints (§8.4 eq. hermite5):
        P(0)=Fa, P'(0)=Ga, P''(0)=Ha,   (normalized: G=h·f', H=h²·f'')
        P(1)=Fb, P'(1)=Gb, P''(1)=Hb.

    Extrapolation (t outside [0,1]) is valid with O(h^6) error bound
    when the extrapolation distance ≤ h (one-sided case, §8.4).
    """
    c0 = Fa
    c1 = Ga
    c2 = 0.5 * Ha
    c3 = 10*(Fb - Fa) - 6*Ga - 4*Gb + 0.5*(Hb - 3*Ha)
    c4 = 15*(Fa - Fb) + 8*Ga + 7*Gb + 0.5*(3*Ha - 2*Hb)
    c5 = 6*(Fb - Fa) - 3*(Ga + Gb) + 0.5*(Hb - Ha)
    return c0 + t*(c1 + t*(c2 + t*(c3 + t*(c4 + t*c5))))


class ClosestPointExtender:
    """O(h^6) field extension via closest-point CCD Hermite interpolation.

    Drop-in replacement for FieldExtender with the same public API:
        compute_normal(phi) → List[array]
        extend(q, phi, n_hat=None) → array
        extend_both(q, phi, n_hat=None) → array

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver  — used for normal computation and q derivatives
    """

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        ccd: "CCDSolver",
    ):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.ndim = grid.ndim

    # ── Public API ────────────────────────────────────────────────────────

    def compute_normal(self, phi) -> List:
        """Compute interface normal n̂ = ∇φ/|∇φ| via CCD (O(h^6)).

        φ is smooth after reinitialisation → CCD gives O(h^6) normals.
        """
        dphi = []
        for ax in range(self.ndim):
            d1, _ = self.ccd.differentiate(phi, ax)
            dphi.append(d1)
        grad_sq = sum(g * g for g in dphi)
        grad_norm = np.maximum(np.sqrt(np.maximum(grad_sq, 1e-28)), 1e-14)
        return [g / grad_norm for g in dphi]

    def extend(self, q, phi, n_hat=None):
        """Extend q from φ<0 (liquid) into φ≥0 (gas) via Hermite interpolation.

        Parameters
        ----------
        q     : array — field to extend (may be discontinuous at Γ)
        phi   : array — signed distance (liquid < 0, gas ≥ 0)
        n_hat : list[array] or None — pre-computed normals (reuse to save CCD calls)

        Returns
        -------
        q_ext : array — extended field (O(h^6) accuracy in extension band)
        """
        if n_hat is None:
            n_hat = self.compute_normal(phi)

        if self.ndim == 2:
            return self._extend_2d(q, phi, n_hat)
        raise NotImplementedError("ClosestPointExtender: only ndim=2 implemented")

    def extend_both(self, q, phi, n_hat=None):
        """Bidirectional extension (same API as FieldExtender.extend_both)."""
        if n_hat is None:
            n_hat = self.compute_normal(phi)
        q_liq = self.extend(q,  phi,  n_hat)
        q_gas = self.extend(q, -phi, [-n for n in n_hat])
        return np.where(phi < 0, q_gas, q_liq)

    # ── 2-D implementation ────────────────────────────────────────────────

    def _extend_2d(self, q, phi, n_hat):
        coords_x = self.grid.coords[0]   # 1-D, length Nx = N[0]+1
        coords_y = self.grid.coords[1]   # 1-D, length Ny = N[1]+1
        Nx = len(coords_x)
        Ny = len(coords_y)

        # ── Step 1: 4 CCD calls → 8 derivative fields ─────────────────────
        q_x,   q_xx   = self.ccd.differentiate(q,    axis=0)
        q_y,   q_yy   = self.ccd.differentiate(q,    axis=1)
        q_xy,  q_xxy  = self.ccd.differentiate(q_y,  axis=0)
        q_xyy, q_xxyy = self.ccd.differentiate(q_yy, axis=0)

        # ── Step 2: Closest-point coordinates (O(h^6) accuracy) ───────────
        XX, YY = np.meshgrid(coords_x, coords_y, indexing='ij')  # (Nx, Ny)
        xc = np.clip(XX - phi * n_hat[0], coords_x[0], coords_x[-1])
        yc = np.clip(YY - phi * n_hat[1], coords_y[0], coords_y[-1])

        # ── Step 3: Bracket left indices via searchsorted ─────────────────
        # ix: largest i with coords_x[i] ≤ xc[i,j] for each target point
        ix = (np.searchsorted(coords_x, xc.ravel(), side='right')
              .reshape(Nx, Ny) - 1)
        iy = (np.searchsorted(coords_y, yc.ravel(), side='right')
              .reshape(Nx, Ny) - 1)
        ix = np.clip(ix, 0, Nx - 2)
        iy = np.clip(iy, 0, Ny - 2)

        # One-sided fallback: ensure bracket-right is strictly source-side.
        # x_Γ is ON the interface; the initial bracket [ix, ix+1] may straddle it,
        # or ix+1 may be an interface node (phi=0).  Shift left until ix+1 is
        # strictly source-side (phi < 0).  3 iterations covers a 3-cell band.
        # Error bound: each shift adds ≤ h to extrapolation distance → O(h^6)
        # is maintained up to total extrapolation distance ≤ 3h (§8.4).
        for _ in range(3):
            ix1 = np.clip(ix + 1, 0, Nx - 1)
            ix = np.where(phi[ix1, iy] >= 0, np.clip(ix - 1, 0, Nx - 2), ix)
        ix1 = np.clip(ix + 1, 0, Nx - 1)

        for _ in range(3):
            iy1 = np.clip(iy + 1, 0, Ny - 1)
            iy = np.where(phi[ix, iy1] >= 0, np.clip(iy - 1, 0, Ny - 2), iy)
        iy1 = np.clip(iy + 1, 0, Ny - 1)

        # ── Step 4: Hermite spacings and normalised coordinates ────────────
        # All shapes (Nx, Ny) via fancy indexing into 1-D coord arrays.
        hx = coords_x[ix1] - coords_x[ix]
        hy = coords_y[iy1] - coords_y[iy]
        tx = (xc - coords_x[ix]) / np.maximum(hx, 1e-30)
        ty = (yc - coords_y[iy]) / np.maximum(hy, 1e-30)

        # ── Step 5: Tensor-product Hermite5 ──────────────────────────────
        # At y-row iy: Hermite5_x in q → val0; in q_y → dval0; in q_yy → ddval0
        val0   = _h5(tx,
                     q   [ix, iy],  hx * q_x  [ix, iy],  hx*hx * q_xx  [ix, iy],
                     q   [ix1,iy],  hx * q_x  [ix1,iy],  hx*hx * q_xx  [ix1,iy])
        dval0  = _h5(tx,
                     q_y [ix, iy],  hx * q_xy [ix, iy],  hx*hx * q_xxy [ix, iy],
                     q_y [ix1,iy],  hx * q_xy [ix1,iy],  hx*hx * q_xxy [ix1,iy])
        ddval0 = _h5(tx,
                     q_yy[ix, iy],  hx * q_xyy[ix, iy],  hx*hx * q_xxyy[ix, iy],
                     q_yy[ix1,iy],  hx * q_xyy[ix1,iy],  hx*hx * q_xxyy[ix1,iy])

        # At y-row iy+1
        val1   = _h5(tx,
                     q   [ix, iy1],  hx * q_x  [ix, iy1],  hx*hx * q_xx  [ix, iy1],
                     q   [ix1,iy1],  hx * q_x  [ix1,iy1],  hx*hx * q_xx  [ix1,iy1])
        dval1  = _h5(tx,
                     q_y [ix, iy1],  hx * q_xy [ix, iy1],  hx*hx * q_xxy [ix, iy1],
                     q_y [ix1,iy1],  hx * q_xy [ix1,iy1],  hx*hx * q_xxy [ix1,iy1])
        ddval1 = _h5(tx,
                     q_yy[ix, iy1],  hx * q_xyy[ix, iy1],  hx*hx * q_xxyy[ix, iy1],
                     q_yy[ix1,iy1],  hx * q_xyy[ix1,iy1],  hx*hx * q_xxyy[ix1,iy1])

        # ── Step 6: Hermite5_y → final interpolated value ─────────────────
        q_interp = _h5(ty,
                       val0, hy * dval0, hy*hy * ddval0,
                       val1, hy * dval1, hy*hy * ddval1)

        # ── Step 7: Assemble: keep source phase unchanged ─────────────────
        return np.where(phi >= 0, q_interp, q)
