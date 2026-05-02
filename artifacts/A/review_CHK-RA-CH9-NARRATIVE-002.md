# CHK-RA-CH9-NARRATIVE-002 — Chapter 9 strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: Chapter 9 read as a list of competing routes instead of a single pressure-step argument. The opening now follows density jump -> pressure jump -> face-operator consistency -> one-sided high-order data -> defect-correction solve.
- MAJOR: The chapter exposed implementation/configuration names and old-path wording in the reader-facing text. Chapter 9 now uses mathematical names only and removes old-version framing.
- MAJOR: The pressure-jump closure and smooth auxiliary-field composition were not cleanly separated. The text now states that a smooth auxiliary field can be absorbed by the elliptic unknown, while `G_\Gamma(p;j)=G(p)-B(j)` keeps the jump in the shared face operator.
- MAJOR: The pure FCCD/DNS material distracted from the adopted closure. It is now framed only as a pure high-order reference limit, not as a requirement for the Chapter 9 closure.
- MAJOR: Gauge discussion included diagnosis-style details rather than the invariant. It now derives the global gauge from the coupled cut-face law and the single constant null mode.
- MINOR: Notation mixed adoption-stack, standard/production wording, raw fields, and English implementation terms. The summary table and boundary-condition section now use closure-condition wording consistently.

## Verification

- Chapter 9 prohibited-term check: PASS for old-version wording, implementation/configuration identifiers, and production/GPU/API terms.
- Formatting check: PASS with `git diff --check`.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` (`paper/main.pdf`, 239 pp).
- Reference check: PASS; `main.log` has no undefined references, undefined citations, or multiply-defined labels.
- Residual warnings: one Chapter 9 summary-table Underfull hbox and one float-only page warning; both nonfatal layout warnings.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed and no tested implementation deleted.
