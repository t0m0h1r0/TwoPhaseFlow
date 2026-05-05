---
ref_id: WIKI-E-059
title: "Projection Underconvergence Was a Real N64 Pressure RCA Component"
domain: experiment
status: ACTIVE
tags: [ch14, ppe_residual, defect_correction, rca]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
  - path: paper/sections/09d_defect_correction.tex
---

# Projection Underconvergence Was a Real N64 Pressure RCA Component

## Claim

The N64 alpha-2 pressure investigation found a real outer defect-correction
underconvergence component before the remaining pressure-representative issue.

## Evidence

- DC3: final relative residual `8.677e-04`, `div_u_max=1.477e-05`.
- DC6: final relative residual `9.617e-06`, `div_u_max=1.466e-07`.
- DC10: final relative residual `3.670e-08`, still above the target.
- DC12: final relative residual `2.505e-09`, `div_u_max=3.256e-11`, converged.

## Rejected Reading

Pressure artifacts after an unconverged projection cannot be assigned to
curvature or surface tension theory.  The elliptic equation must first be solved
to its own high-order residual contract.

## Implication

The N64 production configs correctly raise projection DC capacity.  Future RCA
must report both the physical metric and the PPE residual metric.
