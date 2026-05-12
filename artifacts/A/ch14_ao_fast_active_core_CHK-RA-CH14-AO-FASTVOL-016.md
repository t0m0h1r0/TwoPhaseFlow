# CHK-RA-CH14-AO-FASTVOL-016 - AO-Fast active core implementation

## Scope

Implemented AO-Fast C2-C7 active geometry/projection primitives without
activating chapter-14 runtime YAMLs.

Added:

```text
src/twophase/geometry/active_kernels.py
src/twophase/geometry/active_table.py
src/twophase/geometry/active_projection.py
src/twophase/tests/test_geometry_active_table.py
```

Updated:

```text
src/twophase/geometry/__init__.py
docs/01_PROJECT_MAP.md
docs/wiki/theory/WIKI-T-169.md
docs/02_ACTIVE_LEDGER.md
```

## Implemented Contracts

`active_kernels.py` evaluates P1 cut-cell geometry only for supplied compact
cell ids:

```text
Q_h(phi)_A, S_h(phi)_A, J_q,A, dS_h,A,
case_code_A, edge_mask_A, lambda_edge_A, row_norm_A.
```

`active_table.py` owns compact support metadata:

```text
cell_ids_A, node_ids_A, q_target_A, cell_measure_A, target_theta_A,
target_state_code_A, halo_mask_A, dirty_mask_A, flux_touched_A, origin_mask_A,
owner_epoch_A, metric_key_A.
```

The production-facing table builder consumes compact streams and does not call
the dense oracle.  Dense support scans exist only in
`build_debug_active_table_from_dense(..., allowed_context=...)` and are marked
as `dense_scan_used=True` in the ledger.

`active_projection.py` adds matrix-free active operators:

```text
J, J^T, S = J J^T,
cheap row-norm diagnostics,
PCG with tau_cg_floor fail-close,
fixed-support exact active residual projection.
```

GPU active tables stay device-resident.  The current Python PCG control loop
fails closed on GPU unless explicitly allowed for a diagnostic path; this avoids
hidden device-to-host synchronization inside production AO-Fast.

## Validation

```text
../../../.venv/bin/python3 -m py_compile \
  src/twophase/geometry/active_kernels.py \
  src/twophase/geometry/active_table.py \
  src/twophase/geometry/active_projection.py \
  src/twophase/geometry/__init__.py \
  src/twophase/tests/test_geometry_active_table.py

../../../.venv/bin/python3 -m pytest -q \
  src/twophase/tests/test_geometry_active_table.py \
  src/twophase/tests/test_geometry_dense_reference.py \
  src/twophase/tests/test_geometry_import_manifest.py \
  src/twophase/tests/test_config_state_space.py \
  src/twophase/tests/test_closed_interface_geometry.py

env -u SSH_AUTH_SOCK make test PYTEST_ARGS="-k geometry_active_table -q"
env -u SSH_AUTH_SOCK make test
git diff --check
```

Result:

```text
py_compile PASS,
local targeted regression: 32 passed, 1 skipped,
remote targeted GPU selection: 8 passed, 718 deselected,
full remote GPU suite: 894 passed, 3 skipped in 58.74s,
diff check PASS.
```

## Remaining Gates

Runtime construction remains disabled intentionally.  The next work must connect
the active core through an explicit runtime adapter/checkpoint/capillary gate,
with active-set epoch handling and fused/device-side GPU solver control before
chapter-14 YAML activation.

## SOLID / Policy Notes

```text
[SOLID-S] active kernels, table ownership, and projection operators are split.
[SOLID-D] parser/runtime construction remains separated from geometry kernels.
[SOLID-X] no solver route, chapter-14 YAML, experiment result, fallback physics,
dense runtime fallback, implicit PCG fallback, smoothing, clipping, or main
merge was introduced.
```
