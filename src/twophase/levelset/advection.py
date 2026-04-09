"""
Conservative Level Set advection.

Implements §3.3 (Eq. 16) and §5 of the paper.

The CLS conservation equation is:

    ∂ψ/∂t + ∇·(ψ u) = 0                          (§3.3 Eq.16)

Two schemes are provided (both use TVD-RK3, §9 eq:tvd_rk3):

DissipativeCCDAdvection  (paper-primary, §5)
--------------------------------------------
Computes ∂(ψu)/∂x via CCD first-derivative solve, then applies the
spectral filter (§5 eq:dccd_adv_filter):

    F̃ᵢ = f'ᵢ + ε_d (f'ᵢ₊₁ − 2f'ᵢ + f'ᵢ₋₁),   ε_d = 0.05

Transfer function H(ξ; 0.05) = 1 − 4·0.05·sin²(ξ/2) suppresses
high-frequency modes that are linearly unstable in pure CCD (§5
eq:ccd_adv_instability).  At Nyquist: H(π; 0.05) = 0.80 (20% damping).

ψ is clamped to [0, 1] after each TVD-RK3 stage (§5 warn:adv_clamp)
because the filter has no TVD guarantee.

LevelSetAdvection  (reference scheme, appendix app:weno5)
----------------------------------------------------------
Spatial fluxes via WENO5 + global Lax-Friedrichs splitting.

WENO5 smoothness indicators and weights follow (app:weno5 eq:weno5_beta):
    β₀ = (13/12)(fᵢ₋₂ − 2fᵢ₋₁ + fᵢ)²   + (1/4)(fᵢ₋₂ − 4fᵢ₋₁ + 3fᵢ)²
    β₁ = (13/12)(fᵢ₋₁ − 2fᵢ   + fᵢ₊₁)²  + (1/4)(fᵢ₋₁ − fᵢ₊₁)²
    β₂ = (13/12)(fᵢ   − 2fᵢ₊₁ + fᵢ₊₂)²  + (1/4)(3fᵢ − 4fᵢ₊₁ + fᵢ₊₂)²

Lax-Friedrichs flux splitting (app:weno5 eq:lf_split):
    F⁺ = (1/2)(F + α q),  F⁻ = (1/2)(F − α q)
    α = max|u|  (global Lax-Friedrichs, app:weno5 eq:alpha_glf)

Boundary ghost cells (app:weno5 sec:weno5_boundary):
    bc='periodic' — wrap indices (zero contamination, O(h⁵) preserved)
    bc='neumann'  — symmetric reflection (wall ∂ψ/∂n = 0)
    bc='outflow'  — constant extrapolation (O(h) near boundary)
    bc='zero'     — zero ghost cells (backward-compatible default)
"""

from __future__ import annotations
import numpy as np
from typing import List, TYPE_CHECKING

from ..interfaces.levelset import ILevelSetAdvection

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver

# WENO5 ideal weights (app:weno5 eq:weno5_ideal_weights)
_D0, _D1, _D2 = 1.0 / 10.0, 6.0 / 10.0, 3.0 / 10.0
_WENO_EPS = 1e-6   # avoidance of division by zero in WENO weights


class LevelSetAdvection(ILevelSetAdvection):
    """Advects ψ using WENO5 + TVD-RK3.

    Parameters
    ----------
    backend : Backend
    grid    : Grid — constructor-injected; eliminates temporal coupling from set_grid()
    """

    def __init__(self, backend: "Backend", grid: "Grid", bc: str = 'zero'):
        """
        Parameters
        ----------
        backend : Backend
        grid    : Grid — constructor-injected
        bc      : Ghost-cell boundary condition for WENO5 stencils (§4 sec:weno5_boundary).
                  'periodic' | 'neumann' | 'outflow' | 'zero' (default, backward-compat)
        """
        self.xp = backend.xp
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]
        self._bc = bc  # BCタイプを保持（_weno5_divergenceで使用）

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
            h = self._h[ax]
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
        # §4 sec:weno5_boundary に従ったゴーストセル補充
        psi_p = _pad_bc(xp, psi, axis, 3, self._bc)
        F_p   = _pad_bc(xp, F,   axis, 3, self._bc)

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
        sl_hi = [slice(None)] * psi.ndim
        sl_lo = [slice(None)] * psi.ndim
        sl_hi[axis] = slice(1, None)   # faces 1..n-2
        sl_lo[axis] = slice(0, -1)     # faces 0..n-3

        div_interior = (flux_face[tuple(sl_hi)] - flux_face[tuple(sl_lo)]) / h
        # div_interior has shape n-2 along axis (interior nodes i=1..n-2)

        if self._bc == 'periodic':
            # For periodic BC on a node-centered grid, nodes 0 and n-1 are
            # the same physical point.  The wrap-around divergence is:
            #   div[0] = (flux_face[0] − flux_face[-1]) / h
            # where flux_face[-1] is the face between node n-2 and node 0.
            # Both boundary nodes share this value; div[n-1] = div[0].
            sl_f0 = [slice(None)] * psi.ndim
            sl_fN = [slice(None)] * psi.ndim
            sl_f0[axis] = slice(0, 1)     # first face
            sl_fN[axis] = slice(-1, None) # last face (wrap-around)
            div_wrap = (flux_face[tuple(sl_f0)] - flux_face[tuple(sl_fN)]) / h
            div_full = xp.concatenate([div_wrap, div_interior, div_wrap], axis=axis)
        else:
            # Non-periodic BCs: boundary nodes get zero divergence (wall / zero / outflow)
            shape_pad = list(psi.shape)
            shape_pad[axis] = 1
            pad = xp.zeros(shape_pad)
            div_full = xp.concatenate([pad, div_interior, pad], axis=axis)

        return div_full


