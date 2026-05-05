# CHK-RA-SRC-GPU-OPT-001 — src GPU Optimization Review

## Scope

Strict ResearchArchitect review of `src/twophase/` numerical schemes for GPU
hot-path fidelity: `backend.xp` use, CuPy scalar sync, host transfers, sparse
solver routing, and CPU/GPU semantic parity.

Stop condition: no MAJOR+ findings, or review round > 10.

## Round 1 — MAJOR Fixed

Finding: WENO5 level-set advection/reinitialization and ξ-space SDF crossing
extraction still used Python scalar gates on backend arrays:

- `LevelSetAdvection._rhs`: `float(max(xp.max(...)))`
- `ReinitializerWENO5._rhs`: `float(xp.max(...))`
- `xi_sdf_phi`: `if xp.any(mask)`

Impact: on CuPy these force device-to-host synchronization inside the scheme
hot path; the WENO gates are executed per RHS evaluation, and `xi_sdf_phi`
branches on device reductions.

Fix:

- Keep WENO Lax-Friedrichs `alpha` as a backend scalar via `xp.stack` /
  `xp.max` / `xp.maximum`.
- Use CuPy/NumPy array metadata (`where(...).size`) for zero-crossing branch
  selection in `xi_sdf_phi`, avoiding device scalar truth conversion.

Commit: `5b1c6cec fix: keep levelset scalar gates on GPU`

## Round 2 — No MAJOR+

Audited PPE/FVM/FCCD matrix-free and defect-correction paths. Production GPU
paths keep operator application, sparse matrix values, RHS vectors, and GMRES
matvecs device-resident. Scalar synchronization remains only at convergence /
diagnostic boundaries where Python control flow records residuals or decides
iteration termination.

Host-transfer-heavy paths observed in IIM/CCD-LU helper workflows are legacy or
reference solver paths, not the production FCCD/FVM matrix-free stack. No
additional MAJOR+ production GPU hot-path finding.

## Round 3 — No MAJOR+

Targeted residual scans after the fix:

- No remaining `float(max(...))`, `float(xp.max(...))`, or `if xp.any(...)`
  pattern in active WENO/eikonal hot paths.
- Remaining scalar host conversions are confined to legacy baselines,
  diagnostics, checkpoint/output, configuration parsing, or explicit
  convergence scalar boundaries.

Stop: no MAJOR+ findings before round 10.

## Validation

- `py_compile` PASS for modified modules.
- `git diff --check` PASS.
- `make test` attempted remote first; remote unavailable, local CPU fallback
  run with parent-worktree venv: `553 passed, 31 skipped in 50.20s`.

## SOLID-X

No C1 violation introduced. No tested implementation deleted. No FD/WENO/PPE
fallback introduced. Changes are limited to preserving existing algorithms while
removing avoidable GPU synchronization.
