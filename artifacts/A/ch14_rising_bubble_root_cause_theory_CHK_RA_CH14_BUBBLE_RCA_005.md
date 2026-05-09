# CHK-RA-CH14-BUBBLE-RCA-005

## Question

Identify the cause of the SI rising-bubble blow-up using physics and
mathematics, generating many hypotheses and rejecting them by targeted tests.
No damping, CFL tuning, clipping, fallback, benchmark branch, or pressure/velocity
suppression is allowed as an explanation.

## Governing Identity

For immiscible incompressible two-phase flow,

```text
rho_t + div(rho u) = 0,
div u = 0,
```

and the convective part of the kinetic-energy equation is

```text
d/dt int 1/2 rho |u|^2 dV
  = int rho u . C(u) dV
    + int 1/2 |u|^2 rho_t dV.
```

For closed walls or periodic boundaries this contribution must vanish, except
for intentionally designed non-positive numerical dissipation.  Therefore the
discrete momentum transport must be skew/conservative in the same `rho dV`
metric and with the same mass-flux topology as the phase/density transport.

This identity is the diagnostic theorem.  Any candidate cause that does not
explain a violation of this identity is secondary.

## New Manufactured Test

Reusable script:

```text
artifacts/A/ch14_momentum_transport_manufactured_probe.py
```

Output:

```text
artifacts/A/ch14_momentum_transport_manufactured_CHK_RA_CH14_BUBBLE_MFG_001/
  manufactured_energy_identity.csv
  manufactured_energy_identity_summary.json
  periodic_uccd6_convergence.pdf
  saved_wall_grid_summary.pdf
```

The probe constructs divergence-free manufactured velocity fields and evaluates
the discrete power:

```text
P_pair = sum_i rho_i V_i u_i . C_h(u)_i
       + sum_i 1/2 |u_i|^2 V_i (rho_t)_i
```

It also evaluates the production explicit history term:

```text
P_IMEX = sum_i rho_i V_i u_i . (2 C_h(u^n) - C_h(u^{n-1}))_i
       + sum_i 1/2 |u_i|^2 V_i (rho_t^n)_i.
```

## Hypotheses and Tests

### H1: The blow-up is physically expected

Physical scale:

```text
R = 2.5 mm
Bo ~= 0.85
tau_sigma ~= 1.47e-2 s
U_buoyancy ~= 1.6e-1 m/s
U_capillary ~= 1.7e-1 m/s
```

Observed velocities reach `O(1e4 m/s)`.

Verdict: rejected.

### H2: Raw capillary force is singular

Previous checkpoint recomputation:

```text
raw closed-interface Riesz acceleration linf
t~=0.01:       [6.26e+02, 7.63e+02]
pre-blow-up:   [8.19e+02, 1.76e+03]
final:         [1.16e+03, 2.00e+03]
```

This is large but finite and not `O(1e12)`.  Curvature jump and component saddle
diagnostics also remain bounded.

Verdict: rejected as primary.

### H3: Marching-squares fixed stratum is near singular

Cut-edge diagnostics at pre-blow-up:

```text
min |dpsi| on x-cut edges = 4.079e-02
min |dpsi| on y-cut edges = 5.227e-02
zero-crossing change count = 0
```

Verdict: rejected for this case.

### H4: PPE solve failure creates the blow-up

Near runaway:

```text
ppe_dc_final_relative_l2 ~= O(1e-9)
div_u_max remains small until terminal runaway
```

Offline power signs:

```text
case        pressure actual-sign power
stable      +7.934e-04
pre-blow    -6.486e+12
final       -1.766e+13
```

At pre-blow-up the pressure reaction is damping in the tested sign convention.
It is responding to an already large predictor/history mode.

Verdict: rejected as initial cause.  Pressure is a symptom and constraint
reaction, not the energy source.

### H5: Reinitialization is the primary source

Observed:

```text
reinit_zero_crossing_change_count = 0
reinit_zero_level_displacement = O(1e-6 to 1e-5 m)
```

The manufactured tests reproduce the key energy-metric defect without any
reinitialization.

Verdict: secondary amplifier/confounder, not the primary root.

### H6: Instantaneous UCCD6 single-phase convection is the sole cause

Manufactured periodic smooth-density test, `N=32`:

```text
density            paired_rate for UCCD6 C^n
constant           -2.828e-07
smooth_mild        -2.828e-07
smooth_high_ratio  -2.828e-07
bubble_high_ratio  +3.193e-04
```

