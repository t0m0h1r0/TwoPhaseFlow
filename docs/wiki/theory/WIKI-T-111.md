---
ref_id: WIKI-T-111
title: "xi_ridge Intentionally Violates Eikonal to Carry Topology"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ridge_eikonal, xi_ridge, topology, eikonal, morse, interface]
sources:
  - path: paper/sections/03d_ridge_eikonal.tex
    description: "Gaussian auxiliary field and ridge-set topology representation"
depends_on:
  - "[[WIKI-T-047]]"
  - "[[WIKI-T-048]]"
  - "[[WIKI-T-078]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# xi_ridge Topology Carrier

## Knowledge Card

`xi_ridge` is not a signed-distance function and is not supposed to satisfy
`|grad phi|=1`.  The paper deliberately lets it have local extrema and saddle
points so that mergers and splits can be represented as continuous changes in a
Gaussian auxiliary field.

The design separates two jobs:

```text
xi_ridge : topology freedom via ridge/critical-set evolution
phi      : metric distance reconstructed afterward by Eikonal/FMM
```

This is why forcing Eikonal regularity onto `xi_ridge` would destroy the very
degree of freedom it is introduced to carry.

## Consequences

- `xi_ridge` diagnostics should look for ridge topology, not SDF accuracy.
- Eikonal error metrics are meaningful for reconstructed `phi`, not for
  `xi_ridge`.
- Topology changes are handled before the distance-field contract is restored.
- Grid-density Gaussian fields must not be confused with `xi_ridge`.

## Paper-Derived Rule

Preserve the topology/metric split: let `xi_ridge` be non-Eikonal, then rebuild
`phi` as the metric field after the ridge set is chosen.
