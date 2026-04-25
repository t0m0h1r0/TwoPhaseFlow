"""Lifecycle helpers for the FCCD matrix-free PPE solver."""

from __future__ import annotations

import numpy as np

from .fccd_matrixfree_helpers import (
    build_fccd_face_inverse_density,
    build_fccd_geometry_cache,
    build_fccd_jacobi_inverse,
    compute_fccd_phase_gauges,
)


def invalidate_fccd_matrixfree_cache(solver) -> None:
    """Drop density-dependent cached preconditioner state."""
    solver._rho = None
    solver._rho_dev = None
    solver._diag_inv = None
    solver._coeff_face = None
    solver._phase_threshold = None
    solver._interface_jump_context = None


def refresh_fccd_matrixfree_grid(solver, grid=None) -> None:
    """Refresh grid-dependent FCCD weights after mesh rebuild."""
    if grid is not None:
        solver.grid = grid
        solver.ndim = grid.ndim
        solver.fccd.grid = grid
    solver.fccd._weights = [
        solver.fccd._precompute_weights(ax)
        for ax in range(solver.fccd.ndim)
    ]
    refresh_fccd_geometry_cache(solver)
    invalidate_fccd_matrixfree_cache(solver)


def prepare_fccd_matrixfree_operator(solver, rho) -> None:
    """Cache density and optional diagonal preconditioner."""
    solver._rho_dev = solver.xp.asarray(rho)
    solver._rho = np.asarray(solver.backend.to_host(solver._rho_dev))
    solver._diag_inv = None
    refresh_fccd_phase_gauges(solver)
    solver._coeff_face = [
        build_fccd_face_inverse_density(
            xp=solver.xp,
            rho=solver._rho_dev,
            axis=axis,
            ndim=solver.ndim,
            grid=solver.grid,
            coefficient_scheme=solver.coefficient_scheme,
            phase_threshold=solver._phase_threshold,
        )
        for axis in range(solver.ndim)
    ]
    if solver.preconditioner == "jacobi":
        uses_mean_gauge = (
            hasattr(solver, "_uses_phase_mean_gauge")
            and solver._uses_phase_mean_gauge()
        )
        solver._diag_inv = build_fccd_jacobi_inverse(
            xp=solver.xp,
            rho_dev=solver._rho_dev,
            h_min=solver._h_min,
            pin_dofs=() if uses_mean_gauge else solver._pin_dofs,
        )


def refresh_fccd_phase_gauges(solver) -> None:
    """Refresh phase-separated gauge pins from the cached host density."""
    state = compute_fccd_phase_gauges(
        rho_host=solver._rho,
        coefficient_scheme=solver.coefficient_scheme,
        default_pin_dof=solver._pin_dof,
    )
    solver._pin_dofs = state.pin_dofs
    solver._phase_threshold = state.phase_threshold


def refresh_fccd_geometry_cache(solver) -> None:
    """Cache per-axis geometric scalars reused across every GMRES matvec."""
    cache = build_fccd_geometry_cache(xp=solver.xp, grid=solver.grid, ndim=solver.ndim)
    solver._h_min = cache.h_min
    solver._node_width = cache.node_width
    solver._cell_volume = cache.cell_volume
    solver._cell_volume_host = np.asarray(solver.backend.to_host(cache.cell_volume))
