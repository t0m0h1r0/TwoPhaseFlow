# CHK-RA-CODE-GPU-007 — ch14 capillary one-period regression check

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Worktree: `.claude/worktrees/codex-ra-code-paper-gpu-review-20260516`

## Request

User requested a one-period `ch14_capillary` rerun to confirm the recent code
changes did not degrade the capillary-wave benchmark.

## First Rerun Result

Command:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary --no-checkpoint-final"
```

Result: FAIL at step 2 during low-order DC base factorization.

Error:

```text
RuntimeError: Factor is exactly singular
```

The failure was caused by the immediately preceding CHK-RA-CODE-GPU-006 sparse
low-order face-space mask.  It applied the high-order direct face-flux mask to
the low-order FVM sparse adjacency coefficients.  That is not the same object:
the low-order FVM wall condition is represented by Neumann/ghost-cell rows, not
by deleting the first interior pressure coupling.  Deleting those couplings
isolated wall pressure rows and made the sparse DC base singular.

## Fix Applied Before Final Rerun

- Removed direct face-space coefficient zeroing from:
  - `src/twophase/ppe/ppe_builder_helpers.py`
  - `src/twophase/ppe/fvm_matrixfree_helpers.py`
  - `src/twophase/ppe/fvm_matrixfree.py`
- Kept `boundary_face_space` metadata threading through low-order solvers so
  runtime contracts remain visible.
- Replaced the over-strong sparse-base test with a nonsingularity regression:
  `PPESolverFDDirect.prepare_operator(rho)` must factorize for
  `full_face`, `impermeable_face`, and `constrained_face`.

Interpretation:

The direct constrained face-space is an FCCD face-flux operator restriction.
The sparse low-order FVM base remains a Neumann low-order correction operator,
not a direct deletion of nodal adjacency coefficients.

## Validation Before Final Rerun

Command:

```bash
make test PYTEST_ARGS='-q twophase/tests/test_interface_stress_closure.py::test_fd_direct_low_order_base_factorizes_boundary_face_spaces twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_yaml_builds_solver'
```

Remote pytest root collected the repository suite.

Result:

```text
795 passed, 35 skipped in 45.72s
```

`git diff --check`: PASS.

## Final One-Period Rerun

Command:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary --no-checkpoint-final"
```

Result: PASS.

Runtime:

```text
real 11m35.084s
```

Output:

```text
Saved data -> /root/TwoPhaseFlow/experiment/ch14/results/ch14_capillary/data.npz
Pull complete.
```

Pulled result:

```text
experiment/ch14/results/ch14_capillary/data.npz
```

## Metrics

| Metric | Value |
|---|---:|
| samples | `2585` |
| final time | `0.046742983863` |
| `pre_blowup_checkpoint_written` | `False` |
| initial signed amplitude | `2.002821033748e-04` |
| quarter-period signed amplitude | `1.574613338802e-05` |
| half-period signed amplitude | `-1.833865831437e-04` |
| three-quarter signed amplitude | `-4.067365721147e-05` |
| final signed amplitude | `1.590460892479e-04` |
| final amplitude ratio | `0.794110340205` |
| max kinetic energy | `8.292391914738e-06` |
| final kinetic energy | `1.143411766571e-06` |
| final volume drift | `1.477225460012e-14` |
| max volume drift | `5.719166459861e-14` |
| initial `dy_min` | `3.838821359487e-04` |
| final `dy_min` | `3.919802248741e-04` |

## Regression Verdict

No capillary-wave degradation remains after the sparse low-order base correction.

Compared with the previous paper-update reference recorded in
CHK-RA-CODE-GPU-004 (`final ratio 0.792`, max KE `8.3385e-6`, max volume drift
`9.9611e-14`), this rerun:

- completes the same one-period final time;
- keeps the wave bounded and restoring;
- has a very similar final amplitude ratio (`0.7941`);
- has a slightly lower max kinetic energy (`8.292e-6`);
- improves roundoff-scale volume conservation (`5.72e-14` max drift).

The current paper's exact printed numerical values are therefore slightly stale
relative to this rerun, but the benchmark claim is not degraded.

## SOLID / Scope

[SOLID-S] The regression fix removes an invalid coefficient-level responsibility
from low-order sparse FVM assembly; high-order direct face-space restriction and
low-order Neumann correction remain separate numerical objects.

[SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance weakening,
solver-family substitution, hidden CPU fallback, experiment YAML edit, main
merge, branch deletion, or worktree removal was introduced.
