---
ref_id: WIKI-T-071
title: "Face-Canonical Variable-Density Projection: Literature Survey and PoC Ladder"
domain: theory
status: PROPOSED
superseded_by: null
sources:
  - description: "Almgren, Bell, Szymczak, Howell (1998). A Conservative Adaptive Projection Method for the Variable Density Incompressible Navier–Stokes Equations."
  - description: "Brown, Cortez, Minion (2001). Projection Method III: Spatial Discretization on the Staggered Grid."
  - description: "Guermond, Salgado (2009). A Splitting Method for Incompressible Flows with Variable Density Based on a Pressure Poisson Equation."
  - description: "Rudman (1998). A Volume-Tracking Method for Incompressible Multifluid Flows and Large Density Variations."
  - description: "Raessi, Pitsch (2012). Consistent Mass and Momentum Transport for Simulating Incompressible Interfacial Flows with Large Density Ratios Using the Level Set Method."
  - description: "Dodd, Ferrante (2014). A Fast Pressure-Correction Method for Incompressible Two-Fluid Flows."
  - description: "François et al. (2006). A Balanced-Force Algorithm for Continuous and Sharp Surface Tension Models Within a Volume Tracking Framework."
  - description: "Popinet (2009). An Accurate Adaptive Solver for Surface-Tension-Driven Interfacial Flows."
  - description: "Kumar, Natarajan (2017). A Novel Consistent and Well-Balanced Algorithm for Simulations of Multiphase Flows on Unstructured Grids."
  - description: "Hysing et al. (2009). Quantitative Benchmark Computations of Two-Dimensional Bubble Dynamics."
depends_on:
  - "[[WIKI-T-066]]: Body-force discretization in variable-density NS"
  - "[[WIKI-T-068]]: FCCD face-flux projector"
  - "[[WIKI-T-070]]: Rising-bubble projection-closure diagnosis"
consumers:
  - "[[WIKI-E-031]]: ch13 rising-bubble hypothesis verdicts"
tags: [variable_density, projection, staggered, face_canonical_state, buoyancy, balanced_force, rising_bubble]
compiled_by: ResearchArchitect
compiled_at: "2026-04-24"
---

# Face-Canonical Variable-Density Projection

## Core conclusion

The literature on variable-density incompressible flow, large-density-ratio
multiphase transport, and balanced-force discretisation points in the same
direction:

> the post-corrector velocity should remain canonical on the same face/staggered
> locus where the projection equation is closed.

This is the most credible remedy class for the current ch13 rising-bubble
projection-closure failure.

## Why the survey converges here

### 1. Projection consistency

Almgren et al., Brown–Cortez–Minion, and Guermond–Salgado all imply that the
pressure corrector is not merely a scalar solve; it is a same-space closure
contract between:

- divergence
- pressure gradient
- density weighting
- post-corrector velocity state

If the corrector closes in face space but the authoritative state immediately
returns to nodal space, the closure guarantee weakens.

### 2. Density-ratio consistency

Rudman, Raessi–Pitsch, and Dodd–Ferrante strengthen the same conclusion for
two-phase flows with strong density contrast. They emphasise that stable runs
depend on consistency between mass transport, momentum transport, and
pressure-correction weighting, not just on stronger linear algebra.

### 3. Well-balanced forcing

François, Popinet, and Kumar–Natarajan show that pressure gradient, surface
tension, and buoyancy should be paired on the same geometric locus when the goal
is spurious-current suppression and equilibrium preservation.

This means a buoyancy-only patch is not the right first move if the underlying
state ownership is mismatched.

## Reading for the current FCCD stack

The current FCCD path already contains a face-flux PPE and a face-flux
projection operator. The survey therefore does **not** argue for inventing a new
projection family. Instead, it argues for changing what the runtime treats as
the **canonical** post-corrector state.

In practical terms:

- corrected face flux should be explicitly carried across timesteps
- nodal velocity should become a reconstructed, compatibility-facing view
- face divergence should become the primary incompressibility witness where
  available

## What the survey does not support as a first cure

- increasing PPE iterations alone
- moving buoyancy without changing state ownership
- treating hydrostatic split as the first and only fix

Hydrostatic split remains a useful follow-up for conditioning, but the survey
places it after the canonical-state correction, not before.

## PoC ladder

### P0 — explicit face-state carry

Make corrected face flux available as an explicit grouped step result and accept
it as an explicit grouped step input.

### P1 — runner-level propagation

Teach `runner.py` to propagate that face state between steps on an opt-in path.

### P2 — face divergence gate

Promote face divergence to the primary incompressibility gate when the
face-canonical path is active.

### P3 — same-locus force closure

Only after P0–P2, revisit buoyancy and hydrostatic/residual pressure splitting
under the new canonical state ownership.

## Validation target

The appropriate downstream benchmark is the rising-bubble family in the spirit
of Hysing et al.: stability alone is not enough. The corrected path should also
be judged by centroid rise, deformation, and bounded projection diagnostics.
