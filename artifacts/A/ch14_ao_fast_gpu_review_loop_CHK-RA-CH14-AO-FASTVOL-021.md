# CHK-RA-CH14-AO-FASTVOL-021 — AO-Fast GPU Review Loop

Date: 2026-05-12

## Purpose

Repeat the code review and GPU-optimization review after CHK-020, fixing every
actionable finding until no remaining P0/P1 issue is identified in the active
AO-Fast geometry/projection slice.

## Review Rounds

### Round 1 — Duplicate Coordinate Transfer

Finding: compact table construction avoided dense metric-cache construction, but
`active_table.py` still converted host coordinate axes to backend arrays a
second time to compute active cell measures.  `refresh_active_geometry_2d()`
had already converted the same axes for corner coordinates.

Fix: `P1ActiveGeometry` now carries `cell_measure_A` computed from the active
corner points, and `build_active_table_for_cell_ids()` consumes that value
directly.  This removes the duplicate full-axis H2D conversion in compact table
construction.

### Round 2 — Hidden Scalar Synchronization

Finding: top-level GPU diagnostics/PCG/projection gates failed closed, but the
private scalar helpers would still call `.get()` if a device reduction reached
them through a future path.

Fix: `_scalar_int`, `_scalar_float`, and `_scalar_bool` now reject CUDA device
scalars before any `.get()`/`.item()` conversion.  The GPU regression test locks
this by calling the private norm helper on a device array and expecting a
host-synchronization failure.

### Round 3 — Compact Schur Reduction Hot Path

Finding: full-grid `J^T` scatter used `add.at` even though the active-node ids
are unique, and compact `J^T` still relied on atomic scatter for GPU duplicate
node accumulation.

Fix: full-grid scatter now uses direct indexed assignment.  Compact GPU
accumulation uses backend `bincount(minlength=n_active_nodes)` and casts back to
the active geometry dtype.  If a GPU backend lacks `bincount`, the path fails
closed instead of falling back to atomic scatter.

### Round 4 — Extra Device Allocation

Finding: `metric_key_A` was not consumed by any current path but still allocated
a separate float64 active vector, including on GPU.

Fix: `metric_key_A` now aliases `cell_measure_A` until a future cache actually
admits an owned key.  Tests assert the alias to prevent accidental device-copy
regression.

## Residual Review

No unresolved P0/P1 finding remains in this slice.

Intentional residuals:

- `xp.asarray(grid.coords[axis])` remains once inside active geometry refresh,
  because `Grid.coords` is host-owned by the grid contract and active geometry
  needs backend coordinate arrays.
- CPU-control PCG/projection remains CPU-only; nonempty GPU execution is still
  disabled until fused device solver, reductions, and line search are admitted.
- Dense oracle and `MetricCellComplex.from_grid()` remain available only in the
  debug/oracle builder and tests, not compact production construction.

## Validation

- Local py_compile: PASS for active kernels/table/projection/tests.
- Local targeted pytest:
  `pytest -q src/twophase/tests/test_geometry_active_table.py`
  PASS: `10 passed, 1 skipped`.
- Remote targeted GPU geometry regression:
  `env -u SSH_AUTH_SOCK make test PYTEST_ARGS="-k geometry_active_table -q"`
  PASS: `11 passed, 728 deselected`.
- Remote full GPU suite:
  `env -u SSH_AUTH_SOCK make test`
  PASS: `907 passed, 3 skipped`.
- `git diff --check`: PASS at review-loop update time.

## SOLID / Negative Knowledge

- [SOLID-S] Active geometry refresh owns active coordinate-derived measures;
  table construction owns metadata/ledger assembly; projection owns Schur
  accumulation and scalar-reduction gates.
- [SOLID-D] The compact table depends on the `P1ActiveGeometry` contract instead
  of reconstructing dense metric state.
- [SOLID-X] No chapter-14 runtime activation, experiment result, branch
  deletion, main merge, FD/WENO/PPE fallback, smoothing, clipping, global
  correction, implicit dense fallback, implicit PCG fallback, CPU-first AO
  runtime path, hidden D2H GPU control, or hidden DCCD/UCCD damper was
  introduced.
