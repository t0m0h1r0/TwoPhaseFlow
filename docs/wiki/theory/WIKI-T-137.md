---
ref_id: WIKI-T-137
title: "Nonuniform FCCD Fourth Order Is a Central-Face Contract"
domain: theory
status: ACTIVE
superseded_by: null
tags: [nonuniform_grid, fccd, face_centrality, order_condition, interface_fitted]
sources:
  - path: paper/sections/10c_fccd_nonuniform.tex
    description: "Nonuniform FCCD face expansion, theta centrality, and fourth-order verification scope"
depends_on:
  - "[[WIKI-T-095]]"
  - "[[WIKI-T-122]]"
  - "[[WIKI-T-136]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Central-Face FCCD Contract

## Knowledge Card

Nonuniform FCCD does not promise fourth-order behavior at every face.  The
general off-center face expansion is only `O(H^3)`, while the central-face case
recovers `O(H^4)` when the local geometry satisfies `theta = 1/2`.

The verification contract is therefore:

```text
interface-fitted / central face  -> fourth-order FCCD target
off-center or closure face       -> special lower-order face
```

## Consequences

- `O(dx^4)` nonuniform FCCD claims require a face-centrality audit.
- Boundary, HFE, GFM, and jump faces cannot be silently included in the same
  fourth-order population.
- A stretched grid can be high-order only where the local face geometry is
  treated as central by construction.
- The order claim is a local geometry contract, not a generic property of
  variable-spacing interpolation.

## Paper-Derived Rule

When reading nonuniform FCCD results, ask which faces satisfy the central-face
condition before interpreting a fourth-order slope.
