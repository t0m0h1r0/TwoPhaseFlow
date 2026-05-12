"""Compact active geometry tables for AO-Fast.

A3 chain:
  Equation: SP-AO constrains cell-volume compatibility only on compact support
  ``A_q`` rather than the full cell complex.
  Discretization: ``A_q`` is the union of current/previous mixed cells,
  compact swept-flux support, compact target-mixed support, and a one-face halo.
  Code: this module owns the table schema, capacity gates, support provenance,
  and active-row refresh.

Dense support scans are allowed only through ``build_debug_active_table_from_dense``
and are ledgered as non-production work.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable

import numpy as np

from twophase.backend import is_device_array

from .active_kernels import active_cell_node_ids_2d, refresh_active_geometry_2d
from .dense_reference import MetricCellComplex, cut_geometry_2d


ORIGIN_CURRENT = np.uint16(1 << 0)
ORIGIN_PREVIOUS = np.uint16(1 << 1)
ORIGIN_TARGET = np.uint16(1 << 2)
ORIGIN_FLUX = np.uint16(1 << 3)
ORIGIN_HALO = np.uint16(1 << 4)


class TargetStateCode(IntEnum):
    """Physical state code for ``q_target_A`` relative to ``cell_measure_A``."""

    EMPTY = 0
    FULL = 1
    MIXED = 2
    OUT_OF_BOUNDS = 3


@dataclass(frozen=True)
class ActiveSupportBudget:
    """Declared support capacity contract for AO-Fast active tables."""

    max_active_ratio: float
    max_support_stream_ratio: float
    max_epoch_growth_ratio: float
    on_overrun: str = "fail_close"

    def __post_init__(self) -> None:
        for name in (
            "max_active_ratio",
            "max_support_stream_ratio",
            "max_epoch_growth_ratio",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be positive")
            if name != "max_epoch_growth_ratio" and value > 1.0:
                raise ValueError(f"{name} must be <= 1.0")
        if self.on_overrun != "fail_close":
            raise ValueError("support budget overrun policy must be fail_close")


@dataclass(frozen=True)
class ActiveGeometryLedger:
    """Construction counters and proof flags for one active table."""

    construction_mode: str
    dense_scan_used: bool
    n_cells: int
    n_active: int
    n_core: int
    n_halo: int
    n_flux_touched: int
    n_target_mixed: int
    capacity_limit: int
    support_stream_limit: int
    device_resident: bool = False
    host_transfer_count: int = 0
    deferred_device_count_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActiveGeometryTable:
    """Struct-of-arrays compact table for active AO-Fast geometry."""

    xp: object
    grid_shape: tuple[int, int]
    node_shape: tuple[int, int]
    level: float
    cell_ids_A: object
    node_ids_A: object
    case_code_A: object
    edge_mask_A: object
    lambda_edge_A: object
    q_A: object
    q_target_A: object
    cell_measure_A: object
    target_theta_A: object
    target_state_code_A: object
    s_A: object
    jq_local_A: object
    ds_local_A: object
    row_norm_A: object
    component_A: object
    halo_mask_A: object
    dirty_mask_A: object
    flux_touched_A: object
    origin_mask_A: object
    owner_epoch_A: object
    metric_key_A: object
    finite_mask_A: object
    regular_mask_A: object
    ledger: ActiveGeometryLedger

    @property
    def n_active(self) -> int:
        """Return the compact active row count."""
        return int(self.cell_ids_A.shape[0])


def build_active_table_for_cell_ids(
    grid,
    phi,
    cell_ids,
    *,
    q_target=None,
    origin_mask=None,
    halo_mask=None,
    dirty_mask=None,
    flux_touched_mask=None,
    component=None,
    owner_epoch=None,
    support_budget: ActiveSupportBudget | None = None,
    tau_support: float = 0.0,
    level: float = 0.0,
    construction_mode: str = "compact_stream",
    dense_scan_used: bool = False,
) -> ActiveGeometryTable:
    """Build an active table from already compact cell-id streams."""
    if grid.ndim != 2:
        raise ValueError("ActiveGeometryTable currently supports 2D grids")
    xp = grid.xp
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("cell_ids must have shape (n_active, 2)")
    n_active = int(ids.shape[0])
    n_cells = int(grid.N[0]) * int(grid.N[1])
    _check_support_budget(n_active, n_cells, support_budget, "active support")

    active_geometry = refresh_active_geometry_2d(grid, phi, ids, level=level)
    cell_measure_A = active_geometry.cell_measure_A
    q_target_A = (
        active_geometry.q_A
        if q_target is None
        else _gather_or_vector_values(xp, q_target, ids, n_active)
    )
    target_theta_A = q_target_A / cell_measure_A
    target_state_code_A = _target_state_codes(
        xp,
        q_target_A,
        cell_measure_A,
        tau_support=float(tau_support),
    )

    origin_mask_A = _vector_or_default(
        xp, origin_mask, n_active, xp.uint16, int(ORIGIN_CURRENT)
    )
    halo_mask_A = _vector_or_default(xp, halo_mask, n_active, bool, False)
    dirty_mask_A = _vector_or_default(xp, dirty_mask, n_active, bool, True)
    flux_touched_A = _vector_or_default(xp, flux_touched_mask, n_active, bool, False)
    component_A = _vector_or_default(xp, component, n_active, xp.int32, 0)
    owner_epoch_A = _vector_or_default(xp, owner_epoch, n_active, xp.int32, 0)
    metric_key_A = _metric_key(cell_measure_A)
    support_stream_limit = _support_stream_limit(n_cells, support_budget)
    n_halo = 0 if halo_mask is None else _host_count(halo_mask_A)
    n_flux_touched = 0 if flux_touched_mask is None else _host_count(flux_touched_A)
    n_target_mixed = _host_count(target_state_code_A == int(TargetStateCode.MIXED))
    deferred_count_fields = tuple(
        name
        for name, count in (
            ("n_halo", n_halo),
            ("n_flux_touched", n_flux_touched),
            ("n_target_mixed", n_target_mixed),
        )
        if count < 0
    )
    ledger = ActiveGeometryLedger(
        construction_mode=construction_mode,
        dense_scan_used=bool(dense_scan_used),
        n_cells=n_cells,
        n_active=n_active,
        n_core=int(n_active - n_halo) if n_halo >= 0 else -1,
        n_halo=n_halo,
        n_flux_touched=n_flux_touched,
        n_target_mixed=n_target_mixed,
        capacity_limit=_active_limit(n_cells, support_budget),
        support_stream_limit=support_stream_limit,
        device_resident=is_device_array(ids),
        host_transfer_count=0,
        deferred_device_count_fields=deferred_count_fields,
    )
    return ActiveGeometryTable(
        xp=xp,
        grid_shape=(int(grid.N[0]), int(grid.N[1])),
        node_shape=(int(grid.N[0]) + 1, int(grid.N[1]) + 1),
        level=float(level),
        cell_ids_A=ids,
        node_ids_A=active_cell_node_ids_2d(grid, ids),
        case_code_A=active_geometry.case_code_A,
        edge_mask_A=active_geometry.edge_mask_A,
        lambda_edge_A=active_geometry.lambda_edge_A,
        q_A=active_geometry.q_A,
        q_target_A=q_target_A,
        cell_measure_A=cell_measure_A,
        target_theta_A=target_theta_A,
        target_state_code_A=target_state_code_A,
        s_A=active_geometry.s_A,
        jq_local_A=active_geometry.jq_local_A,
        ds_local_A=active_geometry.ds_local_A,
        row_norm_A=active_geometry.row_norm_A,
        component_A=component_A,
        halo_mask_A=halo_mask_A,
        dirty_mask_A=dirty_mask_A,
        flux_touched_A=flux_touched_A,
        origin_mask_A=origin_mask_A,
        owner_epoch_A=owner_epoch_A,
        metric_key_A=metric_key_A,
        finite_mask_A=active_geometry.finite_mask_A,
        regular_mask_A=active_geometry.regular_mask_A,
        ledger=ledger,
    )


def build_debug_active_table_from_dense(
    grid,
    phi,
    *,
    q_target=None,
    previous_cell_ids=None,
    flux_touched_cell_ids=None,
    target_cell_ids=None,
    support_budget: ActiveSupportBudget | None = None,
    tau_support: float = 0.0,
    include_halo: bool = True,
    boundary: tuple[str, str] = ("wall", "wall"),
    allowed_context: str = "initialization",
    level: float = 0.0,
) -> ActiveGeometryTable:
    """Build a table through a ledgered dense scan for init/oracle/debug only."""
    if allowed_context not in {
        "initialization",
        "restart_validation",
        "oracle_test",
        "debug",
        "metric_epoch_rebuild",
        "degenerate_exact_step",
    }:
        raise ValueError("dense active support scan is not allowed in production mode")
    xp = grid.xp
    geometry = cut_geometry_2d(grid, phi, level=level)
    complex_h = MetricCellComplex.from_grid(grid)
    q_target_full = geometry.q if q_target is None else xp.asarray(q_target)
    current_mixed = _host_ids_from_mask(
        (geometry.q > tau_support) & (geometry.q < complex_h.cell_measures - tau_support)
    )
    target_mixed_from_q = _host_ids_from_mask(
        (q_target_full > tau_support)
        & (q_target_full < complex_h.cell_measures - tau_support)
    )
    ids, origin = compact_active_cell_ids_from_streams(
        grid_shape=(int(grid.N[0]), int(grid.N[1])),
        current_cell_ids=current_mixed,
        previous_cell_ids=previous_cell_ids,
        flux_touched_cell_ids=flux_touched_cell_ids,
        target_cell_ids=_concat_cell_ids(target_mixed_from_q, target_cell_ids),
        support_budget=support_budget,
        include_halo=include_halo,
        boundary=boundary,
    )
    _check_support_budget(
        len(ids),
        int(grid.N[0]) * int(grid.N[1]),
        support_budget,
        "debug active support",
    )
    flux_mask = (origin & int(ORIGIN_FLUX)) != 0
    halo_mask = (origin & int(ORIGIN_HALO)) != 0
    return build_active_table_for_cell_ids(
        grid,
        phi,
        ids,
        q_target=q_target_full,
        origin_mask=origin,
        halo_mask=halo_mask,
        flux_touched_mask=flux_mask,
        support_budget=support_budget,
        tau_support=tau_support,
        level=level,
        construction_mode=f"dense_{allowed_context}",
        dense_scan_used=True,
    )


def compact_active_cell_ids_from_streams(
    *,
    grid_shape: tuple[int, int],
    current_cell_ids=None,
    previous_cell_ids=None,
    flux_touched_cell_ids=None,
    target_cell_ids=None,
    support_budget: ActiveSupportBudget | None = None,
    include_halo: bool = True,
    boundary: tuple[str, str] = ("wall", "wall"),
):
    """Union compact support streams and optionally add a one-face halo."""
    grid_shape = (int(grid_shape[0]), int(grid_shape[1]))
    n_cells = grid_shape[0] * grid_shape[1]
    support: dict[tuple[int, int], int] = {}
    _merge_stream(support, current_cell_ids, int(ORIGIN_CURRENT), grid_shape)
    _merge_stream(support, previous_cell_ids, int(ORIGIN_PREVIOUS), grid_shape)
    _merge_stream(support, target_cell_ids, int(ORIGIN_TARGET), grid_shape)
    _merge_stream(support, flux_touched_cell_ids, int(ORIGIN_FLUX), grid_shape)
    _check_support_stream_budget(
        len(support),
        n_cells,
        support_budget,
        "compact support stream",
    )
    if include_halo:
        core = tuple(support)
        for cell in core:
            for neighbor in _one_face_neighbors(cell, grid_shape, boundary):
                support[neighbor] = support.get(neighbor, 0) | int(ORIGIN_HALO)
    _check_support_budget(
        len(support),
        n_cells,
        support_budget,
        "compact active support",
    )
    if not support:
        return np.zeros((0, 2), dtype=np.int64), np.zeros((0,), dtype=np.uint16)
    cells = np.asarray(sorted(support), dtype=np.int64)
    origin = np.asarray([support[tuple(cell)] for cell in cells], dtype=np.uint16)
    return cells, origin


def _merge_stream(support, cell_ids, origin_bit: int, grid_shape: tuple[int, int]) -> None:
    if cell_ids is None:
        return
    if is_device_array(cell_ids):
        raise ValueError(
            "device support streams require fused GPU compaction; "
            "host compact_active_cell_ids_from_streams would violate the GPU contract"
        )
    ids = np.asarray(cell_ids, dtype=np.int64)
    if ids.size == 0:
        return
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("support stream cell ids must have shape (n, 2)")
    nx, ny = grid_shape
    for i, j in ids:
        i_int = int(i)
        j_int = int(j)
        if not (0 <= i_int < nx and 0 <= j_int < ny):
            raise ValueError("support stream cell id is outside the grid")
        key = (i_int, j_int)
        support[key] = support.get(key, 0) | origin_bit


def _one_face_neighbors(
    cell: tuple[int, int],
    grid_shape: tuple[int, int],
    boundary: tuple[str, str],
) -> Iterable[tuple[int, int]]:
    nx, ny = grid_shape
    i, j = cell
    for di, dj, axis in ((-1, 0, 0), (1, 0, 0), (0, -1, 1), (0, 1, 1)):
        ni = i + di
        nj = j + dj
        if axis == 0 and boundary[0] == "periodic":
            ni %= nx
        if axis == 1 and boundary[1] == "periodic":
            nj %= ny
        if 0 <= ni < nx and 0 <= nj < ny:
            yield ni, nj


def _gather_cell_values(xp, field, cell_ids):
    return field[cell_ids[:, 0], cell_ids[:, 1]]


def _gather_or_vector_values(xp, values, cell_ids, n_active: int):
    arr = xp.asarray(values)
    if arr.ndim == 1:
        if int(arr.shape[0]) != n_active:
            raise ValueError("active vector length must match n_active")
        return arr
    if arr.ndim == 2:
        return _gather_cell_values(xp, arr, cell_ids)
    raise ValueError("q_target must be a full cell field or active vector")


def _target_state_codes(xp, q_target_A, cell_measure_A, *, tau_support: float):
    tau = float(tau_support)
    code = xp.full(q_target_A.shape, int(TargetStateCode.MIXED), dtype=xp.uint8)
    code = xp.where(q_target_A <= tau, int(TargetStateCode.EMPTY), code)
    code = xp.where(
        q_target_A >= cell_measure_A - tau,
        int(TargetStateCode.FULL),
        code,
    )
    out_of_bounds = (q_target_A < -tau) | (q_target_A > cell_measure_A + tau)
    return xp.where(out_of_bounds, int(TargetStateCode.OUT_OF_BOUNDS), code)


def _vector_or_default(xp, value, n_active: int, dtype, default):
    if value is None:
        return xp.full((n_active,), default, dtype=dtype)
    arr = xp.asarray(value, dtype=dtype)
    if tuple(arr.shape) != (n_active,):
        raise ValueError("active metadata vector length must match n_active")
    return arr


def _metric_key(cell_measure_A):
    return cell_measure_A


def _concat_cell_ids(left, right):
    arrays = [np.asarray(a, dtype=np.int64).reshape((-1, 2)) for a in (left, right) if a is not None]
    if not arrays:
        return None
    return np.vstack(arrays)


def _host_ids_from_mask(mask):
    arr = mask.get() if hasattr(mask, "get") else np.asarray(mask)
    return np.argwhere(np.asarray(arr, dtype=bool))


def _host_count(mask) -> int:
    if is_device_array(mask):
        if int(mask.size) == 0:
            return 0
        return -1
    arr = mask.get() if hasattr(mask, "get") else np.asarray(mask)
    return int(np.count_nonzero(arr))


def _active_limit(n_cells: int, support_budget: ActiveSupportBudget | None) -> int:
    if support_budget is None:
        return n_cells
    return max(1, int(np.floor(float(support_budget.max_active_ratio) * n_cells)))


def _support_stream_limit(
    n_cells: int,
    support_budget: ActiveSupportBudget | None,
) -> int:
    if support_budget is None:
        return n_cells
    return max(1, int(np.floor(float(support_budget.max_support_stream_ratio) * n_cells)))


def _check_support_budget(
    n_active: int,
    n_cells: int,
    support_budget: ActiveSupportBudget | None,
    label: str,
) -> None:
    limit = _active_limit(n_cells, support_budget)
    if n_active > limit:
        raise ValueError(
            f"{label} capacity exceeded: n_active={n_active} limit={limit}"
        )


def _check_support_stream_budget(
    n_stream: int,
    n_cells: int,
    support_budget: ActiveSupportBudget | None,
    label: str,
) -> None:
    limit = _support_stream_limit(n_cells, support_budget)
    if n_stream > limit:
        raise ValueError(
            f"{label} capacity exceeded: n_stream={n_stream} limit={limit}"
        )
