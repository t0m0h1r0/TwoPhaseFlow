# CHK-RA-PAPER-COVER-CH1-13-001 Review Record

## Scope

- Review target: cover/title box, abstract, Chapters 1--13.
- Worktree: `.claude/worktrees/codex-ra-paper-review-cover-ch1-13-20260509`
- Branch: `codex/ra-paper-review-cover-ch1-13-20260509`
- Main merge: not performed.
- SOLID classification: `[SOLID-X]` paper/docs only. No solver source, experiment scripts/configs/results, tested implementation, FD/WENO/PPE fallback, damping/CFL workaround, smoothing, curvature cap, blanket projection, or QP-as-physics path changed.

## Review Units and Rounds

| Unit | Rounds | Result |
|---|---:|---|
| Cover/title box + abstract | 2 | MAJOR terminology/narrative issue fixed; no MAJOR+ remains |
| Chapter 1 | 1 | No MAJOR+ remains |
| Chapter 2 | 2 | Remaining internal "face-state" wording fixed; no MAJOR+ remains |
| Chapter 3 | 1 | No MAJOR+ remains; residual `admissibility` occurrences are labels/refs only |
| Chapter 4 | 1 | No MAJOR+ remains |
| Chapter 5 | 1 | No MAJOR+ remains |
| Chapter 6 | 1 | No MAJOR+ remains; legacy labels retained for references only |
| Chapter 7 | 1 | No MAJOR+ remains |
| Chapter 8 | 1 | No MAJOR+ remains |
| Chapter 9 | 3 | MAJOR terminology and logic-presentation issues fixed; no MAJOR+ remains |
| Chapter 10 | 1 | No MAJOR+ remains |
| Chapter 11 | 2 | MAJOR standard-route terminology issue fixed; no MAJOR+ remains |
| Chapter 12 | 3 | MAJOR unit-test narrative and U10/U11 integration issues fixed; no MAJOR+ remains |
| Chapter 13 | 4 | MAJOR V-series/V11 boundary, terminology, and result-table narrative issues fixed; no MAJOR+ remains |
| Part I bridge (frontmatter--Ch3) | 2 | Motivation -> governing equations -> interface representation remains coherent |
| Part II bridge (Ch4--Ch11) | 2 | Operator construction -> pressure/capillary closure -> full algorithm vocabulary aligned |
| Part III bridge (Ch12--Ch13) | 3 | Unit verification -> integrated verification boundary aligned |
| Whole target pass | 2 | No MAJOR+ remains; no unit reached 20 rounds |

## Main Findings and Fixes

- MAJOR: cover/abstract still described the current result with implementation-history words such as "range-projected", "coupled stack", "production stack", and "face footprint". Rewrote these as paper-facing claims about pressure-jump phase-separated PPE, capillary projection, shared face stencil, and standard route.
- MAJOR: Chapter 12 framed U tests as "primitives", "gates", and pass/fail plumbing, which obscured the Equation -> Discretization -> Code evidence chain. Reframed the chapter as single-component verification of numerical elements and aligned U10/U11 with the same summary grammar as Chapter 13.
- MAJOR: Chapter 13 mixed integrated verification with development-route terms around V11/preflight/admissibility and with English labels such as fixed-grid, benchmark/preflight, standard PPE, identity, design criterion, and uniform-offset. Reframed V1--V10 as the Chapter 13 scope and moved finite-amplitude periodic-wall rising-bubble checks to Chapter 14.
- MAJOR: Chapter 9/11 pressure/capillary closure prose still used internal route terms: active pressure metric, face-state, diagnostic gate, full-space pressure projection, wall-only repair, and production fix. Rewrote them as pressure metric, 面速度状態, 診断条件, 全自由度圧力射影, 壁面だけの修復, and 標準補正.
- MINOR: Chapter 12 summary table exceeded page height by 0.19278pt after wording changes. Reduced table row stretch from 0.82 to 0.81 and rebuilt the PDF with a clean log.
- MINOR: several result table labels in Chapter 13 used English shorthand (`mass`, `shape`, `centroid err`, `reversal err`, `uniform-offset`, `$rho_r$/op`). Replaced with Japanese table terms while preserving IDs and figure references.

## Validation

- `git diff --check` passed.
- `make -C paper` passed and rebuilt `paper/main.pdf` (262 pages).
- Final paper log scan returned no matches:
  `rg -n "^(LaTeX Warning|Package .*Warning|Class .*Warning|Overfull|Underfull|! |.*Error|Fatal|Undefined control sequence|LaTeX Error|Float too large)" paper/main.log`
- Target terminology scan across cover/abstract and Chapters 1--13 returned only label/reference names:
  `sec:ridge_admissibility` in Chapter 3. No visible MAJOR internal terms remain.

## Residual Notes

- No BLOCKER or MAJOR findings remain.
- No review unit reached 20 rounds.
- Labels and figure filenames containing legacy English fragments were not renamed when they serve cross-reference or artifact compatibility and do not appear as visible narrative claims.
