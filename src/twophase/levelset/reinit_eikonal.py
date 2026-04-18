"""
Eikonal-based reinitialization: unified shape + thickness correction.

Theory (WIKI-T-031):
  ∂φ/∂τ + sgn(φ₀)(|∇φ| − 1) = 0  (Sussman et al. 1994)
  ψ(i,j) = H_{ε(i,j)}(φ(i,j)),  ε(i,j) = ε_ξ · max(hₓ(i), h_y(j))

Replaces split (shape) + DGR (thickness) with one PDE + local-ε reconstruction:
  - Eikonal preserves zero-set → shape correct
  - |∇φ|=1 guaranteed → thickness = 2ε per cell → uniform on non-uniform grids
  - No global-median scale → no non-uniform sharpening artefact (CHK-135 root cause)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np

from .interfaces import IReinitializer
from .heaviside import invert_heaviside

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class EikonalReinitializer(IReinitializer):
    """Eikonal redistancing + cell-local ε reconstruction.

    Restores |∇φ|=1 via Godunov-upwind pseudo-time iteration
    (Sussman, Smereka, Osher 1994), then reconstructs
      ψ(i,j) = H_{ε(i,j)}(φ(i,j))
    where ε(i,j) = ε_ξ · max(hₓ(i), h_y(j)) is cell-local.

    Advantages over hybrid (split + DGR):
    - Single PDE pass, no two-step composition artefacts
    - No global-median scale → no mode-2 amplification on curved interfaces
    - Cell-local ε naturally handles non-uniform grids
    - Fold cells (|∇φ|→0) are corrected by the Eikonal PDE directly

    See WIKI-T-031 for proofs and benchmarks.
    """

    def __init__(
        self,
        backend: "Backend",
        grid,
        ccd: "CCDSolver",
        eps: float,
        n_iter: int = 20,
        dtau_factor: float = 0.5,
        mass_correction: bool = True,
        local_eps: bool = True,
    ):
        self._xp = backend.xp
        self._grid = grid
        self._eps = float(eps)
        self._n_iter = n_iter
        self._mass_correction = mass_correction

        # Minimum grid spacing (NumPy, host-side — grid.h is always CPU)
        h_min = float(min(np.min(grid.h[ax]) for ax in range(grid.ndim)))
        self._dtau = dtau_factor * h_min

        # ε_ξ = eps / h_min: number of cells spanning the interface
        eps_xi = float(eps) / h_min

        # Precompute spatial arrays on device
        xp = backend.xp
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)   # (Nx+1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)   # (1, Ny+1)

        # Cell-local epsilon: ε(i,j) = ε_ξ · max(hₓ(i), h_y(j))
        # For uniform grids this collapses to the global scalar eps.
        if local_eps:
            self._eps_arr = eps_xi * xp.maximum(hx, hy)   # (Nx+1, Ny+1)
        else:
            self._eps_arr = float(eps)

        # Precompute spacing arrays for upwind differences (device-side)
        # hx_fwd[i] = hₓ(i)   = x_{i+1} - x_i   (forward)
        # hx_bwd[i] = hₓ(i-1) = x_i - x_{i-1}   (backward, rolled by +1)
        self._hx_fwd = hx                            # (Nx+1, 1)
        self._hx_bwd = xp.roll(hx, 1, axis=0)       # h[i-1] at index i
        self._hy_fwd = hy                            # (1, Ny+1)
        self._hy_bwd = xp.roll(hy, 1, axis=1)       # h[j-1] at index j

    # ── Public API ───────────────────────────────────────────────────────────

    def reinitialize(self, psi):
        xp = self._xp
        psi = xp.asarray(psi)
        dV = self._grid.cell_volumes()
        M_old = float(xp.sum(psi * dV))

        # Step 1: ψ → φ via logit inversion (clamped)
        phi = invert_heaviside(xp, psi, self._eps)
        sgn0 = xp.sign(phi)
        # Cells exactly on zero-set: treat as inside (positive)
        sgn0 = xp.where(xp.abs(phi) < 1e-10, 1.0, sgn0)

        # Step 2: Eikonal redistancing — restore |∇φ| = 1
        phi = self._godunov_sweep(phi, sgn0)

        # Step 3: ψ = H_{ε(i,j)}(φ)  with cell-local ε
        eps_arr = self._eps_arr
        psi_new = 1.0 / (1.0 + xp.exp(-phi / eps_arr))

        # Step 4: φ-space mass correction — uniform interface shift
        # δφ = ΔM / ∫H'_ε dV;  H'_ε(φ) = ψ(1-ψ)/ε(i,j)
        # Works with local eps_arr (per-cell H'_ε).
        if self._mass_correction:
            w = psi_new * (1.0 - psi_new) / eps_arr
            W = float(xp.sum(w * dV))
            if W > 1e-14:
                M_new = float(xp.sum(psi_new * dV))
                delta_phi = (M_old - M_new) / W
                phi = phi + delta_phi
                psi_new = 1.0 / (1.0 + xp.exp(-phi / eps_arr))

        return psi_new

    # ── Internal ─────────────────────────────────────────────────────────────

    def _godunov_sweep(self, phi, sgn0):
        """Godunov upwind Eikonal: ∂φ/∂τ + sgn(φ₀)(|∇φ|−1) = 0."""
        xp = self._xp
        dtau = self._dtau
        hx_f = self._hx_fwd   # (Nx+1, 1)
        hx_b = self._hx_bwd
        hy_f = self._hy_fwd   # (1, Ny+1)
        hy_b = self._hy_bwd

        inside = sgn0 > 0

        for _ in range(self._n_iter):
            # First-order upwind differences (Neumann BC via one-sided)
            phi_x = xp.roll(phi, -1, axis=0)  # φ[i+1]
            phi_xm = xp.roll(phi, 1, axis=0)  # φ[i-1]
            phi_y = xp.roll(phi, -1, axis=1)
            phi_ym = xp.roll(phi, 1, axis=1)

            Dpx = (phi_x - phi) / hx_f    # forward  D⁺ₓ
            Dmx = (phi - phi_xm) / hx_b   # backward D⁻ₓ
            Dpy = (phi_y - phi) / hy_f
            Dmy = (phi - phi_ym) / hy_b

            # Godunov flux (Sussman et al. 1994 eq. 2.8)
            ax = xp.where(
                inside,
                xp.maximum(xp.maximum(Dmx, 0.0) ** 2, xp.minimum(Dpx, 0.0) ** 2),
                xp.maximum(xp.minimum(Dmx, 0.0) ** 2, xp.maximum(Dpx, 0.0) ** 2),
            )
            ay = xp.where(
                inside,
                xp.maximum(xp.maximum(Dmy, 0.0) ** 2, xp.minimum(Dpy, 0.0) ** 2),
                xp.maximum(xp.minimum(Dmy, 0.0) ** 2, xp.maximum(Dpy, 0.0) ** 2),
            )

            G = xp.sqrt(ax + ay + 1e-14) - 1.0
            phi = phi - dtau * sgn0 * G

        return phi
