# CHK-RA-REINIT-SHARP-VOLUME-001 — Ridge-Eikonal sharp-volume feasible-set RCA

Date: 2026-05-10

User problem:

```text
Oscillating droplet with reinit every step fails closed around step 400.
The explicit error is not in the NS solver; it is Ridge--Eikonal
sharp_phase_volume failing to bracket the diffuse-mass profile correction
without moving the sharp interface.
```

## Theoretical Reading

Ridge--Eikonal reinitialization is a representation retraction, not physical
transport.  In `sharp_phase_volume` mode the current code attempts two hard
constraints:

```text
V_P1(phi = 0)        = target sharp/P1 phase volume,
sum_i q_s(phi_i) V_i = target diffuse CLS mass,
```

where `q_s = sigmoid(phi / (s eps_i))`.  The first constraint is imposed by a
constant signed-distance shift.  The second constraint is then imposed only by
changing the profile width `s`, explicitly without moving the zero level.

For a fixed zero set, the function

```text
M(s) = sum_i sigmoid(phi_i / (s eps_i)) V_i
```

does not cover all possible masses.  As `s -> 0`, it approaches the nodal
Heaviside control-volume mass, not the marching-squares/P1 area.  As
`s -> infinity`, it approaches half the domain volume.  Therefore a diffuse
mass target outside this interval makes the projection set empty.  A
fail-close is then mathematically correct.

The key mismatch is metric/geometric:

```text
V_P1          sharp marching-squares area,
M_diffuse     nodal control-volume quadrature of q.
```

They are not the same discrete functional, and preserving both as independent
hard invariants can overdetermine the representation.

## Hypotheses

H01 — NS pressure/momentum solver instability caused the failure.
Rejected.  The reported exception is raised inside
`RidgeEikonalReinitializer._apply_diffuse_mass_profile_constraint`, before
pressure/momentum correction can explain the bracket failure.

H02 — The target phase volume is outside the domain.
Rejected for this symptom.  The code has a separate error for
`target < 0` or `target > domain_volume`; the observed error is the later
diffuse-mass bracket failure.

H03 — The sharp/P1 volume shift itself cannot be bracketed.
Rejected for the reported symptom.  The failing message is produced after the
sharp interface has been fixed, during profile-width mass restoration.

H04 — The diffuse mass target is outside the feasible image of fixed-zero-set
profile widening.
Accepted.  Manufactured probes show that targets below the nodal Heaviside
floor fail with the same error.

H05 — The root cause is the finite scale sample list only.
Partially accepted as a secondary risk.  Targets very close to the feasible
lower boundary can fail because the current samples stop at `1/16`, but
extending the scale list alone is not a theorem-grade production fix: some
targets are genuinely outside the feasible interval, and underresolved
profiles violate the representation contract.

H06 — P1 sharp area and nodal diffuse mass are equivalent enough on N=32.
Rejected.  For translated N=32 ellipses with the same physical size, the
nodal Heaviside mass minus P1 area varied from about `-3.83e-03` to
`+5.91e-03`, large enough to empty the fixed-zero-set diffuse mass interval.

H07 — Wall-contact pinning is the primary cause for the oscillating droplet.
Rejected for the closed droplet.  The oscillating droplet does not contact the
wall, so the free mask is effectively the full field.  Wall pinning remains a
separate risk for wall-contact cases because it narrows the feasible interval.

H08 — Sign/orientation of `phi` or `psi` is inverted.
Rejected by manufactured positive-inside probes: feasible targets above the
nodal floor converge, while targets below it fail predictably.

H09 — GPU/CuPy path is the cause.
Rejected as primary.  The same feasible-set obstruction appears in CPU
manufactured probes.  GPU may change numerical details but not the constraint
geometry.

H10 — `every_steps=1` is itself a physical law.
Rejected.  Every-step reinit repeatedly applies this representation
projection.  It increases exposure to an empty feasible set but is not a
physical transport equation.

## Efficient Verification

### Probe A — fixed zero set has bounded diffuse mass

For an N=32 alpha-2 ellipse, using fixed `phi_sdf` and varying only profile
scale:

```text
sharp_area     1.9411781416692794e-01
mass(scale=1)  2.6959903477512837e-01
below_sharp target 1.9311781416692794e-01 -> same bracket failure
above_sharp target 1.9511781416692794e-01 -> pass
too_high target 7.5000000000000000e-01 -> same bracket failure
```

This proves the bracket is a feasibility condition, not a solver instability.

### Probe B — P1 area is not the nodal Heaviside mass

With the same N=32 ellipse translated by subcell offsets:

```text
cx    cy     P1 area       nodal H mass   nodal-P1
0.500 0.500  1.933617e-01  1.943359e-01  +9.742e-04
0.500 0.514  1.932863e-01  1.894531e-01  -3.833e-03
0.515 0.514  1.933125e-01  1.992188e-01  +5.906e-03
```

The lower endpoint of `M(s)` follows nodal Heaviside quadrature, not the P1
area.  A conserved diffuse mass from one stratum can be below the nodal floor
of the next stratum even when the P1 volume is almost unchanged.

### Probe C — same production path failure with two nearby strata

Use an old stratum target mass from one translated ellipse and a new stratum
whose nodal Heaviside floor is higher:

```text
target P1       1.941652533e-01
target diffuse  1.933593750e-01
candidate P1    1.941993731e-01
candidate floor 1.992187500e-01
result          ValueError: failed to bracket diffuse-mass profile correction
```

If the target is moved above the new floor, the same code path succeeds.  This
isolates the cause to feasibility of the two hard constraints.

## Current Root Cause

The current `sharp_phase_volume` projection asks the reinitializer to preserve
a sharp/P1 geometric volume and a nodal diffuse mass as simultaneous hard
constraints after the zero set has already been fixed.  Because the second
constraint can only vary one scalar profile width, and because its feasible
range is bounded by the nodal Heaviside mass of the fixed stratum, the
constraint set can become empty.  In every-step reinit this happens once the
transport/regrid/reinit sequence carries the conserved diffuse mass across a
stratum whose nodal floor is higher than that target.

The fail-close is therefore desirable.  It is identifying an inconsistent
projection contract rather than hiding it.

## Negative Knowledge

- Do not solve this by damping, CFL changes, curvature caps, smoothing, or
  benchmark-specific branches.
- Do not blindly expand the profile-scale list.  That can hide near-boundary
  cases and generate underresolved interfaces while still failing for truly
  empty feasible sets.
- Do not reinterpret reinit as physical capillary work.  Reinit remains a
  representation retraction with its own defect ledger.
- Do not force both P1 volume and nodal diffuse mass as independent exact
  invariants unless a feasibility theorem is supplied.

## Implication For A Future Fix

The next theory step must choose a consistent retraction contract.  Candidates
to analyze:

1. Preserve sharp/P1 phase volume as the hard geometric invariant and record
   diffuse-mass defect as representation error.
2. Preserve conservative diffuse phase mass as the hard transport invariant
   and make sharp volume a diagnostic/projection residual.
3. Formulate a constrained least-change projection with explicit feasibility
   interval checks and a named relaxation when the exact intersection is empty.
4. Use a single discrete measure for both sharp and diffuse constraints, if a
   physically defensible finite-volume/P1 pairing can be derived.

No production correction should be adopted until one of these is proven
against static droplet, oscillating droplet, capillary wave, and wall-contact
cases.
