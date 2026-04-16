"""
IIM stencil correction for CCD-based PPE.

Computes the RHS correction Δq that accounts for pressure jumps [p]=σκ
at interface crossings, enabling the CCD operator to maintain high-order
accuracy across the sharp interface.

Theory (docs/memo/IIM_CCD_PPE_ShortPaper.md §4):
    For an interface crossing between x_i and x_{i+1} at x* = x_i + α·h:
    The CCD Hermite system (p, p', p'') requires corrections from
    C_0=[p], C_1=[p'], C_2=[p''] at all three equation levels.

    RHS^{IIM} = RHS^{std} - W(α) · C

    where W(α) is a weight vector depending on the fractional crossing
    position α ∈ (0,1), and C = [C_0,...,C_5]^T are the jump conditions.

Architecture:
    IIMStencilCorrector: receives the CCD sparse operator L, level-set φ,
    curvature κ, and jump conditions. Produces the flat correction vector Δq.
    Stateless — all grid/operator info passed per call.

Two modes:
    1. "nearest" (zeroth-order): Only C_0=[p]=σκ correction.
       Simple, robust, O(h^2) near interface.
    2. "hermite" (high-order): C_0,C_1,C_2 corrections on all three
       CCD equation types. O(h^6) near interface (if curvature is accurate).
"""

from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.grid import Grid

from .jump_conditions import JumpConditionCalculator


