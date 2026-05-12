# CHK-RA-CH14-AO-FASTVOL-026 - GPU AO capillary fail-close fix

## Scope

User asked whether the capillary-wave issue was already fixed, and to fix it if
not.  The preceding CHK-RA-CH14-AO-FASTVOL-025 was an RCA/probe only; no
production solver guard had been installed.

## Theory Contract

For AO capillarity, the pressure reaction can enter momentum/PPE only when the
active-stratum Young-Laplace normal equation is certified:

```text
J_q^T lambda = -dS
```

The current GPU packet uses a diagonal active-Schur approximation.  It is an
admissible proposal only if its device residuals are within tolerance and if a
non-static packet retains a nonzero pressure-balanced face drive in the same
face-mass work metric.  A `pressure_coordinate` history additionally requires a
scalar AO pressure coordinate; face reaction increments alone are not enough.

## Fix

- Added `validate_geometric_runtime_capillary_fail_close_gpu` at the solver
  boundary.  It synchronizes scalar diagnostics once, outside the packet hot
  path, and rejects:
  - q/phi compatibility residual above tolerance;
  - diagonal active-Schur Young-Laplace normal residual above tolerance;
  - non-static AO with `pressure_history_mode='pressure_coordinate'` before a
    scalar AO pressure coordinate exists;
  - non-static packets whose pressure-balanced drive is zero despite nonzero
    predictor capillary increment.
- Wired the gate into `TwoPhaseNSSolver._advance_geometric_phase_stage` before
  the packet reaches predictor/PPE slots.
- Corrected the sigma-zero GPU classification to `pressure_exact_static` with
  no capillary drive, so the guard does not over-reject the physically empty
  capillary case.
- Updated the ch14 diagnostic probe to print a `FAIL_CLOSE` row instead of
  hiding the intended guard behind an unstructured traceback.

## Verification

- Local py_compile: PASS.
- Local targeted config/GPU-gate tests: PASS, with GPU tests skipped locally.
- Remote GPU targeted tests:
  `make test PYTEST_ARGS="twophase/tests/test_config_state_space.py -k geometric_runtime_gpu_backend -q"`
  -> `2 passed`.
- Remote broader suite:
  `make test PYTEST_ARGS="twophase/tests/test_config_state_space.py -q"`
  -> `710 passed, 33 skipped`.
- `git diff --check`: PASS.

## Residual Work

This is the fail-close production fix, not the full high-speed non-static AO
solver.  A 1/4-period capillary-wave run should now stop with an explicit
contract error until the certified active Schur/PCG/Newton/DC solve and scalar
AO pressure-coordinate history are derived and implemented.
