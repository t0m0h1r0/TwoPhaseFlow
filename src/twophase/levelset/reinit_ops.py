"""
Shared operations for CLS reinitialization strategies.

Pure functions extracted from Reinitializer for reusability (DRY).
All functions take explicit parameters — no class state dependency.
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING, List, Tuple

from .advection import _pad_bc

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


# ── CCD Eq-II coefficients (§4 Table 1 / Chu & Fan 1998) ─────────────────
_BETA2 = -1.0 / 8.0   # M₂ off-diagonal coefficient
_A2    =  3.0           # B₂ coefficient  (B₂ diagonal = −2a₂ = −6)


def _sl(ndim: int, axis: int, start, stop) -> tuple:
    """Return an index tuple that slices ``axis`` from ``start`` to ``stop``."""
    s = [slice(None)] * ndim
    s[axis] = slice(start, stop)
    return tuple(s)


def compute_dtau(grid, eps: float) -> float:
    """Pseudo-time step (eq:dtau_reinit_def)."""
    ndim = grid.ndim
    h = [float(grid.L[ax] / grid.N[ax]) for ax in range(ndim)]
    dx_min = min(h)
    dtau_para = 0.5 * dx_min**2 / (2.0 * ndim * eps)
    dtau_hyp = 0.5 * dx_min
    return min(dtau_para, dtau_hyp)


def compute_gradient_normal(xp, psi, ccd: "CCDSolver"):
    """Compute gradient components and unit normal n̂ = ∇ψ/|∇ψ|.

    Returns (dpsi, n_hat, safe_grad) where dpsi is list of per-axis gradients.
    """
    ndim = psi.ndim
    dpsi = []
    for ax in range(ndim):
        g1, _ = ccd.differentiate(psi, ax)
        dpsi.append(g1)
    grad_sq = sum(g * g for g in dpsi)
    safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-28)), 1e-14)
    n_hat = [g / safe_grad for g in dpsi]
    return dpsi, n_hat, safe_grad


def filtered_divergence(xp, flux, ax, eps_d, ccd, grid, bc):
    """CCD derivative + dissipative filter along one axis.

    On uniform grids the filter operates in x-space.
    On non-uniform grids the filter operates in ξ-space then applies J.
    """
    sl_c  = _sl(flux.ndim, ax, 1, -1)
    sl_p1 = _sl(flux.ndim, ax, 2, None)
    sl_m1 = _sl(flux.ndim, ax, 0, -2)

    if grid.uniform:
        g_prime, _ = ccd.differentiate(flux, ax)
        g_pad = _pad_bc(xp, g_prime, ax, 1, bc)
        return (g_pad[sl_c]
                + eps_d * (g_pad[sl_p1] - 2.0 * g_pad[sl_c]
                           + g_pad[sl_m1]))
    else:
        g_xi, _ = ccd.differentiate(flux, ax, apply_metric=False)
        g_xi_pad = _pad_bc(xp, g_xi, ax, 1, bc)
        F_xi = (g_xi_pad[sl_c]
                + eps_d * (g_xi_pad[sl_p1] - 2.0 * g_xi_pad[sl_c]
                           + g_xi_pad[sl_m1]))
        J_1d = xp.asarray(grid.J[ax])
        shape_J = [1] * flux.ndim
        shape_J[ax] = -1
        return J_1d.reshape(shape_J) * F_xi


def dccd_compression_div(xp, psi, ccd, grid, bc, eps_d):
    """Compute ∇·[ψ(1−ψ) n̂] with Dissipative CCD filter."""
    _, n_hat, _ = compute_gradient_normal(xp, psi, ccd)
    psi_1mpsi = psi * (1.0 - psi)
    div_total = xp.zeros_like(psi)
    for ax in range(grid.ndim):
        flux_ax = psi_1mpsi * n_hat[ax]
        div_total = div_total + filtered_divergence(xp, flux_ax, ax, eps_d, ccd, grid, bc)
    return div_total


def build_cn_factors(grid, eps: float, dtau: float, axis: int):
    """Pre-compute Thomas factors for A_L = M₂ − μ B₂ along ``axis``.

    Returns (factors, modified_diag, super_diag) as numpy float64 arrays.
    """
    h = float(grid.L[axis] / grid.N[axis])
    mu = eps * dtau / (2.0 * h**2)
    n = grid.N[axis] + 1

    d_L = 1.0 + 6.0 * mu
    c_L = _BETA2 - 3.0 * mu

    main = np.full(n, d_L)
    sup = np.full(n - 1, c_L)
    sub = np.full(n - 1, c_L)
    sup[0] = 2.0 * c_L
    sub[-1] = 2.0 * c_L

    m = main.copy()
    factors = np.empty(n - 1)
    for i in range(1, n):
        factors[i - 1] = sub[i - 1] / m[i - 1]
        m[i] -= factors[i - 1] * sup[i - 1]

    return factors, m, sup


def cn_diffusion_axis(xp, psi, axis, eps, dtau, h, cn_factors):
    """One CN diffusion half-step along ``axis`` (ADI sweep).

    Solves: (M₂ − μ B₂) ψ_new = (M₂ + μ B₂) ψ   per 1-D pencil.
    """
    mu = eps * dtau / (2.0 * h**2)
    d_R = 1.0 - 6.0 * mu
    c_R = _BETA2 + 3.0 * mu

    psi_t = xp.moveaxis(psi, axis, 0)
    n = psi_t.shape[0]

    rhs = xp.empty_like(psi_t)
    rhs[1:-1] = c_R * psi_t[:-2] + d_R * psi_t[1:-1] + c_R * psi_t[2:]
    rhs[0] = d_R * psi_t[0] + 2.0 * c_R * psi_t[1]
    rhs[-1] = 2.0 * c_R * psi_t[-2] + d_R * psi_t[-1]

    thomas_f, m_diag, sup = cn_factors

    d = xp.array(rhs)
    for i in range(1, n):
        d[i] = d[i] - thomas_f[i - 1] * d[i - 1]

    x = xp.empty_like(d)
    x[-1] = d[-1] / xp.asarray(m_diag[-1])
    for i in range(n - 2, -1, -1):
        x[i] = (d[i] - xp.asarray(sup[i]) * x[i + 1]) / xp.asarray(m_diag[i])

    return xp.moveaxis(x, 0, axis)


def volume_monitor(xp, psi, grid) -> float:
    """M(τ) = ∫ ψ(1−ψ) dV — decreases during reinitialization."""
    dV = xp.asarray(grid.cell_volumes())
    return float(xp.sum(psi * (1.0 - psi) * dV))
