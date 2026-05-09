# CHK-RA-CH12-13-EXPRUN-001 - Chapter 12--13 experiment run

Date: 2026-05-09

Base branch/worktree: `codex/ra-ch12-13-exp-audit-main-20260509` at
`.claude/worktrees/codex-ra-ch12-13-exp-audit-main-20260509`.

Remote-first status: `make check` failed with `Remote 'python' is NOT
reachable.`  Per project policy, the runs below were executed through local
fallback with:

```text
PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH make cycle EXP=...
```

## Runs

### U10 common-flux ledger

Command:

```text
make cycle EXP=experiment/ch12/exp_U10_common_flux_ledger.py
```

Status: PASS after correcting the experiment-side periodic conservation
measure to exclude duplicate periodic endpoint nodes.

Summary:

- closed max relative energy delta: `0.000e+00`
- closed max `|mass delta|`: `1.137e-13`
- closed max `|momentum delta|`: `2.842e-14`
- closed max affine density error: `0.000e+00`
- negative controls rejected: `2 / 2`

Generated:

- `paper/figures/ch12_u10_common_flux_ledger.pdf`

### V11 conservative common-flux admissibility

Command:

```text
make cycle EXP=experiment/ch13/exp_V11_common_flux_admissibility.py
```

Status: PASS.

Summary:

- backend: `cpu`
- ledger stages: `3`
- certificate energy delta: `-3.092e-22`
- affine density error: `0.000e+00`
- negative controls rejected: `2 / 2`

Generated:

- `paper/figures/ch13_v11_common_flux_admissibility.pdf`

### V3 static droplet long-term

Command:

```text
make cycle EXP=experiment/ch13/exp_V3_static_droplet_longterm.py
```

Status: PASS.

Summary:

| N | `|u|_inf_final` | `|u|_inf_max` | `Delta_p` | relative pressure error |
|---:|---:|---:|---:|---:|
| 128 | `6.271e-03` | `6.271e-03` | `3.9613` | `0.97%` |
| 64 | `1.686e-03` | `1.686e-03` | `3.9510` | `1.23%` |
| 96 | `7.043e-03` | `7.043e-03` | `3.9539` | `1.15%` |

Regenerated:

- `paper/figures/ch13_v3_static_droplet.pdf`
- `paper/figures/ch13_v3_static_droplet_snapshot.pdf`

### V6 density-ratio convergence

Command:

```text
make cycle EXP=experiment/ch13/exp_V6_density_ratio_convergence.py
```

Status: PASS.

Summary:

| `rho_l/rho_g` | N | steps | `u_final` | volume drift | `|dp_corr|/(sigma/R)` |
|---:|---:|---:|---:|---:|---:|
| 2 | 24 | 8 | `1.020e-12` | `1.183e-16` | `7.499e-01` |
| 2 | 32 | 8 | `0.000e+00` | `0.000e+00` | `1.003e+00` |
| 10 | 24 | 8 | `1.238e-09` | `1.183e-16` | `7.394e-01` |
| 10 | 32 | 8 | `0.000e+00` | `0.000e+00` | `1.003e+00` |
| 100 | 24 | 8 | `3.927e-10` | `1.183e-16` | `7.370e-01` |
| 100 | 32 | 8 | `0.000e+00` | `0.000e+00` | `1.002e+00` |
| 833 | 24 | 8 | `3.371e-10` | `1.183e-16` | `7.575e-01` |
| 833 | 32 | 8 | `0.000e+00` | `0.000e+00` | `1.002e+00` |

Regenerated:

- `paper/figures/ch13_v6_density_ratio.pdf`
- `paper/figures/ch13_v6_density_ratio_fields.pdf`

### V7 IMEX/BDF2 twophase time diagnostic

Command:

```text
make cycle EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py
```

Status: PASS.

Summary:

| steps | dt | `Linf_err` | slope |
|---:|---:|---:|---:|
| 8 | `2.500e-03` | `2.498e-06` | |
| 16 | `1.250e-03` | `1.068e-06` | `1.23` |
| 32 | `6.250e-04` | `3.546e-07` | `1.59` |

