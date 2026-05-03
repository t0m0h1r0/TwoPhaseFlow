---
ref_id: WIKI-T-106
title: "Diffuse Interface Width Has Operational Bands"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, interface_width, epsilon, psi, property_interpolation, diagnostics]
sources:
  - path: paper/sections/01_introduction.tex
    description: "CLS transition-layer width convention and psi phase convention"
  - path: paper/sections/02_governing.tex
    description: "psi-based density and viscosity interpolation"
depends_on:
  - "[[WIKI-T-078]]"
  - "[[WIKI-T-093]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Operational Interface Bands

## Knowledge Card

The paper's diffuse interface width is not a single informal thickness.  It
uses several operational bands:

```text
center transition width  ~= 2 epsilon
95% transition band      ~= |phi| <= 3 epsilon
liquid convention        psi ~= 1
gas convention           psi ~= 0
```

These bands connect geometry, material properties, and diagnostics.  The same
`psi` convention drives interpolation such as `rho(psi)` and `mu(psi)`, so a
width/sign mismatch silently becomes a material-property mismatch.

## Consequences

- Width claims should specify whether they refer to center width or full
  transition support.
- `psi=1` must mean liquid everywhere, including figures, interpolation, and
  verification prose.
- A nominal `epsilon` change is a coupled change to curvature support,
  delta-like force support, and material-transition support.
- Interface-band tests should record the band definition they use.

## Paper-Derived Rule

Treat `epsilon` as an operational interface-band contract, not as a cosmetic
plotting parameter.
