---
ref_id: WIKI-T-122
title: "FCCD Balanced-Force Fourth Order Requires a Smooth Constructive Relation"
domain: theory
status: ACTIVE
superseded_by: null
tags: [fccd, balanced_force, chain_rule, face_locus, smoothness, pressure]
sources:
  - path: paper/sections/04e_fccd.tex
    description: "Same-face FCCD operator consistency and O(dx4) residual condition"
  - path: paper/sections/08e_fccd_bf.tex
    description: "GFM/IIM limitations for balanced-force residual order"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-088]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Smooth-Relation BF Order

## Knowledge Card

Applying FCCD to two fields on the same face gives them a common locus, metric,
and Fourier symbol.  The paper's fourth-order balanced-force residual claim
needs one more condition: the continuous fields must be smoothly related, e.g.
`p = P(psi)` with `P'` evaluated on the same face.

Without that constructive relation, `D_f p - g(psi_f) D_f psi` is not promised
to be small merely because both derivatives use FCCD.

## Consequences

- Same operator is necessary for BF consistency but not sufficient for arbitrary
  unrelated fields.
- Standard GFM pressure-jump closure can remain second-order limited even when
  face operators are high-order.
- IIM-style row correction is the path that can promote the jump closure to the
  face-operator order.
- BF audits must state both locus sharing and jump/field smoothness assumptions.

## Paper-Derived Rule

Use FCCD shared faces to preserve the chain-rule structure only when the fields
being balanced come from the same smooth relation or a corrected jump closure.
