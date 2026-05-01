"""
Shared operations for CLS reinitialization strategies.

Pure functions extracted from Reinitializer for reusability (DRY).
All functions take explicit parameters — no class state dependency.
"""

from __future__ import annotations
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


def _axis_bc(bc, axis: int) -> str:
    if isinstance(bc, (tuple, list)):
        return str(bc[axis]).strip().lower()
    return str(bc).strip().lower()


def compute_dtau(grid, eps) -> float:
    """Pseudo-time step (eq:dtau_reinit_def).

    Uses the actual minimum cell spacing (not the nominal L/N) so that
    the CFL condition is satisfied on non-uniform grids.

    *eps* may be a scalar or an array (ξ-space local eps); the minimum
    value is used for the CFL bound.
    """
    import numpy as _np
    ndim = grid.ndim
    dx_min = min(float(grid.h[ax].min()) for ax in range(ndim))
    eps_min = float(_np.min(eps))
    dtau_para = 0.5 * dx_min**2 / (2.0 * ndim * eps_min)
    dtau_hyp = 0.5 * dx_min
    return min(dtau_para, dtau_hyp)


def compute_gradient_normal(xp, psi, ccd: "CCDSolver"):
    """Compute gradient components and unit normal n̂ = ∇ψ/|∇ψ|.

    Returns (dpsi, n_hat, safe_grad) where dpsi is list of per-axis gradients.

    The ``safe_grad`` floor is 1e-6 (CHK-168): below this, |∇ψ| is dominated by
    CCD round-off (ULP-level) and the 1/|∇ψ| amplification would turn the ODD
    y-flip ULP asymmetry into O(1e-3) noise in n̂.  The interface has
    |∇ψ| ~ 1/(2ε) ~ O(30), well above the floor, so values near the interface
    are unchanged (interface bit-exactness preserved on any grid).  The floor
    affects only the bulk where ψ(1-ψ) → 0 and the n̂ direction is physically
    undefined.
    """
    ndim = psi.ndim
    dpsi = []
    for ax in range(ndim):
        g1, _ = ccd.differentiate(psi, ax)
        dpsi.append(g1)
    grad_sq = sum(g * g for g in dpsi)
    safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-12)), 1e-6)
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
        g_pad = _pad_bc(xp, g_prime, ax, 1, _axis_bc(bc, ax))
        return (g_pad[sl_c]
                + eps_d * (g_pad[sl_p1] - 2.0 * g_pad[sl_c]
                           + g_pad[sl_m1]))
    else:
        g_xi, _ = ccd.differentiate(flux, ax, apply_metric=False)
        g_xi_pad = _pad_bc(xp, g_xi, ax, 1, _axis_bc(bc, ax))
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


def build_cn_factors(grid, eps: float, dtau: float, axis: int, backend=None):
    """Pre-compute Thomas factors for A_L = M₂ − μ B₂ along ``axis``.

    Returns (factors, modified_diag, super_diag, A_inv_dev) where the
    fourth element is a device-side dense inverse used by the GPU hot
    path of :func:`cn_diffusion_axis`. ``A_inv_dev`` is ``None`` on CPU.

    The dense-inverse trick mirrors CHK-117/119 for the CCD wall solver:
    ``cuSOLVER`` LU dispatch overhead dominates a per-call solve, so we
    pre-compute ``A_inv`` once at construction and reduce the GPU hot
    path to a single ``cuBLAS`` DGEMM (``A_inv_dev @ rhs_flat``). The
    Thomas factors are kept for the CPU path so PR-5 bit-exactness is
    preserved on the NumPy backend.

    On non-uniform grids, uses the minimum cell spacing along the axis
    to ensure the CN stability condition is satisfied everywhere.
    On uniform grids, min(h) == L/N, preserving bit-exact results.
    """
    import numpy as np
    h = float(grid.h[axis].min())
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

    A_inv_dev = None
    if backend is not None and backend.is_gpu():
        A = np.diag(main) + np.diag(sup, k=1) + np.diag(sub, k=-1)
        A_inv = np.linalg.solve(A, np.eye(n))
        A_inv_dev = backend.xp.asarray(A_inv)

    return factors, m, sup, A_inv_dev


def cn_diffusion_axis(xp, psi, axis, eps, dtau, h, cn_factors):
    """One CN diffusion half-step along ``axis`` (ADI sweep).

    Solves: (M₂ − μ B₂) ψ_new = (M₂ + μ B₂) ψ   per 1-D pencil.

    GPU path uses the cached dense inverse from :func:`build_cn_factors`
    (one cuBLAS DGEMM, O(n²) per pencil instead of 2n sequential kernel
    launches). CPU path keeps the Python Thomas sweep for bit-exactness.
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

    thomas_f, m_diag, sup, A_inv_dev = cn_factors

    if A_inv_dev is not None:
        # GPU hot path: dense matmul (CHK-117/119 idiom).
        batch_shape = rhs.shape[1:]
        rhs_flat = rhs.reshape(n, -1)
        x_flat = A_inv_dev @ rhs_flat
        x = x_flat.reshape((n,) + batch_shape)
    else:
        # CPU bit-exact path: original Python Thomas sweep.
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
    dV = grid.cell_volumes()
    return float(xp.sum(psi * (1.0 - psi) * dV))
