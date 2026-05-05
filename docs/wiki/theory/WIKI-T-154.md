---
ref_id: WIKI-T-154
title: "Raw Interface-Band Pressure Is Not the Physical Scalar Observable"
domain: theory
status: ACTIVE
tags: [pressure, hodge_representative, diffuse_interface, diagnostics]
sources:
  - path: paper/sections/09f_pressure_summary.tex
  - path: paper/sections/13f_error_budget.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# Raw Interface-Band Pressure Is Not the Physical Scalar Observable

## Claim

For affine-jump projection, physical pressure work is carried by the face cochain
`A_f(G_f p - B_f(j))`.  A raw nodal pressure inside the diffuse interface band
is an internal representative, not a directly observable phase pressure.

## Effective Knowledge

- Bulk pressure contrast and face pressure acceleration can remain stable while
  raw nodal values in `0.05 < psi < 0.95` oscillate.
- Hodge or phase-bulk representatives are appropriate output views because
  they match the face-space object used by momentum.
- Raw pressure snapshots remain useful diagnostics, but not evidence of a
  physical pressure field in the band.

## Rejected Reading

Reading `fields/pressure` at the smeared interface as the physical scalar
pressure confuses gauge/extension data with phase pressure.  It can misdiagnose
a visualization representative error as a force-balance failure.

## Implication

Pressure plots for affine-jump runs should use `pressure_hodge` or phase-masked
representatives, while analyses of momentum coupling should inspect the face
acceleration/cochain diagnostics.
