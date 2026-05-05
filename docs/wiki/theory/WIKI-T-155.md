---
ref_id: WIKI-T-155
title: "Discrete Variational Closure Requires Shared Surface-Energy and Pressure-Work Pairing"
domain: theory
status: ACTIVE
tags: [discrete_variational_principle, curvature, pressure_work, ale, remap]
sources:
  - path: paper/sections/09b_split_ppe.tex
  - path: paper/sections/13f_error_budget.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# Discrete Variational Closure Requires Shared Surface-Energy and Pressure-Work Pairing

## Claim

Surface energy differences and pressure work close only when the curvature
force, pressure jump, transport, and remap are paired by the same discrete
variation.

## Effective Knowledge

- A viable route is an ALE/discrete-gradient formulation in which surface area
  variation and pressure work are adjoint under the same face transport/remap
  operator.
- The interface-force object must live in the same face space as the projection
  corrector; otherwise energy can move between geometry and pressure through
  unmatched discrete pairings.
- The useful theory is not "make curvature smoother"; it is "make the surface
  variation and pressure work the same bilinear pairing."

## Rejected Reading

Implicit curvature alone, CCD curvature alone, hyperviscosity, damping, CFL
reduction, smoothing, or curvature caps do not close the variational identity.
They may hide high-frequency symptoms, but they do not prove that surface
energy loss equals pressure work.

## Implication

Future curvature work should be formulated as a mass/weak variational solve only
when its test space, transport map, and pressure-work adjoint are specified
together.
