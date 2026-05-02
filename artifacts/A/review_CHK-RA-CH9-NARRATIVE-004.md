# CHK-RA-CH9-NARRATIVE-004 — Chapter 9 strict review after main merge

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: Reader-facing Chapter 9 prose still mixed mathematical explanation with English method labels such as `pressure step`, `pressure closure`, `solve`, `operator-locus`, `sub-system`, and `primitive`. These now read as 圧力射影段階, 圧力閉包, 求解, 演算子位置, 部分系, and 基本構成.
- MAJOR: Boundary-condition and model terminology was not uniform. Visible prose now consistently uses `Neumann 境界条件`, `Dirichlet 境界条件`, `壁面境界条件`, `smoothed-Heaviside`, `プラトー`, `面係数`, and `定数密度演算子`.
- MAJOR: The Balanced--Force abbreviation layer was inconsistent with the chapter narrative. Reader-facing text now spells out `Balanced--Force 条件` / `Balanced--Force 整合性` rather than switching to unexplained `BF` forms.
- MINOR: `PPE 用アルゴリズム` made the DC section sound implementation-oriented. It is now `PPE 用欠陥補正の構成`.
- MINOR: The equation symbol `A_h^\mathrm{solve}` leaked solver wording into the notation. It is now `A_h^\mathrm{PPE}`.

## Narrative result

Chapter 9 now presents a single through-line: remove the density jump by分相化, insert the oriented pressure jump directly into the shared face-gradient contract, protect high-order one-sided data with HFE, and close the resulting PPE with DC plus a global gauge. FVM/FD, CSF, smoothed-Heaviside, and smooth auxiliary pressure fields are consistently described as limited comparison or support models rather than alternative main closures.

## Verification

- Chapter 9 residual terminology grep: PASS for old-version, implementation, English solve/pressure/operator/BC/face wording, and `\mathrm{solve}`.
- Formatting check: PASS with `git diff --check`.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 239 pp).
- Reference check: PASS; `main.log` has no undefined references, undefined citations, multiply-defined labels, or rerun-to-get-cross-references warning.
- Residual warnings: one Chapter 9 summary-table Underfull hbox and one float-only page warning; both nonfatal layout warnings.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed and no tested implementation deleted.
