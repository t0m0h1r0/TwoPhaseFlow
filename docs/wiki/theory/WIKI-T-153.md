---
ref_id: WIKI-T-153
title: "Affine Pressure History Lives as a Face Acceleration Cochain"
domain: theory
status: ACTIVE
tags: [affine_jump, pressure_history, face_cochain, projection_native]
sources:
  - path: paper/sections/09b_split_ppe.tex
  - path: paper/sections/14_benchmarks.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# Affine Pressure History Lives as a Face Acceleration Cochain

## Claim

In affine-jump IPC, pressure history is the canonical face acceleration
`A_f(G_f p^n - B_f(j^n))`, not a nodal scalar pressure differentiated later.

## Effective Knowledge

- The predictor, PPE right-hand side, velocity corrector, and next history must
  all use the same face-space jump contract.
- The previous full face pressure cochain contributes to the affine PPE source;
  the corrector applies the cochain increment.
- Static and oscillating N64 alpha-2 gates improved only when the pressure
  history was stored and reused in this face cochain form.

## Rejected Reading

Reconstructing a discontinuous nodal `p^n` and differentiating it in the next
predictor injects a nonphysical interface acceleration.  Reusing the new full
affine cochain directly as the correction also violates the unknown/increment
split.

## Implication

Pressure history is part of the same discrete connection as the pressure jump.
Any refactor must preserve the face object, its sign, its cut-face distance, and
its coefficient.
