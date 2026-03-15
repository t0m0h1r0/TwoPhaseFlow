"""
Conservative Level Set advection.

Implements §3.3 (Eq. 16) and §8 of the paper.

The CLS conservation equation is:

    ∂ψ/∂t + ∇·(ψ u) = 0                          (§3.3 Eq.16)

which, using ∇·u = 0, becomes the non-conservative convection form:

    ∂ψ/∂t + u·∇ψ = 0

Time integration uses the TVD-RK3 scheme (§8, Eq. 79–81).
Spatial fluxes use the WENO5 scheme (§8.2) with global Lax-Friedrichs
splitting to handle the near-discontinuous ψ profile without Gibbs
oscillations.

WENO5 smoothness indicators and weights follow (§8.2 Eq. 82):
    β₀ = (13/12)(fᵢ₋₂ − 2fᵢ₋₁ + fᵢ)²   + (1/4)(fᵢ₋₂ − 4fᵢ₋₁ + 3fᵢ)²
    β₁ = (13/12)(fᵢ₋₁ − 2fᵢ   + fᵢ₊₁)²  + (1/4)(fᵢ₋₁ − fᵢ₊₁)²
    β₂ = (13/12)(fᵢ   − 2fᵢ₊₁ + fᵢ₊₂)²  + (1/4)(3fᵢ − 4fᵢ₊₁ + fᵢ₊₂)²

Lax-Friedrichs flux splitting (§8.2 Eq. 73):
    F⁺ = (1/2)(F + α q),  F⁻ = (1/2)(F − α q)
    α = max|u|  (global Lax-Friedrichs)
"""

from __future__ import annotations
import numpy as np
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend

# WENO5 ideal weights
_D0, _D1, _D2 = 1.0 / 10.0, 6.0 / 10.0, 3.0 / 10.0
_WENO_EPS = 1e-6   # avoidance of division by zero in WENO weights


