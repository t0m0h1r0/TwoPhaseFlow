---
ref_id: WIKI-T-090
title: "Boundary Closure Honesty: Interior Order Is Not Whole-Domain Order"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ccd, boundary_closure, convergence_order, l2_norm, gks, verification]
sources:
  - path: paper/sections/04b_ccd_bc.tex
    description: "Boundary closure error contribution to global L2 convergence"
  - path: paper/sections/04d_uccd6.tex
    description: "UCCD6 periodic stability theorem and bounded-domain verification scope"
depends_on:
  - "[[WIKI-T-011]]"
  - "[[WIKI-T-079]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Boundary Closure Honesty

## Knowledge Card

CCD's interior `O(h^6)` accuracy is not automatically a whole-domain convergence
claim.  With low-order boundary closure, the boundary occupies only `O(h)` measure
but can still dominate the global `L2` asymptotic rate.

The paper's boundary analysis gives the key example: pointwise `O(h^2)` boundary
error contributes `O(h^{5/2})` to the whole-domain `L2` norm, even when interior
points are `O(h^6)`.

## Consequences

- Interior-only measurements and whole-domain measurements answer different
  questions.
- Observed high order at finite resolution can be a small boundary coefficient,
  not an asymptotic theorem.
- Periodic UCCD6 stability does not automatically transfer to bounded domains.
- Bounded-domain UCCD6 claims require spectrum/MMS verification with the chosen
  boundary closure.

## Paper-Derived Rule

When reporting CCD order, state the boundary closure and whether the metric is
interior, boundary-excluded, or whole-domain.
