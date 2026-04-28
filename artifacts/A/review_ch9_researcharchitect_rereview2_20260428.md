# ResearchArchitect rereview 2: Chapter 9 CCD-Poisson / PPE

Date: 2026-04-28  
Branch: `worktree-ra-ch9-review`  
Scope: `paper/sections/09*.tex`  
Verdict after fixes: **PASS**

## Review stance

This third pass treated Chapter 9 as a paper section under reviewer scrutiny, with special attention to residual violations from earlier passes:

- no direct §13/ch13 dependency from a theory chapter;
- no overstatement of theoretical guarantees from verification-dependent rows;
- no hidden source comments or prose that preserve old operational history;
- no contradiction between the chapter summary table and its footnotes.

No `src/` files were changed.  No SOLID issue applies.

## Findings and resolution

### RRR9-1 — Chapter 9 still had direct downstream §13 references

Severity: Major  
Status: Fixed

The previous pass removed explicit `ch13` prose but left direct label references to downstream §13 material:

- `sec:interface_crossing` in the split-PPE limitation discussion;
- `sec:bf_static_droplet` in the BF/parasitic-flow validation notes.

These references violate the chapter separation policy established for chapters 2--12: theory chapters may mention validation conceptually, but must not depend on concrete downstream §13 labels.

Resolution:

- Removed direct references to `sec:interface_crossing` and `sec:bf_static_droplet` from Chapter 9.
- Reworded the affected text as theory-level statements or generic validation notes.
- Cleaned a stale source comment that preserved old `interface_crossing` provenance.

### RRR9-2 — Summary table overstated verification-dependent accuracy

Severity: Major  
Status: Fixed

The chapter summary table stated `O(h^4)` for the variable-density monolithic smoothed-Heaviside PPE row, while its footnote correctly said the improvement is outside the chapter's theory guarantee and verification-dependent.  The same summary also said all numerical components are `O(h^5)--O(h^6)`, contradicting the viscous row's `O(h^2)` diagonal contribution.

Resolution:

- Changed the monolithic variable-density PPE row to `理論保証外（界面律速；改善は検証依存）`.
- Reworded the closure box so high-order claims apply to pressure, geometry, and advection components, while lower-order viscous ADI components are scoped by the table footnotes.

### RRR9-3 — Residual operational/history vocabulary remained

Severity: Minor  
Status: Fixed

Remaining prose still used terms such as `現行`, `標準`, `legacy`, `旧表現`, `正規化`, `実用上`, and `本稿のアルゴリズム構成`, making Chapter 9 read partly like an implementation history instead of a theory/discretization section.

Resolution:

- Replaced operational terms with theory-neutral wording:
  - `標準` → `基準ケース` / `基準拘束`;
  - `現行ソルバ` → `連続圧力形式`;
  - historical naming notes → direct placement rationale;
  - `実用上問題なく` → explicit order statement.

## Verification

- `cd paper && latexmk -xelatex -interaction=nonstopmode main.tex`
  - Succeeded.
  - Output: 219 pages.
  - Undefined references: 0.
  - Undefined citations: 0.
- `git diff --check`
  - Succeeded.
- Targeted grep checks:
  - Chapter 9 has no direct `ch13`, `§13`, `sec:interface_crossing`, or `sec:bf_static_droplet` references.
  - Chapter 9 has no residual hits for the reviewed operational vocabulary set.
- Residual TeX warnings are existing §12 cosmetics:
  - Overfull/Underfull boxes in §12 traceability paragraphs.
  - Text-only float pages around §12.

## Final assessment

The third-pass residuals are resolved.  Chapter 9 now keeps theory, discretization, and validation boundaries clean:

- no direct downstream §13 dependency remains;
- verification-dependent accuracy is labeled as such;
- global accuracy claims no longer contradict low-order components in the summary table;
- remaining operational/history wording has been removed.

Recommendation: accept Chapter 9 after this rereview.
