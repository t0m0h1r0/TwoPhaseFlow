"""Helper utilities for `_CCDPPEBase` legacy assembly paths."""

from __future__ import annotations

import numpy as np


def assemble_ccd_pinned_system(base, rhs, rho):
    """Build the pinned CCD operator and matching RHS vector."""
    xp = base.xp
    rho_key = id(rho)
    L_pinned = None
    for k, L_cached, _ in base._L_cache:
        if k == rho_key:
            L_pinned = L_cached
            break

    if L_pinned is None:
        rho_dev = xp.asarray(rho)
        drho_np = []
        for ax in range(base.ndim):
            drho_ax, _ = base.ccd.differentiate(rho_dev, ax)
            drho_np.append(np.asarray(base.backend.to_host(drho_ax), dtype=float))
        rho_np = np.asarray(base.backend.to_host(rho_dev), dtype=float)

        L_sparse = build_ccd_sparse_operator(base, rho_np, drho_np)
        if base._periodic:
            Nx, Ny = base.grid.N
            pin_dof = base._bc_spec.pin_dof_in_shape((Nx, Ny))
        else:
            pin_dof = base._bc_spec.pin_dof

        from ..core.boundary import pin_sparse_row

        L_lil = L_sparse.tolil()
        dummy_rhs = np.zeros(L_lil.shape[0])
        pin_sparse_row(L_lil, dummy_rhs, pin_dof)
        L_pinned = L_lil.tocsr()

        base._L_cache.append((rho_key, L_pinned, None))
        if len(base._L_cache) > base._cache_capacity:
            base._L_cache.pop(0)

    if base._periodic:
        Nx, Ny = base.grid.N
        rhs_full = np.asarray(base.backend.to_host(rhs), dtype=float)
        rhs_np = rhs_full[:Nx, :Ny].ravel()
        pin_dof = base._bc_spec.pin_dof_in_shape((Nx, Ny))
    else:
        pin_dof = base._bc_spec.pin_dof
        rhs_np = np.asarray(base.backend.to_host(rhs), dtype=float).ravel()
    rhs_np[pin_dof] = 0.0

    return L_pinned, rhs_np


def build_ccd_1d_matrices(base, axis: int):
    """Build 1D CCD derivative matrices D1, D2 for the given axis."""
    n_full = base.grid.N[axis] + 1
    to_host = base.backend.to_host

    if base._periodic:
        N_ax = base.grid.N[axis]
        if axis == 0:
            I_per = base.xp.zeros((n_full, N_ax))
            for j in range(N_ax):
                I_per[j, j] = 1.0
            I_per[N_ax, 0] = 1.0
            d1, d2 = base.ccd.differentiate(I_per, axis=0)
            return (
                np.asarray(to_host(d1), dtype=float)[:N_ax, :],
                np.asarray(to_host(d2), dtype=float)[:N_ax, :],
            )

        I_per = base.xp.zeros((N_ax, n_full))
        for j in range(N_ax):
            I_per[j, j] = 1.0
        I_per[0, N_ax] = 1.0
        d1, d2 = base.ccd.differentiate(I_per, axis=1)
        d1_np = np.asarray(to_host(d1), dtype=float)[:, :N_ax]
        d2_np = np.asarray(to_host(d2), dtype=float)[:, :N_ax]
        return d1_np.T, d2_np.T

    I = base.xp.eye(n_full)
    if axis == 0:
        d1, d2 = base.ccd.differentiate(I, axis=0)
        return np.asarray(to_host(d1), dtype=float), np.asarray(to_host(d2), dtype=float)
    d1, d2 = base.ccd.differentiate(I, axis=1)
    return np.asarray(to_host(d1), dtype=float).T, np.asarray(to_host(d2), dtype=float).T


def build_ccd_sparse_operator(base, rho_np, drho_np):
    """Assemble the sparse `L_CCD^rho` matrix via Kronecker products."""
    import scipy.sparse as sp

    D1x = base._D1[0]
    D2x = base._D2[0]
    D1y = base._D1[1]
    D2y = base._D2[1]

    mx = D1x.shape[0]
    my = D1y.shape[0]

    D2x_full = sp.kron(sp.csr_matrix(D2x), sp.eye(my), format='csr')
    D2y_full = sp.kron(sp.eye(mx), sp.csr_matrix(D2y), format='csr')
    D1x_full = sp.kron(sp.csr_matrix(D1x), sp.eye(my), format='csr')
    D1y_full = sp.kron(sp.eye(mx), sp.csr_matrix(D1y), format='csr')

    if base._periodic:
        Nx, Ny = base.grid.N
        rho_trimmed = rho_np[:Nx, :Ny]
        drho_x_trimmed = drho_np[0][:Nx, :Ny]
        drho_y_trimmed = (
            drho_np[1][:Nx, :Ny] if base.ndim > 1 else np.zeros_like(rho_trimmed)
        )
    else:
        rho_trimmed = rho_np
        drho_x_trimmed = drho_np[0]
        drho_y_trimmed = drho_np[1] if base.ndim > 1 else np.zeros_like(rho_trimmed)

    rho_flat = rho_trimmed.ravel()
    drho_x_flat = drho_x_trimmed.ravel()
    drho_y_flat = drho_y_trimmed.ravel()

    inv_rho = sp.diags(1.0 / rho_flat, format='csr')
    coeff_x = sp.diags(drho_x_flat / rho_flat ** 2, format='csr')
    coeff_y = sp.diags(drho_y_flat / rho_flat ** 2, format='csr')

    L = (inv_rho @ (D2x_full + D2y_full) - coeff_x @ D1x_full - coeff_y @ D1y_full)
    return L.tocsr()
