# CHK-RA-CH12-13-EXPRECHECK-001 - Chapter 12--13 experiment recheck after Chapter 1--11 updates

Date: 2026-05-09

Branch/worktree:

```text
codex/ra-ch12-13-exp-recheck-20260509
.claude/worktrees/codex-ra-ch12-13-exp-recheck-20260509
```

Base inspected: local `main` at `381e0b45` plus this audit branch.  A fetch of
`origin/main` returned `69d87435`; local `main` is ahead by 36 commits and
contains the Chapter 1--11 review merge, the Chapter 12--13 experiment refresh,
and the later Chapter 14 pressure/face-state updates.  Therefore local `main`,
not stale `origin/main`, is the correct audit base.

Scope correction after user review: V11 is not required as a Chapter 12--13
rerun.  Its positive route is the Chapter 14 rising-bubble YAML, so it belongs
to Chapter 14 preflight/admissibility work when that chapter is being advanced.
This artifact keeps the V11 evidence as rationale for Chapter 13 text cleanup,
but removes V11 from the required Chapter 12--13 execution set.

## Verdict

Additional/update/rerun work is required, but not a blanket rerun.

The previous Chapter 12--13 experiment refresh already handled the first
Chapter 1--11 common-flux propagation by adding U10 and a V11 admissibility
script, and by rerunning
V3/V6/V7/V9/V10.  The current local-main state adds a stricter Chapter 9
pressure/face-state contract after that refresh:

- wall admissible face space `F_w = ker(B_w R_h)`;
- restricted pressure operator/rank gates `D_h P_w G_A`;
- periodic-wall quotient pressure/face topology;
- variational gravity tied to conservative common-flux transport;
- pressure-coordinate history and passive time checkpoints;
- corrected `ppe_rhs_max` diagnostic contract.

Those changes do not invalidate every existing U/V number.  They do require
targeted new evidence and targeted reruns for the experiments that either
consume the canonical Chapter 14 rising-bubble route or exercise the changed
`TwoPhaseNSSolver` pressure/face-state path.

## Evidence Checked

1. Since the previous Chapter 12--13 experiment merge `6a236e74`, the only
   Chapter 1--11 paper file changed is `paper/sections/09b_split_ppe.tex`.  It
   adds constrained face-state, wall retraction, restricted pressure/rank, and
   periodic-wall quotient theory.
2. Since `6a236e74`, `experiment/ch12` and `experiment/ch13` scripts did not
   change.  Source changes are concentrated in shared solver/config/runtime
   files such as `ns_step_services.py`, `ns_pipeline.py`, `checkpoint.py`,
   `runner.py`, config parsers, `gravity_covector.py`, and `boundary_hodge.py`.
3. `experiment/ch13/exp_V11_common_flux_admissibility.py` builds its positive
   gate from `experiment/ch14/config/ch14_rising_bubble.yaml`.  Because that
   route is Chapter 14-specific, the changed YAML is evidence for deferring V11
   to Chapter 14 preflight, not for requiring a Chapter 13 rerun in this task.
4. `paper/sections/12*.tex` and `paper/sections/13*.tex` still contain no
   `U10`, `V11`, `common-flux ledger`, or `conservative common-flux
   admissibility` text.  The scripts and paper-facing PDFs exist, but the
   chapters still present U1--U9 and V1--V10 as the full bridge.
5. V6/V7/V9 use `TwoPhaseNSSolver` through `experiment/ch13/ch14_stack_common.py`
   or a local equivalent and exercise the pressure-jump/face-projection path
   touched by the new pressure history, RHS diagnostic, and boundary-Hodge
   plumbing.  V3 standalone CSF/BF, V10 passive CLS advection, and V1/V2/V4/V5/V8
   do not consume the modified runtime paths in the same way.

## Required Plan

### R1 - Update Chapter 12 paper integration for U10

The experiment and figure already exist:

```text
experiment/ch12/exp_U10_common_flux_ledger.py
paper/figures/ch12_u10_common_flux_ledger.pdf
```

Required update:

- add `paper/sections/12u10_common_flux_ledger.tex`;
- update `12_component_verification.tex` from U1--U9 to U1--U10;
- update `12h_summary.tex` tables and the U-to-V bridge;
- keep U10 as a component/common-flux ledger gate, not a physical benchmark.

