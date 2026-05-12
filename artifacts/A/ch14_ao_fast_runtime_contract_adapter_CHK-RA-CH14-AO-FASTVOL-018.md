# CHK-RA-CH14-AO-FASTVOL-018 — AO-Fast C9 Runtime Contract Adapter

Date: 2026-05-12

## Purpose

Implement the C9 adapter as a disabled/test-only gate: the config can reach
solver construction, the AO-Fast handoff/capillary/checkpoint contracts are
validated, and then runtime still fails closed before the legacy diffuse solver
can be built.

## Implemented

- Added `src/twophase/simulation/ao_fast_runtime_contract.py`.
- Added `AOFastRuntimeContract` and `AOFastRuntimeDisabledError`.
- `NSSolverBuilder` now calls `raise_ao_fast_runtime_disabled(cfg)` for
  `geometric_cell_fraction`, so the error is emitted only after the AO-Fast
  contract is validated.
- Validated handoff fields: `q`, `theta`, `phi`, `q_cell_fraction`,
  `geometric_swept_volume`, `algorithm: none`, and `reinit_every=0`.
- Validated capillary fields: `bundle_virtual_work`,
  `endpoint=geometric_cell_fraction`, `constraints=('cell_volume',)`, and
  `capillary_reaction_projection=pressure_component_hodge`.
- Added `validate_ao_fast_checkpoint_arrays(...)` for the future
  continuation-frame contract: q/theta/phi/stratum arrays, transport and
  compatibility-projection ledger epochs, and two-component pressure/projected
  face histories with 2D staggered shapes.
- Fixed the C8 parser gap where `bundle_virtual_work` admitted the source but
  did not preserve the declared closed-interface contract in `RunCfg`.

## Fail-Close Boundary

The C9 adapter is deliberately not a runtime activation.  It blocks before
`build_solver_init_options`, which prevents `q_cell_fraction` tracking,
geometric transport, or bundle capillary settings from entering the existing
psi/diffuse runtime by accident.

## Validation

- Local py_compile: PASS for the new adapter, updated operator parser,
  `NSSolverBuilder`, and state-space tests.
- Local config parser regression:
  `pytest -q src/twophase/tests/test_config_state_space.py src/twophase/tests/test_config_io_fccd.py`
  PASS: `90 passed`.
- Local geometry/config regression:
  `pytest -q src/twophase/tests/test_geometry_active_table.py src/twophase/tests/test_config_state_space.py src/twophase/tests/test_config_io_fccd.py`
  PASS: `97 passed, 1 skipped`.
- Remote targeted parser regression:
  `env -u SSH_AUTH_SOCK make test PYTEST_ARGS="-k config_state_space -q"`
  PASS: `14 passed, 717 deselected`.
- Remote full GPU suite:
  `env -u SSH_AUTH_SOCK make test`
  PASS: `899 passed, 3 skipped`.
- `git diff --check`: PASS.

## SOLID / Negative Knowledge

- [SOLID-S] Contract validation is separated from config parsing, solver
  option construction, checkpoint I/O, and geometry kernels.
- [SOLID-D] `NSSolverBuilder` depends on a narrow disabled-gate function, not
  on active geometry internals.
- [SOLID-X] No chapter-14 runtime activation, experiment result, branch
  deletion, main merge, FD/WENO/PPE fallback, smoothing, clipping, global
  correction, implicit dense fallback, implicit PCG fallback, CPU-first AO
  runtime path, hidden D2H GPU control, or hidden DCCD/UCCD damper was
  introduced.
