# CHK-RA-TESTS-002 — Pressure Test Metadata Cleanup

Date: 2026-05-03
Branch: `ra-tests-cleanup-20260503`
Verdict: PASS

## Scope

- Test file: `src/twophase/tests/test_pressure.py`.
- Focus: stale pressure-test descriptions, unused projection scaffolding, and legacy solver configuration fields.

## Findings

- Obsolete metadata: the file header still described CCD+LGMRES/pseudotime coverage and a removed PPESolverSweep test, while the active tests now exercise FVM `PPEBuilder`, CCD-LU component/reference residuals, Rhie-Chow divergence, and MMS convergence.
- Stale test shape: `test_divergence_free_projection` did not run a projection or velocity corrector; it only checked that CCD differentiation keeps an analytic solenoidal field nearly divergence-free.
- Dead config: CCD-LU MMS tests still passed unused `pseudo_*` fields even though the selected solver is explicitly `ccd_lu`.

## Changes

- Rewrote the file-level checklist to match the active tests.
- Renamed `test_divergence_free_projection` to `test_ccd_divergence_of_solenoidal_field_is_small`.
- Removed the unused `VelocityCorrector` import, unused corrector/rho/dt setup, stale `pseudo_*` config fields, and the obsolete removed-test tombstone.

## Validation

- `git diff --check` PASS.
- Remote targeted pytest PASS: `python -m pytest twophase/tests/test_pressure.py -v --tb=short` (`6 passed in 6.46s`).

## SOLID-X

- [SOLID-X] No production code changed. The cleanup aligns test names and metadata with existing component boundaries; no tested implementation was deleted.
