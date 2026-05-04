---
ref_id: WIKI-T-099
title: "HFE Extends Smooth One-Sided Fields, Not Pressure-History Contracts"
domain: theory
status: ACTIVE
superseded_by: null
tags: [hfe, pressure_history, affine_jump, projection, predictor, face_acceleration]
sources:
  - path: paper/sections/09b_split_ppe.tex
    description: "HFE role and affine pressure-history face acceleration"
  - path: paper/sections/09c_hfe.tex
    description: "HFE projection-stage placement and conditional necessity"
depends_on:
  - "[[WIKI-T-018]]"
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-097]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# HFE and Pressure-History Contracts

## Knowledge Card

HFE is a one-sided smooth field extension.  It prevents CCD/FCCD stencils from
directly crossing pressure jumps, and it is essential for high-density-ratio
phase-separated PPE.  But HFE does not replace the cut-face pressure-history
contract.

For projection-native affine-jump IPC, the previous pressure contribution is
stored canonically as a face acceleration built from the same affine jump law:

```text
a_p,f^n = A_f (G_f p^n - B_f(j^n))
```

The next predictor consumes that face acceleration, not a raw nodal derivative
of `p^n`.

## Consequences

- HFE is unnecessary and potentially harmful for smooth smoothed-Heaviside
  contrast runs.
- HFE is mandatory when phase-separated PPE exposes a Young--Laplace pressure
  jump to high-order stencils.
- Previous pressure history must remain on the same cut-face affine contract.
- Extending a field does not license differentiating raw discontinuous pressure
  across an interface.

## Paper-Derived Rule

Use HFE to restore one-sided smoothness; use the affine face law to preserve
projection history.