# ── Dissipative CCD advection (paper-primary, §5) ─────────────────────────

_EPS_D_ADV = 0.05   # uniform filter strength (§5 eq:eps_adv)


class DissipativeCCDAdvection(ILevelSetAdvection):
    """Advects ψ using Dissipative CCD + TVD-RK3 (paper §5, alg:dccd_adv).

    Algorithm per step
    ------------------
    For each axis ax:
        1.  f_i  = ψ_i · u_ax,i            (advective flux)
        2.  f'_i = CCD.differentiate(f, ax) (6th-order derivative)
        3.  F̃_i  = f'_i + ε_d(f'_{i+1} − 2f'_i + f'_{i-1})   (spectral filter)
    RHS = −Σ_ax F̃_ax
    TVD-RK3 with ψ ← clip(ψ, 0, 1) after each stage.

    Parameters
    ----------
    backend : Backend
    grid    : Grid — constructor-injected
    ccd     : CCDSolver — constructor-injected (same instance as NS solver)
    bc      : Ghost-cell BC for the filter second-difference stencil.
              'periodic' | 'neumann' | 'outflow' | 'zero'
    eps_d   : Filter strength ε_d (default 0.05, §5 eq:eps_adv)
    """

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        ccd: "CCDSolver",
        bc: str = 'periodic',
        eps_d: float = _EPS_D_ADV,
        mass_correction: bool = False,
    ):
        self.xp = backend.xp
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]
        self._ccd = ccd
        self._bc = bc
        self._eps_d = float(eps_d)
        self._mass_correction = mass_correction

    # ── Public API ────────────────────────────────────────────────────────

    def advance(self, psi, velocity_components: List, dt: float):
        """Advance ψ by one time step using TVD-RK3 with per-stage clamp.

        Parameters
        ----------
        psi                 : array, shape ``(Nx+1, Ny+1[, Nz+1])``
        velocity_components : list of arrays [u, v[, w]], same shape as psi
        dt                  : time step

        Returns
        -------
        psi_new : updated ψ array, clipped to [0, 1]
        """
        xp = self.xp

        def L(q):
            return self._rhs(q, velocity_components)

        # TVD-RK3 (Shu-Osher) with ψ ∈ [0,1] clamp after each stage
        # (§5 warn:adv_clamp — Dissipative CCD has no TVD guarantee)
        q0 = xp.copy(psi)
        if self._mass_correction:
            M_old = float(xp.sum(q0))
        q1 = xp.clip(q0 + dt * L(q0), 0.0, 1.0)
        q2 = xp.clip(0.75 * q0 + 0.25 * (q1 + dt * L(q1)), 0.0, 1.0)
        q_new = xp.clip(
            (1.0 / 3.0) * q0 + (2.0 / 3.0) * (q2 + dt * L(q2)),
            0.0, 1.0,
        )

        # ── Interface-weighted mass correction (WIKI-T-027) ──
        if self._mass_correction:
            M_new = float(xp.sum(q_new))
            w = 4.0 * q_new * (1.0 - q_new)
            W = float(xp.sum(w))
            if W > 1e-12:
                q_new = q_new + ((M_old - M_new) / W) * w
                q_new = xp.clip(q_new, 0.0, 1.0)

        return q_new

    # ── RHS: −∇·(ψu) via Dissipative CCD ────────────────────────────────

    def _rhs(self, psi, vel):
        """Compute RHS = −Σ_ax F̃_ax  (§5 alg:dccd_adv steps 1–4)."""
        xp = self.xp
        ndim = len(vel)
        result = xp.zeros_like(psi)

        for ax in range(ndim):
            # Step 1: advective flux f_i = ψ_i · u_ax,i
            f = psi * vel[ax]

            # Step 2: CCD first derivative f'_i ≈ ∂f/∂x_ax
            fp, _ = self._ccd.differentiate(f, axis=ax)

            # Step 3: Dissipative filter
            #   F̃_i = f'_i + ε_d (f'_{i+1} − 2f'_i + f'_{i-1})
            fp_pad = _pad_bc(xp, fp, ax, 1, self._bc)
            n = fp.shape[ax]

            def _sl(start, stop, _ax=ax):
                s = [slice(None)] * fp.ndim
                s[_ax] = slice(start, stop)
                return tuple(s)

            fp_p1 = fp_pad[_sl(2, n + 2)]   # f'_{i+1}
            fp_m1 = fp_pad[_sl(0, n)]        # f'_{i-1}
            F_tilde = fp + self._eps_d * (fp_p1 - 2.0 * fp + fp_m1)

            # Step 4: accumulate −∂(ψu)/∂x_ax
            result -= F_tilde

        return result


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


def _pad_bc(xp, arr, axis: int, n_ghost: int, bc_type: str):
    """Pad ``arr`` along ``axis`` with ``n_ghost`` ghost cells.

    Thin wrapper delegating to :func:`twophase.core.boundary.pad_ghost_cells`.
    Kept for backward compatibility (C2: tested code preservation).
    """
    from ..core.boundary import pad_ghost_cells
    return pad_ghost_cells(xp, arr, axis, n_ghost, bc_type)


