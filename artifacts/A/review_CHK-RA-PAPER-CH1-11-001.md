# Review CHK-RA-PAPER-CH1-11-001

Session: `CHK-RA-PAPER-CH1-11-001`
Agent: ResearchArchitect
Branch/worktree: `codex/ra-paper-review-ch1-11-20260509` at `/private/tmp/TwoPhaseFlow-ra-paper-review-ch1-11-20260509`
Scope: Chapters 1--11, `paper/sections/01*.tex`--`paper/sections/11*.tex`

## Verdict

PASS AFTER FIX. Chapters 1--11 were reviewed as a strict paper narrative rather
than as an implementation log. No BLOCKER or MAJOR finding remains in the
target scope. The front half now presents the current research endpoint as the
centerline: continuous two-phase formulation, CLS transport and reinitialization,
compact spatial operators, per-variable spatial/temporal choices, pressure-jump
closure, nonuniform-grid constraints, and the integrated Chapter 11 algorithm.

## Review Units And Rounds

| Unit | Rounds | Final MAJOR+ status |
|---|---:|---|
| Chapter 1: Introduction and roadmap | 3 | none |
| Chapter 2: Governing equations and nondimensionalization | 2 | none |
| Chapter 3: Level set, CLS, Ridge--Eikonal | 2 | none |
| Chapter 4: CCD/DCCD/UCCD6/FCCD operators | 2 | none |
| Chapter 5: Reinitialization and CLS stages | 2 | none |
| Chapter 6: Scheme selection, FCCD advection, viscosity | 2 | none |
| Chapter 7: Time integration | 2 | none |
| Chapter 8: Collocated pressure and Balanced--Force | 2 | none |
| Chapter 9: Split PPE, HFE, DC, pressure summary | 2 | none |
| Chapter 10: Grid and nonuniform extensions | 2 | none |
| Chapter 11: Full algorithm and pure FCCD DNS | 3 | none |
| Part I bridge, Chapters 1--3 | 2 | none |
| Part II bridge, Chapters 4--11 | 2 | none |
| Whole target, Chapters 1--11 | 2 | none |

No unit reached the 20-round stop condition.

## Findings And Fixes

### RA-PAPER-CH1-11-001-01: Latest standard path was blurred by older branch language

Finding: The target range still exposed several older descriptions as if they
were the current paper path: fixed `DC k=3` wording, common-flux transport as a
late experiment detail, and velocity-primary convection described too close to
the conservative common-flux route.

Fix: Re-centered Chapters 1, 6, 7, 9, and 11 on the current distinction:
velocity-primary EXT2/IMEX--BDF2 remains a valid path, while the conservative
common-flux path updates `q`, `m`, and `p_m` from the same face-flux ledger and
accepts DC by residual convergence rather than by a fixed iteration count.

### RA-PAPER-CH1-11-001-02: Reviewer-facing process terms leaked into the paper

Finding: Terms such as `primitive`, `fail-close`, `checkpoint`, `production`,
`fallback`, `damping`, `clipping`, `donor`, and English-heavy labels made parts
of the exposition read like internal engineering history rather than a paper.

Fix: Rewrote visible text into paper-facing Japanese: velocity-primary variable,
保存形共通フラックス, 適用不可条件, 再開状態, 一流体対照経路, 安定化調整パラメータ,
非物理振動, 計算破綻, and 受理条件. The final visible checkpoint occurrence in
Chapter 11 was changed to `保存形再開状態`.

### RA-PAPER-CH1-11-001-03: Chapter-to-chapter logic needed a clearer spine

Finding: The first 11 chapters had the correct pieces, but a reader could still
lose the reason for the order: why CLS precedes operator design, why pressure
jumps are separated from one-fluid CSF/BF controls, and why Chapter 11 requires
restart-state closure.

Fix: Tightened the roadmap and local transitions so the sequence is now:
problem difficulty -> continuous variables -> CLS transport/reinitialization ->
operator placement -> per-variable discretization -> time/pressure closure ->
grid constraints -> integrated state update. Chapter 11 now closes with the
same state variables introduced in the earlier chapters.

### RA-PAPER-CH1-11-001-04: Terminology and notation were inconsistent across units

Finding: Chapter-local edits left visible variation in translated terms and
some source-visible labels/comment names. The main risk was not syntax but a
reviewer seeing multiple names for the same contract.

Fix: Normalized visible terminology in Chapters 1--11. Source labels that are
not visible in the PDF were left only where changing them would add needless
reference churn; the final targeted visible-text scan confirms the user-named
independent English terms are absent from the paper text.

## Whole-Scope Re-review

The final Chapter 1--11 pass found no remaining MAJOR issue. Residual terms such
as 履歴 are used as mathematical time-history/pressure-history quantities, not as
implementation history. Terms such as 完全テンソル版 and 一様格子版 denote
mathematical variants, not old-version narrative. TeX comments and labels were
not treated as paper-body findings unless they affected visible text.

## Validation

- `git diff --check` PASS.
- Targeted visible-text stale/jargon scan PASS:
  `projection-native`, `face-space`, `primitive velocity`, `fail-close`,
  `fallback`, `production`, `checkpoint`, `チェックポイント`, `common flux`,
  `scalar PPE`, `divergence-equivalent`, `divergence-free`, `damping`,
  `clipping`, `curvature cap`, fixed `DC k`, `Predictor`, and `donor` did not
  occur in visible Chapter 1--11 lines.
- `make -B -C paper` PASS; regenerated `paper/main.pdf`, 256 pages.
- Final log scan
  `rg -n "^(LaTeX Warning|Package .*Warning|Class .*Warning|Overfull|Underfull|! |.*Error|Fatal|Undefined control sequence|LaTeX Error)" paper/main.log`
  returned no matches.

## Commits

- `7e1eb6fb chore(ra): start chapter 1-11 paper review`
- `71d3bca8 paper(ch1-11): align terminology with latest standard path`
- `752ef85a paper(ch1-11): remove reviewer-facing process jargon`
- `f44dc6f1 paper(ch1-7): polish narrative vocabulary`
- `ff1e15f1 paper(ch8-11): clarify closing terminology`

## SOLID-X

Paper/docs-only change. No production solver source, experiment script/config,
experiment result, tested implementation, FD/WENO/PPE fallback, damping/CFL
workaround, smoothing, curvature cap, benchmark branch, blanket projection, or
QP-as-physics path was introduced.
