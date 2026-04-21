"""
Unified DCCD reinitialization (WIKI-T-028).

Combined RHS eliminates operator-splitting mismatch.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .interfaces import IReinitializer
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
        self._dV = grid.cell_volumes()

    def reinitialize(self, psi):
        xp = self.xp
        # Ensure psi is on the correct device (no-op on CPU).
        q = xp.asarray(psi).copy()
        dV = self._dV
        M_old = xp.sum(q * dV)

        for _ in range(self.n_steps):
            # Step 1: gradient, Laplacian, normal
            dpsi = []
            d2psi_sum = xp.zeros_like(q)
            for ax in range(self.grid.ndim):
                g1, g2 = self.ccd.differentiate(q, ax)
                dpsi.append(g1)
                d2psi_sum += g2
            grad_sq = sum(g * g for g in dpsi)
            # CHK-169: floor raised from 1e-14 → 1e-6 (same as CHK-168 reinit_ops.py).
            # ψ(1-ψ) → 0 bulk nodes have |∇ψ| at ULP; without the higher floor, ODD
            # y-flip noise in ∂ψ/∂y would be amplified 10¹⁴× into n̂_y, then advected
            # by the backward-parabolic compression term (ASM-122-A).
            safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-12)), 1e-6)
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

            # Step 4: combined RHS with Lagrange conservation correction.
            # Device-resident 0-d scalars throughout. Preserves legacy
            # division order (R_sum / W) for bit-exactness on NumPy.
            R = -C + D
            w = 4.0 * q * (1.0 - q)
            W = xp.sum(w * dV)
            R_sum = xp.sum(R * dV)
            W_safe = xp.where(W > 1e-12, W, 1.0)
            ratio = R_sum / W_safe
            gate_W = xp.where(W > 1e-12, 1.0, 0.0)
            R = R - (gate_W * ratio) * w

            # Step 5: update with two-stage clip repair (device-side gate)
            q_star = q + self.dtau * R
            q_clipped = xp.clip(q_star, 0.0, 1.0)

            delta_M = xp.sum(q_star * dV) - xp.sum(q_clipped * dV)
            w_clip = 4.0 * q_clipped * (1.0 - q_clipped)
            W_clip = xp.sum(w_clip * dV)
            Wc_safe = xp.where(W_clip > 1e-12, W_clip, 1.0)
            repair_ratio = delta_M / Wc_safe
            gate_clip = xp.where(
                (xp.abs(delta_M) > 1e-15) & (W_clip > 1e-12), 1.0, 0.0,
            )
            q_clipped = q_clipped + (gate_clip * repair_ratio) * w_clip
            q = xp.clip(q_clipped, 0.0, 1.0)

        if self._mass_correction:
            q = apply_mass_correction(xp, q, dV, M_old)

        return q

    # ── C2: legacy reference implementation ───────────────────────────
    def _reinitialize_legacy(self, psi):
        """Pre-CuPy-sync-removal reference. DO NOT DELETE — CHK-102 baseline."""
        xp = self.xp
        q = xp.copy(psi)
        dV = self.grid.cell_volumes()
        M_old = float(xp.sum(q * dV))

        for _ in range(self.n_steps):
            dpsi = []
            d2psi_sum = xp.zeros_like(q)
            for ax in range(self.grid.ndim):
                g1, g2 = self.ccd.differentiate(q, ax)
                dpsi.append(g1)
                d2psi_sum += g2
            grad_sq = sum(g * g for g in dpsi)
            # CHK-169: legacy reference path updated to match hot-path floor
            # (1e-14 → 1e-6) — CHK-102 baseline is preserved as a structural
            # reference, not a bit-exact target (no test asserts equality).
            safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-12)), 1e-6)
            n_hat = [g / safe_grad for g in dpsi]
            psi_1mpsi = q * (1.0 - q)
            C = xp.zeros_like(q)
            eps_d = self._eps_d_comp
            for ax in range(self.grid.ndim):
                flux_ax = psi_1mpsi * n_hat[ax]
                C = C + filtered_divergence(
                    xp, flux_ax, ax, eps_d, self.ccd, self.grid, self._bc,
                )
            D = self.eps * d2psi_sum
            R = -C + D
            w = 4.0 * q * (1.0 - q)
            W = float(xp.sum(w * dV))
            R_sum = float(xp.sum(R * dV))
            if W > 1e-12:
                R = R - (R_sum / W) * w
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
            from .heaviside import apply_mass_correction_legacy
            q = apply_mass_correction_legacy(xp, q, dV, M_old)
        return q
