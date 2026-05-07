# CHK-RA-PAPER-REVIEW-CH1-13-001

## Scope
- Review target: paper Chapters 1--13.
- Branch/worktree: `codex/ra-paper-review-ch1-13-20260508` /
  `.claude/worktrees/codex-ra-paper-review-ch1-13-20260508`.
- Mode: ResearchArchitect FULL-PIPELINE, writing-domain prose patch.
- Main merge: not performed.

## Review Units And Rounds

| Unit | Rounds | MAJOR+ status | Notes |
|---|---:|---|---|
| Chapter 1 | 1 | None remaining | Narrative starts from common face-discrete structure and separates CSF contrast path from pressure-jump path. |
| Chapter 2 | 1 | None remaining | Continuous assumptions, sign conventions, CSF/pressure-jump relationship are explicit. |
| Chapter 3 | 1 | None remaining | CLS chapter answers why CLS is needed before algorithmic detail. |
| Chapter 4 | 1 | None remaining | CCD family roles are separated by evaluation location and consumer chapters. |
| Chapter 5 | 1 | None remaining | Reinitialization is framed as auxiliary geometry reconstruction, not physical transport. |
| Chapter 6 | 1 | None remaining | Variable-by-variable operator assignment is clear and avoids universal-CCD overclaim. |
| Chapter 7 | 1 | None remaining | Time-integration narrative separates causal update order from closure-dependency order. |
| Chapter 8 | 1 | None remaining | Projection, collocation failure, BF requirements, and FCCD face subsystem are logically staged. |
| Chapter 9 | 1 | None remaining | PPE chapter states the seven closure problems before implementation details. |
| Chapter 10 | 1 | None remaining | Nonuniform-grid scope is bounded to fixed-grid/static diagnostics and closure conditions. |
| Chapter 11 | 1 | None remaining | Full algorithm chapter is a map from Part II primitives to verification chapters, not a new-claim chapter. |
| Chapter 12 | 2 | None remaining | Round 1 MAJOR terminology/bridge issue fixed; Round 2 no MAJOR. |
| Chapter 13 | 2 | None remaining | Round 1 MAJOR terminology/verdict readability issue fixed; Round 2 no MAJOR. |
| Part I (Ch.1--3) | 1 | None remaining | Governing equations and CLS motivation connect naturally. |
| Part II (Ch.4--11) | 1 | None remaining | Operator chapters now read as dependencies feeding the 7-step algorithm. |
| Part III opening (Ch.12--13) | 2 | None remaining | Component/integration boundary and V-series verdict vocabulary aligned. |
| Full range (Ch.1--13) | 2 | None remaining | Round 2 scan found no visible `projection-native`, `range-projected ... stack`, or `face-space contract` wording in rendered prose. |

No unit reached the 20-round cap.

## Findings And Fixes

### F1 [MAJOR] Internal implementation jargon obscured Chapter 13 verdicts
Round 1 found reader-facing terms such as `projection-native face closure`,
`range-projected pressure-jump stack`, `operator-stack`, `coupled-stack`,
`production stack`, and `pressure-adjoint residual contract` in the Chapter 13
entry, V6/V7/V9 explanations, and accuracy budget. These terms forced readers
to decode implementation nicknames before understanding what was actually
verified.

Fix: replaced them in rendered prose with a stable Japanese vocabulary:
`圧力ジャンプ・毛管射影結合系`, `毛管成分の圧力勾配射影`,
`射影後面速度閉包`, `アフィン圧力履歴面加速度`, `演算子群条件付き診断`,
and `本番構成の静止液滴判定`. Equation labels and figure file names were
left intact for reference compatibility.

### F2 [MAJOR] Chapter 12 to Chapter 13 bridge still read like a change log of stack names
Round 1 found the Chapter 12 boundary table and summary described the next
chapter using English stack nicknames rather than the research question:
which single-component claims are re-tested as coupled physical behavior.

Fix: rewrote the bridge rows so Chapter 12 says precisely which component
primitive is handed to which Chapter 13 integrated diagnostic, using the same
Japanese vocabulary as Chapter 13.

### F3 [MINOR] Production static droplet placement used pipeline words rather than paper words
Round 1 found `production static gate` / `production stack` phrasing in V3 and
the master accuracy table. This made the section sound like implementation
history rather than a paper claim.

Fix: reframed it as `本番構成の静止液滴判定` and `圧力ジャンプ/Riesz 本番構成`.

## Files Changed
- `docs/locks/codex-ra-paper-review-ch1-13-20260508.lock.json`
- `paper/sections/12_component_verification.tex`
- `paper/sections/12h_summary.tex`
- `paper/sections/12u2_ccd_poisson_ppe_bc.tex`
- `paper/sections/12u6_split_ppe_dc_hfe.tex`
- `paper/sections/12u7_bf_static_droplet.tex`
- `paper/sections/13_verification.tex`
- `paper/sections/13b_twophase_static.tex`
- `paper/sections/13d_density_ratio.tex`
- `paper/sections/13e_nonuniform_ns.tex`
- `paper/sections/13f_error_budget.tex`
- `artifacts/A/review_CHK-RA-PAPER-REVIEW-CH1-13-001.md`

## Validation
- `git diff --check` PASS.
- Targeted jargon scan PASS: no rendered-prose matches for
  `projection-native`, `face-space`, `range-projected`,
  `capillary range projection`, `pressure-adjoint residual contract`,
  `operator-stack`, `coupled-stack`, `production stack`,
  `pressure-jump stack`, or `production static gate` in Chapters 1--13.
- Historical/trial-process scan PASS: the only remaining `古い` hit is
  the legitimate mathematical phrase `古い格子` in Chapter 10, not
  old-version prose.
- `make -B -C paper` PASS: `paper/main.pdf` rebuilt successfully
  (253 pages).
- Log scan PASS: no fatal errors, LaTeX errors, undefined references, or
  multiply-defined-reference diagnostics. The only overfull hit remains the
  existing unchanged `paper/sections/04f_face_jet.tex:134--144` paragraph.

## SOLID-X
Paper/docs/artifact-only review patch. No solver source, experiment script,
configuration, or checked-in result behavior changed. No tested implementation
was deleted. No FD/WENO/PPE fallback, damping/CFL workaround, smoothing,
curvature cap, benchmark-name branch, blanket projection, or QP-as-physics path
was introduced.
