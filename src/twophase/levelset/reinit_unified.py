"""
Unified DCCD reinitialization (WIKI-T-028).

Combined RHS eliminates operator-splitting mismatch.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..interfaces.levelset import IReinitializer
from .heaviside import apply_mass_correction
from .reinit_ops import compute_dtau, compute_gradient_normal, filtered_divergence

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class UnifiedDCCDReinitializer(IReinitializer):
    """Unified DCCD reinitialization with Lagrange conservation correction.

    Parameters
    ----------
    backend, grid, ccd, eps, n_steps, bc, eps_d_comp, mass_correction
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero',
                 eps_d_comp: float = 0.05,
                 mass_correction: bool = True):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.n_steps = n_steps
        self._bc = bc
        self._eps_d_comp = float(eps_d_comp)
        self._mass_correction = mass_correction
        self.dtau = compute_dtau(grid, eps)

    def reinitialize(self, psi):
        xp = self.xp
        q = xp.copy(psi)
        dV = xp.asarray(self.grid.cell_volumes())
        M_old = float(xp.sum(q * dV))

        for _ in range(self.n_steps):
            # Step 1: gradient, Laplacian, normal
            dpsi = []
            d2psi_sum = xp.zeros_like(q)
            for ax in range(self.grid.ndim):
                g1, g2 = self.ccd.differentiate(q, ax)
                dpsi.append(g1)
                d2psi_sum += g2
            grad_sq = sum(g * g for g in dpsi)
            safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-28)), 1e-14)
            n_hat = [g / safe_grad for g in dpsi]

            # Step 2: compression divergence with DCCD
            psi_1mpsi = q * (1.0 - q)
            C = xp.zeros_like(q)
            eps_d = self._eps_d_comp
            for ax in range(self.grid.ndim):
                flux_ax = psi_1mpsi * n_hat[ax]
                C = C + filtered_divergence(
                    xp, flux_ax, ax, eps_d, self.ccd, self.grid, self._bc,
                )

            # Step 3: diffusion from CCD d2
            D = self.eps * d2psi_sum

            # Step 4: combined RHS with Lagrange conservation correction
            R = -C + D
            w = 4.0 * q * (1.0 - q)
            W = float(xp.sum(w * dV))
            R_sum = float(xp.sum(R * dV))
            if W > 1e-12:
                R = R - (R_sum / W) * w

            # Step 5: update with two-stage clip repair
            q_star = q + self.dtau * R
            q_clipped = xp.clip(q_star, 0.0, 1.0)

            delta_M = float(xp.sum(q_star * dV)) - float(xp.sum(q_clipped * dV))
            if abs(delta_M) > 1e-15:
                w_clip = 4.0 * q_clipped * (1.0 - q_clipped)
                W_clip = float(xp.sum(w_clip * dV))
                if W_clip > 1e-12:
                    q_clipped = q_clipped + (delta_M / W_clip) * w_clip
                    q_clipped = xp.clip(q_clipped, 0.0, 1.0)
            q = q_clipped

        if self._mass_correction:
            q = apply_mass_correction(xp, q, dV, M_old)

        return q
