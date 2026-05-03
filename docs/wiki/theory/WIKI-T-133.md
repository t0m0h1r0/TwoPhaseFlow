---
ref_id: WIKI-T-133
title: "The Adjoint PPE Pair Solves F-2 and F-3 Together"
domain: theory
status: ACTIVE
superseded_by: null
tags: [balanced_force, adjoint_pair, ppe, projection, collocated_grid]
sources:
  - path: paper/sections/08d_bf_seven_principles.tex
    description: "P-2 adjoint construction and F-2/F-3 failure-mode separation"
depends_on:
  - "[[WIKI-T-130]]"
  - "[[WIKI-T-132]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Adjoint Pair Fixes Two Failures

## Knowledge Card

The paper separates two projection failures:

```text
F-2: PPE gradient path differs from velocity-correction gradient path
F-3: divergence and gradient are not adjoint pairs
```

The P-2 construction fixes both by first choosing the balanced-force gradient
`G_h^bf`, then deriving the divergence as its adjoint:

```text
D_h^bf = -(G_h^bf)^*
```

This makes the PPE and corrector share the same gradient and gives the PPE a
proper SPD structure after gauge removal.

## Consequences

- Patching only the PPE RHS cannot fix F-2 if correction still uses another
  gradient.
- Adjointness is a system property, not a property of one operator alone.
- The selected gradient path determines the entire projection pair.
- Non-uniform grids can switch to a face-adjoint pair without being an F-2
  violation, as long as PPE and corrector both switch.

## Paper-Derived Rule

Build projection from one chosen gradient and its adjoint divergence; do not
assemble PPE and correction gradients independently.
