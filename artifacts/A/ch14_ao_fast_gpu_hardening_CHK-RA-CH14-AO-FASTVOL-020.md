# CHK-RA-CH14-AO-FASTVOL-020 — AO-Fast GPU Hardening

Date: 2026-05-12

## Purpose

Address the GPU-optimization review findings in the active AO-Fast prototype
without enabling chapter-14 runtime execution.

## Fixes

- Reworked active Schur matvecs to avoid full nodal-grid allocation in every
  PCG iteration.  `ActiveSchurOperator` now builds a compact unique active-node
  support and applies `J^T`/`J` in that compact support for `apply_schur`.
  Full-grid scatter remains available only for explicit gauge updates.
- Removed dense metric-cache construction from compact active table builds.
  Cell measures are gathered directly from active cell ids and grid coordinates,
  avoiding the dense oracle/cache path and its device-to-host scalar cache keys.
- Removed the `allow_gpu_host_control` escape hatch for nonempty GPU
  diagnostics, PCG, and active projection.  GPU projection now fails closed
  until fused device-side reductions and line search are admitted.
- Made GPU table ledgers explicit: compact table builds mark
  `device_resident=True`, `host_transfer_count=0`, and defer count fields that
  would require device synchronization rather than calling `.get()`.
- Added regression tests that the compact path does not call dense geometry or
  dense metric-complex construction, that compact Schur equals the full nodal
  reference on CPU, and that the GPU path keeps active arrays and compact
  `J^T` results on device while rejecting host-control diagnostics,
  PCG/projection.

## Residual GPU Work

This hardening removes the reviewed full-grid Schur and hidden D2H blockers.
The active `Q/S/J/dS` formulas are still vectorized backend-native kernels, not
the final fused RawKernel/ElementwiseKernel production path.  Runtime activation
therefore remains blocked until C10/CUDA kernel counters and fused active-row
geometry/acceptance kernels land.

## Validation

- Local py_compile: PASS for `active_table.py`, `active_projection.py`, and
  `test_geometry_active_table.py`.
- Local targeted pytest:
  `pytest -q src/twophase/tests/test_geometry_active_table.py`
  PASS: `10 passed, 1 skipped`.
- Remote targeted GPU geometry regression:
  `env -u SSH_AUTH_SOCK make test PYTEST_ARGS="-k geometry_active_table -q"`
  PASS: `11 passed, 728 deselected`.
- Remote full GPU suite:
  `env -u SSH_AUTH_SOCK make test`
  PASS: `907 passed, 3 skipped`.

## SOLID / Negative Knowledge

- [SOLID-S] Active geometry table construction, compact Schur operators, and
  GPU runtime activation gates remain separate.
- [SOLID-D] The active Schur layer depends on the table contract, not on dense
  geometry or chapter-14 runtime wiring.
- [SOLID-X] No chapter-14 runtime activation, experiment result, branch
  deletion, main merge, FD/WENO/PPE fallback, smoothing, clipping, global
  correction, implicit dense fallback, implicit PCG fallback, CPU-first AO
  runtime path, hidden D2H GPU control, or hidden DCCD/UCCD damper was
  introduced.