Finest observed slope: `1.59`.

Regenerated:

- `paper/figures/ch13_v7_imex_bdf2_time.pdf`

### V9 local-epsilon nonuniform

Command:

```text
make cycle EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py
```

Status: PASS.

Summary:

| N | case | `|u|_max` | `Delta_p` | `|Delta p_corr|/(sigma/R)` | volume drift |
|---:|---|---:|---:|---:|---:|
| 24 | A alpha=1 nominal eps | `5.92e-10` | `0.2975` | `0.74` | `1.18e-16` |
| 24 | B alpha=2 nominal eps | `1.61e-10` | `0.4087` | `1.02` | `4.73e-16` |
| 24 | C alpha=2 local eps | `1.61e-10` | `0.4087` | `1.02` | `4.73e-16` |
| 32 | A alpha=1 nominal eps | `0.00e+00` | `0.4010` | `1.00` | `0.00e+00` |
| 32 | B alpha=2 nominal eps | `9.82e-10` | `0.4017` | `1.00` | `0.00e+00` |
| 32 | C alpha=2 local eps | `9.82e-10` | `0.4017` | `1.00` | `0.00e+00` |

Regenerated:

- `paper/figures/ch13_v9_local_eps.pdf`
- `paper/figures/ch13_v9_ch14_stack_field.pdf`

### V10 CLS advection

Command:

```text
make cycle EXP=experiment/ch13/exp_V10_cls_advection_nonuniform.py
```

Status: PASS.

Summary:

Zalesak slotted disk:

| N | centroid error | volume drift | `V_T/V0` |
|---:|---:|---:|---:|
| 64 | `1.145e-02` | `2.811e-04` | `1.0003` |
| 128 | `4.911e-03` | `4.703e-06` | `1.0000` |

Centroid order: `1.22`.

Single-vortex reversal:

- N=128, alpha=1
- `L1_reverse = 2.248e-02`
- volume drift `4.281e-04`
- `V_T/V0 = 1.0004`
- Ridge-Eikonal reinitialization every 10 steps, 409 calls
- mass correction enabled every 10 steps
- grid rebuild disabled, 0 calls

Regenerated:

- `paper/figures/ch13_v10_zalesak.pdf`
- `paper/figures/ch13_v10_zalesak_snapshot.pdf`
- `paper/figures/ch13_v10_single_vortex.pdf`
- `paper/figures/ch13_v10_single_vortex_phase32.pdf`

## Final Validation

Completed:

```text
git diff --check
make -B -C paper
rg -n "^(LaTeX Warning|Package .*Warning|Class .*Warning|Overfull|Underfull|! |.*Error|Fatal|Undefined control sequence|LaTeX Error)" paper/main.log
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m py_compile \
  experiment/ch12/exp_U10_common_flux_ledger.py \
  experiment/ch13/exp_V11_common_flux_admissibility.py
PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH \
  make test-local PYTEST_ARGS='twophase/tests/test_common_flux_transport.py twophase/tests/test_ns_pipeline_fccd.py::test_ch14_rising_bubble_yaml_builds_solver -q'
```

Results:

- `git diff --check`: PASS
- paper build: PASS, `paper/main.pdf` rebuilt to 256 pages
- final log scan: no matches
- py_compile: PASS
- source test fallback: `633 passed, 33 skipped in 30.88s`

## Notes

- `make test-local` prepends `twophase/tests` in the Makefile, so the requested
  targeted paths expanded to the full CPU source suite.
- Experiment `.npz` and experiment-local PDFs are regenerable and ignored by
  `.gitignore`; paper-facing PDFs are tracked.
- No main merge was performed.

## SOLID-X

Experiment execution, experiment-script measurement correction, paper-facing
figure refresh, artifact, and ledger only.  Production solver source was not
refactored; no FD/WENO/PPE fallback, damping/CFL workaround, smoothing,
curvature cap, benchmark branch, blanket projection, or QP-as-physics path was
introduced.
