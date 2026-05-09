# CHK-RA-CH12-13-EXPRECHECK-002 - Chapter 12--13 scoped experiment execution

Date: 2026-05-09

Branch/worktree:

```text
codex/ra-ch12-13-exp-recheck-20260509
.claude/worktrees/codex-ra-ch12-13-exp-recheck-20260509
```

## Scope Correction

V11 was removed from the required Chapter 12--13 execution set after user
review.  The existing V11-style admissibility route depends on the Chapter 14
canonical rising-bubble YAML, so it is Chapter 14 preflight/admissibility work,
not a Chapter 13 physical benchmark.

Executed scope:

1. add and run U11 constrained face-state component gate;
2. integrate existing U10 and new U11 into Chapter 12 paper text;
3. keep Chapter 13 V-series at V1--V10 and state the V11 deferral;
4. rerun V6/V7/V9 only;
5. rebuild paper and validate logs.

Main was not merged.

## Execution Mode

Remote-first execution was attempted through `make cycle`.  The wrapper reported
remote unavailable in this session, so runs used the documented local fallback
with the project virtual environment on `PATH` and a writable Matplotlib cache:

```text
MPLCONFIGDIR=/private/tmp PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make cycle ...
```

For U11, the first `make cycle` fallback exposed that bare `python3` lacked
`matplotlib`; the accepted run used the same project venv through
`make run-local` after confirming the remote remained unavailable.

## U11 Constrained Face-State Gate

Command:

```text
MPLCONFIGDIR=/private/tmp PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make run-local EXP=experiment/ch12/exp_U11_constrained_face_state_space.py
```

Status: PASS.

Summary:

- max projected wall trace: `2.581e-12`
- max idempotence error: `4.851e-12`
- max metric self-adjoint relative error: `8.707e-14`
- max restricted Green relative residual: `1.294e-16`
- rank gates: wall `19/19`, periodic-wall quotient `25/25`
- post-clamp negative control rejected: wall trace `1.375`, periodic-wall trace `0.986`
- full-array periodic endpoint pressure mode rejected: endpoint gap `2.0`, restricted flux norm `22.14`

Generated:

- `experiment/ch12/exp_U11_constrained_face_state_space.py`
- `paper/figures/ch12_u11_constrained_face_state_space.pdf`

## U10/U11 Paper Integration

Added:

- `paper/sections/12u10_common_flux_ledger.tex`
- `paper/sections/12u11_constrained_face_state_space.tex`

Updated:

- `paper/sections/12_component_verification.tex`
- `paper/sections/12h_summary.tex`
- `paper/sections/13_verification.tex`
- `paper/sections/13f_error_budget.tex`

Chapter 12 now presents U1--U11.  Chapter 13 remains V1--V10 and states that
V11-style canonical-route preflight belongs to Chapter 14.

## V6/V7/V9 Reruns

### V6 density-ratio sweep

Command:

```text
MPLCONFIGDIR=/private/tmp PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make cycle EXP=experiment/ch13/exp_V6_density_ratio_convergence.py
```

Status: PASS.

Summary:

- all 8 cases completed
- max `u_final`: `1.238e-09`
- max `|Delta V_psi|/V_0`: `1.183e-16`
- pressure-correction diagnostic range: `0.737`--`1.003`

Generated/refreshed:

- `paper/figures/ch13_v6_density_ratio.pdf`
- `paper/figures/ch13_v6_density_ratio_fields.pdf`

### V7 IMEX-BDF2 two-phase time diagnostic

Command:

```text
MPLCONFIGDIR=/private/tmp PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make cycle EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py
```

Status: PASS.

Summary:

- `n=8`: `dt=2.500e-03`, `Linf_err=2.498e-06`
- `n=16`: `dt=1.250e-03`, `Linf_err=1.068e-06`, slope `1.23`
- `n=32`: `dt=6.250e-04`, `Linf_err=3.546e-07`, slope `1.59`
- finest observed slope: `1.59`

Generated/refreshed:

- `paper/figures/ch13_v7_imex_bdf2_time.pdf`

### V9 nominal/local epsilon switch

Command:

```text
MPLCONFIGDIR=/private/tmp PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make cycle EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py
```

Status: PASS.

Summary:

- all A/B/C cases completed at `N=24,32`
- max `|u|_max`: `9.82e-10`
- max `|Delta V|/V_0`: `4.73e-16`
- B/C remained identical in this reduced diagnostic, ratio `1.00`

Generated/refreshed:

- `paper/figures/ch13_v9_local_eps.pdf`
- `paper/figures/ch13_v9_ch14_stack_field.pdf`

## Validation

Completed after the experiment and paper updates:

```text
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m py_compile \
  experiment/ch12/exp_U11_constrained_face_state_space.py
git diff --check
make -B -C paper
rg -n "^(LaTeX Warning|Package .*Warning|Class .*Warning|Overfull|Underfull|! |.*Error|Fatal|Undefined control sequence|LaTeX Error)" paper/main.log
```

Results:

- `py_compile`: PASS
- `git diff --check`: PASS
- paper build: PASS, `paper/main.pdf` rebuilt to 262 pages
- final paper log warning/error scan: no matches

## SOLID-X

Experiment scripts, paper-facing figures, paper prose, artifacts, and ledger
only.  No production solver source, tested implementation, FD/WENO/PPE
fallback, damping/CFL workaround, smoothing, curvature cap, benchmark branch,
blanket projection, QP-as-physics path, or hidden DCCD/UCCD damper was added.
