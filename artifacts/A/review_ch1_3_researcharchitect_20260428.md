# §1-§3 ResearchArchitect Review — 2026-04-28

Verdict after fixes: PASS with residual layout-only warnings. Initial verdict was MAJOR REVISION due to stale chapter mapping and terminology drift.

## Scope
- Reviewed `paper/sections/01_introduction.tex` and `paper/sections/01b_classification_roadmap.tex`.
- Reviewed `paper/sections/02_governing.tex`, `02b_surface_tension.tex`, and `02c_nondim_curvature.tex`.
- Reviewed `paper/sections/03_levelset.tex`, `03b_cls_transport.tex`, `03c_levelset_mapping.tex`, and `03d_ridge_eikonal.tex`.

## Findings
- R1 MAJOR, fixed: `01b_classification_roadmap.tex` still numbered the verification/conclusion chapters as 11--14, while `paper/main.tex` has no live §11 and now inputs §12--§15. The overview table now uses §12 component verification, §13 integrated verification, §14 benchmarks, and §15 conclusion.
- R2 MAJOR, fixed: Interface-width language mixed "thickness ≈2ε", "95% width ≈6ε", and `[-3ε,3ε]` without defining the distinction. §1/§2/§3 now distinguish the scale parameter ε, central transition width ≈2ε, and 95% transition band ≈6ε.
- R3 MAJOR, fixed: The FMM/FSM reconstruction theorem in §3.4 claimed uniqueness while writing `±d(x,Γ)` without a prescribed sign. The theorem now requires phase-label sign consistency and states uniqueness for the signed viscosity solution.
- R4 MAJOR, fixed: §3.4 said geometric regularity and projection uniqueness were "naturally guaranteed"; this overstated the numerical guarantee. The text now states these as checks performed during ridge extraction.
- R5 MINOR, fixed: `Ridge-Eikonal`, `Ridge–Eikonal`, `Ridge--Eikonal`, `Balanced-Force`, `Balanced--Force`, `level-set`, and `Level Set` were mixed across §1--§3. The edited scope now uses `Ridge--Eikonal`, `Balanced--Force`, and `Level Set` consistently.
- R6 MINOR, fixed: A Japanese full stop `。` remained in an otherwise `．`-style caption; punctuation is now consistent in the edited scope.
- R7 MINOR, fixed: §2 described signed-distance definition and the Eikonal condition as exactly equivalent without mentioning the zero-set boundary condition. The statement now includes the `φ=0` interface condition.
- R8 MINOR, fixed: Early §1 direct references to `sec:interface_crossing` made the introduction depend on a downstream subfile label. They now point to the §13 integrated verification chapter.

## Traceability
- A3 chain preserved: equations and definitions in §1--§3 still point forward to the algorithm/discretization chapters, with downstream validation references lifted to chapter-level §13 where appropriate.
- [SOLID-N/A] No `src/` code changed; SOLID audit is not applicable.

## Verification
- `latexmk -xelatex -interaction=nonstopmode main.tex` succeeded in `paper/`.
- Output: `main.pdf`, 211 pages.
- Residual warnings: existing Overfull/Underfull boxes, text-only-float, and font substitution warnings outside the edited §1--§3 scope.
