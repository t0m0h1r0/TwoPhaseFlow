# CHK-RA-CODE-GPU-006 — constrained_face DC base strict review and fix

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Worktree: `.claude/worktrees/codex-ra-code-paper-gpu-review-20260516`

## Request

User requested a strict review and repair loop:

1. thoroughly review code;
2. strictly review root-level paper/code mismatches;
3. judge whether refactoring is needed;
4. check GPU-first implementation;
5. stop only after no MAJOR-or-higher finding remains;
6. design an effective fix;
7. update code according to that fix.

## Scope

The review targeted the current open boundary/PPE front:

- `boundary_hodge.state_space=constrained_face`
- `RunCfg.boundary_face_space`
- high-order FCCD PPE operator and affine HFE RHS
- defect-correction low-order PPE base
- sparse/matrix-free FVM low-order implementations sharing `PPEBuilder`
- Ch14 wall/no-slip YAML and paper statements around accepted vs future
  restricted boundary pressure routes.

## Findings

### MAJOR-1: DC low-order base did not share the constrained face space

Status before this patch:

- `PPESolverFCCDMatrixFree` used `boundary_face_space="constrained_face"` in
  the high-order operator and affine RHS.
- `PPESolverFDDirect` did not read `boundary_face_space`.
- `PPEBuilder` did not apply any direct face-space restriction to sparse
  low-order coefficients.
- Therefore `PPESolverDefectCorrection` could solve residual corrections with a
  low-order base `L_L` that was not a low-order approximation of the same
  boundary-space operator `L_H`.

Why this is MAJOR:

Defect correction requires the low-order base to approximate the same physical
operator as the high-order target.  A `constrained_face` high-order operator
paired with a full-face low-order sparse base is a mixed boundary complex, not
the paper's DC contract.

### Paper/code strict check

No new MAJOR paper/code contradiction was found in the reviewed paper passages:

- the paper does not newly claim that the larger metric wall-retraction operator
  `D_h P_w G_A` is already the completed production route;
- the artifact for CHK-RA-CODE-GPU-005 explicitly distinguishes direct
  constrained route `D_h P_c G_A` from future metric `D_h P_w G_A`;
- wiki theory cards still correctly keep metric `P_w` as the larger remaining
  theorem-selected design front.

### Refactor judgment

A small cross-solver refactor was necessary:

- put direct boundary face-space masking at `PPEBuilder`/FVM coefficient
  assembly boundaries;
- thread `boundary_face_space` through `FDDirect`, `FVMSpsolve`, and
  matrix-free FVM/FD base solvers;
- do not introduce a new abstraction for metric `P_w` yet, because that is a
  separate operator-design problem and would overreach this fix.

### GPU-first check

The fix remains GPU-first:

- sparse `PPEBuilder` uses cached static topology masks converted to the active
  array namespace;
- matrix-free FVM applies masks directly in backend arrays with `xp.where`;
- no density, pressure, or residual field is copied to host to decide the
  boundary face-space mask;
- existing prepared sparse solve reuse remains unchanged.

## Implemented Fix

Code changes:

- `src/twophase/ppe/ppe_builder.py`
  - stores canonical `boundary_face_space`.

- `src/twophase/ppe/ppe_builder_helpers.py`
  - masks low-order face coefficients for `impermeable_face` and
    `constrained_face` using the same direct face-space convention as the
    high-order FCCD route.

- `src/twophase/ppe/fd_direct.py`
  - reads `boundary_face_space` from runtime config;
  - passes it to `PPEBuilder`;
  - preserves it across grid rebuild and structure refresh.

- `src/twophase/ppe/fvm_spsolve.py`
  - reads and passes `boundary_face_space` to `PPEBuilder`.

- `src/twophase/ppe/fvm_matrixfree.py`
  - reads canonical `boundary_face_space` and passes it to line coefficient
    assembly.

- `src/twophase/ppe/fvm_matrixfree_helpers.py`
  - applies backend-native direct face-space masks to matrix-free coefficients.

- `src/twophase/tests/test_interface_stress_closure.py`
  - adds a regression proving `FDDirect` low-order base removes constrained
    wall-normal and wall-tangential face couplings.

- `src/twophase/tests/test_ns_pipeline_fccd.py`
  - asserts Ch14 DC base solvers retain the same `boundary_face_space` as the
    high-order operator for both `impermeable_face` and `constrained_face`.

## Residual MAJOR Review State

No MAJOR-or-higher finding remains in the reviewed direct constrained-face
route after this patch.

Important residual lower/strategic item:

- the metric wall-retraction pressure operator `D_h P_w G_A` is still a future
  theory-complete route.  It is not claimed as completed here.  The now-fixed
  route is direct constrained face space `D_h P_c G_A` consistently threaded
  through high-order operator, affine RHS, and low-order DC base.

## Validation

- `git diff --check`: PASS
- Remote-first `make test` with target node IDs:
  - due the remote pytest root behaviour, the command collected the repository
    suite;
  - result: `795 passed, 35 skipped in 44.49s`.

## SOLID / Scope

[SOLID-S] Boundary face-space masking is kept at PPE coefficient/operator
assembly boundaries; solver orchestration remains separate.

[SOLID-O] Existing `full_face` and `impermeable_face` routes remain available;
`constrained_face` now extends them consistently instead of replacing them.

[SOLID-D] Runtime factories continue to pass solver options through the
`PPEBuildCtx`/config-shim contract; high-level NS code does not branch on a
concrete PPE class.

[SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance weakening,
solver-family substitution, hidden CPU fallback, experiment YAML/result, paper
claim expansion, main merge, branch deletion, or worktree removal was
introduced.
