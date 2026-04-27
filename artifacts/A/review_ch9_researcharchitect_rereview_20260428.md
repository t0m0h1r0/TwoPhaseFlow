# ResearchArchitect rereview: Chapter 9 CCD-Poisson / PPE

Date: 2026-04-28  
Branch: `worktree-ra-ch9-review`  
Scope: `paper/sections/09*.tex` plus cross-references in §7 and §14  
Verdict after rereview fixes: **PASS**

## Rereview standard

Chapter 9 was reread as a reviewer, not as an implementer.  The second pass focused on residual contradictions left after the strict review fixes:

- whether the §9 PPE sign convention remains consistent when cited from other chapters;
- whether Neumann/gauge null-space statements are mathematically precise;
- whether theory text still leaks implementation or benchmark-operational vocabulary;
- whether stale DC-divergence, solver-choice, or chapter-specific claims remain.

No `src/` files were changed.  No SOLID issue applies.

## Findings and resolution

### RR9-1 — Projection sign convention was still ambiguous outside §9

Severity: Major  
Status: Fixed

§9b now separates the projection-form operator `D_f A_f G_f` from the SPD solve operator `-D_f A_f G_f`.  The rereview found that §7 and §14 still described PPE coupling as though `D_f A_f G_f` itself were the solve form.  This reintroduced the same sign ambiguity that the initial §9 fix had removed.

Resolution:

- `paper/sections/07_time_integration.tex` now states that projection form uses `D_f A_f G_f`, while the linear solve uses the SPD form `-D_f A_f G_f`.
- `paper/sections/14_benchmarks.tex` now uses the same convention in the benchmark overview.

### RR9-2 — Conditioning statement ignored the Neumann zero mode

Severity: Major  
Status: Fixed

The SPD-conditioning paragraph in §9b described the operator as non-singular without first removing the Neumann null mode.  That is only true on the gauge-projected, nonzero eigenspace.

Resolution:

- `paper/sections/09b_split_ppe.tex` now scopes the condition-number bound to the gauge-projected nonzero eigenspace.
- The text explicitly states that the Neumann zero mode is removed by the gauge condition.

### RR9-3 — Theory chapter still contained operational vocabulary

Severity: Minor  
Status: Fixed

The initial pass removed benchmark magnitudes and stale implementation claims, but several words still made §9 sound like an implementation manual: `実装`, `運用`, `標準設定`, and `推奨`.

Resolution:

- Reworded the remaining operational terms in §9 to mathematical or validation-neutral language.
- Kept the one remaining `発散閾値` occurrence because it is explicitly negated: the robust DC divergence threshold was not reproduced.

## Verification

- `cd paper && latexmk -xelatex -interaction=nonstopmode main.tex`
  - Succeeded.
  - Output: 219 pages.
  - Undefined references: 0.
  - Undefined citations: 0.
- `git diff --check`
  - Succeeded.
- Residual TeX warnings are existing §12 cosmetics:
  - Overfull/Underfull boxes in §12 traceability paragraphs.
  - Text-only float pages around §12.

## Final assessment

The second-pass blockers are resolved.  §9 now has a stable theory-level narrative:

- projection operator and solve operator use explicit opposite signs;
- the gauge condition closes the Neumann null space before SPD conditioning is asserted;
- DC behavior is stated as a verified plateau/non-reproduction result, not as an outdated divergence threshold;
- cross-chapter references in §7 and §14 no longer contradict §9.

Recommendation: accept §9 after these rereview fixes.
