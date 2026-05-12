# CHK-RA-CH14-AO-FASTVOL-024 - AO-Fast GPU Runtime Completion

Date: 2026-05-12

## Purpose

Complete the geometric-cell-fraction runtime after the CHK-023 dense-GPU
fail-close review, then repeat code and GPU optimization review until no
actionable findings remain for this slice.

## Implementation

- Added `twophase.simulation.geometric_phase_runtime_gpu`.
- GPU `geometric_cell_fraction` initialization now bypasses dense exact
  `cut_geometry_2d` and builds a device-resident `GeometricPhaseState` from the
  active P1 geometry formulas.
- Runtime q transport, swept-volume common flux, material Hodge, capillary
  packet, and capillary application now remain backend-native on CUDA.
- `TwoPhaseNSSolver._advance_geometric_phase_stage()` chooses the GPU packet on
  CuPy and keeps the dense exact AO runtime CPU-only.
- q-derived cell density/theta are averaged to the nodal NS material lattice
  before predictor/PPE stages, while the AO material packet keeps cell density
  for face-Hodge/capillary work.
- Non-static AO pressure reaction now passes through existing
  `pressure_coordinate` history coupling instead of being blocked.

## Approximation And Accuracy

The GPU capillary pressure-range solve uses an explicit diagonal active-Schur
approximation:

`lambda_D = diag(J_q J_q^T)^{-1} J_q(-sigma dS_h)`.

This is not a hidden PCG/DC fallback.  Its accuracy is exposed through the
device-resident `schur_residual_linf`, `young_laplace_residual_linf`,
`young_laplace_residual_l2`, and `young_laplace_normal_residual_linf` fields in
the runtime certificate.  The exact CPU dense runtime remains the oracle path;
GPU no longer enters it.

Complexity for this slice is one full-lattice active-kernel pass per geometry
refresh plus face-local vector operations.  It removes the dense Schur/CG
host-control route that dominated the direct AO branch.  Compact support
compaction without device-size host synchronization remains future work; no
fallback to host compaction is used.

## Review Loop

First review findings and fixes:

- P1: GPU runtime still lacked an actual non-dense path after CHK-023. Fixed by
  adding the GPU packet and wiring solver initialization/advance to it.
- P1: AO cell density was handed to nodal NS operators, causing shape mismatch.
  Fixed by adding a q/theta cell-to-node material view at the pipeline boundary.
- P1: non-static AO with `pressure_history.form=pressure_coordinate` was still
  blocked. Fixed by letting the existing pressure-coordinate correction path
  consume the AO pressure-reaction RHS.
- P2: sigma-zero GPU packets could be classified as neither static nor driven.
  Fixed by routing the GPU packet through the non-static zero-increment path,
  avoiding device-scalar static comparisons.

Second review found no remaining dense AO entry, implicit PCG/DC fallback,
host compaction fallback, `.get()`/`asnumpy()`/`to_host()` use inside the new
GPU packet, or pressure-coordinate blocker in this slice.

## Capillary Smoke

Remote GPU short capillary-wave smoke:

`make cycle EXP=experiment/run.py ARGS="--config _tmp_ch14_ao_fast_capillary_short --no-checkpoint-final"`

Result:

- Completed 3 steps on the remote GPU.
- `dt = 9.12945719818128e-06` for all 3 steps.
- Kinetic energy: `1.25e-46`, `4.58e-09`, `2.57e-08`.
- Volume drift: `0.0`, `0.0`, `1.38e-16`.
- Signed mode amplitude stayed finite at `2.0247866136691e-04`.
- Pulled result: `experiment/ch14/results/_tmp_ch14_ao_fast_capillary_short/data.npz`.

The temporary YAML was removed after the smoke run.

## Validation

- Local py_compile for touched modules: PASS.
- Local targeted tests:
  - `test_config_state_space.py`: PASS `20 passed, 1 skipped`.
  - pressure-coordinate history regressions: PASS `2 passed`.
  - GPU gate/config tests: PASS `20 passed, 2 skipped`.
- Remote GPU targeted test:
  `make test PYTEST_ARGS="-k test_geometric_runtime_gpu_backend_uses_active_packet_not_dense_runtime -q"`
  PASS `1 passed, 741 deselected`.
- Remote full suite through `make test`: PASS `910 passed, 3 skipped`.
- `git diff --check`: PASS.

## SOLID / Negative Knowledge

- [SOLID-S] GPU AO packet, dense CPU exact runtime, pressure-stage coupling,
  and NS material-lattice bridge stay separated.
- [SOLID-D] Solver activation depends on geometric runtime interfaces, not on
  direct dense-AO helpers.
- [SOLID-X] No main merge, branch deletion, FD/WENO/PPE fallback, hidden
  PCG/DC fallback, smoothing, clipping, global correction, hidden DCCD/UCCD
  damper, CPU-first fallback, host compaction fallback, or dense GPU fallback
  was introduced.
