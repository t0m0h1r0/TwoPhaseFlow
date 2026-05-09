# CHK-RA-CH14-PERIODIC-WALL-QUOTIENT-001

## Scope

This checkpoint records the periodic-wall quotient formulation, the passive
time-checkpoint correction, and the N=32 x 64 rising-bubble smoke experiment
with periodic horizontal boundaries and wall vertical boundaries.

## Periodic-Wall Quotient Theory

The earlier full-array periodic-wall pressure representation made periodic
terminal nodes independent unknowns.  The resulting Hodge/PPE gate could fail
even when the physical topology was admissible, because the algebraic space was
larger than the quotient manifold on which periodic endpoints are identical.

The corrected representation uses quotient pressure unknowns:

```text
p_Q in Q_h,
E_Q : Q_h -> P_h  (periodic extension),
R_Q : P_h -> Q_h  (unique representative restriction),
E_F : F_Q -> F_h  (periodic face-image extension),
D_per = R_Q D_h E_F,
G_w = P_w G_A E_Q,
K_w = D_per G_w.
```

The pressure inner product folds image control volumes into the unique
representative rows.  Tangential periodic face image planes are synchronized
before applying the wall trace projection and again after it.  With the same
mass metric, the discrete Green identity closes on the quotient space:

```text
<G_w p_Q, u_Q>_M + <p_Q, D_per u_Q>_W = O(roundoff).
```

The rank gate therefore tests the quotient operator, not the unreduced full
node array.  The manufactured probe that previously failed on the full
representation passed after the quotient restriction:

```text
full pressure rows:     rank 27 / 30
quotient pressure rows: rank 25 / 25
Green identity relative residual: ~1.3e-16
```

This is not a fallback or benchmark-specific branch.  It is the discrete
topology required by the periodic boundary condition.

## Passive Time Checkpoints

The time-checkpoint path used to clamp `dt` to hit `checkpoint_interval`
exactly:

```text
dt <- min(dt, checkpoint_target - t)
```

That makes output scheduling part of the discrete flow map.  A large PPE RHS
immediately after a checkpoint is therefore a real implementation bug when it
is caused by the checkpoint cadence: changing I/O frequency changes the
physical timestep sequence and can perturb pressure compatibility.

The corrected rule is observational:

```text
time checkpoint = last pre-step continuation frame whose accepted step crossed target time
```

The checkpoint writer does not change `dt`, does not recapture a post-step
state as a restart input, and only records the state that was actually used to
advance the crossing step.  The regression
`test_time_checkpoints_do_not_clamp_discrete_timestep` fixes the contract with
a manufactured fixed-dt run:

```text
T = 0.8, dt_fixed = 0.2, checkpoint_interval = 0.5
accepted dt sequence = [0.2, 0.2, 0.2, 0.2]
checkpoint_t0p5 stores pre-step t = 0.4
```

The spike immediately after the `t=0.005` checkpoint disappeared under this
passive policy.  Remaining non-checkpoint PPE RHS peaks are separate physical
or discretization events and must not be attributed to checkpoint I/O without a
separate one-step or manufactured probe.

## N=32 x 64 Periodic-Wall Experiment

Run:

```text
config: _tmp_ch14_rising_bubble_periodic_wall_n32x64_t003
canonical YAML updated: experiment/ch14/config/ch14_rising_bubble.yaml
domain: x periodic, y lower/upper wall
grid: 32 x 64
T: 0.01 s
checkpoints: 0.005, 0.010
result directory:
experiment/ch14/results/_tmp_ch14_rising_bubble_periodic_wall_n32x64_t001_continuous_passive_checkpoint
```

Key measurements:

```text
time samples: 1415
last time: 0.01
volume drift max: 4.696675e-06
centroid y at final samples: 5.339477e-03
mean rise velocity max/final: 6.572085e-02
deformation final: 3.166143e-01
max div_u: 7.005216e-07 at first step
max ppe_rhs: 3.010261e+06 at first step
x-periodic final gaps: psi=0, u=0, v=0
```

Generated plots:

```text
bubble_centroid_y.pdf
deformation.pdf
mean_rise_velocity.pdf
volume_drift.pdf
psi_t0.000.pdf, psi_t0.005.pdf, psi_t0.010.pdf
velocity_t0.000.pdf, velocity_t0.005.pdf, velocity_t0.010.pdf
pressure_t0.000.pdf, pressure_t0.005.pdf, pressure_t0.010.pdf
```

## Validation

```text
pytest boundary/config/runner targeted set: 17 passed
git diff --check: pass
make -C paper: pass, main.pdf rebuilt to 259 pages
paper/main.log warning/error/undefined/overfull/underfull scan: no matches
```

## Negative Knowledge

- Do not represent periodic endpoints as independent pressure rows in the
  rank/Hodge gate.
- Do not make checkpoint cadence alter `dt`.
- Do not classify all PPE RHS peaks near checkpoint output as I/O bugs; only
  the checkpoint-induced step split is ruled out here.
