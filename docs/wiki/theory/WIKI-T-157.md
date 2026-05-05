---
ref_id: WIKI-T-157
title: "ALE Discrete-Gradient Energy Endpoints Are Step-Local"
domain: theory
status: ACTIVE
tags: [ale, discrete_gradient, surface_energy, remap]
sources:
  - path: paper/sections/14_benchmarks.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# ALE Discrete-Gradient Energy Endpoints Are Step-Local

## Claim

In the ALE/discrete-gradient route, the previous surface-energy endpoint is the
pre-remap endpoint of the current rebuild step only.

## Effective Knowledge

- Carrying a `previous_surface_energy` value across non-rebuild steps mixes
  different grid measures in one discrete gradient.
- The fix is conceptual, not numerical tuning: make the old-grid endpoint a
  step-local state and clear it outside the remap operation.
- This preserves the intended pressure-work/surface-energy pairing before
  asking whether the variational closure itself is sufficient.

## Rejected Reading

Adding a fixed epsilon to hide a zero-step `0/0`, or letting stale endpoint data
survive between unrelated steps, is not a valid discrete-gradient formulation.

## Implication

Every ALE/remap energy correction must name its two endpoints, their grid
measures, and the exact step in which the pairing is valid.
