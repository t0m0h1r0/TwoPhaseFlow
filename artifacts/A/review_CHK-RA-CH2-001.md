# CHK-RA-CH2-001: Chapter 2 Strict Narrative Review

Scope: `paper/sections/02_governing.tex`, `paper/sections/02b_surface_tension.tex`, `paper/sections/02c_nondim_curvature.tex`, adjacent consistency with chapters 1, 3, 9, and 11.

Stop condition: repeat review/remediation until no MAJOR+ findings remain, or round > 20.

## Round 1 Verdict: FAIL

### MAJOR-1: Chapter 2 presents CSF as the adopted surface-tension closure, contradicting the latest pressure-jump narrative.

`02b_surface_tension.tex` says the paper adopts CSF, then relegates GFM/HFE to a later alternative. This is no longer the latest architecture. Chapters 1, 9, and 11 define the current high-density-ratio closure as pressure-jump split PPE with HFE, DC, and shared face-space projection; CSF is retained as the one-fluid continuous representation and Balanced--Force explanatory/low-contrast contraction, not as the final universal closure. Chapter 2 must state the hierarchy explicitly: continuous CSF identity, one-fluid BF contraction, and split pressure-jump closure for the main high-density path.

### MAJOR-2: Chapter 2 prematurely declares the governing-equation chapter complete before surface tension, nondimensionalization, and curvature are introduced.

`02_governing.tex` ends with a transition to Chapter 3 even though `02b_surface_tension.tex` and `02c_nondim_curvature.tex` are still part of Chapter 2. This breaks the reader's map: the chapter appears to finish before defining the capillary force scale, Young--Laplace jump, and curvature formulas needed by all later chapters.

### MAJOR-3: The curvature implementation guidance is stale and fallback-shaped.

`02c_nondim_curvature.tex` ends with a phi-based "implementation quickstart" and describes the denominator clamp as a defensive fallback. The latest standard path in Chapters 3 and 11 is psi-direct curvature in the active interface band, with phi curvature retained only as an analytic/comparison expression. Chapter 2 should not teach an outdated phi-first implementation or use fallback language.

### MINOR-1: Chapter opening does not give a chapter-level contract.

The section starts immediately with variables. For a strict paper narrative, Chapter 2 should first say what it establishes: sign conventions, two-fluid-to-one-fluid equivalence, face coefficients, capillary jump/CSF relation, nondimensional groups, and curvature convention.

### MINOR-2: Notation around left/right face values and liquid/gas phase subscripts is correct but easy to misread.

The table note exists, but the chapter would be clearer if the main text distinguishes pointwise material laws from face coefficients and pressure-space coefficients earlier.

## Round 1 Remediation Plan

- Add a Chapter 2 roadmap and current-method contract at the opening.
- Replace "CSF is adopted" language with a layered closure hierarchy aligned with Chapters 1, 9, and 11.
- Move the Chapter 3 transition to the true end of Chapter 2 and replace the premature transition with an internal bridge.
- Replace phi-first quickstart/fallback text with psi-direct interface-band guidance and clarify that clamps are domain restrictions/diagnostics, not alternate geometry.
- Re-scan for stale trial/version/fallback language and compile the paper.

## Round 2 Verdict: PASS

MAJOR+ findings: 0.

The Chapter 2 opening now defines the chapter-level contract and explicitly separates the continuous CSF identity, the One-Fluid/Balanced--Force contraction, and the high-density-ratio pressure-jump split PPE closure. The premature transition to Chapter 3 was replaced by an internal bridge to the surface-tension subsection, and the true Chapter 2 ending now hands off to CLS. The curvature section now states the current standard path: psi-direct interface-band curvature, with phi curvature retained for sign convention, analytic checks, and diagnostics only.

Targeted terminology scan: no stale `CSF を採用`, `fallback`, `フォールバック`, `従来は毎ステップ`, `old`, `version`, `試行`, or `変更点` hits in Chapter 2.

Validation:

- `git diff --check`: PASS
- `make -C paper`: PASS (`paper/main.pdf`, 246 pages)
- `paper/main.log` fatal/error/undefined/overfull targeted scan: PASS

[SOLID-X] Paper/docs only; no `src/twophase/`, experiment script, config, or result change. No tested implementation deleted. No FD/WENO/PPE alternate-scheme fallback introduced.
