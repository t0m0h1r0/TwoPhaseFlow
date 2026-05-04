---
ref_id: WIKI-T-120
title: "Face Jet Has Mixed Accuracy by Design"
domain: theory
status: ACTIVE
superseded_by: null
tags: [face_jet, fccd, mixed_accuracy, hermite, face_operator]
sources:
  - path: paper/sections/04f_face_jet.tex
    description: "Face jet components and their O(H4)/O(H2) accuracy roles"
depends_on:
  - "[[WIKI-T-069]]"
  - "[[WIKI-T-117]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Mixed-Accuracy Face Jet

## Knowledge Card

The face jet

```text
J_f(u) = (u_f, u'_f, u''_f)
```

is intentionally mixed-order.  The face value and face gradient are fourth
order, while the face second derivative is a second-order auxiliary average.
This is not a bug: the second-derivative component is used for diagnostics and
connection conditions, not as an independent high-order face unknown.

## Consequences

- Consumers must not assume every face-jet component has the same formal order.
- `u''_f` should not be used where a fourth-order primary flux value is required.
- The API carries a coherent Hermite tuple, not a uniform-accuracy tuple.
- Verification should test `u_f/u'_f` and `u''_f` against their different
  design orders.

## Paper-Derived Rule

Read FaceJet as a three-component contract with component-specific accuracy,
not as three interchangeable fourth-order face fields.
