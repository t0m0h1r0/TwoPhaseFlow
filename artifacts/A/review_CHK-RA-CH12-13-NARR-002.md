# Review CHK-RA-CH12-13-NARR-002

Session: `CHK-RA-CH12-13-NARR-002`
Agent: ResearchArchitect
Branch: `ra-ch12-13-narrative-review-20260503`
Base: post-merge `main` at `75ee5f16`
Scope: `paper/sections/12*.tex`, `paper/sections/13*.tex`

## Verdict

PASS AFTER FIX. The post-merge rereview found no numerical or algorithmic
claim change required, but did find reviewer-facing consistency defects that
would weaken the narrative: the Chapter 12 overview/summary tables still used
slightly different grammars from the Chapter 13 accuracy table, the Chapter 13
overview table did not expose verdicts, and the smoothing-width notation still
mixed `\eps` with `\varepsilon`. These were fixed at the table/narrative layer
rather than patched locally one row at a time.

## Findings And Fixes

### RA-CH12-13-NARR-002-01: U master tables still had divergent column grammar

Finding: `tab:U_summary` and `tab:verification_summary` were both U-series
master tables, but their headers and caption notes used different language
(`期待精度 / 実測値` vs. `期待精度 / 実測精度`) while Chapter 13's master
accuracy table used `期待・判定基準 / 実測・観測値`. This made the common
comparison tables look related by content but not by reading protocol.

Fix: Normalized the Chapter 12 master table grammar to the same reviewer-facing
protocol used by Chapter 13:
`ID / テスト / 期待・判定基準 / 実測・観測値 / 判定`. Added cross-table caption
notes so the U-number order table, Tier-order table, and V accuracy table are
read as the same table family.

### RA-CH12-13-NARR-002-02: V overview omitted the verdict axis

Finding: `tab:V_summary` listed the test target, figures, and major metrics,
but omitted the verdict column. Readers had to jump to `tab:v_accuracy_summary`
to see whether a row was design-pass, Type-A, Type-B, Type-D, or stack
diagnostic. This fractured the Chapter 13 narrative because the overview table
did not carry the same judgment vocabulary as the accuracy table.

Fix: Rebuilt `tab:V_summary` as a five-column `tabularx` table with an explicit
`判定` column. V1--V9 now use the same labels as the accuracy summary, and
V10-a/V10-b show their mass/shape two-axis verdicts in-place.

### RA-CH12-13-NARR-002-03: Smoothing-width notation remained split

Finding: Chapter 12 still used `\eps`, `H_\eps`, `\delta_\eps`, and
`\eps_{\eff}` in U3--U5 and the Chapter 12 summary, while the surrounding
Chapter 12--13 narrative had moved to `\varepsilon`. This was not merely a
cosmetic typo: it made the same smoothing-width concept look like two symbols.

Fix: Normalized the affected Chapter 12 occurrences to `\varepsilon`,
`H_\varepsilon`, `\delta_\varepsilon`, and `\varepsilon_{\eff}`. The scan now
has no remaining `\eps` / `\epsilon` notation in Chapter 12--13 prose.

### RA-CH12-13-NARR-002-04: Minor narrative polish defects remained

Finding: The V settings caption contained `を 補足列` with an unintended
space, and `13f_error_budget.tex` placed a `\paragraph` immediately after an
`itemize` environment without a separating blank line. These are small, but
they are exactly the kind of paper-surface inconsistency a strict reviewer
notices after the larger structure is fixed.

Fix: Removed the caption spacing defect and restored the paragraph separation
after the verdict-summary itemize block.

## Validation

- `git diff --check` PASS.
- Targeted notation scan PASS:
  `\epsilon`, `\eps`, bare `\kappa`, `\hat{n}`, `\mathbf{u}`, `\nabla p`,
  `\nabla H`, and bare `\nabla\cdot` absent from Chapter 12--13 targets.
- Targeted stale wording scan PASS for stale bridge/category/table wording:
  `界面横断 CLS`, `第四カテゴリ`, `Type ラベル不在`, `default 合格`,
  `CN-ADI`, `CCD-LU`, `LGMRES`, `BiCGSTAB`, `WENO`, `を 補足列`,
  and `Master accuracy summary`.
- Targeted table grammar scan PASS for the aligned U/V master-table headers.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS
  in `paper/`; output `main.pdf`, 244 pages.
- Remaining log note observed: pre-existing underfull hbox in
  `sections/09f_pressure_summary.tex:57`; unrelated to this CHK.

## SOLID-X

Paper/audit-only change. No production code boundary changed, no tested code
deleted, no FD/WENO/PPE fallback introduced, and no experiment data or figures
were modified.
