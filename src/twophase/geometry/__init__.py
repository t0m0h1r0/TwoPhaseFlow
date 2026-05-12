"""Geometric cell-fraction AO-Fast support package.

The package exposes dense oracle, import-manifest, and active compact geometry
primitives.  Chapter-14 runtime adapters remain gated until the full AO-Fast
validation ladder passes.
"""

from __future__ import annotations

from .active_kernels import P1ActiveGeometry, refresh_active_geometry_2d
from .active_projection import (
    ActiveProjectionLedger,
    ActiveProjectionResult,
    ActiveSchurOperator,
    project_active_cell_volume_compatibility_2d,
    solve_active_pcg,
)
from .active_table import (
    ActiveGeometryLedger,
    ActiveGeometryTable,
    ActiveSupportBudget,
    TargetStateCode,
    build_active_table_for_cell_ids,
    build_debug_active_table_from_dense,
    compact_active_cell_ids_from_streams,
)
from .dense_reference import MetricCellComplex, P1CutGeometry, cut_geometry_2d

__all__ = [
    "ActiveGeometryLedger",
    "ActiveGeometryTable",
    "ActiveProjectionLedger",
    "ActiveProjectionResult",
    "ActiveSchurOperator",
    "ActiveSupportBudget",
    "MetricCellComplex",
    "P1ActiveGeometry",
    "P1CutGeometry",
    "TargetStateCode",
    "build_active_table_for_cell_ids",
    "build_debug_active_table_from_dense",
    "compact_active_cell_ids_from_streams",
    "cut_geometry_2d",
    "project_active_cell_volume_compatibility_2d",
    "refresh_active_geometry_2d",
    "solve_active_pcg",
]
