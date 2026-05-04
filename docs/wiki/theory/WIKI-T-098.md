---
ref_id: WIKI-T-098
title: "Jump-Corrected Face Gradients Have One Global Gauge"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ppe, gauge, pressure_jump, face_gradient, neumann, balanced_force]
sources:
  - path: paper/sections/09b_split_ppe.tex
    description: "Jump-corrected face flux invariant and gauge choice"
  - path: paper/sections/09e_ppe_bc.tex
    description: "Neumann zero-mode handling and gauge principles"
depends_on:
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-097]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Jump-Corrected Face Gradient Gauge

## Knowledge Card

A jump-corrected face-gradient PPE is not two disconnected Neumann problems with
separate phase gauges.  The interface faces connect the pressure graph through
the affine face law `G_f(p)-B_f(j)`.

The local invariant is:

```text
if the two pressure values already satisfy the Young--Laplace jump,
the interface face emits no artificial flux.
```

This invariant requires the smooth pressure term and the known jump term to use
the same nonzero face coefficient.  Therefore the null mode is one global
constant, not one constant per phase.

## Consequences

- Phase-wise mean-zero gauges are for fully cut Neumann blocks, not for the
  jump-corrected face law.
- Splitting coefficients between `G_f(p)` and `B_f(j)` breaks the local
  zero-flux invariant.
- The gauge fixes an absolute reference only; velocity correction depends on
  gradients and face jumps.
- Gauge changes or moving pin points can introduce pressure-gradient shocks.

## Paper-Derived Rule

In the adopted pressure-jump closure, choose one global pressure gauge on the
connected affine face graph.
