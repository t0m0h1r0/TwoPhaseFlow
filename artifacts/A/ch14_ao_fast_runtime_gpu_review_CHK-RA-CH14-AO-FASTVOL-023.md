# CHK-RA-CH14-AO-FASTVOL-023 - AO-Fast Runtime GPU Review Hardening

Date: 2026-05-12

## Purpose

Repeat the code review and GPU optimization review after CHK-022 runtime
activation, fix all actionable findings, and leave no hidden dense GPU route.

## Findings

### P1 - Dense Exact Runtime Entered GPU Host-Control Paths

The geometric YAML contract requires:

- `gpu_contract.inner_host_transfers: forbidden`
- `gpu_contract.dense_runtime_fallback: forbidden`
- `projection.implementation: active_cached`

The CHK-022 runtime activation could still enter direct dense-AO
`Q_h/S_h/swept_flux/capillary/Schur-CG` helpers with CuPy arrays.  Those helpers
include Python-controlled scalar reductions and CPU-side component least squares,
so a remote GPU smoke run was an unoptimized dense-host-control observation, not
an admitted AO-Fast GPU validation.

Fix:

- Added `twophase.geometry.gpu_runtime_guard`.
- Dense exact geometry, swept flux, compatibility projection, bundle capillary,
  and runtime materialisation now fail closed on CuPy namespaces/device scalars.
- `TwoPhaseNSSolver._advance_geometric_phase_stage` fails closed before dense
  geometric runtime entry on GPU.
- The import manifest classifies salvaged direct-AO functions as
  `cpu_exact_runtime` with `no_d2h_audit=gpu_fail_closed`.

### P1 - Active Projection Schedule Was Admitted Without Active Runtime Wiring

The parser/contract admitted `reinit_method=compatibility_projection` with a
positive schedule, but the active fused projection path is not connected to the
runtime yet.  That would route through dense Schur CG under a contract that says
active cached GPU projection is required.

Fix:

- `build_ao_fast_runtime_contract()` now rejects
  `reinit_method=compatibility_projection` until the fused active projection
  route is wired.
- A regression test locks this fail-close behavior.

### P2 - Legacy Advection Gate Signature Was Too Narrow

The fail-closed `geometric_swept_volume` legacy advection gate accepted only the
minimal `advance(psi, velocity, dt)` signature.  Some legacy call sites pass
`step_index`; those should still reach the fail-close message rather than a
generic Python `TypeError`.

Fix:

- The gate now accepts `**kwargs` and raises the same semantic fail-close error.

## Review Closure

Second-pass scans found no remaining P0/P1 issue in this slice.  Remaining
host boundaries are checkpoint I/O, dense oracle modules, existing active-table
host-compaction gates, and active-projection scalar guards that already fail
closed for CUDA arrays.

## Validation

- Local py_compile on touched runtime modules: PASS.
- Local targeted tests:
  `test_geometry_import_manifest.py`, `test_config_state_space.py`,
  `test_geometric_runtime_gpu_gates.py`,
  `test_geometry_dense_reference.py`, and `test_geometry_active_table.py`
  PASS: `38 passed, 3 skipped`.
- Remote full GPU suite:
  `make test`
  PASS: `910 passed, 3 skipped`.
- `git diff --check`: PASS.

## SOLID / Negative Knowledge

- [SOLID-S] Dense exact runtime guard, solver GPU boundary, contract adapter,
  and import-manifest governance stay split.
- [SOLID-D] GPU admission depends on explicit active fused AO-Fast capability,
  not concrete dense direct-AO helpers.
- [SOLID-X] No main merge, branch deletion, FD/WENO/PPE fallback, implicit PCG
  fallback, smoothing, clipping, global correction, hidden DCCD/UCCD damper,
  implicit CPU-first GPU fallback, or unoptimized dense GPU fallback was
  introduced.
