# CHK-RA-CH12-13-EXPPREP-001 - Chapter 12--13 experiment preparation

Date: 2026-05-09

Base branch/worktree: `codex/ra-ch12-13-exp-audit-main-20260509` at latest-main
worktree `.claude/worktrees/codex-ra-ch12-13-exp-audit-main-20260509`.

Parallel review branch remains intentionally ignored.

## Prepared Experiment Entrypoints

1. `experiment/ch12/exp_U10_common_flux_ledger.py`
   - Chapter 12 component gate for the common phase/mass/momentum flux ledger.
   - Uses `twophase.tools.experiment` infrastructure and writes
     `experiment/ch12/results/U10_common_flux_ledger/data.npz`.
   - Produces `U10_common_flux_ledger.pdf` and the matching paper figure
     `paper/figures/ch12_u10_common_flux_ledger.pdf`.
   - Positive checks: closed FCCD common-flux candidate, affine density,
     mass/momentum conservation, non-increasing kinetic-energy certificate.
   - Negative checks: non-affine density and q-only projected ledger are
     rejected, not accepted as alternate transport routes.

2. `experiment/ch13/exp_V11_common_flux_admissibility.py`
   - Chapter 13 integration/admissibility gate for
     `momentum_form: conservative_common_flux`.
   - Starts from `experiment/ch14/config/ch14_rising_bubble.yaml` and writes a
     reduced runtime config under
     `experiment/ch13/results/V11_common_flux_admissibility/`.
   - Uses grid `[16, 32]`, fixed `dt=1e-6`, and two steps for the gate only;
     this is not a physical rising-bubble benchmark.
   - Positive checks: solver route, disabled reinit/remap, common FCCD ledger,
     conservative density/momentum fields, affine density closure,
     common-flux energy certificate, and checkpoint roundtrip.
   - Negative checks: q-only reinitialization and dynamic grid remap fail
     closed in conservative mode.

## Remote-First Run Order

Fast preparation gates first:

```text
make cycle EXP=experiment/ch12/exp_U10_common_flux_ledger.py
make cycle EXP=experiment/ch13/exp_V11_common_flux_admissibility.py
```

Latest-main affected reruns next:

```text
make cycle EXP=experiment/ch13/exp_V3_static_droplet_longterm.py
make cycle EXP=experiment/ch13/exp_V6_density_ratio_convergence.py
make cycle EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py
make cycle EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py
make cycle EXP=experiment/ch13/exp_V10_cls_advection_nonuniform.py
```

Do not rerun V1/V2/V4/V5/V8 or U1--U9 unless these gates expose a shared
regression.

## Validation After Runs

After the gates and reruns complete:

```text
git diff --check
make test
make -B -C paper
rg -n "^(LaTeX Warning|Package .*Warning|Class .*Warning|Overfull|Underfull|! |.*Error|Fatal|Undefined control sequence|LaTeX Error)" paper/main.log
```

If U10/V11 figures are promoted into the paper, add the corresponding Chapter
12/13 TeX updates in a separate paper-sync checkpoint.

## Preparation Validation

Completed in this checkpoint:

```text
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m py_compile \
  experiment/ch12/exp_U10_common_flux_ledger.py \
  experiment/ch13/exp_V11_common_flux_admissibility.py

PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH \
  make run-local EXP=experiment/ch12/exp_U10_common_flux_ledger.py ARGS=--help

PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH \
  make run-local EXP=experiment/ch13/exp_V11_common_flux_admissibility.py ARGS=--help

PATH=/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin:$PATH \
  make test-local PYTEST_ARGS='twophase/tests/test_common_flux_transport.py twophase/tests/test_ns_pipeline_fccd.py::test_ch14_rising_bubble_yaml_builds_solver -q'
```

Notes:

- `make test` could not reach the remote from this session and fell back to
  local, where the Makefile expected `python` on PATH.  The same test was then
  rerun with the repo venv on PATH.
- Because `test-local` prepends `twophase/tests` in the Makefile, the CPU
  fallback executed the full source suite, not only the two targeted paths.
- Result: `633 passed, 33 skipped in 32.42s`.
- `git diff --check` passed.
- U10/V11 experiment bodies were not executed in this preparation checkpoint;
  use the `make cycle` commands above for official remote-first runs.

## SOLID-X

Experiment entrypoints and preparation artifact only.  The production solver
source was not refactored; no FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection, or
QP-as-physics path was introduced.
