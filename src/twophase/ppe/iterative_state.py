"""State handoff helpers for `PPESolverIterative`."""

from __future__ import annotations

import numpy as np


def unpack_iterative_initial_pressure(p_init, *, backend, shape):
    """Materialize the initial pressure guess on the host."""
    if isinstance(p_init, dict):
        return np.asarray(backend.to_host(p_init["p"]), dtype=float)
    if p_init is not None:
        return np.asarray(backend.to_host(p_init), dtype=float)
    return np.zeros(shape, dtype=float)


def pack_iterative_solution_state(
    p: np.ndarray,
    dp_list: list[np.ndarray],
    d2p_list: list[np.ndarray],
    *,
    backend,
):
    """Pack the last iterative solution and derivative state on the active backend."""
    result = backend.to_device(p)
    return result, {
        "p": result,
        "dp": [backend.to_device(d) for d in dp_list],
        "d2p": [backend.to_device(d) for d in d2p_list],
    }
