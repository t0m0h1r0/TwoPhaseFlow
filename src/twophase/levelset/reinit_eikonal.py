"""
Eikonal-based reinitialization: unified shape + thickness correction.

Theory (WIKI-T-042):
  ∂φ/∂τ + sgn(φ₀)(|∇φ| − 1) = 0  (Sussman et al. 1994)
  ψ(i,j) = H_{ε(i,j)}(φ(i,j)),  ε(i,j) = ε_ξ · max(hₓ(i), h_y(j))

Replaces split (shape) + DGR (thickness) with one PDE + local-ε reconstruction:
  - Eikonal preserves zero-set → shape correct
  - |∇φ|=1 guaranteed → thickness = 2ε per cell → uniform on non-uniform grids
  - No global-median scale → no non-uniform sharpening artefact (CHK-135 root cause)

ZSP (zero-set protection, CHK-137):
  Cells with |φ₀| < h_min/2 are frozen during the Godunov sweep.
  Eliminates per-call discrete zero-set drift that accumulated into mode-2 error (CHK-136).
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
    - ZSP: zero-set protection freezes cells near φ=0 → no discrete drift (CHK-137)

    See WIKI-T-042 for proofs and benchmarks.
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
        zsp: bool = True,
        xi_sdf: bool = False,
    ):
        self._xp = backend.xp
        self._grid = grid
        self._eps = float(eps)
        self._n_iter = n_iter
        self._mass_correction = mass_correction
        self._zsp = zsp
        self._xi_sdf = xi_sdf

        # Minimum grid spacing (NumPy, host-side — grid.h is always CPU)
        h_min = float(min(np.min(grid.h[ax]) for ax in range(grid.ndim)))
        self._h_min = h_min
        self._dtau = dtau_factor * h_min

        # ε_ξ = eps / h_min: number of cells spanning the interface
        eps_xi = float(eps) / h_min
        self._eps_xi = eps_xi

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
        if self._xi_sdf:
            # Non-iterative ξ-space SDF: exact zero-set preservation, no drift
            phi = self._xi_sdf_phi(phi)
            eps_arr = self._eps_xi   # constant in ξ-space (scalar)
        else:
            # Iterative Godunov sweep with ZSP
            phi = self._godunov_sweep(phi, sgn0)
            eps_arr = self._eps_arr

        # Step 3: ψ = H_{ε}(φ)
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
        """Godunov upwind Eikonal: ∂φ/∂τ + sgn(φ₀)(|∇φ|−1) = 0.

        ZSP (zero-set protection, CHK-137): cells with |φ₀| < h_min/2 are
        frozen throughout the sweep to prevent discrete zero-set drift.
        """
        xp = self._xp
        dtau = self._dtau
        hx_f = self._hx_fwd   # (Nx+1, 1)
        hx_b = self._hx_bwd
        hy_f = self._hy_fwd   # (1, Ny+1)
        hy_b = self._hy_bwd

        inside = sgn0 > 0

        # ZSP mask: freeze cells within half a grid cell of the zero-set
        if self._zsp:
            zsp_frozen = xp.abs(phi) < 0.5 * self._h_min

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
            phi_new = phi - dtau * sgn0 * G

            if self._zsp:
                phi = xp.where(zsp_frozen, phi, phi_new)
            else:
                phi = phi_new

        return phi

    def _xi_sdf_phi(self, phi_dev):
        """Non-iterative ξ-SDF: assign each cell the signed ξ-distance to the nearest
        zero-crossing in the discrete grid (sub-cell interpolated).

        Advantages over Godunov sweep:
        - No iteration → no per-call discrete zero-set drift (eliminates CHK-136 root cause)
        - Zero-crossings found from original ψ field → zero-set exactly preserved
        - |∇_ξ φ_ξ| = 1 by construction (true signed distance function)

        Works on CPU (NumPy array operations). GPU inputs are converted host-side.
        """
        phi_np = np.asarray(phi_dev)    # (Nx, Ny), CPU
        sgn = np.sign(phi_np)
        Nx, Ny = phi_np.shape

        # Find sub-cell zero-crossings in each axis direction
        cx_list = []    # (xi_float, eta_float) crossing positions

        # x-direction: (i,j) → (i+1,j)
        px = phi_np[:-1, :]
        px1 = phi_np[1:, :]
        xi_mask = (px * px1) < 0.0
        if xi_mask.any():
            ii, jj = np.where(xi_mask)
            denom = np.abs(px[ii, jj]) + np.abs(px1[ii, jj])
            alpha = np.abs(px[ii, jj]) / np.where(denom > 0, denom, 1.0)
            for k in range(len(ii)):
                cx_list.append((float(ii[k]) + float(alpha[k]), float(jj[k])))

        # y-direction: (i,j) → (i,j+1)
        py = phi_np[:, :-1]
        py1 = phi_np[:, 1:]
        eta_mask = (py * py1) < 0.0
        if eta_mask.any():
            ii, jj = np.where(eta_mask)
            denom = np.abs(py[ii, jj]) + np.abs(py1[ii, jj])
            alpha = np.abs(py[ii, jj]) / np.where(denom > 0, denom, 1.0)
            for k in range(len(ii)):
                cx_list.append((float(ii[k]), float(jj[k]) + float(alpha[k])))

        if not cx_list:
            return phi_dev   # no interface found; leave φ unchanged

        crossings = np.array(cx_list, dtype=np.float64)   # (N_cross, 2)

        # Vectorised minimum ξ-distance: (Nx, Ny, N_cross) → min over crossings
        I = np.arange(Nx, dtype=np.float64).reshape(-1, 1, 1)   # (Nx,1,1)
        J = np.arange(Ny, dtype=np.float64).reshape(1, -1, 1)   # (1,Ny,1)
        kx = crossings[:, 0].reshape(1, 1, -1)                  # (1,1,N_cross)
        ky = crossings[:, 1].reshape(1, 1, -1)
        d = np.sqrt((I - kx) ** 2 + (J - ky) ** 2)             # (Nx,Ny,N_cross)
        dist_min = np.min(d, axis=2)                             # (Nx,Ny)

        phi_xi = sgn * dist_min
        return self._xp.asarray(phi_xi)
