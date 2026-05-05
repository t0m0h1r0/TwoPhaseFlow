---
ref_id: WIKI-T-152
title: "PPE Defect Correction Accuracy Is a Residual Contract, Not a Fixed k"
domain: theory
status: ACTIVE
tags: [ppe, defect_correction, residual_contract, projection]
sources:
  - path: paper/sections/09d_defect_correction.tex
  - path: paper/sections/11_full_algorithm.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# PPE Defect Correction Accuracy Is a Residual Contract, Not a Fixed k

## Claim

The production PPE solve is accepted by the high-order residual
`||b - L_H p|| / ||b||`, not by reaching a fixed number of defect-correction
steps.

## Effective Knowledge

- Component tests show why `k=3` is a useful split-PPE certificate in idealized
  phase-internal Poisson problems.
- N64 alpha-2 affine-jump runs showed that the same `k=3` reading is not a
  production accuracy contract.
- DC12 reduced the measured projection residual to `O(1e-9)` and the projected
  divergence to `O(1e-11)` for the short N64 gates.

## Rejected Reading

Treating `k=3` as a universal solver certificate conflates a component
asymptotic result with the integrated capillary projection problem.

## Implication

Long capillary runs must report the true high-order PPE residual.  If the
residual has not met the configured tolerance, pressure/interface artifacts
cannot be interpreted as physical closure errors yet.
