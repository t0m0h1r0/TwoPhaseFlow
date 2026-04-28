# §4-§10 ResearchArchitect Review — 2026-04-28

Verdict after fixes: PASS with residual layout-only warnings outside the edited scope. Initial verdict was MAJOR REVISION due to role conflicts, precision overclaims, and chapter-format drift.

## Scope
- Reviewed §4 CCD family: `paper/sections/04_ccd.tex` through `04f_face_jet.tex`.
- Reviewed §5--§7 Level Set reinitialization, per-variable schemes, and time integration.
- Reviewed §8--§9 collocated pressure/Balanced--Force and CCD/PPE pressure chapters.
- Reviewed §10 grid and nonuniform extensions, including Ridge--Eikonal nonuniform notes.

## Findings
- R4-10-1 MAJOR, fixed: Ridge--Eikonal was described as a main reinitialization route in §5/§5.2/§7, conflicting with §3.4. It is now consistently scoped as an auxiliary distance-reconstruction path.
- R4-10-2 MAJOR, fixed: §6 overclaimed Ridge--Eikonal/ξ-SDF distance accuracy as `O(h^6)`. It now separates linear zero-crossing accuracy from FMM/ξ distance-field consistency.
- R4-10-3 MAJOR, fixed: §8 overclaimed Balanced--Force as using the "exact same CCD operator". It now states the correct invariant: same discrete locus with an adjoint-compatible gradient/divergence pair.
- R4-10-4 MAJOR, fixed: §10 used `L/N` for grid width while the coordinate definition used `N-1` intervals. The density-width and `h_\mathrm{ref}` definitions now use `L/(N-1)`.
- R4-10-5 MINOR, fixed: Terminology drift was corrected to `Ridge--Eikonal`, `Balanced--Force`, and `仮想時間` across the edited target scope.
- R4-10-6 MINOR, fixed: Chapter openings now follow the §1--§3 style more closely through `本章の位置付け` and `本章の構成` framing where missing.
- R4-10-7 MINOR, fixed: The §5.2 Stage D wording created an edited-scope overfull line after terminology repair; the sentence/table wording was tightened.

## Traceability
- A3 chain preserved: CCD derivations, CLS/reinitialization choices, BF/PPE consistency, and nonuniform-grid definitions remain connected to downstream discretization/verification references.
- [SOLID-N/A] No `src/` code changed; SOLID audit is not applicable.

## Verification
- `git diff --check` passed after the final edits.
- `latexmk -xelatex -interaction=nonstopmode main.tex` succeeded in `paper/`.
- Output: `main.pdf`, 211 pages.
- Residual warnings: existing Overfull/Underfull boxes, text-only-float, and font substitution warnings mainly in §12--§13/appendices, outside the edited §4--§10 scope.
