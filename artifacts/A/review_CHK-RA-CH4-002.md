# CHK-RA-CH4-002 — Chapter 4 Strict Narrative Review

Date: 2026-05-06
Worktree: `.claude/worktrees/ra-ch4-narrative-review-20260506`
Branch: `ra-ch4-narrative-review-20260506`
Scope: paper Chapter 4 (`04_ccd`--`04f_face_jet`) plus adjacent consistency scans where needed.

## Round 1 Verdict: FAIL

MAJOR-1 — Chapter narrative did not pin the current standard operator map early enough.
Chapter 4 opened with "CCD is unavoidable" and listed DCCD, UCCD6, FCCD, and face jet as parallel scheme choices. That made DCCD readable as a standard stabilizer despite the latest standard path: CLS uses FCCD conservative face flux, bulk momentum uses UCCD6, and pressure/capillary face closure uses same-locus FCCD/face-jet operators with no DCCD.

MAJOR-2 — Boundary-closure accuracy contract contradicted itself.
Section 4.3 stated that the standard closed-interval operator requires the 6-point fourth-order Equation-II closure, but the boundary selection guide still recommended the second-order minimal closure for standard Dirichlet/Neumann cases. The chapter also summarized the global closed-interval accuracy only as the second-order minimal-closure lower bound, which blurred the standard paper contract.

MAJOR-3 — DCCD retained an obsolete standard-CLS claim.
Section 4.4 still said that `\varepsilon_d=1/4` is adopted in the CLS stages. That conflicts with the current FCCD CLS standard route and with the pressure/Balanced--Force no-DCCD contract.

MINOR-1 — Several phrases were still written as implementation or development history rather than paper narrative.
Examples included "現実装", "将来的", "致命的な欠落", "実装チェック", and "実装フォールバック". These weaken the final-paper voice and distract from the latest research state.

## Remediation

- Rewrote the Chapter 4 opening as an operator-family chapter: base CCD for smooth nodal fields, DCCD as auxiliary nodal post-filter, UCCD6 for bulk momentum, and FCCD/face jet as same-locus face contracts.
- Added an explicit standard-route map before the scheme roadmap: CLS = FCCD face flux, bulk momentum = UCCD6, pressure/CSF/jump closure = FCCD/face jet, no DCCD in standard CLS/pressure/Balanced--Force closure.
- Separated the second-order Equation-II boundary formula as an analytical minimal closure from the standard closed-interval contract, which now points to the six-point fourth-order uplift closure.
- Updated the boundary selection guide so standard Dirichlet/Neumann cases use Equation-I plus the fourth-order Equation-II uplift, while the second-order closure is only the analytical lower-bound case.
- Removed the obsolete `\varepsilon_d=1/4` CLS adoption statement and recast it as the standalone DCCD post-filter design limit, not a standard CLS parameter.
- Replaced development-history phrasing with paper-facing terms such as applicability conditions, standard closure, evaluation form, and public contract.

## Round 2 Verdict: PASS

MAJOR+ findings: 0.

Targeted scans:
- DCCD standard-route conflict scan: PASS. Remaining DCCD/standard hits are explicit negations or caption notes saying DCCD is not the standard CLS/pressure face operator.
- Boundary closure scan: PASS. Standard closed-interval references now point to the fourth-order Equation-II uplift; second-order closure is marked as analytical lower bound / non-standard.
- Research-history vocabulary scan: PASS for Chapter 4 body. The only remaining "実装" hit is a `paper/main.tex` appendix comment outside Chapter 4 prose.

Validation status:
- `git diff --check`: PASS.
- `make -C paper`: PASS (`paper/main.pdf`, 245 pages).
- `paper/main.log` scans for fatal/error/undefined/overfull/underfull: PASS.

[SOLID-X] Paper/docs only; no `src/twophase/`, experiment script, config, or result change; no tested implementation deleted; no FD/WENO/PPE fallback or alternate pressure scheme introduced.
