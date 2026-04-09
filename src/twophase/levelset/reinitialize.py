"""
Conservative Level Set reinitialization.

Implements the operator-split scheme described in §5c (alg:cls_reinit_dccd):

    Each pseudo-time step τ:
      Stage 1 – Compression  (explicit Forward Euler, Dissipative CCD):
          ψ** = ψ − Δτ ∇·[ψ(1−ψ) n̂]
      Stage 2 – Diffusion    (Crank–Nicolson ADI, CCD Eq-II matrices):
          (M₂ − μ B₂) ψ^{τ+1} = (M₂ + μ B₂) ψ**   per axis (ADI)
          where μ = ε Δτ / (2h²)

Pseudo-time step (eq:dtau_reinit_def):
    Δτ = min(0.5 h²/(2 ndim ε),  0.5 h_min)

M₂ = tridiag(β₂, 1, β₂)  with β₂ = −1/8
B₂ = tridiag(a₂, −2a₂, a₂) with a₂ = 3

Boundary conditions (Neumann, ∂ψ/∂n = 0):
    Off-diagonal entry at boundary rows doubled (ghost-cell reflection).
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING, List, Tuple

from ..interfaces.levelset import IReinitializer
from .advection import _weno5_pos, _weno5_neg, _pad_bc
from .heaviside import heaviside, invert_heaviside


def _sl(ndim: int, axis: int, start, stop) -> tuple:
    """Return an index tuple that slices ``axis`` from ``start`` to ``stop``."""
    s = [slice(None)] * ndim
    s[axis] = slice(start, stop)
    return tuple(s)

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


# ── CCD Eq-II coefficients (§4 Table 1 / Chu & Fan 1998) ─────────────────
_BETA2 = -1.0 / 8.0   # M₂ off-diagonal coefficient
_A2    =  3.0           # B₂ coefficient  (B₂ diagonal = −2a₂ = −6)
_EPS_D_COMP = 0.05      # Dissipative CCD filter strength ε_d (§5 eq:eps_adv)


class Reinitializer(IReinitializer):
    """Reinitialize ψ using operator-split Dissipative CCD + CN diffusion.

    Parameters
    ----------
    backend  : Backend
    grid     : Grid
    ccd      : CCDSolver — injected; used for gradient / divergence
    eps      : interface thickness ε
    n_steps  : pseudo-time steps per call  (default 4, §09_full_algorithm Step 2)
    bc       : boundary condition type for compression flux normal
               'periodic' | 'neumann' (default)
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero',
                 unified_dccd: bool = False,
                 mass_correction: bool = True,
                 eps_d_comp: float = _EPS_D_COMP,
                 method: str = 'split'):
        self.xp      = backend.xp
        self.grid    = grid
        self.ccd     = ccd
        self.eps     = eps
        self.n_steps = n_steps
        self._bc     = bc
        self._eps_d_comp = float(eps_d_comp)
        self._unified = unified_dccd
        self._mass_correction = mass_correction
        self._method = method
        self._h      = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]

        # ── Pseudo-time step (eq:dtau_reinit_def) ────────────────────────
        ndim    = grid.ndim
        dx_min  = min(self._h)
        dtau_para = 0.5 * dx_min**2 / (2.0 * ndim * eps)   # parabolic bound
        dtau_hyp  = 0.5 * dx_min                             # hyperbolic CFL
        self.dtau = min(dtau_para, dtau_hyp)

        # ── Pre-compute CN Thomas factorizations per axis ─────────────────
        # A_L = M₂ − μ B₂  (LHS of CN solve)
        # Store: (thomas_factors, modified_diag, super_diag) per axis
        # (not needed in unified DCCD mode, but kept for operator-split path)
        self._cn_factors: List[Tuple] = []
        if not unified_dccd:
            for ax in range(ndim):
                self._cn_factors.append(self._build_cn_factors(ax))

    # ── Public API ────────────────────────────────────────────────────────

    def reinitialize(self, psi) -> "array":
        """Run n_steps pseudo-time steps on ψ.

        Two modes (selected by ``unified_dccd`` constructor flag):

        **Operator-split** (default, legacy):
          1. Compression  — explicit FE with Dissipative CCD divergence
          2. Diffusion    — CN ADI solve (x-sweep, y-sweep, …)

        **Unified DCCD** (WIKI-T-028):
          Combined RHS = −C + D with Lagrange conservation correction.
          Eliminates operator-splitting mismatch that breaks equilibrium
          identity ψ(1−ψ)n̂ = ε∇ψ.

        After all steps, an interface-weighted mass correction is applied
        to compensate for clipping losses (WIKI-T-027).
        """
        if self._method == 'dgr':
            return self._reinitialize_dgr(psi)
        if self._method == 'hybrid':
            return self._reinitialize_hybrid(psi)
        if self._unified:
            return self._reinitialize_unified(psi)
        return self._reinitialize_split(psi)

    def _reinitialize_split(self, psi) -> "array":
        """Operator-split reinitialization (legacy, pre-WIKI-T-028)."""
        xp = self.xp
        q  = xp.copy(psi)
        dV = xp.asarray(self.grid.cell_volumes())
        M_old = float(xp.sum(q * dV))

        for _ in range(self.n_steps):
            # Stage 1: compression (Forward Euler, Dissipative CCD)
            div_comp = self._dccd_compression_div(q, self.ccd)
            q_star   = xp.clip(q - self.dtau * div_comp, 0.0, 1.0)

            # Stage 2: diffusion (CN ADI, one sweep per axis)
            q_new = q_star
            for ax in range(self.grid.ndim):
                q_new = self._cn_diffusion_axis(q_new, ax)
            q = xp.clip(q_new, 0.0, 1.0)

        # ── Interface-weighted mass correction (Olsson-Kreiss basis) ──
        if self._mass_correction:
            M_new = float(xp.sum(q * dV))
            w = 4.0 * q * (1.0 - q)
            W = float(xp.sum(w * dV))
            if W > 1e-12:
                q = q + ((M_old - M_new) / W) * w
                q = xp.clip(q, 0.0, 1.0)

        return q

    def _reinitialize_unified(self, psi) -> "array":
        """Unified DCCD reinitialization (WIKI-T-028).

        Combined RHS eliminates operator-splitting mismatch:
          R = −D_DCCD[ψ(1−ψ)n̂] + ε·Σ_ax ψ''_ax
        with Lagrange conservation correction and two-stage clip repair.
        """
        xp = self.xp
        q  = xp.copy(psi)
        dV = xp.asarray(self.grid.cell_volumes())
        M_old = float(xp.sum(q * dV))

        for _ in range(self.n_steps):
            # Step 1: gradient, Laplacian, normal (single CCD call per axis)
            dpsi = []
            d2psi_sum = xp.zeros_like(q)
            for ax in range(self.grid.ndim):
                g1, g2 = self.ccd.differentiate(q, ax)
                dpsi.append(g1)
                d2psi_sum += g2

            grad_sq   = sum(g * g for g in dpsi)
            safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-28)), 1e-14)
            n_hat     = [g / safe_grad for g in dpsi]

            # Step 2: compression divergence with DCCD
            psi_1mpsi = q * (1.0 - q)
            C = xp.zeros_like(q)
            eps_d = self._eps_d_comp
            for ax in range(self.grid.ndim):
                flux_ax = psi_1mpsi * n_hat[ax]
                C = C + self._filtered_divergence(flux_ax, ax, eps_d)

            # Step 3: diffusion from CCD d2 (reuses Step 1 output)
            D = self.eps * d2psi_sum

            # Step 4: combined RHS with Lagrange conservation correction
            R = -C + D
            w = 4.0 * q * (1.0 - q)
            W = float(xp.sum(w * dV))
            R_sum = float(xp.sum(R * dV))
            if W > 1e-12:
                R = R - (R_sum / W) * w

            # Step 5: update with two-stage clip repair
            q_star = q + self.dtau * R          # mass-conserving (pre-clip)
            q_clipped = xp.clip(q_star, 0.0, 1.0)

            # Post-clip mass repair
            delta_M = float(xp.sum(q_star * dV)) - float(xp.sum(q_clipped * dV))
            if abs(delta_M) > 1e-15:
                w_clip = 4.0 * q_clipped * (1.0 - q_clipped)
                W_clip = float(xp.sum(w_clip * dV))
                if W_clip > 1e-12:
                    q_clipped = q_clipped + (delta_M / W_clip) * w_clip
                    q_clipped = xp.clip(q_clipped, 0.0, 1.0)
            q = q_clipped

        # Final mass correction for accumulated residuals
        if self._mass_correction:
            M_new = float(xp.sum(q * dV))
            w = 4.0 * q * (1.0 - q)
            W = float(xp.sum(w * dV))
            if W > 1e-12:
                q = q + ((M_old - M_new) / W) * w
                q = xp.clip(q, 0.0, 1.0)

        return q

    # ── Hybrid: Comp-Diff (shape) + DGR (thickness) ─────────────────────

    def _reinitialize_hybrid(self, psi) -> "array":
        """Hybrid reinitialization: shape restoration + thickness correction.

        Step 1: Operator-split compression-diffusion restores the sigmoid
                profile shape but introduces ~1.4× thickness broadening.
        Step 2: DGR corrects the broadened thickness back to ε.

        This avoids both failure modes:
          - Comp-diff alone: ε_eff drifts to ~4ε over many calls
          - DGR alone: no shape restoration → interface position errors
        """
        q = self._reinitialize_split(psi)
        q = self._reinitialize_dgr(q)
        return q

    # ── Direct Geometric Reinitialization (WIKI-T-030) ───────────────────

    def _reinitialize_dgr(self, psi) -> "array":
        """Direct Geometric Reinitialization (DGR).

        Restores interface thickness to ε in one step:
          1. Estimate effective ε_eff from median of ψ(1−ψ)/|∇ψ|
             in the interface band (robust to corner spikes)
          2. Compute φ_raw = ε·logit(ψ) and rescale:
             φ_sdf = φ_raw · (ε_eff / ε) to recover true SDF
          3. Reconstruct ψ_new = H_ε(φ_sdf)
          4. Interface-weighted mass correction

        See WIKI-T-030 for proofs.
        """
        xp = self.xp
        dV = xp.asarray(self.grid.cell_volumes())
        M_old = float(xp.sum(psi * dV))

        # Compute |∇ψ| via CCD
        grad_sq = xp.zeros_like(psi)
        for ax in range(self.grid.ndim):
            g1, _ = self.ccd.differentiate(psi, ax)
            grad_sq = grad_sq + g1 * g1
        grad_psi = xp.sqrt(xp.maximum(grad_sq, 1e-28))

        # Estimate ε_eff from interface band (0.05 < ψ < 0.95)
        # Identity: ε_eff = ψ(1−ψ) / |∇ψ| for ψ = H_{ε_eff}(φ)
        band = (psi > 0.05) & (psi < 0.95)
        psi_1mpsi = psi * (1.0 - psi)
        if xp.any(band):
            eps_local = psi_1mpsi[band] / xp.maximum(grad_psi[band], 1e-14)
            eps_eff = float(xp.median(eps_local))
        else:
            eps_eff = self.eps  # fallback

        # φ_raw = (ε/ε_eff)·φ_true → rescale to recover φ_true
        phi_raw = invert_heaviside(xp, psi, self.eps)
        scale = eps_eff / self.eps if eps_eff > 1e-14 else 1.0
        phi_sdf = phi_raw * scale

        # Reconstruct ψ with target thickness ε
        psi_new = heaviside(xp, phi_sdf, self.eps)

        # Step 4: mass-conserving correction (Thm 2 + Thm 3)
        M_new = float(xp.sum(psi_new * dV))
        w = 4.0 * psi_new * (1.0 - psi_new)
        W = float(xp.sum(w * dV))
        if W > 1e-12:
            psi_new = psi_new + ((M_old - M_new) / W) * w
            psi_new = xp.clip(psi_new, 0.0, 1.0)

        return psi_new

    # ── Dissipative filter helper ───────────────────────────────────────

    def _filtered_divergence(self, flux, ax, eps_d):
        """CCD derivative + dissipative filter along one axis.

        On uniform grids the filter operates in x-space.
        On non-uniform grids the filter operates in ξ-space then applies J.
        """
        xp = self.xp
        sl_c  = _sl(flux.ndim, ax, 1, -1)
        sl_p1 = _sl(flux.ndim, ax, 2, None)
        sl_m1 = _sl(flux.ndim, ax, 0, -2)

        if self.grid.uniform:
            g_prime, _ = self.ccd.differentiate(flux, ax)
            g_pad = _pad_bc(xp, g_prime, ax, 1, self._bc)
            return (g_pad[sl_c]
                    + eps_d * (g_pad[sl_p1] - 2.0 * g_pad[sl_c]
                               + g_pad[sl_m1]))
        else:
            g_xi, _ = self.ccd.differentiate(flux, ax, apply_metric=False)
            g_xi_pad = _pad_bc(xp, g_xi, ax, 1, self._bc)
            F_xi = (g_xi_pad[sl_c]
                    + eps_d * (g_xi_pad[sl_p1] - 2.0 * g_xi_pad[sl_c]
                               + g_xi_pad[sl_m1]))
            J_1d = xp.asarray(self.grid.J[ax])
            shape_J = [1] * flux.ndim
            shape_J[ax] = -1
            return J_1d.reshape(shape_J) * F_xi

    # ── Stage 1: Dissipative CCD compression divergence ──────────────────

    def _dccd_compression_div(self, psi, ccd: "CCDSolver"):
        """Compute ∇·[ψ(1−ψ) n̂] with Dissipative CCD filter."""
        xp   = self.xp
        ndim = self.grid.ndim
        eps_d = self._eps_d_comp

        dpsi = []
        for ax in range(ndim):
            g1, _ = ccd.differentiate(psi, ax)
            dpsi.append(g1)

        grad_sq   = sum(g * g for g in dpsi)
        safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-28)), 1e-14)
        n_hat     = [g / safe_grad for g in dpsi]

        psi_1mpsi = psi * (1.0 - psi)
        div_total = xp.zeros_like(psi)

        for ax in range(ndim):
            flux_ax = psi_1mpsi * n_hat[ax]
            div_total = div_total + self._filtered_divergence(flux_ax, ax, eps_d)

        return div_total

    # ── Stage 2: CN diffusion ADI ─────────────────────────────────────────

    def _cn_diffusion_axis(self, psi, axis: int):
        """One CN diffusion half-step along ``axis`` (ADI sweep).

        Solves: (M₂ − μ B₂) ψ_new = (M₂ + μ B₂) ψ   per 1-D pencil.
        Neumann BC: boundary off-diagonal entries doubled.
        """
        xp  = self.xp
        h   = self._h[axis]
        mu  = self.eps * self.dtau / (2.0 * h**2)

        # A_R coefficients
        d_R = 1.0 - 6.0 * mu   # A_R main diagonal  (1 + μ·(−6))
        c_R = _BETA2 + 3.0 * mu  # A_R off-diagonal   (β₂ + μ·a₂)

        # Move sweep axis to front: shape (n, *batch)
        psi_t = xp.moveaxis(psi, axis, 0)
        n     = psi_t.shape[0]

        # Apply A_R (vectorised, no loop)
        rhs = xp.empty_like(psi_t)
        rhs[1:-1] = c_R * psi_t[:-2] + d_R * psi_t[1:-1] + c_R * psi_t[2:]
        rhs[0]    = d_R * psi_t[0]  + 2.0 * c_R * psi_t[1]      # Neumann left
        rhs[-1]   = 2.0 * c_R * psi_t[-2] + d_R * psi_t[-1]     # Neumann right

        # Apply pre-factored A_L Thomas solve
        thomas_f, m_diag, sup = self._cn_factors[axis]

        # Forward sweep (sequential over n; vectorised over batch)
        d = xp.array(rhs)           # mutable copy
        for i in range(1, n):
            d[i] = d[i] - thomas_f[i - 1] * d[i - 1]

        # Back substitution
        x = xp.empty_like(d)
        x[-1] = d[-1] / xp.asarray(m_diag[-1])
        for i in range(n - 2, -1, -1):
            x[i] = (d[i] - xp.asarray(sup[i]) * x[i + 1]) / xp.asarray(m_diag[i])

        return xp.moveaxis(x, 0, axis)

    # ── CN Thomas factorization (pre-computed in __init__) ────────────────

    def _build_cn_factors(self, axis: int):
        """Pre-compute Thomas factors for A_L = M₂ − μ B₂ along ``axis``.

        Returns (factors, modified_diag, super_diag) as numpy float64 arrays.
        """
        h  = self._h[axis]
        mu = self.eps * self.dtau / (2.0 * h**2)
        n  = self.grid.N[axis] + 1

        d_L = 1.0 + 6.0 * mu    # A_L main diagonal
        c_L = _BETA2 - 3.0 * mu  # A_L interior off-diagonal

        # Build full tridiagonal (sub, main, sup) with Neumann BC
        main = np.full(n, d_L)
        sup  = np.full(n - 1, c_L)
        sub  = np.full(n - 1, c_L)
        sup[0]  = 2.0 * c_L   # Neumann left:  upper entry of row 0
        sub[-1] = 2.0 * c_L   # Neumann right: lower entry of row n-1

        # Thomas forward elimination → store row factors and modified diagonal
        m = main.copy()
        factors = np.empty(n - 1)
        for i in range(1, n):
            factors[i - 1] = sub[i - 1] / m[i - 1]
            m[i] -= factors[i - 1] * sup[i - 1]

        return factors, m, sup  # all numpy float64

    # ── Volume monitor ────────────────────────────────────────────────────

    def volume_monitor(self, psi) -> float:
        """M(τ) = ∫ ψ(1−ψ) dV — decreases during reinitialization."""
        dV = self.xp.asarray(self.grid.cell_volumes())
        return float(self.xp.sum(psi * (1.0 - psi) * dV))


