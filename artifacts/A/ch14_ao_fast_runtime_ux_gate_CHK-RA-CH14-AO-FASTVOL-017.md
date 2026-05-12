# CHK-RA-CH14-AO-FASTVOL-017 — AO-Fast C8 Runtime UX Gate

Date: 2026-05-12

## Purpose

Move AO-Fast from "valid geometric YAML is rejected at config construction" to
"valid geometric YAML builds a typed `ExperimentConfig`, while solver runtime
activation remains fail-closed."  This lets the implementation route exercise
the intended YAML/UX contract before the C9/C10 runtime adapter and chapter-14
smoke gates exist.

## Implemented Contract

- `geometric_swept_volume` is an admitted interface advection scheme.
- `bundle_virtual_work` is an admitted capillary force source.
- `closed_interface.endpoint=geometric_cell_fraction` requires
  `residual_contract.constraints: [cell_volume]`; legacy
  `conservative_psi` still requires `[component_volume]`.
- `interface.reinitialization.algorithm: none` is parsed as no reinit and
  requires `schedule.every_steps=0`.
- `numerics.interface.tracking.primary: q` parses as
  `interface_tracking_method="q_cell_fraction"` and is rejected unless
  `interface.state_space.kind=geometric_cell_fraction`.
- `ExperimentConfig.from_dict(...)` accepts a complete AO-Fast geometric
  contract.
- `NSSolverBuilder` rejects `geometric_cell_fraction` before building runtime
  options with a clear disabled-adapter message.

## Fail-Close Boundary

The boundary is intentionally at solver construction, not inside the first time
step.  A valid AO-Fast YAML may be inspected, serialized, and regression-tested,
but it cannot silently enter the legacy diffuse/psi runtime.  There is no dense
runtime fallback, no implicit PCG fallback, no Ridge-Eikonal volume bracket, and
no CPU-first geometric runtime path.

## Validation

- Local py_compile: PASS for touched config, tracking, reinit, builder, and test
  modules.
- Local targeted parser regression:
  `pytest -q src/twophase/tests/test_config_state_space.py src/twophase/tests/test_config_io_fccd.py`
  PASS: `87 passed`.
- Local geometry/config regression:
  `pytest -q src/twophase/tests/test_geometry_active_table.py src/twophase/tests/test_config_state_space.py src/twophase/tests/test_config_io_fccd.py`
  PASS: `94 passed, 1 skipped`.
- Remote targeted parser regression:
  `env -u SSH_AUTH_SOCK make test PYTEST_ARGS="-k config_state_space -q"`
  PASS: `11 passed, 717 deselected`.
- Remote full GPU suite:
  `env -u SSH_AUTH_SOCK make test`
  PASS: `896 passed, 3 skipped`.
- `git diff --check`: PASS.

## SOLID / Negative Knowledge

- [SOLID-S] YAML parsing, reinit parsing, tracking parsing, and solver runtime
  activation remain separately owned.
- [SOLID-D] The config layer admits the AO-Fast contract without depending on
  geometry kernels or the chapter-14 solver adapter.
- [SOLID-X] No chapter-14 runtime activation, experiment result, main merge,
  FD/WENO/PPE fallback, smoothing, clipping, global correction, implicit dense
  fallback, implicit PCG fallback, CPU-first AO runtime path, hidden D2H GPU
  control, or hidden DCCD/UCCD damper was introduced.
