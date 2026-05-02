# CHK-RA-CH7-NARRATIVE-008 — Chapter 7 eighth strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: The opening table classified physical terms, but the chapter did not explicitly distinguish that classification from the causal order of a timestep. A reader could therefore infer that the section order was the execution order. The prose now states that the actual causal order is CLS conservative update → NS predictor → IPC PPE projection, while the exposition order follows closure dependencies.
- MAJOR: The velocity-consistency subsection said both CLS update and momentum advection use `\bm{u}^n`, which was too coarse for EXT2. It now distinguishes CLS using the projected `\bm{u}^n` from momentum advection using the projected history `\{\bm{u}^n,\bm{u}^{n-1}\}`, and explicitly excludes unprojected `\bm{u}^*` as an advecting velocity.
- MINOR: The timeline sketch now shows the projected velocity history before the combined CLS / momentum-predictor step, so the narrative matches the BDF2/EXT2 formulas that follow.

## Verification

- Chapter 7 eighth-review prose grep: PASS for old-version, implementation, solver, comparison-branch, stage-leakage, and reader-external terminology.
- Obsolete Chapter 7 CN labels: PASS in touched paper sections.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 239 pp).
- Label sanity check: PASS for undefined and multiply-defined label grep.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed.
