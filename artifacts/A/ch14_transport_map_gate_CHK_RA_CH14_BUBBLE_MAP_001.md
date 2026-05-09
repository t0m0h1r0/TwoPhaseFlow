# CHK-RA-CH14-BUBBLE-MAP-001: exact transport-map RCA

## Question

The rising-bubble case can blow up or restart inconsistently before the
observed failure time.  This note tests which part of the discretization can
create kinetic-energy defects before capillary, pressure, viscosity, boundary,
or reinitialization effects are involved.

The theoretical invariant used here is the pure-transport identity.  Let
`Phi` be a volume-preserving map.  For density `rho` and velocity `u`,

```text
E(rho, u) = 1/2 int rho |u|^2 dx
```

is unchanged by the common pullback

```text
rho1 = rho0 o Phi^-1,
u1   = u0   o Phi^-1.
```

This is stronger than checking a spatial RHS power balance: it is an
update-level gate.  If the production update uses different maps or different
time histories for `rho`, `rho u`, and `u`, the identity is no longer a
theorem.

## Hypotheses

H1. A common volume-preserving map for density and velocity preserves kinetic
energy to roundoff.  This is the mathematical control case.

H2. Changing density while leaving velocity on another map can create a mass
metric defect

```text
Delta E = 1/2 int (rho_map - rho0) |u0|^2 dx.
```

This defect may vanish for special orthogonal Fourier fields, so the gate must
use non-degenerate density and velocity-energy modes.

H3. Moving velocity while leaving density on the old map creates the dual
defect

```text
Delta E = 1/2 int rho0 (|u_map|^2 - |u0|^2) dx.
```

H4. Explicit velocity history, represented by `u1 = 2 u0 - u_prev`, is not a
common transport map.  It can increase kinetic energy even at density ratio 1,
so the issue is not only the water-air density jump.

H5. Lagged momentum divided by moved density,

```text
u1 = (rho0 u0) / rho_map,
```

does not preserve either the common-map energy theorem or the correct
transported momentum theorem.  The sign can depend on phase, but nonzero
defect is expected.

H6. Opposite maps for density and velocity are also non-Hamiltonian as an
update.  They should open an energy defect once orthogonality is removed.

H7. Pressure, capillary force, boundary conditions, and reinitialization cannot
be the primary cause if a defect appears in this pure periodic transport gate,
because none of those terms are present.

## Verification design

The probe in
`artifacts/A/ch14_transport_map_gate.py` uses periodic analytic fields on
uniform grids.  Density ratios are `1, 10, 100, 833.3333333333334`; grids are
`N=32,64,128`; shifts are `0, 0.25, 0.5, 1, 2` cells.  The velocity is a
multi-mode divergence-free field from a stream function, and density contains
non-orthogonal Fourier modes.  This prevents accidental zero results from
Fourier orthogonality.

Artifacts:

- CSV: `artifacts/A/ch14_transport_map_gate_CHK_RA_CH14_BUBBLE_MAP_001/transport_map_gate.csv`
- Summary: `artifacts/A/ch14_transport_map_gate_CHK_RA_CH14_BUBBLE_MAP_001/transport_map_gate_summary.json`
- Figure: `artifacts/A/ch14_transport_map_gate_CHK_RA_CH14_BUBBLE_MAP_001/transport_map_gate.pdf`

## Main results

For `N=64`, density ratio `833.3333333333334`, and one-cell map shift:

```text
candidate                         (E1-E0)/E0          mass_delta
common_exact_map                  +0.000000e+00       -5.684e-14
density_map_velocity_current      +4.469091e-04       -5.684e-14
density_current_velocity_map      -5.639845e-04       +0.000e+00
density_map_velocity_imex         +3.128604e-02       -5.684e-14
density_map_momentum_lagged       +2.011059e-04       -5.684e-14
independent_opposite_maps         +7.634354e-04       -5.684e-14
```

The shift sweep at density ratio `833.3333333333334`, `N=64` shows the same
separation:

```text
common_exact_map:
  0:+0.000e+00, 0.25:+0.000e+00, 0.5:+0.000e+00, 1:+0.000e+00, 2:+0.000e+00

density_map_velocity_current:
  0:+0.000e+00, 0.25:+1.233e-04, 0.5:+2.390e-04, 1:+4.469e-04, 2:+7.634e-04

density_map_velocity_imex:
  0:+0.000e+00, 0.25:+1.959e-03, 0.5:+7.832e-03, 1:+3.129e-02, 2:+1.244e-01

density_map_momentum_lagged:
  0:+0.000e+00, 0.25:-8.325e-05, 0.5:-7.817e-05, 1:+2.011e-04, 2:+1.858e-03

independent_opposite_maps:
  0:+0.000e+00, 0.25:+2.390e-04, 0.5:+4.469e-04, 1:+7.634e-04, 2:+9.802e-04
```

Controls:

```text
common_exact_map, ratio 833.333, shift 2:       +0.000000e+00
density_map_velocity_imex, ratio 1, shift 1:    +3.162005e-02
density_map_velocity_imex, ratio 833.333, shift 1:+3.128604e-02
```

## Inference

The strongest surviving cause is not capillary stiffness, pressure solve,
surface tension regularization, boundary handling, or reinitialization as a
first cause.  The gate reproduces an energy defect without any of those
operators.

The cause is update-level loss of a common transport map for mass and
momentum/velocity.  The physical kinetic energy is a quadratic form in the
current mass measure:

```text
E^n = 1/2 <u^n, M(rho^n) u^n>.
```

If `rho` is transported or retracted by one map while the velocity update uses
old-map velocity history, old-map momentum, or another face map, then the
method evaluates the quadratic form in mismatched measures.  This opens
non-physical kinetic energy even in a periodic pure-transport problem.

The IMEX/history candidate is especially important: it opens about `3e-2` in
one shifted update even for density ratio `1`.  Thus a high density ratio can
amplify the observed bubble instability, but it is not the mathematical origin
of the energy defect.

## Consequence for remedies

Any valid remedy must prove an update identity or inequality in the same mass
metric used by the transported density.  Acceptable directions are:

1. Transport conservative variables by one discrete map, then recover velocity
   from the same transported mass.
2. Use a variable-mass G-stable time discretization whose energy estimate is
   written in `M(rho^{n+1})`, not in a stale mass metric.
3. Make CCD/FCCD/UCCD provide the certified common transport/retraction map for
   both phase and momentum data.
4. Add fail-close diagnostics that reject a step when the measured pure
   transport energy defect is outside the proven budget.

The following are not remedies: damping, CFL-only reduction, pressure
projection masking, capillary smoothing, density clipping, or benchmark-specific
branches.  They can hide the symptom but do not restore the common-map theorem.
