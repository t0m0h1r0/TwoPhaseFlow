# CHK-RA-WIKI-REVIEW-RECUR-001 — Recursive Wiki Curation Review

Date: 2026-05-05
Worktree: `.claude/worktrees/ra-wiki-review-recur-20260505`
Branch: `ra-wiki-review-recur-20260505`
Base: `ra-memo-artifact-wiki-20260505`

## Scope

User request: review `docs/wiki`, eliminate stale or known-wrong information
from active retrieval, reorganize retained information, and repeat until no
further review is needed or the process exceeds 10 rounds.

This pass preserved historical/negative evidence but removed it from active
policy by changing status to `SUPERSEDED` or `REFERENCE`, adding curation
notes, and routing readers through `WIKI-X-041`.

## Rounds

| Round | Result | Commit |
|---|---|---|
| 1 | Start bookkeeping and lock for the recursive wiki review. | `f75da648` |
| 2 | Retired stale algorithm/solver maps: old 7-step loop, DCCD mode map, DC+LU architecture, FFT divergence criterion, ten-method role map, ADI jump-decomposition proposal, early paper problem/verification maps, and old AB2/CN/ST proposal. | `2a9e089c` |
| 3 | Demoted stale paper/CFL snapshots and bounded the CCD-LU policy: CFL constants became reference evidence, old paper reviews became provenance, and `WIKI-X-009` now keeps only the ch11-only CCD-LU restriction active. | `d2b0fa90` |
| 4 | Superseded the previous ResearchArchitect atlas `WIKI-X-037` in favor of the current active retrieval gate `WIKI-X-041`; repaired related BF/time-verification references. | `214b9260` |
| 5 | Demoted stale code maps whose file paths or package boundaries predated the current source layout. | `3924c9ea` |
| 6 | Bounded remaining historical code snapshots: old SOLID score and CN strategy moved to reference; GPU/grid-remap cards now point to current backend/code maps. | `0060ee8a` |
| 7 | Targeted rescan found no further active-policy issue requiring edits before round 10. | no new commit |

## Actions

Status demotions:

- `SUPERSEDED`: `WIKI-L-001`, `WIKI-X-005`, `WIKI-X-022`, `WIKI-P-003`,
  `WIKI-P-005`.
- `REFERENCE`: `WIKI-X-001`, `WIKI-X-007`, `WIKI-X-011`, `WIKI-X-025`,
  `WIKI-X-037`, `WIKI-L-008`, `WIKI-L-013`, `WIKI-L-014`, `WIKI-L-015`,
  `WIKI-L-016`, `WIKI-L-022`, `WIKI-L-028`, `WIKI-P-001`, `WIKI-P-002`,
  `WIKI-P-004`, `WIKI-P-006`.

Bounded active cards:

- `WIKI-X-009`: CCD Kronecker+LU ch11-only restriction remains active; old
  solver list and retired verification hierarchy are historical.
- `WIKI-X-029`: BF operator-location/adjointness principles remain active;
  DCCD/Rhie-Chow material is bounded as guardrail/history.
- `WIKI-E-005`: isolated time-integrator component results remain active, but
  no longer imply the retired 7-step loop.
- `WIKI-L-017` and `WIKI-L-018`: retained as implementation evidence with
  current backend/code-map dependencies.

Reorganization:

- `WIKI-X-041` retired-knowledge table now includes the newly demoted cards.
- `docs/wiki/INDEX.md` keeps the same total count (`338`) but marks demoted
  entries with `[SUPERSEDED]` or `[REFERENCE]` in the title column.

## Stop Rationale

The final targeted scans covered:

- retired-card references from active cards;
- stale implementation terms: `WENO5`, `DCCD`, `Rhie`, `ADI`, `FFT`,
  `CCD-LU`, `CN`, `Approach B`, `FD Hessian`, `7-step`, and old `pressure/`
  paths;
- wiki inventory count and active retrieval gate.

Remaining hits are intentionally retained in one of these categories:

- active curation/gate cards that describe retired knowledge;
- component theory or experiment cards where the old term is the object being
  tested, not the current full-stack route;
- already curated cards such as `WIKI-X-031` and `WIKI-T-065`;
- reference/superseded provenance cards.

Verdict: stop at round 7, before the round-10 cap, because no remaining hit
required another active-policy correction.

## Validation

- `git diff --check`: PASS after each edit batch.
- Wiki inventory remains `338` files, matching `docs/wiki/INDEX.md`.
- Targeted curation scans completed for stale terms and retired-card links.

## SOLID-X

Docs/wiki/artifact/ledger only.  No production code boundary changed, no tested
code deleted, and no FD/WENO/PPE fallback introduced.
