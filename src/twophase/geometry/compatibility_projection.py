"""Compatibility projection for SP-AO geometric cell volumes.

Symbol mapping
--------------
``q`` -> physical cell-volume owner.
``Q_h(phi)`` -> P1 cut-cell volume map.
``J_q`` -> cell-local derivative of ``Q_h`` with respect to nodal ``phi``.
``S_q`` -> matrix-free Schur operator ``J_q J_q^T`` under the identity gauge
           metric used by this Stage 2 gate.

This module is still a geometry-layer primitive.  It does not connect the
projection to reinitialization, transport, capillarity, or chapter-14 runtime
activation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .cell_complex import MetricCellComplex
from .p1_cut_geometry import P1CutGeometry, cut_geometry_2d
from .p1_cut_jacobian import cut_geometry_derivatives_2d, scatter_local_to_nodes


@dataclass(frozen=True)
class CompatibilityProjectionLedger:
    """Projection diagnostics in physical q-units."""

    iterations: int
    initial_residual_linf: float
    final_residual_linf: float
    final_residual_l2: float
    sign_margin: float
    delta_surface: float
    min_step_fraction: float


@dataclass(frozen=True)
class CompatibilityProjectionResult:
    """Projected gauge and final geometry satisfying the q target."""

    phi: object
    geometry: P1CutGeometry
    ledger: CompatibilityProjectionLedger


def project_cell_volume_compatibility_2d(
    grid,
    phi,
    target_q,
    *,
    level: float = 0.0,
    tolerance: float = 1.0e-11,
    max_newton_iterations: int = 8,
    max_cg_iterations: int | None = None,
    sign_safety: float = 0.95,
    min_step_fraction: float = 1.0e-8,
) -> CompatibilityProjectionResult:
    """Project ``phi`` so that ``Q_h(phi)=target_q`` in the current stratum."""
    if grid.ndim != 2:
        raise ValueError("project_cell_volume_compatibility_2d supports 2D grids")
    tolerance = float(tolerance)
    if not (math.isfinite(tolerance) and tolerance > 0.0):
        raise ValueError("tolerance must be positive")
    sign_safety = float(sign_safety)
    if not (math.isfinite(sign_safety) and 0.0 < sign_safety < 1.0):
        raise ValueError("sign_safety must be in (0, 1)")
    min_step_fraction = float(min_step_fraction)
    if not (math.isfinite(min_step_fraction) and 0.0 < min_step_fraction <= 1.0):
        raise ValueError("min_step_fraction must be in (0, 1]")
    max_newton_iterations = int(max_newton_iterations)
    if max_newton_iterations < 1:
        raise ValueError("max_newton_iterations must be positive")

    xp = grid.xp
    phi_dev = xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    _validate_regular_stratum(xp, phi_dev, level, tolerance)

    complex_h = MetricCellComplex.from_grid(grid)
    target_dev = xp.asarray(target_q, dtype=phi_dev.dtype)
    if tuple(target_dev.shape) != complex_h.shape:
        raise ValueError("target_q shape must match the grid cell shape")
    _validate_target_bounds(xp, target_dev, complex_h.cell_measures, tolerance)

    max_cg_iterations = (
        4 * (grid.N[0] + 1) * (grid.N[1] + 1)
        if max_cg_iterations is None
        else int(max_cg_iterations)
    )
    if max_cg_iterations < 1:
        raise ValueError("max_cg_iterations must be positive")

    initial_geometry = cut_geometry_2d(grid, phi_dev, level=level)
    initial_surface = initial_geometry.surface_length
    residual = target_dev - initial_geometry.q
    initial_residual_linf = _norm_linf(xp, residual)
    if initial_residual_linf <= tolerance:
        return _result(
            grid=grid,
            phi=phi_dev,
            target_q=target_dev,
            level=level,
            iterations=0,
            initial_residual_linf=initial_residual_linf,
            initial_surface=initial_surface,
            min_step_fraction_used=1.0,
            geometry=initial_geometry,
        )

    min_step_fraction_used = 1.0
    current_geometry = initial_geometry
    current_residual = residual
    current_residual_linf = initial_residual_linf

    for iteration in range(1, max_newton_iterations + 1):
        if current_residual_linf <= tolerance:
            return _result(
                grid=grid,
                phi=phi_dev,
                target_q=target_dev,
                level=level,
                iterations=iteration - 1,
                initial_residual_linf=initial_residual_linf,
                initial_surface=initial_surface,
                min_step_fraction_used=min_step_fraction_used,
                geometry=current_geometry,
            )

        derivatives = cut_geometry_derivatives_2d(grid, phi_dev, level=level)
        row_norm = xp.sum(derivatives.jq_local * derivatives.jq_local, axis=-1)
        active = row_norm > 0.0
        if _scalar_bool(xp, xp.any((~active) & (xp.abs(current_residual) > tolerance))):
            raise ValueError(
                "target_q changes a full/empty cell outside the fixed stratum"
            )

        lagrange = _solve_schur_cg(
            grid=grid,
            jq_local=derivatives.jq_local,
            rhs=xp.where(active, current_residual, xp.zeros_like(current_residual)),
            row_norm=row_norm,
            active=active,
            tolerance=max(tolerance * 0.1, 1.0e-14),
            max_iterations=max_cg_iterations,
        )
        delta_phi = _apply_jq_transpose(grid, derivatives.jq_local, lagrange)
        step_cap = _sign_margin_step_fraction(
            xp,
            phi_dev - float(level),
            delta_phi,
            sign_safety,
        )
        min_step_fraction_used = min(min_step_fraction_used, step_cap)
        if step_cap < min_step_fraction:
            raise ValueError(
                "compatibility projection would cross the fixed sign stratum"
            )

        phi_next, next_geometry, next_residual_linf = _line_search(
            grid=grid,
            phi=phi_dev,
            delta_phi=delta_phi,
            target_q=target_dev,
            level=level,
            current_residual_linf=current_residual_linf,
            step_cap=step_cap,
            min_step_fraction=min_step_fraction,
        )
        if next_residual_linf >= current_residual_linf:
            raise ValueError("compatibility projection failed to reduce residual")
        phi_dev = phi_next
        current_geometry = next_geometry
        current_residual = target_dev - current_geometry.q
        current_residual_linf = next_residual_linf

    if current_residual_linf <= tolerance:
        return _result(
            grid=grid,
            phi=phi_dev,
            target_q=target_dev,
            level=level,
            iterations=max_newton_iterations,
            initial_residual_linf=initial_residual_linf,
            initial_surface=initial_surface,
            min_step_fraction_used=min_step_fraction_used,
            geometry=current_geometry,
        )
    raise ValueError(
        "compatibility projection did not converge; final residual "
        f"{current_residual_linf:.3e}"
    )


def _result(
    *,
    grid,
    phi,
    target_q,
    level: float,
    iterations: int,
    initial_residual_linf: float,
    initial_surface: float,
    min_step_fraction_used: float,
    geometry: P1CutGeometry | None = None,
) -> CompatibilityProjectionResult:
    xp = grid.xp
    if geometry is None:
        geometry = cut_geometry_2d(grid, phi, level=level)
    residual = target_q - geometry.q
    return CompatibilityProjectionResult(
        phi=phi,
        geometry=geometry,
        ledger=CompatibilityProjectionLedger(
            iterations=iterations,
            initial_residual_linf=initial_residual_linf,
            final_residual_linf=_norm_linf(xp, residual),
            final_residual_l2=_norm_l2(xp, residual),
            sign_margin=geometry.sign_margin,
            delta_surface=geometry.surface_length - initial_surface,
            min_step_fraction=min_step_fraction_used,
        ),
    )


def _validate_target_bounds(xp, target_q, cell_measures, tolerance: float) -> None:
    if _scalar_bool(xp, xp.any(~xp.isfinite(target_q))):
        raise ValueError("target_q must be finite")
    below = target_q < -tolerance
    above = target_q > cell_measures + tolerance
    if _scalar_bool(xp, xp.any(below | above)):
        raise ValueError("target_q must lie within physical cell-volume bounds")


def _validate_regular_stratum(xp, phi, level: float, tolerance: float) -> None:
    phi_rel = phi - float(level)
    if _scalar_bool(xp, xp.any(~xp.isfinite(phi_rel))):
        raise ValueError("compatibility projection requires finite phi values")
    margin = _scalar_float(xp, xp.min(xp.abs(phi_rel)))
    if margin <= tolerance:
        raise ValueError("compatibility projection requires a regular sign stratum")


def _line_search(
    *,
    grid,
    phi,
    delta_phi,
    target_q,
    level: float,
    current_residual_linf: float,
    step_cap: float,
    min_step_fraction: float,
):
    xp = grid.xp
    step = min(1.0, step_cap)
    while step >= min_step_fraction:
        candidate = phi + step * delta_phi
        geometry = cut_geometry_2d(grid, candidate, level=level)
        residual_linf = _norm_linf(xp, target_q - geometry.q)
        if residual_linf < current_residual_linf:
            return candidate, geometry, residual_linf
        step *= 0.5
    raise ValueError("compatibility projection line search failed")


def _solve_schur_cg(
    *,
    grid,
    jq_local,
    rhs,
    row_norm,
    active,
    tolerance: float,
    max_iterations: int,
):
    xp = grid.xp
    solution = xp.zeros_like(rhs)
    residual = xp.where(active, rhs, xp.zeros_like(rhs))
    z = _precondition(xp, row_norm, residual, active)
    direction = z
    rz_old = _dot_active(xp, residual, z, active)
    if rz_old <= tolerance * tolerance:
        return solution

    for _iteration in range(max_iterations):
        operator_direction = _apply_schur(grid, jq_local, direction)
        denom = _dot_active(xp, direction, operator_direction, active)
        if denom <= 0.0:
            raise ValueError("compatibility projection Schur operator is singular")
        alpha = rz_old / denom
        solution = solution + alpha * direction
        residual = xp.where(active, residual - alpha * operator_direction, 0.0)
        if _norm_linf(xp, residual) <= tolerance:
            return solution
        z = _precondition(xp, row_norm, residual, active)
        rz_new = _dot_active(xp, residual, z, active)
        if rz_new <= tolerance * tolerance:
            return solution
        beta = rz_new / rz_old
        direction = z + beta * direction
        rz_old = rz_new

    raise ValueError("compatibility projection Schur CG did not converge")


def _apply_schur(grid, jq_local, cell_values):
    nodal = _apply_jq_transpose(grid, jq_local, cell_values)
    return _apply_jq(grid.xp, jq_local, nodal)


def _apply_jq(xp, jq_local, nodal_values):
    local = _local_corner_field(xp, nodal_values)
    return xp.sum(jq_local * local, axis=-1)


def _apply_jq_transpose(grid, jq_local, cell_values):
    return scatter_local_to_nodes(grid, jq_local * cell_values[..., None])


def _local_corner_field(xp, field):
    return xp.stack(
        (
            field[:-1, :-1],
            field[1:, :-1],
            field[1:, 1:],
            field[:-1, 1:],
        ),
        axis=-1,
    )


def _precondition(xp, row_norm, residual, active):
    safe_row_norm = xp.where(active & (row_norm > 0.0), row_norm, 1.0)
    return xp.where(active, residual / safe_row_norm, xp.zeros_like(residual))


def _sign_margin_step_fraction(xp, phi_rel, delta_phi, sign_safety: float) -> float:
    crossing = phi_rel * delta_phi < 0.0
    safe_delta = xp.where(crossing, xp.abs(delta_phi), xp.ones_like(delta_phi))
    ratios = xp.where(crossing, xp.abs(phi_rel) / safe_delta, xp.inf)
    cap = _scalar_float(xp, xp.min(ratios))
    if cap == float("inf"):
        return 1.0
    return min(1.0, sign_safety * cap)


def _dot_active(xp, left, right, active) -> float:
    return _scalar_float(xp, xp.sum(xp.where(active, left * right, 0.0)))


def _norm_linf(xp, value) -> float:
    return _scalar_float(xp, xp.max(xp.abs(value)))


def _norm_l2(xp, value) -> float:
    return _scalar_float(xp, xp.sqrt(xp.sum(value * value)))


def _scalar_bool(xp, value) -> bool:
    if hasattr(value, "get"):
        value = value.get()
    return bool(value)


def _scalar_float(xp, value) -> float:
    if hasattr(value, "get"):
        value = value.get()
    return float(value)