# ── Legacy WENO5 implementation (retained for comparison / validation) ────────
#
# Prior implementation used WENO5 flux splitting + TVD-RK3 for BOTH compression
# and diffusion terms (combined RHS).  Replaced by operator-split Dissipative CCD
# + CN scheme (Reinitializer above) to match the paper (§5c).
# DO NOT DELETE — preserved for cross-validation benchmarks.


class ReinitializerWENO5(IReinitializer):
    """Reinitialize ψ via WENO5 compression + CCD diffusion, TVD-RK3 time march.

    Legacy implementation — kept for comparison against the Dissipative CCD + CN
    scheme (``Reinitializer``).  API is identical.
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero'):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.n_steps = n_steps
        self._bc = bc
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]

        _TVD_RK3_SAFETY = 0.5
        ndim = grid.ndim
        dx_min = min(float(grid.L[ax] / grid.N[ax]) for ax in range(ndim))
        dtau_para = _TVD_RK3_SAFETY * dx_min**2 / (2.0 * ndim * eps)
        dtau_hyp  = 0.5 * dx_min
        self.dtau = min(dtau_para, dtau_hyp)

    def reinitialize(self, psi) -> "array":
        xp = self.xp
        q = xp.copy(psi)
        dtau = self.dtau
        ccd = self.ccd
        for _ in range(self.n_steps):
            r0 = self._rhs(q, ccd)
            q1 = xp.clip(q + dtau * r0, 0.0, 1.0)
            r1 = self._rhs(q1, ccd)
            q2 = xp.clip(0.75 * q + 0.25 * (q1 + dtau * r1), 0.0, 1.0)
            r2 = self._rhs(q2, ccd)
            q = xp.clip((1.0 / 3.0) * q + (2.0 / 3.0) * (q2 + dtau * r2), 0.0, 1.0)
        return q

    def _rhs(self, psi, ccd: "CCDSolver"):
        xp = self.xp
        ndim = self.grid.ndim
        eps = self.eps
        dpsi = []
        d2psi_sum = xp.zeros_like(psi)
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(psi, ax)
            dpsi.append(g1)
            d2psi_sum += g2
        grad_psi_sq = sum(g * g for g in dpsi)
        safe_grad   = xp.maximum(xp.sqrt(xp.maximum(grad_psi_sq, 1e-28)), 1e-14)
        n_hat = [g / safe_grad for g in dpsi]
        psi_1mpsi = psi * (1.0 - psi)
        alpha = float(xp.max(xp.abs(psi_1mpsi)))
        alpha = max(alpha, 1e-14)
        div_compression = xp.zeros_like(psi)
        for ax in range(ndim):
            F_ax = psi_1mpsi * n_hat[ax]
            div_ax = self._weno5_compression_div(psi, F_ax, alpha, ax)
            div_compression += div_ax
        return -div_compression + eps * d2psi_sum

    def _weno5_compression_div(self, psi, F, alpha: float, axis: int):
        xp = self.xp
        n = psi.shape[axis]
        psi_p = _pad_bc(xp, psi, axis, 3, self._bc)
        F_p   = _pad_bc(xp, F,   axis, 3, self._bc)

        def sl(start, stop):
            s = [slice(None)] * psi.ndim
            s[axis] = slice(start, stop if stop != 0 else None)
            return tuple(s)

        i_max = n - 1
        fp_m2 = F_p[sl(1, 1+i_max)]; fp_m1 = F_p[sl(2, 2+i_max)]
        fp_0  = F_p[sl(3, 3+i_max)]; fp_p1 = F_p[sl(4, 4+i_max)]; fp_p2 = F_p[sl(5, 5+i_max)]
        pp_m2 = psi_p[sl(1,1+i_max)]; pp_m1 = psi_p[sl(2,2+i_max)]
        pp_0  = psi_p[sl(3,3+i_max)]; pp_p1 = psi_p[sl(4,4+i_max)]; pp_p2 = psi_p[sl(5,5+i_max)]
        Fplus_m2 = 0.5*(fp_m2+alpha*pp_m2); Fplus_m1 = 0.5*(fp_m1+alpha*pp_m1)
        Fplus_0  = 0.5*(fp_0 +alpha*pp_0 ); Fplus_p1 = 0.5*(fp_p1+alpha*pp_p1)
        Fplus_p2 = 0.5*(fp_p2+alpha*pp_p2)
        Fp_face  = _weno5_pos(xp, Fplus_m2, Fplus_m1, Fplus_0, Fplus_p1, Fplus_p2)

        fm_m1 = F_p[sl(2,2+i_max)]; fm_0  = F_p[sl(3,3+i_max)]; fm_p1 = F_p[sl(4,4+i_max)]
        fm_p2 = F_p[sl(5,5+i_max)]; fm_p3 = F_p[sl(6,6+i_max)]
        pm_m1 = psi_p[sl(2,2+i_max)]; pm_0  = psi_p[sl(3,3+i_max)]; pm_p1 = psi_p[sl(4,4+i_max)]
        pm_p2 = psi_p[sl(5,5+i_max)]; pm_p3 = psi_p[sl(6,6+i_max)]
        Fminus_m1 = 0.5*(fm_m1-alpha*pm_m1); Fminus_0  = 0.5*(fm_0 -alpha*pm_0 )
        Fminus_p1 = 0.5*(fm_p1-alpha*pm_p1); Fminus_p2 = 0.5*(fm_p2-alpha*pm_p2)
        Fminus_p3 = 0.5*(fm_p3-alpha*pm_p3)
        Fm_face   = _weno5_neg(xp, Fminus_m1, Fminus_0, Fminus_p1, Fminus_p2, Fminus_p3)

        flux_face = Fp_face + Fm_face
        h = self._h[axis]
        sl_hi = [slice(None)] * psi.ndim; sl_hi[axis] = slice(1, None)
        sl_lo = [slice(None)] * psi.ndim; sl_lo[axis] = slice(0, -1)
        div_interior = (flux_face[tuple(sl_hi)] - flux_face[tuple(sl_lo)]) / h
        shape_pad = list(psi.shape); shape_pad[axis] = 1
        pad = xp.zeros(shape_pad)
        return xp.concatenate([pad, div_interior, pad], axis=axis)

    def volume_monitor(self, psi) -> float:
        dV = self.xp.asarray(self.grid.cell_volumes())
        return float(self.xp.sum(psi * (1.0 - psi) * dV))
