---
ref_id: WIKI-T-150
title: "Wall-Contact Ridge-Eikonal Needs Closure Seeds and Pinned Mass"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ridge_eikonal, wall_contact, contact_line, fmm, mass_correction, grid_fitting]
sources:
  - path: docs/memo/CHK-RA-WALL-RIDGE-001_wall_closure_ridge_eikonal.md
    description: "Wall-closure Ridge-Eikonal theory and implementation implications"
depends_on:
  - "[[WIKI-T-081]]"
  - "[[WIKI-T-084]]"
  - "[[WIKI-T-112]]"
  - "[[WIKI-T-144]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Wall-Contact Ridge-Eikonal

## Knowledge Card

A wall-attached interface is a zero set on the closed domain, not merely an
interior curve that happens to approach a boundary:

```text
closed interface = interior interface + contact-line set on the wall
```

Ridge extraction, FMM redistancing, mass correction, and interface-fitted grid
monitors must preserve that closed-domain zero set.  Otherwise a free-domain
Gaussian or FMM pipeline can create an artificial wall gap even when the
physical interface remains attached.

## Consequences

- Wall contacts must be explicit FMM seeds, not emergent sign-change accidents.
- Gaussian ridge support near walls needs mirror/closure extension, otherwise
  half-support biases the ridge inward.
- Boundary ridge admissibility is a constrained maximum condition on the
  closed domain.
- Mass correction must be pinned in a contact-line band; if the free correction
  weight is too small, skip and report rather than shift the contact line.
- Grid-fitting monitors must include wall endpoint projections, not only
  interior `min |phi|` samples.

## Paper-Derived Rule

Treat wall-contact preservation as a geometry reconstruction contract before
changing Navier-Stokes wall boundary conditions.
