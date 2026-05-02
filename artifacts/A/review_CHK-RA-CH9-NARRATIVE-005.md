# CHK-RA-CH9-NARRATIVE-005 — Chapter 9 strict review after terminology merge

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: The chapter still mixed `圧力ステップ` and `圧力射影段階`. Reader-facing prose now uses `圧力射影段階` for the chapter-level narrative.
- MAJOR: HFE placement used inconsistent density-ratio thresholds (`>5` and `>10`). The text now states the mathematical split without inventing competing cutoffs: smoothed-Heaviside is a low-density-ratio comparison model, while high-density-ratio pressure-jump closure uses HFE.
- MAJOR: Solver alternatives leaked back into the Chapter 9 narrative through `CG/DC` and `CG/PCG`. These were removed; the text now states conditioning, defect-correction convergence, and positive-definite phase blocks without recommending CG paths.
- MINOR: Boundary-condition notation was inconsistent (`BC` vs `境界条件`). Visible prose now uses `境界条件`, including interface correction, pressure boundary consistency, periodic idealization, and Dirichlet/Neumann summaries.
- MINOR: The DC sweep wording still said `3ステップ`. It now uses `3段`, consistent with the surrounding 第1段/第2段/第3段 notation.

## Narrative result

Chapter 9 now keeps one clean reader path: the pressure projection stage removes density-jump conditioning by phase splitting, carries Young--Laplace stress as an oriented pressure jump, shares that jump through one face-gradient contract, protects high-order stencils with HFE, and closes the solve with DC plus a global gauge. Solver-choice side paths and arbitrary density-ratio thresholds no longer interrupt that story.

## Verification

- Chapter 9 residual terminology grep: PASS for `圧力ステップ`, visible `BC`, `CG/PCG`, `CG`, `PCG`, conflicting density cutoffs, `3ステップ`, and old implementation/English route terms.
- Formatting check: PASS with `git diff --check`.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 240 pp).
- Reference check: PASS; `main.log` has no undefined references, undefined citations, multiply-defined labels, or rerun-to-get-cross-references warning.
- Residual warnings: one Chapter 9 summary-table Underfull hbox and one float-only page warning; both nonfatal layout warnings.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed and no tested implementation deleted.
