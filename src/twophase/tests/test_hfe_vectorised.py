"""
CHK-160 C3: Parity test for vectorised HermiteFieldExtension.

The new ``backend.xp`` path (field_extension.py) replaces a Python-level
``for idx in target_indices`` loop that performed per-cell ``float()`` /
``int()`` D2H syncs.  Paper-exact algorithm fidelity (PR-5) requires that
the new kernel reproduces the legacy loop to machine precision on CPU.

This test builds both paths from scratch on a uniform grid with a circular
interface, feeds the same smooth field, and asserts ``rtol=1e-14``.
"""

from __future__ import annotations
import numpy as np

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.hfe.field_extension import HermiteFieldExtension
from twophase.hfe.hermite_interp import hermite5_coeffs, hermite5_eval


class _GridConfig:
    def __init__(self, N, L):
        self.ndim = len(N)
        self.N = list(N)
        self.L = list(L)
        self.alpha_grid = 1.0


def _legacy_extend(field_data, phi, grid, ccd, band_cells):
    """Original per-cell Python-loop reference implementation."""
    xp = np
    result = xp.copy(field_data)

    dphi_dx, _ = ccd.differentiate(phi, axis=0)
    dphi_dy, _ = ccd.differentiate(phi, axis=1)
    grad_mag = xp.sqrt(dphi_dx**2 + dphi_dy**2)
    grad_mag = xp.maximum(grad_mag, 1e-14)
    nx = dphi_dx / grad_mag
    ny = dphi_dy / grad_mag

    df_dx, d2f_dx2 = ccd.differentiate(field_data, axis=0)
    df_dy, d2f_dy2 = ccd.differentiate(field_data, axis=1)
    df_xy, d2f_xy2 = ccd.differentiate(df_dx, axis=1)

    x_coords = grid.coords[0]
    y_coords = grid.coords[1]
    hx = float(grid.L[0] / grid.N[0])
    hy = float(grid.L[1] / grid.N[1])
    Nx = int(grid.N[0]) - 1
    Ny = int(grid.N[1]) - 1

    is_target = phi > 0.0
    dist_cells = xp.abs(phi) / min(hx, hy)
    in_band = is_target & (dist_cells <= band_cells)
    target_indices = xp.argwhere(in_band)

    def _h1d(ia, ib, j, xi, h, f, df, d2f):
        c = hermite5_coeffs(
            float(f[ia, j]), float(df[ia, j]), float(d2f[ia, j]),
            float(f[ib, j]), float(df[ib, j]), float(d2f[ib, j]),
            h,
        )
        return hermite5_eval(c, xi)

    for idx in target_indices:
        i, j = int(idx[0]), int(idx[1])
        phi_val = float(phi[i, j])
        x_gamma = float(x_coords[i]) - phi_val * float(nx[i, j])
        y_gamma = float(y_coords[j]) - phi_val * float(ny[i, j])
        x_gamma = max(float(x_coords[0]), min(float(x_coords[-1]), x_gamma))
        y_gamma = max(float(y_coords[0]), min(float(y_coords[-1]), y_gamma))

        ix_a = int(np.clip(np.searchsorted(x_coords, x_gamma) - 1, 0, Nx - 1))
        ix_b = ix_a + 1
        jy_a = int(np.clip(np.searchsorted(y_coords, y_gamma) - 1, 0, Ny - 1))
        jy_b = jy_a + 1
        xi_x = (x_gamma - float(x_coords[ix_a])) / hx
        xi_y = (y_gamma - float(y_coords[jy_a])) / hy

        val_ja = _h1d(ix_a, ix_b, jy_a, xi_x, hx, field_data, df_dx, d2f_dx2)
        ddy_ja = _h1d(ix_a, ix_b, jy_a, xi_x, hx, df_dy, df_xy, d2f_xy2)
        d2dy2_ja = (
            float(d2f_dy2[ix_a, jy_a]) * (1.0 - xi_x)
            + float(d2f_dy2[ix_b, jy_a]) * xi_x
        )
        val_jb = _h1d(ix_a, ix_b, jy_b, xi_x, hx, field_data, df_dx, d2f_dx2)
        ddy_jb = _h1d(ix_a, ix_b, jy_b, xi_x, hx, df_dy, df_xy, d2f_xy2)
        d2dy2_jb = (
            float(d2f_dy2[ix_a, jy_b]) * (1.0 - xi_x)
            + float(d2f_dy2[ix_b, jy_b]) * xi_x
        )
        c = hermite5_coeffs(
            val_ja, ddy_ja, d2dy2_ja,
            val_jb, ddy_jb, d2dy2_jb,
            hy,
        )
        result[i, j] = hermite5_eval(c, xi_y)

    return result


def _build(N=48):
    backend = Backend(use_gpu=False)
    gc = _GridConfig(N=[N, N], L=[1.0, 1.0])
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    return grid, ccd, backend


def test_vectorised_hfe_matches_legacy():
    """Vectorised HFE must reproduce legacy per-cell loop to rtol=1e-14."""
    grid, ccd, backend = _build(N=48)
    hfe = HermiteFieldExtension(grid, ccd, backend, band_cells=4)
    xp = backend.xp

    X, Y = grid.meshgrid()
    cx, cy, R = 0.5, 0.5, 0.25
    phi = xp.sqrt((X - cx) ** 2 + (Y - cy) ** 2) - R
    q = xp.cos(np.pi * X) * xp.cos(np.pi * Y) + 0.3 * xp.sin(3.0 * X)

    q_vec = hfe.extend(q, phi)
    q_ref = _legacy_extend(q, phi, grid, ccd, band_cells=4)

    np.testing.assert_allclose(q_vec, q_ref, rtol=1e-14, atol=1e-14)


def test_vectorised_hfe_source_phase_untouched():
    """Source cells (φ < 0) must be byte-identical to input."""
    grid, ccd, backend = _build(N=32)
    hfe = HermiteFieldExtension(grid, ccd, backend)
    xp = backend.xp

    X, Y = grid.meshgrid()
    phi = xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2) - 0.25
    q = xp.cos(np.pi * X) * xp.cos(np.pi * Y)
    q_ext = hfe.extend(q, phi)

    source = phi < 0
    assert xp.all(q_ext[source] == q[source])


def test_vectorised_hfe_random_field():
    """Random smooth-ish field + non-centered interface parity check."""
    rng = np.random.default_rng(0)
    grid, ccd, backend = _build(N=64)
    hfe = HermiteFieldExtension(grid, ccd, backend, band_cells=5)
    xp = backend.xp

    X, Y = grid.meshgrid()
    phi = xp.sqrt((X - 0.4) ** 2 + (Y - 0.55) ** 2) - 0.22
    k1 = rng.uniform(1.0, 3.0)
    k2 = rng.uniform(1.0, 3.0)
    q = xp.sin(k1 * np.pi * X) * xp.cos(k2 * np.pi * Y)

    q_vec = hfe.extend(q, phi)
    q_ref = _legacy_extend(q, phi, grid, ccd, band_cells=5)
    np.testing.assert_allclose(q_vec, q_ref, rtol=1e-13, atol=1e-14)
