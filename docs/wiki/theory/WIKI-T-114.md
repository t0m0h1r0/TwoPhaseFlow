---
ref_id: WIKI-T-114
title: "Reinitialization Mass Conservation Changes Measure on Nonuniform Grids"
domain: theory
status: ACTIVE
superseded_by: null
tags: [reinitialization, mass_conservation, nonuniform_grid, volume_weight, cls]
sources:
  - path: paper/sections/05_reinitialization.tex
    description: "Mass conservation and volume-weighted correction for non-uniform grids"
depends_on:
  - "[[WIKI-T-031]]"
  - "[[WIKI-T-086]]"
  - "[[WIKI-T-096]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Reinit Mass Measure

## Knowledge Card

On a uniform periodic grid, zero-sum derivative operators can make the
unweighted sum of `psi` a useful conservation proxy.  On a non-uniform grid,
that measure is wrong.  The conserved quantity becomes the volume-weighted
mass:

```text
M = sum_ij psi_ij * DeltaV_ij
```

The same change of measure applies to interface weights used during mass
correction.  A computation-space zero sum does not automatically preserve the
physical volume-weighted integral.

## Consequences

- Non-uniform reinitialization must audit physical mass, not raw array sums.
- Clamp/reinit/remap steps need volume-weighted correction after they alter
  `psi`.
- Uniform-grid conservation proofs cannot be copied unchanged to stretched
  grids.
- The correction target is the physical volume integral of the phase indicator.

## Paper-Derived Rule

Whenever grid spacing varies, define CLS mass and correction weights in physical
cell volume, not in index-space counts.
