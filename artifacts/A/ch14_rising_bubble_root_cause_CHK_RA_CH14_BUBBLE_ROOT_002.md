# CHK-RA-CH14-BUBBLE-ROOT-002: rising-bubble root-cause hypotheses

## Scope

This note refines the rising-bubble blow-up RCA after the literature survey on
consistent mass-momentum transport.  The target symptom is a high-density-ratio
water-air bubble that develops nonphysical fields before the expected physical
time scale.  The analysis is theory-first: no damping, CFL-only reduction,
clipping, smoothing, pressure masking, or benchmark-specific branch is accepted
as a cause or remedy.

## Governing invariant

For pure incompressible transport by a volume-preserving map `Phi`, the kinetic
energy

```text
E(rho, u) = 1/2 int rho |u|^2 dx
```

is preserved if and only if mass and velocity/momentum are updated by the same
map:

```text
rho1 = rho0 o Phi^-1,
u1   = u0   o Phi^-1.
```

Equivalently, a finite-volume method must use the same mass flux as the mass
part of the momentum flux.  This is the central condition in Rudman-type VOF,
level-set consistent transport, CLSVOF momentum-preserving schemes, phase-field
energy-conserving momentum transport, and recent LENT/geometric-VOF consistency
papers.

The production code currently has a strong face-native phase transport path, but
the momentum predictor still evolves velocity/acceleration history rather than
transporting conservative momentum with the phase mass flux:

- `src/twophase/levelset/fccd_advection.py:174` computes the phase flux
  `psi_face * face_velocity`.
- `src/twophase/levelset/heaviside.py:185` recomputes `rho` algebraically from
  the transported/reinitialized `psi`.
- `src/twophase/ns_terms/uccd6_convection.py:111` computes a velocity-only
  skew/conservative acceleration from `u`.
- `src/twophase/simulation/ns_step_services.py:482` uses EXT2 history for that
  acceleration in IMEX-BDF2.
- `src/twophase/simulation/viscous_predictors.py:239` uses
  `4/3 u^n - 1/3 u^{n-1}` as a velocity base state in the current `rho` metric.

That is not yet a common transport map for `rho` and `rho u`.

## Hypothesis matrix

H1. Capillary pressure-jump imbalance is the primary cause.

Rejected as first cause.  The exact-map gate produces energy defects with
capillary and pressure removed.  Capillary imbalance can amplify later fields,
but it is not needed to generate the defect.

H2. Pressure projection or affine-jump IPC is the primary cause.

Rejected as first cause.  The pure-transport gate has no pressure solve and no
projection, yet non-common maps open energy.  Projection must still be checked
after the transport theorem is restored, but it cannot explain the isolated
transport defect.

H3. Boundary conditions are the primary cause.

Rejected as first cause.  The gate is periodic and has no walls.  Wall
zeroing/nonuniform-grid metrics can amplify or localize the defect, but they are
not mathematically necessary for it.

H4. Reinitialization is the primary cause.

Partially rejected.  Reinitialization is not present in the pure-transport gate.
However, production reinitialization changes `psi`, hence `rho`, without an
associated momentum retraction.  It is therefore a secondary source of the same
mass-momentum map mismatch.

H5. Density ratio alone is the primary cause.

Rejected.  The IMEX/history candidate produces a relative kinetic-energy
increase of `+3.162e-02` even at density ratio `1`.  High density ratio makes
the defect more dangerous, but the root is not the value of the ratio itself.

H6. Nonuniform grid volume handling is the primary cause.

Not primary by the pure periodic uniform-grid gate.  Still a serious amplifier:
if `rho`, `psi`, and momentum use different cell/face measures on the nonuniform
grid, the same theorem fails with larger and less symmetric local residuals.

H7. UCCD6 spatial convection is the primary cause.

Partially supported, but not because UCCD6 is a bad scalar operator.  UCCD6 is a
velocity-form skew/conservative acceleration operator.  For variable density
two-phase flow, the required object is a conservative momentum flux whose mass
part is the phase mass flux.  A skew velocity operator can preserve a constant
density velocity norm while still failing the `rho |u|^2` transport identity.

H8. IMEX-BDF2 history is the primary cause.

Strongly supported as an exposed mechanism.  The gate's
`density_map_velocity_imex` candidate gives about `+3.13e-02` energy increase
for one shifted update at density ratio `833.333`, and essentially the same
`+3.16e-02` at density ratio `1`.  BDF2 is not forbidden, but the current
velocity-history form lacks a variable-mass G-stability proof in
`M(rho^{n+1})`.

H9. Lagged momentum/current density division is the primary cause.

Supported as a secondary mechanism.  The gate's lagged-momentum candidate gives
nonzero defects, e.g. `+2.011e-04` at `N=64`, density ratio `833.333`, one-cell
shift.  The sign can vary with phase, which matches a metric-mismatch problem
rather than a monotone physical force.

