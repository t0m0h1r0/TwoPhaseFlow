"""Nearest-interface correction strategy for IIM stencil correction."""

from __future__ import annotations

import numpy as np

from .stencil_corrector_utils import sparse_element


def compute_nearest_stencil_correction(grid, L_sparse, phi, kappa, sigma: float) -> np.ndarray:
    """Vectorized zeroth-order IIM correction using only `[p] = σκ`."""
    Nx, Ny = grid.shape
    n = Nx * Ny

    phi_flat = phi.ravel()
    kap_flat = kappa.ravel()
    delta_q = np.zeros(n)
    L_csr = L_sparse.tocsr()

    for axis in range(2):
        if axis == 0:
            idx_a = (np.arange(Nx - 1)[:, None] * Ny + np.arange(Ny)[None, :]).ravel()
            idx_b = idx_a + Ny
        else:
            idx_a = (np.arange(Nx)[:, None] * Ny + np.arange(Ny - 1)[None, :]).ravel()
            idx_b = idx_a + 1

        phi_a = phi_flat[idx_a]
        phi_b = phi_flat[idx_b]
        cross = (phi_a * phi_b) < 0.0
        if not np.any(cross):
            continue

        ca = idx_a[cross]
        cb = idx_b[cross]
        pa = phi_a[cross]

        abs_a = np.abs(phi_flat[ca])
        abs_b = np.abs(phi_flat[cb])
        kap_iface = (abs_b * kap_flat[ca] + abs_a * kap_flat[cb]) / (abs_a + abs_b + 1e-30)
        jump_p = sigma * kap_iface

        L_ab = np.array([sparse_element(L_csr, a, b) for a, b in zip(ca, cb)])
        L_ba = np.array([sparse_element(L_csr, b, a) for a, b in zip(ca, cb)])

        sign = np.where(pa < 0.0, 1.0, -1.0)
        np.add.at(delta_q, ca, sign * L_ab * jump_p)
        np.add.at(delta_q, cb, -sign * L_ba * jump_p)

    return delta_q
