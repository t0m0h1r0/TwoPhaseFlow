# CHK-RA-CH14-BUBBLE-BLOWUP-RCA-002: rising-bubble blow-up root-cause analysis

## Question

The 10 mm x 20 mm, 32 x 64 water-air rising-bubble run is stable to
`T=0.01`, but the continuation toward `T=0.02` fails at

```text
step = 2470
t    = 0.018033000472938543
```

This note records a theory-first root-cause analysis.  It is not a tuning
proposal.  Damping, smoothing, curvature caps, CFL weakening, benchmark
branches, FD/WENO/PPE fallbacks, and ad hoc pressure filtering are not valid
solutions.

## Data Used

```text
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t002_resume/data.npz
experiment/ch14/results/_tmp_ch14_rising_bubble_n32_t002_resume/checkpoint_pre_blowup_input.npz
experiment/ch14/config/_tmp_ch14_rising_bubble_n32_t002_resume.yaml
```

The run used the current production Chapter 14 rising-bubble stack with
`momentum_form: primitive_velocity`.

## Physical Scale Check

For the configured bubble diameter `D=5 mm`, radius `R=2.5 mm`:

```text
Eo = (rho_l-rho_g) g D^2 / sigma = 3.402
Bo_R = (rho_l-rho_g) g R^2 / sigma = 0.851
t_sigma = sqrt(rho_l R^3 / sigma) = 1.473e-02 s
U_sigma = R / t_sigma = 1.697e-01 m/s
sqrt(gD) = 2.215e-01 m/s
Delta p_hydrostatic over 20 mm = 1.960e+02 Pa
Delta p_laplace = sigma/R = 2.880e+01 Pa
```

At the pre-blowup input frame:

```text
max speed        = 1.559372e+04 m/s
max |pressure|   = 1.946613e+11 Pa
speed/sqrt(gD)   = 7.04e+04
pressure/hydro   = 9.93e+08
pressure/Laplace = 6.76e+09
```

Therefore the failure is not physical bubble rise, physical capillary
oscillation, or a real water-air transient.  It is a discrete numerical mode.

## Observed Failure Signature

The final diagnostic values were:

```text
volume_conservation_final     4.436782e-03
mean_rise_velocity_final      5.770133e-01
kinetic_energy_final          1.745169e+06
div_u_max_final               4.953264e-01
kappa_max_final               2.716322e+03
ppe_rhs_max_final             4.829943e+16
bf_residual_max_final         4.707965e+14
dt_advective_final            1.723328e-09
dt_capillary_final            7.248600e-06
capillary_contract_gate_code  0
```

The kinetic energy crossed thresholds very late and very abruptly:

```text
KE > 1e-3 at t=0.018002600052937603
KE > 1e-2 at t=0.018017042196463183
KE > 1e-1 at t=0.018028937729434900
KE > 1    at t=0.018030835407344643
KE > 1e3  at t=0.018032888628203823
```

The last eight recorded steps show collapse of the advective scale and
explosion of the pressure/balanced-force residuals:

```text
t             KE          dt_adv      ppe_rhs      bf_res      div_u
0.018032954   9.875e+03   2.551e-08   2.181e+14   2.227e+12   6.015e-02
0.018032970   2.246e+04   1.630e-08   5.256e+14   5.387e+12   4.072e-02
0.018032981   5.083e+04   1.078e-08   1.213e+15   1.225e+13   1.431e-01
0.018032988   1.079e+05   7.184e-09   2.715e+15   2.734e+13   1.004e-01
0.018032993   2.240e+05   4.919e-09   5.814e+15   5.767e+13   1.328e-01
0.018032996   4.587e+05   3.423e-09   1.211e+16   1.199e+14   2.299e-01
0.018032999   8.839e+05   2.386e-09   2.456e+16   2.414e+14   2.975e-01
0.018033000   1.745e+06   1.723e-09   4.830e+16   4.708e+14   4.953e-01
```

The pre-blowup velocity mode is localized in the interface band and is
left-right symmetric:

```text
max speed index      = (23, 21)
x,y                  = (0.00692914648, 0.00550572121)
psi                  = 7.452546e-02
rho                  = 7.563603e+01
u,v                  = (1.559372e+04, -8.985279)

mirror point         = (9, 21)
u,v                  = (-1.559372e+04, -8.985279)
```

The spectral/index-space check is decisive:

```text
snapshot t=0.0175:
  speed_max               = 4.896838e-01
  high-k energy fraction  = 1.321310e-03
  Nyquist energy fraction = 2.152254e-04

pre-blowup:
  speed_max               = 1.559372e+04
  high-k energy fraction  = 9.999117e-01
  Nyquist energy fraction = 9.991236e-01
  u sign flip in y-band   = 1.0
```

