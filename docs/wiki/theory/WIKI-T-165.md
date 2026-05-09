---
ref_id: WIKI-T-165
title: "Variational Gravity Hodge Projection"
domain: theory
status: ACTIVE
tags: [rising_bubble, gravity, buoyancy, hodge_projection, conservative_momentum, common_flux, pressure_projection]
sources:
  - path: docs/memo/short_paper/SP-AK_variational_gravity_hodge_projection.md
    description: "Short-paper derivation of gravity as a transport-adjoint force covector"
  - path: docs/memo/short_paper/SP-AJ_conservative_common_flux_energy_ledger.md
    description: "Conservative common-flux energy ledger that this card refines for gravity"
  - path: docs/wiki/theory/WIKI-T-164.md
    description: "Active conservative common-flux rising-bubble remedy contract"
  - path: docs/wiki/theory/WIKI-T-162.md
    description: "Closed-interface capillary force as a transport-adjoint covector"
depends_on:
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-088]]"
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-164]]"
consumers:
  - domain: theory
    usage: "Use as the active gravity/buoyancy formulation before implementing rising-bubble fixes"
  - domain: code
    usage: "Route gravity through a force-covector layer, not nodal body acceleration"
  - domain: experiment
    usage: "Design hydrostatic, flat-interface, rising-bubble, restart, and GPU/CPU gates"
  - domain: paper
    usage: "Use after validation to explain rising-bubble gravity/projection coupling"
compiled_by: ResearchArchitect
compiled_at: "2026-05-09"
---

# Variational Gravity Hodge Projection

## Claim

The active rising-bubble gravity formulation is not a nodal acceleration
`-(rho-rho_ref)g/rho`.  Gravity is the force covector obtained by pulling back
the discrete gravitational potential through the same common-flux mass
transport differential used by the conservative state:

```text
Phi_g(m) = y^T(g m)
r_g(q)  = -T_m(q)^T d Phi_g/dm
a_g(q)  = M_f(q)^{-1} r_g(q).
```

Pressure is the same `M_f`-metric Hodge reaction used by the projection:

```text
u^{n+1} = argmin_{D_f u=0, BC} 1/2 ||u-u^dagger||_{M_f}^2,
u^dagger = u^n + dt M_f^{-1}(r_g+r_sigma+r_mu+...).
```

Hydrostatic gravity is the pressure-range component.  Physical buoyant motion is
the remaining divergence-free Hodge component.

## Reason

The current pressure-coordinate history fix did not remove the rising-bubble
failure.  Local probes showed:

```text
pressure_coordinate history      fails in the old blow-up band
legacy face_acceleration history fails in the same band
sigma = 0                        still fails
g = 0                            passes the same band
balanced_buoyancy toggles        do not change the root behavior
```

Therefore the remaining root is gravity/pressure/face-metric compatibility.
The formulation must be rebuilt at the force-covector level.

## Discrete Contract

Let `D_f` be the production face divergence, `T_m(q)` the production
common-flux mass-transport differential, and `M_f(q)` the transported face-mass
metric.  The gravity force is accepted only if the transport adjoint identity
holds:

```text
<r_g,w_f> + <g y,T_m(q)w_f> = 0
```

for the same nonuniform grid, boundary, face locus, and backend used in the
step.  A body-force representative is allowed only after proving

```text
<M_f a_body,w_f> = <r_g,w_f>
```

in that same metric.

## Hodge Split

The pressure range is

```text
R_p = { M_f^{-1} G_f pi : pi in Q_h/constants }.
```

The gravitational acceleration decomposes as

```text
a_g = Pi_R^M a_g + H_R^M a_g.
```

`Pi_R^M a_g` is hydrostatic pressure reaction.  `H_R^M a_g` is the physical
buoyant drive.  Static tests must have zero Hodge remainder; rising-bubble
tests should have a finite nonzero remainder at the physical scale.

For capillary plus gravity:

```text
r_total = r_g + r_sigma,
r_sigma = -T_q(q)^T d(sigma S_h)/dq.
```

Static flat interfaces require

```text
H_aug^M(M_f^{-1}r_total) ~= 0,
```

where `H_aug` includes pressure, affine jump, component-volume, and boundary
reaction ranges.

## Required Gates

Use these before calling the route production:

```text
G1 random-adjoint:      <r_g,w> + <g y,T_m w> ~= 0
G2 single-phase:        ||H_R^M a_g|| ~= 0
G3 flat two-phase:      ||H_aug^M(a_g+a_sigma)|| ~= 0
G4 rising bubble:       0 < ||H_aug^M a_g|| < physical scale bound
G5 gravity energy:      W_g + Delta Phi_g ~= 0
G6 projection energy:   Delta K_projection <= tolerance
G7 restart invariance:  saved/restored state reproduces r_g and projection
G8 GPU/CPU identity:    backend.xp force path matches CPU within tolerance
```

## Implementation Reading

The next implementation should introduce a gravity force-covector service:

```text
GravityPotentialCovector(q, face_mass, grid_y, g)
  -> r_g faces
  -> a_g = M_f^{-1} r_g
  -> adjoint/energy diagnostics
```

YAML should expose the theorem, not a tuning parameter:

```yaml
numerics:
  momentum:
    terms:
      gravity:
        formulation: variational_potential
        transport_adjoint: common_flux
        metric: transported_face_mass
        hodge_gate: fail_close
```

The legacy `balanced_buoyancy` names are compatibility aliases only if they
route to this covector theorem.

## Negative Knowledge

Do not treat these as physical fixes:

```text
CFL reduction
velocity damping
pressure smoothing
curvature cap
DCCD/UCCD high-k filter
node-to-face body-force interpolation
hydrostatic split using a gradient different from PPE/corrector
benchmark-specific rising-bubble branch
```

They may delay the symptom, but they do not establish the energy/Hodge law.

## Pointers

Read [[WIKI-T-164]] for the surrounding conservative common-flux energy ledger
and [[WIKI-T-162]] for the analogous capillary transport-adjoint covector.
