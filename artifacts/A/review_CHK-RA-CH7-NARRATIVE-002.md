# CHK-RA-CH7-NARRATIVE-002 — Chapter 7 second strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: The accuracy-principle paragraph still described a first-order explicit treatment of variable-viscosity cross derivatives. It now states the adopted same-time high-order residual treatment and removes the contradictory branch.
- MAJOR: The narrative still exposed non-adopted comparison branches in the CSF and third-order outlook passages. These were replaced by positive explanations of the adopted jump-decomposed CSF and second-order closure.
- MAJOR: The final reinitialization note still named solver-level future alternatives. It now states only the mathematical scope of non-adopted higher-order time integration.
- MAJOR: Chapter 7 mixed English/Japanese terms for projection, predictor/corrector, rising bubble, balanced-buoyancy, full stress, and splitting. Terms are now normalized in prose and tables.
- MINOR: Hard-coded section numbers and stage labels leaked into the time-integration narrative. These were replaced by semantic cross-references and mathematical step descriptions.
- MINOR: The explicit-method description incorrectly implied step reversibility. It now states the intended property: no algebraic solve is required.

## Verification

- Chapter 7 old-version and implementation-term prose grep: PASS.
- Chapter 7 notation consistency grep for major English/Japanese variants: PASS, excluding stable labels and math identifiers.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 239 pp).
- Label sanity check: PASS for undefined and multiply-defined label grep.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed.
