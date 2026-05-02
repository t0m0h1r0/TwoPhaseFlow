# CHK-RA-CH7-NARRATIVE-001 — Chapter 7 strict review

Verdict: PASS after fixes. Open findings: 0 FATAL / 0 MAJOR / 0 MINOR.

## Findings fixed

- MAJOR: Chapter 7 mixed the adopted implicit-BDF2 + defect-correction path with Crank--Nicolson comparison material and implementation notes. The chapter now explains only the adopted mathematical scheme.
- MAJOR: The viscous narrative did not clearly separate low-order implicit correction from the high-order full-stress residual. The section now states that the same-time high-order residual determines accuracy.
- MAJOR: Accuracy claims and cross-term wording were inconsistent with the adopted viscous scheme. The summary table now records full-stress implicit-BDF2 defect correction as second-order in time.
- MAJOR: Cross-chapter references still pointed to removed Crank--Nicolson labels. Sections 6d, 11, 11d, and 12u8 now point to the adopted Chapter 7 formulation.
- MAJOR: Chapter 11 contradicted Chapter 7 on CLS flux notation and BDF startup. It now uses FCCD face-flux divergence and a one-step BDF1 startup before BDF2.
- MINOR: Chapter 7 contained wording about old versions and implementation-level solvers. Those terms were removed from Chapter 7.

## Verification

- Chapter 7 prohibited-term check: PASS for old-version wording and implementation solver terms.
- Removed-label check: PASS for obsolete Crank--Nicolson Chapter 7 labels.
- LaTeX build: PASS with `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`.
- Formatting check: PASS with `git diff --check`.

## SOLID audit

- [SOLID-X] Paper and review documentation only; no production code boundary changed.