Thus the proximate failure is a grid-scale, near-Nyquist horizontal velocity
mode concentrated on the interface.  It is not a smooth buoyant rise.

## Hypotheses and Checks

### H01: Real physical bubble rise

Rejected.  The pre-blowup speed is `7.0e4` times `sqrt(gD)`, and pressure is
`~1e9` times the hydrostatic scale.  This is not a physical water-air state.

### H02: Capillary CFL too large

Rejected as primary cause.  `dt_capillary` stays bounded and smooth:

```text
7.071088e-06 <= dt_capillary <= 7.377619e-06
```

The time-step collapse is advective:

```text
dt_advective -> 1.723328e-09
```

This happens after the velocity mode appears.  Reducing CFL might postpone the
symptom, but it would not restore the missing discrete energy law.

### H03: PPE linear solve failure

Rejected as primary cause.  The RHS becomes enormous, but the reported
defect-correction relative residual remains small:

```text
ppe_dc_final_relative_l2_final = 2.669801e-09
ppe_dc_final_relative_l2_max   = 1.673501e-07
```

The PPE is solving a bad discrete right-hand side; it is not obviously failing
to solve the system it was given.

### H04: Phase topology or pressure-gauge singularity

Rejected as primary cause.  The pressure phase topology counters stay fixed:

```text
ppe_phase_count = 1
ppe_pin_count   = 1
```

There is no sudden component count or gauge-change event at the blow-up.

### H05: Restart/checkpoint corruption

Rejected for this run.  Restarting from `checkpoint_final.npz` was correctly
rejected because it is a post-step analysis artifact.  Restarting from
`checkpoint_continuation.npz` was accepted as a pre-step frame:

```text
step=1358, t=0.0099952543, phase=pre_step
```

The failure then develops dynamically after restart.  It is not a load of the
wrong terminal frame.

### H06: Pressure visualization artifact

Rejected.  The earlier `pressure_hodge` fail-close was a plotting theorem
gate.  The current blow-up is present in the saved velocity, pressure,
kinetic-energy, PPE-RHS, and face-history arrays themselves.

### H07: Reinitialization moves the zero set catastrophically

Rejected as sole cause.  Reinitialization diagnostics remain geometrically
small compared with grid spacing:

```text
max zero-level displacement = 1.963148e-05
h_min ~= 2.08e-04
volume delta per reinit <= 1e-10
```

However, `reinit_linf_delta` grows during the last unstable steps:

```text
0.0031 at t=0.017995
0.0192 at t=0.018024
0.0353 at t=0.018033
```

This suggests reinitialization/profile projection may feed the density/profile
part of the instability, but it is not the geometric trigger by itself.

### H08: Closed-interface capillary contract failure

Rejected as the direct trigger.  The capillary contract gate code remains zero:

```text
capillary_contract_failed_gate_code = 0
capillary_contract_pressure_adjoint_residual ~= 0.35, stable
```

The component-Hodge residual magnitude is also bounded:

```text
capillary_component_hodge_linf ~= O(1)
```

Therefore the specific closed-interface Riesz gate is not what trips.

### H09: Full affine pressure face cochain explosion

Supported as a proximate feedback channel.  The face cochain diagnostics show
that the full pressure/history cochain becomes enormous:

```text
capillary_face_linf:
  3.198e+03 at t=0.017649
  2.608e+04 at t=0.018003
  1.542e+05 at t=0.018024
  2.577e+09 at t=0.018032889
  3.292e+12 at t=0.018033000

capillary_face_divergence_linf:
  3.197e+06 at t=0.017649
  2.227e+08 at t=0.018003
  1.436e+09 at t=0.018024
  2.470e+13 at t=0.018032889
  3.190e+16 at t=0.018033000
```

By contrast, the pressure-range/Hodge residual diagnostics stay modest.  This
means the pressure reaction range is exploding in response to the unstable
velocity/transport state.  The face-history IPC path then feeds this large
cochain into the next RHS through `D_f a_p^n`.

### H10: Balanced buoyancy decomposition fails as the first cause

Not primary, but strongly coupled.  The diagnostic named `bf_residual_max`
records the mismatch between pressure acceleration and force acceleration at
the corrector stage.  It stays moderate until the same late interval, then
explodes with the pressure RHS:

```text
bf_residual_max:
  3.087e+06 at t=0.018002600
  1.436e+09 ppe-scale already visible
  4.708e+14 final
```

This is not pure hydrostatic imbalance alone.  It is a pressure-force
compatibility failure after the grid-scale velocity mode has entered the
pressure/capillary history.

