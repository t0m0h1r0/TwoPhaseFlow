"""Lifecycle helpers for the FCCD matrix-free PPE solver."""

from __future__ import annotations

import numpy as np

from .fccd_matrixfree_helpers import (
    build_fccd_face_inverse_density,
    build_fccd_geometry_cache,
    build_fccd_jacobi_inverse,
    build_fccd_phase_mean_gauge_cache,
    compute_fccd_phase_gauges,
)


def invalidate_fccd_matrixfree_cache(solver) -> None:
    """Drop density-dependent cached preconditioner state."""
    solver._rho = None
    solver._rho_dev = None
    solver._prepared_rho_token = None
    solver._diag_inv = None
    solver._coeff_face = None
    solver._phase_mean_gauge_cache = None
    solver._phase_mean_gauge_cache_host = None
    solver._phase_threshold = None
    solver._interface_jump_context = None
    solver._interface_stress_context = None


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
    rho_dev = solver.xp.asarray(rho)
    rho_token = _static_rho_token(rho_dev)
    if (
        getattr(solver, "_reuse_static_operator", False)
        and solver._rho_dev is not None
        and solver._coeff_face is not None
        and getattr(solver, "_prepared_rho_token", None) == rho_token
    ):
        return
    solver._rho_dev = rho_dev
    solver._prepared_rho_token = rho_token
    needs_host_density = (
        solver.coefficient_scheme == "phase_separated"
        and getattr(solver, "interface_coupling_scheme", "none") != "affine_jump"
    )
    if solver.backend.is_gpu() and not needs_host_density:
        solver._rho = None
    else:
        solver._rho = np.asarray(solver.backend.to_host(solver._rho_dev))
    solver._diag_inv = None
    refresh_fccd_phase_gauges(solver)
    refresh_fccd_phase_mean_gauge_cache(solver)
    solver._coeff_face = [
        build_fccd_face_inverse_density(
            xp=solver.xp,
            rho=solver._rho_dev,
            axis=axis,
            ndim=solver.ndim,
            grid=solver.grid,
            coefficient_scheme=solver.coefficient_scheme,
            phase_threshold=solver._phase_threshold,
            interface_coupling_scheme=solver.interface_coupling_scheme,
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


def _static_rho_token(rho) -> tuple:
    pointer = getattr(getattr(rho, "data", None), "ptr", None)
    dtype = getattr(getattr(rho, "dtype", None), "str", str(getattr(rho, "dtype", "")))
    return (id(rho), pointer, tuple(getattr(rho, "shape", ())), dtype)


def refresh_fccd_phase_gauges(solver) -> None:
    """Refresh phase-separated gauge pins from the cached host density."""
    if getattr(solver, "interface_coupling_scheme", "none") == "affine_jump":
        solver._pin_dofs = (solver._pin_dof,)
        solver._phase_threshold = None
        return
    state = compute_fccd_phase_gauges(
        rho_host=solver._rho,
        coefficient_scheme=solver.coefficient_scheme,
        default_pin_dof=solver._pin_dof,
    )
    solver._pin_dofs = state.pin_dofs
    solver._phase_threshold = state.phase_threshold


def refresh_fccd_phase_mean_gauge_cache(solver) -> None:
    """Cache phase masks and control-volume weights for mean-gauge projections."""
    if solver._phase_threshold is None:
        solver._phase_mean_gauge_cache = None
        solver._phase_mean_gauge_cache_host = None
        return
    solver._phase_mean_gauge_cache = build_fccd_phase_mean_gauge_cache(
        xp=solver.xp,
        rho=solver._rho_dev,
        cell_volume=solver._cell_volume,
        phase_threshold=solver._phase_threshold,
    )
    if solver._cell_volume_host is None:
        solver._cell_volume_host = np.asarray(
            solver.backend.to_host(solver._cell_volume)
        )
    solver._phase_mean_gauge_cache_host = build_fccd_phase_mean_gauge_cache(
        xp=np,
        rho=solver._rho,
        cell_volume=solver._cell_volume_host,
        phase_threshold=solver._phase_threshold,
    )


def refresh_fccd_geometry_cache(solver) -> None:
    """Cache per-axis geometric scalars reused across every GMRES matvec."""
    cache = build_fccd_geometry_cache(xp=solver.xp, grid=solver.grid, ndim=solver.ndim)
    solver._h_min = cache.h_min
    solver._node_width = cache.node_width
    solver._node_width_inv = [1.0 / width for width in cache.node_width]
    solver._cell_volume = cache.cell_volume
    solver._cell_volume_host = None if solver.backend.is_gpu() else cache.cell_volume
