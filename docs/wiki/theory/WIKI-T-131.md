---
ref_id: WIKI-T-131
title: "HFE Is Mandatory Only When the Solved Pressure Field Has a Jump"
domain: theory
status: ACTIVE
superseded_by: null
tags: [hfe, pressure_jump, split_ppe, smoothed_heaviside, ccd, projection]
sources:
  - path: paper/sections/09c_hfe.tex
    description: "HFE scope for split PPE and unnecessary error in smoothed-Heaviside one-PPE path"
depends_on:
  - "[[WIKI-T-099]]"
  - "[[WIKI-T-123]]"
  - "[[WIKI-T-129]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# HFE Scope by Pressure Regularity

## Knowledge Card

HFE is not a universal pressure post-processor.  In a smoothed-Heaviside
one-PPE path, pressure is regularized and smooth; applying HFE can add
unnecessary extrapolation error.  In the high-density split-PPE path, pressure
has an explicit Young--Laplace jump, so CCD stencils must not cross the raw
field.  HFE is then mandatory.

The paper applies HFE in two projection places:

```text
p^n       before predictor pressure-gradient evaluation
delta p   before velocity correction
```

## Consequences

- HFE necessity is determined by the regularity of the pressure unknown being
  differentiated.
- Smooth one-PPE and split-PPE pressure paths should not share one blind HFE
  toggle.
- Applying CCD across a raw jump is the thing HFE prevents.
- HFE belongs to the split-PPE pressure-jump closure, not to every CSF path.

## Paper-Derived Rule

Use HFE when the pressure field being differentiated carries an explicit jump;
avoid it when the chosen pressure closure is already smooth.