class LevelSetAdvection:
    """Advects ψ using WENO5 + TVD-RK3.

    Parameters
    ----------
    backend : Backend
    """

    def __init__(self, backend: "Backend"):
        self.xp = backend.xp
        self._h = None   # set by set_grid()

    # ── Public API ────────────────────────────────────────────────────────

    def advance(self, psi, velocity_components: List, dt: float):
        """Advance ψ by one time step using TVD-RK3.

        Parameters
        ----------
        psi                 : array, shape ``(Nx+1, Ny+1[, Nz+1])``
        velocity_components : list of arrays [u, v[, w]], same shape as psi
        dt                  : time step

        Returns
        -------
        psi_new : updated ψ array
        """
        xp = self.xp

        def L(q):
            return self._rhs(q, velocity_components)

        # TVD-RK3 (Shu-Osher scheme, §8 Eq. 79–81)
        q0 = xp.copy(psi)
        q1 = q0 + dt * L(q0)
        q2 = 0.75 * q0 + 0.25 * (q1 + dt * L(q1))
        q_new = (1.0 / 3.0) * q0 + (2.0 / 3.0) * (q2 + dt * L(q2))

        # Clamp to [0, 1] to suppress overshoots
        return xp.clip(q_new, 0.0, 1.0)

    def set_grid(self, grid) -> None:
        """Register the grid so that h is available for flux divergence."""
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]

    # ── RHS: −u·∇ψ via WENO5 ─────────────────────────────────────────────

    def _rhs(self, psi, vel):
        xp = self.xp
        ndim = len(vel)
        result = xp.zeros_like(psi)

        alpha_global = float(max(
            xp.max(xp.abs(vel[ax])) for ax in range(ndim)
        ))
        alpha_global = max(alpha_global, 1e-14)

        for ax in range(ndim):
            h = self._h[ax] if self._h is not None else 1.0
            div_f = self._weno5_divergence(psi, vel[ax], ax, alpha_global, h)
            result -= div_f   # −∂(uψ)/∂x in the non-conservative form

        return result

    # ── Vectorised WENO5 divergence along one axis ────────────────────────

    def _weno5_divergence(self, psi, u, axis: int, alpha: float, h: float):
        """Compute the WENO5 numerical flux divergence along ``axis``.

        Strategy:
        1. Pad ψ and F=uψ with 3 ghost cells on each side (wrap/zero).
        2. Compute positive flux F⁺ and negative flux F⁻ at each of the
           (n-1) internal faces between consecutive nodes.
        3. Assemble the divergence (F_{i+1/2} − F_{i-1/2}) / h.

        Here n = psi.shape[axis] (number of nodes along this axis).
        """
        xp = self.xp
        n = psi.shape[axis]   # number of nodes

        F = u * psi   # advective flux F = u·ψ

        # Pad with 3 ghost cells (using zero-padding for wall BC; does not
        # affect interior nodes for smooth flows)
        psi_p = _pad_zero(xp, psi, axis, 3)
        F_p   = _pad_zero(xp, F, axis, 3)

        # Number of internal faces: n-1 (between node 0..n-2)
        # After padding, node i maps to padded index 3+i
        # Face i+1/2 is reconstructed from stencil centred between 3+i and 3+i+1

        # Build stencil arrays for all faces simultaneously.
        # For positive flux (upwind from left): use q[k] for k = i-2..i+2
        # For negative flux (upwind from right): use q[k] for k = i-1..i+3
        # Face index i runs from 0 to n-2 (total n-1 faces)

        def sl_ax(start, stop):
            s = [slice(None)] * psi.ndim
            s[axis] = slice(start, stop if stop != 0 else None)
            return tuple(s)

        # Stencil nodes for positive reconstruction (from i-2 to i+2 around face i+1/2)
        # face i: psi_pad[3+i-2 .. 3+i+2] = psi_pad[1+i .. 5+i]
        i_max = n - 1   # number of internal faces

        # Positive flux stencils: centred at left cell of face
        fp_m2 = F_p[sl_ax(1, 1 + i_max)]   # k = i-2
        fp_m1 = F_p[sl_ax(2, 2 + i_max)]   # k = i-1
        fp_0  = F_p[sl_ax(3, 3 + i_max)]   # k = i
        fp_p1 = F_p[sl_ax(4, 4 + i_max)]   # k = i+1
        fp_p2 = F_p[sl_ax(5, 5 + i_max)]   # k = i+2

        pp_m2 = psi_p[sl_ax(1, 1 + i_max)]
        pp_m1 = psi_p[sl_ax(2, 2 + i_max)]
        pp_0  = psi_p[sl_ax(3, 3 + i_max)]
        pp_p1 = psi_p[sl_ax(4, 4 + i_max)]
        pp_p2 = psi_p[sl_ax(5, 5 + i_max)]

        # Lax-Friedrichs split: F⁺ = (F + α·ψ)/2,  F⁻ = (F − α·ψ)/2
        Fplus_m2 = 0.5 * (fp_m2 + alpha * pp_m2)
        Fplus_m1 = 0.5 * (fp_m1 + alpha * pp_m1)
        Fplus_0  = 0.5 * (fp_0  + alpha * pp_0 )
        Fplus_p1 = 0.5 * (fp_p1 + alpha * pp_p1)
        Fplus_p2 = 0.5 * (fp_p2 + alpha * pp_p2)

        # Positive WENO5 reconstruction at face i+1/2 (from left)
        Fp_face = _weno5_pos(xp, Fplus_m2, Fplus_m1, Fplus_0, Fplus_p1, Fplus_p2)

        # Negative flux stencils: centred at right cell of face (shifted by 1)
        fm_m1 = F_p[sl_ax(2, 2 + i_max)]   # k = i-1
        fm_0  = F_p[sl_ax(3, 3 + i_max)]   # k = i
        fm_p1 = F_p[sl_ax(4, 4 + i_max)]   # k = i+1
        fm_p2 = F_p[sl_ax(5, 5 + i_max)]   # k = i+2
        fm_p3 = F_p[sl_ax(6, 6 + i_max)]   # k = i+3

        pm_m1 = psi_p[sl_ax(2, 2 + i_max)]
        pm_0  = psi_p[sl_ax(3, 3 + i_max)]
        pm_p1 = psi_p[sl_ax(4, 4 + i_max)]
        pm_p2 = psi_p[sl_ax(5, 5 + i_max)]
        pm_p3 = psi_p[sl_ax(6, 6 + i_max)]

        Fminus_m1 = 0.5 * (fm_m1 - alpha * pm_m1)
        Fminus_0  = 0.5 * (fm_0  - alpha * pm_0 )
        Fminus_p1 = 0.5 * (fm_p1 - alpha * pm_p1)
        Fminus_p2 = 0.5 * (fm_p2 - alpha * pm_p2)
        Fminus_p3 = 0.5 * (fm_p3 - alpha * pm_p3)

        # Negative WENO5 reconstruction at face i+1/2 (from right)
        Fm_face = _weno5_neg(xp, Fminus_m1, Fminus_0, Fminus_p1, Fminus_p2, Fminus_p3)

        # Total face flux
        flux_face = Fp_face + Fm_face   # shape: n-1 along axis

        # Divergence: (F_{i+1/2} − F_{i-1/2}) / h at interior nodes i=1..n-2
        # For boundary nodes, use zero boundary flux (wall BC)
        sl_hi = [slice(None)] * psi.ndim
        sl_lo = [slice(None)] * psi.ndim
        sl_hi[axis] = slice(1, None)   # faces 1..n-2
        sl_lo[axis] = slice(0, -1)     # faces 0..n-3

        div_interior = (flux_face[tuple(sl_hi)] - flux_face[tuple(sl_lo)]) / h
        # div_interior has shape n-2 along axis (interior nodes i=1..n-2)

        # Pad to full size: boundary nodes get 0 divergence (wall BC)
        shape_pad = list(psi.shape)
        shape_pad[axis] = 1
        pad = xp.zeros(shape_pad)
        div_full = xp.concatenate([pad, div_interior, pad], axis=axis)

        return div_full


