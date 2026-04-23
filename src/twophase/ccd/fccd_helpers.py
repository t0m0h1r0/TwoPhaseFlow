"""Non-hot helpers for FCCD geometry and diagnostics."""

from __future__ import annotations

import numpy as np


def build_node_H_over_16(xp, H_host):
    """Return the per-node `H/16` correction used by `R_4`."""
    H_node = np.zeros(len(H_host) + 1)
    H_node[1:-1] = 0.5 * (H_host[:-1] + H_host[1:])
    H_node[0] = H_host[0]
    H_node[-1] = H_host[-1]
    return xp.asarray(H_node / 16.0)


def build_axis_weights(grid, xp, ax: int) -> dict:
    """Build per-axis FCCD geometry weights."""
    N_faces = grid.N[ax]
    coords_host = grid.coords[ax]
    H_host = coords_host[1:] - coords_host[:-1]

    if grid.uniform:
        H = float(H_host[0])
        return {
            "uniform": True,
            "H": H,
            "inv_H": 1.0 / H,
            "H_half": 0.5 * H,
            "H_over_24": H / 24.0,
            "H_sq_over_16": H * H / 16.0,
            "H_sq_over_8": H * H / 8.0,
            "H_over_16": H / 16.0,
            "N_faces": N_faces,
        }

    H = xp.asarray(H_host)
    H_node_host = 0.5 * (H_host[:-1] + H_host[1:]) if len(H_host) > 1 else H_host
    return {
        "uniform": False,
        "H": H,
        "inv_H": 1.0 / H,
        "inv_H_node": xp.asarray(1.0 / H_node_host),
        "H_half": 0.5 * H,
        "H_over_24": H / 24.0,
        "H_sq_over_16": H * H / 16.0,
        "H_sq_over_8": H * H / 8.0,
        "H_over_16_node": build_node_H_over_16(xp, H_host),
        "N_faces": N_faces,
    }


def enforce_wall_option_iii(face_array, axis: int):
    """Semantic no-op for interior-only FCCD face arrays."""
    return face_array


def enforce_wall_option_iv(face_array, axis: int, wall_value: float = 0.0):
    """Semantic no-op hook for interior-only FCCD wall faces."""
    return face_array


def periodic_symbol(H: float, omega: float) -> complex:
    """Return the truncated 4th-order periodic DFT symbol."""
    return 1j * omega * (1.0 - 7.0 * (omega * H) ** 4 / 5760.0)
