# CHK-RA-CH14-AO-FASTVOL-028 - Blow-up-assumed AO experiment strategy

## Purpose

User request:

> 効率よく実験を進める方法を検討して。ブローアップが起きる前提で、できるだけ手戻りの少ないやり方を考えて。

This note defines the experiment workflow after CHK-027.  The goal is not to
hide blow-ups.  The goal is to make each expected failure classify exactly one
missing contract, so the next implementation step is obvious and long runs are
not used as discovery tools.

## Core Principle

Treat blow-up as a terminal symptom, not as the experiment target.  The
efficient ladder is:

```text
algebraic certificate
  -> one-step impulse
  -> two-step pressure-history replay
  -> short horizon
  -> fractional-period horizon
```

Only advance to the next rung if the previous rung passes its exact invariant
gates.  A failed gate records a compact artifact and stops; it does not launch
a longer run.

## Failure Taxonomy

| Code | First failing signal | Interpretation | Next action |
|---|---|---|---|
| G1 | `q != Q_h(phi)` above tolerance | phase and geometry are incompatible | implement/repair compatibility projection before capillarity |
| G2 | active Schur residual/Young-Laplace normal residual above tolerance | pressure split is uncertified | implement/repair active Schur PCG/Newton/DC certification |
| G3 | `capillary_drive_present` with zero balanced drive | non-static capillary residual is being deleted | implement residual lifted drive `-e[L_B(w)]` |
| G4 | `pressure_coordinate` requested but no scalar `p_sigma` | undefined pressure history | implement scalar AO pressure coordinate storage/extrapolation |
| H1 | one-step finite, two-step `ppe_rhs` jumps | history/extrapolation defect | replay from step-1 pre-step checkpoint and compare scalar vs face history |
| H2 | algebra/history pass, short horizon `div_u` grows with `ppe_rhs` | pressure/PPE coupling defect | inspect PPE RHS decomposition and pressure adjoint pairing |
| H3 | residuals pass, `dt_adv` collapses after KE growth | momentum/time-integration coupling defect | replay pre-blowup frame with term budgets |
| H4 | only long horizon fails after all short gates | accumulated projection/work drift | inspect q/phi work ledger and active-set epoch history |

This table prevents repeating the same expensive 1/4-period experiment when
the first failure is already algebraic.

## Rung 0 - Static And Algebraic Smoke

Run before any time integration:

```text
flat interface, sigma=0
flat interface, sigma>0
static droplet / certified Young-Laplace state
capillary-wave initial geometry
```

Required outputs:

```text
compat_linf
active_rank_status
schur_residual_norm
young_laplace_normal_residual_linf
pressure_exact_static
predictor_l2
balanced_l2
max_abs_balanced_face_increment
p_sigma_gauge_status
```

Pass rules:

```text
static states:
  normal residual <= tolerance,
  pressure_exact_static=True,
  balanced_l2 <= tolerance.

capillary-wave initial state:
  compatibility <= tolerance,
  Schur residual certified by declared tolerance,
  p_sigma exists if pressure_coordinate is selected,
  balanced_l2 > mode floor.
```

The mode floor should be derived from the linear capillary-wave oracle or, for
the first implementation pass, from the exact active residual norm.  It must
not be a tuned stabilizer.

## Rung 1 - One-Step Capillary Impulse

Purpose: verify that the non-static capillary split injects the right impulse
before pressure history can contaminate the run.

Run one step from rest with:

```text
debug.step_diagnostics=true
checkpoint final disabled unless the input frame is needed
```

Required checks:

```text
balanced_l2 nonzero for capillary wave
KE growth = O(dt^2 ||balanced||^2_M)
ppe_rhs remains finite and consistent with the projected face drive
div_u after correction remains below the configured pressure tolerance scale
q volume drift remains roundoff-scale
```

If this fails, do not run two steps.  The bug is in capillary packet assembly,
face Hodge/Riesz representation, or PPE coupling inside the first step.

## Rung 2 - Two-Step Pressure-History Replay

Purpose: isolate `pressure_coordinate` without waiting for long-time blow-up.

Procedure:

1. Run one accepted step and save the pre-step continuation frame.
2. Replay the second step under the same physical state with:
   - certified scalar `p_sigma` pressure-coordinate history,
   - diagnostic face-acceleration history,
   - no-history control if available as an explicit diagnostic mode.
3. Compare only diagnostics, not trajectories.

Required outputs:

```text
||T^T p_sigma - pressure_reaction_face||_{M_f^{-1}}
pressure_extrapolated_base_norm
ppe_rhs_max
div_u_max
KE ratio over step 1
```

