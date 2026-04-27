# §9 ResearchArchitect Strict Review — 2026-04-28

Initial verdict: MAJOR REVISION.
Verdict after fixes: PASS (0 FATAL, 0 MAJOR).

## Scope
- Reviewed `paper/sections/09_ccd_poisson.tex`.
- Reviewed `paper/sections/09b_split_ppe.tex`.
- Reviewed `paper/sections/09c_hfe.tex`.
- Reviewed `paper/sections/09d_defect_correction.tex`.
- Reviewed `paper/sections/09e_ppe_bc.tex`.
- Reviewed `paper/sections/09f_pressure_summary.tex`.

## Findings
- R9-1 MAJOR: §9b mixed the projection-form operator `D_f A_f G_f` with the SPD solve operator without declaring the sign convention. The text claimed SPD while also writing the continuous split equation with the opposite sign.
- R9-2 MAJOR: §9e still claimed density-ratio-driven DC divergence at `rho_l/rho_g >= 10`, while §9b and §13 state that the renewed retest did not reproduce divergence and instead found grid-convergence plateau.
- R9-3 MAJOR: Gauge policy was inconsistent. §9b uses phase-wise mean gauge and warns that point pins break symmetry, while §9e recommends a one-point pin and §9b still names GMRES despite the SPD/CG framing.
- R9-4 MAJOR: §9 included verification-stage or operational claims inside a theory chapter: benchmark-order parasitic-current values, "verification planned", "measured value" language, and solver-scale recommendations not tied to a proven theorem.
- R9-5 MINOR: Boundary-condition wording retained FVM-specific periodic-matrix language in the CCD/FCCD chapter summary.
- R9-6 MINOR: Source comments still referred to old §8 placement and a `ch13` cleanup condition, despite the current chapter being §9 and the paper source policy removing chapter-specific implementation leakage.

## Planned Fix Policy
- Preserve the equations and labels used by downstream chapters.
- Clarify sign conventions locally rather than rewriting cross-chapter notation.
- Replace stale divergence and "planned/measured" claims with verification-backed or conditional wording.
- Align gauge wording with phase-wise mean gauge as the default for split PPE.
- Keep FVM only as a comparison or legacy low-order reference, not as the primary §9 boundary path.

## Fix Summary
- R9-1 fixed: `09b_split_ppe.tex` now separates projection-form `D_f A_f G_f` from SPD solve form `A_h=-D_fA_fG_f` and states the simultaneous RHS sign flip.
- R9-2 fixed: `09e_ppe_bc.tex` now matches the §13 retest: robust DC divergence was not reproduced; the remaining limitation is grid-convergence plateau.
- R9-3 fixed: Split PPE gauge text now prefers phase-wise volume-mean gauge, keeps point pins as fallback, and removes GMRES-specific wording.
- R9-4 fixed: §9 benchmark magnitudes, "verification planned", and "measured value" phrasing were replaced by structural comparisons and verification-dependent qualifiers.
- R9-5/R9-6 fixed: FVM wording is scoped to low-order baselines, and stale §8/chapter-specific source comments were removed.

## Verification
- `cd paper && latexmk -xelatex -interaction=nonstopmode main.tex` passed.
- Output: 219 pages, undefined references 0, undefined citations 0.
- Residual warnings are pre-existing §12 Overfull/Underfull and text-only float cosmetics; §9 introduced no remaining Overfull after table-width adjustment.
- SOLID audit: not applicable; no `src/` code changed.
