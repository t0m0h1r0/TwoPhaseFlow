# Review CHK-RA-CH12-13-UPDATE-001

## Scope

Recent-result impact audit for paper chapters 12--13, followed by rerun of the affected chapter-13 experiments and paper/figure refresh.

## Impact Decision

- Chapter 12 needs no new primitive experiment. Its U-tests remain component contracts; the only required update is the U-to-V bridge wording so V6/V7 explicitly depend on capillary range projection.
- Chapter 13 does need reruns for V6, V7, and V9, because those scripts claimed the reference / production-family pressure-jump stack but did not yet require `capillary_range_projection: range_projected`.
- V3 remains the reduced BF/CSF long-term static-droplet test. The range-projected pressure-jump static gate is already represented as the auxiliary V3 face-balance gate in `13b_twophase_static.tex`, so duplicating it as a new V-number would blur the chapter structure.
- No experiment is deleted. Old claims that V6/V9 velocities are merely bounded or density-ratio-scaled are superseded by the stronger range-projected face-balance result.

## Rerun Evidence

Remote-first commands used `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=...`:

- `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py`: PASS, `n_ref=64`, errors `2.175e-6, 9.249e-7, 3.068e-7`, local slopes `1.23, 1.59`.
- `experiment/ch13/exp_V6_density_ratio_convergence.py`: PASS, all 8 cases stable. Final speed max `5.723e-10`; volume drift max `1.269e-16`; pressure-correction diagnostic ratio range `0.737--1.003`.
- `experiment/ch13/exp_V9_local_eps_nonuniform.py`: PASS, all 6 cases stable. `N=32` B/C identical; max speed `4.269e-10`; volume drift max `6.345e-16`.

Local plot-only regenerated the paper PDFs:

- `paper/figures/ch13_v6_density_ratio.pdf`
- `paper/figures/ch13_v6_density_ratio_fields.pdf`
- `paper/figures/ch13_v7_imex_bdf2_time.pdf`
- `paper/figures/ch13_v9_local_eps.pdf`
- `paper/figures/ch13_v9_ch14_stack_field.pdf`

## Paper Updates

- `paper/sections/12h_summary.tex`: U-to-V bridge now names capillary range projection for V6/V7.
- `paper/sections/13d_density_ratio.tex`: V6 table/captions and V7 table/verdict updated to range-projected rerun values.
- `paper/sections/13e_nonuniform_ns.tex`: V9 table/captions/verdict updated to range-projected rerun values.
- `paper/sections/13_verification.tex` and `13f_error_budget.tex`: summary/error-budget rows synchronized with V6/V7/V9.

## Validation

- `py_compile` PASS for modified ch13 experiment scripts.
- `git diff --check` PASS.
- `make -C paper` PASS, producing `paper/main.pdf` (244 pages).
- `paper/main.log` fatal/error/undefined-control scan PASS.
- Existing overfull remains only at `paper/sections/09f_pressure_summary.tex:71`.

## Verdict

PASS. Chapters 12--13 are now aligned with the last three days' pressure-Hodge / capillary range projection results. The affected experiments were rerun, and the paper text plus figures reflect the new evidence.