For smooth density the instantaneous paired identity is essentially satisfied;
for a sharp bubble-like density it leaves a positive residual that converges
with refinement:

```text
bubble_high_ratio paired_rate
N=16: +1.554e-03
N=32: +3.193e-04
N=64: +7.545e-05
```

Verdict: partially supported only as a seed at sharp density gradients.  It is
not the whole explanation.

### H7: Explicit IMEX-BDF2 history is not energy-stable in a changing density metric

Manufactured periodic test, UCCD6, `N=32`:

```text
density            paired_rate C^n      IMEX-paired rate
constant           -2.828e-07           -2.843e-07
smooth_mild        -2.828e-07           +6.774e-03
smooth_high_ratio  -2.828e-07           +1.126e-02
bubble_high_ratio  +3.193e-04           +3.697e-03
```

For constant density the explicit history remains nearly neutral.  For variable
density, even smooth density, the same history extrapolation creates positive
physical kinetic-energy work.  This is exactly the two-phase metric mismatch:
`C^{n-1}` is not skew with respect to the current `rho^n dV` inner product.

Checkpoint confirmation, production UCCD6:

```text
case                    conv_prev rho dV   conv_n rho dV    2conv_n-conv_prev rho dV
stable_t0p01            -1.484e-03         +1.508e-04       +1.786e-03
pre_blowup_t0p018033    +1.286e+15         -1.410e+13       -1.314e+15
final_guard_t0p018033   +3.498e+15         -3.858e+13       -3.575e+15
```

At `t~=0.01`, before the catastrophic mode, the actual production history term
already injects positive `rho dV` kinetic work.  By pre-blow-up the current
convection and pressure are damping, but the explicit-history mode has already
grown to `O(1e15)` power and is alternating sign.

Verdict: strongly supported.

### H8: Wall/nonuniform grid is the root

Manufactured test on the saved rising-bubble wall/nonuniform grid:

```text
density            UCCD6 paired_rate    UCCD6 IMEX-paired rate
constant           -1.127e+02           -1.127e+02
smooth_mild        -9.410e+01           -9.326e+01
smooth_high_ratio  -8.183e+01           -8.041e+01
bubble_high_ratio  -1.435e+02           -1.422e+02
```

This grid/operator combination is very dissipative for the manufactured wall
field, so it is not by itself an energy source.  However, the large magnitude
shows that nonuniform-wall compact operators can strongly amplify any
inconsistent history mode.

Verdict: not the root, but a likely amplifier.

### H9: Restart/checkpoint corruption

Checkpoint payload preserves previous convection, previous velocity, pressure
history faces, projected faces, pressure, grid, and step metadata.  The
manufactured tests isolate the same energy-history mechanism without using
restart at all.

Verdict: rejected as physical/numerical root.

## Root Cause

The most consistent root cause is:

```text
The production momentum equation advances velocity with a single-phase
skew-style convection operator and an explicit IMEX-BDF2 history extrapolate,
while the physical two-phase kinetic energy uses a time-dependent, sharply
varying rho dV metric tied to phase transport and reinitialization.

The instantaneous C^n operator can be nearly neutral for smooth density, but
the explicit history term 2C^n-C^{n-1} is not skew with respect to the current
rho^n dV metric.  It can inject physical kinetic energy even in manufactured
divergence-free periodic fields.  The rising-bubble checkpoint confirms that
this production history term is already positive at t~=0.01 before the
catastrophic mode.  Later, pressure and current convection damp the already
formed mode, so looking only at terminal signs misidentifies symptoms as causes.
```

This is a mathematical structure defect, not a parameter accident.

## What This Rules Out

The following are not root-cause solutions:

- lower CFL as the explanation;
- damping or velocity suppression;
- pressure clipping;
- DCCD as a post-hoc damper;
- curvature caps or smoothing;
- fallbacks to FD/WENO/PPE variants;
- benchmark-specific branches.

DCCD/FCCD/UCCD remain important, but they must be used to build a
two-phase-compatible mass/momentum transport complex, not to hide the energy
defect after it is created.

## Next Theoretical Target

The next scheme must be derived from a discrete momentum/energy pair:

```text
rho_t + D_f m_f = 0
(rho u)_t + D_f(m_f tensor u)_h = forces
```

with `m_f` the same mass flux used by phase/density transport.  The velocity
equation may be recovered only after the conservative momentum update, or via a
skew split that is algebraically equivalent in the `rho dV` metric.  Any
explicit history term must satisfy a G-stability/energy estimate in the
time-varying mass matrix, or fail-close for two-phase high-density-ratio runs.
