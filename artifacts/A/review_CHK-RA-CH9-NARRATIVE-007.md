# CHK-RA-CH9-NARRATIVE-007 — Chapter 9 closure consistency review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: The six-part narrative was still not fully propagated into §9.3. The local split-PPE closure list still said five parts and omitted `DC k=3` and reprojection separation. The local closure formula and the pure-FCCD boundary paragraph now match the chapter opening and summary.
- MAJOR: The defect-correction discussion still drifted into implementation-facing low-solve language (`LU`, factor reuse, repeated decomposition, cost avoidance). It now states the mathematical role split: high-order residual evaluation by `L_H`, low-order correction by `L_L`, and a direct low-order correction equation used to isolate algebraic error from DC convergence.
- MAJOR: Reprojection wording still used the reader-visible `再メッシュ` frame in section/table prose. It now uses `格子再生成後の再投影`, matching the mathematical condition that jump information is not inherited by the reprojection PPE.
- MINOR: The chapter still exposed `CCD-LU` as a role-limited model name. It now uses `直接解型 CCD`, avoiding solver-specific shorthand in the reader-facing narrative.
- MINOR: The closing sentence repeated `圧力ジャンプ` tautologically and HFE prose still called the method a `基盤技術`. These are now phrased as an oriented Young--Laplace interface condition and HFE as field-extension theory.
- MINOR: The updated six-term closure display caused an Overfull hbox. The formula now uses a two-line aligned display.

## Narrative result

Chapter 9 now carries the same closure contract in every layer: opening, split-PPE definition, pure-FCCD comparison, summary table, and final paragraph all state the same route. The reader sees one story: phase splitting removes density-jump conditioning, an oriented Young--Laplace condition carries interface stress, one face-gradient contract shares that jump between PPE and velocity correction, HFE supplies one-sided smooth data, DC separates high-order residual evaluation from low-order correction, and the global gauge/reprojection separation closes the remaining null-mode and remap issue.

## Verification

- Chapter 9 residual terminology grep: PASS for stale five-part narrative, `CCD-LU`, cost/reuse/LU wording, `再メッシュ`, implementation/legacy terms, visible `BC`, `CG/PCG`, `RHS`, `Predictor`, `Corrector`, `圧力ステップ`, and `3ステップ`.
- Formatting check: PASS with `git diff --check`.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 240 pp).
- Reference check: PASS; `main.log` has no undefined references, undefined citations, multiply-defined labels, or rerun-to-get-cross-references warning.
- Residual warnings: one §9 summary-table Underfull hbox and one float-only page warning; both nonfatal layout warnings.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed and no tested implementation deleted.
