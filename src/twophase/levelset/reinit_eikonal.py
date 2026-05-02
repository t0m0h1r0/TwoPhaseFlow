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
from .reinit_eikonal_distance import (
    fmm_phi as compute_reinit_fmm_phi,
    xi_sdf_phi as compute_reinit_xi_sdf_phi,
    xi_sdf_phi_cpu_legacy,
)
from .reinit_eikonal_godunov import godunov_sweep as compute_reinit_godunov_sweep
from ..core.boundary import boundary_axes, sync_periodic_image_nodes

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
    - FMM: uniform-grid Fast Marching helper — C¹ SDF, no Voronoi kinks (CHK-138)

    See WIKI-T-042 for proofs and benchmarks.

    The ``xi_sdf`` and ``fmm`` helpers are the Chapter 5 uniform-grid basis.
    On non-uniform grids, use ``RidgeEikonalReinitializer`` so the D3 physical
    FMM and D4 local-ε field from Chapter 10 are applied.  ``fmm`` is also
    rejected on GPU here because its legacy helper materialises the solve on
    the host; the GPU-resident FMM path lives in ``RidgeEikonalReinitializer``.
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
        fmm: bool = False,
        eps_scale: float = 1.0,
    ):
        self._xp = backend.xp
        self._backend = backend
        self._grid = grid
        self._eps = float(eps)
        self._n_iter = n_iter
        self._mass_correction = mass_correction
        self._zsp = zsp
        self._xi_sdf = xi_sdf
        self._fmm = fmm
        self._bc_axes = boundary_axes(getattr(ccd, "bc_type", "wall"), grid.ndim)
        if (xi_sdf or fmm) and not getattr(grid, "uniform", True):
            raise ValueError(
                "eikonal_xi/eikonal_fmm are Chapter 5 uniform-grid basis "
                "paths; use method='ridge_eikonal' for non-uniform grids "
                "so D3 physical FMM and D4 local epsilon are enforced."
            )
        if fmm and backend.is_gpu():
            raise ValueError(
                "eikonal_fmm uses a legacy CPU FMM helper and is not a "
                "GPU-resident path; use method='ridge_eikonal' on GPU."
            )

        # Minimum grid spacing (NumPy, host-side — grid.h is always CPU)
        h_min = float(min(np.min(grid.h[ax]) for ax in range(grid.ndim)))
        self._h_min = h_min
        self._dtau = dtau_factor * h_min

        # ε_ξ = eps_scale * eps / h_min: cells spanning the interface
        # eps_scale > 1 widens the interface (e.g. 1.4 matches split-only's ~1.4ε)
        eps_xi = float(eps) * float(eps_scale) / h_min
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
        sync_periodic_image_nodes(psi, self._bc_axes)
        dV = self._grid.cell_volumes()
        # Device scalar — no GPU sync forced here.
        M_old = xp.sum(psi * dV)

        # Step 1: ψ → φ via logit inversion (clamped)
        phi = invert_heaviside(xp, psi, self._eps)
        sync_periodic_image_nodes(phi, self._bc_axes)
        sgn0 = xp.sign(phi)
        # Cells exactly on zero-set: treat as inside (positive)
        sgn0 = xp.where(xp.abs(phi) < 1e-10, 1.0, sgn0)

        # Step 2: Eikonal redistancing — restore |∇φ| = 1
        if self._fmm:
            # Fast Marching Method: C¹ SDF, no Voronoi kinks (CHK-138)
            phi = self._fmm_phi(phi)
            sync_periodic_image_nodes(phi, self._bc_axes)
            eps_arr = self._eps_xi
        elif self._xi_sdf:
            # Non-iterative ξ-space SDF: exact zero-set preservation, no drift
            phi = sgn0 * xp.minimum(xp.abs(phi), 2.0 * self._eps)
            phi = self._xi_sdf_phi(phi)
            sync_periodic_image_nodes(phi, self._bc_axes)
            eps_arr = self._eps_xi   # constant in ξ-space (scalar)
        else:
            # Iterative Godunov sweep with ZSP
            phi = self._godunov_sweep(phi, sgn0)
            sync_periodic_image_nodes(phi, self._bc_axes)
            eps_arr = self._eps_arr

        # Step 3: ψ = H_{ε}(φ)
        psi_new = 1.0 / (1.0 + xp.exp(-phi / eps_arr))
        sync_periodic_image_nodes(psi_new, self._bc_axes)

        # Step 4: φ-space mass correction — uniform interface shift
        # δφ = ΔM / ∫H'_ε dV;  H'_ε(φ) = ψ(1-ψ)/ε(i,j)
        # Works with local eps_arr (per-cell H'_ε).
        if self._mass_correction:
            w = psi_new * (1.0 - psi_new) / eps_arr
            W = xp.sum(w * dV)          # device scalar
            # Guard against W≈0 without a Python-level sync (float() would force one).
            W_safe = xp.where(W > 1e-14, W, 1.0)
            gate = xp.where(W > 1e-14, 1.0, 0.0)
            M_new = xp.sum(psi_new * dV)
            delta_phi = gate * (M_old - M_new) / W_safe
            phi = phi + delta_phi
            sync_periodic_image_nodes(phi, self._bc_axes)
            if self._xi_sdf:
                # CHK-140: large delta_phi (from eps_xi mismatch at first reinit)
                # can push interface-adjacent liquid cells across zero, creating
                # false interior zero-crossings on the next reinit call.
                # Clamp: preserve cell phase relative to sgn0.
                phi = xp.where(sgn0 * phi < 0, sgn0 * 1e-14, phi)
                sync_periodic_image_nodes(phi, self._bc_axes)
            psi_new = 1.0 / (1.0 + xp.exp(-phi / eps_arr))
            sync_periodic_image_nodes(psi_new, self._bc_axes)

        return psi_new

    # ── Internal ─────────────────────────────────────────────────────────────

    def _godunov_sweep(self, phi, sgn0):
        """Godunov upwind Eikonal: ∂φ/∂τ + sgn(φ₀)(|∇φ|−1) = 0.

        ZSP (zero-set protection, CHK-137): cells with |φ₀| < h_min/2 are
        frozen throughout the sweep to prevent discrete zero-set drift.
        """
        return compute_reinit_godunov_sweep(
            self._xp,
            phi,
            sgn0,
            dtau=self._dtau,
            n_iter=self._n_iter,
            hx_fwd=self._hx_fwd,
            hx_bwd=self._hx_bwd,
            hy_fwd=self._hy_fwd,
            hy_bwd=self._hy_bwd,
            zsp=self._zsp,
            h_min=self._h_min,
        )

    def _xi_sdf_phi(self, phi_dev):
        """Non-iterative ξ-SDF: signed ξ-distance to nearest zero-crossing.

        Unified xp implementation — runs on both NumPy (CPU) and CuPy (GPU)
        with the same code path. All ops (xp.where, xp.stack, xp.concatenate,
        xp.sqrt, xp.min) are available in both backends.

        Note: (Nx, Ny, N_cross) distance tensor fits in GPU memory for
        ch13 grid sizes (N≤128). Chunking not implemented.
        """
        return compute_reinit_xi_sdf_phi(self._xp, phi_dev)

    def _xi_sdf_phi_cpu(self, phi_dev):
        """DO NOT DELETE — CPU sequential baseline (CHK-137, bit-exact reference).

        Original implementation using Python for-loops and numpy D2H conversion.
        Superseded by _xi_sdf_phi() (unified xp); kept for regression testing.
        """
        return xi_sdf_phi_cpu_legacy(self._xp, phi_dev)

    def _fmm_phi(self, phi_dev):
        """Uniform-grid CPU Fast Marching Method (Sethian 1996).

        Avoids Voronoi gradient kinks of ξ-SDF by propagating via the Godunov
        quadratic update, producing a C¹-smooth signed distance field (CHK-138).

        Algorithm:
          1. Seed cells adjacent to zero-crossings with sub-cell distances
          2. Dijkstra-like propagation: process cells in ascending distance order
          3. Update neighbours using frozen accepted values + quadratic stencil

        Works on CPU (NumPy).  The constructor rejects GPU use so this helper
        is never an implicit device-to-host reroute.
        """
        return compute_reinit_fmm_phi(self._xp, phi_dev)
