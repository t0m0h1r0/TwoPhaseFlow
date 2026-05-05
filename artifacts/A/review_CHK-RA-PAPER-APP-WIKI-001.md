# CHK-RA-PAPER-APP-WIKI-001 — Paper/Appendix Wiki Compile

Date: 2026-05-05
Worktree: `.claude/worktrees/ra-wiki-curation-20260505`
Branch: `ra-paper-appendix-wiki-20260505`

## Scope

User request: extract reusable insights from paper chapters 1--13 and
appendices, compile them into `docs/wiki`, and repeat until no new insight is
found or the process exceeds 20 rounds.

This pass compared `paper/sections/01*.tex` through `13*.tex` and
`paper/sections/appendix_*.tex` against the active wiki retrieval gate
`WIKI-X-041` and the current `docs/wiki/INDEX.md`.

## Rounds

| Round | Result | Wiki output |
|---|---|---|
| 1 | Chapter 1 failure taxonomy is a reusable routing map from symptoms to numerical contracts. | `docs/wiki/cross-domain/WIKI-X-042.md` |
| 2 | Chapter 2 Eikonal rigidity needs a separate topology carrier reading. | `docs/wiki/theory/WIKI-T-144.md` |
| 3 | Chapter 2 Young--Laplace sign convention is a global jump contract. | `docs/wiki/theory/WIKI-T-145.md` |
| 4 | Chapters 2/8 balanced-force failure modes are five distinct discrete mismatches. | `docs/wiki/theory/WIKI-T-146.md` |
| 5 | Chapter 7 IMEX-BDF2 startup is a projected-state consistency contract. | `docs/wiki/theory/WIKI-T-147.md` |
| 6 | Appendix F bootstrap reinitialization is pre-consistency, not an HFE proof. | `docs/wiki/theory/WIKI-T-148.md` |
| 7 | Appendix C periodic CCD must use interior wraparound rows everywhere. | `docs/wiki/theory/WIKI-T-149.md` |
| 8 | Chapters 1--13 should be retrieved as failure-mode to contract traceability. | `docs/wiki/paper/WIKI-P-015.md` |
| 9 | Appendices are proof layers for main-text contracts. | `docs/wiki/paper/WIKI-P-016.md` |
| 10 | Targeted rescan found remaining candidates already covered by existing cards or by the new cards above. Stop condition reached before round 20. | no new card |

## Index Updates

- `docs/wiki/INDEX.md`: total `317 -> 326`.
- Theory: `143 -> 149`.
- Cross-Domain: `41 -> 42`.
- Paper: `14 -> 16`.
- Corrected stale index title for `WIKI-L-009` from 5 abstractions to 6
  abstractions, matching the card body.

## No-New-Insight Stop Rationale

The final targeted scan focused on paper/appendix warning, principle, contract,
failure, Eikonal, Young--Laplace, balanced-force, BDF2, bootstrap, and periodic
CCD signatures.  The remaining hits mapped to existing active cards such as
`WIKI-T-009`, `WIKI-T-101`, `WIKI-T-124`, `WIKI-T-125`, `WIKI-T-126`,
`WIKI-T-132`, `WIKI-T-133`, `WIKI-X-039`, `WIKI-X-041`, `WIKI-P-014`, and
experiment cards `WIKI-E-050`--`WIKI-E-054`, or to the newly added cards in
this CHK.

Verdict: stop at round 10 because no additional wiki-worthy, non-duplicate
insight remained in the requested scope.

## Validation

- `git diff --check`: PASS before the wiki-card commit.
- Targeted index scan verified the new IDs and counts.
- Targeted paper/appendix rescan performed for stop-condition evidence.

## Commits

- `52212c7e` — `docs: start RA paper appendix wiki compile`
- `0c1db7da` — `docs: compile paper appendix wiki insights`
