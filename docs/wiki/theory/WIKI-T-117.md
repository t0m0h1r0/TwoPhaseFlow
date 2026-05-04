---
ref_id: WIKI-T-117
title: "CCD Sixth Order Comes from Coupling f-prime and f-double-prime Unknowns"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ccd, compact_difference, sixth_order, coupled_unknowns, taylor]
sources:
  - path: paper/sections/04_ccd.tex
    description: "CCD core idea and coefficient derivation from coupled first/second derivatives"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-011]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# CCD Coupling Source of Order

## Knowledge Card

CCD reaches sixth order on a three-point compact stencil because it solves first
and second derivatives as coupled unknowns.  Equation-I and Equation-II each
carry three independent coefficient conditions, so the method gets six coupled
constraints rather than treating `f'` as the only implicit unknown.

This is not "ordinary compact FD with nicer coefficients."  The extra order
comes from the simultaneous Hermite-like solve for `(f', f'')`.

## Consequences

- Dropping the second-derivative unknown changes the method class.
- Boundary closures must preserve the coupled character as far as possible.
- Reusing CCD output downstream means reusing a coupled derivative pair, not
  two independent finite differences.
- The three-point support is misleading unless the global compact solve is
  counted.

## Paper-Derived Rule

When auditing CCD implementations, check that first and second derivatives are
solved as a coupled system; otherwise the sixth-order claim has lost its
mechanism.
