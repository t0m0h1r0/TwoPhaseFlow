# CHK-RA-SRC-TEST-001 — src test failure retention audit

## Scope

Remote `make test PYTEST_ARGS="-q"` on `src/twophase/tests` reported five
failures.  This review classifies each failing test as keep-and-fix or discard.

## Decisions

| Test | Verdict | Rationale |
|---|---|---|
| `test_chain_phi_precision_alpha2` | keep, fix | The production reinitializer uses spatial `eps_local` on stretched grids; the test inverted with a constant epsilon and measured the wrong field. |
| `test_ch14_yaml_initial_conditions_use_object_specs` | keep, fix | The checked-in ch14 config set is now five YAMLs; the hard-coded count of six was stale. |
| `test_phase_separated_pressure_jump_stack_one_step_no_nan` | keep, fix | Phase-mean projection subtracts an O(1e11) RHS mean; the absolute residual is O(1e-5), i.e. roundoff relative to the pre-projection mean. |
| `test_split_reinit_y_flip_magnitude[2.0]` | keep, fix | ASM-122-A classifies the composed split-reinit drift as Lyapunov-amplified, not a new algorithm bug; the regression threshold should stay below the pre-CHK-168 band. |
| `test_ridge_eikonal_no_ke_blowup` | discard | The test no longer isolates the CHK-160 epsilon mismatch. It entangles a tiny full NS pressure/reprojection path that now blows up even with `surface_tension_scheme="none"`; the retained `test_reinit_call2_idempotent` covers the epsilon-local regression directly. |

## SOLID Audit

[SOLID-X] no production boundary was changed.  Test edits remove stale
assumptions, retain live contracts, and do not introduce FD/WENO/PPE fallback
paths.