class IIMStencilCorrector:
    """Compute IIM RHS correction for the CCD PPE operator.

    Parameters
    ----------
    grid : Grid
    mode : str
        "nearest" — zeroth-order jump only (C_0).
        "hermite" — high-order jumps (C_0, C_1, C_2) with Hermite weighting.
    """

    def __init__(self, grid: "Grid", mode: str = "hermite") -> None:
        self.grid = grid
        self.mode = mode
        self._jump_calc = JumpConditionCalculator(
            max_order=2 if mode == "hermite" else 0
        )

    def compute_correction(
        self,
        L_sparse,
        phi: np.ndarray,
        kappa: np.ndarray,
        sigma: float,
        rho: np.ndarray,
        rhs: np.ndarray,
        dp_dx: np.ndarray | None = None,
        dp_dy: np.ndarray | None = None,
    ) -> np.ndarray:
        """Compute the IIM RHS correction vector Δq.

        Parameters
        ----------
        L_sparse : scipy.sparse matrix (n, n) — CCD operator (before pin)
        phi      : (Nx, Ny) — level-set signed distance (φ<0 = liquid)
        kappa    : (Nx, Ny) — interface curvature
        sigma    : surface tension coefficient
        rho      : (Nx, Ny) — density field
        rhs      : (Nx, Ny) — PPE RHS
        dp_dx    : (Nx, Ny) or None — pressure x-gradient (for hermite mode)
        dp_dy    : (Nx, Ny) or None — pressure y-gradient (for hermite mode)

        Returns
        -------
        delta_q : np.ndarray, shape (n,) — RHS correction (add to RHS)
        """
        if self.mode == "nearest":
            return self._correction_nearest(L_sparse, phi, kappa, sigma)
        else:
            return self._correction_hermite(
                L_sparse, phi, kappa, sigma, rho, rhs,
                dp_dx, dp_dy,
            )

    def _correction_nearest(
        self,
        L_sparse,
        phi: np.ndarray,
        kappa: np.ndarray,
        sigma: float,
    ) -> np.ndarray:
        """Vectorized zeroth-order IIM correction using only [p] = σκ.

        For each interface-crossing face, applies:
            Δq_L += L[L,R] · σκ   (liquid row)
            Δq_R -= L[R,L] · σκ   (gas row)

        Crossing detection and coefficient gathering are fully vectorized.
        Only the sparse element extraction uses a loop over O(N_Γ)
        crossing faces (typically N_Γ << N²).
        """
        shape = self.grid.shape
        Nx, Ny = shape
        n = Nx * Ny

        phi_flat = phi.ravel()
        kap_flat = kappa.ravel()
        delta_q = np.zeros(n)

        L_csr = L_sparse.tocsr()

        # Build face index pairs and detect crossings vectorially.
        for axis in range(2):
            if axis == 0:
                # X-direction faces: (i, i+1) for i in [0, Nx-2], all j
                idx_a = (np.arange(Nx - 1)[:, None] * Ny
                         + np.arange(Ny)[None, :]).ravel()
                idx_b = idx_a + Ny
            else:
                # Y-direction faces: (j, j+1) for all i, j in [0, Ny-2]
                idx_a = (np.arange(Nx)[:, None] * Ny
                         + np.arange(Ny - 1)[None, :]).ravel()
                idx_b = idx_a + 1

            phi_a = phi_flat[idx_a]
            phi_b = phi_flat[idx_b]
            cross = (phi_a * phi_b) < 0.0

            if not np.any(cross):
                continue

            # Extract crossing subset
            ca = idx_a[cross]
            cb = idx_b[cross]
            pa = phi_a[cross]

            abs_a = np.abs(phi_flat[ca])
            abs_b = np.abs(phi_flat[cb])
            kap_iface = (
                (abs_b * kap_flat[ca] + abs_a * kap_flat[cb])
                / (abs_a + abs_b + 1e-30)
            )
            jump_p = sigma * kap_iface

            # Sparse element extraction — O(N_Γ) only
            L_ab = np.array([_sparse_element(L_csr, a, b) for a, b in zip(ca, cb)])
            L_ba = np.array([_sparse_element(L_csr, b, a) for a, b in zip(ca, cb)])

            # Sign: a<0 means a=liquid → += L_ab·jump, -= L_ba·jump
            # Sign: a>0 means a=gas   → -= L_ab·jump, += L_ba·jump
            sign = np.where(pa < 0.0, 1.0, -1.0)
            np.add.at(delta_q, ca, sign * L_ab * jump_p)
            np.add.at(delta_q, cb, -sign * L_ba * jump_p)

        return delta_q

    def _correction_hermite(
        self,
        L_sparse,
        phi: np.ndarray,
        kappa: np.ndarray,
        sigma: float,
        rho: np.ndarray,
        rhs: np.ndarray,
        dp_dx: np.ndarray | None,
        dp_dy: np.ndarray | None,
    ) -> np.ndarray:
        """High-order IIM correction using C_0, C_1, C_2.

        For each interface crossing, computes the full jump condition
        vector and applies Hermite-weighted corrections that account
        for [p], [p'], and [p''] simultaneously.

        The correction at each crossing face uses the fractional
        position α = |φ_a|/(|φ_a|+|φ_b|) to weight the contributions.
        """
        shape = self.grid.shape
        Nx, Ny = shape
        n = Nx * Ny

        phi_flat = phi.ravel()
        kap_flat = kappa.ravel()
        rho_flat = rho.ravel()
        rhs_flat = rhs.ravel()
        delta_q = np.zeros(n)

        L_csr = L_sparse.tocsr()

        # Material properties (assumed piecewise constant near Γ)
        rho_l = float(np.max(rho))
        rho_g = float(np.min(rho))

        for axis in range(2):
            h = self.grid.L[axis] / self.grid.N[axis]

            if axis == 0:
                N_walk = Nx - 1
                N_perp = Ny
            else:
                N_walk = Nx
                N_perp = Ny - 1

            for i in range(N_walk):
                for j in range(N_perp if axis == 1 else Ny):
                    if axis == 0:
                        idx_a = i * Ny + j
                        idx_b = (i + 1) * Ny + j
                    else:
                        idx_a = i * Ny + j
                        idx_b = i * Ny + (j + 1)

                    phi_a = phi_flat[idx_a]
                    phi_b = phi_flat[idx_b]

                    if phi_a * phi_b >= 0.0:
                        continue

                    # Fractional crossing position
                    abs_a = abs(phi_a)
                    abs_b = abs(phi_b)
                    alpha = abs_a / (abs_a + abs_b + 1e-30)

                    # Interface curvature
                    kap_iface = (1.0 - alpha) * kap_flat[idx_a] + alpha * kap_flat[idx_b]

                    # Determine liquid/gas sides
                    if phi_a < 0.0:
                        idx_liq, idx_gas = idx_a, idx_b
                    else:
                        idx_liq, idx_gas = idx_b, idx_a

                    # Liquid-side pressure gradient along this axis
                    p_prime_l = 0.0
                    if axis == 0 and dp_dx is not None:
                        p_prime_l = float(dp_dx.ravel()[idx_liq])
                    elif axis == 1 and dp_dy is not None:
                        p_prime_l = float(dp_dy.ravel()[idx_liq])

                    # Compute jump conditions
                    C = self._jump_calc.compute_1d_jumps(
                        sigma=sigma,
                        kappa=kap_iface,
                        rho_l=rho_l,
                        rho_g=rho_g,
                        p_prime_l=p_prime_l,
                        p_double_prime_l=0.0,
                        q_l=float(rhs_flat[idx_liq]),
                        q_g=float(rhs_flat[idx_gas]),
                    )

                    # Hermite-weighted correction (§4.2 of short paper)
                    # W(α) weights for the CCD stencil crossing:
                    #   w_0 = 1          (p equation contribution)
                    #   w_1 = h·(1-α)    (p' equation, distance to crossing)
                    #   w_2 = h²·(1-α)²/2  (p'' equation)
                    w = np.array([
                        1.0,
                        h * (1.0 - alpha),
                        0.5 * h**2 * (1.0 - alpha)**2,
                    ])
                    correction = float(np.dot(w, C[:3]))

                    # Apply via sparse operator elements
                    L_ab = _sparse_element(L_csr, idx_a, idx_b)
                    L_ba = _sparse_element(L_csr, idx_b, idx_a)

                    if phi_a < 0.0:
                        # a=liquid, b=gas
                        delta_q[idx_a] += L_ab * correction
                        delta_q[idx_b] -= L_ba * correction
                    else:
                        # a=gas, b=liquid
                        delta_q[idx_a] -= L_ab * correction
                        delta_q[idx_b] += L_ba * correction

        return delta_q

    def find_interface_crossings(
        self,
        phi: np.ndarray,
    ) -> list[dict]:
        """Identify all grid faces where the interface crosses.

        Returns a list of crossing descriptors for diagnostics/testing.

        Parameters
        ----------
        phi : (Nx, Ny) level-set field

        Returns
        -------
        crossings : list of dict with keys:
            axis, idx_a, idx_b, alpha, phi_a, phi_b
        """
        shape = self.grid.shape
        Nx, Ny = shape
        crossings = []

        for axis in range(2):
            if axis == 0:
                for i in range(Nx - 1):
                    for j in range(Ny):
                        idx_a = i * Ny + j
                        idx_b = (i + 1) * Ny + j
                        phi_a = phi.ravel()[idx_a]
                        phi_b = phi.ravel()[idx_b]
                        if phi_a * phi_b < 0.0:
                            abs_a = abs(phi_a)
                            abs_b = abs(phi_b)
                            crossings.append({
                                "axis": axis,
                                "idx_a": idx_a,
                                "idx_b": idx_b,
                                "alpha": abs_a / (abs_a + abs_b),
                                "phi_a": phi_a,
                                "phi_b": phi_b,
                            })
            else:
                for i in range(Nx):
                    for j in range(Ny - 1):
                        idx_a = i * Ny + j
                        idx_b = i * Ny + (j + 1)
                        phi_a = phi.ravel()[idx_a]
                        phi_b = phi.ravel()[idx_b]
                        if phi_a * phi_b < 0.0:
                            abs_a = abs(phi_a)
                            abs_b = abs(phi_b)
                            crossings.append({
                                "axis": axis,
                                "idx_a": idx_a,
                                "idx_b": idx_b,
                                "alpha": abs_a / (abs_a + abs_b),
                                "phi_a": phi_a,
                                "phi_b": phi_b,
                            })

        return crossings


def _sparse_element(L_csr, row: int, col: int) -> float:
    """Extract a single element from a CSR sparse matrix.

    CSR indices may be unsorted after Kronecker products / arithmetic,
    so we use linear search instead of searchsorted.
    """
    start = L_csr.indptr[row]
    end = L_csr.indptr[row + 1]
    cols = L_csr.indices[start:end]
    mask = (cols == col)
    if mask.any():
        return float(L_csr.data[start:end][mask][0])
    return 0.0
