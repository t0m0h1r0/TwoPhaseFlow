"""Ridge extraction helpers for ridge-eikonal reinitialization."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .ridge_eikonal_kernels import _sigma_eff_kernel

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver


class RidgeExtractor:
    """Gaussian-xi ridge extraction on non-uniform grids."""

    def __init__(
        self,
        backend: "Backend",
        grid,
        sigma_0: float = 3.0,
        h_ref: float | None = None,
        wall_closure: bool = True,
        wall_axes: tuple[bool, ...] | None = None,
        ccd: "CCDSolver | None" = None,
    ):
        self._xp = backend.xp
        self._grid = grid
        self._ccd = ccd
        self._sigma_0 = float(sigma_0)
        if wall_axes is None:
            wall_axes = tuple(bool(wall_closure) for _axis in range(grid.ndim))
        self._wall_axes = tuple(bool(value) for value in wall_axes)
        self._wall_closure = any(self._wall_axes)
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

    def compute_xi_ridge(self, phi, extra_points=None) -> "array":
        xp = self._xp
        phi = xp.asarray(phi)
        crossings = self._find_crossings(phi)
        if extra_points:
            points = xp.asarray(extra_points, dtype=phi.dtype)
            crossings = points if crossings is None or crossings.shape[0] == 0 else xp.concatenate([crossings, points], axis=0)
        if crossings is None or crossings.shape[0] == 0:
            return xp.zeros_like(phi)
        if self._wall_closure:
            crossings = self._with_wall_reflections(crossings)

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

        if self._ccd is not None:
            gx, hxx = self._ccd.differentiate(xi, 0)
            gy, hyy = self._ccd.differentiate(xi, 1)
            hxy = self._ccd.first_derivative(gx, 1)
        else:
            if not self._grid.uniform:
                raise ValueError(
                    "non-uniform ridge extraction requires CCDSolver; "
                    "low-order Hessian fallback is not permitted"
                )
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

        hess_neg = (hxx < 0.0) | (hyy < 0.0) | ((hxx + hyy) < 0.0)
        det_h = hxx * hyy - hxy * hxy
        ridge_mask = local_max & hess_neg & (det_h > 0.0)
        boundary_ridge = xp.zeros_like(xi, dtype=bool)
        if self._axis_wall(0):
            boundary_ridge[0, 1:-1] = (
                (xi[0, 1:-1] > xi[0, :-2])
                & (xi[0, 1:-1] > xi[0, 2:])
                & (xi[0, 1:-1] >= xi[1, 1:-1])
                & (hyy[0, 1:-1] < 0.0)
            )
            boundary_ridge[-1, 1:-1] = (
                (xi[-1, 1:-1] > xi[-1, :-2])
                & (xi[-1, 1:-1] > xi[-1, 2:])
                & (xi[-1, 1:-1] >= xi[-2, 1:-1])
                & (hyy[-1, 1:-1] < 0.0)
            )
        if self._axis_wall(1):
            boundary_ridge[1:-1, 0] = (
                (xi[1:-1, 0] > xi[:-2, 0])
                & (xi[1:-1, 0] > xi[2:, 0])
                & (xi[1:-1, 0] >= xi[1:-1, 1])
                & (hxx[1:-1, 0] < 0.0)
            )
            boundary_ridge[1:-1, -1] = (
                (xi[1:-1, -1] > xi[:-2, -1])
                & (xi[1:-1, -1] > xi[2:, -1])
                & (xi[1:-1, -1] >= xi[1:-1, -2])
                & (hxx[1:-1, -1] < 0.0)
            )

        grad_mag = xp.sqrt(gx * gx + gy * gy)
        tol = 0.5 * xp.max(grad_mag)
        ridge_mask = (ridge_mask & (grad_mag < tol + 1e-30)) | boundary_ridge
        return ridge_mask

    def _axis_wall(self, axis: int) -> bool:
        return axis < len(self._wall_axes) and self._wall_axes[axis]

    def _with_wall_reflections(self, crossings):
        """Mirror crossing points across solid walls for closed-domain ridges."""
        xp = self._xp
        length_x = float(self._grid.L[0])
        length_y = float(self._grid.L[1])
        point_x = crossings[:, 0]
        point_y = crossings[:, 1]
        images = []
        x_options = ("none", "low", "high") if self._axis_wall(0) else ("none",)
        y_options = ("none", "low", "high") if self._axis_wall(1) else ("none",)
        for reflect_x in x_options:
            if reflect_x == "none":
                image_x = point_x
            elif reflect_x == "low":
                image_x = -point_x
            else:
                image_x = 2.0 * length_x - point_x
            for reflect_y in y_options:
                if reflect_x == "none" and reflect_y == "none":
                    continue
                if reflect_y == "none":
                    image_y = point_y
                elif reflect_y == "low":
                    image_y = -point_y
                else:
                    image_y = 2.0 * length_y - point_y
                images.append(xp.stack([image_x, image_y], axis=1))
        if not images:
            return crossings
        return xp.concatenate([crossings, *images], axis=0)

    def _find_crossings(self, phi):
        xp = self._xp
        cx = xp.asarray(self._grid.coords[0])
        cy = xp.asarray(self._grid.coords[1])
        parts = []
        tol = 1e-12

        p, p1 = phi[:-1, :], phi[1:, :]
        mask = (p * p1) < 0.0
        ii, jj = xp.where(mask)
        denom = xp.abs(p[ii, jj]) + xp.abs(p1[ii, jj])
        frac = xp.abs(p[ii, jj]) / xp.where(denom > 0.0, denom, 1.0)
        xk = cx[ii] + frac * (cx[ii + 1] - cx[ii])
        yk = cy[jj]
        parts.append(xp.stack([xk, yk], axis=1))

        p, p1 = phi[:, :-1], phi[:, 1:]
        mask = (p * p1) < 0.0
        ii, jj = xp.where(mask)
        denom = xp.abs(p[ii, jj]) + xp.abs(p1[ii, jj])
        frac = xp.abs(p[ii, jj]) / xp.where(denom > 0.0, denom, 1.0)
        xk = cx[ii]
        yk = cy[jj] + frac * (cy[jj + 1] - cy[jj])
        parts.append(xp.stack([xk, yk], axis=1))

        zero_i, zero_j = xp.where(xp.abs(phi) <= tol)
        if zero_i.shape[0] > 0:
            xk = cx[zero_i]
            yk = cy[zero_j]
            parts.append(xp.stack([xk, yk], axis=1))

        return xp.concatenate(parts, axis=0)
