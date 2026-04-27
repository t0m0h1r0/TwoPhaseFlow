# ResearchArchitect strict review: chapter 8

Date: 2026-04-28
Branch: `worktree-ra-ch8-review`
Scope: `paper/sections/08*.tex`
Mode: FULL-PIPELINE -> PaperWorkflowCoordinator / PaperReviewer stance

## Verdict

FAIL until the fatal/major items below are fixed. Chapter 8 has a strong narrative, but several claims currently contradict the paper's own FVM coefficient derivation, IPC time-step policy, and verification references.

## Findings

### FATAL-1: face coefficient definition reverses the coefficient

- Location: `paper/sections/08d_bf_seven_principles.tex:113`
- Problem: P-4 says `\betaf^\text{harm}` is the harmonic average of `1/\rho`, but writes the inverse of the arithmetic average of `1/\rho`: `[(1/\rho_L+1/\rho_R)/2]^{-1}=2\rho_L\rho_R/(\rho_L+\rho_R)`. This has density units and contradicts the selected coefficient `2/(\rho_L+\rho_R)`.
- Evidence: `paper/sections/appendix_numerics_solver_s4.tex:14` and `paper/sections/appendix_numerics_solver_s4.tex:177` define the correct face coefficient as `2/(\rho_L+\rho_R)`.
- Required fix: State `a=1/\rho`, `a_f^\mathrm{harm}=2a_La_R/(a_L+a_R)=2/(\rho_L+\rho_R)`, and explicitly mark the inverse harmonic density form as the implementation error.

### MAJOR-1: FCCD residual order is asserted as fourth order while GFM path is second-order limited

- Location: `paper/sections/08e_fccd_bf.tex:27`
- Problem: Equation `eq:bf_fccd_unification` states `BF_res = O(\Delta x^4)` unconditionally. The same section later states Phase 1 FCCD+GFM is `O(\Delta x^2)` and only IIM reaches `O(\Delta x^4)`.
- Evidence: `paper/sections/08e_fccd_bf.tex:106` and `paper/sections/08e_fccd_bf.tex:111`.
- Required fix: Split operator footprint consistency from full BF residual: smooth/IIM-corrected face jets can be fourth-order; Phase 1 GFM/CSF remains second-order limited.

### MAJOR-2: IPC derivation uses the wrong projection time width

- Location: `paper/sections/08b_pressure.tex:23`
- Problem: The chapter derives IPC using `\Delta t`, while Chapter 7 defines `\Delta t_{\mathrm{proj}}=\gamma\Delta t` for IMEX-BDF2 and `\Delta t` only for BDF1 startup.
- Evidence: `paper/sections/07_time_integration.tex:402` and `paper/sections/07_time_integration.tex:736`.
- Required fix: Use `\Delta t_{\mathrm{proj}}` in the projection derivation and explain that the displayed algebra extracts the projection substep.

### MAJOR-3: `sec:fvm_ccd_corrector` points to the wrong content

- Location: `paper/sections/08b_pressure.tex:6`
- Problem: Multiple later sections cite `sec:fvm_ccd_corrector` as the FVM--CCD metric consistency argument, but the label currently anchors the general variable-density projection derivation.
- Evidence: `paper/sections/10b_ccd_extensions.tex:71`, `paper/sections/13h_nonuniform_grid.tex:310`, and `paper/sections/13h_nonuniform_grid.tex:335`.
- Required fix: Move the label to a dedicated paragraph/subsubsection that defines the nonuniform-grid face-average/adjoint correction and points verification to `sec:gadjacent_verification`.

### MAJOR-4: nonuniform-grid BF path mixes operators in prose

- Location: `paper/sections/08_collocate.tex:171`
- Problem: The prose says the velocity correction switches to `\mathcal{G}^\text{adj}` while surface tension keeps CCD and BF is still maintained. Under P-1/P-2 this is only true if the BF force is evaluated in the same face slot/operator pair; otherwise this is exactly an F-1/F-2 style mismatch.
- Required fix: Rephrase the nonuniform path as an adjoint-pair BF path and explicitly rule out mixing nodal CCD surface tension with `\mathcal{G}^\text{adj}` correction.

### MINOR-1: stale or undefined verification references

- Location: `paper/sections/08e_fccd_bf.tex:111`
- Problem: `sec:fccd_adv_bf_theorem` has no label in `paper/sections`.
- Location: `paper/sections/08e_fccd_bf.tex:121`
- Problem: The text says `§11 検証章`, but the independent chapter 11 was removed and component verification is now section 12.
- Required fix: Replace the undefined theorem reference with `sec:fccd_def`/`sec:face_jet_def` and remove the stale chapter number.

## SOLID audit

[SOLID-N/A] No `src/twophase/` code changes are in scope for this review. The relevant gate is P3/A3 consistency: equation -> discretization -> verification references.