Pass rule:

```text
scalar pressure-coordinate and regenerated face reaction agree within the
Schur residual error bound from CHK-027.
```

If step 2 fails but step 1 passed, the next task is pressure-history storage
or extrapolation, not capillary geometry.

## Rung 3 - Short Horizon Ladder

Do not jump to 1/4 period.  Use a doubling ladder:

```text
steps: 1, 2, 5, 10
time:  T/256, T/128, T/64, T/32, T/16, T/8, T/4
```

Advance only when the previous rung passes.  Store a compact CSV/NPZ summary
for each rung with the same columns as `diagnose_ao_gpu_theory_probe.py`, plus:

```text
schur_residual_norm
p_sigma_norm
balanced_drive_error_bound
active_cell_count
active_epoch
projection_work_delta
dt_limiter
dt_adv/dt_cap/dt_visc
```

Stop early if any sentinel triggers:

```text
NaN/Inf in any primary field,
fail-close contract error,
ppe_rhs grows by >= 1e4 over its initial accepted baseline,
div_u grows by >= 1e4 over its initial accepted baseline,
KE grows by >= 1e6 over one step without corresponding capillary work ledger,
dt_adv collapses by >= 1e2 while capillary/PPE residuals are growing.
```

These are experiment sentinels, not numerical fixes.  They exist to save the
pre-failure state before the normal kinetic-energy blow-up guard is reached.

## Rung 4 - Pre-Blowup Replay

For any horizon blow-up, use the existing runner behavior:

```text
checkpoint_pre_blowup_input.npz
```

as the next RCA input.  Replay exactly one step from that pre-step frame with
extra term budgets.  Do not rerun from `t=0` until the replay identifies the
first broken invariant.

The replay should decompose:

```text
capillary predictor face work
pressure reaction face work
balanced drive work
PPE RHS components
pressure correction work
convection/viscosity contribution
q/phi compatibility change
active-set epoch change
```

If the replay is not reproducible from the checkpoint, fix checkpoint/runtime
state first.  Otherwise every long-run conclusion is suspect.

## Minimal Command Pattern

Use remote-first commands, but keep each run small:

```text
make test PYTEST_ARGS="twophase/tests/test_config_state_space.py -k geometric_runtime_gpu_backend -q"

make run EXP=experiment/ch14/diagnose_ao_gpu_theory_probe.py \
  ARGS="--config <ao_capillary_probe> --steps 1"

make run EXP=experiment/ch14/diagnose_ao_gpu_theory_probe.py \
  ARGS="--config <ao_capillary_probe> --steps 2"

make cycle EXP=experiment/run.py \
  ARGS="--config <ao_capillary_probe> --final-time <T/64> \
        --checkpoint-every-steps 20 --no-checkpoint-final"
```

After code changes, use `make cycle` for the first validation so the remote
state and local source remain synchronized.  For repeated no-code diagnostic
runs, prefer `make run` after one successful push.

## Experiment Matrix

Keep the matrix small and orthogonal:

```text
Geometry:
  flat, static droplet, capillary wave

Pressure split:
  exact/active Schur candidate,
  diagonal Schur expected fail-close,
  dense oracle only in test/debug

History:
  scalar pressure_coordinate,
  face_acceleration diagnostic,
  no-history diagnostic where explicitly supported

Time horizon:
  1 step, 2 steps, T/64, T/16, T/4
```

Do not combine two unproven changes in the same run.  For example, do not test
new DC acceleration and new pressure history simultaneously.  First certify the
Schur split, then history, then acceleration.

## Commit Cadence

Use one commit per rung:

```text
1. algebraic probe + expected fail/pass tests
2. active Schur pressure-coordinate implementation
3. one-step impulse validation artifact
4. two-step history validation artifact
5. short-horizon ladder artifact
6. 1/4-period run only after all earlier artifacts pass
```

This preserves bisectability.  A later blow-up can be traced to the first rung
whose invariant changed, rather than to a large mixed commit.

## Immediate Next Step

The next efficient implementation task is not a 1/4-period rerun.  It is an
algebraic/non-time-integrating probe that materializes the AO capillary packet
and checks the CHK-027 Schur split:

```text
build J_q, g=sigma dS_h, W^{-1} action,
solve or oracle-check S pi = -J_q W^{-1}g,
compute e=g+J_q^Tpi,
construct balanced_drive=-e[L_B(w)],
record p_sigma gauge,
fail if the residual error bound is not certified.
```

Only after this passes should the fail-close gate be relaxed for the certified
path.
