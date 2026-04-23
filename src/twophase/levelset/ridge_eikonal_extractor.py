"""Ridge extraction helpers for ridge-eikonal reinitialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .ridge_eikonal_kernels import _sigma_eff_kernel

if TYPE_CHECKING:
    from ..backend import Backend


class RidgeExtractor:
    """Gaussian-xi ridge extraction on non-uniform grids."""

    def __init__(self, backend: "Backend", grid, sigma_0: float = 3.0,
                 h_ref: float | None = None):
        self._xp = backend.xp
        self._grid = grid
        self._sigma_0 = float(sigma_0)
        if h_ref is None:
            h_ref = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
        self._h_ref = h_ref

        xp = self._xp
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        self._h_field = xp.sqrt(hx * hy)
        self._sigma_eff = _sigma_eff_kernel(self._h_field, self._sigma_0, self._h_ref)
        self._X = xp.asarray(grid.coords[0]).reshape(-1, 1)
        self._Y = xp.asarray(grid.coords[1]).reshape(1, -1)

    def update_grid(self, grid) -> None:
        self._grid = grid
        xp = self._xp
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        self._h_field = xp.sqrt(hx * hy)
        self._sigma_eff = _sigma_eff_kernel(self._h_field, self._sigma_0, self._h_ref)
        self._X = xp.asarray(grid.coords[0]).reshape(-1, 1)
        self._Y = xp.asarray(grid.coords[1]).reshape(1, -1)

    @property
    def sigma_eff(self):
        return self._sigma_eff

    def compute_xi_ridge(self, phi) -> "array":
        xp = self._xp
        phi = xp.asarray(phi)
        crossings = self._find_crossings(phi)
        if crossings is None or crossings.shape[0] == 0:
            return xp.zeros_like(phi)

        cx = crossings[:, 0].reshape(-1, 1, 1)
        cy = crossings[:, 1].reshape(-1, 1, 1)
        dx = self._X.reshape(1, -1, 1) - cx
        dy = self._Y.reshape(1, 1, -1) - cy
        d2 = dx * dx + dy * dy
        sig2 = (self._sigma_eff * self._sigma_eff).reshape(1, *self._sigma_eff.shape)
        return xp.sum(xp.exp(-d2 / sig2), axis=0)

    def extract_ridge_mask(self, xi_ridge) -> "array":
        xp = self._xp
        xi = xp.asarray(xi_ridge)
        loc_x = xp.zeros_like(xi, dtype=bool)
        loc_x[1:-1, :] = (xi[1:-1, :] > xi[:-2, :]) & (xi[1:-1, :] > xi[2:, :])
        loc_y = xp.zeros_like(xi, dtype=bool)
        loc_y[:, 1:-1] = (xi[:, 1:-1] > xi[:, :-2]) & (xi[:, 1:-1] > xi[:, 2:])
        local_max = loc_x | loc_y

        hx = self._grid.h[0]
        hy = self._grid.h[1]
        hx_dev = xp.asarray(hx).reshape(-1, 1)
        hy_dev = xp.asarray(hy).reshape(1, -1)

        hxx = xp.zeros_like(xi)
        hyy = xp.zeros_like(xi)
        hxy = xp.zeros_like(xi)
        hxx[1:-1, :] = (xi[2:, :] - 2.0 * xi[1:-1, :] + xi[:-2, :]) / (hx_dev[1:-1] * hx_dev[1:-1])
        hyy[:, 1:-1] = (xi[:, 2:] - 2.0 * xi[:, 1:-1] + xi[:, :-2]) / (hy_dev[:, 1:-1] * hy_dev[:, 1:-1])
        hxy[1:-1, 1:-1] = (xi[2:, 2:] - xi[2:, :-2] - xi[:-2, 2:] + xi[:-2, :-2]) / (
            4.0 * hx_dev[1:-1] * hy_dev[:, 1:-1]
        )

        hess_neg = (hxx < 0.0) | (hyy < 0.0) | ((hxx + hyy) < 0.0)
        det_h = hxx * hyy - hxy * hxy
        ridge_mask = local_max & hess_neg & (det_h > 0.0)

        hx_bwd = xp.roll(hx_dev, 1, axis=0)
        hx_fwd = xp.roll(hx_dev, -1, axis=0)
        hy_bwd = xp.roll(hy_dev, 1, axis=1)
        hy_fwd = xp.roll(hy_dev, -1, axis=1)
        dx2 = hx_dev[1:-1] + 0.5 * (hx_bwd[1:-1] + hx_fwd[1:-1])
        dy2 = hy_dev[:, 1:-1] + 0.5 * (hy_bwd[:, 1:-1] + hy_fwd[:, 1:-1])
        gx = xp.zeros_like(xi)
        gy = xp.zeros_like(xi)
        gx[1:-1, :] = (xi[2:, :] - xi[:-2, :]) / dx2
        gy[:, 1:-1] = (xi[:, 2:] - xi[:, :-2]) / dy2
        grad_mag = xp.sqrt(gx * gx + gy * gy)
        tol = 0.5 * xp.max(grad_mag)
        ridge_mask = ridge_mask & (grad_mag < tol + 1e-30)
        return ridge_mask

    def _find_crossings(self, phi):
        xp = self._xp
        cx = xp.asarray(self._grid.coords[0])
        cy = xp.asarray(self._grid.coords[1])
        parts = []

        p, p1 = phi[:-1, :], phi[1:, :]
        mask = (p * p1) < 0.0
        if bool(xp.any(mask)):
            ii, jj = xp.where(mask)
            denom = xp.abs(p[ii, jj]) + xp.abs(p1[ii, jj])
            frac = xp.abs(p[ii, jj]) / xp.where(denom > 0.0, denom, 1.0)
            xk = cx[ii] + frac * (cx[ii + 1] - cx[ii])
            yk = cy[jj]
            parts.append(xp.stack([xk, yk], axis=1))

        p, p1 = phi[:, :-1], phi[:, 1:]
        mask = (p * p1) < 0.0
        if bool(xp.any(mask)):
            ii, jj = xp.where(mask)
            denom = xp.abs(p[ii, jj]) + xp.abs(p1[ii, jj])
            frac = xp.abs(p[ii, jj]) / xp.where(denom > 0.0, denom, 1.0)
            xk = cx[ii]
            yk = cy[jj] + frac * (cy[jj + 1] - cy[jj])
            parts.append(xp.stack([xk, yk], axis=1))

        if not parts:
            return None
        return xp.concatenate(parts, axis=0)