No U10 rerun is required unless the script or `ConservativeCommonFluxTransport`
/ `FCCDLevelSetAdvection` changes during the update.

### R2 - Add a Chapter 12 constrained face-state component gate

Add a new component experiment, tentatively:

```text
experiment/ch12/exp_U11_constrained_face_state_space.py
paper/figures/ch12_u11_constrained_face_state_space.pdf
```

Acceptance metrics:

- `P_w` idempotence in the transported face metric;
- `P_w` metric self-adjointness;
- `C_w P_w = 0` for wall and x-periodic/y-wall small grids;
- restricted Green identity for `G_w = P_w G_A` or the quotient version
  `G_w = P_w G_A E_Q`;
- rank gate on `D_h P_w G_A` for full-wall and `D_per P_w G_A E_Q` for
  periodic-wall quotient probes;
- negative controls: nodal post-clamp and full-array periodic endpoints must
  not be accepted as equivalent.

This is the component evidence now missing from Chapter 12 after the Chapter 9
state-space theory update.  It should reuse the existing boundary-Hodge helper
APIs and small manufactured probes.  It must not enable a production restricted
PPE solver unless the rank/manufactured gates pass.

### R3 - Rerun only V6/V7/V9 for shared pressure/face-state runtime drift

These experiments exercise the changed `TwoPhaseNSSolver` pressure-jump and
face-projection path.  Rerun them after R2 code/script updates:

```text
make cycle EXP=experiment/ch13/exp_V6_density_ratio_convergence.py
make cycle EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py
make cycle EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py
```

Refresh paper-facing PDFs only if the generated figures or metrics change.
When updating text, describe V6/V7/V9 as the existing pressure-jump/HFE
integration set and keep constrained face-state evidence separate unless the
new U11 gate has actually passed.

### R4 - Update Chapter 13 paper integration

Required update:

- keep V-series overview and accuracy-summary tables as V1--V10 for Chapter 13;
- state that V6/V7/V9 cover the current pressure-jump/HFE integration route;
- add a short note that constrained face-state/periodic-wall rank evidence is
  component evidence in U11 and full physical periodic-wall rising-bubble
  response, including any V11-style canonical-route preflight, remains Chapter
  14.

### R5 - Validation

After implementation/reruns:

```text
git diff --check
make -B -C paper
rg -n "^(LaTeX Warning|Package .*Warning|Class .*Warning|Overfull|Underfull|! |.*Error|Fatal|Undefined control sequence|LaTeX Error)" paper/main.log
```

For script additions:

```text
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m py_compile \
  experiment/ch12/exp_U11_constrained_face_state_space.py
```

Remote-first execution remains the project default.  Use local fallback only if
the remote wrapper is unavailable and record the fallback reason.

## Work Not Required

- No blanket rerun of U1--U9: their primitive implementations are not touched
  by the post-refresh local-main diff.
- No U10 rerun unless its script or direct transport dependencies change.
- No V1/V2/V4/V5/V8 rerun: their target kernels do not consume the changed
  pressure-coordinate, variational-gravity, boundary-Hodge, or canonical
  rising-bubble route.
- No V10 rerun: post-`6a236e74` changes do not touch
  `FCCDLevelSetAdvection`, `Reinitializer`, or the passive CLS advection logic
  used by V10.
- No V11 Chapter 13 rerun: its positive route is the Chapter 14 rising-bubble
  route, so any update belongs to Chapter 14 preflight/admissibility work.
- No Chapter 13 full physical periodic-wall benchmark: the N=32 x 64
  periodic-wall rising-bubble response is Chapter 14 evidence.  Chapter 12--13
  should add the theorem/admissibility evidence, not duplicate the benchmark.
- No conservative-mode retrofit of V6/V7/V9 until conservative `(q,m,p)`
  reinitialization/remap and the constrained pressure state-space production
  solve are available.

## SOLID-X

Audit/plan artifact only.  No solver source, experiment script/config/result,
paper prose, tested implementation, FD/WENO/PPE fallback, damping/CFL
workaround, smoothing, curvature cap, benchmark branch, blanket projection, or
QP-as-physics path changed in this checkpoint.
