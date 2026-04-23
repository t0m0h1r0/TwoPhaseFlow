"""Shared utilities for IIM stencil correction."""

from __future__ import annotations

import numpy as np


def sparse_element(L_csr, row: int, col: int) -> float:
    """Extract a single element from a CSR sparse matrix."""
    start = L_csr.indptr[row]
    end = L_csr.indptr[row + 1]
    cols = L_csr.indices[start:end]
    mask = cols == col
    if mask.any():
        return float(L_csr.data[start:end][mask][0])
    return 0.0


def find_interface_crossings(phi: np.ndarray) -> list[dict]:
    """Identify all grid faces where the interface crosses."""
    Nx, Ny = phi.shape
    phi_flat = phi.ravel()
    crossings = []
    for axis in range(2):
        if axis == 0:
            for i in range(Nx - 1):
                for j in range(Ny):
                    idx_a = i * Ny + j
                    idx_b = (i + 1) * Ny + j
                    phi_a = phi_flat[idx_a]
                    phi_b = phi_flat[idx_b]
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
                    phi_a = phi_flat[idx_a]
                    phi_b = phi_flat[idx_b]
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
