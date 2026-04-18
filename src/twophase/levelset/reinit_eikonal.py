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
    - FMM: Fast Marching Method — C¹ SDF, no Voronoi kinks (CHK-138)

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
        fmm: bool = False,
    ):
        self._xp = backend.xp
        self._grid = grid
        self._eps = float(eps)
        self._n_iter = n_iter
        self._mass_correction = mass_correction
        self._zsp = zsp
        self._xi_sdf = xi_sdf
        self._fmm = fmm

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
        # Device scalar — no GPU sync forced here.
        M_old = xp.sum(psi * dV)

        # Step 1: ψ → φ via logit inversion (clamped)
        phi = invert_heaviside(xp, psi, self._eps)
        sgn0 = xp.sign(phi)
        # Cells exactly on zero-set: treat as inside (positive)
        sgn0 = xp.where(xp.abs(phi) < 1e-10, 1.0, sgn0)

        # Step 2: Eikonal redistancing — restore |∇φ| = 1
        if self._fmm:
            # Fast Marching Method: C¹ SDF, no Voronoi kinks (CHK-138)
            phi = self._fmm_phi(phi)
            eps_arr = self._eps_xi
        elif self._xi_sdf:
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
            W = xp.sum(w * dV)          # device scalar
            if float(W) > 1e-14:        # one sync: needed for Python guard
                M_new = xp.sum(psi_new * dV)   # device scalar
                delta_phi = (M_old - M_new) / W  # device scalar arithmetic
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
        """Non-iterative ξ-SDF: signed ξ-distance to nearest zero-crossing.

        Unified xp implementation — runs on both NumPy (CPU) and CuPy (GPU)
        with the same code path. All ops (xp.where, xp.stack, xp.concatenate,
        xp.sqrt, xp.min) are available in both backends.

        Note: (Nx, Ny, N_cross) distance tensor fits in GPU memory for
        ch13 grid sizes (N≤128). Chunking not implemented.
        """
        xp = self._xp
        sgn = xp.sign(phi_dev)
        Nx, Ny = phi_dev.shape

        cx_parts = []   # list of (n_cross, 2) arrays

        # x-direction crossings: (i,j) → (i+1,j)
        px  = phi_dev[:-1, :]
        px1 = phi_dev[1:, :]
        xi_mask = (px * px1) < 0.0
        if xp.any(xi_mask):
            ii, jj = xp.where(xi_mask)
            denom = xp.abs(px[ii, jj]) + xp.abs(px1[ii, jj])
            alpha = xp.abs(px[ii, jj]) / xp.where(denom > 0, denom, 1.0)
            cx_parts.append(xp.stack(
                [ii.astype(xp.float64) + alpha.astype(xp.float64),
                 jj.astype(xp.float64)],
                axis=1,
            ))

        # y-direction crossings: (i,j) → (i,j+1)
        py  = phi_dev[:, :-1]
        py1 = phi_dev[:, 1:]
        eta_mask = (py * py1) < 0.0
        if xp.any(eta_mask):
            ii, jj = xp.where(eta_mask)
            denom = xp.abs(py[ii, jj]) + xp.abs(py1[ii, jj])
            alpha = xp.abs(py[ii, jj]) / xp.where(denom > 0, denom, 1.0)
            cx_parts.append(xp.stack(
                [ii.astype(xp.float64),
                 jj.astype(xp.float64) + alpha.astype(xp.float64)],
                axis=1,
            ))

        if not cx_parts:
            return phi_dev   # no interface found; leave φ unchanged

        crossings = xp.concatenate(cx_parts, axis=0)   # (N_cross, 2)

        # Vectorised ξ-distance: broadcast (Nx, Ny, N_cross)
        I  = xp.arange(Nx, dtype=xp.float64).reshape(-1, 1, 1)
        J  = xp.arange(Ny, dtype=xp.float64).reshape(1, -1, 1)
        kx = crossings[:, 0].reshape(1, 1, -1)
        ky = crossings[:, 1].reshape(1, 1, -1)
        return sgn * xp.min(xp.sqrt((I - kx) ** 2 + (J - ky) ** 2), axis=2)

    def _xi_sdf_phi_cpu(self, phi_dev):
        """DO NOT DELETE — CPU sequential baseline (CHK-137, bit-exact reference).

        Original implementation using Python for-loops and numpy D2H conversion.
        Superseded by _xi_sdf_phi() (unified xp); kept for regression testing.
        """
        phi_np = phi_dev.get() if hasattr(phi_dev, 'get') else np.asarray(phi_dev)
        sgn = np.sign(phi_np)
        Nx, Ny = phi_np.shape

        cx_list = []
        px = phi_np[:-1, :]
        px1 = phi_np[1:, :]
        xi_mask = (px * px1) < 0.0
        if xi_mask.any():
            ii, jj = np.where(xi_mask)
            denom = np.abs(px[ii, jj]) + np.abs(px1[ii, jj])
            alpha = np.abs(px[ii, jj]) / np.where(denom > 0, denom, 1.0)
            for k in range(len(ii)):
                cx_list.append((float(ii[k]) + float(alpha[k]), float(jj[k])))

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
            return phi_dev
        crossings = np.array(cx_list, dtype=np.float64)
        I = np.arange(Nx, dtype=np.float64).reshape(-1, 1, 1)
        J = np.arange(Ny, dtype=np.float64).reshape(1, -1, 1)
        kx = crossings[:, 0].reshape(1, 1, -1)
        ky = crossings[:, 1].reshape(1, 1, -1)
        phi_xi = sgn * np.min(np.sqrt((I - kx) ** 2 + (J - ky) ** 2), axis=2)
        return self._xp.asarray(phi_xi)

    def _fmm_phi(self, phi_dev):
        """Fast Marching Method (Sethian 1996): single-pass Eikonal solver.

        Avoids Voronoi gradient kinks of ξ-SDF by propagating via the Godunov
        quadratic update, producing a C¹-smooth signed distance field (CHK-138).

        Algorithm:
          1. Seed cells adjacent to zero-crossings with sub-cell distances
          2. Dijkstra-like propagation: process cells in ascending distance order
          3. Update neighbours using frozen accepted values + quadratic stencil

        Works on CPU (NumPy). GPU inputs are converted host-side.
        """
        import heapq

        phi_np = phi_dev.get() if hasattr(phi_dev, 'get') else np.asarray(phi_dev)
        sgn = np.sign(phi_np)
        sgn = np.where(np.abs(phi_np) < 1e-10, 1.0, sgn)
        Nx, Ny = phi_np.shape

        INF = 1e30
        dist = np.full((Nx, Ny), INF)
        frozen = np.zeros((Nx, Ny), dtype=bool)
        heap = []

        def _push(i, j, d):
            if 0 <= i < Nx and 0 <= j < Ny and not frozen[i, j] and d < dist[i, j]:
                dist[i, j] = d
                heapq.heappush(heap, (d, i, j))

        # Seed: cells adjacent to zero-crossings (sub-cell linear interpolation)
        for axis in range(2):
            if axis == 0:
                p, p1 = phi_np[:-1, :], phi_np[1:, :]
            else:
                p, p1 = phi_np[:, :-1], phi_np[:, 1:]
            mask = (p * p1) < 0.0
            if mask.any():
                ii, jj = np.where(mask)
                denom = np.abs(p[ii, jj]) + np.abs(p1[ii, jj])
                alpha = np.abs(p[ii, jj]) / np.where(denom > 0, denom, 1.0)
                for k in range(len(ii)):
                    a = float(alpha[k])
                    i0, j0 = int(ii[k]), int(jj[k])
                    if axis == 0:
                        _push(i0,     j0, a)
                        _push(i0 + 1, j0, 1.0 - a)
                    else:
                        _push(i0, j0,     a)
                        _push(i0, j0 + 1, 1.0 - a)

        if not heap:
            return phi_dev

        # FMM propagation: accept minimum-distance cell, update its 4 neighbours
        while heap:
            d, i, j = heapq.heappop(heap)
            if frozen[i, j]:
                continue
            frozen[i, j] = True

            for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                if not (0 <= ni < Nx and 0 <= nj < Ny) or frozen[ni, nj]:
                    continue

                # Minimum accepted distance from x-neighbours
                ax = INF
                if ni > 0 and frozen[ni - 1, nj]:     ax = min(ax, dist[ni - 1, nj])
                if ni < Nx - 1 and frozen[ni + 1, nj]: ax = min(ax, dist[ni + 1, nj])
                # Minimum accepted distance from y-neighbours
                ay = INF
                if nj > 0 and frozen[ni, nj - 1]:     ay = min(ay, dist[ni, nj - 1])
                if nj < Ny - 1 and frozen[ni, nj + 1]: ay = min(ay, dist[ni, nj + 1])

                if ax == INF and ay == INF:
                    continue
                elif ax == INF:
                    d_new = ay + 1.0
                elif ay == INF:
                    d_new = ax + 1.0
                else:
                    diff = ax - ay
                    if diff * diff >= 1.0:
                        # Caustic regime: 1D update from closer neighbour
                        d_new = min(ax, ay) + 1.0
                    else:
                        # Quadratic update: solves (d-ax)²+(d-ay)²=1
                        d_new = 0.5 * (ax + ay + np.sqrt(2.0 - diff * diff))

                _push(ni, nj, d_new)

        phi_fmm = sgn * dist
        return self._xp.asarray(phi_fmm)
