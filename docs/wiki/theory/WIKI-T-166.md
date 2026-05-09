---
ref_id: WIKI-T-166
title: "Boundary-Constrained Face Hodge Projection"
domain: theory
status: ACTIVE
tags: [rising_bubble, hodge_projection, no_slip, wall_boundary, common_flux, conservative_momentum, pressure_projection]
sources:
  - path: docs/memo/short_paper/SP-AL_boundary_constrained_face_hodge.md
    description: "Short-paper derivation of the boundary-constrained face Hodge projection"
  - path: artifacts/A/ch14_rising_bubble_root_cause_hypotheses_CHK-RA-CH14-BUBBLE-RCA-BOUNDARY-HODGE-001.md
    description: "RCA showing the face/nodal mismatch is wall-localized"
  - path: docs/memo/short_paper/SP-AJ_conservative_common_flux_energy_ledger.md
    description: "Conservative common-flux state and energy ledger"
  - path: docs/memo/short_paper/SP-AK_variational_gravity_hodge_projection.md
    description: "Variational gravity force covector"
depends_on:
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-164]]"
  - "[[WIKI-T-165]]"
consumers:
  - domain: theory
    usage: "Use before proposing rising-bubble wall-boundary projection fixes"
  - domain: code
    usage: "Implement preserved face-state projection as a constrained KKT problem, not nodal post-clamping"
  - domain: experiment
    usage: "Design gates for D_f f, wall_trace_from_faces, reconstruction, and momentum consistency"
  - domain: paper
    usage: "Use after validation to explain wall-bounded face Hodge closure"
compiled_by: ResearchArchitect
compiled_at: "2026-05-09"
---

# Boundary-Constrained Face Hodge Projection

## Claim

For wall-bounded conservative common-flux two-phase flow, the projection target
is not only divergence-free face flux.  It is the constrained face subspace

```text
K_h = { f : D_h f = 0 and B_h R_h f = 0 }.
```

`D_h` is the production face divergence, `R_h` reconstructs nodal velocity from
face velocity, and `B_h` selects no-slip wall nodal components.  The corrector
must produce `f in K_h`, then publish

```text
u = R_h f,
m = rho u,
next transport uses f.
```

## Reason

The rising-bubble RCA found:

```text
projected-face divergence near roundoff,
face/nodal mismatch entirely localized on wall nodes,
interior mismatch equal to zero,
momentum consistent with the wall-clamped nodal velocity,
next transport still using the preserved face state.
```

Thus the defect is not a bulk pressure solve failure.  It is a split state:

```text
transport velocity = f,
momentum velocity  = B_h R_h f.
```

This violates the common-flux phase-space identity.

## KKT Contract

Given predictor face velocity `f_dag`, solve

```text
min_f 1/2 ||f-f_dag||_{M_f(q)}^2
subject to D_h f = 0,
           B_h R_h f = 0.
```

The stationarity equations are

```text
M_f(f-f_dag) + D_h^T p + (B_h R_h)^T lambda = 0,
D_h f = 0,
B_h R_h f = 0.
```

With the production pressure-adjoint face map `G_A`, the practical form is

```text
f = f_dag - G_A p - M_f^{-1}(B_h R_h)^T lambda.
```

`lambda` is a wall reaction, not damping.  It is the no-slip Lagrange
multiplier.

## Acceptance Gates

A preserved face-state step is valid only if:

```text
D_h f <= tolerance_div,
B_h R_h f <= tolerance_wall,
u = R_h f,
m = rho u.
```

Checkpoint restart must verify the same invariants.

## Rejected Shortcuts

Do not fix this by:

```text
turning off canonical face state,
zeroing boundary faces only,
post-clamping nodal velocity while preserving old faces,
recomputing faces from clamped nodes without a Hodge projection,
penalty slip,
CFL reduction,
smoothing,
curvature caps,
DCCD/UCCD damping.
```

The mathematical remedy is to include the wall trace constraint in the same
metric projection as pressure.

## Active Reading

Read SP-AL for the full derivation.  Read [[WIKI-T-164]] for the common-flux
state, [[WIKI-T-165]] for variational gravity, and [[WIKI-T-162]] for
closed-interface capillary covectors.
