"""Hermite correction strategy for IIM stencil correction."""

from __future__ import annotations

import numpy as np

from .stencil_corrector_utils import sparse_element


def compute_hermite_stencil_correction(
    grid,
    jump_calc,
    L_sparse,
    phi: np.ndarray,
    kappa: np.ndarray,
    sigma: float,
    rho: np.ndarray,
    rhs: np.ndarray,
    dp_dx: np.ndarray | None,
    dp_dy: np.ndarray | None,
) -> np.ndarray:
    """High-order IIM correction using `C_0`, `C_1`, `C_2`."""
    Nx, Ny = grid.shape
    n = Nx * Ny

    phi_flat = phi.ravel()
    kap_flat = kappa.ravel()
    rhs_flat = rhs.ravel()
    delta_q = np.zeros(n)
    L_csr = L_sparse.tocsr()

    rho_l = float(np.max(rho))
    rho_g = float(np.min(rho))

    for axis in range(2):
        h = grid.L[axis] / grid.N[axis]
        N_walk = Nx - 1 if axis == 0 else Nx
        N_perp = Ny if axis == 0 else Ny - 1

        for i in range(N_walk):
            for j in range(N_perp):
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

                abs_a = abs(phi_a)
                abs_b = abs(phi_b)
                alpha = abs_a / (abs_a + abs_b + 1e-30)
                kap_iface = (1.0 - alpha) * kap_flat[idx_a] + alpha * kap_flat[idx_b]

                idx_liq, idx_gas = (idx_a, idx_b) if phi_a < 0.0 else (idx_b, idx_a)
                p_prime_l = 0.0
                if axis == 0 and dp_dx is not None:
                    p_prime_l = float(dp_dx.ravel()[idx_liq])
                elif axis == 1 and dp_dy is not None:
                    p_prime_l = float(dp_dy.ravel()[idx_liq])

                C = jump_calc.compute_1d_jumps(
                    sigma=sigma,
                    kappa=kap_iface,
                    rho_l=rho_l,
                    rho_g=rho_g,
                    p_prime_l=p_prime_l,
                    p_double_prime_l=0.0,
                    q_l=float(rhs_flat[idx_liq]),
                    q_g=float(rhs_flat[idx_gas]),
                )
                weights = np.array([1.0, h * (1.0 - alpha), 0.5 * h**2 * (1.0 - alpha) ** 2])
                correction = float(np.dot(weights, C[:3]))

                L_ab = sparse_element(L_csr, idx_a, idx_b)
                L_ba = sparse_element(L_csr, idx_b, idx_a)
                if phi_a < 0.0:
                    delta_q[idx_a] += L_ab * correction
                    delta_q[idx_b] -= L_ba * correction
                else:
                    delta_q[idx_a] -= L_ab * correction
                    delta_q[idx_b] += L_ba * correction

    return delta_q