# ── WENO5 reconstruction kernels (vectorised) ─────────────────────────────

def _weno5_pos(xp, q0, q1, q2, q3, q4):
    """WENO5 positive flux at i+1/2 from stencil q[i-2..i+2] = q0..q4."""
    # Smoothness indicators
    b0 = (13.0/12.0)*(q0 - 2*q1 + q2)**2 + (1.0/4.0)*(q0 - 4*q1 + 3*q2)**2
    b1 = (13.0/12.0)*(q1 - 2*q2 + q3)**2 + (1.0/4.0)*(q1 - q3)**2
    b2 = (13.0/12.0)*(q2 - 2*q3 + q4)**2 + (1.0/4.0)*(3*q2 - 4*q3 + q4)**2

    a0 = _D0 / (_WENO_EPS + b0)**2
    a1 = _D1 / (_WENO_EPS + b1)**2
    a2 = _D2 / (_WENO_EPS + b2)**2
    a_sum = a0 + a1 + a2
    w0, w1, w2 = a0/a_sum, a1/a_sum, a2/a_sum

    r0 = (1.0/3.0)*q0 - (7.0/6.0)*q1 + (11.0/6.0)*q2
    r1 = -(1.0/6.0)*q1 + (5.0/6.0)*q2 + (1.0/3.0)*q3
    r2 = (1.0/3.0)*q2 + (5.0/6.0)*q3 - (1.0/6.0)*q4
    return w0*r0 + w1*r1 + w2*r2


def _weno5_neg(xp, q0, q1, q2, q3, q4):
    """WENO5 negative flux at i+1/2 from stencil q[i-1..i+3] = q0..q4."""
    b0 = (13.0/12.0)*(q0 - 2*q1 + q2)**2 + (1.0/4.0)*(q0 - 4*q1 + 3*q2)**2
    b1 = (13.0/12.0)*(q1 - 2*q2 + q3)**2 + (1.0/4.0)*(q1 - q3)**2
    b2 = (13.0/12.0)*(q2 - 2*q3 + q4)**2 + (1.0/4.0)*(3*q2 - 4*q3 + q4)**2

    a0 = _D2 / (_WENO_EPS + b0)**2
    a1 = _D1 / (_WENO_EPS + b1)**2
    a2 = _D0 / (_WENO_EPS + b2)**2
    a_sum = a0 + a1 + a2
    w0, w1, w2 = a0/a_sum, a1/a_sum, a2/a_sum

    r0 = -(1.0/6.0)*q0 + (5.0/6.0)*q1 + (1.0/3.0)*q2
    r1 = (1.0/3.0)*q1 + (5.0/6.0)*q2 - (1.0/6.0)*q3
    r2 = (11.0/6.0)*q2 - (7.0/6.0)*q3 + (1.0/3.0)*q4
    return w0*r0 + w1*r1 + w2*r2


def _pad_zero(xp, arr, axis: int, n_ghost: int):
    """Pad array along ``axis`` with n_ghost zero cells on each side."""
    shape_pad = list(arr.shape)
    shape_pad[axis] = n_ghost
    pad = xp.zeros(shape_pad)
    return xp.concatenate([pad, arr, pad], axis=axis)
