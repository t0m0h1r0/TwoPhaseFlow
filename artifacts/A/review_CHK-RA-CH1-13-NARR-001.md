# Review CHK-RA-CH1-13-NARR-001

Session: `CHK-RA-CH1-13-NARR-001`
Agent: ResearchArchitect
Branch: `ra-ch1-13-narrative-review-20260503`
Base: `main` at `4cecd47c`
Scope: `paper/sections/01*.tex`--`paper/sections/13*.tex`

## Verdict

PASS AFTER FIX. The Chapter 1--13 rereview found the front-half narrative mostly
sound after the Chapter 1--11 pass, but the expanded scope exposed several
reader-visible seams at the Chapter 12--13 boundary and in notation discipline.
The paper now presents one coherent story: Chapters 1--11 define the adopted
operators, Chapter 12 verifies primitives in a stable Tier/U order, and Chapter
13 reports integration evidence with matching Type-A/B/D verdict grammar.

## Findings And Fixes

### RA-CH1-13-NARR-001-01: Chapter 12 Tier order contradicted U numbering

Finding: U7 appeared after U8/U9 in the body and still carried old Tier labels
in file comments and subsubsection titles. This made the chapter look edited in
place rather than deliberately structured, and it weakened the bridge from
primitive verification to the V tests.

Fix: Reordered the Chapter 12 Tier V--VII body so U7 precedes U8 and U9, then
propagated the same Tier map through the opening design map, subtest headings,
and Chapter 12 summary table.

### RA-CH1-13-NARR-001-02: Chapter 1 caveats lagged Chapter 13 evidence

Finding: The introduction still said the NS pipeline and long-time moving
interface verification were wholly future work, while Chapter 13 now contains
V7 coupled-stack timing and V10-a/b uniform-grid CLS-only strong-deformation
tests. It also quoted the obsolete V7 slope `1.58`.

Fix: Split the claim into verified scope and future verification gates:
V6/V7/V10-a/b are acknowledged as current evidence, while nonuniform
moving-interface CLS and long-time fully coupled NS moving-interface convergence
remain future gates. The V7 caveat is synchronized to the current observed
slope `1.04`.

### RA-CH1-13-NARR-001-03: V10 wording denied the interface test it described

Finding: V10-a/b were described as "界面追跡なし" even though the tests are
explicitly CLS advection tests with Ridge--Eikonal and mass correction. A
reviewer would read this as a contradiction in the experimental contract.

Fix: Recast the condition as "NS 連成なし" and described V10 as fixed-grid
CLS advection, preserving the intended distinction without denying interface
tracking.

### RA-CH1-13-NARR-001-04: Cross-chapter notation and acronym style drifted

Finding: Chapters 1--13 mixed `\bm{x}`/`\bm x` with `\bx`, `\bm{u}`/`\bm u`
with `\bu`, `\epsilon` with `\varepsilon`, and both `TVD--RK3`/`IMEX--BDF2`
and `TVD-RK3`/`IMEX-BDF2` in prose. U5 also described the Heaviside kernel as
if it used the CLS sign convention directly.

Fix: Normalized continuous position/velocity notation to `\bx`/`\bu`, retained
matrix unknowns as non-position vectors, used `\varepsilon` notation in the
reviewed scope, standardized prose acronyms to `TVD-RK3` and `IMEX-BDF2`, and
rewrote U5 as a sign-independent Heaviside-kernel moment test while explicitly
reminding that the CLS variable is `\psi=H_\varepsilon(-\phi)`.

## Validation

- `git diff --check` PASS.
- Targeted stale-contract scan PASS: no `TVD--RK3`, `IMEX--BDF2`, `EXT2--AB2`,
  `AB2+IPC`, `U6-c`, `界面追跡なし`, `future gate`, `未検証 gate`, stale V7
  `slope $1.58`, or obsolete "NS パイプライン完全結合" wording remains in the
  Chapter 1--13 targets.
- Targeted notation scan PASS: no `\bm{x}`, `\bm x`, `\bm{u}`, `\bm u`,
  `\epsilon`, positive-sign `H_\varepsilon(\phi)`, or
  `H_{\varepsilon}(\phi)` remains in the Chapter 1--13 targets.
- Chapter 12 Tier scan PASS: U7/Tier V, U8/Tier VI, and U9/Tier VII agree across
  design map, body headings, comments, and summary table.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS in
  `paper/`; output `main.pdf`, 243 pages.
- Remaining log notes observed: pre-existing underfull hbox in
  `sections/09f_pressure_summary.tex:57` and a Chapter 12 float-only page
  warning (`Text page 132 contains only floats`). Neither was introduced as a
  semantic issue by this review.

## SOLID-X

Paper/audit-only change. No production code boundary changed, no tested code
deleted, no FD/WENO/PPE fallback introduced, and no experiment data or figures
were modified.
