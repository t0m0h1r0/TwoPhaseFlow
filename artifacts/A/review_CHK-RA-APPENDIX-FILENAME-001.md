# CHK-RA-APPENDIX-FILENAME-001 — Appendix File Naming Convention

Date: 2026-05-03
Branch: `ra-appendix-narrative-review-20260503`
Worktree: `.claude/worktrees/ra-appendix-narrative-review-20260503`

## Convention

Appendix section files now follow one idea:

- Top-level appendix entry files use `appendix_<letter>_<domain>.tex`.
- Child files use `appendix_<letter><printed-number>_<semantic-topic>.tex`.
- Sub-subsection files preserve the visible printed hierarchy with underscores, e.g. `appendix_e4_1_predictor_imex_bdf2.tex` for Appendix E.4.1.
- Historical names that encode implementation history rather than paper structure are forbidden: `appD_*`, `appendix_*_sN`, and generic buckets such as `appendix_numerics_solver_sN`.
- File names describe the reader-facing appendix location first, and the mathematical/content role second.

## Renaming Summary

- Appendix roots: `appendix_a_nondim_details`, `appendix_b_interface`, `appendix_c_ccd`, `appendix_d_advection_stability`, `appendix_e_pressure_coupling`, `appendix_f_bootstrap`, `appendix_g_verification_details`.
- Appendix B children: `appendix_b1_psi_phi_newton` through `appendix_b4_cls_reinitialization`, eliminating the old `s3` gap.
- Appendix C children: `appendix_c1_1_*`, `appendix_c1_2_*`, `appendix_c2_1_*`, `appendix_c2_2_*`, `appendix_c3_1_*`, `appendix_c3_2_*`.
- Appendix D/E children: DCCD stability, capillary CFL, DC Thomas / pseudo-time / spectral convergence, FVM reference, predictor, and DC-PPE files now carry their printed appendix numbers.

## Validation

- `git diff --check` PASS.
- `make -C paper` PASS; `paper/main.pdf` remains 242 pages.
- Final `paper/main.log` diagnostic scan PASS for `Underfull \hbox`, `Overfull \hbox`, `Text page`, and `LaTeX Warning`.
- Old-name scan PASS for `appD_*`, `appendix_*_sN`, `appendix_numerics_solver_sN`, `appendix_ppe_pseudotime`, `appendix_stability_analysis`, and stale `appendix_ccd_h01`.

## SOLID-X

No violation.  This CHK is paper-structure only: no production code boundary changed, no tested implementation was deleted, and no algorithmic fallback or numerical workaround was introduced.
