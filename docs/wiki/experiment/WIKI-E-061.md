---
ref_id: WIKI-E-061
title: "N64 Non-DC Trial Matrix Separates Contracts from Probes"
domain: experiment
status: ACTIVE
tags: [ch14, n64_alpha2, rca, negative_knowledge, trial_matrix]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
  - path: paper/sections/14_benchmarks.tex
---

# N64 Non-DC Trial Matrix Separates Contracts from Probes

## Claim

The N64 alpha-2 RCA was not a DC-only investigation.  Non-DC trials should be
retained as a matrix of contract-confirming fixes, falsified hypotheses, and
diagnostic probes.

## Contract-Confirming Fixes

- Projection-native CLS transport: use the projected face velocity directly.
- Affine pressure-history faces: carry history as a jump-corrected face
  acceleration cochain.
- Hodge/phase pressure representative: do not read raw interface-band pressure
  as the physical scalar pressure.
- Volume-weighted phase pressure diagnostics: use grid volume, not arithmetic
  node means, on fitted grids.
- ALE discrete-gradient endpoint hygiene: keep old-grid surface energy
  step-local.

## Falsified or Non-Production Probes

- Raw nodal pressure plots in the diffuse band are diagnostics, not proof of
  momentum-force failure.
- Static-grid, `fccdface`, `transportvar`, `phi`, `purerho`, and `cutrho`
  variants are useful controls only when paired with a stated acceptance gate.
- Long brute-force one-period attempts without short gates do not isolate root
  cause.
- Damping, smoothing, curvature caps, hyperviscosity, and blind CFL reduction
  remain outside the accepted theory route.

## Implication

Paper text should cite only the contract-confirming fixes.  Wiki and ledger
should preserve the probes so future work does not repeat them as if they were
new solutions.
