# CHK-RA-TESTS-001 — Src Test Cleanup Unit 1

Date: 2026-05-03
Branch: `ra-tests-cleanup-20260503`
Verdict: PASS

## Scope

- Test files: `src/twophase/tests/test_simulation.py`, `src/twophase/tests/test_gfm.py`.
- Focus: obsolete xfail removal, PR-2 compliant PPE choice in retained integration smokes, and preservation of still-useful builder/GFM stability checks.

## Findings

- Obsolete: two `strict=False` Laplace pressure sign xfails encoded the retired CCD-LU sharp-discontinuity integration path. They were not active regression coverage and contradicted the current PPE policy that restricts CCD Kronecker LU to intentional component/reference use.
- Retain: the builder and GFM smoke checks still exercise useful construction and finite-field guarantees, so they were kept and moved to `fvm_direct` PPE instead of deleting the whole files.

## Changes

- Removed `test_laplace_pressure_sign` from `test_simulation.py`.
- Removed `test_gfm_laplace_pressure_sign` from `test_gfm.py`.
- Updated the remaining simulation and GFM integration smoke configs from explicit `ccd_lu` to `fvm_direct`.
- Removed stale docstring text and unused radius constants tied to the deleted Laplace sign checks.

## Validation

- `git diff --check` PASS.
- Remote targeted pytest PASS: `python -m pytest twophase/tests/test_simulation.py twophase/tests/test_gfm.py -v --tb=short` (`9 passed in 0.20s`).
- Note: `make test PYTEST_ARGS='-k ...'` could not preserve the quoted expression through `remote.sh test`; it failed before collection with `file or directory not found: or`. Direct remote targeted pytest is the acceptance signal for this unit.

## SOLID-X

- [SOLID-X] No production code changed. The retained tests now use a production PPE family; no tested implementation was deleted.