H10. Density moved but velocity left on current nodes is enough to cause error.

Supported.  The gate gives `+4.469e-04` at `N=64`, density ratio `833.333`,
one-cell shift.  This is exactly the mass-metric defect
`1/2 int (rho_map-rho0)|u0|^2 dx`.

H11. Velocity moved but density left on current nodes is enough to cause error.

Supported.  The gate gives `-5.640e-04` at the same setting.  The sign differs,
but the theorem is still broken.

H12. Independent/opposite maps for density and velocity are enough to cause
error.

Supported.  The gate gives `+7.634e-04` once non-orthogonal modes are used.
This excludes the accidental-zero false negative seen with overly symmetric
Fourier probes.

H13. Face-native projection fixes the transport mismatch automatically.

Rejected.  Face-native projection fixes the divergence and pressure-correction
state.  It does not by itself make the momentum convective flux use the same
phase mass flux as `psi` transport.

H14. DCCD/FCCD/UCCD can solve the issue if used as a shared geometric transport
engine.

Supported as a direction, not yet as implemented.  FCCD already provides a
projection-native face velocity path for `psi`.  The missing theorem is to use
that same face mass flux in the conservative momentum update, or to transport
momentum by the same certified map and recover velocity from the transported
mass.

## Verification evidence

From `CHK-RA-CH14-BUBBLE-MAP-001`, for `N=64`, density ratio `833.3333333333334`,
and one-cell shift:

```text
common_exact_map                  +0.000000e+00
density_map_velocity_current      +4.469091e-04
density_current_velocity_map      -5.639845e-04
density_map_velocity_imex         +3.128604e-02
density_map_momentum_lagged       +2.011059e-04
independent_opposite_maps         +7.634354e-04
```

Density-ratio sweep at `N=64`, one-cell shift:

```text
common_exact_map:
  ratio 1:+0.000e+00, 10:+1.136e-16, 100:+1.980e-16, 833.333:+0.000e+00

density_map_velocity_imex:
  ratio 1:+3.162e-02, 10:+3.135e-02, 100:+3.129e-02, 833.333:+3.129e-02

density_map_velocity_current:
  ratio 1:+0.000e+00, 10:+3.662e-04, 100:+4.391e-04, 833.333:+4.469e-04

independent_opposite_maps:
  ratio 1:+0.000e+00, 10:+6.256e-04, 100:+7.501e-04, 833.333:+7.634e-04
```

This evidence separates three facts:

1. The common-map theorem is numerically closed to roundoff.
2. Map mismatch opens energy even without pressure/capillary/reinit/walls.
3. IMEX velocity history opens energy even at density ratio 1.

## Identified cause

The root cause is update-level mass-momentum inconsistency:

```text
phase path:     psi^n -> face phase flux -> psi^{n+1} -> rho^{n+1}
momentum path:  u^n, u^{n-1}, C(u^n), C(u^{n-1}) -> u*
energy metric:  E^{n+1} = 1/2 <u^{n+1}, M(rho^{n+1}) u^{n+1}>
```

The velocity/momentum path has no certificate that it is the same map used to
produce `rho^{n+1}`.  Therefore the method evaluates old-map velocity history in
a new mass metric.  This creates nonphysical kinetic energy before the physical
operators are allowed to do work.

The failure is structural, not parametric.  CFL reduction, damping, pressure
filtering, curvature smoothing, density clipping, or DCCD suppression of
velocity/pressure can at best lower the observed growth rate.  They do not
restore the common-map theorem and must not be considered a valid fix.

## Required remedy class

A valid remedy must establish one of the following discrete theorems.

1. Conservative common-flux theorem:

```text
rho^{n+1}       = rho^n       - dt D F_rho
(rho u)^{n+1}  = (rho u)^n   - dt D (F_rho * u_face)
u^{n+1}         = (rho u)^{n+1} / rho^{n+1}
```

with `F_rho` exactly the mass flux induced by `psi` transport.

2. Common-map retraction theorem:

```text
(psi, rho, rho u)^{n+1} = R_h Phi_h (psi, rho, rho u)^n
```

where reinitialization/retraction acts on mass and momentum consistently, not
only on `psi`.

3. Variable-mass G-stability theorem:

```text
E^{n+1}_{M(rho^{n+1})} - E^n_{M(rho^n)}
  <= physical work - viscous dissipation + certified truncation budget
```

for the actual IMEX-BDF2/convection/projection composition.

Among these, the most compatible with the present FCCD/CCD/UCCD architecture is
to make FCCD face phase transport produce a certified mass flux, then use that
flux as the mass part of conservative momentum transport.  UCCD6 can remain as
a high-order reconstruction/dissipation ingredient only after the conservative
mass-momentum flux theorem is restored.
