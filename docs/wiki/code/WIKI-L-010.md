---
id: WIKI-L-010
title: "PPE Solver Architecture: FCCD Operator, DC Wrapper, and Explicit FVM/FD Routes"
status: ACTIVE
created: 2026-04-10
updated: 2026-05-16
depends_on: [WIKI-L-009, WIKI-L-046, WIKI-X-053, WIKI-X-054]
---

# PPE Solver Architecture

## Current Production Reading

The current production pressure architecture is no longer the April
CCD-LU/IIM/iterative factory stack.  Chapter 14 active-geometry capillary runs
use a phase-separated FCCD matrix-free pressure operator, wrapped by defect
correction, with a low-order base that must represent the same boundary and
affine interface physics.

```text
YAML / RunCfg
  -> SolverPPEOptions
  -> PPESolverFCCDMatrixFree         (L_H)
  -> PPESolverDefectCorrection
       base: PPESolverFDDirect or PPESolverFDMatrixFree  (L_L)
```

`src/twophase/ppe/factory.py` still exposes explicit keyed FVM/FD routes:

| Key | Solver | Role |
|---|---|---|
| `fvm_iterative`, `fvm_matrixfree`, `matrixfree` | `PPESolverFVMMatrixFree` | Matrix-free FVM PPE with backend Krylov solve and fail-closed preconditioner selection. |
| `fvm_direct`, `fvm_spsolve`, `spsolve` | `PPESolverFVMSpsolve` | Sparse FVM direct reference route. |
| `fd_direct`, `fd_spsolve` | `PPESolverFDDirect` | Factorized low-order FD base for DC and explicit FD direct solves. |
| `fd_iterative`, `fd_matrixfree` | `PPESolverFDMatrixFree` | Matrix-free FD low-order base route. |

`PPESolverFCCDMatrixFree` is scheme-registered as `fccd_iterative` with
aliases `fccd_matrixfree` and `fccd`; it is built through the scheme build
context because it requires the shared `FCCDSolver`.

## Active Contract Details

- `PPESolverFCCDMatrixFree` applies `D_f A_f G_f p` with phase-separated
  coefficients, affine Young--Laplace jump closure, pressure-history face
  coordinates, and `boundary_face_space` via `apply_direct_face_boundary_space`.
- The affine RHS and the operator must be projected through the same direct
  face space.  Applying the boundary face space to `A_f G_f p` but not to
  `A_f B_HFE(j)` is a mixed-complex bug.
- `PPESolverDefectCorrection` accepts by residual convergence.  Correction
  count is only a cap.
- `PPESolverFDDirect`/`PPEBuilder` must receive the same affine interface
  context and boundary face space as the high-order operator.  The cut-face
  coefficient for `affine_jump` is the phase-separated resistance
  `1/(theta rho_L + (1-theta) rho_H)`, not the smooth harmonic coefficient.
- Low-order FVM/FD sparse bases must not implement direct face-space
  restrictions by deleting sparse adjacency coefficients.  Low-order FVM wall
  Neumann rows are not high-order direct face components; over-masking can
  isolate pressure rows and make the factorization singular.

## Grid and Cache Epochs

All PPE implementations must refresh or invalidate metric-dependent state
after grid rebuilds.  This includes FCCD geometry caches, FVM line
preconditioner coefficients, sparse factors, phase gauges, affine interface
contexts, and pressure-history decode contexts.  Reusing a prepared solve plan
across a changed grid, density, phase, boundary, or affine-context epoch is a
different algebraic problem.

## Legacy and Reference Reading

Older CCD-LU, IIM, pseudotime, ADI/sweep, Rhie--Chow, and GFM-corrector cards
remain useful for historical comparisons and isolated references.  They must
not be read as current production defaults or as fallback remedies for
phase-separated FCCD/HFE/DC failures.

## Review Checklist

Before changing PPE code, prove:

1. high-order `L_H` and low-order `L_L` encode the same physical operator;
2. affine RHS, corrector subtraction, and pressure history use the same sign,
   gauge, coefficient, and time level;
3. `full_face`, `impermeable_face`, and `constrained_face` all factorize or
   fail closed in the intended solver family;
4. nonuniform, periodic, wall, cut-face, and rebuild paths share the same
   metric epoch;
5. absent required context raises instead of silently selecting a smooth or old
   pressure law.