### H11: Nonuniform grid metric bug

Not supported as the primary cause by current evidence.  The unstable mode is
localized symmetrically around the bubble interface, not at the minimum grid
cell alone.  Grid spacing is stable:

```text
min dx = 2.755923e-04
min dy = 2.117645e-04
```

A metric error could amplify a high-frequency mode, so it remains a secondary
risk, but the observed mode is better explained by the mass/momentum/pressure
coupling.

### H12: Wall boundary/no-slip failure

Not supported as primary.  The pressure scalar has large wall values, but the
largest velocities are inside the interface band, not on the walls.  The
dominant mode is left-right symmetric around the bubble.

### H13: UCCD6 core instability

Rejected as a standalone explanation.  Existing UCCD6 tests verify
energy-monotone behavior for the intended smooth single-phase operator.  The
observed failure appears only in the coupled high-density-ratio, moving
interface, pressure-jump, affine-history system.  Blaming UCCD6 alone would
miss the coupling theorem.

### H14: Primitive-velocity momentum form violates common-flux transport

Supported as the leading root-cause class.

The current production run uses:

```text
run.momentum_form = primitive_velocity
```

The interface is transported first, density is rebuilt from the new `psi`,
and the solver advances nodal velocity.  But the physical two-phase transport
state is `(q, M, P)`, not `(q, u)`.  The transport theorem requires:

```text
F_M = rho_g F_V + (rho_l-rho_g) F_q
M_t = -D F_M
P_t = -D(F_M u_donor)
K(M^{n+1}, P^{n+1}) <= K(M^n, P^n) + physical work
```

The current primitive route has no theorem guaranteeing that the interface
transport, reinitialization/profile projection, density update, and momentum
state share one mass flux.  At density ratio `833`, any mismatch between the
transported phase and the velocity/momentum state is strongly amplified.

This explains why the failure first appears as an interface-band high-frequency
velocity mode and then enters the pressure/history cochain.  It also matches
the recently implemented but intentionally fail-closed
`conservative_common_flux` foundation.

### H15: Collocated/face reconstruction checkerboard mode

Supported as the proximate modal form.

At `t=0.0175`, high-index spectral energy is negligible.  In the pre-blowup
frame, the velocity is almost purely near-Nyquist:

```text
high-k energy fraction  = 0.9999117
Nyquist energy fraction = 0.9991236
u sign flip in y-band   = 1.0
```

This is the actual mode that blows up.  The cause is not that the smooth
physical solution becomes large; the cause is that the coupled discretization
admits and feeds a grid-scale interface velocity mode.

## Root-Cause Determination

The best current determination is:

```text
Primary mathematical defect:
  The production rising-bubble route still advances primitive velocity rather
  than a conservative common-flux (M,P) state.  The density/interface transport,
  reinitialization/profile projection, pressure-jump affine face history, and
  velocity predictor/corrector are therefore not tied by a single discrete
  energy law.

Proximate numerical manifestation:
  A near-Nyquist horizontal velocity mode appears in the interface band near
  t ~= 0.01803.  The mode collapses dt_advective, drives an enormous PPE RHS,
  and feeds an exploding affine pressure face-history cochain.

Rejected explanations:
  physical bubble rise, capillary CFL alone, PPE solver nonconvergence,
  pressure visualization, phase-count/gauge singularity, and wrong restart
  checkpoint.
```

In short: the blow-up is not primarily "too large CFL" or "pressure should be
filtered."  It is a missing conservative mass-momentum-pressure transport
theorem in the production path, exposed by high density ratio and affine
pressure history.

## Theory-Valid Next Checks

The next checks should not add damping.  They should test the theorem directly:

```text
1. Replay a short window ending before t=0.01803 and record stage-wise
   transport ledgers, mass fluxes, momentum fluxes, and kinetic-energy
   production.

2. Wire the already implemented conservative_common_flux transport into the
   NS predictor/projection route only when (q,M,P), face pressure history,
   restart, and visualization all consume the conservative state.

3. Add a per-step certificate:
      K_after - K_before
      minus gravity work
      minus capillary work
      minus viscous dissipation
      minus pressure constraint work
   and fail-close if the residual becomes positive at grid scale.

4. Track high-frequency interface-band velocity energy as a diagnostic, not
   as a filter.  It identifies the forbidden mode without suppressing it.

5. Keep pressure_hodge fail-close behavior.  Do not relabel nonintegrable
   affine face cochains as scalar physical pressure.
```

The decisive production fix should be a conservative common-flux state update,
not DCCD/FCCD/UCCD damping of the observed mode.
