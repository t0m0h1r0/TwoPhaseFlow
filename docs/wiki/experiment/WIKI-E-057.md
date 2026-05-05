---
ref_id: WIKI-E-057
title: "Wall-Contact Capillary Blowup Can Be a Curvature-Closure Energy Defect"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [ch14, capillary_wave, wall_contact, curvature, energy_defect, rca]
sources:
  - path: artifacts/A/ch14_capillary_energy_wall_curvature_rca_CHK-RA-GPU-UTIL-013.md
    description: "Capillary energy instability RCA after wall topology fix"
  - path: artifacts/A/ch14_no_slip_contact_line_theory_design_CHK-RA-GPU-UTIL-009.md
    description: "No-slip contact-line invariant and wall-contact constraint service design"
depends_on:
  - "[[WIKI-T-150]]"
  - "[[WIKI-E-055]]"
  - "[[WIKI-X-043]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Wall-Contact Curvature Energy Defect

## Knowledge Card

After wall topology is fixed, a capillary-wave failure can still be caused by
the curvature/stress closure at the wall-contact neighborhood.  The important
distinction is:

- wall-contact topology remains pinned;
- the first-mode Young--Laplace sign is restoring;
- nevertheless, bulk nodal curvature near a no-slip contact point on a fitted
  non-uniform grid can become orders of magnitude too large.

The RCA observed runtime wall-neighborhood curvature of order `1e2` where the
expected mode-2 curvature amplitude was order `1`.  That defect is clipped,
averaged into affine pressure-jump faces, and inserted into the PPE/corrector
without a discrete surface-energy identity.  The result is high-frequency
capillary work, not a contact-line drift or gross sign reversal.

## Consequences

- A no-slip wall-contact benchmark needs both contact-line pinning and a
  wall-compatible curvature/contact geometry closure.
- CFL reduction, curvature caps, smoothing, or relaxed wall topology are masks
  unless they restore the same discrete capillary-energy law.
- Volume drift and advective limiter activation can be downstream symptoms;
  early large balanced-force residuals are the sharper RCA signal.
- Initial-state local reconstruction around wall contacts is a decisive test:
  boundary-layer exclusion should collapse anomalous curvature if the wall
  closure is the source.

## Paper-Derived Rule

For wall-attached capillary waves, judge repair candidates by pinned wall
contact plus non-increasing capillary-plus-kinetic energy.  A bulk curvature
formula is not automatically valid at no-slip contact points.
