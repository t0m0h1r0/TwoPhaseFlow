# CHK-RA-SRC-GPU-OPT-004 — Retired Scheme Exclusion Review

Date: 2026-05-06

Scope: `src/twophase/` public scheme selection after the GPU-first PPE audit.

## User Trigger

User requested stale/obsolete computation schemes be excluded after the remaining non-GPU-first paths were classified.

## Verdict

MAJOR fixed. The remaining non-GPU-first PPE/IIM paths are no longer public active routes:

- `ppe_solver_type="ccd_lu"` is removed from `SolverConfig` and the default PPE factory registry.
- `ppe_solver_type="iim"` is removed from `SolverConfig` and the default PPE factory registry.
- `ppe_solver_type="iterative"` is removed from `SolverConfig` and the default PPE factory registry.
- IIM velocity reprojection modes (`iim`, `consistent_iim`) are removed from run-config parsing and default reprojection registration.

The implementations remain direct-import C2 references with `# DO NOT DELETE` comments and `docs/01_PROJECT_MAP.md §8` registration:

- `PPESolverCCDLU`
- `PPESolverIIM`
- `PPESolverIterative`
- `ConsistentIIMReprojector`

This follows C2: tested implementations were not deleted; stale schemes were excluded from active/public construction paths.

## Validation

- Targeted route/config/reference tests: `168 passed, 3 skipped`.
- `make test PYTEST_ARGS="..."` attempted first; remote was unavailable and local fallback failed because `python` is not on PATH in this worktree. The same target set passed with the workspace venv interpreter.
- Full local CPU suite with workspace venv: `569 passed, 32 skipped`.

## SOLID

[SOLID-X] No C1 violation found. High-level construction now depends only on active PPE/reprojection registrations; retired references are direct-import only.
