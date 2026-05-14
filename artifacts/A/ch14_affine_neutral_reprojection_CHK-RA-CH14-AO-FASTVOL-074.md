# CHK-RA-CH14-AO-FASTVOL-074

## Problem

Strict theory review found that the phase-separated affine-jump PPE route was
not fully context-safe.

The established contract is:

```text
a_f^Gamma = 1 / (theta rho_L + (1 - theta) rho_H)
```

for cut faces whenever the configured PPE is `phase_separated + affine_jump`.
Even when the physical jump is zero, the coefficient still requires the
current interface geometry `psi` so `theta` is defined.  Clearing the interface
context before homogeneous grid-rebuild reprojection changes the operator
contract.

## Root Cause

1. `LegacyReprojector` and `VariableDensityReprojector` cleared the PPE jump
   context before solving the homogeneous reprojection PPE.  After the
   low-order FDDirect base was corrected to fail closed, this exposed the
   missing neutral affine context during grid rebuild.
2. The high-order FCCD affine coefficient helper still silently returned the
   smooth harmonic coefficient when the affine context was missing.  That made
   the high-order route less strict than the low-order DC base.

## Fix

- Added a homogeneous reprojection context gate in
  `src/twophase/simulation/velocity_reprojector_basic.py`.
- For affine-jump PPE, homogeneous reprojection now installs a neutral
  zero-jump interface context carrying the current `psi`.
- Non-affine reprojection still clears the context before and after the solve.
- `affine_jump_face_inverse_density` now fails closed if affine context is
  missing.
- `PPESolverFCCDMatrixFree._add_affine_interface_jump_rhs` now distinguishes
  missing context from neutral zero-jump context: missing context raises;
  neutral context contributes zero RHS but still preserves cut-face
  coefficients.

## Verification

- `python3 -m py_compile` for changed source and tests: PASS.
- `git diff --check`: PASS.
- Remote `make test PYTEST_ARGS='-q -k affine'`: PASS
  (`27 passed, 1 skipped, 793 deselected`).
- Remote `make test PYTEST_ARGS='-q -k rebuild'`: PASS
  (`10 passed, 811 deselected`).
- Remote full `make test PYTEST_ARGS='-q'`: PASS
  (`786 passed, 35 skipped`).
- Remote ch14 AO stage-chain smoke:
  `make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 10 --runner-initial-grid-rebuild --prepare-grid-each-step --backend gpu --summary-only'`
  completed.  Key diagnostics: `max_ao_compat=0`, `max_yl_normal=0`,
  `max_div_u=9.399483863123e-08`, mean PPE DC iterations `34.7`.

## SOLID / Scope

[SOLID-S] The change is scoped to PPE interface-context ownership for
homogeneous reprojection and affine fail-close coefficient assembly.
[SOLID-D] Reprojection depends on the `IPPESolver` interface and runtime
options, not a concrete solver class.
[SOLID-X] No physical parameter, CFL, tolerance weakening, iteration-cap
tuning, solver-family substitution, GPU fallback, uniform-grid shortcut,
nonuniform-grid removal, interface-tracking rebuild removal, main merge,
branch deletion, or worktree removal was introduced.
