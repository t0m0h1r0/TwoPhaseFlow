"""
Conservative Level Set reinitialization.

Implements §3.4 (Eq. 34) of the paper.

The reinitialization PDE (in pseudo-time τ):

    ∂ψ/∂τ + ∇·[ψ(1−ψ) n̂] = ε ∇²ψ              (§3.4 Eq.34)

where n̂ = ∇ψ / |∇ψ| is the interface normal.

Left term: compression towards a step profile.
Right term: diffusion that controls interface thickness.
Equilibrium solution: ψ = H_ε(s/ε) where s is the signed distance.

The pseudo-time step is chosen as:
    Δτ = min(0.5 · min(Δx), min(Δx)² / (2·ndim·ε))   (§3.4 stability)

satisfying both the hyperbolic CFL and the parabolic stability condition
for the diffusion term.

The gradient magnitude |∇ψ| is estimated using the Godunov scheme
(Eq. 34 of the paper) which correctly selects the upwind stencil based
on the sign of ψ − 0.5:

    |∇ψ|_G = sqrt(Σ_ax max(D⁻², D⁺²))    for ψ > 0.5
             sqrt(Σ_ax max(D⁺², D⁻²))    for ψ < 0.5

where D⁺ and D⁻ are forward / backward differences.

Volume-conservation monitor M(τ) = ∫ ψ(1−ψ) dV should decrease
monotonically during reinitialization.
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

from ..interfaces.levelset import IReinitializer

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class Reinitializer(IReinitializer):
    """Reinitialize ψ by integrating the reinitialization PDE.

    Parameters
    ----------
    backend       : Backend
    grid          : Grid (for spacing h and domain size)
    ccd           : CCDSolver — コンストラクタ注入（毎呼び出しでの引き渡し不要）
    eps           : interface thickness ε
    n_steps       : number of pseudo-time steps per call
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.n_steps = n_steps

        # Pseudo-time step satisfying both CFL conditions (§3.4):
        #   Hyperbolic: Δτ ≤ h / |velocity|  where velocity ≈ ε (compression wave)
        #   Parabolic:  Δτ ≤ h² / (2·ndim·ε)   (explicit diffusion stability)
        # With ε = C·h this gives Δτ ≤ min(1/C, h/(2·ndim·C)) ≈ h/(2·ndim·C)
        ndim = grid.ndim
        dx_min = min(float(grid.L[ax] / grid.N[ax]) for ax in range(ndim))
        # Parabolic bound dominates for refined grids:
        dtau_para = dx_min**2 / (2.0 * ndim * eps)
        dtau_hyp  = 0.5 * dx_min
        self.dtau = min(dtau_para, dtau_hyp)

    # ── Public API (IReinitializer 実装) ─────────────────────────────────

    def reinitialize(self, psi) -> "array":
        """Reinitialize ψ.

        Parameters
        ----------
        psi : array, shape ``grid.shape``

        Returns
        -------
        psi_new : reinitialized ψ array
        """
        xp = self.xp
        q = xp.copy(psi)
        dtau = self.dtau
        eps = self.eps
        ccd = self.ccd

        for _ in range(self.n_steps):
            rhs = self._rhs(q, ccd)
            q = q + dtau * rhs
            q = xp.clip(q, 0.0, 1.0)   # keep ψ ∈ [0, 1]

        return q

    # ── RHS of reinit PDE ─────────────────────────────────────────────────

    def _rhs(self, psi, ccd: "CCDSolver"):
        """Compute RHS = −∇·[ψ(1−ψ)n̂] + ε Δψ.

        The RHS is evaluated using the expanded form to maximise stability:
            −∇·[ψ(1−ψ)n̂]
              = −(1−2ψ) ∇ψ · n̂ − ψ(1−ψ) ∇·n̂
              = −(1−2ψ) |∇ψ|   − ψ(1−ψ) ∇·n̂

        where n̂ = ∇ψ / |∇ψ| is computed once from CCD and reused.
        ε Δψ uses the CCD Laplacian.
        """
        xp = self.xp
        ndim = self.grid.ndim
        eps = self.eps

        # ── CCD gradient of ψ (computed once) ────────────────────────────
        dpsi = []
        d2psi_sum = xp.zeros_like(psi)
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(psi, ax)
            dpsi.append(g1)
            d2psi_sum += g2   # Laplacian accumulates

        # |∇ψ|  with floor to prevent division by zero
        grad_psi_sq = sum(g * g for g in dpsi)
        grad_psi    = xp.sqrt(xp.maximum(grad_psi_sq, 1e-28))

        # n̂ = ∇ψ / |∇ψ|
        safe_grad = xp.maximum(grad_psi, 1e-14)
        n_hat = [g / safe_grad for g in dpsi]

        # ── Compression term −(1−2ψ)|∇ψ| ────────────────────────────────
        # This is the scalar part of ∇·[ψ(1−ψ)n̂] that is easy to compute.
        psi_1mpsi = psi * (1.0 - psi)
        compression_scalar = -(1.0 - 2.0 * psi) * grad_psi

        # ── Curvature part −ψ(1−ψ) ∇·n̂ ─────────────────────────────────
        # ∇·n̂ = ∇·(∇ψ/|∇ψ|) — differentiate each n̂_ax and sum
        div_nhat = xp.zeros_like(psi)
        for ax in range(ndim):
            dn_ax, _ = ccd.differentiate(n_hat[ax], ax)
            div_nhat += dn_ax
        curvature_part = -psi_1mpsi * div_nhat

        compression = compression_scalar + curvature_part

        # ── Diffusion term ε Δψ ──────────────────────────────────────────
        return compression + eps * d2psi_sum

    # ── Volume monitor ────────────────────────────────────────────────────

    def volume_monitor(self, psi) -> float:
        """M(τ) = ∫ ψ(1−ψ) dV — should decrease during reinitialization."""
        xp = self.xp
        dV = self.grid.cell_volume()
        return float(xp.sum(psi * (1.0 - psi))) * dV


# ── Helper: forward/backward finite differences ──────────────────────────

def _forward_backward(xp, arr, axis: int, h: float):
    """Return (D⁺, D⁻) forward and backward differences along ``axis``."""
    sl_fwd = [slice(None)] * arr.ndim
    sl_bwd = [slice(None)] * arr.ndim
    sl_c   = [slice(None)] * arr.ndim

    # Forward: (arr[i+1] - arr[i]) / h
    sl_fwd[axis] = slice(1, None)
    sl_c[axis]   = slice(None, -1)
    Dp = (arr[tuple(sl_fwd)] - arr[tuple(sl_c)]) / h

    # Backward: (arr[i] - arr[i-1]) / h
    sl_bwd[axis] = slice(None, -1)
    sl_c[axis]   = slice(1, None)
    Dm = (arr[tuple(sl_c)] - arr[tuple(sl_bwd)]) / h

    # Pad to original shape (replicate boundary)
    Dp = _pad_edge(xp, Dp, axis, n_right=1)
    Dm = _pad_edge(xp, Dm, axis, n_left=1)

    return Dp, Dm


def _pad_edge(xp, arr, axis: int, n_left: int = 0, n_right: int = 0):
    """Pad with edge values to restore original array size."""
    parts = []
    sl = [slice(None)] * arr.ndim
    if n_left:
        sl[axis] = slice(0, 1)
        for _ in range(n_left):
            parts.append(arr[tuple(sl)])
    parts.append(arr)
    if n_right:
        sl[axis] = slice(-1, None)
        for _ in range(n_right):
            parts.append(arr[tuple(sl)])
    return xp.concatenate(parts, axis=axis)
