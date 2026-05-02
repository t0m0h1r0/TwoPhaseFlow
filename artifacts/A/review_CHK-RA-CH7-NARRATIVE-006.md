# CHK-RA-CH7-NARRATIVE-006 — Chapter 7 sixth strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: The timestep synthesis used the opaque catch-all `\Delta t_\text{operator}` and tied it to projection closure, which contradicted the chapter's claim that projection is a non-growing elliptic constraint. It is now replaced by `\Delta t_{\mathrm{disc}}`, explicitly limited to additional discrete spectral bounds for explicit or extrapolated residual terms.
- MAJOR: The capillary CFL notation mixed `h`, `\Delta x`, and `\min(\Delta x,\Delta y)` in a way that obscured the anisotropic-grid meaning. Chapter 7 now defines `h_{\min}` once and uses it consistently in the CFL definition, synthesis formula, and derivation.
- MINOR: Reader-external wording such as `7 段階フロー`, `運用`, and `1 ショット` remained in the prose. These were replaced by mathematical descriptions: projection as a map to divergence-free velocity, stability coefficients, and geometric reconstruction without virtual-time evolution.

## Verification

- Chapter 7 sixth-review prose grep: PASS for old-version, implementation, solver, comparison-branch, notation-drift, stage-leakage, and operational wording.
- Obsolete Chapter 7 CN labels: PASS in touched paper sections.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 239 pp).
- Label sanity check: PASS for undefined and multiply-defined label grep.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed.
