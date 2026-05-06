# CHK-RA-CH9-001 Review Record

- Date: 2026-05-06
- Branch/worktree: `ra-ch9-narrative-review-20260506` / `.claude/worktrees/ra-ch9-narrative-review-20260506`
- Scope: Chapter 9 pressure closure (`paper/sections/09*.tex`)
- Reviewer stance: strict ResearchArchitect review, prioritizing narrative convincingness, notation consistency, and logical coherence.
- Stop condition: repeat until no MAJOR+ findings remain or round count exceeds 20.

## Round 1 Findings

### RA-CH9-MAJOR-001: HFE was written as a direct nodal-gradient pressure-correction path

- Location: `paper/sections/09c_hfe.tex`
- Severity: MAJOR
- Issue: The HFE section said to extend `p^n` and `\delta p` and then use `\bnabla(p^n_{\mathrm{ext}})` or `\bnabla(\delta p_{\mathrm{ext}})` directly in prediction/correction. That conflicted with the affine-jump IPC contract in §9.3, where pressure history and correction are represented as the face cochain `A_f(G_fp-B_f(j))`.
- Resolution: Reframed HFE as the supplier of high-order one-sided Hermite data for GFM jump rows and affine-jump face cochains. Nodal-extension gradient use is now explicitly limited to comparison/diagnostic paths, not the standard closure.

### RA-CH9-MAJOR-002: CLS mass preservation was attributed to the wrong stage

- Location: `paper/sections/09b_split_ppe.tex`
- Severity: MAJOR
- Issue: The design rationale attributed CLS volume mass preservation to Stage D. In Chapter 5, Stage D is Ridge--Eikonal reinitialization, while volume correction and mass closure are Stage B and Stage F. This made the conservation narrative logically inconsistent across chapters.
- Resolution: Changed the reference to Stage B and Stage F and removed the unsupported asymptotic-order claim from that sentence.

### RA-CH9-MAJOR-003: Diagnostic pressure representation was mixed with output/regeneration policy

- Location: `paper/sections/09b_split_ppe.tex`, `paper/sections/09f_pressure_summary.tex`
- Severity: MAJOR
- Issue: The pressure snapshot discussion described old result files, masked pressure, plot failure, and regeneration policy inside the mathematical closure narrative. This obscured the important point: the scalar diagnostic pressure must be the Hodge representative of the saved face cochain, not raw nodal pressure.
- Resolution: Rewrote the paragraphs as a mathematical diagnostic-representative definition. Raw nodal values and hidden interface-band displays are excluded from the Chapter 9 pressure representative without introducing output-contract instructions.

### RA-CH9-MINOR-001: "fallback" wording weakened the no-fallback contract

- Location: `paper/sections/09b_split_ppe.tex`
- Severity: MINOR
- Issue: The Hodge range projection was described as not a "low-order FD fallback". The English fallback term is risky in this repository because fallback routes are explicitly disallowed for paper-exact pressure closure.
- Resolution: Replaced it with "低次 FD 代替経路" and kept the algebraic range-projection explanation.

## Round 2 Review

Re-reviewed the patched Chapter 9 narrative for:

- HFE/affine-jump consistency.
- CLS stage references.
- pressure representative versus implementation-output policy.
- raw/masked/fallback terminology.
- Chapter 9 summary alignment with §9.3 and §9.4.

Result: no MAJOR or higher findings remain after Round 2. Remaining risk is layout/LaTeX-only and is covered by the validation step.

## Validation

- `git diff --check`: PASS.
- Targeted Chapter 9 terminology scans: no remaining `fallback`, `Stage D`, `masked`, or `plot は失敗` in `paper/sections/09*.tex`.
- `make -C paper`: PASS; generated `paper/main.pdf` with 244 pages.
- Log scan: no fatal LaTeX errors, undefined references, undefined citations, or overfull hboxes remain in `paper/main.log`.
