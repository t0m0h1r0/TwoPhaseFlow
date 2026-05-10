# CHK-RA-CH14-PPE-DC-GPU-D2H-001 — PPE defect-correction GPU D2H audit

## Question

Confirm whether the residual-minimizing PPE defect-correction line search is
GPU-optimal, and especially whether it transfers large arrays from device to
host merely to make acceptance decisions.

## Finding

The previous implementation did not transfer full pressure/residual arrays to
host in the line-search decision.  However, it did perform repeated scalar
device-to-host synchronizations and repeated `operator.apply(trial_pressure)`
calls for each candidate alpha.  That is not a large D2H bug, but it is not the
right GPU shape either.

## Fix

The line search now evaluates all candidates on device using the quadratic
identity

```text
||r - alpha A delta||_2^2
  = ||r||_2^2 - 2 alpha <r,A delta> + alpha^2 ||A delta||_2^2.
```

The candidate vector consists of the residual-minimizing alpha and the generic
backtracking sequence.  `trial_sq` and the validity mask are device arrays.
Only a tiny selected tuple is copied to host:

```text
[accepted, selected_alpha]
```

There is no per-candidate large D2H transfer and no per-candidate pressure
operator application.

## Remaining Host Boundaries

The solver still transfers scalar diagnostics and loop-control reductions:

- initial RHS norm;
- current residual norm per correction;
- selected alpha tuple, length 2;
- final residual norm and infinity norm.

These are scalar or length-2 transfers, not field transfers.  They are the
current Python-control boundary and diagnostics boundary.

## Validation

- `python3 -m pytest src/twophase/tests/test_defect_correction.py src/twophase/tests/test_interface_projection_diagnostics.py -q`
  PASS: `17 passed`
- `git diff --check` PASS
- new test `test_defect_correction_line_search_keeps_gpu_transfers_scalar_sized`
  asserts the tracked GPU-style `asnumpy` transfers are scalar-sized, with
  maximum transfer length `<= 2`.
- existing overscaled-correction test now asserts the one-step solve uses only
  three high-order `operator.apply` calls for the accepted correction path:
  residual, `A delta`, and final residual.
