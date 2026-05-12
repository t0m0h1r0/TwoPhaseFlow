"""Matrix-free active AO-Fast projection operators.

This layer owns active ``J``, ``J^T``, and Schur matvecs over
``ActiveGeometryTable``.  It deliberately consumes compact active tables and
never assembles a dense full-grid Schur matrix.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from twophase.backend import is_device_array

from .active_table import ActiveGeometryTable
from .active_table import build_active_table_for_cell_ids


@dataclass(frozen=True)
class ActiveSchurDiagnostics:
    """Cheap active-row diagnostics for rank/conditioning gates."""

    n_rows: int
    active_row_count: int
    row_norm_min: float
    row_norm_max: float
    cheap_condition_estimate: float


@dataclass(frozen=True)
class ActivePCGResult:
    """CPU-control PCG result for active Schur gates and tests."""

    x: object
    iterations: int
    residual_linf: float
    stop_reason: str


@dataclass(frozen=True)
class ActiveProjectionLedger:
    """Exact active-residual acceptance ledger for one AO-Fast projection."""

    iterations: int
    initial_residual_linf: float
    final_residual_linf: float
    min_step_fraction: float
    stop_reason: str
    pcg_stop_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ActiveProjectionResult:
    """Projected gauge and final active table for a fixed support epoch."""

    phi: object
    table: ActiveGeometryTable
    ledger: ActiveProjectionLedger


class ActiveSchurOperator:
    """Matrix-free ``S_q = J_q J_q^T`` over compact active rows."""

    def __init__(self, table: ActiveGeometryTable):
        self.table = table
        self.xp = table.xp

    def apply_j(self, nodal_values):
        """Apply active ``J`` to a nodal vector/field."""
        xp = self.xp
        nodal = xp.asarray(nodal_values).reshape((-1,))
        local = nodal[self.table.node_ids_A]
        return xp.sum(self.table.jq_local_A * local, axis=-1)

    def apply_j_transpose(self, cell_values):
        """Apply active ``J^T`` and scatter to nodal shape."""
        xp = self.xp
        values = xp.asarray(cell_values)
        if tuple(values.shape) != (self.table.n_active,):
            raise ValueError("cell_values length must match n_active")
        flat = xp.zeros(
            (self.table.node_shape[0] * self.table.node_shape[1],),
            dtype=self.table.jq_local_A.dtype,
        )
        contribution = self.table.jq_local_A * values[:, None]
        xp.add.at(flat, self.table.node_ids_A.reshape((-1,)), contribution.reshape((-1,)))
        return flat.reshape(self.table.node_shape)

    def apply_schur(self, cell_values):
        """Apply ``J J^T`` without materializing a dense Schur matrix."""
        return self.apply_j(self.apply_j_transpose(cell_values))

    def diagnostics(self, *, row_norm_tolerance: float = 0.0) -> ActiveSchurDiagnostics:
        """Return cheap row-norm rank and conditioning estimates."""
        xp = self.xp
        row_norm = self.table.row_norm_A
        active = row_norm > float(row_norm_tolerance)
        active_count = _scalar_int(xp, xp.sum(active.astype(xp.int64)))
        if active_count == 0:
            return ActiveSchurDiagnostics(
                n_rows=self.table.n_active,
                active_row_count=0,
                row_norm_min=0.0,
                row_norm_max=0.0,
                cheap_condition_estimate=math.inf,
            )
        active_rows = xp.where(active, row_norm, xp.nan)
        row_norm_min = _scalar_float(xp, xp.nanmin(active_rows))
        row_norm_max = _scalar_float(xp, xp.nanmax(active_rows))
        condition = (
            math.inf if row_norm_min <= 0.0 else float(row_norm_max / row_norm_min)
        )
        return ActiveSchurDiagnostics(
            n_rows=self.table.n_active,
            active_row_count=active_count,
            row_norm_min=row_norm_min,
            row_norm_max=row_norm_max,
            cheap_condition_estimate=condition,
        )


def solve_active_pcg(
    operator: ActiveSchurOperator,
    rhs,
    *,
    tolerance: float,
    max_iterations: int,
    tau_cg_floor: float | None = None,
    allow_gpu_host_control: bool = False,
) -> ActivePCGResult:
    """Solve an active Schur system with fail-closed tolerance-floor policy."""
    tolerance = float(tolerance)
    if not (math.isfinite(tolerance) and tolerance > 0.0):
        raise ValueError("tolerance must be positive")
    max_iterations = int(max_iterations)
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    if tau_cg_floor is not None and float(tau_cg_floor) > tolerance:
        raise ValueError("active PCG roundoff floor exceeds requested target")
    if is_device_array(operator.table.q_A) and not allow_gpu_host_control:
        raise ValueError(
            "GPU active PCG host-control loop is disabled; use a fused C7 path"
        )

    xp = operator.xp
    b = xp.asarray(rhs)
    if tuple(b.shape) != (operator.table.n_active,):
        raise ValueError("rhs length must match n_active")
    x = xp.zeros_like(b)
    r = b - operator.apply_schur(x)
    z = _jacobi_precondition(operator, r)
    p = z
    rz_old = _dot(xp, r, z)
    residual = _norm_linf(xp, r)
    if residual <= tolerance:
        return ActivePCGResult(x=x, iterations=0, residual_linf=residual, stop_reason="initial")

    for iteration in range(1, max_iterations + 1):
        Ap = operator.apply_schur(p)
        denom = _dot(xp, p, Ap)
        if denom <= 0.0:
            raise ValueError("active Schur operator is singular or indefinite")
        alpha = rz_old / denom
        x = x + alpha * p
        r = r - alpha * Ap
        residual = _norm_linf(xp, r)
        if residual <= tolerance:
            return ActivePCGResult(
                x=x,
                iterations=iteration,
                residual_linf=residual,
                stop_reason="algebraic_tolerance",
            )
        z = _jacobi_precondition(operator, r)
        rz_new = _dot(xp, r, z)
        if rz_new <= 0.0:
            raise ValueError("active PCG preconditioned residual is nonpositive")
        beta = rz_new / rz_old
        p = z + beta * p
        rz_old = rz_new
    return ActivePCGResult(
        x=x,
        iterations=max_iterations,
        residual_linf=residual,
        stop_reason="iteration_limit",
    )


def project_active_cell_volume_compatibility_2d(
    grid,
    phi,
    table: ActiveGeometryTable,
    *,
    tolerance: float,
    max_newton_iterations: int = 8,
    max_pcg_iterations: int | None = None,
    sign_safety: float = 0.95,
    min_step_fraction: float = 1.0e-8,
    tau_cg_floor: float | None = None,
    allow_gpu_host_control: bool = False,
) -> ActiveProjectionResult:
    """Project ``phi`` against ``q_target_A`` on a fixed active support.

    Acceptance is always based on exact active-row recomputation of ``Q_h``.
    Active-set changes are fail-closed here; an outer epoch manager must rebuild
    support explicitly before retrying.
    """
    tolerance = float(tolerance)
    if not (math.isfinite(tolerance) and tolerance > 0.0):
        raise ValueError("tolerance must be positive")
    if not (math.isfinite(sign_safety) and 0.0 < sign_safety < 1.0):
        raise ValueError("sign_safety must be in (0, 1)")
    if not (math.isfinite(min_step_fraction) and 0.0 < min_step_fraction <= 1.0):
        raise ValueError("min_step_fraction must be in (0, 1]")

    xp = table.xp
    phi_current = xp.asarray(phi)
    if tuple(phi_current.shape) != table.node_shape:
        raise ValueError("phi shape must match active table node_shape")
    max_pcg_iterations = (
        4 * max(1, table.n_active)
        if max_pcg_iterations is None
        else int(max_pcg_iterations)
    )
    if max_pcg_iterations < 1:
        raise ValueError("max_pcg_iterations must be positive")

    current_table = table
    residual = current_table.q_target_A - current_table.q_A
    initial_residual = _norm_linf(xp, residual)
    current_residual = initial_residual
    min_step_used = 1.0
    pcg_reasons: list[str] = []
    if current_residual <= tolerance:
        return ActiveProjectionResult(
            phi=phi_current,
            table=current_table,
            ledger=ActiveProjectionLedger(
                iterations=0,
                initial_residual_linf=initial_residual,
                final_residual_linf=current_residual,
                min_step_fraction=1.0,
                stop_reason="initial_exact_residual",
                pcg_stop_reasons=(),
            ),
        )

    case_code_initial = current_table.case_code_A
    for iteration in range(1, int(max_newton_iterations) + 1):
        _reject_unrepresentable_active_residual(current_table, residual, tolerance)
        operator = ActiveSchurOperator(current_table)
        pcg = solve_active_pcg(
            operator,
            residual,
            tolerance=max(tolerance * 0.1, 1.0e-14),
            tau_cg_floor=tau_cg_floor,
            max_iterations=max_pcg_iterations,
            allow_gpu_host_control=allow_gpu_host_control,
        )
        pcg_reasons.append(pcg.stop_reason)
        if pcg.stop_reason == "iteration_limit":
            raise ValueError("active PCG reached iteration limit")
        delta_phi = operator.apply_j_transpose(pcg.x)
        step_cap = _sign_margin_step_fraction(
            xp,
            phi_current - float(current_table.level),
            delta_phi,
            sign_safety,
        )
        min_step_used = min(min_step_used, step_cap)
        if step_cap < min_step_fraction:
            raise ValueError("active projection would cross the fixed sign stratum")

        phi_next, next_table, next_residual = _active_line_search(
            grid=grid,
            phi=phi_current,
            delta_phi=delta_phi,
            table=current_table,
            current_residual_linf=current_residual,
            step_cap=step_cap,
            min_step_fraction=min_step_fraction,
            case_code_initial=case_code_initial,
        )
        phi_current = phi_next
        current_table = next_table
        residual = current_table.q_target_A - current_table.q_A
        current_residual = next_residual
        if current_residual <= tolerance:
            return ActiveProjectionResult(
                phi=phi_current,
                table=current_table,
                ledger=ActiveProjectionLedger(
                    iterations=iteration,
                    initial_residual_linf=initial_residual,
                    final_residual_linf=current_residual,
                    min_step_fraction=min_step_used,
                    stop_reason="exact_active_residual",
                    pcg_stop_reasons=tuple(pcg_reasons),
                ),
            )

    raise ValueError(
        "active projection did not converge; final residual "
        f"{current_residual:.3e}"
    )


def _jacobi_precondition(operator: ActiveSchurOperator, residual):
    xp = operator.xp
    diagonal = xp.where(operator.table.row_norm_A > 0.0, operator.table.row_norm_A, 1.0)
    return residual / diagonal


def _refresh_same_support(grid, phi, table: ActiveGeometryTable) -> ActiveGeometryTable:
    return build_active_table_for_cell_ids(
        grid,
        phi,
        table.cell_ids_A,
        q_target=table.q_target_A,
        origin_mask=table.origin_mask_A,
        halo_mask=table.halo_mask_A,
        dirty_mask=table.dirty_mask_A,
        flux_touched_mask=table.flux_touched_A,
        component=table.component_A,
        owner_epoch=table.owner_epoch_A,
        support_budget=None,
        tau_support=0.0,
        level=table.level,
        construction_mode="fixed_active_epoch_refresh",
        dense_scan_used=False,
    )


def _active_line_search(
    *,
    grid,
    phi,
    delta_phi,
    table: ActiveGeometryTable,
    current_residual_linf: float,
    step_cap: float,
    min_step_fraction: float,
    case_code_initial,
):
    xp = table.xp
    step = min(1.0, float(step_cap))
    while step >= min_step_fraction:
        candidate = phi + step * delta_phi
        candidate_table = _refresh_same_support(grid, candidate, table)
        if _scalar_bool(xp, xp.any(candidate_table.case_code_A != case_code_initial)):
            step *= 0.5
            continue
        residual_linf = _norm_linf(xp, candidate_table.q_target_A - candidate_table.q_A)
        if residual_linf < current_residual_linf:
            return candidate, candidate_table, residual_linf
        step *= 0.5
    raise ValueError("active projection line search failed")


def _reject_unrepresentable_active_residual(
    table: ActiveGeometryTable,
    residual,
    tolerance: float,
) -> None:
    xp = table.xp
    blocked = (table.row_norm_A <= 0.0) & (xp.abs(residual) > float(tolerance))
    if _scalar_bool(xp, xp.any(blocked)):
        raise ValueError("active residual changes a row outside the fixed stratum")


def _sign_margin_step_fraction(xp, phi_rel, delta_phi, sign_safety: float) -> float:
    crossing = phi_rel * delta_phi < 0.0
    safe_delta = xp.where(crossing, xp.abs(delta_phi), xp.ones_like(delta_phi))
    ratios = xp.where(crossing, xp.abs(phi_rel) / safe_delta, xp.inf)
    cap = _scalar_float(xp, xp.min(ratios))
    if cap == float("inf"):
        return 1.0
    return min(1.0, float(sign_safety) * cap)


def _dot(xp, left, right) -> float:
    return _scalar_float(xp, xp.sum(left * right))


def _norm_linf(xp, value) -> float:
    return _scalar_float(xp, xp.max(xp.abs(value)))


def _scalar_int(xp, value) -> int:
    if hasattr(value, "get"):
        value = value.get()
    if hasattr(value, "item"):
        value = value.item()
    return int(value)


def _scalar_float(xp, value) -> float:
    if hasattr(value, "get"):
        value = value.get()
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def _scalar_bool(xp, value) -> bool:
    if hasattr(value, "get"):
        value = value.get()
    if hasattr(value, "item"):
        value = value.item()
    return bool(value)
