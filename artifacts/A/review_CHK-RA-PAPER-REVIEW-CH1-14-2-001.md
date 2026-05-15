# CHK-RA-PAPER-REVIEW-CH1-14-2-001 Review Record

## Scope

- Paper Chapters 1--13.
- Chapter 14 through Section 14.2: common benchmark policy and capillary wave.
- Chapter 14 Sections 14.3 onward were read only as local connection context when needed; no claims from those later sections are part of this review verdict.

## Review Method

Each unit was reviewed as a paper reviewer for narrative, structure, logic, terminology, freshness of research content, and equation/text/figure alignment. Units with material findings were revised and re-reviewed. No unit reached the 20-round cap.

## Findings And Fixes

| Severity | Unit | Finding | Resolution |
|---|---|---|---|
| MAJOR | Ch12 U12 / Ch13 V11 / Ch14.1--14.2 | The active-geometry capillary path was explained with process-history and implementation-facing words such as old/new path, GPU packet, fail-close, split-pending, production-stack, and solver option. This made the paper read like a development log instead of a stable research claim. | Reframed the story as accepted boundary conditions, rejected over-projection, undefined-split rejection, pressure-history separation, graph-HFE jump, regular-stratum guard, and capillary benchmark evidence. |
| MAJOR | Ch14.1--14.2 | The common benchmark policy and capillary-wave setup mixed English operational terms into the narrative: pressure projection shared face locus, step rebuild, profile restoration, solve/corrector, run, snapshot, and mode labels. | Rewrote visible prose into Japanese paper terms: common numerical configuration, shared face position, grid rebuild at each time stage, profile restoration, solve form/correction stage, computation, and snapshot diagnostics. |
| MINOR | Ch9 / Ch11 / Ch12 / Ch13 | Several paper-facing terms used "standard" claims through implementation-style wording such as production path, contract, CPU/GPU fallback, YAML lineage, and graph-HFE jump/history in English. | Replaced with standard closure, state-space condition, hidden alternative route, standard configuration, graph HFE jump, pressure-history coordinate, and acceptance boundary. |
| MINOR | Ch1 roadmap | The active-geometry flow caption used "contract pass" and Hodge wording in a way that was heavier than the introductory role of the figure. | Reworded it as an adoption-condition boundary and made the Hodge phrase explanatory rather than slogan-like. |

## Review Rounds

| Unit | Rounds | Result |
|---|---:|---|
| Chapter 1: introduction and roadmap | 2 | PASS, no MAJOR-or-higher remaining |
| Chapter 2: governing equations and surface tension | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 3: CLS and interface mapping | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 4: CCD operator family | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 5: CLS reinitialization | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 6: per-term spatial discretization | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 7: time integration | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 8: pressure-velocity coupling | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 9: PPE / HFE / DC / pressure summary | 2 | PASS, no MAJOR-or-higher remaining |
| Chapter 10: interface-fitted nonuniform grid | 1 | PASS, no MAJOR-or-higher remaining |
| Chapter 11: integrated update and active-geometry state space | 2 | PASS, no MAJOR-or-higher remaining |
| Chapter 12: component verification U1--U12 | 2 | PASS, no MAJOR-or-higher remaining |
| Chapter 13: integrated verification V1--V11 | 2 | PASS, no MAJOR-or-higher remaining |
| Chapter 14.1--14.2: benchmark policy and capillary wave | 3 | PASS, no MAJOR-or-higher remaining |
| Part-level pass: methods, verification, benchmark bridge | 2 | PASS, no MAJOR-or-higher remaining |
| Full target-scope pass | 2 | PASS, no MAJOR-or-higher remaining |

## Validation

- `git diff --check` PASS.
- P1 math heading/caption scan PASS: no section/subsection/caption math without `texorpdfstring`.
- Target visible-term scans PASS for the corrected history/implementation terms in Chapters 1--13 and Chapter 14 through Section 14.2.
- TODO/placeholder scan PASS; remaining "未定義" hits are explanatory pressure-display text, not incomplete work.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS.
- Final `paper/main.log` diagnostic scan PASS: no LaTeX warnings, package warnings, overfull/underfull boxes, missing glyphs, undefined control sequences, emergency stops, or fatal errors.

## Commits Before Final Bookkeeping

- `eb2c8ac8` chore(paper-review): start ch1-14.2 review worktree
- `84b8840e` paper(active-geometry): clarify review-gate terminology
- `3a953edb` paper(ch14): polish capillary benchmark wording

## Verdict

MAJOR-or-higher findings are resolved for the target scope. Main has not been merged.
