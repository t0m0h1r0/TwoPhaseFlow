---
ref_id: WIKI-T-109
title: "Direct psi Curvature Is Interface-Band Only"
domain: theory
status: ACTIVE
superseded_by: null
tags: [curvature, psi, interface_band, saturation, cls, surface_tension]
sources:
  - path: paper/sections/03c_levelset_mapping.tex
    description: "Direct psi curvature formula and interface-band applicability"
depends_on:
  - "[[WIKI-T-008]]"
  - "[[WIKI-T-079]]"
  - "[[WIKI-T-108]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Interface-Band Curvature

## Knowledge Card

Direct `psi` curvature is not a license to evaluate curvature everywhere.  The
formula is meant for the non-saturated interface band, typically

```text
psi_min < psi < 1 - psi_min
```

with far-field cells assigned no surface-tension contribution.  The reason is
structural: `|grad psi|` is largest near `psi ~= 0.5` and vanishes as `psi`
approaches either bulk phase.

The paper's hybrid policy is therefore "evaluate high-order curvature where
`psi` is a resolved monotone profile; set irrelevant far-field curvature to
zero."

## Consequences

- Far-field curvature values are not physical observables in the CSF product.
- Division by tiny `|grad psi|` is a domain-of-application error, not just a
  floating-point issue.
- Curvature masks should follow the same interface-band convention as surface
  force support.
- Reinitialization quality matters because it preserves the monotone profile
  that makes direct curvature meaningful.

## Paper-Derived Rule

Apply direct `psi` curvature only inside the resolved interface band; outside
that band, remove the surface-tension contribution instead of regularizing a
meaningless curvature.
