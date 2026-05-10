# CHK-RA-REINIT-VOLUME-PRIORITY-001 — Volume-first reinitialization theory

Date: 2026-05-10

User premise:

```text
Follow physics.  Volume conservation has highest priority.
Within that constraint, identify theoretically admissible remedies.
```

## Physical Principle

For an incompressible immiscible two-phase flow without phase change, the
material phase volume is an invariant:

```text
d/dt |Omega_l(t)| = integral_{Gamma(t)} u dot n dS = integral_{Omega_l(t)} div u dV = 0.
```

At the continuous sharp-interface level, this is the volume of the liquid
region.  At the discrete level we must choose exactly one discrete functional
as the physical volume invariant.  The current failure arose because the
reinitializer tried to enforce two non-identical volume-like functionals as
hard constraints:

```text
V_P1(phi) = marching-squares / P1 sharp area,
M_q(q)    = sum_i q_i V_i, nodal finite-volume phase mass.
```

These are both plausible approximations of physical volume, but they are not
the same discrete functional.  Treating both as exact independent invariants
overdetermines the retraction.

Therefore a volume-first theory must begin with:

```text
Pick one V_h^phys.
Require V_h^phys(R_h q) = V_h^phys(q^T).
Demote all other volume-like quantities to diagnostics or soft defects.
```

## Candidate Volume Functionals

### A. Finite-volume phase volume

```text
V_h^F(q) = 1^T V_c q.
```

This is the transported conserved quantity in the current
`conservative_common_flux` state.  It also determines density:

```text
rho(q) = rho_g + (rho_l - rho_g) q.
```

If volume preservation has priority inside the current solver architecture,
this is the most consistent invariant because mass, density, momentum, and
checkpoint state are all functions of `q`.

Cost: the sharp/P1 interface area enclosed by the `q=0.5` contour can change
slightly during reinitialization.  That change must be recorded as a geometry
representation defect, not hidden.

### B. P1 sharp-interface volume

```text
V_h^P1(phi) = marching-squares area enclosed by phi=0.
```

This is the natural volume paired with the current closed-interface surface
energy `S_h` and Young--Laplace volume Lagrange multiplier.  If the code were
a pure sharp-interface method, this would be the physically clean hard
invariant.

Cost in the current solver: density and conservative momentum are not stored
as P1 cell fractions; they are stored through nodal `q`.  If `V_h^P1` is exact
but `1^T V q` changes, the conservative state receives a hidden phase-mass
impulse.  This is not acceptable unless the whole state is recast around
geometric cell fractions.

### C. Geometric finite-volume cell fractions

```text
q_i = |cell_i cap Omega_l| / |cell_i|,
V_h^G(q) = sum_i q_i V_i = V_h^P1(phi).
```

This is the best long-term reconciliation: sharp geometry and conservative
phase mass share one measure.  It is essentially a geometric CLS/VOF hybrid:
`phi` carries normals/curvature, while `q` carries conservative volume.

Cost: this requires a larger state-space change: geometric fraction
construction, conservative remap of fractions, face apertures or compatible
fluxes, and updated capillary/pressure pairing.  It is not a one-line fix.

## Admissible Retractions Under Volume Priority

### Route 1 — Conservative phase-volume hard constraint

Use the current finite-volume phase volume as the hard invariant:

```text
Find lambda such that
  1^T V sigmoid((phi_sdf + lambda)/eps_local) = M_target.
```

Here `lambda` is a constant normal offset of the signed-distance field.  For a
closed interface with all nodes free, the left side is monotone in `lambda`
and spans `[0, |Omega|]`; therefore the scalar solve is bracketable whenever
the target volume is physically admissible.

This moves the sharp interface if necessary.  That is not a violation under
the volume-first premise; it is the correct Lagrange multiplier response for
preserving material volume when the reinitialization SDF changed the
representation.

Required certificates:

```text
Delta V_F = 0 within tolerance,
Delta V_P1 recorded,
Delta K_reinit recorded through q,m,p lift,
zero-set displacement norm recorded,
topology/stratum change diagnostic recorded.
```

This route is the most compatible with the current conservative common-flux
scheme.

### Route 2 — Sharp/P1 volume hard constraint, diffuse mass soft

Use the P1 enclosed area as the hard invariant:

