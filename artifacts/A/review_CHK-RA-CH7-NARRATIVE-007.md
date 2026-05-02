# CHK-RA-CH7-NARRATIVE-007 — Chapter 7 seventh strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: The chapter still leaked reader-external stage-count wording (`CLS 6 段階`) into the explanation of the global time-order narrative. It now describes the same idea as the causal order shared by CLS conservative update, viscous implicit update, and IPC projection.
- MAJOR: Physical-timescale notation mixed `\text{...}` and `\mathrm{...}` subscripts for the same role (`adv`, `buoy`, `syn`, `BV`, `ref`, `hs`, `spurious`). Chapter 7 now uses roman math subscripts consistently for these scale and diagnostic symbols.
- MINOR: The timestep synthesis and buoyancy sections used different subscript styles from the earlier CFL map. They now match the same `\Delta t_{\mathrm{adv}}`, `\Delta t_{\mathrm{buoy}}`, `\Delta t_{\mathrm{syn}}`, `N_{\mathrm{BV}}`, and `C_{\mathrm{adv}}` convention.

## Verification

- Chapter 7 seventh-review prose/notation grep: PASS for old-version, implementation, solver, comparison-branch, notation-drift, stage-leakage, and operational wording.
- Obsolete Chapter 7 CN labels: PASS in touched paper sections.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 239 pp).
- Label sanity check: PASS for undefined and multiply-defined label grep.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed.
