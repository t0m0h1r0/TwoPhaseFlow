# CHK-RA-WIKI-PAPER-CODE-001 — Wiki / Paper / Code Curation Review

Date: 2026-05-16
Branch: `codex/ra-wiki-paper-code-review-20260516`
Worktree: `.claude/worktrees/codex-ra-wiki-paper-code-review-20260516`

## Scope

User request: review all wiki information for stale/update/split/merge needs,
review the paper for wiki-worthy information, review the code for wiki-worthy
information, then apply the resulting changes.

The review was executed as a docs/wiki curation pass.  Source code was read for
contract alignment, but no `src/twophase/` behavior was changed.

## Inventory Evidence

- `docs/wiki/INDEX.md` and all wiki markdown files were inventoried: 386
  entries before edits, 387 after adding `WIKI-P-019`.
- Category review focused on the active retrieval stack:
  `WIKI-X-041`, `WIKI-X-054`, `WIKI-X-053`, `WIKI-X-052`, `WIKI-X-055`,
  `WIKI-T-168`, `WIKI-T-169`, `WIKI-T-172`, `WIKI-T-173`,
  `WIKI-E-063`, `WIKI-P-018`, `WIKI-L-009`, `WIKI-L-010`,
  `WIKI-L-045`, and reference/path outliers found by scan.
- Paper review focused on current chapter routing and the latest capillary
  result in `paper/main.tex`, `paper/sections/12u12_ao_capillary_split_gate.tex`,
  `paper/sections/13e2_ao_capillary_split_gate.tex`, and
  `paper/sections/14_benchmarks.tex`.
- Code review focused on the current PPE and capillary runtime contracts:
  `src/twophase/ppe/interfaces.py`, `src/twophase/ppe/factory.py`,
  `src/twophase/ppe/fccd_matrixfree.py`, `src/twophase/ppe/fd_direct.py`,
  `src/twophase/ppe/fvm_matrixfree.py`,
  `src/twophase/ppe/defect_correction.py`,
  `src/twophase/simulation/ns_solver_builder.py`,
  `src/twophase/simulation/ns_runtime_factories.py`,
  `src/twophase/simulation/velocity_reprojector_basic.py`,
  `src/twophase/simulation/ns_grid_rebuild.py`, and targeted tests under
  `src/twophase/tests`.

## Findings and Actions

| Finding | Action |
|---|---|
| `WIKI-E-063` still read like the early AO-Fast split gate where capillarity remained closed. | Rewrote it as the current U12/V11 active-geometry capillary split gate: old full-pressure-image cancellation is negative knowledge, while graph HFE, face bridge, moving face cochains, pressure history, regular stratum, and DC convergence form the accepted gate stack. |
| Paper had a new Chapter 14 capillary benchmark contract not represented in paper wiki. | Added `WIKI-P-019` with the one-period N32 capillary-wave reading, published values, figure set, and wording guardrails. |
| `WIKI-L-009` and `WIKI-L-010` described the April CCD-LU/IIM/iterative PPE stack as active. | Rewrote both cards around current runtime scheme interfaces and PPE architecture: FCCD matrix-free high-order operator, DC wrapper, FD low-order bases, and explicit FVM/FD routes. |
| Active cards still pointed to old `src/twophase/ns/*` and `src/twophase/projection/*` paths. | Updated `WIKI-X-052`, `WIKI-T-172`, and `WIKI-L-045` to `src/twophase/simulation/*`; fixed the broken `ACTIVE_LEDGER` relative link in `WIKI-X-018`. |
| `WIKI-T-169` is still useful but its old geometric-cell-fraction status/name can be misread as the current front door. | Added a 2026-05-16 curation note routing current production reading through `WIKI-X-054`, `WIKI-E-063`, and `WIKI-P-019`, and warning not to expose `geometric_cell_fraction` as the user-facing name. |
| Active retrieval did not expose the new Chapter 14 paper contract or current PPE architecture. | Updated `WIKI-X-041` and `docs/wiki/INDEX.md`; index count is now 387 entries, Paper count 19. |

## Split / Merge Decisions

- Split: Chapter 14 capillary benchmark paper knowledge belongs in new
  `WIKI-P-019`, not in `WIKI-P-018`, because `WIKI-P-018` is explicitly scoped
  to Chapters 1--13.
- Merge avoided: U12/V11 experiment knowledge remains in `WIKI-E-063`; the
  card was rewritten instead of creating `WIKI-E-064` because the ref-id is
  already the active retrieval target.
- Merge avoided: broad state-space theory remains in `WIKI-T-169`; current
  production synthesis stays in `WIKI-X-054` to avoid turning a long theory
  source into the operational retrieval gate.
- Retained as reference: old `pressure/` path mentions in `WIKI-L-015` remain
  historical because the card is already marked `REFERENCE` and contains a
  curation note pointing readers to `WIKI-L-037` / `WIKI-L-038`.

## Validation

- `git diff --check`: PASS before the wiki curation commit.
- Wiki metadata/link audit after edits:
  - entry files: 387
  - indexed entries: 387
  - missing from index: 0
  - indexed missing files: 0
  - broken relative wiki links: 0
  - active stale `src/twophase/ns|projection|pressure|interfaces` path refs:
    0, excluding historical `REFERENCE` card `WIKI-L-015`.

## Commits

- `b41ab8fe` — `chore(ledger): start wiki paper code review`
- `a7cef18e` — `wiki: refresh capillary and PPE curation`

## SOLID-X

Wiki/artifact/ledger curation only.  No `src/twophase/`, experiment YAML,
result data, physical parameter, CFL, damping, smoothing, tolerance, solver
family, fallback behavior, production algorithm, main merge, branch deletion,
or worktree removal changed.