```text
Find lambda such that
  V_h^P1(phi_sdf + lambda) = V_target.
```

Then reconstruct `q` from the profile and accept that `1^T V q` may change.
The diffuse-mass change is not corrected by profile width unless feasible; it
is recorded as a representation defect.

This is physically natural for a sharp-interface capillary variational
derivation, but it is not fully compatible with the current finite-volume
density/momentum state at high density ratio.  It should not be the default
production route unless density and momentum are also lifted in a way that
keeps the total material volume interpretation consistent.

### Route 3 — Volume-hard least-change projection

Formulate reinitialization as a constrained projection:

```text
minimize   ||phi - phi_sdf||_W^2 + alpha ||q - H_eps(phi)||_V^2
subject to V_h^phys(q, phi) = V_target,
           admissible topology/regularity constraints.
```

Only the selected physical volume is hard.  Other desired quantities enter as
penalties or recorded residuals.  This route is the most general and can
handle wall contact and topology-sensitive cases, but it needs a careful
solver and GPU-oriented implementation.

### Route 4 — Geometric CLS/VOF unification

Promote geometric cell fractions to the conservative variable:

```text
q_i = geometric fraction from phi,
1^T V q = V_h^P1(phi) by construction.
```

Then the conflict between P1 volume and finite-volume phase mass disappears.
The reinitializer can preserve sharp volume and conservative mass
simultaneously because they are the same discrete object.

This is the most mathematically satisfying long-term route, especially for
closed interfaces, capillary waves, and wall-contact bubbles.  It is also the
largest implementation shift.

## Rejected Remedies

- Enlarging the profile-scale list is not a volume-first fix.  It may repair
  sample insufficiency near the feasible boundary but cannot solve an empty
  constraint set.
- Keeping the zero set fixed while forcing diffuse mass exactly is impossible
  in general.  A fixed zero set has a bounded profile-mass image.
- Preserving both `V_h^P1` and `1^T V q` as exact independent constraints is
  invalid unless the discretization is changed so that the two functionals are
  identical.
- Turning off fail-close hides the fact that no admissible projection exists
  under the requested hard constraints.
- Damping, CFL changes, smoothing, curvature caps, or benchmark-specific
  branches do not restore the invariant.

## Decision Under Current Architecture

For the current `conservative_common_flux` solver, the volume-first production
candidate should be Route 1:

```text
Hard invariant: V_h^F(q) = 1^T V q.
Reinit action: signed-distance reconstruction followed by a scalar normal
               offset that exactly restores V_h^F.
Soft/diagnostic: P1 sharp volume drift, surface-energy drift, topology/stratum
                 change, kinetic-energy lift defect.
```

Reason:

1. `q` is the conserved transported phase variable.
2. `rho(q)` and conservative momentum use `q`.
3. Checkpoint/restart state is already closed around `(q, rho(q), p)`.
4. A scalar normal offset has a monotone existence theorem for physically
   admissible volumes.
5. It turns the current fail-close from "two hard constraints impossible" into
   "one physical invariant exact, geometry defect explicit."

If the project later chooses the pure sharp-interface interpretation as the
top priority, then Route 4 is the proper long-term replacement: construct
geometric fractions so the sharp volume and conservative phase mass are the
same quantity.  Route 2 alone is not enough for high-density-ratio dynamics.

## Required Verification Before Implementation Acceptance

1. Manufactured fixed-interface probes:
   prove scalar offset restores `1^T V q` for targets across `[0, |Omega|]`
   and fails only for impossible targets.
2. Reinit-only oscillating-droplet replay:
   compare `every_steps=1` current failing path with volume-first offset
   retraction near the step-400 state.
3. One-step transport/reinit split:
   verify `q^T -> q^R` preserves `1^T V q` exactly and records `V_P1` drift.
4. Static droplet:
   confirm no hidden velocity/momentum impulse is introduced by the reinit
   lift.
5. Oscillating droplet:
   confirm capillary drive remains nonzero and volume drift remains bounded by
   the scalar solve tolerance.
6. Capillary wave and wall-contact bubble:
   check that open-interface and wall-constrained masks do not break the
   monotonicity/bracketing assumptions; if masks restrict all useful nodes,
   fail-close with an explicit infeasible-volume certificate.

No implementation should be promoted without these gates.
