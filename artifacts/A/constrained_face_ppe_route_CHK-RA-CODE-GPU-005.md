# CHK-RA-CODE-GPU-005 — constrained_face PPE execution route

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Worktree: `.claude/worktrees/codex-ra-code-paper-gpu-review-20260516`

## Request

User requested a concrete fix based on the strict code review findings.

## Review Finding Being Addressed

`boundary_hodge.state_space=constrained_face` was parsed as a no-slip face-state
contract, but it did not reach the pressure solve as an executable face-space
restriction:

- YAML/config declared `constrained_face`.
- `RunCfg.boundary_face_space` collapsed it to `full_face`.
- runtime normalization rejected `constrained_face`.
- existing FCCD matrix-free PPE code already had a direct constrained-face
  branch, but production configs could not select it.

This made the wall-bounded no-slip route a mixed contract: corrected/stored
faces could be no-slip constrained while the PPE operator was still full-face.

## Fix Options Considered

1. Metric wall retraction `D_h P_w G_A` inside every matrix-free PPE operator
   application.
   This is the largest theory-complete route, but it would nest a boundary
   Schur/CG projection inside GMRES, change the operator range/nullspace, and
   require a separate high/low defect-correction design and GPU performance
   review.  It remains the larger theorem-selected front.

2. Executable direct constrained face-space route `D_h P_c G_A`.
   `P_c` is the existing direct no-slip face-space projector implemented by
   `apply_direct_face_boundary_space(..., boundary_face_space="constrained_face")`.
   It is already used by FCCD matrix-free operator assembly and affine RHS
   assembly, is backend-array based, and keeps `full_face` and
   `impermeable_face` routes intact.  The missing piece was config/runtime
   routing and tests.

3. Post-corrector or diagnostic-only boundary Hodge.
   Rejected as a fix for this review item, because the left-hand PPE operator
   and affine HFE RHS must use the same admissible face space.

Chosen fix: option 2.  This closes the executable-routing bug and makes
`constrained_face` a first-class direct PPE face space.  It does not relabel the
metric boundary-Hodge diagnostic `P_w` as solved.

## Implemented Changes

- `src/twophase/simulation/config_run_builder_sections.py`
  - maps `boundary_hodge.state_space in {impermeable_face, constrained_face}`
    directly to `RunCfg.boundary_face_space`.
  - keeps `full_face` unchanged for unconstrained routes.

- `src/twophase/simulation/ns_runtime_config.py`
  - normalizes `boundary_face_space` through
    `normalise_boundary_face_space`, so aliases and `constrained_face` share
    one canonical parser.

- `src/twophase/tests/test_config_io_fccd.py`
  - updates Ch14 canonical YAML expectations so no-slip wall configs retain
    `boundary_face_space="constrained_face"` instead of collapsing to
    `full_face`.

- `src/twophase/tests/test_ns_pipeline_fccd.py`
  - asserts Ch14 rising-bubble solver construction threads
    `constrained_face` into the FCCD PPE operator.

- `src/twophase/tests/test_interface_stress_closure.py`
  - adds an operator/RHS contract test:
    - `_apply_operator_core(p)` equals `D_h P_c G_A p`;
    - wall traces of direct constrained faces are zero;
    - affine HFE RHS uses the same constrained face space as the operator.

## Contract After This Change

For a no-slip wall configuration with

```yaml
numerics:
  projection:
    face_no_slip_boundary_state: true
    boundary_hodge:
      state_space: constrained_face
```

the executable pressure route is now the direct constrained-face route:

```text
L_c p = D_h P_c G_A p
rhs_c += D_h P_c A_f B_HFE(j)
```

where `P_c` is the direct wall-face no-slip projector.  This removes the
previous mixed-complex bug where `P_c` was absent from the PPE solve.

The larger metric wall-retraction route

```text
K_w p = D_h P_w G_A p
```

remains a separate future design item and should not be claimed as completed by
this patch.

## Validation

- `git diff --check`: PASS
- Remote-first validation:
  - command attempted with targeted node IDs using `src/twophase/...`; remote
    pytest root rejected those paths before collection.
  - rerun with `twophase/tests/...`; the remote pytest root collected the full
    suite.
  - result: `794 passed, 35 skipped in 44.05s`.

## SOLID / Scope

[SOLID-S] The code change is scoped to boundary-face-space routing and tests for
the already implemented FCCD direct constrained-face operator branch.

[SOLID-O] Existing `full_face` and `impermeable_face` behavior is preserved;
`constrained_face` is added as the third executable route.

[SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance weakening,
solver-family substitution, hidden CPU fallback, experiment YAML change, main
merge, branch deletion, or worktree removal was introduced.
