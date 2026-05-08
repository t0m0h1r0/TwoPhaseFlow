# CHK-RA-CH14-BUBBLE-HIST-001

## Purpose

Design and execute an efficient verification procedure for the current
rising-bubble RCA.  The goal is not to tune the run, but to falsify or support
the mathematical hypothesis:

```text
The blow-up is seeded by the interaction between a time-varying two-phase
rho dV kinetic-energy metric and an explicit IMEX-BDF2 convection history
extrapolate that is only single-phase/skew in an unweighted metric.
```

## Verification Strategy

The efficient strategy is a control-pair design:

```text
Control A: constant density + history lag
  -> should stay energy-neutral if history alone is not the cause.

Control B: variable density + zero history lag
  -> should stay energy-neutral if density variation alone is not the cause.

Test C: variable density + history lag
  -> should open the energy gate if the interaction is the cause.

Checkpoint replay:
  -> the same signature must appear in the actual rising-bubble states.
```

This is better than running another long bubble experiment because it directly
targets the theorem:

```text
P_pair = sum rho V u.C_h + sum 1/2 |u|^2 V rho_t
```

and the production history object:

```text
P_IMEX = sum rho V u.(2 C_h^n - C_h^{n-1})
       + sum 1/2 |u|^2 V rho_t^n.
```

## Artifacts

Reusable script:

```text
artifacts/A/ch14_transport_history_validation.py
```

Output directory:

```text
artifacts/A/ch14_transport_history_validation_CHK_RA_CH14_BUBBLE_HIST_001/
```

Files:

- `history_density_sweep.csv`
- `checkpoint_history_replay.csv`
- `history_validation_summary.json`
- `history_density_interaction_heatmap.pdf`
- `checkpoint_history_replay.pdf`

## Manufactured Controls

Periodic manufactured divergence-free field, UCCD6, `N=32`:

```text
case                              paired_rate   imex_rate    imex-current
constant density, 1-cell lag      -2.828e-07   -2.882e-07   -5.434e-09
rho ratio 833, zero lag           -2.828e-07   -2.828e-07    0.000e+00
rho ratio 833, 0.25-cell lag      -2.828e-07   +7.589e-03   +7.589e-03
rho ratio 833, 1-cell lag         -2.828e-07   +3.052e-02   +3.052e-02
rho ratio 100, 1-cell lag         -2.828e-07   +2.999e-02   +2.999e-02
rho ratio 10, 1-cell lag          -2.828e-07   +2.503e-02   +2.503e-02
```

Interpretation:

- History lag alone does not create appreciable physical kinetic-energy work.
- Variable density alone does not create appreciable physical kinetic-energy
  work for the smooth manufactured field.
- Variable density and history lag together open the energy gate by `O(1e-2)`
  normalized rate.

This strongly supports the interaction hypothesis and rejects the simpler
single-factor hypotheses.

## Checkpoint Replay

Actual rising-bubble checkpoints:

```text
case                         dt          KE         conv_n      conv_prev    IMEX        linear dE with 2/3 dt
stable_pre_step_t0p009995    7.361e-06   5.931e-05  +1.515e-04  -1.479e-03  +1.782e-03  +8.744e-09
stable_post_step_t0p01       0.000e+00   5.936e-05  +1.508e-04  -1.484e-03  +1.786e-03   0.000e+00
pre_blowup_t0p018033         1.723e-09   8.839e+05  -1.410e+13  +1.286e+15  -1.314e+15  -1.510e+06
```

Interpretation:

- At the stable pre-step, the production IMEX history term is already positive.
- The one-step linear increment is small relative to KE, so the claim is not
  "one step explodes the run".  The claim is that the method admits a positive
  energy channel that can be repeatedly fed by capillary/buoyancy/interface
  motion and then amplified by non-normal pressure/viscous/history coupling.
- At pre-blow-up the current convection and pressure are already damping the
  runaway mode.  Terminal sign checks therefore identify symptoms, not cause.

## Hypothesis Decisions

### Rejected: history alone

Constant density with a full-cell history lag remains neutral:

```text
imex-current = -5.434e-09
```

### Rejected: variable density alone

Density ratio `833` with zero lag remains neutral:

```text
imex-current = 0
```

### Supported: variable density metric plus history lag

Density ratio `833` with a quarter-cell lag gives:

```text
imex-current = +7.589e-03
```

With one-cell lag:

```text
imex-current = +3.052e-02
```

### Supported: actual production checkpoint has the same sign before blow-up

The `t~=0.01` pre-step has:

```text
conv_n      = +1.515e-04
conv_prev   = -1.479e-03
IMEX        = +1.782e-03
```

This is the same mechanism as the manufactured interaction test.

## Root-Cause Refinement

The root cause is now more precise:

```text
The production explicit convection history uses velocity-space history
C^{n-1} but pairs it with the current density metric rho^n dV.  In two-phase
flow, rho^n changes with the interface, so the previous skew operator is not
skew in the current inner product.  The IMEX-BDF2 extrapolate therefore has no
two-phase energy estimate, even when C^n itself is nearly neutral.
```

This explains why:

- constant-density manufactured tests pass;
- variable-density zero-history tests pass;
- variable-density history-lag tests fail;
- the rising-bubble run looks plausible early but later develops a runaway
  history mode;
- terminal pressure and current convection can be damping while the run still
  already contains catastrophic kinetic energy.

## Next Efficient Verification

The next best test is still offline before any production implementation:

```text
Construct a candidate mass-compatible momentum transport/history form and run
the exact same controls:

1. constant density + history lag;
2. variable density + zero lag;
3. variable density + history lag;
4. rising-bubble checkpoint replay.
```

The candidate is promising only if it closes all four gates without damping,
clipping, fallback, or benchmark-specific logic.

