# CHK-RA-CH9-NARRATIVE-006 — Chapter 9 post-merge strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: The chapter opening and closing did not carry the same narrative skeleton. The introduction used five issues, while the summary emphasized gauge/reprojection and omitted defect correction from the list. Both now state the same six-part story: density jump, pressure jump, face-operator consistency, high-order one-sided data, defect correction, and global gauge/reprojection separation.
- MAJOR: The re-mesh/reprojection subsection used implementation-facing wording (`コンテキスト`, `メインステップ`, `前段で走る`, `渡さず`, `分離設計`). It now states the mathematical separation principle: reprojection PPE excludes interface-jump information, while only the pressure projection PPE carries `[p]_\Gamma`.
- MAJOR: The reader-facing name of the comparison model varied between `一括 smoothed-Heaviside PPE`, `変密度一括 smoothed-Heaviside PPE`, `一括変密度 PPE`, and `一括解法`. Chapter 9 now consistently uses `smoothed-Heaviside 一括 PPE`.
- MINOR: The GFM subsection still used stitching language and an English visible equation note. It now uses `相間接続`, a `\mathrm{conn}` superscript, and a mathematical extension operator.
- MINOR: The HFE tensor-product note described the mixed-derivative omission as a low-cost version. It now states the actual accuracy condition: omitting mixed derivatives fails the data condition for the `\Ord{h^6}` guarantee.

## Narrative result

Chapter 9 now presents one coherent reviewer-facing path. The pressure projection problem is not a menu of solvers; it is a closure problem for discontinuous interfacial stress on shared discrete faces. The chapter first removes the density jump by phase splitting, then introduces the oriented Young--Laplace pressure jump, imposes it through a shared face-gradient contract, protects high-order stencils with HFE, handles the high-order operator through DC, and closes the remaining null mode/reprojection issue with a global gauge and jump-information separation.

## Verification

- Chapter 9 residual terminology grep: PASS for stale five-part narrative, reprojection-guard wording, `一括 smoothed`, `変密度一括`, `一括解法`, stitching wording, implementation/legacy terms, visible `BC`, `CG/PCG`, `RHS`, `Predictor`, `Corrector`, `圧力ステップ`, and `3ステップ`.
- Formatting check: PASS with `git diff --check`.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 239 pp).
- Reference check: PASS; `main.log` has no undefined references, undefined citations, multiply-defined labels, or rerun-to-get-cross-references warning.
- Residual warnings: one §9 summary-table Underfull hbox and one float-only page warning; both nonfatal layout warnings.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed and no tested implementation deleted.
