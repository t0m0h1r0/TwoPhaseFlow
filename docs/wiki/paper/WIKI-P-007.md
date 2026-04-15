---
ref_id: WIKI-P-007
title: "Ch11 Formal Review Corrections: 9 Factual Errors Fixed (2026-04-15)"
domain: A
status: ACTIVE
superseded_by: null
sources:
  - commit: "6c4dded"
    description: "paper: fix ch11 factual errors and misleading claims from formal review"
  - path: "paper/sections/11a_spatial_discretization.tex"
  - path: "paper/sections/11c_interface_pipeline.tex"
  - path: "paper/sections/11d_interface_field.tex"
  - path: "paper/sections/11g_summary.tex"
  - path: "paper/sections/12h_error_budget.tex"
  - path: "paper/sections/07b_reinitialization.tex"
depends_on:
  - "[[WIKI-P-006]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-15
---

# Ch11 Formal Review Corrections: 9 Factual Errors Fixed

Commit `6c4dded` (2026-04-15) applied 9 corrections identified during formal
review of chapter 11. [[WIKI-P-006]] (2026-04-11) is the last prior review
entry; these corrections postdate it.

---

## Correction Table

| ID | Section | File | Old Claim | Corrected Claim | Rationale |
|----|---------|------|-----------|-----------------|-----------|
| C-1 | 12.6 error budget | 12h_error_budget.tex | HFE 2D order O(h^3.0) | O(h^5.8), conditional pass at N=256 (rounding floor L_inf=4.6e-11) | Old value was misread from output |
| C-2 | 12.6 error budget | 12h_error_budget.tex | CCD curvature in CLS pipeline O(h^5.0) | O(h^1.0) | Standalone CCD operator is O(h^6); CLS pipeline (eps=1.5h regularization + 3h band) limits it to O(h^1) |
| C-3 | 12.6 error budget | 12h_error_budget.tex | No pass/fail column | Added checkmark/triangle column aligned with 11g | Symmetry with chapter 11 presentation |
| C-4 | 07b, 11c | 07b_reinitialization.tex, 11c_interface_pipeline.tex | DCCD zero-sum "< 3e-13 (machine precision)" | "< 5e-13, O(N * eps_mach) floating-point accumulation" | O(N * eps_mach) is the correct bound for N-cell discrete sum |
| C-5 | 11a | 11a_spatial_discretization.tex | 2nd derivative order p=5.97 | p=5.9-6.0; at N=128 to 256 reaches rounding floor (p drops to ~0.5) | Range is more honest; floor at fine grids is real |
| C-6 | 11d | 11d_interface_field.tex | NS grid-rebuild: "stable operation" for alpha=2 | "Numerically stable but mass conservation not achieved (23% loss)" | [[WIKI-E-017]] shows 23% mass loss at alpha=2; "stable" was misleading |
| C-7 | 11g | 11g_summary.tex | DCCD H(pi)=0 (unconditional) | H(pi)=0 at eps_d=0.25; at eps_d=0.05, H(pi)=0.80 | eps_d=0.25 is extreme damping; production eps_d=0.05 retains 80% at Nyquist |
| C-8 | 11g | 11g_summary.tex | DCCD TV "comparable" for discontinuous profiles | "56% larger" (DCCD TV=17.14 vs CCD TV=10.96) | Quantitative value replaces vague word |
| C-9 | 11c | 11c_interface_pipeline.tex | DGR "92x improvement" | "~99x" via excess ratio (eps_eff/eps - 1): 2.97 vs 0.03 | 92x was the raw ratio; excess ratio is the correct metric |

---

## Correction Patterns

Three systematic patterns emerged:

### 1. Standalone vs Pipeline Distinction (C-1, C-2)

A component achieving O(h^k) in isolation may not propagate that accuracy
through the full pipeline. The CCD curvature operator is O(h^6) standalone,
but CLS regularization (eps=1.5h) and evaluation band (3h) reduce it to
O(h^1) in the pipeline context. Always specify which context applies.

### 2. Quantitative vs Qualitative Language (C-6, C-7, C-8)

"Stable", "machine precision", "comparable" all proved imprecise. Formal
review consistently demanded numbers:

- "stable" -> "23% mass loss"
- "machine precision" -> "< 5e-13, O(N * eps_mach)"
- "comparable" -> "56% larger"

### 3. Rounding / Accumulation Models (C-4, C-5)

- O(N * eps_mach) is the correct floating-point bound for accumulated sums
  over N cells, not "machine precision"
- Rounding floors at fine grids (N=128 to 256) cause apparent order
  degradation that must be disclosed, not hidden

---

## Additional Re-Run Value Changes (commit 5daab29)

Beyond the 9 formal corrections, the ch11 re-run (same day) produced these
numerical updates in the paper tables:

- DCCD 1D total variation: 3.15 to 17.14
- RC bracket accuracy ratio: 24,876x to 14,229x
- CLS area error at N=256: O(10^-4) to O(10^-3)
- CLS remapping: "85x improvement" rewritten as machine precision O(10^-16)
- Young-Laplace: N=32 sign reversal eliminated
- NS grid rebuild alpha=2 mass error: 7.7e-5 to 2.3e-1
- DCCD zero-sum bound: 3e-13 to 5e-13
- GCL residual: 5.4e-14 to 2.4e-14
- exp11_32 spectral radius: 3.43 to 9.6

---

## Cross-References

- [[WIKI-P-006]] — Previous review entry (2026-04-11)
- [[WIKI-E-002]] — HFE experiments (source of O(h^5.8) in C-1)
- [[WIKI-E-017]] — NS grid-rebuild (source of 23% mass loss in C-6)
- [[WIKI-E-021]] — Ch12 re-run deltas (parallel changes in 12h)
- [[WIKI-T-002]] — DCCD filter theory (transfer function H(pi) in C-7)
