# Review CHK-RA-CH1-13-NARR-002

Session: `CHK-RA-CH1-13-NARR-002`
Agent: ResearchArchitect
Branch: `ra-ch1-13-narrative-review-20260503`
Base: `main` at `d08dc132`
Scope: latest `paper/sections/01*.tex`--`paper/sections/13*.tex` after V7/V10 RCA updates

## Verdict

PASS AFTER FIX. The retry review found no structural contradiction in Chapters
1--13 after the V7 and V10 RCA updates, but it did find reader-visible drift in
how V10 was described and in a small amount of notation / LaTeX literal style.
The fixed narrative now states the same experimental contract everywhere:
V10 is a fixed uniform-grid, NS-non-coupled CLS advection test that includes
Ridge--Eikonal reinitialization and Olsson--Kreiss mass correction, but excludes
momentum/PPE/surface-tension coupling.

## Findings And Fixes

### RA-CH1-13-NARR-002-01: V10 terminology blurred the tested axis

Finding: After the V10 RCA, Chapters 1, 12, and 13 still mixed
`CLS-only`, `passive scalar`, and Japanese descriptions of the same test. This
could be read as denying interface tracking, even though the test explicitly
uses CLS transport, Ridge--Eikonal reinitialization, and mass correction.

Fix: Recast the contract as `NS 非連成 CLS 強変形移流` / `NS 非連成 CLS 受動移流`
across the introduction, Chapter 12 bridge table, and Chapter 13 setting table.
This preserves the intended exclusion: no momentum/PPE/surface-tension coupling.

### RA-CH1-13-NARR-002-02: Galilean offset vector notation drifted from macros

Finding: V4 used raw `\bm U` while the reviewed notation policy uses vector
macros such as `\bu` and `\bx` for recurring physical vectors.

Fix: Added `\bU` in `paper/preamble.tex` and propagated it through V4 and the
Chapter 13 summary table. This separates the imposed Galilean offset from the
velocity field `\bu` without reintroducing raw `\bm{u}` / `\bm u` drift.

### RA-CH1-13-NARR-002-03: Code literals used prose quote syntax

Finding: `fixed_reinit_count` and `psi_direct_hfe` appeared as TeX prose quotes,
which made code/config identifiers visually inconsistent with surrounding
`\texttt{...}` usage.

Fix: Rewrote both as `\texttt{fixed\_reinit\_count}` and
`\texttt{psi\_direct\_hfe}`.

### RA-CH1-13-NARR-002-04: V7 slope `1.58` is not stale

Finding: The stale-value scan still finds `slope $1.58`, but both occurrences
are V7 RCA control results (`static-interface` diagnostics), not the main V7
verdict. The main result remains slope `1.48`.

Fix: No paper change beyond the literal-style cleanup; this is recorded so a
future scan does not misclassify valid RCA evidence as a stale primary result.

## Validation

- `git diff --check` PASS.
- Targeted stale-contract / notation scan PASS for `CLS-only`, `passive scalar`,
  `界面追跡なし`, `TVD--RK3`, `IMEX--BDF2`, `EXT2--AB2`, `AB2+IPC`, raw
  `\bm{x}` / `\bm x` / `\bm{u}` / `\bm u` / `\bm U`, and `\epsilon`.
- `make -C paper` PASS; output `paper/main.pdf`, 244 pages.
- Follow-up warning cleanup PASS: `sections/09f_pressure_summary.tex:57`
  underfull hbox removed by ragged-right table cells; Chapter 12 U1
  float-only page warning removed by changing U1 floats to `[htbp]`.
- Final `main.log` scan PASS: no `Underfull \hbox`, `Overfull \hbox`,
  `Text page`, or `LaTeX Warning`.

## SOLID-X

Paper/audit-only change. No production code boundary changed, no tested code
deleted, no FD/WENO/PPE fallback introduced, and no experiment data or figures
were modified.
