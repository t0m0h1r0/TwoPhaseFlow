# CHK-RA-GPU-UTIL-004 — Optional FD iterative CG base for DC

Date: 2026-05-01
Branch/worktree: `ra-gpu-util-20260501` /
`.claude/worktrees/ra-gpu-util-20260501`

## Request

Make the defect-correction low-order slot selectable so `fd/direct` can remain
the fast default while CG and related iterative solvers can be tried as the
`L_L` correction solve.

## Design

- Keep the paper contract: high-order residual `L_H` remains the outer FCCD
  operator; the inner solver remains the low-order FD `L_L` correction path.
- Add `fd_iterative` as an optional base solver rather than replacing
  `fd_direct`.
- CG solves the control-volume-weighted SPD equivalent system
  `-W L_L p = -W rhs`; the unweighted row-scaled FD/FVM operator is not
  symmetric in the Euclidean inner product.
- Reject `line_pcr` with CG because it is a GMRES-oriented nonsymmetric
  preconditioner.  CG accepts `jacobi` or `none`.
- Disable direct fallback in `fd_iterative` so the configured iterative path
  cannot silently turn back into a direct solve.

## Implementation

- Added `PPESolverFDMatrixFree` and registered `fd_iterative`,
  `fd_matrixfree`, and `fd_cg` aliases.
- Extended backend Krylov helpers with CG compatibility wrappers.
- Extended the matrix-free low-order solver with method-specific GMRES/CG
  paths and weighted-CG operator/preconditioner handling.
- Extended YAML parsing so DC base solvers can specify:

  ```yaml
  base_solver:
    discretization: fd
    kind: iterative
    method: cg
    preconditioner: jacobi
  ```

- Kept ch14 production YAMLs on `fd/direct`; documented the optional iterative
  base in `experiment/ch14/config/README.md`.

## Validation

- `make test PYTEST_ARGS='-k fd_iterative -q'` → PASS, 2 selected.
- `make test PYTEST_ARGS='-k fd_matrixfree -q'` → PASS, 1 selected; CG result
  matches `PPESolverFDDirect` on the same low-order operator.
- `make test PYTEST_ARGS='-k fvm_matrixfree -q'` → PASS, 8 selected.
- `make test PYTEST_ARGS='-k defect_correction -q'` → PASS, 11 selected.
- `git diff --check` → PASS.

## SOLID Audit

- `[SOLID-X]` no violation found.  The new solver is additive, registered
  through the existing `IPPESolver` registry, and runtime/config code depends
  on solver names and the existing interface rather than concrete class checks.
