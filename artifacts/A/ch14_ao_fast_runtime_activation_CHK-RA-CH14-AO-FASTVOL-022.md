# CHK-RA-CH14-AO-FASTVOL-022 - AO-Fast Runtime Activation

Date: 2026-05-12

## Purpose

Complete the implementation phase by turning the previously validated AO-Fast
YAML/runtime contract into an executable chapter-14 geometric runtime path,
while preserving the fail-closed GPU policy and the no-hidden-fallback contract.

## Implemented Runtime Path

- Imported the direct AO branch's reusable state, geometry, swept-volume,
  capillary, compatibility-projection, and checkpoint knowledge into typed
  `twophase.geometry` and `twophase.simulation` modules.
- Replaced the disabled solver gate with `build_ao_fast_runtime_contract(cfg)`
  validation followed by normal solver construction.
- Added initial geometric `phi` construction and `GeometricPhaseState` creation
  so the runtime owns q/theta/phi handoff explicitly.
- Routed q/common-flux transport, bundle virtual-work capillary forcing,
  pressure reaction, corrector embedding, and diagnostic q-volume through the
  geometric runtime state.
- Admitted `q_cell_fraction`, `geometric_swept_volume`,
  `bundle_virtual_work`, and `compatibility_projection` only under explicit
  geometric YAML declarations.
- Added a fail-closed geometric swept-volume advection gate so the legacy
  psi-advection API cannot silently execute the AO geometric transport path.

## GPU / Fail-Closed Notes

- The runtime uses the existing `backend.xp` contract for arrays and keeps the
  active AO-Fast GPU gates from CHK-020/021 intact.
- Unsupported nonempty GPU PCG/projection control remains fail-closed; no
  implicit CPU fallback is introduced.
- Dense direct-AO modules are carried as exact state/capillary/runtime
  components and oracle/debug material, not as a hidden replacement when the
  active AO-Fast path refuses an unsupported GPU operation.

## Capillary Smoke Experiment

Temporary config:
`experiment/ch14/config/_tmp_ch14_ao_fast_capillary_short.yaml`.

Command:
`make cycle EXP=experiment/run.py ARGS="--config _tmp_ch14_ao_fast_capillary_short --no-checkpoint-final"`.

Result:

- Remote GPU run completed 3 steps.
- Step 3 reported finite kinetic energy and `div_u = 2.077e-16`.
- Data was pulled to
  `experiment/ch14/results/_tmp_ch14_ao_fast_capillary_short/data.npz`.
- The temporary YAML was removed after the smoke run because chapter-14
  production configs remain curated separately.

## Validation

- `git diff --check`: PASS before this ledger/artifact update.
- Targeted remote test:
  `make test PYTEST_ARGS="-k test_valid_geometric_contract_builds_config_and_solver_runtime"`
  PASS: `1 passed, 738 deselected`.
- Full remote GPU suite:
  `make test`
  PASS: `907 passed, 3 skipped`.

## SOLID / Negative Knowledge

- [SOLID-S] Solver-contract validation, phase-state runtime, step force and
  corrector services, diagnostics, and advection gating stay split.
- [SOLID-D] Solver construction depends on the AO-Fast runtime contract and
  backend-neutral runtime interfaces rather than concrete direct-AO internals.
- [SOLID-X] No main merge, branch deletion, FD/WENO/PPE fallback, implicit PCG
  fallback, smoothing, clipping, global correction, hidden DCCD/UCCD damper, or
  implicit CPU-first GPU fallback was introduced.
