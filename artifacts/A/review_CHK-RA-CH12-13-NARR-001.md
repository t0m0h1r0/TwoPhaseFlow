# Review CHK-RA-CH12-13-NARR-001

Session: `CHK-RA-CH12-13-NARR-001`
Agent: ResearchArchitect
Branch: `ra-ch12-13-narrative-review-20260503`
Lock: `docs/locks/ra-ch12-13-narrative-review-20260503.lock.json`
Scope: `paper/sections/12*.tex`, `paper/sections/13*.tex`

## Verdict

PASS AFTER FIX. Chapters 12--13 now present the U-series component verification
and V-series integration verification with a consistent reviewer-facing
narrative: primitive evidence in Chapter 12 is explicitly bridged to the
integrated physics diagnostics in Chapter 13, and the two master accuracy
tables use the same column grammar.

## Findings And Fixes

### RA-CH12-13-NARR-001: Chapter 12 to 13 bridge was stale

Finding: The Chapter 12 closing bridge mapped time splitting to Taylor--Green
energy decay and nonuniform-grid verification to "interface-crossing CLS
advection", which no longer matches the current Chapter 13 roles. V7 is the
coupled-stack time diagnostic, V8/V9 cover fixed nonuniform NS/local-thickness
diagnostics, and V10 is explicitly uniform-grid CLS-only advection.

Fix: Replaced the loose bullet bridge with `tab:U_to_V_bridge`, which maps each
unverified coupling effect to the current V tests: standard PPE time/velocity
coupling, BF pressure-interface balance, high-density-ratio pressure-jump stack,
nonuniform/local-thickness diagnostics, and CLS conservative advection.

### RA-CH12-13-NARR-002: Master tables used different reading grammars

Finding: Chapter 12's master summary used `ID / test / expected / measured /
verdict`, while Chapter 13 embedded verdicts inside the observation column and
kept design order in the final column. This made the common comparison tables
feel unrelated and forced the reader to relearn the table grammar.

Fix: Rebuilt `tab:v_accuracy_summary` to match Chapter 12's grammar:
`ID / テスト / 期待・判定基準 / 実測・観測値 / 判定`. The V10 mass/shape axes
remain split, but their verdicts now sit in the same explicit判定 column as the
U-series table.

### RA-CH12-13-NARR-003: V9 was hidden as an implicit fourth category

Finding: V9's §14 stack switch diagnostic was described in a caption as an
implicit fourth category, while `tab:V_verdict_types` only listed Type-A/B/D.
That invited a reviewer to read V9 as an ad hoc exception.

Fix: Added a named `§14 stack 診断` row to `tab:V_verdict_types` and propagated
the same wording to V9 and the Chapter 13 accuracy summary. V9 is now explicitly
a no-regression switch diagnostic, not an unlabelled Type-A/B/D exception and
not evidence that local epsilon improves this reduced probe.

### RA-CH12-13-NARR-004: Notation drift across Chapters 12--13

Finding: Chapter 12/13 text mixed bare `\nabla`, `\kappa`, `\hat{n}`,
`\mathbf{u}`, and `\epsilon` with the established paper notation
`\bnabla`, `\kappa_{lg}`, `\hat{\bm n}_{lg}`, `\bm{u}`, and `\varepsilon`.

Fix: Normalized the affected Chapter 12--13 prose and captions around BF
coupling, DCCD pressure prohibition, Kovasznay residuals, static-droplet CSF
curvature, V7 initial conditions, V8/V9 nonuniform diagnostics, and the Chapter
13 error budget.

## Validation

- `git diff --check` PASS.
- Targeted stale-expression scan PASS for removed bridge/category/notation
  strings.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS
  in `paper/`; output `main.pdf`, 242 pages.
- Remaining log note observed: pre-existing underfull hbox in
  `sections/09f_pressure_summary.tex:57`; unrelated to this CHK.

## SOLID-X

Paper/audit-only change. No production code boundary changed, no tested code
deleted, no FD/WENO/PPE fallback introduced, and no experiment data or figures
were modified.
