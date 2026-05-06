# CHK-RA-SRC-MAJOR-ROUNDS-002 — Source Scheme Major Review

Date: 2026-05-06

Scope: targeted strict review of `src/twophase/` numerical scheme paths after the GPU-first and no-unsolicited-fallback audits.

## User Trigger

User requested a strict `src/` code review, root-cause fixes for all findings, and repeated rounds until no MAJOR-or-higher findings remain or the review exceeds 10 rounds.

## Verdict

MAJOR fixed. Stop condition reached at Round 6: targeted rescans found no active MAJOR-or-higher issue in the audited paths.

## Rounds

- Round 1 MAJOR fixed: `ccd/block_tridiag.py` silently substituted a pseudo-inverse when a 2x2 block pivot was singular and clamped near-zero determinants in the batched solve. The block Thomas path now validates pivots and fails closed with `LinAlgError`; pseudo-inverse and determinant clamp fallbacks are prohibited.
- Round 2 MAJOR fixed: direct import of `simulation/velocity_reprojector_iim.py` re-registered retired `iim` / `consistent_iim` reprojector modes through `SchemeRegistryMixin`. The class is now direct-import reference only and does not mutate the public registry.
- Round 3 MAJOR fixed: `levelset/field_extender.py` replaced non-finite source-phase physical data with zero before extension. Source-phase non-finite data now raises `ValueError`; zero replacement remains limited to target-phase placeholders.
- Round 4 MAJOR fixed: `ppe/defect_correction.py` rejected same-operator defect correction only for one affine-jump case. The DC contract now rejects same high/base operators generally, and the dormant collapse branch fails closed if reached.
- Round 5 rescan: no additional MAJOR+ active issue. Remaining matches were fail-closed diagnostics, explicit C2 reference code, runtime/reporting host boundaries, or non-substitution numerical initialization.
- Round 6 rescan: no additional MAJOR+ active issue in fallback/registry/same-operator patterns. Remaining hits were tests, explicit rejection messages, or reference-only terminology.

## Tests

- Targeted tests after fixes: `31 passed`.
- Full local CPU suite with workspace venv: `574 passed, 32 skipped`.
- `make test` was attempted first per remote-first policy; remote was unavailable and the Makefile local fallback failed because `python` is not on PATH in this worktree. The same suite passed with `/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m pytest`.
- `git diff --check` passed.

## SOLID

[SOLID-X] No C1 violation found. Fixes tighten existing scheme contracts rather than adding alternate calculation schemes. No tested implementation was deleted; obsolete public routes remain excluded from active construction.
